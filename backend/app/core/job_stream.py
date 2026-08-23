"""
Real-Time Job Stream Manager
============================
Thread-safe WebSocket stream manager for broadcasting live AI pipeline
execution metrics, progress percentages, FPS, and log lines to connected clients.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Set
# pyrefly: ignore [missing-import]
from fastapi import WebSocket

logger = logging.getLogger("job_stream")


class JobStreamManager:
    """Manages active WebSocket connections subscribed to AI jobs."""

    def __init__(self):
        # job_id (str) -> Set[WebSocket]
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store reference to the main asyncio event loop for sync worker thread broadcasts."""
        self._loop = loop

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """Accept and register a new client connection."""
        await websocket.accept()
        if job_id not in self._connections:
            self._connections[job_id] = set()
        self._connections[job_id].add(websocket)
        logger.info(f"WebSocket client connected to job {job_id}. Total: {len(self._connections[job_id])}")

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        """Unregister a disconnected client."""
        if job_id in self._connections:
            self._connections[job_id].discard(websocket)
            if not self._connections[job_id]:
                del self._connections[job_id]
        logger.info(f"WebSocket client disconnected from job {job_id}")

    async def broadcast(self, job_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a message asynchronously to all clients subscribed to job_id."""
        if job_id not in self._connections:
            return

        dead_connections: Set[WebSocket] = set()
        for ws in list(self._connections[job_id]):
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.debug(f"Failed to send to client ({exc}). Removing dead connection.")
                dead_connections.add(ws)

        for dead_ws in dead_connections:
            self.disconnect(job_id, dead_ws)

    def broadcast_sync(self, job_id: str, message: Dict[str, Any]) -> None:
        """
        Thread-safe synchronous bridge for background worker threads to broadcast messages.
        """
        if job_id not in self._connections:
            return

        if self._loop is None or not self._loop.is_running():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._loop = loop
            except Exception:
                pass

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(job_id, message), self._loop)


# Global singleton
job_stream_manager = JobStreamManager()
