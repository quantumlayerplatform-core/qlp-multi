import pytest
from unittest.mock import patch

def add(a, b):
    """
    Adds two numbers and returns the result.
    
    Args:
        a (int or float): The first number to add.
        b (int or float): The second number to add.
    
    Returns:
        int or float: The sum of the two input numbers.
    
    Raises:
        TypeError: If either input is not a number (int or float).
    """
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both inputs must be numbers (int or float)")
    return a + b

def test_add_positive_numbers():
    assert add(2, 3) == 5
    assert add(10, 20) == 30

def test_add_negative_numbers():
    assert add(-2, -3) == -5
    assert add(-10, -20) == -30

def test_add_zero():
    assert add(0, 0) == 0
    assert add(5, 0) == 5
    assert add(0, 10) == 10

def test_add_float_numbers():
    assert add(2.5, 3.7) == 6.2
    assert add(-2.1, -3.4) == -5.5

def test_add_string_and_number():
    with pytest.raises(TypeError):
        add("2", 3)

def test_add_none_and_number():
    with pytest.raises(TypeError):
        add(None, 3)