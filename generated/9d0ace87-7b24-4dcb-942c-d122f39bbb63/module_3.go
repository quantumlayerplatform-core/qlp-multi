package main

import (
    "fmt"
)

func main() {
    a := 10
    b := 20
    sum := addNumbers(a, b)
    fmt.Println("The sum of", a, "and", b, "is", sum)
}

func addNumbers(x, y int) int {
    return x + y
}