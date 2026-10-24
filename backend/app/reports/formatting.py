"""Mise en forme des montants et indicateurs à la française (1 234 567,89 MAD)."""


def _group(value: float, decimals: int) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",")


def fmt_value(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    if unit == "MAD":
        return f"{_group(value, 0)} MAD"
    if unit == "%":
        return f"{_group(value, 1)} %"
    if unit == "ratio":
        return _group(value, 2)
    if unit in ("jours", "mois", "heures", "ans"):
        return f"{_group(value, 1)} {unit}"
    return _group(value, 0 if float(value).is_integer() else 1)


def fmt_delta(delta: float | None) -> str | None:
    if delta is None:
        return None
    return f"{'+' if delta > 0 else ''}{_group(delta, 1)} % vs mois précédent"


STATUS_LABELS = {"ok": "Bon niveau", "warning": "À surveiller", "critical": "Critique"}
