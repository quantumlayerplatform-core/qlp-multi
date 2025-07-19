class NonIntegerError(TypeError):
    """Exception raised for errors in the input type."""
    pass

class NegativeValueError(ValueError):
    """Exception raised for negative input values."""
    pass

def factorial(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer n.

    Args:
        n (int): The number to calculate the factorial for. Must be a non-negative integer.

    Returns:
        int: The factorial of n.

    Raises:
        NonIntegerError: If n is not an integer.
        NegativeValueError: If n is negative.

    Examples:
        >>> factorial(5)
        120
    """
    if not isinstance(n, int):
        raise NonIntegerError("Input must be an integer")
    
    if n < 0:
        raise NegativeValueError("Input must be a non-negative integer")
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
