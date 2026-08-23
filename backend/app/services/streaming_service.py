"""
Real-Time Streaming Service & Redis Event Bus
=============================================
Provides asynchronous Redis Streams message publishing and pub/sub channels
with automatic zero-config in-memory fallback for local development.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("streaming_service")


class InMemoryFallbackBus:
    """Lightweight in-memory queue & pub-sub fallback when Redis is unreachable."""

    def __init__(self):
        self._streams: Dict[str, List[Dict[str, Any]]] = {}
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}

    async def publish(self, stream_name: str, event_data: Dict[str, Any]) -> str:
        if stream_name not in self._streams:
            self._streams[stream_name] = []
        event_id = f"{len(self._streams[stream_name]) + 1}-0"
        self._streams[stream_name].append({"id": event_id, "data": event_data})

        # Notify in-memory subscribers
        if stream_name in self._subscribers:
            for sub in self._subscribers[stream_name]:
                try:
                    if inspect.iscoroutinefunction(sub):
                        asyncio.create_task(sub(event_data))
                    else:
                        sub(event_data)
                except Exception as e:
                    logger.debug(f"In-memory sub error: {e}")
        return event_id

    def subscribe(self, stream_name: str, callback: Callable[[Dict[str, Any]], Any]) -> None:
        if stream_name not in self._subscribers:
            self._subscribers[stream_name] = []
        self._subscribers[stream_name].append(callback)


class StreamingService:
    """Enterprise streaming event bus for video frames and AI job events."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client = None
        self._is_connected = False
        self._fallback_bus = InMemoryFallbackBus()

    async def connect(self) -> bool:
        """Attempt connection to Redis server."""
        try:
            import redis.asyncio as aioredis
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=1.5,
            )
            await self.redis_client.ping()
            self._is_connected = True
            logger.info(f"Connected to Redis streaming bus at {self.redis_url}")
            return True
        except Exception as e:
            logger.info(f"Redis not available ({e}). Using resilient In-Memory Event Bus.")
            self._is_connected = False
            return False

    async def publish_event(self, stream: str, data: Dict[str, Any]) -> str:
        """
        Publish an event payload to a stream or pub-sub channel.
        """
        if self._is_connected and self.redis_client:
            try:
                # Serialize payload dict
                payload = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()}
                event_id = await self.redis_client.xadd(stream, payload)
                # Also publish to PubSub channel for instant WebSocket forwarding
                await self.redis_client.publish(f"channel:{stream}", json.dumps(data))
                return str(event_id)
            except Exception as e:
                logger.warning(f"Redis publish failed, falling back to memory queue: {e}")

        return await self._fallback_bus.publish(stream, data)

    async def publish_job_progress(self, job_id: int, status: str, progress: float, stage: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Publish real-time AI job progress telemetry."""
        event = {
            "job_id": job_id,
            "status": status,
            "progress_percent": round(progress, 1),
            "stage": stage,
            "metrics": metrics or {},
        }
        await self.publish_event(f"ai:job:{job_id}", event)

    def subscribe_in_memory(self, stream: str, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """Register an in-memory listener for event bus messages."""
        self._fallback_bus.subscribe(stream, callback)

    async def close(self) -> None:
        """Close connection cleanly."""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception:
                pass


# Global singleton instance
streaming_service = StreamingService()
