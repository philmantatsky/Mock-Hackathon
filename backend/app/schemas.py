from typing import Literal

from pydantic import BaseModel, ConfigDict


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    detail: str


class Location(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    address: str | None = None
