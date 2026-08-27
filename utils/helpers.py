"""Quarter/week parsing and run-rate helpers."""
import re


def parse_quarter(q_str: str) -> tuple:
    """'2025-Q2' → (2025, 2)"""
    m = re.match(r"(\d{4})-Q(\d)", str(q_str))
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def quarter_to_int(q_str: str) -> int:
    """'2025-Q2' → sequential int (used for arithmetic on quarters)."""
    y, q = parse_quarter(q_str)
    return y * 4 + (q - 1)


def int_to_quarter(n: int) -> str:
    """Reverse of quarter_to_int."""
    y = n // 4
    q = (n % 4) + 1
    return f"{y}-Q{q}"


def get_prior_n_quarters(current_q: str, n: int) -> list:
    """Return list of n quarters immediately before current_q, newest-first."""
    curr_int = quarter_to_int(current_q)
    return [int_to_quarter(curr_int - i) for i in range(1, n + 1)]


def sort_quarters(quarters: list) -> list:
    return sorted(quarters, key=quarter_to_int)


def quarter_label(q_str: str) -> str:
    """'2025-Q2' → 'Q2'25' display label."""
    y, q = parse_quarter(q_str)
    return f"Q{q}'{str(y)[2:]}"
