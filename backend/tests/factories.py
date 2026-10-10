"""Builders for the JSON a device sends to /api/sync."""

import uuid
from datetime import datetime, timezone
from typing import Any


def _visit(**fields: Any) -> dict[str, Any]:
    """Common fields plus the given ones. A test can override any field, even the method."""
    visit = {
        "id": str(uuid.uuid4()),
        "location_id": "loc-1",
        "visited_at": datetime.now(timezone.utc).isoformat(),
    }
    visit.update(fields)
    return visit


def phone_visit(phone: str = "555-123-4567", **fields: Any) -> dict[str, Any]:
    return _visit(**{"method": "phone", "phone": phone, **fields})


def no_phone_visit(
    first_initial: str = "M", birth_month: int = 3, birth_year: int = 1988, household_size: int = 2, **fields: Any
) -> dict[str, Any]:
    return _visit(
        **{
            "method": "no_phone",
            "first_initial": first_initial,
            "birth_month": birth_month,
            "birth_year": birth_year,
            "household_size": household_size,
            **fields,
        }
    )


def anonymous_visit(**fields: Any) -> dict[str, Any]:
    return _visit(**{"method": "anonymous", **fields})


def sync(client, *visits: dict[str, Any]) -> list[dict[str, Any]]:
    """Send visits to /api/sync and return the per-visit results."""
    response = client.post("/api/sync", json={"visits": list(visits)})
    assert response.status_code == 200, response.text
    return response.json()["results"]
