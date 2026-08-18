import asyncio
import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

_runs: Dict[str, Dict[str, Any]] = {}
_config: Dict[str, Any] = {"mock_mode": True, "mapbox_key": None, "whatsapp_key": None}


def init_run(run_id: str, input_data: Dict[str, Any]):
    _runs[run_id] = {"status": "pending", "progress": 0, "input": input_data, "logs": []}


def append_log(run_id: str, message: str):
    entry = {"message": message, "ts": time.time()}
    _runs[run_id]["logs"].append(entry)


def get_status(run_id: str):
    r = _runs.get(run_id)
    if not r:
        return None
    return {"run_id": run_id, "status": r["status"], "progress": r["progress"], "logs": r["logs"]}


def get_logs(run_id: str):
    r = _runs.get(run_id)
    if not r:
        return None
    return r["logs"]


def set_config(cfg: Dict[str, Any]):
    _config.update(cfg)


def get_config():
    return _config


async def _simulate_coverage_lookup(address: str):
    await asyncio.sleep(0.25)
    # rudimentary heuristic: addresses containing "Main" are covered
    if "main" in address.lower():
        return {"coverage": "covered", "lat": 51.0, "lon": -0.12}
    if len(address.strip()) == 0:
        return {"coverage": "unknown"}
    return {"coverage": "near_coverage"}


async def _simulate_send_whatsapp(phone: str, message: str):
    await asyncio.sleep(0.1)
    return {"sent": True, "to": phone}


async def run_agent_background(run_id: str):
    try:
        run = _runs.get(run_id)
        if not run:
            return
        run["status"] = "running"
        append_log(run_id, "Kimi agent started")

        append_log(run_id, f"Starting coverage lookup for '{run['input'].get('address', '')}'")
        cov = await _simulate_coverage_lookup(run["input"].get("address", ""))
        append_log(run_id, f"Coverage lookup result: {cov}")
        run["progress"] = 30

        append_log(run_id, "Creating lead record")
        await asyncio.sleep(0.1)
        lead_id = f"lead_{int(time.time())}"
        run["lead_id"] = lead_id
        append_log(run_id, f"Lead created: {lead_id}")
        run["progress"] = 60

        append_log(run_id, "Sending WhatsApp message to lead")
        whatsapp_res = await _simulate_send_whatsapp(run["input"].get("phone", ""), "Thanks for your interest — a rep will follow up.")
        append_log(run_id, f"WhatsApp result: {whatsapp_res}")
        run["progress"] = 100

        run["status"] = "completed"
        append_log(run_id, "Kimi agent run completed")
    except Exception as e:
        run = _runs.get(run_id)
        if run:
            run["status"] = "failed"
            append_log(run_id, f"Agent failed: {e}")
        logger.exception("Kimi run failed")


# synchronous scheduler used by FastAPI BackgroundTasks
def schedule_run(run_id: str):
    # schedule the async background job on the running event loop
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_agent_background(run_id))
    except RuntimeError:
        # no running loop — fire and forget
        asyncio.create_task(run_agent_background(run_id))
