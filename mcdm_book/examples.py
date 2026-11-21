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

_NET_312 = {"clusters": {"AS": ["f1", "f2"], "AT": ["f3", "f4"]}, "variants_cluster": "W",
            "dependency_matrix": [[0, 0, 1, 1, 1, 1], [0, 0, 0, 1, 1, 1], [0, 1, 0, 0, 1, 1],
                                  [0, 0, 0, 0, 1, 1], [0, 1, 0, 1, 0, 0], [0, 1, 1, 0, 0, 0]],
            "comparisons": {"f1": {"AT": [[1, 5], [None, 1]], "W": [[1, 3], [None, 1]]},
                            "f2": {"W": [[1, 3], [None, 1]]},
                            "f3": {"W": [[1, "1/9"], [None, 1]]},
                            "f4": {"W": [[1, 7], [None, 1]]}}}
_CRIT_312 = [{"name": "f1", "label": "adekwatność do warunków lokalnych"}, {"name": "f2", "label": "sposób zarządzania"},
             {"name": "f3", "label": "możliwość realizacji"}, {"name": "f4", "label": "zasoby niezbędne do realizacji"}]
# Przykład 3.13: priorytety wariantów w podsieciach (Super Decisions, kolumna Ideals, rys. 10–13);
# kolejność wariantów: obecny dostawca, X, Y, Z
_BOCR_313 = {"B": [0.932695, 0.422383, 0.978943, 1.0], "O": [0.287789, 1.0, 0.279291, 0.406939],
             "C": [0.814394, 1.0, 0.300590, 0.394819], "R": [0.502724, 0.788117, 0.590836, 1.0]}

# --- rozdz. 6 ---
_X_67 = [[40, 10, 3], [27, 45, 30], [2, 38, 52], [44, 29, 6], [18, 37, 44]]
_C_67 = [{"name": "f1", "weight": 0.5, "q": 5, "p": 10, "v": 12}, {"name": "f2", "weight": 0.2, "q": 5, "p": 8, "v": 11},
         {"name": "f3", "weight": 0.3, "q": 5, "p": 11, "v": 13}]
_X_65 = [[6, 10, 23, 99, 1.25, 250], [4, 11, 22, 105, 3.5, 248], [4, 13, 25, 95, 2.5, 249], [5, 12, 20, 74, 1.75, 252]]
_C_65 = [{"name": "f1", "weight": 0.2, "type": 1}, {"name": "f2", "weight": 0.1, "type": 2, "q": 2},
         {"name": "f3", "weight": 0.3, "type": 3, "p": 4}, {"name": "f4", "weight": 0.1, "type": 4, "q": 5, "p": 10},
         {"name": "f5", "weight": 0.1, "type": 5, "q": 1, "p": 2}, {"name": "f6", "weight": 0.2, "type": 6, "s": 1}]


def _dist_611():
    x = ([0, 1, 2, 3, 4], [7, 7.5, 8, 8.5], [400, 450, 500, 550, 600])
    P = ([[.6, .24, .1, .04, .02], [.6, .2, .1, .05, .05], [.7, .1, .1, .1, 0], [.4, .15, .15, .15, .15],
          [.5, .15, .15, .1, .1]],
         [[.24, .48, .24, .04], [.2, .4, .3, .1], [.2, .35, .3, .15], [.3, .5, .15, .05], [.15, .5, .25, .1]],
         [[.1, .1, .4, .2, .2], [.2, .1, 0, .5, .2], [.1, .15, .35, .25, .15], [.05, .1, .45, .25, .15],
          [.15, .35, .25, .2, .05]])
    return [[{"values": x[k], "probs": P[k][i]} for k in range(3)] for i in range(5)]


_C_611 = [{"name": "f1", "weight": 0.40, "p": 0.5, "v": 0.8}, {"name": "f2", "weight": 0.35, "p": 0.25, "v": 0.75},
          {"name": "f3", "weight": 0.25, "p": 10, "v": 35}]


_X5 = [[3, 6, 7, 8], [5, 4, 7, 9], [10, 2, 5, 4], [4, 8, 5, 2], [2, 5, 11, 1], [9, 6, 3, 6], [4, 9, 7, 6],
       [1, 7, 9, 10], [5, 3, 6, 4]]
_X513 = [_X5[i] for i in (0, 2, 4, 5, 6, 7)]
_W5 = [0.08, 0.33, 0.17, 0.42]
_C5 = [{"name": f"f{k + 1}", "weight": w} for k, w in enumerate(_W5)]
_C5V = [{"name": f"f{k + 1}", "weight": w, "v": v} for k, (w, v) in enumerate(zip(_W5, (5, 7, 6, 5)))]
_C5III = [{"name": f"f{k + 1}", "weight": w, "q": q, "p": pp, "v": v}
          for k, (w, q, pp, v) in enumerate(zip(_W5, (1, 2, 1, 1), (3, 4, 4, 3), (5, 7, 6, 5)))]


def _tri(name):
    return {"name": name, "variants": _V6, "criteria": _C5III, "values": _X513,
            "profiles": [[5, 4, 6, 3], [7, 6, 8, 8]], "categories": ["słabe", "średnie", "dobre"]}


_D713 = [[15, 110, 9], [14, 56, 4], [18, 90, 6], [19, 120, 7], [15, 30, 8], [11, 18, 8], [12, 15, 6], [13, 15, 5],
         [20, 25, 9], [13, 95, 7], [19, 65, 6], [9, 150, 5], [23, 58, 5], [15, 74, 4], [12, 80, 6], [12, 70, 4],
         [20, 35, 5], [13, 50, 3], [15, 45, 3], [11, 78, 8]]
_Z713 = [[7, 31, 1], [2, 65, 3], [4, 95, 4], [3, 5, 5], [12, 3, 5], [2, 14, 3], [7, 28, 2], [2, 32, 6], [5, 70, 4],
         [3, 40, 3], [10, 50, 2], [11, 49, 1], [7, 85, 0], [2, 125, 5], [4, 55, 4], [3, 45, 1], [12, 15, 3],
         [5, 25, 4], [11, 35, 6], [15, 53, 2]]
_A713 = [[25, 115, 6], [18, 80, 8], [19, 35, 9], [10, 65, 5], [14, 13, 8], [15, 17, 13], [21, 13, 8], [14, 25, 9],
         [8, 35, 1], [5, 15, 3]]


