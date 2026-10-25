import re

LOGGER_NAME = "python_jira_plus"

ALLOWED_VALUE_KEYS = ("name", "key", "value", "id")
SCHEME_PATTERN = re.compile(r"^(https?)://", re.IGNORECASE)
FIELD_TYPE_CHECKS: dict[str, tuple[type | tuple[type, ...], str]] = {
    "string": (str, "a string"),
    "number": ((int, float), "a number"),
    "boolean": (bool, "a boolean"),
    "array": (list, "an array"),
    "object": (dict, "an object"),
    "issuetype": (dict, "an issue type"),
}
