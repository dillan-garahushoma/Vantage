from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)

def test_kimi_e2e_flow():
    # start a run
    resp = client.post('/api/v1/kimi/start', json={"address": "123 Main St", "phone": "+123456789"})
    assert resp.status_code == 200
    data = resp.json()
    run_id = data.get('run_id')
    assert run_id

    # poll status until completed
    for _ in range(50):
        resp = client.get(f'/api/v1/kimi/status/{run_id}')
        assert resp.status_code == 200
        status = resp.json()
        if status.get('status') == 'completed':
            break
        time.sleep(0.1)
    else:
        assert False, 'Kimi run did not complete in time'

    resp = client.get(f'/api/v1/kimi/logs/{run_id}')
    assert resp.status_code == 200
    logs = resp.json().get('logs', [])
    assert any('Lead created' in entry.get('message', '') for entry in logs), 'Lead creation not found in logs'