def _bip79(name):
    """Dane przykładów 7.9–7.12 (i rys. 1 przykładu 7.7 — obliczenia P7.7 odpowiadają tym danym)."""
    return {"name": name, "variants": ["a1", "a2", "a3", "a4"],
            "criteria": [{"name": "f1", "weight": 0.6, "q": 0.25, "v": 0}, {"name": "f2", "weight": 0.4, "q": 0.25, "v": 0}],
            "values": [[1, 5], [3, 5], [4, 3], [5, 2]], "good": [[0, 6], [5, 6], [5, 0]], "bad": [[0, 2], [2, 0]]}


def _bip713(name, **crit):
    return {"name": name, "variants": [f"a{i}" for i in range(1, 11)],
            "criteria": [{"name": f"f{k}", **crit} for k in range(1, 4)], "values": _A713, "good": _D713, "bad": _Z713}


_C16 = ["c11 wartość historyczno-badawcza", "c12 wartość historyczno-techniczna", "c13 wartość emocjonalna",
        "c14 wartość posiadanego oryginału", "c21 wartość historyczno-artystyczna", "c22 jakość artystyczna",
        "c23 oddziaływanie artystyczne", "c31 wartość historyczno-muzyczna", "c32 jakość muzyczna",
        "c33 oddziaływanie muzyczne", "c41 wartość użytkowa wizualna", "c42 wartość użytkowa muzyczna"]
_G16 = ["C1 wartości historyczne"] * 4 + ["C2 wartości artystyczne"] * 3 + ["C3 wartości muzyczne"] * 3 + \
       ["C4 wartości użytkowe"] * 2
_T161 = [[10, 8, 6, 6, 6, 6, 6, 6, 6, 6, 6, 0], [4, 6, 10, 8, 8, 6, 10, 6, 10, 6, 10, 0],
         [10, 10, 10, 8, 6, 10, 6, 6, 4, 4, 2, 0], [10, 10, 10, 9, 5, 8, 5, 9, 4, 5, 0, 0],
         [0, 2, 4, 6, 6, 4, 4, 6, 6, 8, 8, 0], [0, 0, 2, 4, 8, 2, 2, 4, 4, 8, 8, 8],
         [2, 2, 6, 8, 10, 6, 6, 8, 8, 10, 10, 10], [0, 0, 0, 0, 0, 10, 4, 10, 4, 10, 4, 4],
         [0, 0, 0, 0, 0, 8, 10, 8, 10, 8, 10, 10], [0, 0, 0, 0, 0, 8, 10, 8, 10, 8, 10, 10],
         [2, 4, 6, 8, 10, 6, 6, 8, 8, 10, 10, 10], [0, 0, 0, 0, 0, 8, 10, 8, 10, 8, 10, 10]]
_O164 = [[0, 3, 1, 4, 4, 4, 1, 4, 1, 1, 2, 2], [3, 0, 1, 4, 2, 1, 0, 2, 1, 1, 2, 2], [2, 2, 0, 3, 2, 2, 1, 2, 1, 2, 4, 4],
         [4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 3, 3], [3, 3, 3, 4, 0, 4, 4, 2, 2, 2, 4, 0], [2, 2, 2, 2, 3, 0, 2, 0, 0, 0, 4, 0],
         [1, 1, 1, 4, 4, 4, 0, 0, 0, 0, 4, 0], [3, 3, 2, 4, 0, 0, 0, 0, 4, 4, 0, 4], [1, 1, 0, 2, 0, 0, 0, 4, 0, 4, 0, 4],
         [1, 1, 0, 2, 0, 0, 0, 4, 4, 0, 0, 4], [0, 0, 0, 0, 4, 4, 4, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 0, 0]]
_O163 = [[2, 2, 2, 3], [3, 2, 0, 3], [3, 0, 3, 2], [0, 4, 4, 0]]


_ZS = lambda L: [L + "1", L + "2", L + "3"]
_CRIT_ZAPROS = [{"name": "f1 działalność dydaktyczna", "scale": _ZS("A")},
                {"name": "f2 udokumentowany dorobek naukowy", "scale": _ZS("B")},
                {"name": "f3 potencjał w kierowaniu projektami", "scale": _ZS("C")}]
_V46 = [["A1", "B2", "C2"], ["A2", "B2", "C1"], ["A3", "B1", "C2"], ["A1", "B3", "C1"], ["A2", "B1", "C3"],
        ["A3", "B2", "C2"]]
_Y46 = [["I", "P", "P", "P", "P", "P", "P"], [None, "I", "P", "P", "P", None, "P"],
        [None, None, "I", None, None, None, "I"], [None, None, "P", "I", "P", None, "P"],
        [None, None, "P", None, "I", None, "P"], [None, "P", "P", "P", "P", "I", "P"],
        [None, None, "I", None, None, None, "I"]]
_QV_TABLE = [["I", "P", "P", "P", "P", "P"], [None, "I", None, None, "P", None], [None, "P", "I", None, "P", "P"],
             [None, "P", "P", "I", "P", "P"], [None, None, None, None, "I", None], [None, "P", None, None, "P", "I"]]
_QV_TABLE_C = [["I", "P", "P", None, "P", "P"], [None, "I", None, None, "P", None], [None, "P", "I", None, "P", "P"],
               ["P", "P", "P", "I", "P", "P"], [None, None, None, None, "I", None], [None, "P", None, None, "P", "I"]]
_N = None
_P43 = {"name": "Wybór telefonu komórkowego",
        "variants": ["Samsung Galaxy S3", "HTC One S", "LG Prada Phone 3.0", "Sony Xperia P", "Nokia Lumia 800"],
        "criteria": [
            {"name": "Jakość wyświetlania",
             "macbeth": {"levels": ["Doskonała", "Bardzo dobra", "Dobra", "Neutralna", "Niewystarczająca"],
                         "judgements": [[0, "moderate", "strong", "strong", "extreme"],
                                        [_N, 0, "moderate", "positive", "very strong"],
                                        [_N, _N, 0, "moderate", "strong"], [_N, _N, _N, 0, "moderate"],
                                        [_N, _N, _N, _N, 0]],
                         "upper": "Bardzo dobra", "lower": "Neutralna"}},
            {"name": "Przekątna wyświetlacza"}, {"name": "Kolor telefonu"},
            {"name": "Ciężar",
             "macbeth": {"levels": [120, 122, 130, 140, 144],
                         "judgements": [[0, "weak", "moderate", "strong", "very strong"],
                                        [_N, 0, "moderate", "positive", "very strong"],
                                        [_N, _N, 0, "strong", "strong"], [_N, _N, _N, 0, "strong"],
                                        [_N, _N, _N, _N, 0]],
                         "upper": 122, "lower": 140}}],
        "values": [["Doskonała", 500, 200, 133], ["Dobra", 100, 100, 121], ["Bardzo dobra", 100, 0, 140],
                   ["Neutralna", 0, 100, 122], ["Bardzo dobra", -400, -100, 144]],
        "criteria_judgements": [[0, "moderate", _N, "very strong", "very strong"],
                                [_N, 0, _N, "very strong", "very strong"],
                                ["strong", "strong", 0, "very strong", "very strong"],
                                [_N, _N, _N, 0, "weak"], [_N, _N, _N, _N, 0]]}


