"""MOC-16: dedup job assigns visits to household IDs."""

import pytest
from sqlalchemy import text

from app import models
from app.config import get_settings
from app.services.dedup import Profile, match_score
from tests.factories import anonymous_visit, no_phone_visit, phone_visit, sync

NOTHING_TO_DO = {"phone_visits_assigned": 0, "no_phone_visits_merged": 0, "households_created": 0, "sent_to_review": 0}


def run_dedup(client):
    response = client.post("/api/dedup/run")
    assert response.status_code == 200, response.text
    return response.json()


def household_of(db, visit):
    return db.scalar(text("SELECT household_id FROM visits WHERE id = :id"), {"id": visit["id"]})


def count(db, table):
    return db.scalar(text(f"SELECT count(*) FROM {table}"))


# --- Scoring ------------------------------------------------------------------

KNOWN = Profile(first_initial="M", birth_month=3, birth_year=1988, household_size=2)


@pytest.mark.parametrize(
    "visit, expected, outcome",
    [
        (Profile("M", 3, 1988, 2), 1.0, "everything matches: merge"),
        (Profile("M", 3, 1988, 3), 0.925, "household size off by one: merge"),
        (Profile("M", 3, 1988, 5), 0.85, "household size off by more: review"),
        (Profile("M", 4, 1988, 2), 0.8, "birth month differs: review"),
        (Profile("M", 3, 1989, 2), 0.7, "birth year differs: review"),
        (Profile("J", 3, 1988, 2), 0.65, "initial differs: new household"),
        (Profile("J", 7, 1970, 6), 0.0, "nothing matches: new household"),
    ],
)
def test_match_score(visit, expected, outcome):
    assert match_score(visit, KNOWN) == expected, outcome


# --- Acceptance criteria ------------------------------------------------------


def test_exact_phone_hash_matches_are_assigned_to_the_same_household(client, db):
    first = phone_visit(phone="(555) 123-4567")
    again = phone_visit(phone="+1 555 123 4567", location_id="loc-2")  # same number, another pantry
    someone_else = phone_visit(phone="555-999-0000")
    sync(client, first, again, someone_else)

    summary = run_dedup(client)

    assert household_of(db, first) is not None
    assert household_of(db, first) == household_of(db, again)
    assert household_of(db, someone_else) not in (None, household_of(db, first))
    assert summary == {**NOTHING_TO_DO, "phone_visits_assigned": 3, "households_created": 2}


def test_fallback_records_above_the_score_threshold_are_merged_to_the_same_household(client, db):
    first = no_phone_visit("M", 3, 1988, 2, visited_at="2026-10-01T10:00:00Z")
    exact = no_phone_visit("M", 3, 1988, 2, visited_at="2026-10-02T10:00:00Z")
    one_more_person = no_phone_visit("M", 3, 1988, 3, visited_at="2026-10-03T10:00:00Z")
    sync(client, first, exact, one_more_person)

    summary = run_dedup(client)

    assert household_of(db, first) is not None
    assert household_of(db, first) == household_of(db, exact) == household_of(db, one_more_person)
    assert summary == {**NOTHING_TO_DO, "households_created": 1, "no_phone_visits_merged": 2}


def test_raw_visit_records_are_preserved(client, db):
    sync(
        client,
        phone_visit(),
        phone_visit(),
        no_phone_visit("M", 3, 1988, 2),
        no_phone_visit("M", 4, 1988, 2),
        anonymous_visit(),
    )
    raw_columns = (
        "id, location_id, method, visited_at, received_at, phone_hash, "
        "first_initial, birth_month, birth_year, household_size, language"
    )
    snapshot = text(f"SELECT {raw_columns} FROM visits ORDER BY id")
    before = db.execute(snapshot).all()

    run_dedup(client)

    assert db.execute(snapshot).all() == before
    assert count(db, "visits") == 5


