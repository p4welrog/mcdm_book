"""Dominacje dla kryteriów w skali porządkowej (tabl. 1.3 i 1.4).

Rozkład oceny na skali porządkowej to prawdopodobieństwa kolejnych ocen
skali S = {1, …, z}, od najgorszej do najlepszej. Ocenom przypisuje się
umowne wartości liczbowe (przykłady 1.12-1.16); tu reprezentujemy rozkład
jako :class:`Rozklad` na tych wartościach, a skalę jako pełną, rosnącą listę
wartości — także ocen, których żaden z porównywanych wariantów nie uzyskał,
bo wchodzą one do sum (1.32) i do normy ‖F_i − F_j‖ (przykład 1.15).

Oznaczenia: P_s = Σ_{l≤s} p_l, Q_s = Σ_{l≤s} q_l (dystrybuanty w punktach
skali), PP_s = Σ_{r≤s} P_r, QQ_s = Σ_{r≤s} Q_r.

* OFSD (1.31): P_s ≤ Q_s dla każdego s,
* OSSD (1.32): PP_s ≤ QQ_s dla każdego s,
* S_1 = {s: Q_s < P_s}, S_2 = {s ∈ S_1: QQ_s < PP_s}, ‖F_i − F_j‖ = Σ_s |P_s − Q_s|,
* ε_1 = Σ_{s∈S_1}(P_s − Q_s)/‖·‖, ε_2 = Σ_{s∈S_2}(P_s − Q_s)/‖·‖ (tabl. 1.4),
* OAFSD(ε*): ε_1 ≤ ε* (1.33); OASSD(ε*): ε_2 ≤ ε* oraz μ_i ≥ μ_j (1.34).
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..rozklad import Rozklad
from .kardynalne import TOLERANCJA
from .relacje import Relacja, WynikPorownania


def _sumy(F: Rozklad, skala: Sequence) -> tuple:
    poza = set(F.wartosci) - set(skala)
    if poza:
        raise ValueError(f"wartości spoza skali: {sorted(poza)}")
    P = [F.dystrybuanta(s) for s in skala]
    PP, acc = [], 0
    for v in P:
        acc = acc + v
        PP.append(acc)
    return P, PP


def porownaj_porzadkowo(
    Fi: Rozklad, Fj: Rozklad, skala: Sequence, tolerancja: float = TOLERANCJA
) -> WynikPorownania:
    """Porównuje F_i z F_j na skali porządkowej ``skala`` (rosnąca lista ocen).

    W wyniku ``definicje`` zawiera OFSD i/lub OSSD, a ``eps_afsd`` i
    ``eps_assd`` to porządkowe ε_1 i ε_2 z tabl. 1.4 (sprawdzanie:
    :meth:`WynikPorownania.afsd`, :meth:`WynikPorownania.assd`).

    >>> from mcdm_ryzyko import Rozklad
    >>> skala = list(range(11))                       # przykład 1.16
    >>> X = Rozklad([3, 5, 6, 8, 10], [0.2] * 5)
    >>> Y = Rozklad([4, 5, 6, 9], [0.2, 0.4, 0.2, 0.2])
    >>> round(porownaj_porzadkowo(X, Y, skala).eps_afsd, 6)
    0.2
    """
    skala = list(skala)
    if sorted(set(skala)) != skala:
        raise ValueError("skala musi być rosnącym ciągiem różnych wartości")
    tol = tolerancja
    P, PP = _sumy(Fi, skala)
    Q, QQ = _sumy(Fj, skala)
    definicje = set()
    if all(p <= q + tol for p, q in zip(P, Q)):
        definicje.add(Relacja.OFSD)
    if all(p <= q + tol for p, q in zip(PP, QQ)):
        definicje.add(Relacja.OSSD)
    norma = sum(abs(p - q) for p, q in zip(P, Q))
    e1: Optional[object] = None
    e2: Optional[object] = None
    if norma > tol:
        S1 = [s for s in range(len(skala)) if Q[s] < P[s] - tol]
        S2 = [s for s in S1 if QQ[s] < PP[s] - tol]
        e1 = sum((P[s] - Q[s] for s in S1), 0) / norma
        e2 = sum((P[s] - Q[s] for s in S2), 0) / norma
    return WynikPorownania(
        definicje=frozenset(definicje),
        mu_i=Fi.wartosc_oczekiwana(),
        mu_j=Fj.wartosc_oczekiwana(),
        eps_afsd=e1,
        eps_assd=e2,
        tolerancja=tolerancja,
    )