def _obs(scores):
    """scores[k][osoba][wariant] → oceny wariantów jako obserwacje (rozkłady empiryczne)."""
    m = len(scores[0][0])
    return [[{"obs": [row[i] for row in scores[k]]} for k in range(len(scores))] for i in range(m)]


_OBS_612 = [[[1, 7, 6, 1, 8, 4, 1, 10], [8, 6, 5, 7, 6, 8, 6, 10], [2, 9, 5, 7, 5, 7, 5, 10]],
            [[5, 7, 5, 7, 7, 3, 5, 5], [7, 5, 5, 6, 5, 6, 2, 10], [6, 7, 8, 6, 4, 5, 4, 10]],
            [[8, 8, 7, 8, 8, 2, 7, 3], [7, 9, 8, 8, 8, 8, 6, 4], [7, 9, 8, 9, 8, 5, 7, 10]]]
_OBS_616 = [[[3, 5, 4, 7, 6, 7, 6, 5], [5, 7, 0, 6, 4, 6, 3, 3], [8, 9, 8, 9, 9, 10, 10, 10], [3, 10, 5, 9, 10, 10, 7, 5],
             [3, 8, 2, 5, 8, 9, 5, 4]],
            [[3, 7, 2, 7, 4, 3, 6, 5], [5, 8, 6, 7, 3, 6, 3, 3], [7, 10, 9, 10, 9, 8, 10, 10], [4, 10, 9, 9, 2, 10, 7, 10],
             [4, 10, 5, 9, 5, 7, 7, 4]],
            [[6, 7, 3, 3, 7, 2, 3, 6], [6, 8, 2, 2, 6, 4, 5, 4], [8, 10, 6, 10, 10, 10, 10, 10], [10, 10, 2, 0, 5, 10, 10, 4],
             [5, 8, 4, 4, 9, 9, 9, 7]]]
_V8 = [f"a{i}" for i in range(1, 9)]

# --- Część II: zastosowania (rozdz. 9–16) ---
_C_R95 = [{"name": f"f{k + 1}", "weight": w, "q": q, "p": pp, "v": v} for k, (w, q, pp, v) in enumerate(
    [(0.23, 1, 3.5, 7), (0.14, 0, 3, 11), (0.23, 0.5, 2, 8), (0.23, 1, 3, 8), (0.02, 1, 3, 11), (0.04, 1.5, 3, 11),
     (0.05, 1.5, 3.5, 11), (0.01, 3, 5, 11), (0.05, 0, 2, 7)])]
_X_R95 = [[10, 2, 10, 10, 10, 8.3, 8.3, 1.7, 0.7], [7.7, 5.3, 7, 7.3, 10, 5.3, 7, 10, 10],
          [10, 6.7, 10, 10, 8.7, 7, 7, 8.3, 8.3], [7, 5.3, 3.7, 5, 10, 5, 7, 10, 10],
          [7.3, 6.7, 7.7, 8, 8.3, 8, 8, 8.7, 6], [8, 8, 7.7, 8.3, 8.7, 8.7, 8.7, 9, 9.7],
          [9, 9, 9.3, 8, 9.7, 9, 10, 9, 9.3], [9.7, 7, 9.3, 9.7, 5.7, 7.7, 6.7, 6.7, 7.7],
          [7.7, 5.7, 7.7, 7, 10, 5.3, 4.3, 10, 10], [9, 7, 6.7, 8, 5.3, 5.7, 7.7, 6.7, 7.7]]
_P_R95 = {"name": "Projekty RPO WK-P (tabl. 9.4–9.5)", "variants": [f"a{i}" for i in range(1, 11)],
          "criteria": _C_R95, "values": _X_R95}

# R11.1 — początkowa supermacierz (kolumna = element, ze względu na który porównywano)
_R11_EL = ["F", "FX", "S", "SA", "UF", "R", "SI", "SR", "TA", "FOC", "IT", "MS", "SS", "TC", "IFS", "IM5", "SAP"]
_R11_CL = {"C1": ["F", "FX", "S", "SA", "UF"], "C2": ["R", "SI", "SR", "TA"], "C3": ["FOC", "IT", "MS", "SS", "TC"]}
_R11_M = [
    [0, 0.3333, 0, 1, 0, 0, 0, 0.25, 0.2756, 0, 0, 0.218, 0, 1, 0.2031, 0.1169, 0.4804],
    [0.6738, 0, 0, 0, 0.5, 0, 0.5, 0.25, 0.1412, 0, 0.8333, 0.5153, 0, 0, 0.1276, 0.2122, 0.2402],
    [0.1007, 0, 0, 0, 0.5, 1, 0.5, 0.25, 0, 0, 0, 0.0603, 0, 0, 0.0535, 0.0587, 0.1146],
    [0.2255, 0.3333, 0, 0, 0, 0, 0, 0.25, 0.4827, 0, 0, 0.1199, 0, 0, 0.527, 0.3697, 0.1098],
    [0, 0.3333, 0, 0, 0, 0, 0, 0, 0.1006, 0, 0.1667, 0.0865, 1, 0, 0.0889, 0.2425, 0.0549],
    [0, 0, 1, 0, 1, 0, 1, 0.3333, 0, 0, 0, 0.2581, 0, 0, 0.1704, 0.1851, 0.064],
    [0, 0, 0, 0, 0, 0, 0, 0.3333, 0, 1, 0, 0.1076, 0, 1, 0.0724, 0.1163, 0.1005],
    [0, 0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.1896, 0, 0, 0.3418, 0.2404, 0.5731],
    [1, 0.5, 0, 1, 0, 0, 0, 0.3333, 0, 0, 0, 0.4448, 0, 0, 0.4154, 0.4582, 0.2624],
    [0, 0.3333, 0, 0, 0, 0, 0.5, 0, 0, 0, 0.8571, 0.2175, 0, 0.25, 0.2, 0.1135, 0.2728],
    [0.1429, 0.3333, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.1237, 0, 0.25, 0.2, 0.2054, 0.1327],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.25, 0.2, 0.0868, 0.4923],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0.2, 0, 0.0894, 0, 0.25, 0.2, 0.2302, 0.065],
    [0.8571, 0.3333, 0, 0, 0, 1, 0.5, 1, 1, 0.8, 0.1429, 0.5694, 0, 0, 0.2, 0.3641, 0.0372],
    [0.4, 0.0936, 0.3108, 0.5469, 0.2493, 0.1958, 0.1634, 0.2403, 0.4, 0.3108, 0.122, 0.2403, 0.1311, 0.2583, 0, 0.6667, 0.8571],
    [0.4, 0.6267, 0.4934, 0.3445, 0.5936, 0.4934, 0.297, 0.2098, 0.4, 0.1958, 0.6483, 0.2098, 0.6608, 0.637, 0.125, 0, 0.1429],
    [0.2, 0.2797, 0.1958, 0.1085, 0.1571, 0.3108, 0.5396, 0.5499, 0.2, 0.4934, 0.2297, 0.5499, 0.2081, 0.1047, 0.875, 0.3333, 0]]


