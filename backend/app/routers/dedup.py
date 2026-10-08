from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import PROTECTED
from app.db import get_db
from app.services.dedup import run_dedup

router = APIRouter(prefix="/api", tags=["dedup"], **PROTECTED)


@router.post("/dedup/run", response_model=schemas.DedupSummary, summary="Run the dedup job")
def run_dedup_job(db: Session = Depends(get_db)) -> schemas.DedupSummary:
    """Assign visits that have no household yet, and report what was done.

    Phone visits with the same number share a household. No-phone visits are
    scored against known households: a strong match joins, a near match waits
    in the review list, anything else becomes a new household. Anonymous visits
    are left alone. Visits themselves are never changed or deleted.
    """
    return run_dedup(db)


@router.get("/reviews", response_model=list[schemas.ReviewItem], summary="List matches waiting for review")
def list_reviews(db: Session = Depends(get_db)) -> list[schemas.ReviewItem]:
    """No-phone visits that might belong to an existing household, oldest first."""
    query = (
        select(models.ReviewItem, models.Visit, models.Household)
        .join(models.Visit, models.ReviewItem.visit_id == models.Visit.id)
        .join(models.Household, models.ReviewItem.candidate_household_id == models.Household.id)
        .where(models.ReviewItem.status == "pending")
        .order_by(models.ReviewItem.created_at, models.ReviewItem.id)
    )
    return [
        schemas.ReviewItem(
            id=item.id,
            score=item.score,
            created_at=item.created_at,
            visit=schemas.ReviewVisit.model_validate(visit),
            candidate_household=schemas.ReviewHousehold.model_validate(household),
        )
        for item, visit, household in db.execute(query)
    ]
