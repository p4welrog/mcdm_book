"""Mierniki zgodności opinii dwóch ekspertów (zbiór R9.6, rozdz. 9.5): wskaźnik zgodności ocen punktowych z₁ (10)–(11),
wskaźnik zgodności pozycji z₂ (12)–(16) i wskaźnik zgodności uszeregowania (liczby inwersji) z₃ (17)–(18).

W (15) brak czynnika 100 % i źle zapisana dolna granica sumy, a wzoru na z₃ w R9.6 brak — przyjmuję z₃ = 1 − w₃,
jak z₁, z₂; inwersje liczone po parach uporządkowanych (i, j) i (j, i), dlatego mianownik n(n − 1) (R9.6: „suma
ciągu” n(n − 1)). Tak odtwarza się zbiór R9.11 (z pozycji ze zbioru R9.10)."""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from .problem import ProblemError

DESCRIPTION = {"title": "Mierniki zgodności dwóch uszeregowań (zbiór R9.6)", "chapter": "9.5",
               "needs": "\"positions\": [pozycje A, pozycje B] (pozycja 1 = najlepsza, remisy dozwolone); "
                        "opcjonalnie \"scores\": [oceny A, oceny B] dla z₁"}


def score_agreement(a: Sequence[float], b: Sequence[float]) -> float:
    """z₁ = 1 − (średnia |o(i, A) − o(i, B)|)/(M − m) (10)–(11)."""
    lo, hi = min(min(a), min(b)), max(max(a), max(b))
    if hi == lo:
        return 1.0
    return 1 - sum(abs(x - y) for x, y in zip(a, b)) / len(a) / (hi - lo)


def position_agreement(pa: Sequence[float], pb: Sequence[float]) -> float:
    """z₂ = 1 − Σ|p(i, A) − p(i, B)| / Σ|n − 2i + 1| (12)–(16)."""
    n = len(pa)
    den = sum(abs(n - 2 * i + 1) for i in range(1, n + 1))
    return 1 - sum(abs(x - y) for x, y in zip(pa, pb)) / den


def inversions(pa: Sequence[float], pb: Sequence[float]) -> int:
    n = len(pa)
    return sum(1 for i in range(n) for j in range(n)
               if (pa[i] < pa[j] and pb[i] > pb[j]) or (pa[i] > pa[j] and pb[i] < pb[j]))


def order_agreement(pa: Sequence[float], pb: Sequence[float]) -> float:
    """z₃ = 1 − I/(n(n − 1)) (17)–(18)."""
    n = len(pa)
    return 1 - inversions(pa, pb) / (n * (n - 1))


def indices(positions: Any, scores: Optional[Any] = None) -> Dict[str, Any]:
    if not isinstance(positions, list) or len(positions) != 2 or len(positions[0]) != len(positions[1]) \
            or len(positions[0]) < 2:
        raise ProblemError("agreement: \"positions\" — dwie listy pozycji tej samej długości (≥ 2)")
    pa, pb = [list(map(float, x)) for x in positions]
    out = {"method": "agreement", "n": len(pa), "position_agreement": position_agreement(pa, pb),
           "order_agreement": order_agreement(pa, pb), "inversions": inversions(pa, pb),
           "position_differences": [abs(x - y) for x, y in zip(pa, pb)],
           "notes": ["z₃ = 1 − I/(n(n − 1)); I liczone po parach uporządkowanych (wzór (17) zbioru R9.6)."]}
    if scores is not None:
        if not isinstance(scores, list) or len(scores) != 2 or any(len(s) != len(pa) for s in scores):
            raise ProblemError("agreement: \"scores\" — dwie listy ocen tej samej długości co pozycje")
        out["score_agreement"] = score_agreement(list(map(float, scores[0])), list(map(float, scores[1])))
    return out
