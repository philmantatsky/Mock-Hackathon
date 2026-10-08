"""Validation messages that never repeat what the client sent.

A visit can contain a phone number, and FastAPI's default 422 response echoes
the rejected input back. These helpers say where the problem is and which rule
was broken, without the submitted value.
"""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

METHOD_RULE = "method must be 'phone', 'no_phone' or 'anonymous'"


def safe_message(error: dict[str, Any]) -> str:
    # Pydantic quotes the unrecognised value in this one message; all the
    # others only describe the rule.
    if error["type"].startswith("union_tag"):
        return METHOD_RULE
    return error["msg"].removeprefix("Value error, ")


async def validation_error_without_inputs(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = [{"loc": list(error["loc"]), "msg": safe_message(error), "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})
