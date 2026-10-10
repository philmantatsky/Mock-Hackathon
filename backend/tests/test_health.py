from sqlalchemy import text


def test_health_reports_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_dev_server_is_allowed_by_cors(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_migrations_create_the_tables_and_demo_locations(db):
    tables = set(db.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))
    assert {"locations", "households", "visits", "review_items"} <= tables

    location_ids = set(db.scalars(text("SELECT id FROM locations")))
    assert location_ids == {"loc-1", "loc-2"}


def test_visits_table_has_no_column_for_a_raw_phone_number(db):
    columns = set(
        db.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'visits'"))
    )
    assert "phone_hash" in columns
    assert not {name for name in columns if "phone" in name and name != "phone_hash"}
