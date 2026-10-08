"""MOC-17: dashboard metrics endpoint."""

from tests.factories import anonymous_visit, no_phone_visit, phone_visit, sync


def metrics(client):
    response = client.get("/api/metrics")
    assert response.status_code == 200, response.text
    return response.json()


def sync_a_typical_day(client):
    """7 visits: 3 households that can be identified, 1 near match, 1 anonymous."""
    sync(
        client,
        phone_visit(phone="(555) 123-4567"),
        phone_visit(phone="+1 555 123 4567"),  # the same phone again
        phone_visit(phone="555-999-0000"),
        no_phone_visit("M", 3, 1988, 2, visited_at="2026-10-01T10:00:00Z"),
        no_phone_visit("M", 3, 1988, 2, visited_at="2026-10-02T10:00:00Z"),  # the same person again
        no_phone_visit("M", 4, 1988, 2, visited_at="2026-10-03T10:00:00Z"),  # close, but birth month differs
        anonymous_visit(),
    )


# --- Acceptance criteria ------------------------------------------------------


def test_endpoint_returns_unique_household_count(client):
    sync_a_typical_day(client)
    client.post("/api/dedup/run")

    assert metrics(client)["unique_households"] == 3


def test_endpoint_returns_total_visit_count(client):
    sync_a_typical_day(client)

    assert metrics(client)["total_visits"] == 7


def test_endpoint_returns_pending_review_count(client):
    sync_a_typical_day(client)
    client.post("/api/dedup/run")

    assert metrics(client)["pending_review"] == 1


# --- Details ------------------------------------------------------------------


def test_everything_is_zero_before_any_visit(client):
    assert metrics(client) == {
        "unique_households": 0,
        "total_visits": 0,
        "pending_review": 0,
        "anonymous_visits": 0,
        "unprocessed_visits": 0,
    }


def test_running_dedup_changes_the_metrics(client):
    sync_a_typical_day(client)

    assert metrics(client) == {
        "unique_households": 0,
        "total_visits": 7,
        "pending_review": 0,
        "anonymous_visits": 1,
        "unprocessed_visits": 6,
    }

    client.post("/api/dedup/run")

    assert metrics(client) == {
        "unique_households": 3,
        "total_visits": 7,
        "pending_review": 1,
        "anonymous_visits": 1,
        "unprocessed_visits": 0,
    }


def test_returning_visitor_adds_a_visit_but_not_a_household(client):
    sync(client, phone_visit())
    client.post("/api/dedup/run")
    sync(client, phone_visit())
    client.post("/api/dedup/run")

    assert metrics(client)["total_visits"] == 2
    assert metrics(client)["unique_households"] == 1


def test_anonymous_visits_count_as_visits_but_never_as_households(client):
    sync(client, anonymous_visit(), anonymous_visit())
    client.post("/api/dedup/run")

    counts = metrics(client)
    assert (counts["total_visits"], counts["anonymous_visits"]) == (2, 2)
    assert (counts["unique_households"], counts["unprocessed_visits"]) == (0, 0)


def test_metrics_need_the_token_when_one_is_configured(client, api_token):
    assert client.get("/api/metrics").status_code == 401
    assert client.get("/api/metrics", headers={"Authorization": f"Bearer {api_token}"}).status_code == 200
