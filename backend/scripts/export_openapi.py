"""Write the API contract to openapi.json at the repo root.

Run from backend/ after changing any endpoint or schema, and commit the result:

    python -m scripts.export_openapi

The frontend generates its types from that file (npm run gen:api).
"""

import json

from app.config import BACKEND_DIR
from app.main import app

SPEC_PATH = BACKEND_DIR.parent / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2) + "\n"


if __name__ == "__main__":
    SPEC_PATH.write_text(render())
    print(f"Wrote {SPEC_PATH}")
