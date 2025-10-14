# describe_allowed_value.py

from functools import singledispatch
from typing import Any


@singledispatch
def describe_allowed_value(value: Any, allowed_values: set = None) -> bool:
    raise NotImplementedError(f"cannot describe this object of type {type(value)}")


@describe_allowed_value.register
def _(value: int, allowed_values: list = None) -> bool:
    return value == allowed_values


@describe_allowed_value.register
def _(value: float, allowed_values: list = None) -> bool:
    return value == allowed_values


@describe_allowed_value.register
def _(value: str, allowed_values: list = None) -> bool:
    return value == allowed_values


@describe_allowed_value.register
def _(value: list, allowed_values: list = None) -> bool:
    if all(isinstance(v, str | int | float) for v in value):
        return any(v in allowed_values for v in value)
    if all(isinstance(v, dict) for v in value):
        return any(list(v.values())[0] in allowed_values for v in value)
    return False


@describe_allowed_value.register
def _(value: set, allowed_values: list = None) -> bool:
    return any(v in allowed_values for v in value)


@describe_allowed_value.register
def _(value: dict, allowed_values: list = None) -> bool:
    return any(v in allowed_values for v in value.values())
