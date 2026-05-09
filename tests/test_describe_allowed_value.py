import pytest

from python_jira_plus.describe_allowed_value import describe_allowed_value


class TestDescribeAllowedValueStr:
    def test_str_in_allowed_set_returns_true(self) -> None:
        assert describe_allowed_value("High", allowed_values={"High", "Medium", "Low"}), \
            "Expected True for 'High' in allowed set"

    def test_str_not_in_allowed_set_returns_false(self) -> None:
        assert not describe_allowed_value("Critical", allowed_values={"High", "Medium", "Low"}), \
            "Expected False for 'Critical' not in allowed set"


class TestDescribeAllowedValueInt:
    def test_int_in_allowed_set_returns_true(self) -> None:
        assert describe_allowed_value(1, allowed_values={1, 2, 3}), \
            "Expected True for 1 in allowed set"

    def test_int_not_in_allowed_set_returns_false(self) -> None:
        assert not describe_allowed_value(9, allowed_values={1, 2, 3}), \
            "Expected False for 9 not in allowed set"


class TestDescribeAllowedValueFloat:
    def test_float_in_allowed_set_returns_true(self) -> None:
        assert describe_allowed_value(1.5, allowed_values={1.5, 2.5}), \
            "Expected True for 1.5 in allowed set"

    def test_float_not_in_allowed_set_returns_false(self) -> None:
        assert not describe_allowed_value(9.9, allowed_values={1.5, 2.5}), \
            "Expected False for 9.9 not in allowed set"


class TestDescribeAllowedValueList:
    def test_list_of_strings_with_match_returns_true(self) -> None:
        assert describe_allowed_value(["High", "Unknown"], allowed_values={"High", "Medium"}), \
            "Expected True when at least one item matches"

    def test_list_of_strings_no_match_returns_false(self) -> None:
        assert not describe_allowed_value(["Critical", "Unknown"], allowed_values={"High", "Medium"}), \
            "Expected False when no items match"

    def test_list_of_dicts_with_match_returns_true(self) -> None:
        assert describe_allowed_value([{"name": "High"}], allowed_values={"High", "Medium"}), \
            "Expected True when dict value matches"

    def test_list_of_dicts_no_match_returns_false(self) -> None:
        assert not describe_allowed_value([{"name": "Critical"}], allowed_values={"High", "Medium"}), \
            "Expected False when dict value doesn't match"


class TestDescribeAllowedValueSet:
    def test_set_with_match_returns_true(self) -> None:
        assert describe_allowed_value({"High", "Unknown"}, allowed_values={"High", "Medium"}), \
            "Expected True when set contains a match"

    def test_set_no_match_returns_false(self) -> None:
        assert not describe_allowed_value({"Critical"}, allowed_values={"High", "Medium"}), \
            "Expected False when set has no match"


class TestDescribeAllowedValueDict:
    def test_dict_value_in_allowed_set_returns_true(self) -> None:
        assert describe_allowed_value({"name": "High"}, allowed_values={"High", "Medium"}), \
            "Expected True when dict value matches"

    def test_dict_value_not_in_allowed_set_returns_false(self) -> None:
        assert not describe_allowed_value({"name": "Critical"}, allowed_values={"High", "Medium"}), \
            "Expected False when dict value doesn't match"


class TestDescribeAllowedValueUnknownType:
    def test_unknown_type_raises_not_implemented_error(self) -> None:
        with pytest.raises(NotImplementedError):
            describe_allowed_value(object(), allowed_values={"High"})
