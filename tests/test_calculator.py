"""Tests for calculator tool behavior and edge cases."""
import pytest

from backend.tools.calculator import calculator


@pytest.mark.parametrize(
    ("first", "second", "operation", "expected"),
    [
        (2, 3, "add", 5),
        (5, 2, "sub", 3),
        (4, 3, "mul", 12),
        (9, 3, "div", 3),
        (3.5, 2.0, "add", 5.5),
    ],
)
def test_calculator_supported_operations(first: float, second: float, operation: str, expected: float):
    """Calculator should return correct result for each supported operation."""
    result = calculator.invoke(
        {
            "first_num": first,
            "second_num": second,
            "operation": operation,
        }
    )
    assert "error" not in result
    assert result["result"] == expected


def test_calculator_division_by_zero_returns_error():
    """Division by zero should not raise; it should return a structured error."""
    result = calculator.invoke({"first_num": 10, "second_num": 0, "operation": "div"})
    assert result["error"] == "Division by zero is not allowed"


def test_calculator_unsupported_operation_returns_error():
    """Unsupported operations should return a clear error message."""
    result = calculator.invoke({"first_num": 10, "second_num": 2, "operation": "pow"})
    assert "Unsupported operation 'pow'" in result["error"]
