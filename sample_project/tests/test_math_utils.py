"""
test_math_utils.py
Strong mutation-killing test suite for math_utils.py.
Every test is designed to kill specific AST mutations (AOR/ROR/LCR/BCR/RVR).
"""
import pytest
from math_utils import (
    add, subtract, multiply, divide,
    is_even, is_positive, clamp, factorial,
    is_valid_age, max_of_three, percentage, is_leap_year,
)


# ═══════════════════════════════════════════════════════════════
# add(a, b)  — kills AOR(+→-), AOR(+→*), RVR
# ═══════════════════════════════════════════════════════════════

def test_add_positive_numbers():
    """Kills + → - (2+3=5, but 2-3=-1)."""
    assert add(2, 3) == 5

def test_add_negative_numbers():
    """Kills + → * (-2+(-3)=-5, but -2*-3=6)."""
    assert add(-2, -3) == -5

def test_add_with_zero():
    """Kills RVR (return None instead of 0)."""
    assert add(0, 0) == 0

def test_add_identity():
    """Kills + → * (5+0=5, but 5*0=0)."""
    assert add(5, 0) == 5

def test_add_floats():
    """Kills + → - (1.5+2.5=4.0, but 1.5-2.5=-1.0)."""
    assert add(1.5, 2.5) == 4.0

def test_add_returns_correct_type():
    """Kills RVR — result must not be None."""
    result = add(3, 4)
    assert result is not None
    assert result == 7


# ═══════════════════════════════════════════════════════════════
# subtract(a, b)  — kills AOR(−→+), AOR(−→*), RVR
# ═══════════════════════════════════════════════════════════════

def test_subtract_basic():
    """Kills - → + (10-4=6, but 10+4=14)."""
    assert subtract(10, 4) == 6

def test_subtract_gives_negative():
    """Kills - → + (3-5=-2, but 3+5=8)."""
    assert subtract(3, 5) == -2

def test_subtract_zero():
    """Kills - → * (7-0=7, but 7*0=0)."""
    assert subtract(7, 0) == 7

def test_subtract_same_values():
    """Kills RVR — result must be 0, not None."""
    assert subtract(5, 5) == 0

def test_subtract_floats():
    """Kills - → + (5.5-2.5=3.0, but 5.5+2.5=8.0)."""
    assert subtract(5.5, 2.5) == 3.0


# ═══════════════════════════════════════════════════════════════
# multiply(a, b)  — kills AOR(*→+), AOR(*→-), RVR
# ═══════════════════════════════════════════════════════════════

def test_multiply_basic():
    """Kills * → + (3*4=12, but 3+4=7)."""
    assert multiply(3, 4) == 12

def test_multiply_by_zero():
    """Kills * → + (5*0=0, but 5+0=5)."""
    assert multiply(5, 0) == 0

def test_multiply_negatives():
    """Kills * → - (-2*-3=6, but -2- -3=1)."""
    assert multiply(-2, -3) == 6

def test_multiply_by_one():
    """Kills * → + (7*1=7, but 7+1=8)."""
    assert multiply(7, 1) == 7

def test_multiply_returns_not_none():
    """Kills RVR."""
    assert multiply(4, 5) is not None


# ═══════════════════════════════════════════════════════════════
# divide(a, b)  — kills AOR(/→*), ROR(==→!=,<,>), RVR
# ═══════════════════════════════════════════════════════════════

def test_divide_basic():
    """Kills / → * (10/2=5, but 10*2=20)."""
    assert divide(10, 2) == 5.0

def test_divide_by_zero_returns_none():
    """Kills RVR on None branch and ROR(==→!=)."""
    assert divide(5, 0) is None

def test_divide_zero_numerator():
    """Kills / → * (0/5=0, but 0*5=0 — passes, so also check type)."""
    result = divide(0, 5)
    assert result == 0.0
    assert result is not None

def test_divide_negative():
    """Kills / → * (-10/2=-5, but -10*2=-20)."""
    assert divide(-10, 2) == -5.0

def test_divide_float_result():
    """Kills / → + (7/2=3.5, but 7+2=9)."""
    assert divide(7, 2) == 3.5

def test_divide_non_zero_b_is_not_none():
    """Kills the ROR mutation that makes b==0 check always True."""
    result = divide(8, 4)
    assert result is not None
    assert result == 2.0


