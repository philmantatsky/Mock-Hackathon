import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import PROTECTED
from app.db import get_db
from app.security import hash_phone

router = APIRouter(prefix="/api", tags=["sync"], **PROTECTED)


def _to_row(visit: schemas.PhoneVisit | schemas.NoPhoneVisit | schemas.AnonymousVisit) -> dict[str, Any]:
    """Build the database row for a visit.

    This is the only place a raw phone number is read, and only its hash leaves.
    """
    row: dict[str, Any] = {
        "id": visit.id,
        "location_id": visit.location_id,
        "method": visit.method,
        "visited_at": visit.visited_at,
        "language": visit.language,
        "phone_hash": None,
        "first_initial": None,
        "birth_month": None,
        "birth_year": None,
        "household_size": None,
    }
    if isinstance(visit, schemas.PhoneVisit):
        row["phone_hash"] = hash_phone(visit.phone.get_secret_value())
        row["household_size"] = visit.household_size
    elif isinstance(visit, schemas.NoPhoneVisit):
        row["first_initial"] = visit.first_initial
        row["birth_month"] = visit.birth_month
        row["birth_year"] = visit.birth_year
        row["household_size"] = visit.household_size
    return row


@router.post("/sync", response_model=schemas.SyncResponse, summary="Upload visits recorded offline")
def sync_visits(payload: schemas.SyncRequest, db: Session = Depends(get_db)) -> schemas.SyncResponse:
    """Store a batch of visits.

    Idempotent: each visit carries a UUID generated on the device. Re-sending a
    visit that is already stored returns `duplicate` instead of creating it
    again, so the client can safely retry after a dropped connection.

    A visit that fails validation comes back as `rejected` with the reason in
    `error`; the other visits in the batch are still stored.
    """
    known_locations = set(db.scalars(select(models.Location.id)))

    rows: dict[uuid.UUID, dict[str, Any]] = {}  # first copy of each id wins
    rejected: dict[int, str] = {}  # position in the request -> reason
    for position, visit in enumerate(payload.visits):
        if isinstance(visit, schemas.RejectedVisit):
            rejected[position] = visit.error
        elif visit.location_id not in known_locations:
            rejected[position] = "location_id: unknown location"
        elif visit.id not in rows:
            rows[visit.id] = _to_row(visit)

    created: set[uuid.UUID] = set()
    if rows:
        # ON CONFLICT DO NOTHING skips ids that are already stored, and
        # RETURNING lists only the rows that really were inserted.
        statement = (
            insert(models.Visit)
            .values(list(rows.values()))
            .on_conflict_do_nothing(index_elements=[models.Visit.id])
            .returning(models.Visit.id)
        )
        created = set(db.scalars(statement))
        db.commit()

    results = []
    for position, visit in enumerate(payload.visits):
        if position in rejected:
            results.append(schemas.SyncResult(id=visit.id, status="rejected", error=rejected[position]))
        elif visit.id in created:
            created.discard(visit.id)  # a second copy in the same request counts as a duplicate
            results.append(schemas.SyncResult(id=visit.id, status="created"))
        else:
            results.append(schemas.SyncResult(id=visit.id, status="duplicate"))
    return schemas.SyncResponse(results=results)
