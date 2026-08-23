"""
Unit Tests — Real-Time Streaming Service
=========================================
Tests in-memory fallback, event bus publishing, and subscriber callback execution.
"""

import sys
from pathlib import Path
import pytest
import asyncio

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.streaming_service import StreamingService, InMemoryFallbackBus


def test_in_memory_fallback_bus():
    async def _run():
        bus = InMemoryFallbackBus()
        received = []

        def on_event(data):
            received.append(data)

        bus.subscribe("test_stream", on_event)
        event_id = await bus.publish("test_stream", {"foo": "bar", "val": 42})

        assert event_id == "1-0"
        assert len(received) == 1
        assert received[0]["foo"] == "bar"
        assert received[0]["val"] == 42

    asyncio.run(_run())


def test_streaming_service_publish_progress():
    async def _run():
        service = StreamingService()
        received_events = []

        def handle_ai_job(data):
            received_events.append(data)

        service.subscribe_in_memory("ai:job:999", handle_ai_job)
        await service.publish_job_progress(job_id=999, status="RUNNING", progress=45.5, stage="GAZE_ESTIMATION")

        assert len(received_events) == 1
        assert received_events[0]["job_id"] == 999
        assert received_events[0]["progress_percent"] == 45.5
        assert received_events[0]["stage"] == "GAZE_ESTIMATION"

    asyncio.run(_run())
