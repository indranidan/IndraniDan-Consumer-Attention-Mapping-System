"""
Unified Stream Manager
========================
Thread-safe WebSocket stream manager supporting channel multiplexing:
  - ``job:<id>``   — AI pipeline progress, FPS, and log lines
  - ``alerts``     — system-wide alert broadcasts to authenticated clients

Backward-compatible: the existing ``JobStreamManager`` API surface
(connect, disconnect, broadcast, broadcast_sync) still works for
per-job streaming.  New alert methods extend without breaking callers.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Set
# pyrefly: ignore [missing-import]
from fastapi import WebSocket

logger = logging.getLogger("job_stream")


class JobStreamManager:
    """Manages active WebSocket connections for AI jobs and system alerts."""

    def __init__(self):
        # job_id (str) -> Set[WebSocket]  (per-job channels)
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Global alert subscribers: Set[WebSocket]
        self._alert_connections: Set[WebSocket] = set()
        # role -> Set[WebSocket] for targeted role broadcasts
        self._alert_role_map: Dict[str, Set[WebSocket]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store reference to the main asyncio event loop for sync worker thread broadcasts."""
        self._loop = loop

    # ── Per-Job Streaming (backward-compatible) ───────────────

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket client for a specific AI job stream."""
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

    # ── Alert Channel (Module 11) ─────────────────────────────

    async def connect_alert_client(self, websocket: WebSocket, role: str = "all") -> None:
        """Register a WebSocket client for system alert broadcasts."""
        self._alert_connections.add(websocket)
        if role not in self._alert_role_map:
            self._alert_role_map[role] = set()
        self._alert_role_map[role].add(websocket)
        logger.info(f"Alert WebSocket client connected (role={role}). Total: {len(self._alert_connections)}")

    def disconnect_alert_client(self, websocket: WebSocket) -> None:
        """Unregister an alert WebSocket client."""
        self._alert_connections.discard(websocket)
        for role_set in self._alert_role_map.values():
            role_set.discard(websocket)
        logger.info("Alert WebSocket client disconnected")

    async def broadcast_alert(self, message: Dict[str, Any]) -> None:
        """
        Broadcast an alert to all connected alert subscribers.
        If the message contains a target_role, only sends to matching clients.
        """
        target_role = message.get("alert", {}).get("target_role", "all")
        dead: Set[WebSocket] = set()

        # Determine target set
        if target_role == "all":
            targets = list(self._alert_connections)
        else:
            # Send to matching role + any "all"-subscribed clients
            targets = list(
                self._alert_role_map.get(target_role, set())
                | self._alert_role_map.get("all", set())
                | self._alert_role_map.get("admin", set())  # admins see everything
            )

        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self.disconnect_alert_client(ws)

    def broadcast_alert_sync(self, message: Dict[str, Any]) -> None:
        """Thread-safe synchronous bridge to broadcast alert messages."""
        if not self._alert_connections:
            return

        if self._loop is None or not self._loop.is_running():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._loop = loop
            except Exception:
                pass

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_alert(message), self._loop)


# Global singleton
job_stream_manager = JobStreamManager()
