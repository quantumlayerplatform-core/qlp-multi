from typing import Union

class FactorialError(ValueError):
    """Custom exception for factorial calculation errors."""
    pass

def factorial(n: Union[int, float]) -> int:
    """
    Calculate the factorial of a non-negative integer n.

    Args:
        n (int or float): The number to calculate the factorial for. Must be a non-negative integer.

    Returns:
        int: The factorial of n.

    Raises:
        FactorialError: If n is not an integer or is negative.
        TypeError: If n is not a number.

    Examples:
        >>> factorial(5)
        120

    """
    if not isinstance(n, (int, float)):
        raise TypeError(f"Input must be a number, got {type(n).__name__}")

    if isinstance(n, float):
        if not n.is_integer():
            raise FactorialError(f"Input must be an integer, got float {n}")
        n = int(n)

    if n < 0:
        raise FactorialError("Input must be a non-negative integer")

    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

if __name__ == "__main__":
    import sys
    try:
        if len(sys.argv) != 2:
            print("Usage: python main.py <non-negative integer>")
            sys.exit(1)
        input_value = sys.argv[1]
        # Attempt to convert input to float first to validate
        num = float(input_value)
        print(f"Factorial of {int(num)} is {factorial(num)}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

