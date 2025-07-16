package main

import "fmt"

// Add takes two integers and returns their sum.
// Parameters:
//   a (int): The first number to add.
//   b (int): The second number to add.
// Returns:
//   int: The sum of the two input numbers.
func Add(a, b int) int {
    return a + b
}

func main() {
    result := Add(5, 3)
    fmt.Println("The sum is:", result) // Output: The sum is: 8

    result = Add(-2, 7)
    fmt.Println("The sum is:", result) // Output: The sum is: 5
}