import re
from typing import NamedTuple

LOGGER_NAME = "python_jira_plus"


class FieldTypeCheck(NamedTuple):
    python_types: type | tuple[type, ...]
    label: str


ALLOWED_VALUE_KEYS = ("name", "key", "value", "id")
SCHEME_PATTERN = re.compile(r"^(https?)://", re.IGNORECASE)
FIELD_TYPE_CHECKS = {
    "string": FieldTypeCheck(str, "a string"),
    "number": FieldTypeCheck((int, float), "a number"),
    "boolean": FieldTypeCheck(bool, "a boolean"),
    "array": FieldTypeCheck(list, "an array"),
    "object": FieldTypeCheck(dict, "an object"),
    "issuetype": FieldTypeCheck(dict, "an issue type"),
}
ISSUE_REF_PATTERN = re.compile(r"[A-Za-z0-9_]+(-[0-9]+)?")
ORDER_BY_PATTERN = re.compile(r"\border\s+by\b", re.IGNORECASE)