def test_ambiguous_cases_remain_available_for_review(client, db):
    known = no_phone_visit("M", 3, 1988, 2, visited_at="2026-10-01T10:00:00Z")
    close = no_phone_visit("M", 4, 1988, 2, visited_at="2026-10-02T10:00:00Z")  # birth month differs
    sync(client, known, close)

    summary = run_dedup(client)

    assert summary == {**NOTHING_TO_DO, "households_created": 1, "sent_to_review": 1}
    assert household_of(db, close) is None  # not guessed either way
    reviews = client.get("/api/reviews").json()
    assert len(reviews) == 1
    assert reviews[0]["score"] == 0.8
    assert reviews[0]["visit"]["id"] == close["id"]
    assert reviews[0]["visit"]["birth_month"] == 4
    assert reviews[0]["candidate_household"]["id"] == str(household_of(db, known))
    assert reviews[0]["candidate_household"]["birth_month"] == 3


# --- Details ------------------------------------------------------------------


def test_clearly_different_no_phone_visit_becomes_its_own_household(client, db):
    one = no_phone_visit("M", 3, 1988, 2)
    other = no_phone_visit("J", 7, 1970, 6)
    sync(client, one, other)

    summary = run_dedup(client)

    assert household_of(db, one) != household_of(db, other)
    assert None not in (household_of(db, one), household_of(db, other))
    assert summary == {**NOTHING_TO_DO, "households_created": 2}


def test_visit_matching_two_households_equally_goes_to_review(client, db):
    for _ in range(2):
        db.add(models.Household(first_initial="M", birth_month=3, birth_year=1988, household_size=2))
    db.commit()
    visit = no_phone_visit("M", 3, 1988, 2)
    sync(client, visit)

    summary = run_dedup(client)

    assert summary == {**NOTHING_TO_DO, "sent_to_review": 1}
    assert household_of(db, visit) is None


def test_running_the_job_again_changes_nothing(client, db):
    sync(client, phone_visit(), no_phone_visit("M", 3, 1988, 2), no_phone_visit("M", 4, 1988, 2), anonymous_visit())
    run_dedup(client)
    households, reviews = count(db, "households"), count(db, "review_items")

    assert run_dedup(client) == NOTHING_TO_DO
    assert (count(db, "households"), count(db, "review_items")) == (households, reviews)


def test_returning_visitors_join_their_existing_household_on_a_later_run(client, db):
    first_phone, first_no_phone = phone_visit(), no_phone_visit("M", 3, 1988, 2)
    sync(client, first_phone, first_no_phone)
    run_dedup(client)
    second_phone, second_no_phone = phone_visit(), no_phone_visit("M", 3, 1988, 2)
    sync(client, second_phone, second_no_phone)

    summary = run_dedup(client)

    assert household_of(db, second_phone) == household_of(db, first_phone)
    assert household_of(db, second_no_phone) == household_of(db, first_no_phone)
    assert summary == {**NOTHING_TO_DO, "phone_visits_assigned": 1, "no_phone_visits_merged": 1}


def test_anonymous_visits_are_left_alone(client, db):
    visit = anonymous_visit()
    sync(client, visit)

    assert run_dedup(client) == NOTHING_TO_DO
    assert household_of(db, visit) is None
    assert count(db, "households") == 0


def test_phone_and_no_phone_visits_are_never_matched_to_each_other(client, db):
    with_phone, without_phone = phone_visit(household_size=2), no_phone_visit("M", 3, 1988, 2)
    sync(client, with_phone, without_phone)

    run_dedup(client)

    assert household_of(db, with_phone) != household_of(db, without_phone)
    assert count(db, "review_items") == 0


def test_merge_threshold_is_configurable(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "dedup_merge_threshold", 0.8)
    known = no_phone_visit("M", 3, 1988, 2, visited_at="2026-10-01T10:00:00Z")
    close = no_phone_visit("M", 4, 1988, 2, visited_at="2026-10-02T10:00:00Z")  # scores 0.8
    sync(client, known, close)

    run_dedup(client)

    assert household_of(db, close) == household_of(db, known)
    assert count(db, "review_items") == 0


def test_dedup_and_reviews_need_the_token_when_one_is_configured(client, api_token):
    headers = {"Authorization": f"Bearer {api_token}"}

    assert client.post("/api/dedup/run").status_code == 401
    assert client.get("/api/reviews").status_code == 401
    assert client.post("/api/dedup/run", headers=headers).status_code == 200
    assert client.get("/api/reviews", headers=headers).status_code == 200