def _anp_from_supermatrix(M, elements, clusters, variants):
    """Porównania ze względu na każdy element jako gotowe wektory wag bloków supermacierzy początkowej."""
    idx = {e: i for i, e in enumerate(elements)}
    allc = dict(clusters, Warianty=list(variants))
    comp = {}
    for e in elements:
        per = {}
        for c, els in allc.items():
            v = [M[idx[x]][idx[e]] for x in els if x != e]
            if sum(v) > 0:
                per[c] = v
        comp[e] = per
    return comp


_R15 = [("a1", 0.54, 11, 0.2), ("a2", 0.75, 11, 0.8), ("a6", 0.3, 2, 0), ("a7", 0.82, 8, 0.2), ("a8", 0.64, 4, 0.9), ("a11", 0.75, 12, 0.5), ("a12", 0.7, 11, 0.7), ("a13", 0.56, 3, 0.9), ("a14", 0.69, 26, 0.3), ("a15", 0.63, 63, 0.1), ("a16", 0.61, 28, 0.2), ("a17", 0.36, 26, 0), ("a18", 0.41, 36, 0.1), ("a19", 0.86, 10, 0), ("a20", 0.35, 9, 0.9), ("a21", 0.61, 82, 0.4), ("a23", 0.69, 23, 0.7), ("a24", 0.98, 9, 0), ("a25", 0.49, 0, 0.6), ("a26", 0.88, 3, 0.6), ("a27", 0.5, 0, 0.6), ("a28", 0.84, 3, 0), ("a29", 0.85, 9, 0.4), ("a31", 0.76, 8, 0.3), ("a32", 0.61, 14, 0.6), ("a35", 0.53, 12, 0.6), ("a37", 0.72, 12, 0.9), ("a38", 0.71, 10, 0.7), ("a39", 0.85, 16, 0), ("a40", 0.44, 0, 0.7), ("a41", 0.77, 15, 0.8), ("a42", 0.89, 14, 0.1), ("a43", 0.79, 0, 0.6), ("a44", 0.65, 9, 0), ("a47", 0.55, 8, 0.4), ("a48", 0.56, 7, 0.7), ("a50", 0.61, 11, 0), ("a52", 0.76, 12, 0.7), ("a55", 0.74, 2, 0.2), ("a57", 0.84, 29, 0), ("a59", 0.59, 12, 0.9), ("a62", 0.45, 1, 0.7), ("a65", 0.79, 10, 0.5), ("a66", 0.7, 1, 0.8), ("a67", 0.72, 5, 0.8), ("a68", 0.69, 49, 0.7), ("a69", 0.64, 26, 0.2), ("a70", 0.48, 20, 0.9), ("a72", 0.29, 7, 0.5), ("a73", 0.41, 14, 0.2), ("a74", 0.41, 1, 0.9)]
_R16_W = [50, 50, 30, 130, 50, 30, 30, 80, 50, 30, 15, 30]
_R16_T = [[10, 8, 6, 6, 6, 6, 6, 6, 6, 6, 6, 0], [4, 6, 10, 8, 8, 6, 10, 6, 10, 6, 10, 0],
          [10, 10, 10, 8, 6, 10, 6, 6, 4, 4, 2, 0], [10, 10, 10, 9, 5, 8, 5, 9, 4, 5, 0, 0],
          [0, 2, 4, 6, 6, 4, 4, 6, 6, 8, 8, 0], [0, 0, 2, 4, 8, 2, 2, 4, 4, 8, 8, 8],
          [2, 2, 6, 8, 10, 6, 6, 8, 8, 10, 10, 10], [0, 0, 0, 0, 0, 10, 4, 10, 4, 10, 4, 4],
          [0, 0, 0, 0, 0, 8, 10, 8, 10, 8, 10, 10], [0, 0, 0, 0, 0, 8, 10, 8, 10, 8, 10, 10],
          [2, 4, 6, 8, 10, 6, 6, 8, 8, 10, 10, 10], [0, 0, 0, 0, 0, 8, 10, 8, 10, 8, 10, 10]]
