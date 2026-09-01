import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app

routes = [r.path for r in app.routes if "recommendations" in getattr(r, "path", "")]
print("Mounted recommendation routes:")
for route in sorted(routes):
    print(" -", route)

assert "/api/v1/recommendations" in routes
assert "/api/v1/recommendations/jobs/{job_id}" in routes
assert "/api/v1/recommendations/jobs/{job_id}/run" in routes
assert "/api/v1/recommendations/simulate" in routes
print("All routes verified successfully!")
