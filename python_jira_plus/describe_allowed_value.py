# describe_allowed_value.py

from functools import singledispatch


@singledispatch
def describe_allowed_value(value, allowed_values: set = None):
    raise NotImplementedError(f"cannot describe this object of type {type(value)}")


@describe_allowed_value.register
def _(value: int, allowed_values: list = None):
    return value == allowed_values


@describe_allowed_value.register
def _(value: float, allowed_values: list = None):
    return value == allowed_values


@describe_allowed_value.register
def _(value: str, allowed_values: list = None):
    return value == allowed_values


@describe_allowed_value.register
def _(value: list, allowed_values: list = None):
    return any(v in allowed_values for v in value)


@describe_allowed_value.register
def _(value: set, allowed_values: list = None):
    return any(v in allowed_values for v in value)


@describe_allowed_value.register
def _(value: dict, allowed_values: list = None):
    return any(v in allowed_values for v in value.values())