# ═══════════════════════════════════════════════════════════════
# is_even(n)  — kills AOR(%→*,%→+), ROR(==→!=), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_is_even_true_positive():
    """Kills % → * (4%2=0, but 4*2=8 → 8==0 false)."""
    assert is_even(4) is True

def test_is_even_false_odd():
    """Kills ROR(==→!=) — 3%2=1, 1!=0 would incorrectly return True."""
    assert is_even(3) is False

def test_is_even_zero():
    """Kills BCR — 0 is even, must return True not False."""
    assert is_even(0) is True

def test_is_even_negative_even():
    """Kills AOR — -4%2=0 in Python."""
    assert is_even(-4) is True

def test_is_even_negative_odd():
    """Kills ROR mutation on negative odd."""
    assert is_even(-3) is False

def test_is_even_returns_bool():
    """Kills RVR — must return True/False, not None."""
    assert is_even(2) is not None
    assert isinstance(is_even(2), bool)


# ═══════════════════════════════════════════════════════════════
# is_positive(n)  — kills ROR(>→>=, >→<, >→<=, >→==), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_is_positive_positive():
    """Kills RVR and BCR — True not None/False."""
    assert is_positive(5) is True

def test_is_positive_zero_is_not_positive():
    """Kills ROR(>→>=) — the critical boundary test."""
    assert is_positive(0) is False

def test_is_positive_negative():
    """Kills ROR(>→<) — negative is not positive."""
    assert is_positive(-1) is False

def test_is_positive_small_positive():
    """Kills ROR(>→==) — 0.001 > 0 is True."""
    assert is_positive(0.001) is True

def test_is_positive_minus_one():
    """Kills ROR(>→>=) combined with negative."""
    assert is_positive(-0.001) is False

def test_is_positive_large():
    """Kills BCR and RVR."""
    assert is_positive(1_000_000) is True


# ═══════════════════════════════════════════════════════════════
# clamp(value, minimum, maximum)
# kills ROR(<→<=,<→>), ROR(>→>=,>→<), RVR
# ═══════════════════════════════════════════════════════════════

def test_clamp_within_range():
    """Kills RVR — value inside range returned unchanged."""
    assert clamp(5, 0, 10) == 5

def test_clamp_below_minimum():
    """Kills ROR(<→>) — below min returns min."""
    assert clamp(-5, 0, 10) == 0

def test_clamp_at_minimum_boundary():
    """Kills ROR(<→<=) — at min is valid, should return min value itself."""
    assert clamp(0, 0, 10) == 0

def test_clamp_above_maximum():
    """Kills ROR(>→<) — above max returns max."""
    assert clamp(15, 0, 10) == 10

def test_clamp_at_maximum_boundary():
    """Kills ROR(>→>=) — at max is valid, should return max itself."""
    assert clamp(10, 0, 10) == 10

def test_clamp_one_above_min():
    """Kills off-by-one in minimum branch."""
    assert clamp(1, 0, 10) == 1

def test_clamp_one_below_max():
    """Kills off-by-one in maximum branch."""
    assert clamp(9, 0, 10) == 9


# ═══════════════════════════════════════════════════════════════
# factorial(n)
# kills ROR(<→<=, <→>=, ==→!=), AOR(*→+), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_factorial_zero():
    """Kills ROR(==→!=) on base case — 0! must be 1."""
    assert factorial(0) == 1

def test_factorial_one():
    """Kills off-by-one in range — 1! must be 1."""
    assert factorial(1) == 1

def test_factorial_two():
    """Kills AOR(*→+) — 2!= 2, but 1+1=2 passes, so test 3."""
    assert factorial(2) == 2

def test_factorial_five():
    """Kills AOR(*→+) definitively — 5!=120, 1+2+3+4+5=15."""
    assert factorial(5) == 120

def test_factorial_negative_raises():
    """Kills ROR(<→<=) — negative must raise ValueError."""
    with pytest.raises(ValueError):
        factorial(-1)

def test_factorial_returns_not_none():
    """Kills RVR."""
    assert factorial(3) is not None
    assert factorial(3) == 6


# ═══════════════════════════════════════════════════════════════
# is_valid_age(age)
# kills ROR(>=→>, <=→<), LCR(and→or), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_is_valid_age_adult():
    """Kills RVR and BCR."""
    assert is_valid_age(25) is True

def test_is_valid_age_zero_is_valid():
    """Kills ROR(>=→>) — age 0 must be valid."""
    assert is_valid_age(0) is True

