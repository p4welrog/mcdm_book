"""Metoda INSDECM (rozdz. 8.4, wzory 8.6-8.12, rys. 8.3).

Decydent ogląda macierz możliwości P^(l) (wartości pesymistyczne
i optymistyczne wybranych parametrów rozkładów ocen w zbiorze 𝒜^(l), wzory
8.6-8.7) i formułuje dodatkowe warunki na parametry, które zawężają zbiór
wariantów. Warunek niespójny z regułami dominacji stochastycznej (8.8) — gdy
odrzucany wariant a^i dominuje pozostawiany a^j w sensie SD_T — jest
wyjaśniany z decydentem w kolejności rosnącego ε_ij^k (8.9): podtrzymanie,
osłabienie albo zaostrzenie warunku. Gdy wartości pesymistyczne są
satysfakcjonujące, decydent wybiera rozwiązanie z macierzy R^(l).

Wartości parametrów są liczone na rozkładach w orientacji „wyższe lepsze”
(DECYZJE.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .dialog import BlednaOdpowiedz, Pytanie, PytanieTakNie, Wynik
from .dominacje.regula import RegulaDominacji
from .parametry import Parametr, RodzajParametru
from .problem import Problem
from .rozklad import Rozklad

WARTOSC_OCZEKIWANA = Parametr(RodzajParametru.WARTOSC_OCZEKIWANA)

#: Liczba przedziałów ρ w (8.12) proponowana na początek (s. 165: „np. na poziomie 10”).
RHO_DOMYSLNE = 10


# --- warunki i macierze -------------------------------------------------------

@dataclass(frozen=True)
class Warunek:
    """Dodatkowy warunek decydenta dla kryterium ``k``.

    Dla parametru „wyższe lepsze” (Q_1): v ≥ granica (v > granica, gdy ``ostry``);
    dla parametru „niższe lepsze” (Q_2): v ≤ granica (v < granica).
    """

    k: int
    parametr: Parametr
    granica: Any
    ostry: bool = False

    def spelnia(self, v, tolerancja: float = 1e-9) -> bool:
        if self.parametr.wyzsze_lepsze:
            return v > self.granica + tolerancja if self.ostry else v >= self.granica - tolerancja
        return v < self.granica - tolerancja if self.ostry else v <= self.granica + tolerancja

    def opis(self, nazwa_kryterium: str = "") -> str:
        znak = (">" if self.ostry else "≥") if self.parametr.wyzsze_lepsze else ("<" if self.ostry else "≤")
        kr = f" dla {nazwa_kryterium}" if nazwa_kryterium else ""
        return f"{self.parametr.opis()}{kr} {znak} {self.granica}"


@dataclass(frozen=True)
class MacierzMozliwosci:
    """Macierz P^(l): kolumny (k, parametr), wartości pesymistyczne i optymistyczne."""

    warianty: Tuple[int, ...]
    kolumny: Tuple[Tuple[int, Parametr], ...]
    pesymistyczne: Tuple
    optymistyczne: Tuple


@dataclass(frozen=True)
class MacierzRozwiazan:
    """Macierz R^(l): wartości parametrów dla każdego wariantu z 𝒜^(l)."""

    warianty: Tuple[int, ...]
    kolumny: Tuple[Tuple[int, Parametr], ...]
    wiersze: Tuple[Tuple, ...]


def _kolumny(parametry: Dict[int, Sequence[Parametr]]) -> Tuple[Tuple[int, Parametr], ...]:
    return tuple((k, p) for k in sorted(parametry) for p in parametry[k])


def wartosc_parametru(problem: Problem, i: int, k: int, p: Parametr):
    """v_ip: wartość parametru ``p`` dla rozkładu oceny a^i względem f_k."""
    return p.wartosc(problem.zorientowana(i, k))


def macierz_mozliwosci(problem: Problem, parametry: Dict[int, Sequence[Parametr]], warianty: Sequence[int]) -> MacierzMozliwosci:
    """P^(l) według wzorów 8.6-8.7 dla zbioru ``warianty``."""
    kol = _kolumny(parametry)
    warianty = tuple(warianty)
    pes, opt = [], []
    for k, p in kol:
        v = [wartosc_parametru(problem, i, k, p) for i in warianty]
        pes.append(p.pesymistyczna(v) if v else None)
        opt.append(p.optymistyczna(v) if v else None)
    return MacierzMozliwosci(warianty, kol, tuple(pes), tuple(opt))


def macierz_rozwiazan(problem: Problem, parametry: Dict[int, Sequence[Parametr]], warianty: Sequence[int]) -> MacierzRozwiazan:
    """R^(l): wiersze wartości parametrów dla wariantów z ``warianty``."""
    kol = _kolumny(parametry)
    warianty = tuple(warianty)
    wiersze = tuple(tuple(wartosc_parametru(problem, i, k, p) for k, p in kol) for i in warianty)
    return MacierzRozwiazan(warianty, kol, wiersze)


# --- niespójności (kroki 7-12) ---------------------------------------------------

def zbior_niespojnosci(problem: Problem, regula: RegulaDominacji, k: int, przed: Sequence[int], po: Sequence[int]) -> List[Tuple[int, int]]:
    """𝒩^(l) (8.8): pary (a^i, a^j), a^i ∈ 𝒜^(l) \\ 𝒜^(l+1), a^j ∈ 𝒜^(l+1), F_ik SD_T F_jk."""
    po_set = set(po)
    odrzucone = [i for i in przed if i not in po_set]
    return [(i, j) for i in odrzucone for j in po if regula.dominuje(problem.porownanie(i, j, k))]


def eps_niespojnosci(problem: Problem, i: int, j: int, k: int):
    """ε_ij^k: siła dominacji a^i nad a^j (krok 8; DECYZJE.md).

    Liczone jak ε_1 Leshno, Levy (tabl. 1.2): pole, na którym F_ik > F_jk,
    przez ‖F_ik − F_jk‖; 0 przy FSD a^i nad a^j, 1 przy FSD a^j nad a^i,
    zgodnie z opisem na s. 165 (wzór 8.9 w druku daje kierunek odwrotny).
    """
    e = problem.porownanie(i, j, k).eps_afsd
    return 0 if e is None else e


@dataclass(frozen=True)
class PrezentacjaRozkladow:
    """Dane z kroku 10: punkty s_r (8.12) i prawdopodobieństwa dla obu wariantów."""

    i: int
    j: int
    k: int
    punkty: Tuple
    wartosci_i: Tuple
    wartosci_j: Tuple
    dekumulanta: bool
    rho: int


def prezentacja_rozkladow(Fi: Rozklad, Fj: Rozklad, rho: int = RHO_DOMYSLNE, *, dekumulanta: bool = True, i: int = 0, j: int = 0, k: int = 0) -> PrezentacjaRozkladow:
    """Wzory 8.11-8.12: ρ + 1 równo odległych punktów na [min(α_i, α_j), max(β_i, β_j)].

    Dla każdego punktu P(X ≥ s_r) (``dekumulanta=True``) albo P(X ≤ s_r).
    """
    if rho < 1:
        raise ValueError("liczba przedziałów ρ musi być dodatnia")
    a = min(Fi.minimum(), Fj.minimum())
    b = max(Fi.maksimum(), Fj.maksimum())
    punkty = tuple(a + r * (b - a) / rho for r in range(rho + 1))
    f = (lambda F, s: F.dekumulanta(s)) if dekumulanta else (lambda F, s: F.dystrybuanta(s))
    return PrezentacjaRozkladow(
        i, j, k, punkty,
        tuple(f(Fi, s) for s in punkty),
        tuple(f(Fj, s) for s in punkty),
        dekumulanta, rho,
    )


def propozycje_modyfikacji(problem: Problem, warunek: Warunek, i: int, j: int, oslabienie: bool) -> List[Warunek]:
    """Propozycje z kroku 12 dla pary (a^i odrzucony, a^j przyjęty).

    Osłabienie — oba warianty spełniają warunek; zaostrzenie — oba go nie spełniają.
    Zawsze: zmiana granicy (osłabienie: granica = v_i; zaostrzenie: warunek ostry
    z granicą v_j). Dla prawdopodobieństw P(X ≥ s), P(X ≤ s) dodatkowo zmiana progu
    s na najbliższą wartość z nośników obu rozkładów, przy której cel jest
    osiągnięty (instrukcja MCDM, rozdz. 4.2.5; DECYZJE.md).
    """
    k, p = warunek.k, warunek.parametr
    vi = wartosc_parametru(problem, i, k, p)
    vj = wartosc_parametru(problem, j, k, p)
    wynik = []
    if oslabienie:
        wynik.append(replace(warunek, granica=vi, ostry=False))
    else:
        wynik.append(replace(warunek, granica=vj, ostry=True))
    if p.rodzaj in (RodzajParametru.P_NIE_MNIEJ, RodzajParametru.P_NIE_WIECEJ):
        Fi, Fj = problem.zorientowana(i, k), problem.zorientowana(j, k)
        kandydaci = []
        for c in Fi.nosnik_wspolny(Fj):
            if c == p.prog:
                continue
            nowy = replace(warunek, parametr=replace(p, prog=c))
            si = nowy.spelnia(nowy.parametr.wartosc(Fi))
            sj = nowy.spelnia(nowy.parametr.wartosc(Fj))
            if (si and sj) if oslabienie else (not si and not sj):
                kandydaci.append((abs(c - p.prog), c, nowy))
        if kandydaci:
            wynik.append(min(kandydaci, key=lambda t: (t[0], t[1]))[2])
    return wynik


# --- pytania ---------------------------------------------------------------------

@dataclass(frozen=True)
class ZmianaPrezentacji:
    """Odpowiedź w kroku 10: zmiana liczby przedziałów ρ lub rodzaju prezentacji."""

    rho: int = RHO_DOMYSLNE
    dekumulanta: bool = True


PODTRZYMAJ = "podtrzymaj"
OSLAB = "oslab"
ZAOSTRZ = "zaostrz"


@dataclass
class PytanieParametry(Pytanie):
    """Wybór parametrów prezentowanych w macierzy możliwości.

    Odpowiedź: słownik ``{k: [Parametr, ...]}``. Kryterium pominięte w słowniku
    dostaje wartość oczekiwaną; pusta lista oznacza brak kolumn dla kryterium.
    """

    n: int = 0
    biezace: Optional[Dict[int, Tuple[Parametr, ...]]] = None

    def sprawdz(self, odpowiedz):
        if not isinstance(odpowiedz, dict):
            raise BlednaOdpowiedz("oczekiwano słownika {k: [Parametr, ...]}")
        wynik = {}
        for k in range(self.n):
            lista = odpowiedz.get(k, [WARTOSC_OCZEKIWANA])
            if not all(isinstance(p, Parametr) for p in lista):
                raise BlednaOdpowiedz(f"kryterium {k}: oczekiwano listy obiektów Parametr")
            unikalne = []
            for p in lista:
                if p not in unikalne:
                    unikalne.append(p)
            wynik[k] = tuple(unikalne)
        if set(odpowiedz) - set(range(self.n)):
            raise BlednaOdpowiedz("numery kryteriów spoza zakresu")
        if not any(wynik.values()):
            raise BlednaOdpowiedz("trzeba wybrać co najmniej jeden parametr")
        return wynik


@dataclass
class PytanieDaneWystarczajace(PytanieTakNie):
    """Krok 2: czy decydent jest usatysfakcjonowany zaprezentowanymi danymi."""

    macierz: Optional[MacierzMozliwosci] = None
    iteracja: int = 0


@dataclass
class PytaniePesymistyczne(PytanieTakNie):
    """Krok 3: czy wartości pesymistyczne są satysfakcjonujące."""

    macierz: Optional[MacierzMozliwosci] = None
    iteracja: int = 0


@dataclass
class PytanieWarunek(Pytanie):
    """Krok 4: kryterium i dodatkowy warunek (odpowiedź: :class:`Warunek`)."""

    macierz: Optional[MacierzMozliwosci] = None
    problem: Optional[Problem] = None

    def sprawdz(self, odpowiedz):
        if not isinstance(odpowiedz, Warunek):
            raise BlednaOdpowiedz("oczekiwano obiektu Warunek")
        if not 0 <= odpowiedz.k < self.problem.n:
            raise BlednaOdpowiedz("numer kryterium spoza zakresu")
        if not any(odpowiedz.spelnia(wartosc_parametru(self.problem, i, odpowiedz.k, odpowiedz.parametr))
                   for i in self.macierz.warianty):
            raise BlednaOdpowiedz("żaden wariant nie spełnia warunku")
        return odpowiedz


@dataclass
class PytanieAkceptacjaZmian(PytanieTakNie):
    """Krok 6: macierze P^(l) i P^(l+1); czy decydent akceptuje skutki warunku."""

    przed: Optional[MacierzMozliwosci] = None
    po: Optional[MacierzMozliwosci] = None
    warunek: Optional[Warunek] = None


@dataclass
class PytanieNiespojnosc(Pytanie):
    """Krok 10: para niespójna; odpowiedź: PODTRZYMAJ, OSLAB, ZAOSTRZ albo :class:`ZmianaPrezentacji`."""

    warunek: Optional[Warunek] = None
    eps: Any = None
    prezentacja: Optional[PrezentacjaRozkladow] = None
    pozostale: Tuple[Tuple[int, int], ...] = ()

    def sprawdz(self, odpowiedz):
        if isinstance(odpowiedz, ZmianaPrezentacji):
            if odpowiedz.rho < 1:
                raise BlednaOdpowiedz("ρ musi być dodatnie")
            return odpowiedz
        if odpowiedz not in (PODTRZYMAJ, OSLAB, ZAOSTRZ):
            raise BlednaOdpowiedz("oczekiwano 'podtrzymaj', 'oslab', 'zaostrz' albo ZmianaPrezentacji")
        return odpowiedz


@dataclass
class PytaniePropozycja(Pytanie):
    """Krok 12: wybór jednej z propozycji (indeks) albo None (odrzucenie)."""

    propozycje: Tuple[Warunek, ...] = ()
    oslabienie: bool = True

    def sprawdz(self, odpowiedz):
        if odpowiedz is None:
            return None
        if not isinstance(odpowiedz, int) or not 0 <= odpowiedz < len(self.propozycje):
            raise BlednaOdpowiedz("oczekiwano numeru propozycji albo None")
        return odpowiedz


@dataclass
class PytanieRozwiazanie(Pytanie):
    """Krok 13: macierz R^(l); odpowiedź: indeks wybranego wariantu albo None."""

    macierz: Optional[MacierzRozwiazan] = None

    def sprawdz(self, odpowiedz):
        if odpowiedz is None:
            return None
        if odpowiedz not in self.macierz.warianty:
            raise BlednaOdpowiedz("wariant spoza macierzy rozwiązań")
        return odpowiedz


# --- procedura ---------------------------------------------------------------------

@dataclass
class StanInsdecm:
    """Zapis zakończonej iteracji: zbiory, przyjęty warunek i niespójności."""

    iteracja: int
    przed: Tuple[int, ...]
    po: Tuple[int, ...]
    warunek: Warunek
    niespojnosci: Tuple[Tuple[int, int], ...]
    podtrzymane: Tuple[Tuple[int, int], ...] = ()


@dataclass
class WynikInsdecm(Wynik):
    """Wynik INSDECM; ``historia`` — lista :class:`StanInsdecm`, ``warunki`` — przyjęte warunki."""

    warunki: List[Warunek] = field(default_factory=list)
    warianty: Tuple[int, ...] = ()


class Insdecm:
    """Procedura INSDECM dla ``problem`` z regułą SD_T ``regula``."""

    def __init__(self, problem: Problem, regula: Optional[RegulaDominacji] = None):
        self.problem = problem
        self.regula = regula or RegulaDominacji.awersja()

    def przebieg(self):
        """Generator dialogu (zob. :mod:`mcdm_ryzyko.dialog`); zwraca :class:`WynikInsdecm`."""
        p = self.problem
        historia: List[StanInsdecm] = []
        warunki: List[Warunek] = []
        l = 1
        A: Tuple[int, ...] = tuple(range(p.m))
        parametry = yield PytanieParametry("Podaj parametry rozkładów ocen prezentowane w dialogu.", n=p.n)
        while True:
            # krok 1-2
            P = macierz_mozliwosci(p, parametry, A)
            if not (yield PytanieDaneWystarczajace("Czy zaprezentowane dane są wystarczające?", macierz=P, iteracja=l)):
                parametry = yield PytanieParametry("Podaj parametry rozkładów ocen prezentowane w dialogu.", n=p.n, biezace=parametry)
                continue
            # krok 3
            if (yield PytaniePesymistyczne("Czy wartości pesymistyczne są satysfakcjonujące?", macierz=P, iteracja=l)):
                R = macierz_rozwiazan(p, parametry, A)
                wybor = yield PytanieRozwiazanie("Czy akceptujesz jedno z proponowanych rozwiązań?", macierz=R)
                if wybor is not None:
                    return WynikInsdecm("zaakceptowano", wybor, historia, warunki, A)
                continue  # krok 2
            # krok 4
            warunek = yield PytanieWarunek("Wskaż kryterium i sformułuj dodatkowy warunek.", macierz=P, problem=p)
            while True:
                # krok 5-6
                po = tuple(i for i in A if warunek.spelnia(wartosc_parametru(p, i, warunek.k, warunek.parametr)))
                P_po = macierz_mozliwosci(p, parametry, po)
                if not (yield PytanieAkceptacjaZmian("Czy akceptujesz rezultaty uwzględnienia warunku?",
                                                      przed=P, po=P_po, warunek=warunek)):
                    break  # krok 2
                # krok 7-8
                k = warunek.k
                N = zbior_niespojnosci(p, self.regula, k, A, po)
                N_poczatkowe = tuple(N)
                eps = {(i, j): eps_niespojnosci(p, i, j, k) for i, j in N}
                podtrzymane = []
                nastepny = "krok9"
                while N:
                    # krok 10
                    i, j = min(N, key=lambda para: (eps[para], para))
                    rho, dek = RHO_DOMYSLNE, True
                    while True:
                        prez = prezentacja_rozkladow(p.zorientowana(i, k), p.zorientowana(j, k), rho,
                                                     dekumulanta=dek, i=i, j=j, k=k)
                        odp = yield PytanieNiespojnosc(
                            "Warunek jest niespójny z dominacją stochastyczną: podtrzymać, osłabić czy zaostrzyć?",
                            warunek=warunek, eps=eps[(i, j)], prezentacja=prez, pozostale=tuple(N),
                        )
                        if isinstance(odp, ZmianaPrezentacji):
                            rho, dek = odp.rho, odp.dekumulanta
                            continue
                        break
                    if odp == PODTRZYMAJ:
                        # krok 11
                        podtrzymane.append((i, j))
                        N = [(r, s) for r, s in N if r != i and s != j]
                        continue
                    # krok 12
                    oslabienie = odp == OSLAB
                    # propozycje, po których nie zostałby żaden wariant, są pomijane (DECYZJE.md)
                    props = tuple(
                        w for w in propozycje_modyfikacji(p, warunek, i, j, oslabienie)
                        if any(w.spelnia(wartosc_parametru(p, a, w.k, w.parametr)) for a in A)
                    )
                    wybor = yield PytaniePropozycja(
                        "Czy akceptujesz jedną z proponowanych modyfikacji warunku?",
                        propozycje=props, oslabienie=oslabienie,
                    )
                    if wybor is None:
                        nastepny = "krok2"
                    else:
                        warunek = props[wybor]
                        nastepny = "krok5"
                    break
                if nastepny == "krok5":
                    continue
                if nastepny == "krok2":
                    break
                # krok 9: 𝒩 puste — następna iteracja
                historia.append(StanInsdecm(l, A, po, warunek, N_poczatkowe, tuple(podtrzymane)))
                warunki.append(warunek)
                A = po
                l += 1
                break
