"""MOC-15: phone numbers are stored only as HMAC hashes."""

import hashlib
import hmac
import re

import pytest
from pydantic import SecretStr

from app.config import get_settings
from app.security import hash_phone, normalize_phone


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
