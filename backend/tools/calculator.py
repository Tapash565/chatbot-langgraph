"""Calculator tool."""
from langchain_core.tools import tool

from backend.core.logging import get_logger, log_span

logger = get_logger(__name__)


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.

    Args:
        first_num: The first number
        second_num: The second number
        operation: The operation to perform (add, sub, mul, div)

    Returns:
        A dictionary with the operation details and result
    """
    with log_span("tool_calculator", operation=operation):
        logger.info(
            "calculator_invoked",
            operation=operation,
            first_num=first_num,
            second_num=second_num,
        )

        try:
            if operation == "add":
                result = first_num + second_num
            elif operation == "sub":
                result = first_num - second_num
            elif operation == "mul":
                result = first_num * second_num
            elif operation == "div":
                if second_num == 0:
                    logger.error("calculator_error", error="Division by zero")
                    return {"error": "Division by zero is not allowed"}
                result = first_num / second_num
            else:
                logger.warning("calculator_unsupported", operation=operation)
                return {"error": f"Unsupported operation '{operation}'"}

            response = {
                "first_num": first_num,
                "second_num": second_num,
                "operation": operation,
                "result": result,
            }
            logger.info("calculator_success", operation=operation, result=result)
            return response
        except Exception as e:
            logger.error(
                "calculator_exception",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"error": str(e)}
