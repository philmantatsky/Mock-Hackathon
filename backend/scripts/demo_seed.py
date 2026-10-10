"""Walk through the backend half of the demo (MOC-19) against a running server.

    fastapi dev app/main.py        # in one terminal, from backend/
    python -m scripts.demo_seed    # in another, from backend/

Every run sends new visits from the same made-up people, so total visits grow
while unique households stay the same: returning visitors are recognised.
Set API_URL to point at a server somewhere other than http://localhost:8000.
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")


def call(method: str, path: str, body: Any = None) -> Any:
    headers = {"Content-Type": "application/json"}
    token = get_settings().api_token
    if token is not None:
        headers["Authorization"] = f"Bearer {token.get_secret_value()}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"{method} {path} failed with {error.code}: {error.read().decode()}")
    except urllib.error.URLError as error:
        sys.exit(f"Could not reach {API_URL} ({error.reason}). Is `fastapi dev app/main.py` running?")


def todays_visits() -> list[dict[str, Any]]:
    """Seven check-ins. The phone numbers are fictional (555-01xx)."""
    start = datetime.now(timezone.utc) - timedelta(minutes=30)

    def visit(minutes: int, location_id: str = "loc-1", **details: Any) -> dict[str, Any]:
        visited_at = (start + timedelta(minutes=minutes)).isoformat()
        return {"id": str(uuid.uuid4()), "location_id": location_id, "visited_at": visited_at, **details}

    return [
        visit(0, method="phone", phone="(415) 555-0101", household_size=4, language="es"),
        visit(5, "loc-2", method="phone", phone="+1 415 555 0101"),  # same family, second pantry
        visit(10, method="phone", phone="415-555-0102", household_size=1),
        visit(15, method="no_phone", first_initial="M", birth_month=3, birth_year=1988, household_size=2),
        visit(20, method="no_phone", first_initial="R", birth_month=11, birth_year=1975, household_size=5),
        visit(25, method="no_phone", first_initial="M", birth_month=4, birth_year=1988, household_size=2),  # near match
        visit(30, method="anonymous"),
    ]


def show(title: str, values: dict[str, Any]) -> None:
    print(f"\n{title}")
    for name, value in values.items():
        print(f"  {name:<24}{value}")


def tally(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return counts


def main() -> None:
    call("GET", "/api/health")
    show("Dashboard before", call("GET", "/api/metrics"))

    batch = {"visits": todays_visits()}
    show("Sync 7 offline visits", tally(call("POST", "/api/sync", batch)["results"]))
    show("Sync the same batch again (a retry)", tally(call("POST", "/api/sync", batch)["results"]))
    show("Dashboard after sync, before dedup", call("GET", "/api/metrics"))

    show("Run dedup", call("POST", "/api/dedup/run"))
    show("Dashboard after dedup", call("GET", "/api/metrics"))

    reviews = call("GET", "/api/reviews")
    print(f"\nWaiting for review: {len(reviews)}")
    for review in reviews:
        seen, known = review["visit"], review["candidate_household"]
        print(
            f"  score {review['score']:.2f}: visit {seen['first_initial']} {seen['birth_month']}/{seen['birth_year']}"
            f" size {seen['household_size']}  vs  household {known['first_initial']}"
            f" {known['birth_month']}/{known['birth_year']} size {known['household_size']}"
        )


if __name__ == "__main__":
    main()
