from typing import TypedDict


class CreateField(TypedDict):
    id: str
    name: str
    required: bool
    type: str | None
    allowed_values: list[str] | None
