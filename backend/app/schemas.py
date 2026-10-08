import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    field_validator,
)
from typing_extensions import TypeAliasType

from app.errors import safe_message
from app.security import normalize_phone

VISIT_METHODS = ("phone", "no_phone", "anonymous")


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    detail: str


class Location(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    address: str | None = None


# --- Visits coming in through /api/sync -------------------------------------
#
# There are three ways to check in. Each has its own model, and extra fields
# are refused, so an anonymous visit cannot carry identifying details and no
# visit can carry a name or an email.


class _VisitBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID = Field(
        description="Generated on the device when the visit is recorded; used for idempotent retries."
    )
    location_id: str = Field(min_length=1, max_length=64)
    visited_at: AwareDatetime = Field(
        description="Device time when the visitor was signed in (not upload time). Must include a UTC offset."
    )
    language: Literal["en", "es"] | None = None


class PhoneVisit(_VisitBase):
    """Check-in with a phone number."""

    method: Literal["phone"]
    # SecretStr keeps the number out of logs and error output. Only its hash is stored.
    phone: SecretStr = Field(
        description=(
            "10 to 15 digits, optional leading +. Spaces and punctuation are ignored, "
            "and 10 digits without a + are read as a US number."
        )
    )
    household_size: int | None = Field(default=None, ge=1, le=30)

    @field_validator("phone")
    @classmethod
    def _must_be_a_phone_number(cls, value: SecretStr) -> SecretStr:
        normalize_phone(value.get_secret_value())
        return value


class NoPhoneVisit(_VisitBase):
    """Check-in without a phone: first initial, birth month and year, household size."""

    method: Literal["no_phone"]
    first_initial: str = Field(min_length=1, max_length=1, description="One letter. Stored as a capital without accents.")
    birth_month: int = Field(ge=1, le=12)
    birth_year: int = Field(ge=1900)
    household_size: int = Field(ge=1, le=30)

    @field_validator("first_initial", mode="before")
    @classmethod
    def _capital_without_accents(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        # Split accents off the letter and drop them, so "á" and "A" are the same initial.
        decomposed = unicodedata.normalize("NFKD", value.strip())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).upper()

    @field_validator("first_initial")
    @classmethod
    def _must_be_a_letter(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("first initial must be a letter")
        return value

    @field_validator("birth_year")
    @classmethod
    def _not_in_the_future(cls, value: int) -> int:
        if value > date.today().year:
            raise ValueError("birth year cannot be in the future")
        return value


class AnonymousVisit(_VisitBase):
    """"Prefer not to say": a visit with no identifying details at all."""

    method: Literal["anonymous"]


VisitIn = TypeAliasType(
    "VisitIn",
    Annotated[PhoneVisit | NoPhoneVisit | AnonymousVisit, Field(discriminator="method")],
)


@dataclass(frozen=True)
class RejectedVisit:
    """Stands in for a visit that failed validation. Internal, never part of the API."""

    id: uuid.UUID
    error: str


def _describe_rejection(exc: ValidationError) -> str:
    problems = []
    for error in exc.errors(include_url=False, include_context=False, include_input=False):
        loc = error["loc"]
        if loc and loc[0] in VISIT_METHODS:  # errors inside a visit start with its method
            loc = loc[1:]
        field = ".".join(str(part) for part in loc)
        message = safe_message(error)
        problems.append(f"{field}: {message}" if field else message)
    return "; ".join(problems)


def _usable_id(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value["id"]))
    except (TypeError, KeyError, ValueError):
        return None


def _reject_instead_of_failing(value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
    """Turn one invalid visit into a RejectedVisit, so the rest of the batch is still stored.

    One bad record must not block an offline queue forever. The exception is a
    visit with no usable id: its result could not be reported, so the request fails.
    """
    try:
        return handler(value)
    except ValidationError as exc:
        visit_id = _usable_id(value)
        if visit_id is None:
            raise
        return RejectedVisit(id=visit_id, error=_describe_rejection(exc))


class SyncRequest(BaseModel):
    # After validation each item is a visit model or a RejectedVisit.
    visits: list[Annotated[VisitIn, WrapValidator(_reject_instead_of_failing)]] = Field(max_length=500)


class SyncResult(BaseModel):
    id: uuid.UUID
    status: Literal["created", "duplicate", "rejected"]
    error: str | None = None


class SyncResponse(BaseModel):
    results: list[SyncResult] = Field(description="One result per visit, in the same order as the request.")
