"""Phone numbers are stored only as keyed hashes (MOC-15)."""

import hashlib
import hmac
import re

from app.config import get_settings


def normalize_phone(raw: str) -> str:
    """Reduce a phone number to its digits, country code included.

    Spaces and punctuation are dropped. A 10-digit number written without a
    leading + is taken to be a US number, so "(555) 123-4567", "555-123-4567"
    and "+1 555 123 4567" all come out as "15551234567".

    The error messages never include the number itself.
    """
    text = raw.strip()
    if re.search(r"[^0-9+().\-\s]", text):
        raise ValueError("phone number may only contain digits, spaces and + ( ) - .")
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) == 10 and not text.startswith("+"):
        digits = "1" + digits
    if not 10 <= len(digits) <= 15:
        raise ValueError("phone number must have 10 to 15 digits")
    return digits


def hash_phone(raw: str) -> str:
    """Return HMAC-SHA256 of the normalized number, as 64 hex characters.

    A plain hash would protect nothing: there are few enough phone numbers to
    hash every one of them and look the answer up. Mixing in a secret key
    (PHONE_HMAC_KEY) makes that impossible without the key.
    """
    key = get_settings().phone_hmac_key.get_secret_value().encode()
    return hmac.new(key, normalize_phone(raw).encode(), hashlib.sha256).hexdigest()
