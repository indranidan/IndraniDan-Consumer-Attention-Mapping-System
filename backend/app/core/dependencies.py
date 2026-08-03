"""
Convenience Role Dependencies
===============================
Pre-configured dependency instances for common role combinations.
Import these directly in route handlers for clean, readable access control.

Usage:
    from app.core.dependencies import admin_only

    @router.get("/admin", dependencies=[Depends(admin_only)])
    def admin_route():
        ...
"""

from app.middleware.jwt_auth import require_roles

# ── Single Role Dependencies ─────────────────────────────────
admin_only = require_roles("Administrator")
store_manager_only = require_roles("Store Manager")
retail_analyst_only = require_roles("Retail Analyst")
marketing_manager_only = require_roles("Marketing Manager")

# ── Combined Role Dependencies ───────────────────────────────
admin_or_store_manager = require_roles("Administrator", "Store Manager")
admin_or_analyst = require_roles("Administrator", "Retail Analyst")
admin_or_marketing = require_roles("Administrator", "Marketing Manager")

# ── All roles (any authenticated user with a valid role) ─────
any_role = require_roles(
    "Administrator",
    "Store Manager",
    "Retail Analyst",
    "Marketing Manager",
)
