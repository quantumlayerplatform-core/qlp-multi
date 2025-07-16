import pytest
from typing import Union

def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """
    Adds two numbers and returns the result.
    
    Args:
        a (Union[int, float]): The first number to add.
        b (Union[int, float]): The second number to add.
    
    Returns:
        Union[int, float]: The sum of the two input numbers.
    
    Raises:
        TypeError: If either input is not a number (int or float).
    """
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both inputs must be numbers (int or float)")
    return a + b