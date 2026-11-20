"""Zadanie decyzyjne: warianty, kryteria, oceny. Format JSON wspólny dla wszystkich metod.

{
  "name": "Wybór konta",                      # opcjonalnie
  "variants": ["a1", "a2", ...],
  "criteria": [
     {"name": "f1", "direction": "max", "weight": 0.1,
      "fuzzy_weight": [0, 0.1, 0.5],          # metody rozmyte (FSAW)
      "rank": 3, "swing": 30,                 # SMART / SMARTER (wagi z rang lub punktów)
      "scale": {...}},                        # SMART: sposób oceny kryterium (zob. additive.smart)
     ...],
  "values": [[4, 26, 2.5], ...]               # values[i][k]; liczby albo trójki [l, m, u]
}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

MAX, MIN = "max", "min"


class ProblemError(ValueError):
    """Błąd danych wejściowych (komunikat dla użytkownika)."""


@dataclass
class Criterion:
    name: str
    direction: str = MAX
    weight: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def maximize(self) -> bool:
        return self.direction == MAX


@dataclass
class Problem:
    variants: List[str]
    criteria: List[Criterion]
    values: List[List[Any]]
    name: str = ""

    @property
    def m(self) -> int:
        return len(self.variants)

    @property
    def n(self) -> int:
        return len(self.criteria)

    def column(self, k: int) -> List[Any]:
        return [row[k] for row in self.values]

    def weights(self, *, required: bool = True, normalize: bool = True, notes: Optional[list] = None) -> List[float]:
        w = [c.weight for c in self.criteria]
        if any(x is None for x in w):
            if required:
                raise ProblemError("Brak wag kryteriów (pole \"weight\")")
            return []
        if any(x < 0 for x in w):
            raise ProblemError("Wagi muszą być nieujemne")
        s = sum(w)
        if s <= 0:
            raise ProblemError("Suma wag musi być dodatnia")
        if normalize and abs(s - 1) > 1e-9:
            if notes is not None:
                notes.append(f"Wagi sumowały się do {s:g}; znormalizowano je do sumy 1.")
            w = [x / s for x in w]
        return list(map(float, w))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Problem":
        try:
            variants = [str(v) for v in d["variants"]]
            crit_in = d["criteria"]
            values = d["values"]
        except KeyError as e:
            raise ProblemError(f"Brak pola {e.args[0]!r} w opisie zadania") from None
        criteria = []
        for c in crit_in:
            if isinstance(c, str):
                c = {"name": c}
            c = dict(c)
            name = str(c.pop("name"))
            direction = str(c.pop("direction", MAX)).lower()
            if direction in ("maks", "zysk", "benefit", "profit"):
                direction = MAX
            if direction in ("koszt", "cost"):
                direction = MIN
            if direction not in (MAX, MIN):
                raise ProblemError(f"Kryterium {name}: kierunek musi być \"max\" albo \"min\"")
            w = c.pop("weight", None)
            criteria.append(Criterion(name, direction, None if w is None else float(w), c))
        if len(set(variants)) != len(variants):
            raise ProblemError("Nazwy wariantów muszą być różne")
        if len(values) != len(variants):
            raise ProblemError(f"Liczba wierszy ocen ({len(values)}) różna od liczby wariantów ({len(variants)})")
        for i, row in enumerate(values):
            if len(row) != len(criteria):
                raise ProblemError(f"Wariant {variants[i]}: {len(row)} ocen, a kryteriów jest {len(criteria)}")
        return cls(variants, criteria, [list(r) for r in values], str(d.get("name", "")))

    def to_dict(self) -> Dict[str, Any]:
        crit = []
        for c in self.criteria:
            x = {"name": c.name, "direction": c.direction, **c.extra}
            if c.weight is not None:
                x["weight"] = c.weight
            crit.append(x)
        return {"name": self.name, "variants": self.variants, "criteria": crit, "values": self.values}


def crisp(v: Any, where: str) -> float:
    if isinstance(v, (list, tuple)):
        raise ProblemError(f"{where}: oczekiwano liczby, a jest {list(v)} (dane rozmyte wymagają metody rozmytej)")
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ProblemError(f"{where}: niepoprawna liczba {v!r}") from None


def crisp_matrix(p: Problem) -> List[List[float]]:
    return [[crisp(v, f"{p.variants[i]}/{p.criteria[k].name}") for k, v in enumerate(row)]
            for i, row in enumerate(p.values)]


def ranks(scores: Sequence[float], *, descending: bool = True, tol: float = 1e-9) -> List[int]:
    """Rangi z remisami (1, 2, 2, 4): równe w granicach tolerancji wyniki dostają tę samą rangę."""
    out = []
    for s in scores:
        better = sum(1 for t in scores if (t - s > tol if descending else s - t > tol))
        out.append(better + 1)
    return out


def ranking(variants: Sequence[str], scores: Sequence[float], *, descending: bool = True) -> List[str]:
    order = sorted(range(len(variants)), key=lambda i: (-scores[i] if descending else scores[i], i))
    return [variants[i] for i in order]
