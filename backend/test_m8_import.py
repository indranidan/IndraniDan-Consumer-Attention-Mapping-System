"""Quick smoke test that FastAPI app loads with Module 8 router."""
import sys
sys.path.insert(0, ".")
from app.main import app

routes = [r.path for r in app.routes]
scoring_routes = [r for r in routes if "/scoring" in r]
print(f"Total routes: {len(routes)}")
print(f"Module 8 scoring routes: {scoring_routes}")
assert len(scoring_routes) >= 4, f"Expected at least 4 scoring routes, got {len(scoring_routes)}"
print("Router registration OK")
