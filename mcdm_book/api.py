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

from . import additive, ahp, anp, reference, selection
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
    "ahp": {"fn": ahp.ahp, "chapter": "3.1", "title": "AHP",
            "needs": "criteria_comparisons (macierz n×n, skala 1–9 Saaty'ego) lub wagi; comparisons {kryterium: macierz m×m} "
                     "albo oceny liczbowe kryterium w values",
            "options": {"method": ahp.PRIORITY_METHODS, "eps": "dokładność metody potęgowej"},
            "scale": ahp.SAATY_SCALE},
    "rembrandt": {"fn": ahp.rembrandt, "chapter": "3.2", "title": "REMBRANDT",
                  "needs": "criteria_comparisons i comparisons z ocenami δ ∈ {−8, …, 8} (tabl. 3.3)",
                  "options": {"gamma_criteria": "γ dla kryteriów (domyślnie ln √2)",
                              "gamma_variants": "γ dla wariantów (domyślnie ln 2; przykład 3.7 używa ln √2)"}},
    "fuzzy_ahp": {"fn": ahp.fuzzy_ahp, "chapter": "3.3", "title": "Rozmyty AHP (Mikhailov)",
                  "needs": "macierze porównań z trójkami [l, m, u] (lub nazwami ze skali Changa, tabl. 3.4)",
                  "options": {"alphas": "poziomy α (domyślnie 0; 0,2; …; 1)", "d": "tolerancja względem zera (domyślnie 1)"},
                  "scale": {k: list(v) for k, v in ahp.CHANG_SCALE.items()}},
    "anp": {"fn": anp.anp, "chapter": "3.4", "title": "ANP (sieć zależności, supermacierz)",
            "needs": "clusters (komponenty kryteriów), influences lub dependency_matrix, comparisons {element: "
                     "{komponent: macierz}}, cluster_comparisons lub cluster_weights; BOCR: subnets + bocr_weights",
            "options": {"method": ahp.PRIORITY_METHODS, "limit": anp.LIMITS, "sinks": anp.SINKS,
                        "read_from": "element, z którego kolumny supermacierzy granicznej odczytać wektor skali",
                        "formula": anp.FORMULAS, "bocr_mode": "ideal (domyślnie, jak Super Decisions) | normal"}},
    "fuzzy_anp": {"fn": anp.fuzzy_anp, "chapter": "3.5", "title": "Rozmyta ANP (analiza Changa)",
                  "needs": "jak ANP; cluster_comparisons z trójkami [l, m, u] lub nazwami skali Changa (tabl. 3.4); "
                           "porównania elementów ostre lub rozmyte",
                  "options": {"method": ahp.PRIORITY_METHODS, "limit": anp.LIMITS, "sinks": anp.SINKS,
                              "read_from": "jak w ANP", "formula": anp.FORMULAS, "bocr_mode": "ideal | normal"},
                  "scale": {k: list(v) for k, v in ahp.CHANG_SCALE.items()}},
    "compromise": {"fn": selection.compromise, "chapter": "9.3", "title": "Programowanie kompromisowe (L1, wzór 9.1)",
                   "needs": "oceny liczbowe, kierunki, wagi; kryteria obowiązkowe z polem mandatory: true",
                   "options": {"ideal": "wartości optymalne kryteriów (domyślnie najlepsze w danych)"}},
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


SELECT_METHOD = {"chapter": "9.3", "title": "Wybór metody (model typu Gershona)",
                 "needs": "profile — cechy problemu (bez pola problem)", "profile": selection.PROFILE_FIELDS,
                 "options": {"scores": "nadpisanie ocen metod {metoda: {cecha: 0–10}}",
                             "methods": "lista rozważanych metod (domyślnie wszystkie)"}}


def methods() -> Dict[str, Any]:
    """Opis metod do wyświetlenia lub wyboru (bez funkcji)."""
    out = {k: {kk: vv for kk, vv in v.items() if kk != "fn"} for k, v in METHODS.items()}
    out["select_method"] = SELECT_METHOD
    return out


def run(request: Dict[str, Any]) -> Dict[str, Any]:
    method = request.get("method")
    if method == "select_method":
        opts = dict(request.get("options") or {})
        unknown = set(opts) - {"scores", "methods"}
        if unknown:
            raise ProblemError(f"select_method: nieznane opcje {', '.join(sorted(unknown))}")
        return selection.select(request.get("profile") or {}, **opts)
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
