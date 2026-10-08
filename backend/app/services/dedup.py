"""The dedup job: works out which visits belong to the same household (MOC-16).

The job only ever fills in visits.household_id. Visits are never deleted or
rewritten, so the original records are always there to check against.
"""

from dataclasses import dataclass

from sqlalchemy import exists, select, text
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import get_settings

# Any fixed number works. It names the database lock that stops two runs overlapping.
DEDUP_LOCK_ID = 1_600_016

# Points out of 1000 for each detail a no-phone visit shares with a household.
POINTS_FIRST_INITIAL = 350
POINTS_BIRTH_YEAR = 300
POINTS_BIRTH_MONTH = 200
POINTS_HOUSEHOLD_SIZE = 150
POINTS_HOUSEHOLD_SIZE_OFF_BY_ONE = 75  # families grow and shrink by one


@dataclass(frozen=True)
class Profile:
    """The details a no-phone visitor gives, which are also what a no-phone household is known by."""

    first_initial: str
    birth_month: int
    birth_year: int
    household_size: int


def _profile(record: models.Visit | models.Household) -> Profile:
    return Profile(record.first_initial, record.birth_month, record.birth_year, record.household_size)


def match_score(visit: Profile, household: Profile) -> float:
    """How strongly a no-phone visit matches a household, from 0.0 to 1.0."""
    points = 0
    if visit.first_initial == household.first_initial:
        points += POINTS_FIRST_INITIAL
    if visit.birth_year == household.birth_year:
        points += POINTS_BIRTH_YEAR
    if visit.birth_month == household.birth_month:
        points += POINTS_BIRTH_MONTH
    size_gap = abs(visit.household_size - household.household_size)
    if size_gap == 0:
        points += POINTS_HOUSEHOLD_SIZE
    elif size_gap == 1:
        points += POINTS_HOUSEHOLD_SIZE_OFF_BY_ONE
    # Adding whole points keeps the sum exact, so a score that equals a
    # threshold really does compare as equal.
    return points / 1000


def run_dedup(db: Session) -> schemas.DedupSummary:
    """Give every unprocessed visit a household, or send it to review.

    Safe to run as often as you like: a run with nothing new to process changes nothing.
    """
    settings = get_settings()
    # Held until the commit below. A second run started in the meantime waits
    # here, then finds nothing left to do.
    db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": DEDUP_LOCK_ID})

    summary = schemas.DedupSummary()
    _assign_phone_visits(db, summary)
    _assign_no_phone_visits(db, summary, settings.dedup_merge_threshold, settings.dedup_review_threshold)
    db.commit()
    return summary


def _assign_phone_visits(db: Session, summary: schemas.DedupSummary) -> None:
    """Exact match: every visit with the same phone hash is one household."""
    created = db.execute(
        text(
            """
            INSERT INTO households (phone_hash)
            SELECT DISTINCT phone_hash FROM visits
            WHERE method = 'phone' AND household_id IS NULL
            ON CONFLICT (phone_hash) DO NOTHING
            """
        )
    )
    assigned = db.execute(
        text(
            """
            UPDATE visits SET household_id = households.id
            FROM households
            WHERE visits.method = 'phone'
              AND visits.household_id IS NULL
              AND visits.phone_hash = households.phone_hash
            """
        )
    )
    summary.households_created += created.rowcount
    summary.phone_visits_assigned += assigned.rowcount


def _assign_no_phone_visits(
    db: Session, summary: schemas.DedupSummary, merge_threshold: float, review_threshold: float
) -> None:
    """Scored match: compare each no-phone visit with the no-phone households known so far."""
    known = [
        (household, _profile(household))
        for household in db.scalars(
            select(models.Household)
            .where(models.Household.first_initial.is_not(None))
            .order_by(models.Household.created_at, models.Household.id)
        )
    ]
    already_in_review = exists().where(models.ReviewItem.visit_id == models.Visit.id)
    visits = db.scalars(
        select(models.Visit)
        .where(models.Visit.method == "no_phone", models.Visit.household_id.is_(None), ~already_in_review)
        .order_by(models.Visit.visited_at, models.Visit.id)
    ).all()

    for visit in visits:
        profile = _profile(visit)
        ranked = sorted(
            ((match_score(profile, household_profile), household) for household, household_profile in known),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best = ranked[0] if ranked else (0.0, None)
        tied = len(ranked) > 1 and ranked[1][0] == best_score

        if best is not None and best_score >= merge_threshold and not tied:
            visit.household_id = best.id
            summary.no_phone_visits_merged += 1
        elif best is not None and best_score >= review_threshold:
            # Close but not certain, or equally close to two households: a
            # person decides. The visit stays unassigned until then.
            db.add(models.ReviewItem(visit_id=visit.id, candidate_household_id=best.id, score=best_score))
            summary.sent_to_review += 1
        else:
            household = models.Household(
                first_initial=profile.first_initial,
                birth_month=profile.birth_month,
                birth_year=profile.birth_year,
                household_size=profile.household_size,
            )
            db.add(household)
            db.flush()  # gives the new household its id
            known.append((household, profile))
            visit.household_id = household.id
            summary.households_created += 1
