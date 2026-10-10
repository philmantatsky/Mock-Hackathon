def test_api_is_open_when_no_token_is_configured(client):
    assert client.get("/api/locations").status_code == 200


def test_missing_token_is_rejected_when_one_is_configured(client, api_token):
    response = client.get("/api/locations")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid token"}


def test_wrong_token_is_rejected(client, api_token):
    response = client.get("/api/locations", headers={"Authorization": "Bearer not-the-token"})

    assert response.status_code == 401


def test_correct_token_is_accepted(client, api_token):
    response = client.get("/api/locations", headers={"Authorization": f"Bearer {api_token}"})

    assert response.status_code == 200


def test_health_never_needs_a_token(client, api_token):
    assert client.get("/api/health").status_code == 200
