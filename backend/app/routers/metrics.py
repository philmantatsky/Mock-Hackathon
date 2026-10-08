from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import PROTECTED
from app.db import get_db

router = APIRouter(prefix="/api", tags=["metrics"], **PROTECTED)


@router.get("/metrics", response_model=schemas.Metrics, summary="Dashboard counts")
def get_metrics(db: Session = Depends(get_db)) -> schemas.Metrics:
    """Counts for the coalition dashboard (MOC-17).

    Households only exist once the dedup job has run, so `unique_households`
    and `pending_review` change when it does. Anonymous visits and visits
    waiting for review count as visits but not as households.
    """
    visit = models.Visit
    review = models.ReviewItem
    # A visit has at most one review item, so the join never repeats a visit.
    query = (
        select(
            func.count(visit.household_id.distinct()).label("unique_households"),
            func.count().label("total_visits"),
            func.count().filter(review.status == "pending").label("pending_review"),
            func.count().filter(visit.method == "anonymous").label("anonymous_visits"),
            func.count()
            .filter(visit.method != "anonymous", visit.household_id.is_(None), review.id.is_(None))
            .label("unprocessed_visits"),
        )
        .select_from(visit)
        .outerjoin(review, review.visit_id == visit.id)
    )
    return schemas.Metrics.model_validate(db.execute(query).one())
