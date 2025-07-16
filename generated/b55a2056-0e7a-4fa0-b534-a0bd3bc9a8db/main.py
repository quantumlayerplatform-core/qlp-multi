def add_numbers(a, b):
    """
    Adds two numbers and returns the result.
    
    Args:
        a (int, float): The first number to add.
        b (int, float): The second number to add.
    
    Returns:
        int or float: The sum of the two input numbers.
    
    Raises:
        TypeError: If either input is not a number (int or float).
    """
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both inputs must be numbers (int or float)")
    return a + b