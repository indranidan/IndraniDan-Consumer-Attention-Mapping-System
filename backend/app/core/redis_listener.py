"""
Hybrid Event Bus & Redis Listener
==================================
Provides:
* ``dispatch_job_event`` – transport-agnostic event dispatcher that publishes
  via Redis Pub/Sub when available, or falls back to an in-process asyncio
  task executor when Redis is unreachable.
* ``redis_event_listener_task`` – long-running background coroutine that
  subscribes to Redis Pub/Sub and processes incoming job events.
* ``_process_job`` – concurrently runs M4, M5, M6, M8, M9 in background threads.
"""

import asyncio
import json
import logging
from typing import Optional
import uuid

from app.core.redis_client import get_redis_client, is_redis_available
from app.database.database import SessionLocal

logger = logging.getLogger("event_bus")

# ── Captured event loop reference (set during lifespan startup) ─────────
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store the main asyncio event loop for thread-safe scheduling."""
    global _event_loop
    _event_loop = loop


# ── Core processing logic ──────────────────────────────────────────────

async def _process_job(job_id: str):
    """
    Run M4, M5, M6, M8 concurrently in background threads
    to avoid blocking the asyncio event loop.
    """
    from app.services.attention_service import get_or_run_module4_analysis
    from app.services.interaction_service import get_or_run_module5_analysis
    from app.services.behavior_service import run_module6_analysis
    from app.services.scoring_service import get_or_run_module8_analysis
    from app.services.recommendation_service import run_module9_analysis

    job_uuid = uuid.UUID(job_id)
    loop = asyncio.get_running_loop()

    def run_m4():
        with SessionLocal() as db:
            get_or_run_module4_analysis(db, job_uuid, force_rerun=True)

    def run_m5():
        with SessionLocal() as db:
            get_or_run_module5_analysis(db, job_uuid, force_rerun=True)

    def run_m6():
        with SessionLocal() as db:
            run_module6_analysis(job_id=job_uuid, db=db, force_recompute=True)

    def run_m8():
        with SessionLocal() as db:
            get_or_run_module8_analysis(db, job_uuid, force_rerun=True)

    def run_m9():
        with SessionLocal() as db:
            run_module9_analysis(db, job_uuid, force_rerun=True)

    logger.info(f"Starting async processing for job {job_id}")

    results = await asyncio.gather(
        loop.run_in_executor(None, run_m4),
        loop.run_in_executor(None, run_m5),
        loop.run_in_executor(None, run_m6),
        loop.run_in_executor(None, run_m8),
        loop.run_in_executor(None, run_m9),
        return_exceptions=True,
    )

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            module_names = ["M4 (Attention)", "M5 (Interaction)", "M6 (Behavior)", "M8 (Scoring)", "M9 (Recommendations)"]
            logger.warning(f"{module_names[idx]} failed for job {job_id}: {result}")

    logger.info(f"Finished async processing for job {job_id}")


# ── Hybrid Event Dispatcher ───────────────────────────────────────────

def dispatch_job_event(event: str, job_id: str) -> None:
    """
    Publish a job event through the best available transport.

    1. If Redis is reachable → publish to ``ai_job_events`` channel.
    2. Otherwise → schedule ``_process_job`` on the captured asyncio event
       loop using ``run_coroutine_threadsafe`` (safe from worker threads).

    This function is called from the background AI worker thread, NOT from
    an asyncio context, so we must use thread-safe scheduling.
    """
    payload = json.dumps({"event": event, "job_id": job_id})

    # Attempt Redis first
    client = get_redis_client()
    if client is not None:
        try:
            client.publish("ai_job_events", payload)
            logger.info(f"Published {event} via Redis for job {job_id}")
            return
        except Exception as exc:
            logger.warning(f"Redis publish failed ({exc}), falling back to in-process dispatch")

    # Fallback: schedule directly on the FastAPI event loop
    if _event_loop is not None and _event_loop.is_running():
        asyncio.run_coroutine_threadsafe(_process_job(job_id), _event_loop)
        logger.info(f"Dispatched {event} via in-process fallback for job {job_id}")
    else:
        logger.error(
            f"Cannot dispatch {event} for job {job_id}: "
            "Redis unavailable and no event loop captured."
        )


# ── Redis Pub/Sub Listener ────────────────────────────────────────────

async def redis_event_listener_task():
    """Background task to listen to Redis Pub/Sub."""
    client = get_redis_client()
    if not client:
        logger.warning("Redis client not available at listener start. Event listener disabled.")
        return

    pubsub = client.pubsub()
    pubsub.subscribe("ai_job_events")
    logger.info("Subscribed to Redis ai_job_events")

    while True:
        try:
            message = await asyncio.get_running_loop().run_in_executor(
                None, pubsub.get_message, True, 1.0
            )
            if message and message.get("type") == "message":
                data = json.loads(message.get("data"))
                if data.get("event") == "JOB_PROCESSED":
                    job_id = data.get("job_id")
                    if job_id:
                        asyncio.create_task(_process_job(job_id))

            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")
            await asyncio.sleep(5)


# ── Lifecycle helpers ─────────────────────────────────────────────────

_listener_task: Optional[asyncio.Task] = None


def start_redis_listener():
    """Start the background Redis subscriber (no-op if Redis is down)."""
    global _listener_task
    _listener_task = asyncio.create_task(redis_event_listener_task())


def stop_redis_listener():
    """Cancel the background Redis subscriber."""
    global _listener_task
    if _listener_task:
        _listener_task.cancel()
