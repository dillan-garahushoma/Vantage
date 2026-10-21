"""Authenticated TCP acceptance on the dedicated local migration-test database.

Creates synthetic records and retains them. Never logs credentials, bearer
tokens or HTTP bodies. Never targets development or an existing API process.
"""
import asyncio
from datetime import date
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from scripts.accept_local_database import guarded_url, connect  # noqa: E402


async def create_world():
    import app.db.database  # noqa: F401
    from app.core.security import hash_password
    from app.identity.models.estate_membership import EstateMembership
    from app.identity.models.user import User
    from app.property.models.estate import Estate
    from app.property.models.property import Property

    engine = create_async_engine(os.environ['DATABASE_URL'])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    stamp, login_secret = secrets.token_hex(6), secrets.token_urlsafe(32)
    async with factory() as db:
        estate = Estate(name=f'TCP Fictional Musgrave {stamp}', suburb='Musgrave', city='Durban', province='KwaZulu-Natal')
        db.add(estate)
        await db.flush()
        unit = Property(estate_id=estate.estate_id, unit_no='M-101', complex_name=estate.name,
                        street_address='Fictional acceptance address')
        db.add(unit)
        await db.flush()
        users = []
        for index, role in enumerate(('hoa_admin', 'resident', 'estate_agent', 'resident')):
            user = User(email=f'market-{stamp}-{index}@example.com', full_name=f'Acceptance market {index}',
                        role=role, password_hash=hash_password(login_secret), email_verified=True, hoa_approved=True)
            db.add(user)
            await db.flush()
            db.add(EstateMembership(estate_id=estate.estate_id, user_id=user.user_id,
                property_id=unit.unit_id if index == 1 else None, membership_role=role))
            users.append({'user_id': user.user_id, 'email': user.email})
        await db.commit()
        ids = estate.estate_id, unit.unit_id
    await engine.dispose()
    return ids, users, login_secret


def acceptance():
    guarded_url()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 18002))
    (estate_id, unit_id), users, login_secret = asyncio.run(create_world())
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18002'],
        cwd=BACKEND, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        with httpx.Client(base_url='http://127.0.0.1:18002', timeout=20) as client:
            for _ in range(80):
                if process.poll() is not None:
                    raise RuntimeError('Owned acceptance API exited before readiness.')
                try:
                    if client.get('/health').status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError('Owned acceptance API readiness timed out.')
            sessions = []
            for user in users:
                response = client.post('/api/v1/auth/login', json={'email': user['email'], 'password': login_secret})
                assert response.status_code == 200, 'Synthetic real login failed'
                sessions.append({'Authorization': f"Bearer {response.json()['access_token']}"})

            def call(index, method, path, body=None, status=200):
                result = client.request(method, '/api/v1/property-market' + path,
                    params={'estate_id': estate_id}, json=body, headers=sessions[index])
                assert result.status_code == status, f'{method} {path} returned {result.status_code}, expected {status}'
                return result.json()

            call(1, 'POST', '/requests', {'property_id': unit_id, 'purpose': 'sale', 'requested_price': '1350000'}, status=403)
            call(0, 'POST', '/authorities', {'property_id': unit_id, 'representative_id': users[1]['user_id'],
                'verification_reference': 'Synthetic TCP acceptance mandate'}, status=201)
            request = call(1, 'POST', '/requests', {'property_id': unit_id, 'purpose': 'sale', 'requested_price': '1350000'}, status=201)
            call(0, 'POST', f"/requests/{request['request_id']}/decision", {
                'decision': 'approved', 'agent_id': users[2]['user_id'], 'reason': 'Synthetic consent checked'})
            listing = call(2, 'POST', '/listings', {'request_id': request['request_id'], 'title': 'Fictional TCP apartment',
                'description': 'Synthetic acceptance only.', 'asking_price': '1350000'}, status=201)
            ident = listing['listing_id']
            call(3, 'GET', f'/listings/{ident}', status=404)
            call(2, 'POST', f'/listings/{ident}/actions', {'action': 'publish', 'expected_version': 1, 'reason': 'Approved copy'})
            call(3, 'GET', f'/listings/{ident}')
            call(2, 'PATCH', f'/listings/{ident}/price', {'asking_price': '1400000', 'expected_version': 2, 'reason': 'Revised mandate'})
            call(3, 'GET', f'/listings/{ident}/price-history', status=404)
            assert call(1, 'GET', f'/listings/{ident}/price-history')['total'] == 2
            transaction = call(0, 'POST', f'/listings/{ident}/complete', {'actual_amount': '1380000',
                'effective_date': date.today().isoformat(), 'expected_version': 3,
                'reference': 'Synthetic TCP completed sale'}, status=201)
            assert transaction['actual_amount'] == '1380000'
            assert call(1, 'GET', f"/requests/{request['request_id']}")['status'] == 'fulfilled'
            call(1, 'POST', '/requests', {'property_id': unit_id, 'purpose': 'sale', 'requested_price': '1500000'}, status=403)
            with connect() as connection, connection.cursor() as cursor:
                cursor.execute('SELECT actual_amount, asking_price_at_completion FROM market_transactions WHERE transaction_id=%s AND estate_id=%s',
                               (transaction['transaction_id'], estate_id))
                amounts = cursor.fetchone()
                assert tuple(map(str, amounts)) == ('1380000.00', '1400000.00')
                cursor.execute('SELECT count(*) FROM listing_price_events WHERE estate_id=%s AND listing_id=%s', (estate_id, ident))
                assert cursor.fetchone()[0] == 2
            return {'tcp_http': True, 'real_login': True, 'verified_authority': True,
                    'request_listing_price_sale': True, 'private_history': True,
                    'independent_postgres_rows': True, 'seller_mandate_retired': True}
    finally:
        process.terminate()
        process.wait(timeout=15)


if __name__ == '__main__':
    try:
        print(json.dumps(acceptance(), sort_keys=True))
    except Exception as error:
        print(f'Property market acceptance failed ({type(error).__name__}); sensitive diagnostics withheld.', file=sys.stderr)
        sys.exit(1)
