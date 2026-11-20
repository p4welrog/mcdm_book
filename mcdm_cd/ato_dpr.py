"""Metoda ATO-DPR (rozdz. 8.5): Analysis of Trade-Offs for Discrete Decision Making Problems under Risk.

Pierwszy wariant próbny jak w STEM-DPR (8.2)–(8.4). W iteracji decydent porządkuje kryteria wg malejącej
satysfakcji (q₁ … q_n); kandydaci to warianty, których ocena na q_n nie jest zdominowana przez ocenę
wariantu próbnego (8.17); wybór spośród nich przez dominację FSD rozkładów współczynników wymiany
T^{q_n q_k} (8.15)–(8.16), (8.19) dla k = 1 … n−1, a potem przez dominację rozkładów ocen na
kryteriach q_n, q_{n−1}, …, q₁ (8.20).

Dialog jak w STEM-DPR: generator pytań `Ask` (protokół `AtoDecisionMaker`), `ScriptedAtoDM` do testów.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

from .dialog import Ask, drive
from .distribution import Distribution
from .dominance import DARA, IDENTICAL, INARA, afsd_mcdm, stochastic_dominance
from .mcf import Problem

BIG_M = 10000.0          # „duża liczba” M w (8.15), jak w przykładzie 8.5
SD_DEFAULT = {DARA: ("FSD", "SSD", "TSD"), INARA: ("FSD", "SISD", "TISD1", "TISD2")}


@dataclass
class AtoStep:
    """Jeden krok zawężania zbioru ℬ (do raportu)."""
    rule: str                        # "tradeoff" | "rating"
    criteria: Tuple[int, int]        # (q_n, q_k) dla współczynników wymiany; (q_k, q_k) dla ocen
    before: List[int]
    removed: Dict[int, List[Tuple[int, str]]]   # wariant usunięty → [(kto dominuje, typ)]
    after: List[int]


@dataclass
class AtoIteration:
    number: int
    trial: int
    means: List[float]
    ideal: List[float]
    active_variants: List[int]
    order: Optional[List[int]] = None          # q₁ … q_n (od najbardziej satysfakcjonującego)
    candidates: Optional[List[int]] = None     # 𝒜^{(l+1)}
    relaxed: bool = False                       # (8.18): pominięto wcześniejsze ograniczenia
    steps: List[AtoStep] = field(default_factory=list)
    arbitrary: bool = False                     # krok (12): wybór dowolnego wariantu z ℬ


@dataclass
class AtoResult:
    status: str                     # "final" | "cancelled"
    solution: Optional[int]
    iterations: List[AtoIteration] = field(default_factory=list)


class AtoDecisionMaker(Protocol):
    def satisfied(self, state: "AtoDPR", it: AtoIteration) -> Optional[bool]:
        """Czy wariant próbny jest satysfakcjonujący? None = Anuluj."""

    def order(self, state: "AtoDPR", it: AtoIteration) -> Optional[Sequence[int]]:
        """Kryteria od najbardziej do najmniej satysfakcjonującego (ostatnie = do poprawy)."""

    def relax(self, state: "AtoDPR", it: AtoIteration, k: int) -> Optional[bool]:
        """Brak wariantów lepszych na kryterium k w 𝒜^{(l)} — czy pominąć wcześniejsze ograniczenia (8.18)?"""


def tradeoff(state: "AtoDPR", s: int, i: int, p: int, q: int, M: float = BIG_M) -> Distribution:
    """Rozkład T_{is}^{pq} (8.15)–(8.16): zysk na kryterium p na jednostkę straty na q przy zastąpieniu
    wariantu s wariantem i (oceny w orientacji „więcej = lepiej”)."""
    Xsp, Xip = state.d(s, p), state.d(i, p)
    Xsq, Xiq = state.d(s, q), state.d(i, q)
    acc: Dict[float, float] = {}
    for a, pa in Xsp:            # x_{ipk}: obecny wariant, kryterium p
        for b, pb in Xip:        # x_{jpl}: kandydat, kryterium p
            for c, pc in Xsq:    # x_{iqt}: obecny, kryterium q
                for e, pe in Xiq:  # x_{jqv}: kandydat, kryterium q
                    if b > a:
                        t = (b - a) / (c - e) if c > e else M
                    elif b == a:
                        t = 0.0
                    else:
                        t = -M
                    acc[t] = acc.get(t, 0.0) + pa * pb * pc * pe
    vs = sorted(acc)
    return Distribution(tuple(vs), tuple(acc[v] for v in vs))


class AtoDPR:
    def __init__(self, problem: Problem, *, risk: str = DARA, dominances: Optional[Sequence[str]] = None,
                 almost: bool = True, tradeoff_rules: Sequence[str] = ("FSD",), big_m: float = BIG_M):
        """dominances — relacje SD_T zgodne z funkcją użyteczności (domyślnie wg risk: DARA → FSD, SSD, TSD;
        przykład 8.5, klasa U₂: FSD, SSD); almost — AFSD(ε < 0,5) przy pierwszym wariancie próbnym (8.4);
        tradeoff_rules — dominacje rozkładów współczynników wymiany (8.19: FSD; przykład 8.5: FSD i SSD)."""
        if risk not in (DARA, INARA):
            raise ValueError("risk: DARA albo INARA")
        self.p = problem
        self.risk = risk
        self.sd = tuple(dominances) if dominances else SD_DEFAULT[risk]
        bad = set(self.sd) - set(SD_DEFAULT[DARA]) - set(SD_DEFAULT[INARA])
        if bad:
            raise ValueError(f"Nieznane dominacje {sorted(bad)}")
        tb = set(tradeoff_rules) - {"FSD", "SSD"}
        if tb:
            raise ValueError("tradeoff_rules: FSD i/lub SSD")
        self.tradeoff_rules = tuple(tradeoff_rules)
        self.almost = almost
        self.big_m = big_m
        n, m = problem.n, problem.m
        self._dist = [[problem.oriented(i, k) for k in range(m)] for i in range(n)]
        self.dom: List[List[List[Optional[str]]]] = [[[None] * n for _ in range(n)] for _ in range(m)]
        self.eps = [[[0.0] * n for _ in range(n)] for _ in range(m)]
        for k in range(m):
            for i in range(n):
                for j in range(n):
                    if i != j:
                        self.dom[k][i][j] = self._sd(self._dist[i][k], self._dist[j][k])
                        if self.dom[k][i][j] is None and almost:
                            self.eps[k][i][j] = afsd_mcdm(self._dist[i][k], self._dist[j][k])
        self.means = [[problem.dist[i][k].mean() for k in range(m)] for i in range(n)]

    # --- pomocnicze ---
    def d(self, i: int, k: int) -> Distribution:
        return self._dist[i][k]

    def _sd(self, x: Distribution, y: Distribution, rules: Optional[Sequence[str]] = None) -> Optional[str]:
        """Najsilniejsza dominacja z listy rules (domyślnie SD_T), jaka zachodzi dla X nad Y."""
        rules = rules or self.sd
        risk = self.risk if any(r in ("SISD", "TISD1", "TISD2") for r in rules) else DARA
        r = stochastic_dominance(x, y, risk)
        if r.code == IDENTICAL:
            return None
        for name in ("FSD", "SSD", "TSD", "SISD", "TISD1", "TISD2"):
            if name in rules and r.holds.get(name):
                return name
        if risk == DARA and any(x in rules for x in ("SISD", "TISD1", "TISD2")):
            r2 = stochastic_dominance(x, y, INARA)
            for name in ("SISD", "TISD1", "TISD2"):
                if name in rules and r2.holds.get(name):
                    return name
        return None

    def ideal(self, active: Sequence[int]) -> List[float]:
        return [(max if self.p.maximize[k] else min)(self.means[i][k] for i in active) for k in range(self.p.m)]

    def d_index(self, active: Sequence[int]) -> List[List[float]]:
        """d_{jk} (8.3)–(8.4) dla wariantów aktywnych."""
        out = [[0.0] * self.p.m for _ in range(self.p.n)]
        for k in range(self.p.m):
            for j in active:
                s = 0.0
                for i in active:
                    if i == j:
                        continue
                    if self.dom[k][i][j]:
                        s += 1
                    elif 0 < self.eps[k][i][j] < 0.5:
                        s += (0.5 - self.eps[k][i][j]) / 0.5
                out[j][k] = s
        return out

    def first_trial(self) -> Tuple[int, List[List[float]]]:
        act = list(range(self.p.n))
        D = self.d_index(act)
        best = min(act, key=lambda j: (max(D[j]), j))
        return best, D

    # --- krok iteracji (obliczenia) ---
    def candidates(self, s: int, k: int, pool: Sequence[int]) -> List[int]:
        """(8.17)/(8.18): warianty ≠ s z puli, których ocena na k nie jest zdominowana przez ocenę s."""
        return [i for i in pool if i != s and not self.dom[k][s][i]]

    def narrow(self, s: int, order: Sequence[int], B: List[int], it: Optional[AtoIteration] = None) -> Tuple[int, bool]:
        """Kroki (5)–(12): nowy wariant próbny z ℬ; zwraca (wariant, czy wybór był dowolny)."""
        n = self.p.m
        qn = order[-1]
        B = list(B)
        if len(B) == 1:
            return B[0], False
        for kk in range(n - 1):                                          # (6)–(8)
            qk = order[kk]
            T = {i: tradeoff(self, s, i, qn, qk, self.big_m) for i in B}
            removed: Dict[int, List[Tuple[int, str]]] = {}
            for i in B:
                for j in B:
                    if i != j:
                        r = self._sd(T[j], T[i], self.tradeoff_rules)
                        if r:
                            removed.setdefault(i, []).append((j, r))
            after = [i for i in B if i not in removed]
            if it is not None:
                it.steps.append(AtoStep("tradeoff", (qn, qk), list(B), removed, after))
            B = after or B
            if len(B) == 1:
                return B[0], False
        for qk in reversed(order):                                       # (9)–(11)
            removed = {}
            for i in B:
                for j in B:
                    if i != j and self.dom[qk][j][i]:
                        removed.setdefault(i, []).append((j, self.dom[qk][j][i]))
            after = [i for i in B if i not in removed]
            if it is not None:
                it.steps.append(AtoStep("rating", (qk, qk), list(B), removed, after))
            B = after or B
            if len(B) == 1:
                return B[0], False
        return B[0], True                                                # (12)

    # --- dialog ---
    def run(self, dm: AtoDecisionMaker, max_iter: int = 100) -> AtoResult:
        return drive(self.dialog(max_iter), lambda q: getattr(dm, q.kind)(self, *q.args))

    def dialog(self, max_iter: int = 100):
        its: List[AtoIteration] = []
        self.history = its
        s, self.first_d = self.first_trial()
        active = list(range(self.p.n))
        for no in range(1, max_iter + 1):
            it = AtoIteration(no, s, list(self.means[s]), self.ideal(active), list(active))
            its.append(it)
            ans = yield Ask("satisfied", (it,))
            if ans is None:
                return AtoResult("cancelled", None, its)
            if ans:
                return AtoResult("final", s, its)
            while True:
                order = yield Ask("order", (it,))
                if order is None:
                    return AtoResult("cancelled", None, its)
                order = [int(k) for k in order]
                if sorted(order) != list(range(self.p.m)):
                    raise ValueError("Uporządkowanie kryteriów musi zawierać każde kryterium dokładnie raz")
                qn = order[-1]
                cand = self.candidates(s, qn, active)
                relaxed = False
                if not cand:
                    ans = yield Ask("relax", (it, qn))
                    if ans is None:
                        return AtoResult("cancelled", None, its)
                    if not ans:
                        continue
                    cand = self.candidates(s, qn, range(self.p.n))
                    relaxed = True
                    if not cand:
                        return AtoResult("impossible", None, its)
                break
            it.order, it.candidates, it.relaxed = order, cand, relaxed
            s, it.arbitrary = self.narrow(s, order, cand, it)
            active = cand
        raise RuntimeError("Przekroczono max_iter")


class ScriptedAtoDM:
    """Decydent ze scenariusza: lista uporządkowań kryteriów (nazwy lub indeksy) na kolejne iteracje;
    po ich wyczerpaniu akceptuje wariant próbny. relax — odpowiedź na pytanie (8.18)."""

    def __init__(self, orders: Sequence[Sequence], relax: bool = True):
        self.orders = [list(o) for o in orders]
        self.relax_answer = relax

    def satisfied(self, s, it):
        return it.number > len(self.orders)

    def order(self, s, it):
        o = self.orders[it.number - 1]
        return [s.p.criteria.index(k) if isinstance(k, str) else int(k) for k in o]

    def relax(self, s, it, k):
        return self.relax_answer
