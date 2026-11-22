"""Wyznaczanie wag kryteriów: wagi ROC i sumy rang (SMARTER, 2.11–2.12), wagi rozpiętości (SMART)."""
from __future__ import annotations

from typing import Dict, List, Sequence

from .problem import ProblemError


def roc(n: int) -> List[float]:
    """Wagi ROC dla rang 1..n: w(r) = (1/n) Σ_{s=r}^{n} 1/s (wzór 2.11)."""
    return [sum(1 / s for s in range(r, n + 1)) / n for r in range(1, n + 1)]


def rank_sum(n: int) -> List[float]:
    """Wagi sumy rang dla rang 1..n: w(r) = 2(n + 1 − r) / (n(n + 1)) (wzór 2.12)."""
    return [2 * (n + 1 - r) / (n * (n + 1)) for r in range(1, n + 1)]


def from_ranks(ranks: Sequence[int], method: str = "roc") -> List[float]:
    """Wagi kryteriów z rang (1 = najważniejsze). Rangi muszą być permutacją 1..n."""
    n = len(ranks)
    if sorted(ranks) != list(range(1, n + 1)):
        raise ProblemError(f"Rangi kryteriów muszą być permutacją 1..{n}, są {list(ranks)}")
    table = {"roc": roc, "rank_sum": rank_sum}.get(method)
    if table is None:
        raise ProblemError("Metoda wag z rang: \"roc\" albo \"rank_sum\"")
    w = table(n)
    return [w[r - 1] for r in ranks]


def swing(points: Sequence[float]) -> List[float]:
    """Wagi rozpiętości (SMART): punkty 0–100 (najważniejsze kryterium = 100) dzielone przez ich sumę."""
    if any(p < 0 for p in points):
        raise ProblemError("Punkty wag rozpiętości muszą być nieujemne")
    s = sum(points)
    if s <= 0:
        raise ProblemError("Suma punktów wag rozpiętości musi być dodatnia")
    return [p / s for p in points]


def describe() -> Dict[str, str]:
    return {"roc": "wagi centroidu opartego na uszeregowaniu (2.11)",
            "rank_sum": "wagi sumy rang (2.12)",
            "swing": "wagi rozpiętości: punkty 0–100 / suma punktów (SMART)"}
