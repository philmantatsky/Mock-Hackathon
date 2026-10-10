from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import PROTECTED
from app.db import get_db

router = APIRouter(prefix="/api", tags=["locations"], **PROTECTED)


@router.get("/locations", response_model=list[schemas.Location], summary="List pantry locations")
def list_locations(db: Session = Depends(get_db)) -> list[models.Location]:
    """All active pantry locations, by name."""
    query = select(models.Location).where(models.Location.active).order_by(models.Location.name)
    return list(db.scalars(query))
