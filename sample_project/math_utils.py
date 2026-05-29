"""
math_utils.py
Sample target codebase for AMIL demonstration.
Contains intentional variety of operators for rich mutation coverage.
"""


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        return None
    return a / b


def is_even(n: int) -> bool:
    return n % 2 == 0


def is_positive(n: float) -> bool:
    return n > 0


def clamp(value: float, minimum: float, maximum: float) -> float:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def is_valid_age(age: int) -> bool:
    return age >= 0 and age <= 150


def max_of_three(a: float, b: float, c: float) -> float:
    if a >= b and a >= c:
        return a
    if b >= c:
        return b
    return c


def percentage(part: float, total: float) -> float:
    if total == 0:
        return 0.0
    return (part / total) * 100


def is_leap_year(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
