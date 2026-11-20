"""Jednolity interfejs JSON: run({"method": ..., "problem": {...}, "options": {...}}) → wynik (dict).

Wynik każdej metody:
  method, variants, criteria,
  scores: {label, values, better: "higher"|"lower"},
  ranks (1 = najlepszy, remisy mają tę samą rangę), ranking (od najlepszego), best,
  steps (wyniki pośrednie metody), notes (uwagi: normalizacja wag, przyjęte konwencje, rozbieżności z książką).
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict

from . import additive, reference
from .problem import Problem, ProblemError

METHODS: Dict[str, Dict[str, Any]] = {
    "saw": {"fn": additive.saw, "chapter": "2.1", "title": "Metoda sumy ważonej (SAW)",
            "needs": "oceny liczbowe, wagi (weight)",
            "options": {"normalization": additive.NORMALIZATIONS}},
    "scoring": {"fn": additive.scoring, "chapter": "2.1", "title": "Metoda scoringowa",
                "needs": "punkty przyznane wariantom (values), opcjonalnie max_points dla kryteriów", "options": {}},
    "fsaw": {"fn": additive.fsaw, "chapter": "2.2", "title": "Rozmyta suma ważona (FSAW)",
             "needs": "oceny liczbowe, wagi rozmyte fuzzy_weight = [min, najlepsza, max]",
             "options": {"normalization": additive.NORMALIZATIONS}},
    "smart": {"fn": additive.smart, "chapter": "2.3", "title": "SMART",
              "needs": "oceny; scale dla kryteriów (linear / direct / value_function); wagi rozpiętości swing (0–100)",
              "options": {"weights": "auto | swing | given | roc | rank_sum"}, "scales": additive.SCALES},
    "smarter": {"fn": additive.smarter, "chapter": "2.4", "title": "SMARTER",
                "needs": "oceny; rangi kryteriów rank (1 = najważniejsze); opcjonalnie best/worst w scale",
                "options": {"weights": "auto | roc | rank_sum | given | swing"}},
    "topsis": {"fn": reference.topsis, "chapter": "7.1", "title": "TOPSIS",
               "needs": "oceny liczbowe, kierunki, wagi", "options": {"metric": "rząd metryki p (domyślnie 2)"}},
    "fuzzy_topsis": {"fn": reference.fuzzy_topsis, "chapter": "7.2", "title": "Rozmyty TOPSIS",
                     "needs": "oceny [l, m, u] ≥ 0, kierunki, wagi",
                     "options": {"cost_norm": reference.COST_NORMS,
                                 "reference": "{ideal: [...], anti_ideal: [...]} — własne punkty odniesienia"}},
    "vikor": {"fn": reference.vikor, "chapter": "7.3", "title": "VIKOR",
              "needs": "oceny liczbowe, kierunki, wagi",
              "options": {"q": "waga strategii większości (domyślnie 0,5)",
                          "ideal": "własne f* (lista)", "anti_ideal": "własne f_* (lista)",
                          "w2": "both (książka) | either (Opricovic, Tzeng 2004)"}},
}


def methods() -> Dict[str, Any]:
    """Opis metod do wyświetlenia lub wyboru (bez funkcji)."""
    return {k: {kk: vv for kk, vv in v.items() if kk != "fn"} for k, v in METHODS.items()}


def run(request: Dict[str, Any]) -> Dict[str, Any]:
    method = request.get("method")
    if method not in METHODS:
        raise ProblemError(f"Nieznana metoda {method!r}; dostępne: {', '.join(METHODS)}")
    fn: Callable = METHODS[method]["fn"]
    p = Problem.from_dict(request.get("problem") or {})
    opts = dict(request.get("options") or {})
    allowed = set(inspect.signature(fn).parameters) - {"p"}
    unknown = set(opts) - allowed
    if unknown:
        raise ProblemError(f"Metoda {method}: nieznane opcje {', '.join(sorted(unknown))}; dostępne: {', '.join(sorted(allowed)) or 'brak'}")
    res = fn(p, **opts)
    if p.name:
        res["problem"] = p.name
    return res


def run_safe(request: Dict[str, Any]) -> Dict[str, Any]:
    """Jak run, ale błędy danych zwraca jako {"error": komunikat}."""
    try:
        return run(request)
    except ProblemError as e:
        return {"error": str(e)}
