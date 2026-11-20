"""Przykłady z książki i płyty CD w formacie zadania JSON (dane wejściowe; wyniki — zob. testy)."""
from __future__ import annotations

import copy
from typing import Any, Dict

_BANKS = {
    "variants": ["a1", "a2", "a3", "a4", "a5"],
    "variant_labels": ["PKO BP", "BPS", "Kredyt Bank", "BZ WBK", "PEKAO SA"],
    "values": [[4, 26, 2.5], [2, 25, 3], [3, 26, 4.8], [2, 30, 0.62], [3, 26, 3]],
}
_BANK_CRIT = [("f1", "liczba rodzajów kart kredytowych", 0.1), ("f2", "wiek, do którego można otrzymać konto", 0.3),
              ("f3", "liczba bankomatów (tys.)", 0.6)]


def _banks(name, **crit_extra):
    crit = []
    for (c, desc, w) in _BANK_CRIT:
        x = {"name": c, "description": desc, "direction": "max", "weight": w}
        x.update(crit_extra.get(c, {}))
        crit.append(x)
    return {"name": name, "variants": _BANKS["variants"], "variant_labels": _BANKS["variant_labels"],
            "criteria": crit, "values": _BANKS["values"]}


_P7 = [[3, 6, 7, 8], [5, 4, 7, 9], [10, 2, 5, 4], [4, 8, 5, 4], [2, 5, 11, 1], [9, 6, 3, 6], [4, 9, 7, 6],
       [1, 7, 9, 10], [5, 3, 6, 4]]
_P73 = [[(2, 3, 5), (3, 6, 10), (6, 7, 8), (7, 8, 10)], [(3, 5, 6), (2, 4, 5), (4, 7, 8), (7, 9, 9)],
        [(10, 10, 12), (2, 2, 4), (4, 5, 8), (3, 4, 6)], [(1, 4, 5), (7, 8, 9), (3, 5, 6), (2, 4, 5)],
        [(1, 2, 4), (3, 5, 7), (9, 11, 12), (1, 1, 4)], [(7, 9, 10), (3, 6, 6), (2, 3, 4), (5, 6, 8)],
        [(3, 4, 5), (7, 9, 11), (6, 7, 9), (3, 6, 7)], [(1, 1, 1), (6, 7, 11), (8, 9, 11), (7, 10, 13)],
        [(3, 5, 5), (1, 3, 5), (6, 6, 9), (2, 4, 5)]]
_W7 = [0.25, 0.15, 0.4, 0.2]
_SMART_DATA = [[28, 7, 30], [29, 6, 60], [20, 7, 50], [20, 2, 90]]

_V6 = [f"a{i}" for i in range(1, 7)]

