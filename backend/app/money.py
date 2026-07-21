"""Money helpers. All monetary values are integer minor units (e.g. cents)."""


def format_minor(amount_minor: int, currency: str = "USD") -> str:
    return f"{amount_minor / 100:,.2f} {currency}"


def dollars_to_minor(dollars: float) -> int:
    return round(dollars * 100)
