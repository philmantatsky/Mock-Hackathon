from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import schemas
from app.config import get_settings
from app.db import get_db
from app.errors import validation_error_without_inputs
from app.routers import locations, visits

app = FastAPI(
    title="Pantry Sign-In API",
    version="0.1.0",
    description=(
        "Check-in API for pantry sites. The backend owns this contract; "
        "`openapi.json` at the repo root is generated from this app.\n\n"
        "Privacy: a visitor is identified only by a phone number (stored as an HMAC hash, "
        "never the number itself) or, without a phone, by first initial, birth month/year "
        "and household size. Never add name or email fields."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(RequestValidationError, validation_error_without_inputs)
app.include_router(locations.router)
app.include_router(visits.router)


@app.get("/api/health", response_model=schemas.Health, summary="Health check", tags=["health"])
def health(db: Session = Depends(get_db)) -> schemas.Health:
    db.execute(text("SELECT 1"))
    return schemas.Health()
