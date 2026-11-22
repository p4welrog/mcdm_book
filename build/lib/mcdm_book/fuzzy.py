"""Trójkątne liczby rozmyte (rozdz. 1.4): (l, m, u), l ≤ m ≤ u."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Iterable

from .problem import ProblemError


@dataclass(frozen=True)
class TFN:
    l: float
    m: float
    u: float

    @classmethod
    def of(cls, v: Any, where: str = "") -> "TFN":
        """Trójka [l, m, u]; liczba x → (x, x, x)."""
        if isinstance(v, TFN):
            return v
        if isinstance(v, (list, tuple)):
            if len(v) != 3:
                raise ProblemError(f"{where}: liczba trójkątna musi mieć 3 składowe, jest {list(v)}")
            l, m, u = (float(x) for x in v)
        else:
            try:
                l = m = u = float(v)
            except (TypeError, ValueError):
                raise ProblemError(f"{where}: niepoprawna wartość {v!r}") from None
        if not (l <= m <= u):
            raise ProblemError(f"{where}: liczba trójkątna wymaga l ≤ m ≤ u, jest ({l:g}; {m:g}; {u:g})")
        return cls(l, m, u)

    def __add__(self, o: "TFN") -> "TFN":
        return TFN(self.l + o.l, self.m + o.m, self.u + o.u)

    def scale(self, c: float) -> "TFN":
        """c · (l, m, u) dla c ≥ 0."""
        return TFN(c * self.l, c * self.m, c * self.u)

    def coa(self) -> float:
        """Defuzyfikacja metodą środka ciężkości: (l + m + u) / 3."""
        return (self.l + self.m + self.u) / 3

    def as_list(self):
        return [self.l, self.m, self.u]


def distance(a: TFN, b: TFN) -> float:
    """Odległość wierzchołkowa: sqrt(((l_a−l_b)² + (m_a−m_b)² + (u_a−u_b)²) / 3)."""
    return sqrt(((a.l - b.l) ** 2 + (a.m - b.m) ** 2 + (a.u - b.u) ** 2) / 3)


def tfn_sum(xs: Iterable[TFN]) -> TFN:
    s = TFN(0.0, 0.0, 0.0)
    for x in xs:
        s = s + x
    return s
