"""Metoda ATO-DPR (rozdz. 8.5): Analysis of Trade-Offs for Discrete Decision Making Problems under Risk.

Pierwszy wariant próbny jak w STEM-DPR (8.2)–(8.4). W iteracji decydent porządkuje kryteria według malejącej
satysfakcji (q₁ … q_n); kandydaci to warianty, których ocena na q_n nie jest zdominowana przez ocenę
wariantu próbnego (8.17); wybór spośród nich przez dominację FSD rozkładów współczynników wymiany
T^{q_n q_k} (8.15)–(8.16), (8.19) dla k = 1 … n−1, a potem przez dominację rozkładów ocen na
kryteriach q_n, q_{n−1}, …, q₁ (8.20).

Rozkłady, dominacje i wskaźniki d liczy `mcdm_ryzyko`. Dialog jak w `mcdm_ryzyko`: generator pytań
(`Sesja` krok po kroku, `uruchom` na odpowiedziach z góry); `AtoDPR.run(ScriptedAtoDM(...))` do testów.
Oceny w orientacji „więcej = lepiej” (dla kryterium minimalizowanego ze zmienionym znakiem).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mcdm_ryzyko import Postawa, Problem, RegulaDominacji, Relacja, Rozklad, Sesja, porownaj
from mcdm_ryzyko.dialog import BlednaOdpowiedz, Pytanie, PytanieTakNie
from mcdm_ryzyko.stem_dpr import wskazniki_d

BIG_M = 10000           # „duża liczba” M w (8.15), jak w przykładzie 8.5
SD_DEFAULT = {"DARA": ("FSD", "SSD", "TSD"), "INARA": ("FSD", "SISD", "TISD1", "TISD2")}


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
    means: List[float]                         # wartości oczekiwane wariantu próbnego (jednostki oryginalne)
    ideal: List[float]                         # najlepsze wartości oczekiwane w zbiorze rozpatrywanym
    active_variants: List[int]
    order: Optional[List[int]] = None          # q₁ … q_n (od najbardziej satysfakcjonującego)
    candidates: Optional[List[int]] = None     # 𝒜^{(l+1)}
    relaxed: bool = False                       # (8.18): pominięto wcześniejsze ograniczenia
    steps: List[AtoStep] = field(default_factory=list)
    arbitrary: bool = False                     # krok (12): wybór dowolnego wariantu z ℬ


@dataclass
class AtoResult:
    status: str                     # "final" | "impossible" | "cancelled"
    solution: Optional[int]
    iterations: List[AtoIteration] = field(default_factory=list)


@dataclass
class PytanieSatysfakcjaAto(PytanieTakNie):
    """Czy wariant próbny jest satysfakcjonujący?"""
    iteracja: Optional[AtoIteration] = None


@dataclass
class PytanieKolejnosc(Pytanie):
    """Uporządkowanie kryteriów od najbardziej do najmniej satysfakcjonującego (ostatnie — do poprawy)."""
    iteracja: Optional[AtoIteration] = None
    n: int = 0

    def sprawdz(self, odpowiedz: Any) -> List[int]:
        try:
            order = [int(k) for k in odpowiedz]
        except (TypeError, ValueError):
            raise BlednaOdpowiedz("oczekiwano listy numerów kryteriów") from None
        if sorted(order) != list(range(self.n)):
            raise BlednaOdpowiedz("uporządkowanie musi zawierać każde kryterium dokładnie raz")
        return order


@dataclass
class PytanieOgraniczenia(PytanieTakNie):
    """Brak wariantów lepszych na kryterium k w 𝒜^{(l)} — czy pominąć wcześniejsze ograniczenia (8.18)?"""
    iteracja: Optional[AtoIteration] = None
    k: int = 0


def tradeoff(state: "AtoDPR", s: int, i: int, p: int, q: int, M: float = BIG_M) -> Rozklad:
    """Rozkład T_{is}^{pq} (8.15)–(8.16): zysk na kryterium p na jednostkę straty na q przy zastąpieniu
    wariantu s wariantem i."""
    Xsp, Xip = state.d(s, p).pary(), state.d(i, p).pary()
    Xsq, Xiq = state.d(s, q).pary(), state.d(i, q).pary()
    acc: Dict[Any, Any] = {}
    for a, pa in Xsp:            # obecny wariant, kryterium p
        for b, pb in Xip:        # kandydat, kryterium p
            for c, pc in Xsq:    # obecny, kryterium q
                for e, pe in Xiq:  # kandydat, kryterium q
                    if b > a:
                        t = (b - a) / (c - e) if c > e else M
                    elif b == a:
                        t = 0
                    else:
                        t = -M
                    acc[t] = acc.get(t, 0) + pa * pb * pc * pe
    vs = sorted(acc)
    return Rozklad(vs, [acc[v] for v in vs])


class AtoDPR:
    def __init__(self, problem: Problem, *, risk: str = "DARA", dominances: Optional[Sequence[str]] = None,
                 almost: bool = True, tradeoff_rules: Sequence[str] = ("FSD",), big_m: float = BIG_M):
        """dominances — relacje SD_T zgodne z funkcją użyteczności (domyślnie wg risk: DARA → FSD, SSD, TSD;
        przykład 8.5, klasa U₂: FSD, SSD); almost — AFSD(ε < 0,5) przy pierwszym wariancie próbnym (8.4);
        tradeoff_rules — dominacje rozkładów współczynników wymiany (8.19: FSD; przykład 8.5: FSD i SSD)."""
        if risk not in SD_DEFAULT:
            raise ValueError("risk: DARA albo INARA")
        self.p = problem
        self.risk = risk
        self.sd = tuple(dominances) if dominances else SD_DEFAULT[risk]
        bad = set(self.sd) - set(SD_DEFAULT["DARA"]) - set(SD_DEFAULT["INARA"])
        if bad:
            raise ValueError(f"Nieznane dominacje {sorted(bad)}")
        if set(tradeoff_rules) - {"FSD", "SSD"}:
            raise ValueError("tradeoff_rules: FSD i/lub SSD")
        self.tradeoff_rules = tuple(tradeoff_rules)
        self.almost = almost
        self.big_m = big_m
        postawa = Postawa.AWERSJA if risk == "DARA" else Postawa.SKLONNOSC
        self.regula = RegulaDominacji(postawa=postawa, relacje=tuple(Relacja[r] for r in self.sd), afsd=almost)
        m, n = problem.m, problem.n
        self.dom: List[List[List[Optional[str]]]] = [
            [[None if i == j else self._rel(problem.porownanie(i, j, k)) for j in range(m)] for i in range(m)]
            for k in range(n)]
        mu = problem.wartosci_oczekiwane()
        self.mu = [[float(x) for x in r] for r in mu]                          # orientacja „więcej = lepiej”
        self.means = [[float(problem.kryteria[k].z_orientacji(mu[i][k])) for k in range(n)] for i in range(m)]

    def _rel(self, w) -> Optional[str]:
        r = self.regula.relacja(w)
        return None if r is None else r.value

    # --- pomocnicze ---
    def d(self, i: int, k: int) -> Rozklad:
        return self.p.zorientowana(i, k)

    def ideal(self, active: Sequence[int]) -> List[float]:
        return [float(self.p.kryteria[k].z_orientacji(max(self.mu[i][k] for i in active))) for k in range(self.p.n)]

    def d_index(self, active: Sequence[int]) -> List[List[float]]:
        """d_{jk} (8.3)–(8.4) dla wariantów aktywnych (wiersze: wszystkie warianty)."""
        out = [[0.0] * self.p.n for _ in range(self.p.m)]
        for k in range(self.p.n):
            for j, v in wskazniki_d(self.p, self.regula, list(active), k).items():
                out[j][k] = float(v)
        return out

    def first_trial(self) -> Tuple[int, List[List[float]]]:
        act = list(range(self.p.m))
        D = self.d_index(act)
        best = min(act, key=lambda j: (max(D[j]), j))
        return best, D

    # --- krok iteracji (obliczenia) ---
    def candidates(self, s: int, k: int, pool: Sequence[int]) -> List[int]:
        """(8.17)/(8.18): warianty ≠ s z puli, których ocena na k nie jest zdominowana przez ocenę s."""
        return [i for i in pool if i != s and not self.dom[k][s][i]]

    def _sd_tradeoff(self, x: Rozklad, y: Rozklad) -> Optional[str]:
        if x == y:
            return None
        w = porownaj(x, y)
        for name in ("FSD", "SSD"):
            if name in self.tradeoff_rules and w.zachodzi(Relacja[name]):
                return name
        return None

    def narrow(self, s: int, order: Sequence[int], B: List[int], it: Optional[AtoIteration] = None) -> Tuple[int, bool]:
        """Kroki (5)–(12): nowy wariant próbny z ℬ; zwraca (wariant, czy wybór był dowolny)."""
        n = self.p.n
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
                        r = self._sd_tradeoff(T[j], T[i])
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
    def dialog(self, max_iter: int = 100):
        """Generator pytań (`PytanieSatysfakcjaAto`, `PytanieKolejnosc`, `PytanieOgraniczenia`); zwraca `AtoResult`."""
        its: List[AtoIteration] = []
        self.history = its
        s, self.first_d = self.first_trial()
        active = list(range(self.p.m))
        for no in range(1, max_iter + 1):
            it = AtoIteration(no, s, list(self.means[s]), self.ideal(active), list(active))
            its.append(it)
            if (yield PytanieSatysfakcjaAto("Czy oceny wariantu próbnego są satysfakcjonujące?", iteracja=it)):
                return AtoResult("final", s, its)
            while True:
                order = yield PytanieKolejnosc("Uporządkuj kryteria od najbardziej do najmniej satysfakcjonującej oceny.",
                                               iteracja=it, n=self.p.n)
                qn = order[-1]
                cand = self.candidates(s, qn, active)
                relaxed = False
                if not cand:
                    if not (yield PytanieOgraniczenia("Czy pominąć wcześniejsze ograniczenia (8.18)?", iteracja=it, k=qn)):
                        continue
                    cand = self.candidates(s, qn, range(self.p.m))
                    relaxed = True
                    if not cand:
                        return AtoResult("impossible", None, its)
                break
            it.order, it.candidates, it.relaxed = order, cand, relaxed
            s, it.arbitrary = self.narrow(s, order, cand, it)
            active = cand
        raise RuntimeError("Przekroczono max_iter")

    def run(self, dm: "ScriptedAtoDM", max_iter: int = 100) -> AtoResult:
        sesja = Sesja(self.dialog(max_iter))
        while not sesja.zakonczona:
            q = sesja.pytanie
            if isinstance(q, PytanieSatysfakcjaAto):
                sesja.odpowiedz(dm.satisfied(self, q.iteracja))
            elif isinstance(q, PytanieKolejnosc):
                sesja.odpowiedz(dm.order(self, q.iteracja))
            else:
                sesja.odpowiedz(dm.relax(self, q.iteracja, q.k))
        return sesja.wynik


class ScriptedAtoDM:
    """Decydent ze scenariusza: lista uporządkowań kryteriów (nazwy lub indeksy) na kolejne iteracje;
    po ich wyczerpaniu akceptuje wariant próbny. relax — odpowiedź na pytanie (8.18)."""

    def __init__(self, orders: Sequence[Sequence], relax: bool = True):
        self.orders = [list(o) for o in orders]
        self.relax_answer = relax

    def satisfied(self, s: AtoDPR, it: AtoIteration) -> bool:
        return it.number > len(self.orders)

    def order(self, s: AtoDPR, it: AtoIteration) -> List[int]:
        o = self.orders[it.number - 1]
        return [s.p.indeks_kryterium(k) if isinstance(k, str) else int(k) for k in o]

    def relax(self, s: AtoDPR, it: AtoIteration, k: int) -> bool:
        return self.relax_answer
