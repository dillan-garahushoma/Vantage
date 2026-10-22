"""Real TCP management acceptance on synthetic rows in the migration-test DB.

No truncation, no customer data, no credentials or response bodies printed.
Optionally runs a real browser against a separate Vite instance.
"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import httpx
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


async def create_world(password):
    from app.core.security import hash_password
    import app.db.database  # noqa: F401
    from app.identity.models.user import User
    from app.identity.models.estate_membership import EstateMembership
    from app.property.models.estate import Estate
    from app.property.models.property import Property
    from app.providers.models.service_provider import ServiceProvider

    engine = create_async_engine(os.environ['DATABASE_URL'])
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            suffix = secrets.token_hex(6)
            estate = Estate(name=f'Fictional Musgrave Management {suffix}', suburb='Musgrave',
                city='Durban', province='KwaZulu-Natal', is_demo=True)
            db.add(estate)
            await db.flush()
            unit = Property(estate_id=estate.estate_id, unit_no='01', complex_name=estate.name,
                street_address='1 Fictional Ridge Road', suburb='Musgrave', size_m2=85, bedrooms=2, bathrooms=1)
            db.add(unit)
            digest = hash_password(password)
            users = [User(full_name=f'Acceptance {role}', email=f'{role}-{suffix}@example.com',
                role=role, password_hash=digest) for role in ('hoa_admin', 'resident', 'service_provider')]
            db.add_all(users)
            await db.flush()
            for user in users:
                db.add(EstateMembership(estate_id=estate.estate_id, user_id=user.user_id,
                    property_id=unit.unit_id if user.role == 'resident' else None, membership_role=user.role))
            provider = ServiceProvider(user_id=users[2].user_id, full_name='Fictional local plumber',
                email=users[2].email, trade='plumber', phone='0821110001', verified=True)
            db.add(provider)
            await db.commit()
            return estate.estate_id, unit.unit_id, provider.provider_id, [u.email for u in users]
    finally:
        await engine.dispose()


def ready(process, url):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('Acceptance service exited before readiness.')
        try:
            if httpx.get(url, timeout=1).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(.2)
    raise RuntimeError('Acceptance service readiness timed out.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', help='Optional Node executable for real browser acceptance')
    args = parser.parse_args()
    url = make_url(os.environ['DATABASE_URL'])
    if (url.host, url.port, url.database) != ('127.0.0.1', 54329, 'valora_migration_test'):
        raise RuntimeError('Refusing any database except the dedicated loopback migration-test database.')
    secret = secrets.token_urlsafe(24)
    estate, unit, provider, emails = asyncio.run(create_world(secret))
    api_port, ui_port = free_port(), free_port()
    api_url, ui_url = f'http://127.0.0.1:{api_port}', f'http://127.0.0.1:{ui_port}'
    environment = os.environ.copy()
    environment['CORS_ORIGINS'] = json.dumps([ui_url])
    environment['EMAIL_ENABLED'] = 'false'
    environment['ENABLE_LEGACY_ROUTES'] = 'true'
    processes = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
            '--port', str(api_port)], cwd=BACKEND, env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        processes.append(api)
        ready(api, api_url + '/health')
        with httpx.Client(base_url=api_url, timeout=20) as client:
            headers = []
            for email in emails:
                result = client.post('/api/v1/auth/login', json={'email': email, 'password': secret})
                assert result.status_code == 200, 'Real login failed'
                headers.append({'Authorization': 'Bearer ' + result.json()['access_token']})
            admin, resident, contractor = headers

            def call(method, path, actor=admin, body=None, expected=200):
                result = client.request(method, '/api/v1' + path, params={'estate_id': estate},
                    headers=actor, json=body)
                assert result.status_code == expected, f'{method} {path} returned {result.status_code}'
                return result.json() if result.content else None

            for path in ('/investment-scenarios', '/property-market/listings', '/listings', '/sales'):
                call('GET', path, expected=404)
            complaint = call('POST', '/complaints', resident, {'unit_id': unit, 'category': 'water',
                'description': 'Fictional leaking kitchen tap', 'priority': 'urgent'}, 201)
            complaint_id = complaint['id']
            call('PATCH', f'/complaints/{complaint_id}/status', admin, {'status': 'reviewed'})
            work = call('POST', '/work-orders', admin, {'complaint_id': complaint_id, 'provider_id': provider,
                'estimated_completion_date': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}, 201)
            work_id = work['id']
            brief = call('POST', '/analytics/intelligence/briefing/generate', expected=201)
            assert brief['recommendations'], 'Overdue maintenance priority missing'
            call('PATCH', f'/work-orders/{work_id}', contractor, {'status': 'in_progress'})
            call('PATCH', f'/work-orders/{work_id}', contractor, {'status': 'completed',
                'completion_notes': 'Synthetic repair completed and checked', 'job_cost': '650.00'})
            call('POST', f'/work-orders/{work_id}/rating', resident, {'rating': 5})
            call('PATCH', f'/work-orders/{work_id}', contractor, {'job_cost': '1.00'}, 409)
            score = call('POST', '/analytics/living-score/recalculate', expected=201)
            assert score['estate_id'] == estate
            assert call('GET', '/notifications', resident)['total'] >= 2
            call('POST', f'/complaints/{complaint_id}/reopen', resident, {'note': 'Fictional leak recurred after repair'})
            call('PATCH', f'/complaints/{complaint_id}/status', admin, {'status': 'reviewed'})
            second = call('POST', '/work-orders', admin, {'complaint_id': complaint_id, 'provider_id': provider}, 201)
            assert second['id'] != work_id, 'Repeat repair replaced original work order'
            assert len(call('GET', f'/complaints/{complaint_id}/events', resident)) >= 7
            assert call('GET', f"/analytics/intelligence/history/{brief['briefing_id']}") == brief
            assert call('GET', '/analytics/intelligence', resident)['recommendations'] == []
        if args.node:
            environment['VITE_API_BASE_URL'] = api_url
            frontend = BACKEND.parent / 'frontend'
            vite = subprocess.Popen([args.node, str(frontend / 'node_modules/vite/bin/vite.js'), '--host',
                '127.0.0.1', '--port', str(ui_port), '--strictPort'], cwd=frontend, env=environment,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
            processes.append(vite)
            ready(vite, ui_url)
            environment.update(VALORA_ACCEPTANCE_UI=ui_url, VALORA_ACCEPTANCE_EMAIL=emails[1],
                               VALORA_ACCEPTANCE_PASSWORD=secret)
            browser = subprocess.run([args.node, str(BACKEND / 'scripts/accept_management_browser.mjs')],
                cwd=frontend, env=environment, capture_output=True, creationflags=flags)
            if browser.returncode:
                # Emit only our closed diagnostic enum, never raw browser output.
                try:
                    stage = json.loads(browser.stdout).get('failed_stage')
                except (ValueError, AttributeError):
                    stage = 'browser-startup'
                allowed = {'create-page', 'login-page', 'submit-login', 'signed-in-navigation', 'complaint-record', 'browser-startup'}
                raise RuntimeError('Live browser acceptance failed at ' + (stage if stage in allowed else 'unknown') + '.')
        print(json.dumps({'tcp_http': True, 'real_role_logins': 3, 'retired_routes': True,
            'complaint_repair_rating_reopen': True, 'repeat_repair_preserves_history': True,
            'living_score': True, 'maintenance_intelligence': True, 'notifications': True,
            'real_browser_signin_and_complaints': bool(args.node)}))
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
