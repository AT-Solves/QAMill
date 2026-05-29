"""
math_utils.py
Sample target codebase for QAMill demonstration.
Contains intentional variety of operators for rich mutation coverage.
Includes original 12 functions plus 10 new functions targeting new operators.
"""
import os


# ── Stub helpers used by new functions ─────────────────────────────────────

def validate_user_id(user_id):
    """Stub: returns True if user_id is a positive integer."""
    return isinstance(user_id, int) and user_id > 0


def get_account_balance(account_id):
    """Stub: returns a fake balance for testing."""
    balances = {1: 1000.0, 2: 500.0, 3: 250.0}
    return balances.get(account_id, 0.0)


def update_account_balance(account_id, new_balance):
    """Stub: simulates updating account balance."""
    return True


def send_notification(user_id, message):
    """Stub: simulates sending a notification."""
    return True


# ── Original 12 functions ───────────────────────────────────────────────────

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


# ── New functions targeting additional mutation operators ──────────────────

def create_account(user_id: int, initial_balance: float, account_type: str) -> dict:
    """Create a new account. Targets SDL, NIM, SCM, DFM, BVM."""
    if not validate_user_id(user_id):
        raise ValueError("Invalid user ID")
    if initial_balance < 0:
        raise ValueError("Initial balance cannot be negative")
    status = "active"
    account = {
        "user_id": user_id,
        "balance": initial_balance,
        "type": account_type,
        "status": status,
        "transactions": [],
    }
    send_notification(user_id, "Account created successfully")
    return account


def process_payment(amount: float, sender_id: int, receiver_id: int) -> bool:
    """Process a payment between two accounts. Targets AOR, ROR, DFM, NIM, BVM."""
    if amount <= 0:
        return False
    if sender_id == receiver_id:
        return False
    sender_balance = get_account_balance(sender_id)
    if sender_balance < amount:
        return False
    new_sender_balance = sender_balance - amount
    receiver_balance = get_account_balance(receiver_id)
    new_receiver_balance = receiver_balance + amount
    update_account_balance(sender_id, new_sender_balance)
    update_account_balance(receiver_id, new_receiver_balance)
    return True


def get_grade(score: int) -> str:
    """Convert numeric score to letter grade. Targets ROR, BVM, SCM, BCR."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def safe_divide(numerator: float, denominator: float) -> float:
    """Safe division that raises on zero. Targets EHM, ROR, AOR."""
    if denominator == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    try:
        result = numerator / denominator
        return result
    except Exception as e:
        raise RuntimeError(f"Division failed: {e}")


def transfer_funds(from_account: int, to_account: int, amount: float) -> str:
    """Transfer funds between accounts. Targets DFM, AOR, ROR, SDL."""
    if amount <= 0:
        return "failure"
    balance = get_account_balance(from_account)
    if balance < amount:
        return "failure"
    new_balance = balance - amount
    update_account_balance(from_account, new_balance)
    dest_balance = get_account_balance(to_account)
    update_account_balance(to_account, dest_balance + amount)
    return "success"


def get_user_status(user_id: int, is_admin: bool) -> str:
    """Return user status string. Targets SCM, BCR, LCR, ROR."""
    if not validate_user_id(user_id):
        return "invalid"
    if is_admin and user_id > 0:
        return "admin"
    if user_id > 0:
        return "active"
    return "inactive"


def find_first_positive(numbers: list) -> int:
    """Find first positive number in list. Targets LMO, ROR, RVR."""
    for num in numbers:
        if num > 0:
            return num
    return -1


def running_total(values: list) -> list:
    """Return running totals. Targets LMO, SDL, AOR."""
    totals = []
    current = 0
    for val in values:
        current = current + val
        totals.append(current)
    return totals


def parse_config(config_key: str, default_value: str) -> str:
    """Read configuration from environment. Targets CEM, SCM."""
    value = os.environ.get(config_key, default_value)
    if not value:
        return default_value
    return str(value)


def get_connection_string(host: str, port: int, database: str) -> str:
    """Build a database connection string. Targets DFM, SCM, TCM, BVM."""
    if not host:
        raise ValueError("Host cannot be empty")
    if port <= 0 or port > 65535:
        raise ValueError("Invalid port number")
    port_str = str(port)
    return f"{host}:{port_str}/{database}"
