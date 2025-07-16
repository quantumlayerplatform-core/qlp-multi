def sum_numbers(a, b):
    """
    Adds two numbers and returns the result.
    
    Args:
        a (int): The first number to add.
        b (int): The second number to add.
    
    Returns:
        int: The sum of the two input numbers.
    """
    return a + b

def main():
    """
    The main entry point of the program.
    
    This function prompts the user to enter two numbers,
    calls the sum_numbers function to calculate the sum,
    and prints the result.
    """
    num1 = int(input("Enter the first number: "))
    num2 = int(input("Enter the second number: "))
    result = sum_numbers(num1, num2)
    print(f"The sum of {num1} and {num2} is {result}")

if __name__ == "__main__":
    main()