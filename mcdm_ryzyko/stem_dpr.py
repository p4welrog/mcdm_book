"""Metoda STEM-DPR (rozdz. 8.3, wzory 8.1-8.5, rys. 8.2).

W każdej iteracji l wyznaczany jest wariant próbny a^s minimalizujący
max_{k∈𝒦} d_jk^(l) (8.2), gdzie d_jk^(l) = Σ_{i∈I^(l)} φ_ij^k (8.3), a
φ_ij^k = 1, gdy F_ik SD_T F_jk; (0,5 − ε_ij^k)/0,5, gdy ε_ij^k < 0,5;
0 w pozostałych przypadkach (8.4). Decydent ocenia wariant próbny; jeśli nie
jest satysfakcjonujący, wskazuje kryterium z oceną satysfakcjonującą i próg
δ_k, co zawęża zbiór wariantów (8.5) i usuwa k z 𝒦.

Wszystkie wartości w dialogu (μ, wektor idealny, δ_k) są w orientacji
„wyższe lepsze” (założenie z rozdz. 8.2); dla kryterium minimalizowanego to
wartości ze zmienionym znakiem, jak w rozdz. 10 (DECYZJE.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .dialog import BlednaOdpowiedz, Pytanie, PytanieTakNie, Wynik
from .dominacje.regula import RegulaDominacji
from .parametry import Parametr
from .problem import Problem

_POL = Fraction(1, 2)


def phi(problem: Problem, regula: RegulaDominacji, i: int, j: int, k: int):
    """Współczynnik φ_ij^k (wzór 8.4): przewaga a^i nad a^j względem f_k."""
    if i == j:
        return 0
    w = problem.porownanie(i, j, k)
    if regula.dominuje(w):
        return 1
    if regula.afsd and w.eps_afsd is not None and w.eps_afsd < _POL - problem.tolerancja:
        return (_POL - w.eps_afsd) / _POL
    return 0


def wskazniki_d(problem: Problem, regula: RegulaDominacji, indeksy: Sequence[int], k: int) -> Dict[int, Any]:
    """d_jk = Σ_{i∈I} φ_ij^k dla j ∈ I (wzór 8.3)."""
    return {j: sum((phi(problem, regula, i, j, k) for i in indeksy), 0) for j in indeksy}


@dataclass(frozen=True)
class Prog:
    """Odpowiedź z kroku 6: kryterium ``k`` i minimalna akceptowalna wartość oczekiwana ``delta``.

    ``delta`` w orientacji „wyższe lepsze” (dla kryterium minimalizowanego:
    minus maksymalna akceptowalna średnia).
    """

    k: int
    delta: Any


@dataclass
class StanStem:
    """Dane z iteracji l prezentowane decydentowi (krok 2) i wyniki obliczeń."""

    iteracja: int
    warianty: Tuple[int, ...]
    aktywne: Tuple[int, ...]
    d: Dict[int, Tuple]
    maks_d: Dict[int, Any]
    proba: int
    remis: Tuple[int, ...]
    mu_proby: Tuple
    idealny: Tuple
    dodatkowe: Dict[Tuple[int, Parametr], Any] = field(default_factory=dict)

    @property
    def d_proby(self) -> Tuple:
        """d_sk^(l) dla k = 1, …, n."""
        return self.d[self.proba]


@dataclass
class PytanieInformacje(Pytanie):
    """Krok 3: czy informacje są wystarczające.

    Odpowiedź: ``True`` (wystarczające) albo lista par (k, :class:`Parametr`)
    z parametrami wariantu próbnego, które należy dodatkowo obliczyć.
    """

    stan: Optional[StanStem] = None
    n: int = 0

    def sprawdz(self, odpowiedz):
        if odpowiedz is True:
            return True
        try:
            pary = [(int(k), p) for k, p in odpowiedz]
        except (TypeError, ValueError):
            raise BlednaOdpowiedz("oczekiwano True albo listy par (k, Parametr)") from None
        for k, p in pary:
            if not 0 <= k < self.n or not isinstance(p, Parametr):
                raise BlednaOdpowiedz(f"niepoprawna para ({k!r}, {p!r})")
        if not pary:
            raise BlednaOdpowiedz("pusta lista parametrów")
        return tuple(pary)


@dataclass
class PytanieSatysfakcja(PytanieTakNie):
    """Krok 4: czy oceny wariantu próbnego są satysfakcjonujące."""

    stan: Optional[StanStem] = None


@dataclass
class PytanieKryteriumSatysfakcjonujace(PytanieTakNie):
    """Krok 5: czy ocena względem przynajmniej jednego kryterium jest satysfakcjonująca."""

    stan: Optional[StanStem] = None


@dataclass
class PytanieProg(Pytanie):
    """Krok 6: wskazanie kryterium i progu δ_k (odpowiedź: :class:`Prog`)."""

    stan: Optional[StanStem] = None
    mu: Optional[List[List[Any]]] = None
    tolerancja: float = 1e-6

    def sprawdz(self, odpowiedz):
        if not isinstance(odpowiedz, Prog):
            raise BlednaOdpowiedz("oczekiwano obiektu Prog(k, delta)")
        n = len(self.stan.idealny)
        if not 0 <= odpowiedz.k < n:
            raise BlednaOdpowiedz(f"numer kryterium spoza zakresu 0…{n - 1}")
        if not any(self.mu[j][odpowiedz.k] >= odpowiedz.delta - self.tolerancja for j in self.stan.warianty):
            raise BlednaOdpowiedz("żaden wariant nie spełnia warunku μ_jk ≥ δ_k")
        return odpowiedz


@dataclass
class WynikStem(Wynik):
    """Wynik STEM-DPR; ``historia`` to lista :class:`StanStem` kolejnych iteracji."""


class StemDpr:
    """Procedura STEM-DPR dla problemu ``problem`` i reguły SD_T ``regula``.

    :param pytaj_o_informacje: czy zadawać pytanie z kroku 3 (program MCDM go
        nie zadaje — instrukcja, rozdz. 3.2; przykład 8.1 tak).

    >>> from mcdm_ryzyko.dialog import uruchom
    >>> # wynik = uruchom(StemDpr(problem, regula).przebieg(), [True, True])
    """

    def __init__(self, problem: Problem, regula: Optional[RegulaDominacji] = None, *, pytaj_o_informacje: bool = True):
        self.problem = problem
        self.regula = regula or RegulaDominacji.awersja()
        self.pytaj_o_informacje = pytaj_o_informacje

    # --- obliczenia ----------------------------------------------------------

    def stan_iteracji(self, l: int, warianty: Sequence[int], aktywne: Sequence[int]) -> StanStem:
        """Krok 1 iteracji: wskaźniki d, wariant próbny (8.2), wektor idealny (8.1)."""
        p = self.problem
        warianty = tuple(warianty)
        aktywne = tuple(aktywne)
        mu = p.wartosci_oczekiwane()
        d_k = [wskazniki_d(p, self.regula, warianty, k) for k in range(p.n)]
        d = {j: tuple(d_k[k][j] for k in range(p.n)) for j in warianty}
        maks_d = {j: max(d[j][k] for k in aktywne) for j in warianty}
        najmniejsze = min(maks_d.values())
        remis = tuple(j for j in warianty if maks_d[j] <= najmniejsze + p.tolerancja)
        s = remis[0]  # przy remisie wariant o najniższym numerze (DECYZJE.md)
        return StanStem(
            iteracja=l,
            warianty=warianty,
            aktywne=aktywne,
            d=d,
            maks_d=maks_d,
            proba=s,
            remis=remis,
            mu_proby=tuple(mu[s]),
            idealny=tuple(max(mu[j][k] for j in warianty) for k in range(p.n)),
        )

    # --- dialog --------------------------------------------------------------

    def przebieg(self):
        """Generator dialogu (zob. :mod:`mcdm_ryzyko.dialog`); zwraca :class:`WynikStem`."""
        p = self.problem
        mu = p.wartosci_oczekiwane()
        warianty = tuple(range(p.m))
        wszystkie = tuple(range(p.n))
        aktywne = wszystkie
        historia: List[StanStem] = []
        l = 1
        while True:
            stan = self.stan_iteracji(l, warianty, aktywne)
            historia.append(stan)
            if self.pytaj_o_informacje:
                while True:
                    odp = yield PytanieInformacje("Czy przedstawione informacje są wystarczające?", stan=stan, n=p.n)
                    if odp is True:
                        break
                    for k, par in odp:
                        stan.dodatkowe[(k, par)] = par.wartosc(p.zorientowana(stan.proba, k))
            if (yield PytanieSatysfakcja("Czy oceny wariantu próbnego są satysfakcjonujące?", stan=stan)):
                return WynikStem("zaakceptowano", stan.proba, historia)
            if not (yield PytanieKryteriumSatysfakcjonujace(
                "Czy ocena wariantu próbnego względem przynajmniej jednego kryterium jest satysfakcjonująca?",
                stan=stan,
            )):
                return WynikStem("brak_rozwiazania", None, historia)
            prog = yield PytanieProg(
                "Wskaż kryterium o satysfakcjonującej ocenie i minimalną akceptowalną wartość oczekiwaną δ_k.",
                stan=stan, mu=mu, tolerancja=p.tolerancja,
            )
            warianty = tuple(j for j in warianty if mu[j][prog.k] >= prog.delta - p.tolerancja)  # (8.5)
            aktywne = tuple(k for k in aktywne if k != prog.k)
            if not aktywne:
                aktywne = wszystkie
            l += 1
