"""Metoda STEM-DPR (odpowiednik M_Stem.bas i M_Util_Stem.bas z MCDM 1.00).

Dialog z decydentem przez obiekt z metodami (protokół `StemDecisionMaker`); do testów i pracy
wsadowej służy `ScriptedStemDM`, do pracy w konsoli `ConsoleStemDM`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Sequence

from .dominance import DARA, IDENTICAL, afsd_mcdm, stochastic_dominance
from .mcf import Problem
from .dialog import Ask, drive


@dataclass
class StemIteration:
    number: int
    trial: int                     # indeks wariantu próbnego
    means: List[float]             # średnie wariantu próbnego wg kryteriów
    d: List[float]                 # współczynniki d wariantu próbnego wg kryteriów
    ideal: List[float]
    active_criteria: List[bool]
    active_variants: List[int]
    relaxed: Optional[int] = None  # kryterium wskazane jako satysfakcjonujące
    threshold: Optional[float] = None


class StemDecisionMaker(Protocol):
    def satisfied(self, state: "StemDPR", it: StemIteration) -> Optional[bool]:
        """Czy wariant próbny jest satysfakcjonujący? None = Anuluj."""

    def some_criterion_satisfactory(self, state: "StemDPR", it: StemIteration) -> Optional[bool]:
        """Czy dla przynajmniej jednego kryterium ocena wariantu próbnego jest satysfakcjonująca?"""

    def choose_criterion(self, state: "StemDPR", it: StemIteration, candidates: List[int]) -> Optional[int]:
        """Kryterium, względem którego ocena jest satysfakcjonująca (z aktywnych). None = Anuluj."""

    def threshold(self, state: "StemDPR", it: StemIteration, k: int, default: float) -> float:
        """Minimalna (max) / maksymalna (min) akceptowana wartość średniej; podpowiedź = wartość idealna."""


@dataclass
class StemResult:
    status: str                    # "final" | "cancelled" | "impossible"
    solution: Optional[int]
    iterations: List[StemIteration] = field(default_factory=list)


class StemDPR:
    def __init__(self, problem: Problem, *, orient_min: bool = True):
        """orient_min=False odtwarza MCDM 1.00, które bada dominacje na surowych wartościach
        także dla kryteriów minimalizowanych (kierunek kryterium wpływa tylko na średnie)."""
        self.p = problem
        n, m = problem.n, problem.m
        # dom[k][i][j]: kod dominacji wariantu i nad j (7/6/4/128) albo stopień AFSD (0 < ε < 0,5)
        self.dom = [[[0.0] * n for _ in range(n)] for _ in range(m)]
        for k in range(m):
            for i in range(n):
                for j in range(n):
                    if orient_min:
                        x, y = problem.oriented(i, k), problem.oriented(j, k)
                    else:
                        x, y = problem.dist[i][k], problem.dist[j][k]
                    c = stochastic_dominance(x, y, DARA).code
                    self.dom[k][i][j] = float(c) if c else afsd_mcdm(x, y)
        self.means = [[problem.dist[i][k].mean() for k in range(m)] for i in range(n)]
        pick = lambda k: max if problem.maximize[k] else min
        self.ideal = [pick(k)(self.means[i][k] for i in range(n)) for k in range(m)]
        self.active_variant = [True] * n
        self.active_criterion = [True] * m
        self.d = [[0.0] * m for _ in range(n)]

    # --- obliczenia ---
    def _d(self, i: int, k: int) -> float:
        s = 0.0
        for j in range(self.p.n):
            if not self.active_variant[j]:
                continue
            v = self.dom[k][j][i]
            if v in (7.0, 6.0, 4.0):
                s += 1
            elif 0 < v < 0.5:
                s += (0.5 - v) / 0.5
        return s

    def trial_variant(self) -> int:
        """Wariant próbny: min po wariantach aktywnych z max po kryteriach aktywnych współczynnika d."""
        best, arg = float(self.p.n), 0
        for i in range(self.p.n):
            if not self.active_variant[i]:
                continue
            dmax = 0.0
            for k in range(self.p.m):
                self.d[i][k] = self._d(i, k)
                if self.active_criterion[k] and self.d[i][k] > dmax:
                    dmax = self.d[i][k]
            if dmax < best:
                best, arg = dmax, i
        return arg

    def reduce(self, k: int, value: float) -> None:
        for i in range(self.p.n):
            m = self.means[i][k]
            if (self.p.maximize[k] and m < value) or (not self.p.maximize[k] and m > value):
                self.active_variant[i] = False
        self.active_criterion[k] = False
        if not any(self.active_criterion):
            self.active_criterion = [True] * self.p.m

    # --- dialog ---
    def run(self, dm: StemDecisionMaker, max_iter: int = 100) -> StemResult:
        """Przebieg dialogu z decydentem `dm` (wywołania blokujące)."""
        return drive(self.dialog(max_iter), lambda q: getattr(dm, q.kind)(self, *q.args))

    def dialog(self, max_iter: int = 100):
        """Dialog jako generator: zwraca kolejne pytania `Ask`, przyjmuje odpowiedzi przez send().
        Wynik (StemResult) jest wartością StopIteration. Używany przez interfejs widżetowy."""
        its: List[StemIteration] = []
        for no in range(1, max_iter + 1):
            t = self.trial_variant()
            it = StemIteration(no, t, list(self.means[t]), list(self.d[t]), list(self.ideal),
                               list(self.active_criterion),
                               [i for i in range(self.p.n) if self.active_variant[i]])
            its.append(it)
            ans = yield Ask("satisfied", (it,))
            if ans is None:
                return StemResult("cancelled", None, its)
            if ans:
                return StemResult("final", t, its)
            ans = yield Ask("some_criterion_satisfactory", (it,))
            if ans is None:
                return StemResult("cancelled", None, its)
            if not ans:
                return StemResult("impossible", None, its)
            cand = [k for k in range(self.p.m) if self.active_criterion[k]]
            k = yield Ask("choose_criterion", (it, cand))
            if k is None:
                return StemResult("cancelled", None, its)
            if k not in cand:
                raise ValueError(f"Kryterium {k} nie jest aktywne")
            v = yield Ask("threshold", (it, k, self.ideal[k]))
            it.relaxed, it.threshold = k, v
            self.reduce(k, v)
        raise RuntimeError("Przekroczono max_iter")


class ScriptedStemDM:
    """Decydent ze scenariusza: lista kroków (kryterium, próg) i ewentualnie liczba iteracji
    zakończona akceptacją. Kryterium i próg mogą być podane nazwą / None (= wartość idealna)."""

    def __init__(self, steps: Sequence[tuple], accept_after: Optional[int] = None):
        self.steps = list(steps)
        self.accept_after = accept_after if accept_after is not None else len(self.steps) + 1
        self.log: List[str] = []

    def satisfied(self, s, it):
        return it.number >= self.accept_after

    def some_criterion_satisfactory(self, s, it):
        return it.number - 1 < len(self.steps)

    def choose_criterion(self, s, it, cand):
        k = self.steps[it.number - 1][0]
        return s.p.criteria.index(k) if isinstance(k, str) else k

    def threshold(self, s, it, k, default):
        v = self.steps[it.number - 1][1]
        return default if v is None else v


class ConsoleStemDM:
    """Prosty dialog w terminalu."""

    def _yn(self, q):
        while True:
            a = input(q + " [t/n/a] ").strip().lower()
            if a in ("t", "n", "a"):
                return None if a == "a" else a == "t"

    def satisfied(self, s, it):
        p = s.p
        print(f"\nIteracja {it.number}: wariant próbny {p.variants[it.trial]}")
        for k in range(p.m):
            print(f"  {p.criteria[k]:>10}: średnia {it.means[k]:.4g}  d {it.d[k]:.4g}  "
                  f"idealna {it.ideal[k]:.4g}  {'aktywne' if it.active_criteria[k] else ''}")
        print("  Warianty rozpatrywane:", ", ".join(p.variants[i] for i in it.active_variants))
        return self._yn("Czy otrzymane rozwiązanie jest satysfakcjonujące?")

    def some_criterion_satisfactory(self, s, it):
        return self._yn("Czy dla przynajmniej jednego kryterium ocena wariantu próbnego jest satysfakcjonująca?")

    def choose_criterion(self, s, it, cand):
        names = [s.p.criteria[k] for k in cand]
        a = input(f"Kryterium ({', '.join(names)}; puste = anuluj): ").strip()
        return s.p.criteria.index(a) if a in names else None

    def threshold(self, s, it, k, default):
        a = input(f"Akceptowana wartość średniej dla {s.p.criteria[k]} [{default:.6g}]: ").strip().replace(",", ".")
        return float(a) if a else default
