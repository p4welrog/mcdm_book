"""Prawie dominacje stochastyczne AFSD i ASSD (tabl. 1.2; Leshno, Levy 2002).

Dla pary (F_i, F_j) na wspólnej siatce z_0 < … < z_n:

* S_1 = {t: F_j(t) < F_i(t)} — tam, gdzie naruszony jest warunek FSD,
* S_2 = {t ∈ S_1: ∫_a^t F_j < ∫_a^t F_i} — część S_1, w której η⁽²⁾ > 0,
* ‖F_i − F_j‖ = ∫_a^b |F_i − F_j|,
* ε_1 = ∫_{S_1}(F_i − F_j) / ‖F_i − F_j‖, ε_2 = ∫_{S_2}(F_i − F_j) / ‖F_i − F_j‖.

F_i AFSD(ε*) F_j, gdy ε_1 ≤ ε* (1.29); F_i ASSD(ε*) F_j, gdy ε_2 ≤ ε* i μ_i ≥ μ_j
(1.30). Wartość ε_1 jest zarazem najmniejszym ε, dla którego zachodzi AFSD(ε),
czyli współczynnikiem ε_ij^k używanym w STEM-DPR (rozdz. 8.3).
"""

from __future__ import annotations

from typing import Optional, Tuple

from ..rozklad import Rozklad
from .kardynalne import TOLERANCJA, funkcje_eta


def stopnie_naruszenia(Fi: Rozklad, Fj: Rozklad, tolerancja: float = TOLERANCJA) -> Tuple[Optional[object], Optional[object]]:
    """Zwraca (ε_1, ε_2) z tabl. 1.2; (None, None) dla rozkładów identycznych.

    >>> from mcdm_ryzyko import Rozklad
    >>> F1 = Rozklad([2, 8], ["0,8", "0,2"]); F2 = Rozklad([1, 4], ["0,4", "0,6"])
    >>> stopnie_naruszenia(F1, F2)   # przykład 1.11
    (Fraction(2, 5), Fraction(1, 5))
    """
    e = funkcje_eta(Fi, Fj)
    z = e.wezly
    norma = 0
    s1 = 0
    s2 = 0
    for t, (d, _, _) in enumerate(e.eta1.wsp):
        h = z[t + 1] - z[t]
        norma += abs(d) * h
        if d > tolerancja:
            s1 += d * h
            # Na tym odcinku η⁽²⁾(z_t + s) = η⁽²⁾(z_t) + d·s rośnie; S_2 to część,
            # gdzie η⁽²⁾ > 0, czyli s > −η⁽²⁾(z_t)/d.
            g0 = e.eta2.wsp[t][0]
            poczatek = 0 if g0 > 0 else min(h, -g0 / d)
            s2 += d * (h - poczatek)
    if norma <= tolerancja:
        return None, None
    return s1 / norma, s2 / norma


def afsd(Fi: Rozklad, Fj: Rozklad, eps: float, tolerancja: float = TOLERANCJA) -> bool:
    """Czy F_i AFSD(ε*) F_j dla ε* = ``eps`` ∈ (0; 0,5) (wzór 1.29)."""
    _sprawdz_eps(eps)
    e1, _ = stopnie_naruszenia(Fi, Fj, tolerancja)
    return e1 is not None and e1 <= eps + tolerancja


def assd(Fi: Rozklad, Fj: Rozklad, eps: float, tolerancja: float = TOLERANCJA) -> bool:
    """Czy F_i ASSD(ε*) F_j dla ε* = ``eps`` ∈ (0; 0,5) (wzór 1.30, z μ_i ≥ μ_j)."""
    _sprawdz_eps(eps)
    _, e2 = stopnie_naruszenia(Fi, Fj, tolerancja)
    return (
        e2 is not None
        and e2 <= eps + tolerancja
        and Fi.wartosc_oczekiwana() >= Fj.wartosc_oczekiwana() - tolerancja
    )


def _sprawdz_eps(eps) -> None:
    if not 0 < eps < 0.5:
        raise ValueError("dopuszczalny stopień naruszenia ε* musi należeć do przedziału (0; 0,5)")