EXAMPLES: Dict[str, Dict[str, Any]] = {
    "P2.1": {"title": "Przykład 2.1 — SAW, wybór konta w banku", "method": "saw",
             "options": {"normalization": "minmax"}, "problem": _banks("Wybór konta osobistego")},
    "P2.2": {"title": "Przykład 2.2 — metoda scoringowa (punkty przyznane przez studenta)", "method": "scoring",
             "options": {},
             "problem": {"name": "Wybór konta osobistego — punkty", "variants": _BANKS["variants"],
                         "variant_labels": _BANKS["variant_labels"],
                         "criteria": [{"name": "f1", "max_points": 10}, {"name": "f2", "max_points": 30},
                                      {"name": "f3", "max_points": 60}],
                         "values": [[10, 6, 27], [0, 0, 34], [5, 6, 60], [0, 30, 0], [5, 6, 34]]}},
    "P2.3": {"title": "Przykład 2.3 — FSAW, wagi rozmyte", "method": "fsaw", "options": {"normalization": "ratio"},
             "problem": _banks("Wybór konta osobistego — wagi rozmyte",
                               f1={"fuzzy_weight": [0, 0.1, 0.5]}, f2={"fuzzy_weight": [0.1, 0.3, 0.4]},
                               f3={"fuzzy_weight": [0.4, 0.6, 0.7]})},
    "P2.7": {"title": "Przykład 2.7 — SMART (unitaryzacja, ocena bezpośrednia, funkcja wartości)", "method": "smart",
             "options": {"weights": "swing"},
             "problem": {"name": "Przykład 2.7", "variants": ["a1", "a2", "a3", "a4"],
                         "criteria": [{"name": "f1", "direction": "min", "swing": 30, "scale": {"type": "linear"}},
                                      {"name": "f2", "direction": "max", "swing": 75, "scale": {"type": "direct"}},
                                      {"name": "f3", "direction": "max", "swing": 100,
                                       "scale": {"type": "value_function", "interpolation": "piecewise",
                                                 "points": [[30, 0], [50, 25], [70, 50], [80, 75], [90, 100]]}}],
                         "values": [[28, 100, 30], [29, 20, 60], [20, 100, 50], [20, 0, 90]]}},
    "P2.11": {"title": "Przykład 2.11 — SMARTER (liniowe funkcje wartości, wagi ROC)", "method": "smarter",
              "options": {"weights": "roc"},
              "problem": {"name": "Przykład 2.11", "variants": ["a1", "a2", "a3", "a4"],
                          "criteria": [{"name": "f1", "direction": "min", "rank": 3},
                                       {"name": "f2", "direction": "max", "rank": 2},
                                       {"name": "f3", "direction": "max", "rank": 1}],
                          "values": _SMART_DATA}},
    "P3.4": {"title": "Przykład 3.4 — AHP (dwa kryteria z porównań, trzecie z wartości)", "method": "ahp",
             "options": {"method": "saaty"},
             "problem": {"name": "Przykład 3.4", "variants": _V6,
                         "criteria": [{"name": "f1"}, {"name": "f2"}, {"name": "f3", "direction": "max"}],
                         "values": [[None, None, 21], [None, None, 25], [None, None, 19], [None, None, 17],
                                    [None, None, 28], [None, None, 25]],
                         "criteria_comparisons": [[1, "1/7", "1/3"], [7, 1, 3], [3, "1/3", 1]],
                         "comparisons": {
                             "f1": [[1, 7, 9, 3, 8, 9], ["1/7", 1, 5, "1/2", 5, 7], ["1/9", "1/5", 1, "1/5", 1, 3],
                                    ["1/3", 2, 5, 1, 5, 7], ["1/8", "1/5", 1, "1/5", 1, 5],
                                    ["1/9", "1/7", "1/3", "1/7", "1/5", 1]],
                             "f2": [[1, 3, 7, 3, 7, "1/2"], ["1/3", 1, 5, "1/3", 4, "1/5"], ["1/7", "1/5", 1, "1/7", "1/4", "1/7"],
                                    ["1/3", 3, 7, 1, 5, "1/3"], ["1/7", "1/4", 4, "1/5", 1, "1/5"], [2, 5, 7, 3, 5, 1]]}}},
    "P3.7": {"title": "Przykład 3.7 — REMBRANDT (γ = ln √2 także dla wariantów, jak w przykładzie)",
             "method": "rembrandt", "options": {"gamma_variants": 0.34657359027997264},
             "problem": {"name": "Przykład 3.7", "variants": _V6,
                         "criteria": [{"name": "f1"}, {"name": "f2"}, {"name": "f3"}],
                         "criteria_comparisons": [[0, -6, -2], [6, 0, 2], [2, -2, 0]],
                         "comparisons": {
                             "f1": [[0, 6, 8, 2, 7, 8], [-6, 0, 4, -1, 4, 6], [-8, -4, 0, -4, 0, 2], [-2, 1, 4, 0, 4, 6],
                                    [-7, -4, 0, -4, 0, 4], [-8, -6, -2, -6, -4, 0]],
                             "f2": [[0, 2, 6, 2, 6, -1], [-2, 0, 4, -2, -3, -4], [-6, -4, 0, -6, -3, -6],
                                    [-2, 3, 6, 0, 4, -2], [-6, -3, 3, -4, 0, -4], [1, 4, 6, 2, 4, 0]],
                             "f3": [[0, 4, 8, 3, 5, 4], [-4, 0, -4, -6, 3, -7], [-8, 4, 0, -4, -3, -4],
                                    [-3, 6, 4, 0, 4, -1], [-5, -3, 3, -4, 0, -4], [-4, 7, 4, 1, 4, 0]]}}},
    "P3.10": {"title": "Przykład 3.10 — rozmyty AHP (Mikhailov), dwa warianty, ocena (1, 3, 4)",
              "method": "fuzzy_ahp", "options": {"alphas": [0, 0.2, 0.4, 0.6, 0.8, 1], "d": 1},
              "problem": {"name": "Przykład 3.10", "variants": ["a1", "a2"],
                          "criteria": [{"name": "f", "weight": 1}],
                          "comparisons": {"f": [[1, [1, 3, 4]], [None, 1]]}}},
    "P7.1": {"title": "Przykład 7.1 — TOPSIS", "method": "topsis", "options": {"metric": 2},
             "problem": {"name": "Przykład 7.1", "variants": [f"a{i}" for i in range(1, 10)],
                         "criteria": [{"name": f"f{k + 1}", "direction": "max", "weight": w} for k, w in enumerate(_W7)],
                         "values": _P7}},
    "P7.3": {"title": "Przykład 7.3 — rozmyty TOPSIS", "method": "fuzzy_topsis", "options": {},
             "problem": {"name": "Przykład 7.3", "variants": [f"a{i}" for i in range(1, 10)],
                         "criteria": [{"name": f"f{k + 1}", "direction": "max", "weight": w} for k, w in enumerate(_W7)],
                         "values": [[list(t) for t in row] for row in _P73]}},
    "P7.4": {"title": "Przykład 7.4 — VIKOR, wybór konta w banku", "method": "vikor", "options": {"q": 0.5},
             "problem": _banks("Wybór konta osobistego")},
    "R14": {"title": "Rozdz. 14 — rozmyty TOPSIS z poziomami aspiracji i rezerwacji (oferty negocjacyjne)",
            "method": "fuzzy_topsis",
            "options": {"cost_norm": "min_l",
                        "reference": {"ideal": [[7, 10, 14], [15, 17.5, 20], [9, 10, 10]],
                                      "anti_ideal": [[30, 35, 60], [40, 42.5, 45], [0, 0, 1]]}},
            "problem": {"name": "Oferty negocjacyjne Comp4You", "variants": [f"a{i}" for i in range(1, 7)],
                        "criteria": [{"name": "czas dostawy (dni)", "direction": "min", "weight": 0.3},
                                     {"name": "cena jednostkowa (zł)", "direction": "min", "weight": 0.5},
                                     {"name": "gwarancja jakości", "direction": "max", "weight": 0.2}],
                        "values": [[[21, 36, 43], [35, 40, 45], [5, 7, 9]], [[7, 14, 21], [25, 26.5, 28], [7, 9, 10]],
                                   [[21, 21, 60], [30, 33.5, 37], [0, 1, 3]], [[21, 21, 60], [30, 33.5, 37], [5, 7, 9]],
                                   [[21, 21, 60], [20, 22.5, 25], [5, 7, 9]], [[21, 21, 60], [18, 19, 20], [3, 5, 7]]]}},
}


def listing():
    return [{"id": k, "title": v["title"], "method": v["method"]} for k, v in EXAMPLES.items()]


def get(name: str) -> Dict[str, Any]:
    if name not in EXAMPLES:
        raise KeyError(f"Nieznany przykład {name!r}; dostępne: {', '.join(EXAMPLES)}")
    e = copy.deepcopy(EXAMPLES[name])
    return {"method": e["method"], "options": e["options"], "problem": e["problem"], "title": e["title"]}
