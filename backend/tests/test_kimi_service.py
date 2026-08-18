import asyncio
from app.kimi.services.kimi_service import init_run, schedule_run, get_status, get_logs


def test_kimi_run_loop():
    run_id = "test_run_1"
    init_run(run_id, {"address": "123 Main St", "phone": "+1234567890"})
    schedule_run(run_id)
    # wait for background tasks to run
    async def wait_for_completion():
        for _ in range(20):
            status = get_status(run_id)
            if status and status["status"] == "completed":
                return True
            await asyncio.sleep(0.1)
        return False

    loop = asyncio.get_event_loop()
    completed = loop.run_until_complete(wait_for_completion())
    assert completed, "Kimi run did not complete in time"
    logs = get_logs(run_id)
    assert any("Lead created" in l["message"] for l in logs), "Lead creation log missing"
