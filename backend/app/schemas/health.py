"""
Deep Health Probe Response Schemas
===================================
Pydantic models for the `/api/health/deep` endpoint, providing
structured component-level health diagnostics for PostgreSQL,
MongoDB, Redis, and storage subsystems.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ComponentHealth(BaseModel):
    """Health status for a single subsystem component."""
    status: str = Field(..., description="Component status: healthy, degraded, or unavailable")
    latency_ms: Optional[float] = Field(None, description="Probe round-trip latency in milliseconds")
    details: Optional[str] = Field(None, description="Additional diagnostic information")


class DeepHealthResponse(BaseModel):
    """Structured deep health probe response."""
    overall_status: str = Field(..., description="Overall system status: healthy, degraded, or critical")
    components: dict[str, ComponentHealth] = Field(
        ..., description="Per-component health diagnostics"
    )
    modules_loaded: int = Field(..., description="Number of registered application modules")
    version: str = Field(..., description="Application version identifier")