_R16_NAMES = ["wartość historyczno-badawcza", "wartość historyczno-techniczna", "wartość emocjonalna",
              "wartość posiadanego oryginału", "wartość historyczno-artystyczna", "jakość artystyczna",
              "oddziaływanie artystyczne", "wartość historyczno-muzyczna", "jakość muzyczna",
              "oddziaływanie muzyczne", "wartość użytkowa wizualna", "wartość użytkowa muzyczna"]


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
    "R9.2": {"title": "Zbiór R9.2 — model Gershona: wybór metody do rankingu wniosków o dofinansowanie z UE",
             "method": "compromise", "options": {"ideal": [1, 1, 1, 1, 1, 1, 1, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]},
             "problem": {"name": "Model Gershona (R9.2)",
                         "variants": ["średnia z ważonych sum", "ELECTRE III", "PROMETHEE II", "EXPROM II", "BIPOLAR",
                                      "SMART", "TOPSIS"],
                         "criteria": [{"name": "kryteria jakościowe", "mandatory": True},
                                      {"name": "zbiory dyskretne", "mandatory": True},
                                      {"name": "porównanie z punktem docelowym", "weight": 1},
                                      {"name": "porównanie z poziomem aspiracji", "weight": 1},
                                      {"name": "bezpośrednie porównania", "weight": 1},
                                      {"name": "kompletny ranking", "weight": 7},
                                      {"name": "ranking na skali kardynalnej", "weight": 5},
                                      {"name": "czas pracy komputera", "weight": 1},
                                      {"name": "czas na implementację metody", "weight": 1},
                                      {"name": "czas na interakcję", "weight": 3},
                                      {"name": "świadomość decydenta", "weight": 2},
                                      {"name": "zgodność / konsekwencja / logika rozwiązań", "weight": 4},
                                      {"name": "grupowy decydent", "weight": 4},
                                      {"name": "poziom wiedzy decydenta", "weight": 3},
                                      {"name": "czas dostępny na interakcję", "weight": 2},
                                      {"name": "potrzeba interakcji", "weight": 3},
                                      {"name": "przekonanie dotyczące struktury preferencji", "weight": 7}],
                         "values": [list(r) for r in zip(
                             [1] * 7, [1] * 7, [0, 0, 0, 1, 1, 0, 1], [1, 0, 0, 0, 0, 1, 0], [0, 1, 1, 1, 0, 0, 0],
                             [1, 0, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 1, 1], [10, 8, 9, 9, 9, 10, 10],
                             [10, 2, 4, 4, 4, 9, 9], [10, 6, 6, 6, 2, 10, 10], [10, 2, 3, 3, 3, 8, 6],
                             [10, 8, 10, 10, 10, 10, 10], [4, 10, 10, 10, 10, 4, 4], [10, 6, 6, 6, 2, 10, 10],
                             [10, 8, 8, 8, 6, 10, 10], [10, 7, 7, 7, 5, 10, 10], [6, 9, 10, 10, 10, 5, 5])]}},
    "R9.3": {"title": "Zbiór R9.3 — procedura Tecle'a: wybór metody do rankingu wniosków o dofinansowanie z UE",
             "method": "compromise", "options": {"ideal": [1, 1] + [10] * 21},
             "problem": {"name": "Procedura Tecle'a (R9.3)",
                         "variants": ["średnia z ważonych sum", "ELECTRE III", "PROMETHEE II", "EXPROM II", "BIPOLAR",
                                      "SMART", "TOPSIS"],
                         "criteria": [{"name": n, "weight": w} for n, w in (
                             ("P1 skończona liczba wariantów", 50), ("P3 kryteria jakościowe", 50),
                             ("D1 indywidualne lub grupowe podejmowanie decyzji", 28), ("D2 czas na interakcję", 6),
                             ("D3 zainteresowanie interakcją", 28), ("D5 rzeczywisty stan wiedzy decydenta", 16),
                             ("D6 wymagany stan wiedzy decydenta", 11), ("D7 potrzeba wykwalifikowanego analityka", 11),
                             ("T4 przewidywanie najlepszego wariantu", 19), ("T6 stosowalność do rzeczywistych problemów", 19),
                             ("T8 łatwość użycia", 14), ("T11 łatwość kodowania", 7), ("T12 ciężar obliczeniowy", 2),
                             ("T13 wymagany czas interakcji", 14), ("T14 wymagany czas pracy komputera", 2),
                             ("T16 wymagane charakterystyki parametrów", 14), ("T20 specjalne oprogramowanie", 9),
                             ("S1 typ rozwiązania", 15), ("S4 zupełny ranking", 15), ("S5 kardynalny ranking", 5),
                             ("S6 spójność rozwiązań", 15), ("S8 zaufanie do rozwiązania", 25),
                             ("S9 użyteczność rozwiązania", 25))],
                         "values": [list(r) for r in zip(
                             [1] * 7, [1] * 7, [4, 10, 10, 10, 10, 4, 4], [10, 8, 8, 8, 6, 10, 10],
                             [10, 7, 7, 7, 5, 10, 10], [10, 1, 2, 2, 2, 8, 8], [10, 6, 6, 6, 2, 10, 10],
                             [10, 4, 5, 5, 5, 9, 9], [3, 7, 8, 9, 10, 4, 4], [5, 7, 10, 10, 10, 4, 4],
                             [10, 1, 3, 2, 2, 9, 8], [10, 4, 6, 6, 6, 9, 9], [10, 7, 8, 8, 8, 10, 10],
                             [10, 6, 6, 6, 2, 10, 10], [10, 8, 9, 9, 9, 10, 10], [10, 7, 7, 7, 4, 10, 10],
                             [10, 1, 2, 2, 2, 8, 8], [10, 4, 7, 10, 10, 10, 10], [10, 5, 10, 10, 10, 10, 10],
                             [10, 0, 0, 10, 10, 10, 10], [10, 8, 10, 10, 10, 10, 10], [6, 9, 10, 10, 10, 5, 5],
                             [7, 4, 7, 10, 10, 7, 7])]}},
    "P3.12": {"title": "Przykład 3.12 — ANP, wybór projektu inwestycyjnego", "method": "anp", "options": {},
              "problem": {"name": "Przykład 3.12", "variants": ["a1", "a2"], "criteria": _CRIT_312, **_NET_312,
                          "cluster_comparisons": {"AS": {"clusters": ["AT", "W"], "matrix": [[1, 5], [None, 1]]},
                                                  "AT": {"clusters": ["AS", "W"], "matrix": [[1, "1/3"], [None, 1]]},
                                                  "W": {"clusters": ["AS", "AT"], "matrix": [[1, 1], [None, 1]]}}}},
    "P3.13": {"title": "Przykład 3.13 — ANP, synteza BOCR (priorytety podsieci z Super Decisions)", "method": "anp",
              "options": {"formula": "multiplicative"},
              "problem": {"name": "Wybór dostawcy", "variants": ["obecny dostawca", "dostawca X", "dostawca Y", "dostawca Z"],
                          "criteria": [], "subnets": {k: {"priorities": v} for k, v in _BOCR_313.items()}}},
    "P3.14": {"title": "Przykład 3.14 — rozmyta ANP (porównania komponentów w skali Changa)", "method": "fuzzy_anp",
              "options": {},
              "problem": {"name": "Przykład 3.14", "variants": ["a1", "a2"], "criteria": _CRIT_312, **_NET_312,
                          "cluster_comparisons": {
                              "AS": {"clusters": ["AT", "W"], "matrix": [[1, "silnie ważniejsze"], [None, 1]]},
                              "AT": {"clusters": ["AS", "W"], "matrix": [[1, None], ["umiarkowanie ważniejsze", 1]]},
                              "W": {"clusters": ["AS", "AT"], "matrix": [[1, "równoważne"], [None, 1]]}}}},
    "P4.2": {"title": "Przykład 4.2 — MACBETH: wagi kryteriów z ocen różnic istotności", "method": "macbeth_scale",
             "options": {},
             "problem": {"name": "Zakup mieszkania (Pan Hieronim)",
                         "variants": ["f1 cena lokalu", "f2 powierzchnia", "f3 układ pomieszczeń", "f4 czas dojazdu"],
                         "criteria": [],
                         "judgements": [[0, "duża", "duża", "bardzo duża"], [None, 0, "bardzo mała", "umiarkowana"],
                                        [None, None, 0, "mała"], [None, None, None, 0]]}},
    "P4.3": {"title": "Przykład 4.3 — MACBETH (dane z programu M-MACBETH; przekątna i kolor jako gotowe oceny)",
             "method": "macbeth", "options": {}, "problem": _P43},
    "P4.5": {"title": "Przykład 4.5 — ZAPROS: porównanie dwóch kandydatów przez JOS", "method": "zapros",
             "options": {},
             "problem": {"name": "Konkurs na stanowisko adiunkta", "variants": ["Katarzyna", "Wojciech"],
                         "criteria": [{"name": f"f{k + 1}", "scale": _ZS("ABCDEF"[k])} for k in range(6)],
                         "values": [["A2", "B2", "C1", "D1", "E1", "F1"], ["A1", "B1", "C2", "D2", "E1", "F1"]],
                         "jos": [["A1", "B1", "C1", "D1", "E1", "F1"], ["C2", "E2"], ["A2", "D2", "F2"], ["B2"],
                                 ["B3", "E3", "F3"], ["A3", "C3", "D3"]]}},
    "P4.6": {"title": "Przykład 4.6 — ZAPROS (JOS z porównań wektorów, porządek częściowy)", "method": "zapros",
             "options": {},
             "problem": {"name": "Wybór kandydata (6 osób)", "variants": [f"a{i}" for i in range(1, 7)],
                         "criteria": _CRIT_ZAPROS, "values": _V46, "y_comparisons": _Y46}},
    "P4.7": {"title": "Przykład 4.7 — ZAPROS III: porównanie par kandydatów (JSQV → JSCV)", "method": "zapros_iii",
             "options": {},
             "problem": {"name": "Konkurs na asystenta", "variants": ["Zofia", "Kazimierz", "Karolina", "Marek"],
                         "criteria": _CRIT_ZAPROS,
                         "values": [["A3", "B1", "C2"], ["A2", "B2", "C1"], ["A1", "B2", "C3"], ["A3", "B3", "C1"]],
                         "jsqv": [["A1>A2", "B1>B2", "A1>A3", "B1>B3", "A2>A3", "B2>B3"],
                                  ["C1>C2", "B1>B2", "B1>B3", "C1>C3", "B2>B3", "C2>C3"],
                                  ["C1>C2", "A1>A2", "A1>A3", "C1>C3", "A2>A3", "C2>C3"]]}},
    "P4.8": {"title": "Przykład 4.8 — ZAPROS III (porównania wariacji, FIQ, rangi)", "method": "zapros_iii",
             "options": {},
             "problem": {"name": "Wybór kandydata (9 osób)", "variants": [f"K{i}" for i in range(1, 10)],
                         "criteria": _CRIT_ZAPROS,
                         "values": _V46 + [["A3", "B2", "C1"], ["A3", "B3", "C1"], ["A2", "B1", "C2"]],
                         "qv_comparisons": [
                             {"qv": ["A1>A2", "A1>A3", "A2>A3", "B1>B2", "B1>B3", "B2>B3"], "matrix": _QV_TABLE},
                             {"qv": ["B1>B2", "B1>B3", "B2>B3", "C1>C2", "C1>C3", "C2>C3"], "matrix": _QV_TABLE_C},
                             {"qv": ["A1>A2", "A1>A3", "A2>A3", "C1>C2", "C1>C3", "C2>C3"], "matrix": _QV_TABLE_C}]}},
    "P5.10": {"title": "Przykład 5.10 — ELECTRE I", "method": "electre_i", "options": {"s": 0.83, "v": 6},
              "problem": {"name": "Przykład 5.10", "variants": [f"a{i}" for i in range(1, 10)], "criteria": _C5,
                          "values": _X5}},
    "P5.11": {"title": "Przykład 5.11 — ELECTRE Iv (progi weta kryteriów)", "method": "electre_iv",
              "options": {"s": 0.83},
              "problem": {"name": "Przykład 5.11", "variants": [f"a{i}" for i in range(1, 10)], "criteria": _C5V,
                          "values": _X5}},
    "P5.12": {"title": "Przykład 5.12 — ELECTRE Is", "method": "electre_is", "options": {"s": 0.83},
              "problem": {"name": "Przykład 5.12", "variants": [f"a{i}" for i in range(1, 10)], "criteria": _C5V,
                          "values": _X5}},
    "P5.13": {"title": "Przykład 5.13 — ELECTRE III (destylacje, ranking końcowy)", "method": "electre_iii",
              "options": {}, "problem": {"name": "Przykład 5.13", "variants": _V6, "criteria": _C5III,
                                         "values": _X513}},
    "P5.14": {"title": "Przykład 5.14 — ELECTRE III (dane programu ELECTRE III/IV)", "method": "electre_iii",
              "options": {}, "problem": {"name": "Przykład 5.14", "variants": _V6, "criteria": _C5III,
                                         "values": [_X513[0], [4, 8, 5, 2]] + _X513[2:]}},
    "P5.15": {"title": "Przykład 5.15 — ELECTRE TRI, procedura pesymistyczna", "method": "electre_tri",
              "options": {"cut": 0.75, "procedure": "pessimistic"}, "problem": _tri("Przykład 5.15")},
    "P5.16": {"title": "Przykład 5.16 — ELECTRE TRI, procedura optymistyczna", "method": "electre_tri",
              "options": {"cut": 0.75, "procedure": "optimistic"}, "problem": _tri("Przykład 5.16")},
    "P5.19": {"title": "Przykład 5.19 — ELECTRE I z dominacjami stochastycznymi (s = 0,75, para niejasna włączona)",
              "method": "electre_i_sd", "options": {"s": 0.75, "risk": "DARA", "include_unclear": True},
              "problem": {"name": "Przykład 5.19", "variants": [f"a{i}" for i in range(1, 6)],
                          "criteria": [{"name": c["name"], "weight": c["weight"]} for c in _C_611],
                          "values": _dist_611()}},
    "P5.20": {"title": "Przykład 5.20 — ELECTRE III z dominacjami stochastycznymi", "method": "electre_iii_sd",
              "options": {"risk": "DARA"},
              "problem": {"name": "Przykład 5.20", "variants": [f"a{i}" for i in range(1, 6)], "criteria": _C_611,
                          "values": _dist_611()}},
    "P6.2": {"title": "Przykład 6.2 — PROMETHEE I (kryteria typów 5, 4, 3, 1)", "method": "promethee_i", "options": {},
             "problem": {"name": "Przykład 6.2", "variants": [f"a{i}" for i in range(1, 8)],
                         "criteria": [{"name": "f1", "weight": 0.4, "type": 5, "q": 5, "p": 10},
                                      {"name": "f2", "weight": 0.1, "type": 4, "q": 3, "p": 5},
                                      {"name": "f3", "weight": 0.3, "type": 3, "p": 2},
                                      {"name": "f4", "weight": 0.2, "type": 1}],
                         "values": [[10, 5, 3, 0], [65, 0, 1, 1], [25, 15, 2, 1], [9, 2, 3, 0], [200, 0, 2, 1],
                                    [74, 1, 1, 0], [36, 2, 1, 1]]}},
    "P6.4": {"title": "Przykład 6.4 — PROMETHEE II (kryteria typu 1)", "method": "promethee_ii", "options": {},
             "problem": {"name": "Przykład 6.4", "variants": [f"a{i}" for i in range(1, 6)],
                         "criteria": [{"name": c["name"], "weight": c["weight"]} for c in _C_67], "values": _X_67}},
    "P6.5": {"title": "Przykład 6.5 — PROMETHEE II, kryteria wszystkich sześciu typów", "method": "promethee_ii",
             "options": {},
             "problem": {"name": "Projekty rozwoju regionalnego", "variants": ["a1", "a2", "a3", "a4"],
                         "criteria": _C_65, "values": _X_65}},
    "P6.7": {"title": "Przykład 6.7 — PROMETHEE II z progami weta", "method": "promethee_ii_veto", "options": {},
             "problem": {"name": "Przykład 6.7", "variants": [f"a{i}" for i in range(1, 6)], "criteria": _C_67,
                         "values": _X_67}},
    "P6.8": {"title": "Przykład 6.8 — EXPROM II", "method": "exprom", "options": {},
             "problem": {"name": "Przykład 6.8", "variants": ["a1", "a2", "a3", "a4"],
                         "criteria": [{"name": "f1", "weight": 0.6}, {"name": "f2", "weight": 0.1},
                                      {"name": "f3", "weight": 0.3}],
                         "values": [[30, 34, 4], [4, 5, 39], [40, 18, 33], [44, 20, 3]]}},
    "P6.10": {"title": "Przykład 6.10 — EXPROM II z progami weta", "method": "exprom_veto", "options": {},
              "problem": {"name": "Przykład 6.10", "variants": [f"a{i}" for i in range(1, 6)], "criteria": _C_67,
                          "values": _X_67}},
    "P6.11": {"title": "Przykład 6.11 — PROMETHEE II z progami weta i dominacjami stochastycznymi",
              "method": "promethee_ii_sd", "options": {"risk": "DARA"},
              "problem": {"name": "Przykład 6.11", "variants": [f"a{i}" for i in range(1, 6)], "criteria": _C_611,
                          "values": _dist_611()}},
    "P6.12": {"title": "Przykład 6.12 — PROMETHEE II z wetem i porządkowymi (prawie) dominacjami stochastycznymi",
              "method": "promethee_ii_sd", "options": {"dominances": ["FSD", "SSD", "AFSD:0.333", "ASSD:0.2"]},
              "problem": {"name": "Ocena 8 wariantów przez 3 osoby", "variants": _V8,
                          "criteria": [{"name": "f1", "weight": 0.27, "q": 1, "p": 3, "v": 6},
                                       {"name": "f2", "weight": 0.39, "q": 1, "p": 3, "v": 5},
                                       {"name": "f3", "weight": 0.34, "q": 2, "p": 4, "v": 7}],
                          "values": _obs(_OBS_612)}},
    "P6.14": {"title": "Przykład 6.14 — EXPROM II z progami weta i dominacjami stochastycznymi",
              "method": "exprom_ii_sd", "options": {"risk": "DARA"},
              "problem": {"name": "Przykład 6.14", "variants": [f"a{i}" for i in range(1, 6)], "criteria": _C_611,
                          "values": _dist_611()}},
    "P6.16": {"title": "Przykład 6.16 — EXPROM II z wetem i porządkowymi (prawie) dominacjami stochastycznymi",
              "method": "exprom_ii_sd", "options": {"dominances": ["FSD", "SSD", "AFSD:0.2", "ASSD:0.125"]},
              "problem": {"name": "Ocena 8 wariantów przez 5 osób", "variants": _V8,
                          "criteria": [{"name": "f1", "weight": 0.4, "q": 1, "p": 3, "v": 6},
                                       {"name": "f2", "weight": 0.1, "q": 2, "p": 4, "v": 8},
                                       {"name": "f3", "weight": 0.5, "q": 1, "p": 2, "v": 5}],
                          "values": _obs(_OBS_616)}},
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
    "P7.5": {"title": "Przykład 7.5 — DEMATEL (aspekty renowacji organów)", "method": "dematel", "options": {},
             "problem": {"name": "Przykład 7.5", "variants": ["C1 wartości historyczne", "C2 wartości artystyczne",
                                                             "C3 wartości muzyczne", "C4 wartości użytkowe"],
                         "criteria": [], "influence": _O163}},
    "P7.6": {"title": "Przykład 7.6 — metoda hybrydowa DEMATEL–ANP–VIKOR (renowacja organów)", "method": "hybrid",
             "options": {"alpha": 0.1, "ideal": [10] * 12, "anti_ideal": [0] * 12},
             "problem": {"name": "Renowacja pozytywu z Sokół (rozdz. 16)", "variants": [f"a{i}" for i in range(1, 13)],
                         "criteria": [{"name": c, "cluster": g} for c, g in zip(_C16, _G16)],
                         "values": [list(r) for r in zip(*_T161)], "cluster_influence": _O163,
                         "criteria_influence": _O164}},
    "P7.7": {"title": "Przykład 7.7 — BIPOLAR (dane z rys. 1; test weta jak w przykładzie)", "method": "bipolar",
             "options": {"s": 0.5, "veto_test": "example"}, "problem": _bip79("Przykład 7.7")},
    "P7.8": {"title": "Przykład 7.8 — BIPOLAR (2)", "method": "bipolar", "options": {"s": 0.4},
             "problem": {"name": "Przykład 7.8", "variants": [f"a{i}" for i in range(1, 8)],
                         "criteria": [{"name": f"f{k}", "weight": 0.25, "v": 1, **({"q": 0.1} if k < 3 else {})}
                                      for k in range(1, 5)],
                         "values": [[15, 15, 15, 10], [20, 15, 10, 10], [30, 8, 30, 30], [10, 6, 10, 10], [6, 6, 6, 6],
                                    [6, 3, 3, 3], [3, 3, 3, 3]],
                         "good": [[15, 15, 15, 15], [8, 10, 15, 20]], "bad": [[5, 5, 5, 5]]}},
    "P7.10": {"title": "Przykład 7.10 — BIPOLAR, modyfikacja zbioru obiektów „dobrych”", "method": "bipolar",
              "options": {"s": 0.5, "veto_test": "example", "modify": "good"}, "problem": _bip79("Przykład 7.10")},
    "P7.11": {"title": "Przykład 7.11 — BIPOLAR, modyfikacja zbioru obiektów „złych”", "method": "bipolar",
              "options": {"s": 0.5, "veto_test": "example", "modify": "bad"}, "problem": _bip79("Przykład 7.11")},
    "P7.12": {"title": "Przykład 7.12 — BIPOLAR, kategoria B2′", "method": "bipolar",
              "options": {"s": 0.5, "veto_test": "example", "b2_prime": True}, "problem": _bip79("Przykład 7.12")},
    "P7.13": {"title": "Przykład 7.13 — BIPOLAR dla dużego systemu referencyjnego (funkcje lokalnej preferencji)",
              "method": "bipolar",
              "options": {"s": 0.1, "weights": "objects", "veto_decile": 1, "local_preference": True,
                          "position": "counts"}, "problem": _bip713("Przykład 7.13")},
    "P7.15": {"title": "Przykład 7.15 — zmodyfikowany BIPOLAR, wariant klasyczny (wagi z decyli)", "method": "bipolar",
              "options": {"s": 0.5, "weights": "deciles"}, "problem": _bip713("Przykład 7.15", v=1)},
    "P7.16": {"title": "Przykład 7.16 — BIPOLAR z porządkowymi (prawie) dominacjami stochastycznymi",
              "method": "bipolar_sd", "options": {"dominances": ["FSD", "SSD", "AFSD:0.333", "ASSD:0.2"]},
              "problem": {"name": "Ocena 8 wariantów przez 3 osoby", "variants": _V8,
                          "criteria": [{"name": "f1", "weight": 0.27, "q": 1, "p": 3, "v": 3},
                                       {"name": "f2", "weight": 0.39, "q": 1, "p": 3, "v": 3},
                                       {"name": "f3", "weight": 0.34, "q": 2, "p": 4, "v": 3}],
                          "values": _obs(_OBS_612),
                          "good": [[{"obs": [9, 9, 9]}] * 3, [{"obs": [6, 7, 8]}, {"obs": [7, 7, 8]}, {"obs": [7, 7, 7]}]],
                          "bad": [[{"obs": [4, 4, 4]}, {"obs": [4, 4, 4]}, {"obs": [4, 5, 6]}], [{"obs": [5, 5, 5]}] * 3]}},
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
    "R9.5": {"title": "Rozdz. 9 (R9.5) — PROMETHEE II z progami weta, projekty RPO WK-P", "method": "promethee_ii_veto",
             "options": {}, "problem": _P_R95},
    "R9.5E": {"title": "Rozdz. 9 (R9.5) — EXPROM II z progami weta, projekty RPO WK-P", "method": "exprom_veto",
              "options": {}, "problem": _P_R95},
    "R11": {"title": "Rozdz. 11 — ANP, wybór systemu ERP (supermacierz R11.1, wagi komponentów tabl. 11.8)",
            "method": "anp", "options": {},
            "problem": {"name": "Wybór systemu klasy ERP", "variants": ["IFS", "IM5", "SAP"],
                        "criteria": [e for e in _R11_EL if e not in ("IFS", "IM5", "SAP")], "clusters": _R11_CL,
                        "comparisons": _anp_from_supermatrix(_R11_M, _R11_EL, _R11_CL, ["IFS", "IM5", "SAP"]),
                        "cluster_weights": [[0.2542, 0.4539, 0.1728, 0.5609], [0.5790, 0.3531, 0.1301, 0.1898],
                                            [0.0808, 0.0752, 0.4331, 0.1783], [0.0860, 0.1178, 0.2640, 0.0710]]}},
    "R15": {"title": "Rozdz. 15 — PROMETHEE II, premiowy system motywacji (51 pracowników, tabl. 15.4)",
            "method": "promethee_ii", "options": {},
            "problem": {"name": "Pracownicy call center po selekcji", "variants": [r[0] for r in _R15],
                        "criteria": [{"name": "f1 (efektywność)", "weight": 0.57, "type": 5, "q": 0.1, "p": 0.98},
                                     {"name": "f2 (sprzedaż)", "weight": 0.10, "type": 5, "q": 9.1, "p": 82},
                                     {"name": "f3 (jakość)", "weight": 0.33, "type": 5, "q": 0.1, "p": 0.9}],
                        "values": [list(r[1:]) for r in _R15]}},
    "R16": {"title": "Rozdz. 16 — ELECTRE I, renowacja organów (s = 0,72, bez weta)", "method": "electre_i",
            "options": {"s": 0.72, "v": 10},
            "problem": {"name": "Warianty rekonstrukcji organów", "variants": [f"a{i}" for i in range(1, 13)],
                        "criteria": [{"name": n, "weight": w} for n, w in zip(_R16_NAMES, _R16_W)],
                        "values": [[_R16_T[k][i] for k in range(12)] for i in range(12)]}},
}


def listing():
    return [{"id": k, "title": v["title"], "method": v["method"]} for k, v in EXAMPLES.items()]


def get(name: str) -> Dict[str, Any]:
    if name not in EXAMPLES:
        raise KeyError(f"Nieznany przykład {name!r}; dostępne: {', '.join(EXAMPLES)}")
    e = copy.deepcopy(EXAMPLES[name])
    return {"method": e["method"], "options": e["options"], "problem": e["problem"], "title": e["title"]}
