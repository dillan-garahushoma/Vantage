"""Explicitly destructive acceptance ONLY on this workspace's migration-test DB.

Never target development/customer databases. Does not print connection secrets,
account credentials, bearer tokens or HTTP bodies. Leaves synthetic evidence rows.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import httpx
import psycopg2
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def guarded_url():
    url = make_url(os.environ['DATABASE_URL'])
    if (url.host, url.port, url.database) != ('127.0.0.1', 54329, 'valora_migration_test'):
        raise RuntimeError('Acceptance refuses anything except the dedicated loopback migration-test database.')
    return url


def connect():
    url = guarded_url()
    connection = psycopg2.connect(host=url.host, port=url.port, dbname=url.database,
                                  user=url.username, password=url.password)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != 'valora_migration_test':
            raise RuntimeError('Live database identity mismatch.')
    return connection


def migration_acceptance():
    from app.db.migration_config import configure_database_url
    config = Config(str(BACKEND / 'alembic.ini'))
    configure_database_url(config, os.environ['DATABASE_URL'])
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    command.upgrade(config, 'head')
    stamp = secrets.token_hex(5)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone()[0] == expected_head
        cursor.execute("INSERT INTO estates(name,suburb,city,province) VALUES (%s,'Musgrave','Durban','KwaZulu-Natal') RETURNING estate_id", (f'Migration canary {stamp}',))
        estate_id = cursor.fetchone()[0]
    command.downgrade(config, 'f1a2b3c4d5e6')
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.investment_scenarios')")
        assert cursor.fetchone()[0] is None
        cursor.execute('SELECT name FROM estates WHERE estate_id=%s', (estate_id,))
        assert cursor.fetchone()[0] == f'Migration canary {stamp}'
    command.upgrade(config, 'head')
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name='investment_scenarios' AND column_name='result'")
        assert cursor.fetchone()[0] == 'jsonb'
        cursor.execute('SELECT count(*) FROM estates WHERE estate_id=%s', (estate_id,))
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone()[0] == expected_head
    return {'migration_head': expected_head, 'full_upgrade': True,
            'investment_downgrade_reupgrade': True, 'unrelated_canary_preserved': True}


async def create_http_world():
    from app.core.security import hash_password
    from app.identity.models.estate_membership import EstateMembership
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property
    engine = create_async_engine(os.environ['DATABASE_URL'])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    stamp = secrets.token_hex(5)
    login_secret = secrets.token_urlsafe(32)
    logins = []
    async with factory() as db:
        estate_a = Estate(name=f'HTTP Musgrave {stamp}', suburb='Musgrave', city='Durban', province='KwaZulu-Natal')
        estate_b = Estate(name=f'HTTP Other {stamp}', suburb='Other', city='Durban', province='KwaZulu-Natal')
        db.add_all([estate_a, estate_b])
        await db.flush()
        for index, estate in enumerate([estate_a, estate_a, estate_b], 1):
            email = f'local-{stamp}-{index}@example.com'
            user = User(email=email, full_name=f'Acceptance user {index}', role='resident', password_hash=hash_password(login_secret))
            property_ = Property(estate_id=estate.estate_id, unit_no=f'A{index}', complex_name=estate.name, street_address='Fictional acceptance address')
            db.add_all([user, property_])
            await db.flush()
            db.add(EstateMembership(user_id=user.user_id, estate_id=estate.estate_id, property_id=property_.unit_id, membership_role='resident'))
            logins.append({'email': email, 'estate_id': estate.estate_id, 'property_id': property_.unit_id})
        await db.commit()
    await engine.dispose()
    return logins, login_secret


def http_acceptance():
    # Never send acceptance requests to an unrelated service on this port.
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', 18001))
        except OSError:
            raise RuntimeError('Acceptance port 18001 is already in use.') from None
    # Import model registry before creating references; no metadata.create_all.
    import app.db.database  # noqa: F401
    logins, login_secret = asyncio.run(create_http_world())
    address = 'http://127.0.0.1:18001'
    log_directory = BACKEND.parent / '.local/postgresql'
    server_log = log_directory / 'acceptance-http.log'
    with server_log.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18001'],
                                   cwd=BACKEND, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            with httpx.Client(base_url=address, timeout=15) as client:
                for _ in range(50):
                    if process.poll() is not None:
                        raise RuntimeError('Acceptance API exited before readiness.')
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError('Acceptance API did not become healthy.')
                sessions = []
                for account in logins:
                    response = client.post('/api/v1/auth/login', json={'email': account['email'], 'password': login_secret})
                    assert response.status_code == 200, 'Real login failed.'
                    sessions.append({'Authorization': f"Bearer {response.json()['access_token']}"})
                estate_id, property_id = logins[0]['estate_id'], logins[0]['property_id']
                preset = client.get('/api/v1/investment-scenarios/presets/musgrave', params={'estate_id': estate_id, 'property_id': property_id}, headers=sessions[0])
                assert preset.status_code == 200
                payload = {'estate_id': estate_id, 'property_id': property_id, 'assumptions': preset.json() | {'financing': {}}}
                preview = client.post('/api/v1/investment-scenarios/calculate', json=payload, headers=sessions[0])
                assert preview.status_code == 200
                original = client.post('/api/v1/investment-scenarios', json=payload | {'name': 'HTTP original'}, headers=sessions[0])
                assert original.status_code == 201
                snapshot = original.json()
                assert snapshot['result'] == preview.json()
                revision_payload = payload | {'name': 'HTTP lower rent', 'revision_of': snapshot['scenario_id'], 'assumptions': payload['assumptions'] | {'monthly_rent': '10000'}}
                revised = client.post('/api/v1/investment-scenarios', json=revision_payload, headers=sessions[0])
                assert revised.status_code == 201
                target = f"/api/v1/investment-scenarios/{snapshot['scenario_id']}"
                assert client.get(target, params={'estate_id': estate_id}, headers=sessions[0]).json() == snapshot
                assert client.get(target, params={'estate_id': estate_id}, headers=sessions[1]).status_code == 404
                assert client.get(target, params={'estate_id': estate_id}, headers=sessions[2]).status_code == 403
                assert client.get(target, params={'estate_id': logins[2]['estate_id']}, headers=sessions[2]).status_code == 404
                listed = client.get('/api/v1/investment-scenarios', params={'estate_id': estate_id}, headers=sessions[0])
                assert listed.status_code == 200 and listed.json()['total'] == 2
                message = client.post('/api/v1/contact', json={'name': 'Local acceptance', 'email': logins[0]['email'], 'message': 'Synthetic local acceptance contact persistence check.'})
                assert message.status_code == 201
                with connect() as connection, connection.cursor() as cursor:
                    cursor.execute('SELECT count(*) FROM investment_scenarios WHERE scenario_id IN (%s,%s)', (snapshot['scenario_id'], revised.json()['scenario_id']))
                    assert cursor.fetchone()[0] == 2
                    cursor.execute('SELECT count(*) FROM contact_messages WHERE message_id=%s', (message.json()['id'],))
                    assert cursor.fetchone()[0] == 1
                return {'tcp_http': True, 'real_login': True, 'persisted_roi_and_revision': True,
                        'private_and_cross_estate_denials': True, 'contact_persistence': True}
        finally:
            process.terminate()
            process.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['migration', 'http'])
    args = parser.parse_args()
    guarded_url()
    result = migration_acceptance() if args.mode == 'migration' else http_acceptance()
    result['checked_at'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Exception messages can contain connection credentials or HTTP tokens.
        print(f'Local acceptance failed ({type(error).__name__}); no secrets or response bodies displayed.', file=sys.stderr)
        raise SystemExit(1)
