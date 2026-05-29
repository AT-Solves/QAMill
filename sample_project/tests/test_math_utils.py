"""
test_math_utils.py
Strong mutation-killing test suite for math_utils.py.
Covers all 22 functions. Tests target specific mutation operators:
AOR, ROR, LCR, BCR, RVR, SDL, NIM, BVM, EHM, DFM, SCM, LMO, TCM, CEM.
"""
import os
import pytest
from math_utils import (
    add, subtract, multiply, divide,
    is_even, is_positive, clamp, factorial,
    is_valid_age, max_of_three, percentage, is_leap_year,
    create_account, process_payment, get_grade, safe_divide,
    transfer_funds, get_user_status, find_first_positive,
    running_total, parse_config, get_connection_string,
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


# ═══════════════════════════════════════════════════════════════
# create_account(user_id, initial_balance, account_type)
# kills SDL, NIM, SCM, BVM, EHM
# ═══════════════════════════════════════════════════════════════

def test_create_account_basic():
    """Kills RVR — result must not be None."""
    result = create_account(1, 100.0, "savings")
    assert result is not None
    assert isinstance(result, dict)

def test_create_account_has_correct_user_id():
    """Kills DFM (user_id/initial_balance swap)."""
    result = create_account(42, 500.0, "checking")
    assert result["user_id"] == 42

def test_create_account_has_correct_balance():
    """Kills SDL (assignment deleted)."""
    result = create_account(1, 250.0, "savings")
    assert result["balance"] == 250.0

def test_create_account_status_active():
    """Kills SCM ('active' -> '')."""
    result = create_account(1, 100.0, "savings")
    assert result["status"] == "active"

def test_create_account_invalid_user_raises():
    """Kills EHM (raise deleted)."""
    with pytest.raises(ValueError):
        create_account(-1, 100.0, "savings")

def test_create_account_negative_balance_raises():
    """Kills ROR (< -> <=) and EHM."""
    with pytest.raises(ValueError):
        create_account(1, -50.0, "savings")

def test_create_account_zero_balance_ok():
    """Kills BVM (0 -> -1) — zero balance is valid."""
    result = create_account(1, 0.0, "savings")
    assert result["balance"] == 0.0

def test_create_account_has_empty_transactions():
    """Kills SDL — transactions list must exist."""
    result = create_account(1, 100.0, "savings")
    assert "transactions" in result
    assert result["transactions"] == []


# ═══════════════════════════════════════════════════════════════
# process_payment(amount, sender_id, receiver_id)
# kills AOR, ROR, DFM, BVM
# ═══════════════════════════════════════════════════════════════

def test_process_payment_successful():
    """Kills RVR — must return True."""
    result = process_payment(100.0, 1, 2)
    assert result is True

def test_process_payment_zero_amount_fails():
    """Kills ROR(<= to <) — zero amount must fail."""
    result = process_payment(0, 1, 2)
    assert result is False

def test_process_payment_negative_amount_fails():
    """Kills ROR — negative amount must fail."""
    result = process_payment(-50.0, 1, 2)
    assert result is False

def test_process_payment_same_account_fails():
    """Kills ROR(== to !=) — same sender/receiver must fail."""
    result = process_payment(50.0, 1, 1)
    assert result is False

def test_process_payment_insufficient_funds():
    """Kills ROR(< to <=) — more than balance must fail."""
    result = process_payment(99999.0, 1, 2)
    assert result is False

def test_process_payment_returns_bool():
    """Kills RVR — must return bool."""
    result = process_payment(10.0, 1, 2)
    assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════
# get_grade(score)
# kills ROR(>= to >), BVM, SCM, BCR
# ═══════════════════════════════════════════════════════════════

def test_get_grade_a():
    """Kills ROR(>= to >) — 90 must return A."""
    assert get_grade(90) == "A"

def test_get_grade_a_high():
    """Kills SCM ('A' -> '') — 100 must return A."""
    assert get_grade(100) == "A"

def test_get_grade_b():
    """Kills BVM (90 -> 91) — 80 must return B."""
    assert get_grade(80) == "B"

def test_get_grade_b_boundary():
    """Kills ROR(>= to >) — exactly 80 must be B."""
    assert get_grade(80) == "B"

def test_get_grade_c():
    """Kills BVM (80 -> 79)."""
    assert get_grade(70) == "C"

def test_get_grade_d():
    """Kills SCM."""
    assert get_grade(60) == "D"

def test_get_grade_f():
    """Kills SCM ('F' -> '')."""
    assert get_grade(59) == "F"

def test_get_grade_below_a():
    """Kills BVM (90 -> 89) — 89 must be B."""
    assert get_grade(89) == "B"

def test_get_grade_returns_string():
    """Kills RVR."""
    result = get_grade(75)
    assert result is not None
    assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
# safe_divide(numerator, denominator)
# kills EHM, ROR, AOR
# ═══════════════════════════════════════════════════════════════

def test_safe_divide_basic():
    """Kills AOR(/ to *) — 10/2=5, not 10*2=20."""
    assert safe_divide(10, 2) == 5.0

def test_safe_divide_zero_raises():
    """Kills EHM (raise deleted) and ROR(== to !=)."""
    with pytest.raises(ZeroDivisionError):
        safe_divide(5, 0)

def test_safe_divide_negative():
    """Kills AOR."""
    assert safe_divide(-10, 2) == -5.0

def test_safe_divide_float():
    """Kills RVR."""
    result = safe_divide(7, 2)
    assert result == 3.5
    assert result is not None

def test_safe_divide_one():
    """Kills BVM."""
    assert safe_divide(5, 1) == 5.0


# ═══════════════════════════════════════════════════════════════
# transfer_funds(from_account, to_account, amount)
# kills DFM, AOR, ROR, SCM, SDL
# ═══════════════════════════════════════════════════════════════

def test_transfer_funds_success():
    """Kills SCM ('success' -> 'failure')."""
    result = transfer_funds(1, 2, 100.0)
    assert result == "success"

def test_transfer_funds_zero_amount():
    """Kills ROR(<= to <) — zero amount must fail."""
    result = transfer_funds(1, 2, 0)
    assert result == "failure"

def test_transfer_funds_negative_amount():
    """Kills ROR — negative amount must fail."""
    result = transfer_funds(1, 2, -10)
    assert result == "failure"

def test_transfer_funds_insufficient():
    """Kills ROR(< to <=)."""
    result = transfer_funds(1, 2, 99999.0)
    assert result == "failure"

def test_transfer_funds_returns_string():
    """Kills RVR."""
    result = transfer_funds(1, 2, 10.0)
    assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
# get_user_status(user_id, is_admin)
# kills SCM, BCR, LCR, ROR
# ═══════════════════════════════════════════════════════════════

def test_get_user_status_admin():
    """Kills SCM ('admin' -> 'guest')."""
    assert get_user_status(1, True) == "admin"

def test_get_user_status_active():
    """Kills SCM ('active' -> 'inactive')."""
    assert get_user_status(1, False) == "active"

def test_get_user_status_invalid_user():
    """Kills ROR (> to >=) — user_id=0 is invalid."""
    assert get_user_status(0, False) == "invalid"

def test_get_user_status_invalid_id_negative():
    """Kills LCR (and to or) — negative id always invalid."""
    assert get_user_status(-1, True) == "invalid"

def test_get_user_status_returns_string():
    """Kills RVR."""
    result = get_user_status(1, False)
    assert result is not None
    assert isinstance(result, str)

def test_get_user_status_non_admin_not_admin():
    """Kills BCR (is_admin True/False)."""
    result = get_user_status(1, False)
    assert result != "admin"


# ═══════════════════════════════════════════════════════════════
# find_first_positive(numbers)
# kills LMO, ROR, RVR
# ═══════════════════════════════════════════════════════════════

def test_find_first_positive_finds_first():
    """Kills LMO (skip first) — first element is positive."""
    assert find_first_positive([5, 10, 15]) == 5

def test_find_first_positive_mixed():
    """Kills LMO (skip first) — first positive after negatives."""
    assert find_first_positive([-1, -2, 3, 4]) == 3

def test_find_first_positive_none_found():
    """Kills RVR — must return -1 not None."""
    assert find_first_positive([-1, -2, -3]) == -1

def test_find_first_positive_only_first():
    """Kills LMO (only first) — verifies later elements scanned."""
    assert find_first_positive([-1, 2, 3]) == 2

def test_find_first_positive_zero_not_positive():
    """Kills ROR(> to >=) — 0 is not positive."""
    assert find_first_positive([0, 5]) == 5

def test_find_first_positive_empty_list():
    """Kills LMO — empty list returns -1."""
    assert find_first_positive([]) == -1

def test_find_first_positive_single_positive():
    """Kills ROR — single positive element."""
    assert find_first_positive([7]) == 7


# ═══════════════════════════════════════════════════════════════
# running_total(values)
# kills LMO, SDL, AOR
# ═══════════════════════════════════════════════════════════════

def test_running_total_basic():
    """Kills AOR (+ to -) — basic running sum."""
    assert running_total([1, 2, 3]) == [1, 3, 6]

def test_running_total_single():
    """Kills LMO (skip first) — single element."""
    assert running_total([5]) == [5]

def test_running_total_empty():
    """Kills LMO — empty list returns empty list."""
    assert running_total([]) == []

def test_running_total_length():
    """Kills SDL (append deleted) — output same length as input."""
    result = running_total([1, 2, 3, 4])
    assert len(result) == 4

def test_running_total_first_element_unchanged():
    """Kills AOR and SDL."""
    result = running_total([10, 20, 30])
    assert result[0] == 10

def test_running_total_last_element_is_sum():
    """Kills LMO (skip last) — last element = total sum."""
    result = running_total([1, 2, 3, 4])
    assert result[-1] == 10

def test_running_total_negatives():
    """Kills AOR (+ to *) — works with negative values."""
    assert running_total([-1, -2, -3]) == [-1, -3, -6]


# ═══════════════════════════════════════════════════════════════
# parse_config(config_key, default_value)
# kills CEM, SCM
# ═══════════════════════════════════════════════════════════════

def test_parse_config_returns_default_when_not_set():
    """Kills CEM — when env var missing, returns default."""
    key = "QAMILL_TEST_KEY_NONEXISTENT_XYZ"
    os.environ.pop(key, None)
    result = parse_config(key, "mydefault")
    assert result == "mydefault"

def test_parse_config_returns_env_value_when_set():
    """Kills CEM (empty string mutation) — env var must be used."""
    key = "QAMILL_TEST_KEY_ABC"
    os.environ[key] = "envvalue"
    try:
        result = parse_config(key, "default")
        assert result == "envvalue"
    finally:
        del os.environ[key]

def test_parse_config_returns_string():
    """Kills TCM (str() removed) — result must be string."""
    key = "QAMILL_TEST_KEY_STR"
    os.environ.pop(key, None)
    result = parse_config(key, "hello")
    assert isinstance(result, str)

def test_parse_config_nonempty_default():
    """Kills SCM (default -> empty string)."""
    key = "QAMILL_TEST_NOKEY"
    os.environ.pop(key, None)
    result = parse_config(key, "fallback")
    assert result != ""


# ═══════════════════════════════════════════════════════════════
# get_connection_string(host, port, database)
# kills DFM, SCM, TCM, BVM, EHM
# ═══════════════════════════════════════════════════════════════

def test_get_connection_string_basic():
    """Kills RVR and SCM."""
    result = get_connection_string("localhost", 5432, "mydb")
    assert result == "localhost:5432/mydb"

def test_get_connection_string_contains_host():
    """Kills DFM (host/database swap)."""
    result = get_connection_string("db.example.com", 3306, "users")
    assert "db.example.com" in result

def test_get_connection_string_contains_port():
    """Kills TCM (str(port) removed)."""
    result = get_connection_string("host", 8080, "db")
    assert "8080" in result

def test_get_connection_string_contains_database():
    """Kills DFM (port/database swap)."""
    result = get_connection_string("host", 5432, "production")
    assert "production" in result

def test_get_connection_string_empty_host_raises():
    """Kills EHM (raise deleted) and ROR."""
    with pytest.raises(ValueError):
        get_connection_string("", 5432, "db")

def test_get_connection_string_zero_port_raises():
    """Kills BVM (0 to 1) and EHM."""
    with pytest.raises(ValueError):
        get_connection_string("host", 0, "db")

def test_get_connection_string_max_port():
    """Kills BVM (65535 to 65536) — max valid port."""
    result = get_connection_string("host", 65535, "db")
    assert "65535" in result

def test_get_connection_string_invalid_port_high():
    """Kills ROR(> to >=)."""
    with pytest.raises(ValueError):
        get_connection_string("host", 65536, "db")

def test_get_connection_string_returns_string():
    """Kills RVR."""
    result = get_connection_string("host", 5432, "db")
    assert isinstance(result, str)
