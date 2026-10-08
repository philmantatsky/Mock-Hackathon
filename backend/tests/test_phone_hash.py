"""MOC-15: phone numbers are stored only as HMAC hashes."""

import hashlib
import hmac
import re

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from app.config import get_settings
from app.schemas import PhoneVisit
from app.security import hash_phone, normalize_phone
from tests.factories import phone_visit, sync


@pytest.mark.parametrize(
    "written",
    ["5551234567", "(555) 123-4567", "555-123-4567", "555.123.4567", "1 555 123 4567", "+15551234567", " +1 (555) 123-4567 "],
)
def test_one_us_number_normalizes_the_same_however_it_is_written(written):
    assert normalize_phone(written) == "15551234567"


def test_international_number_keeps_its_own_country_code():
    assert normalize_phone("+44 20 7123 4567") == "442071234567"


def test_ten_digits_after_a_plus_are_not_treated_as_a_us_number():
    assert normalize_phone("+4512345678") == "4512345678"


@pytest.mark.parametrize("bad", ["", "12345", "555-CALL-NOW", "5551234567 ext 9", "1234567890123456"])
def test_invalid_numbers_are_refused_without_repeating_them(bad):
    with pytest.raises(ValueError) as error:
        normalize_phone(bad)

    assert not bad or bad not in str(error.value)


def test_hash_is_64_hex_characters():
    assert re.fullmatch(r"[0-9a-f]{64}", hash_phone("555-123-4567"))


def test_same_number_gives_the_same_hash_and_another_number_does_not():
    assert hash_phone("(555) 123-4567") == hash_phone("+1 555 123 4567")
    assert hash_phone("555-123-4567") != hash_phone("555-123-4568")


def test_hash_is_an_hmac_with_the_secret_key_not_a_plain_hash():
    key = get_settings().phone_hmac_key.get_secret_value().encode()

    assert hash_phone("555-123-4567") == hmac.new(key, b"15551234567", hashlib.sha256).hexdigest()
    assert hash_phone("555-123-4567") != hashlib.sha256(b"15551234567").hexdigest()


def test_a_different_key_gives_a_different_hash(monkeypatch):
    before = hash_phone("555-123-4567")
    monkeypatch.setattr(get_settings(), "phone_hmac_key", SecretStr("a-completely-different-key-0123456789abcdef"))

    assert hash_phone("555-123-4567") != before


# --- Through the API: what actually reaches the database ----------------------


def test_raw_phone_number_is_never_persisted(client, db):
    sync(client, phone_visit(phone="(555) 123-4567", household_size=3))

    row_as_text = db.scalar(text("SELECT visits::text FROM visits"))
    for written in ("5551234567", "15551234567", "555-123-4567", "(555) 123-4567"):
        assert written not in row_as_text


def test_only_the_hmac_hash_is_stored_as_the_phone_identity(client, db):
    sync(client, phone_visit(phone="(555) 123-4567"))

    assert db.scalar(text("SELECT phone_hash FROM visits")) == hash_phone("555-123-4567")


def test_one_number_typed_two_ways_is_stored_as_one_hash(client, db):
    sync(client, phone_visit(phone="(555) 123-4567"), phone_visit(phone="+1 555 123 4567"))

    assert db.scalar(text("SELECT count(DISTINCT phone_hash) FROM visits")) == 1


def test_phone_number_is_masked_when_a_visit_is_printed_or_logged():
    visit = PhoneVisit.model_validate(phone_visit(phone="555-123-4567"))

    assert "555-123-4567" not in repr(visit)
    assert "555-123-4567" not in str(visit.model_dump())
    assert "555-123-4567" not in visit.model_dump_json()


def test_rejecting_a_visit_does_not_repeat_its_phone_number(client):
    results = sync(
        client,
        phone_visit(phone="555-12"),
        phone_visit(phone="555-123-4567", household_size=0),
        phone_visit(phone="555-123-4567", method="5551234567"),
    )

    assert [result["status"] for result in results] == ["rejected", "rejected", "rejected"]
    for result in results:
        assert "555" not in result["error"]


def test_validation_error_response_does_not_echo_the_phone_number(client):
    # No usable id, so the whole request fails with a 422 instead of a per-visit result.
    visits = [
        phone_visit(phone="555-123-4567", id="not-a-uuid"),
        phone_visit(phone="555-123-4567", id="not-a-uuid", method="5551234567"),
    ]

    response = client.post("/api/sync", json={"visits": visits})

    assert response.status_code == 422
    assert "555" not in response.text
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
