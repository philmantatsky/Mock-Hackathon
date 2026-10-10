"""MOC-14: batch visit sync endpoint with UUID idempotency."""

from sqlalchemy import text

from tests.factories import anonymous_visit, no_phone_visit, phone_visit, sync


def statuses(results):
    return [result["status"] for result in results]


def count_visits(db):
    return db.scalar(text("SELECT count(*) FROM visits"))


# --- Acceptance criteria ------------------------------------------------------


def test_sync_accepts_a_batch_of_visits(client, db):
    batch = [phone_visit(household_size=4), no_phone_visit(), anonymous_visit()]

    results = sync(client, *batch)

    assert [result["id"] for result in results] == [visit["id"] for visit in batch]
    assert statuses(results) == ["created", "created", "created"]
    assert count_visits(db) == 3


def test_duplicate_visit_uuid_is_ignored_rather_than_inserted_again(client, db):
    already_sent = phone_visit()
    sync(client, already_sent)

    results = sync(client, already_sent, anonymous_visit())

    assert statuses(results) == ["duplicate", "created"]
    assert count_visits(db) == 2


def test_retrying_the_same_batch_does_not_create_duplicate_visits(client, db):
    batch = [phone_visit(), no_phone_visit(), anonymous_visit()]
    sync(client, *batch)

    results = sync(client, *batch)

    assert statuses(results) == ["duplicate", "duplicate", "duplicate"]
    assert count_visits(db) == 3


# --- Details ------------------------------------------------------------------


def test_uuid_repeated_inside_one_batch_is_stored_once(client, db):
    visit = phone_visit()

    results = sync(client, visit, visit)

    assert statuses(results) == ["created", "duplicate"]
    assert count_visits(db) == 1


def test_resending_an_id_with_different_details_keeps_the_first_version(client, db):
    original = no_phone_visit(household_size=2)
    sync(client, original)

    results = sync(client, {**original, "household_size": 7})

    assert statuses(results) == ["duplicate"]
    assert db.scalar(text("SELECT household_size FROM visits")) == 2


def test_each_kind_of_visit_is_stored_with_only_its_own_fields(client, db):
    sync(
        client,
        phone_visit(household_size=4, language="es", location_id="loc-2"),
        no_phone_visit(first_initial="M", birth_month=3, birth_year=1988, household_size=2),
        anonymous_visit(),
    )

    rows = {row.method: row for row in db.execute(text("SELECT * FROM visits"))}
    assert (rows["phone"].household_size, rows["phone"].language, rows["phone"].location_id) == (4, "es", "loc-2")
    assert rows["phone"].phone_hash is not None and rows["phone"].first_initial is None
    assert (rows["no_phone"].first_initial, rows["no_phone"].birth_month, rows["no_phone"].birth_year) == ("M", 3, 1988)
    assert rows["no_phone"].household_size == 2 and rows["no_phone"].phone_hash is None
    anonymous = rows["anonymous"]
    assert anonymous.phone_hash is None and anonymous.first_initial is None
    assert anonymous.birth_month is None and anonymous.birth_year is None and anonymous.household_size is None
    assert all(row.household_id is None for row in rows.values())  # households are the dedup job's work


def test_visit_time_from_the_device_is_kept(client, db):
    sync(client, anonymous_visit(visited_at="2026-10-01T09:30:00-05:00"))

    stored = db.scalar(text("SELECT visited_at AT TIME ZONE 'UTC' FROM visits"))
    assert stored.isoformat() == "2026-10-01T14:30:00"


def test_first_initial_is_stored_as_a_capital_without_accents(client, db):
    sync(client, no_phone_visit(first_initial="á"))

    assert db.scalar(text("SELECT first_initial FROM visits")) == "A"


def test_one_invalid_visit_is_rejected_and_the_rest_are_stored(client, db):
    results = sync(client, phone_visit(), no_phone_visit(birth_month=13), anonymous_visit())

    assert statuses(results) == ["created", "rejected", "created"]
    assert results[1]["error"] == "birth_month: Input should be less than or equal to 12"
    assert count_visits(db) == 2


def test_unknown_location_is_rejected(client, db):
    results = sync(client, anonymous_visit(location_id="loc-nowhere"))

    assert statuses(results) == ["rejected"]
    assert results[0]["error"] == "location_id: unknown location"
    assert count_visits(db) == 0


def test_unknown_method_is_rejected(client):
    results = sync(client, anonymous_visit(method="walk_in"))

    assert statuses(results) == ["rejected"]
    assert results[0]["error"] == "method must be 'phone', 'no_phone' or 'anonymous'"


def test_anonymous_visit_cannot_carry_identifying_details(client, db):
    results = sync(client, anonymous_visit(first_initial="M", birth_month=3))

    assert statuses(results) == ["rejected"]
    assert "first_initial: Extra inputs are not permitted" in results[0]["error"]
    assert count_visits(db) == 0


def test_name_and_email_fields_are_refused(client, db):
    results = sync(client, phone_visit(name="Maria"), no_phone_visit(email="m@example.com"))

    assert statuses(results) == ["rejected", "rejected"]
    assert count_visits(db) == 0


def test_visit_time_without_a_timezone_is_rejected(client):
    results = sync(client, anonymous_visit(visited_at="2026-10-01T09:30:00"))

    assert statuses(results) == ["rejected"]
    assert results[0]["error"] == "visited_at: Input should have timezone info"


def test_visit_without_a_usable_id_fails_the_whole_request(client, db):
    response = client.post("/api/sync", json={"visits": [anonymous_visit(), anonymous_visit(id="not-a-uuid")]})

    assert response.status_code == 422
    assert count_visits(db) == 0


def test_empty_batch_is_accepted(client):
    assert sync(client) == []


def test_more_than_500_visits_in_one_request_is_refused(client, db):
    response = client.post("/api/sync", json={"visits": [anonymous_visit() for _ in range(501)]})

    assert response.status_code == 422
    assert count_visits(db) == 0


def test_sync_needs_the_token_when_one_is_configured(client, db, api_token):
    batch = {"visits": [anonymous_visit()]}

    assert client.post("/api/sync", json=batch).status_code == 401
    assert count_visits(db) == 0
    assert client.post("/api/sync", json=batch, headers={"Authorization": f"Bearer {api_token}"}).status_code == 200
    assert count_visits(db) == 1