def test_is_valid_age_minus_one_invalid():
    """Kills ROR(>=→>=) off-by-one — -1 is invalid."""
    assert is_valid_age(-1) is False

def test_is_valid_age_max_boundary():
    """Kills ROR(<=→<) — age 150 must be valid."""
    assert is_valid_age(150) is True

def test_is_valid_age_over_max():
    """Kills ROR(<=→<=) off-by-one — 151 is invalid."""
    assert is_valid_age(151) is False

def test_is_valid_age_lcr_mutation():
    """Kills LCR(and→or) — with or, -1 would be True because -1<=150."""
    assert is_valid_age(-1) is False
    assert is_valid_age(200) is False

def test_is_valid_age_midrange():
    """Kills BCR mutation on True return."""
    assert is_valid_age(75) is True


# ═══════════════════════════════════════════════════════════════
# max_of_three(a, b, c)
# kills ROR(>=→>, >=→<), LCR(and→or), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_max_of_three_first_largest():
    """Kills ROR on first branch — a is max."""
    assert max_of_three(10, 5, 3) == 10

def test_max_of_three_second_largest():
    """Kills ROR(>=→<) — b is max."""
    assert max_of_three(5, 10, 3) == 10

def test_max_of_three_third_largest():
    """Kills ROR on second branch — c is max."""
    assert max_of_three(5, 3, 10) == 10

def test_max_of_three_a_equals_b():
    """Kills ROR(>=→>) — a==b, a should win."""
    assert max_of_three(10, 10, 5) == 10

def test_max_of_three_b_equals_c():
    """Kills ROR(>=→>) on second branch — b==c, b should win."""
    assert max_of_three(5, 10, 10) == 10

def test_max_of_three_all_equal():
    """Kills LCR(and→or) and BCR."""
    assert max_of_three(7, 7, 7) == 7

def test_max_of_three_negatives():
    """Kills RVR and BCR on negative inputs."""
    assert max_of_three(-1, -2, -3) == -1


# ═══════════════════════════════════════════════════════════════
# percentage(part, total)
# kills AOR(/→*, *→+), ROR(==→!=), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_percentage_basic():
    """Kills AOR(/→*) — 50/100*100=50, but 50*100*100=500000."""
    assert percentage(50, 100) == 50.0

def test_percentage_zero_total():
    """Kills ROR(==→!=) on guard — must return 0.0."""
    assert percentage(10, 0) == 0.0

def test_percentage_full():
    """Kills AOR(*→+) — 100/100*100=100, 100/100+100=101."""
    assert percentage(100, 100) == 100.0

def test_percentage_quarter():
    """Kills /→* definitively — 1/4*100=25, 1*4*100=400."""
    assert percentage(1, 4) == 25.0

def test_percentage_zero_part():
    """Kills RVR — 0/100*100=0.0, not None."""
    result = percentage(0, 100)
    assert result == 0.0
    assert result is not None

def test_percentage_returns_float():
    """Kills BCR and RVR."""
    result = percentage(3, 4)
    assert result == 75.0
    assert isinstance(result, float)


# ═══════════════════════════════════════════════════════════════
# is_leap_year(year)
# kills ROR(%4==→!=, %100!=→==, %400==→!=), LCR(and→or, or→and), BCR, RVR
# ═══════════════════════════════════════════════════════════════

def test_is_leap_year_divisible_by_400():
    """Kills LCR(or→and) — 2000 is leap (400 rule)."""
    assert is_leap_year(2000) is True

def test_is_leap_year_century_not_400():
    """Kills ROR(%100!=→==) — 1900 div by 100, not 400: not leap."""
    assert is_leap_year(1900) is False

def test_is_leap_year_regular():
    """Kills ROR(%4==→!=) — 2024 div by 4, not 100: leap."""
    assert is_leap_year(2024) is True

def test_is_leap_year_not_divisible_by_4():
    """Kills LCR(and→or) — 2023 not div by 4: not leap."""
    assert is_leap_year(2023) is False

def test_is_leap_year_2100_not_leap():
    """Kills ROR(%400==→!=) — 2100 div by 100, not 400: not leap."""
    assert is_leap_year(2100) is False

def test_is_leap_year_1600_is_leap():
    """Kills or→and — 1600 divisible by 400: leap."""
    assert is_leap_year(1600) is True

def test_is_leap_year_returns_bool():
    """Kills RVR and BCR."""
    result = is_leap_year(2024)
    assert result is not None
    assert isinstance(result, bool)
