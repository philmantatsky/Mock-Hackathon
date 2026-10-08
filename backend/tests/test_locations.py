import pytest

from app import models


@pytest.fixture
def closed_location(db):
    location = models.Location(id="loc-closed", name="Closed Pantry", active=False)
    db.add(location)
    db.commit()
    yield location
    db.delete(location)
    db.commit()


def test_lists_active_locations_by_name(client):
    response = client.get("/api/locations")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "loc-1", "name": "Eastside Community Pantry", "address": "120 Main St"},
        {"id": "loc-2", "name": "Riverside Church Pantry", "address": None},
    ]


def test_inactive_locations_are_not_listed(client, closed_location):
    ids = [location["id"] for location in client.get("/api/locations").json()]

    assert "loc-closed" not in ids
