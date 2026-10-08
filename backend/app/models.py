import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Location(Base):
    """A pantry site where visitors check in."""

    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Household(Base):
    """One unique household. Created only by the dedup job."""

    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    # Set for households identified by phone.
    phone_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    # Set for households identified without a phone; copied from their first visit.
    first_initial: Mapped[str | None] = mapped_column(String(1))
    birth_month: Mapped[int | None] = mapped_column(SmallInteger)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    household_size: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Visit(Base):
    """One check-in, stored as it was received.

    There is deliberately no column for a raw phone number, only its HMAC hash.
    The dedup job fills in household_id and changes nothing else.
    """

    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint("method IN ('phone', 'no_phone', 'anonymous')", name="method_valid"),
        CheckConstraint("birth_month BETWEEN 1 AND 12", name="birth_month_range"),
        CheckConstraint("household_size >= 1", name="household_size_positive"),
        CheckConstraint(
            "(method = 'phone' AND phone_hash IS NOT NULL"
            " AND first_initial IS NULL AND birth_month IS NULL AND birth_year IS NULL)"
            " OR (method = 'no_phone' AND phone_hash IS NULL"
            " AND first_initial IS NOT NULL AND birth_month IS NOT NULL"
            " AND birth_year IS NOT NULL AND household_size IS NOT NULL)"
            " OR (method = 'anonymous' AND phone_hash IS NULL"
            " AND first_initial IS NULL AND birth_month IS NULL"
            " AND birth_year IS NULL AND household_size IS NULL)",
            name="identity_matches_method",
        ),
    )

    # Generated on the device, so re-sending a visit can never store it twice.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    method: Mapped[str] = mapped_column(String(16))
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    phone_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    first_initial: Mapped[str | None] = mapped_column(String(1))
    birth_month: Mapped[int | None] = mapped_column(SmallInteger)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    household_size: Mapped[int | None] = mapped_column(SmallInteger)
    language: Mapped[str | None] = mapped_column(String(8))
    household_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("households.id"), index=True)


class ReviewItem(Base):
    """A no-phone visit that might belong to an existing household, waiting for a person to decide."""

    __tablename__ = "review_items"
    __table_args__ = (CheckConstraint("status IN ('pending', 'merged', 'separate')", name="status_valid"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), unique=True)
    candidate_household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id"))
    score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
