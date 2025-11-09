from typing import Sequence

from fastmcp import FastMCP
from logger import get_logger
from pydantic import BaseModel, Field


mcp = FastMCP(name="calculator")
log = get_logger("calculator_mcp_server")


class CalculationResult(BaseModel):
    operation: str = Field(..., description="Arithmetic operation that was performed")
    operands: list[float] = Field(..., description="Numbers that were used in the calculation")
    result: float = Field(..., description="Result of the arithmetic operation")


def _normalize_operands(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


@mcp.tool(description="Add numbers together and return the sum.")
async def add_numbers(values: list[float]) -> CalculationResult:
    if not values:
        raise ValueError("At least one value is required to perform addition.")

    operands = _normalize_operands(values)
    result = sum(operands)
    log.info(f"[add_numbers] operands={operands} result={result}")
    return CalculationResult(operation="addition", operands=operands, result=result)


@mcp.tool(description="Subtract the second number from the first and return the difference.")
async def subtract(minuend: float, subtrahend: float) -> CalculationResult:
    operands = _normalize_operands([minuend, subtrahend])
    result = operands[0] - operands[1]
    log.info(f"[subtract] operands={operands} result={result}")
    return CalculationResult(operation="subtraction", operands=operands, result=result)


@mcp.tool(description="Multiply numbers together and return the product.")
async def multiply_numbers(values: list[float]) -> CalculationResult:
    if not values:
        raise ValueError("At least one value is required to perform multiplication.")

    operands = _normalize_operands(values)
    product = 1.0
    for value in operands:
        product *= value

    log.info(f"[multiply_numbers] operands={operands} result={product}")
    return CalculationResult(operation="multiplication", operands=operands, result=product)


def main() -> None:
    log.info("Starting Calculator MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
