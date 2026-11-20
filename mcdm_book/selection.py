"""Wybór metody wielokryterialnej (rozdz. 9.3): programowanie kompromisowe (9.1) w modelu Gershona
i procedurze Tecle'a oraz dobór metody pakietu do profilu problemu.

compromise(p)   — odległość L1 od rozwiązania idealnego (9.1) z kryteriami obowiązkowymi (eliminującymi);
select(profile) — buduje zadanie typu Gershona: warianty = metody pakietu, kryteria = cechy problemu
                  (obowiązkowe: rodzaj danych, wymagana postać wyniku; punktowane 0–10 z wagami
                  wynikającymi z profilu) i rozwiązuje je przez compromise.

Oceny metod w katalogu METHOD_PROFILES: dla SAW, SMART, TOPSIS (i częściowo ELECTRE III, PROMETHEE II, EXPROM II) oparte na zbiorze R9.2 (D. Górecka),
dla pozostałych — oceny własne autora pakietu przez analogię; można je nadpisać (opcja `scores`).
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Sequence

from .additive import _result
from .problem import Problem, ProblemError, crisp_matrix, ranking, ranks

# ---------------------------------------------------------------------------
# Programowanie kompromisowe (9.1)
# ---------------------------------------------------------------------------


def compromise(p: Problem, ideal: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    """L1(a^i) = Σ_k w_k (f_k(a*) − f_k(a^i)) / (f_k(a*) − f_k(a_*))  (9.1).

    f_k(a*) — wartość optymalna (`ideal`, domyślnie najlepsza ocena w danych), f_k(a_*) — najgorsza ocena
    osiągnięta przez warianty niewyeliminowane. Kryterium z polem "mandatory": true eliminuje wariant,
    który nie osiąga wartości optymalnej (kryteria obowiązkowe modelu Gershona); takie kryterium nie
    wchodzi do sumy. Kryterium, dla którego wszystkie warianty mają tę samą ocenę, wnosi 0."""
    notes: list = []
    X = crisp_matrix(p)
    n = p.n
    if ideal is not None and len(ideal) != n:
        raise ProblemError("ideal musi mieć po jednej wartości na kryterium")
    best = [float(ideal[k]) if ideal is not None else
            (max(r[k] for r in X) if c.maximize else min(r[k] for r in X)) for k, c in enumerate(p.criteria)]
    mandatory = [bool(c.extra.get("mandatory")) for c in p.criteria]
    eliminated: Dict[str, List[str]] = {}
    for i, v in enumerate(p.variants):
        failed = [p.criteria[k].name for k in range(n) if mandatory[k] and
                  (X[i][k] < best[k] - 1e-12 if p.criteria[k].maximize else X[i][k] > best[k] + 1e-12)]
        if failed:
            eliminated[v] = failed
    active = [i for i, v in enumerate(p.variants) if v not in eliminated]
    if not active:
        notes.append("Wszystkie warianty wyeliminowane przez kryteria obowiązkowe.")
    w = []
    for c, mand in zip(p.criteria, mandatory):
        if mand:
            w.append(0.0)
        elif c.weight is None:
            raise ProblemError(f"Kryterium {c.name}: brak wagi (pole \"weight\")")
        else:
            w.append(float(c.weight))
    pool = active or list(range(p.m))
    worst = [min(X[i][k] for i in pool) if c.maximize else max(X[i][k] for i in pool)
             for k, c in enumerate(p.criteria)]
    contrib = [[0.0] * n for _ in range(p.m)]
    L = []
    for i in range(p.m):
        s = 0.0
        for k in range(n):
            if mandatory[k] or best[k] == worst[k]:
                continue
            contrib[i][k] = w[k] * (best[k] - X[i][k]) / (best[k] - worst[k])
            s += contrib[i][k]
        L.append(s if i in active else float("inf"))
    if eliminated:
        notes.append("Wyeliminowane przez kryteria obowiązkowe: " +
                     "; ".join(f"{v} ({', '.join(f)})" for v, f in eliminated.items()) + ".")
    scores = [x if x != float("inf") else None for x in L]
    key = [x if x is not None else 1e300 for x in scores]
    rk = ranks(key, descending=False)
    order = [v for v in ranking(p.variants, key, descending=False) if v not in eliminated]
    best_v = [p.variants[i] for i in active if rk[i] == 1]
    return {"method": "compromise", "variants": p.variants, "criteria": [c.name for c in p.criteria],
            "scores": {"label": "L1 (odległość od rozwiązania idealnego, im mniej, tym lepiej)",
                       "values": scores, "better": "lower"},
            "ranks": [r if p.variants[i] not in eliminated else None for i, r in enumerate(rk)],
            "ranking": order, "best": best_v,
            "steps": {"ideal": best, "worst": worst, "weights": w, "mandatory": mandatory,
                      "contributions": contrib, "eliminated": eliminated},
            "notes": notes}


# ---------------------------------------------------------------------------
# Katalog metod pakietu
# ---------------------------------------------------------------------------

# Cechy binarne: dane, które metoda przyjmuje, i postać wyniku.
#   numeric — oceny liczbowe; qualitative — oceny jakościowe (porównania parami lub ocena bezpośrednia 0–100);
#   fuzzy — oceny lub porównania niepewne (trójki); stochastic — rozkłady prawdopodobieństwa;
#   ranking — pełny ranking wszystkich wariantów; cardinal — wynik liczbowy z interpretacją odległości między
#   wariantami; reference — punkty odniesienia (ideał, poziomy aspiracji i rezerwacji); dependence — zależności
#   między kryteriami oraz między kryteriami i wariantami (sieć ANP).
# Sposób pozyskania preferencji (natywny): weights, swing, ranks, pairwise, fuzzy_weights, points, dialog.
# Oceny 0–10 (więcej = lepiej): transparency — łatwość zrozumienia i wyjaśnienia wyniku; knowledge — niska
#   wymagana wiedza decydenta; effort — mały wysiłek i czas interakcji; noncomp — ograniczenie kompensacji;
#   uncertainty — uwzględnienie niepewności ocen lub preferencji; consistency — kontrola spójności ocen.
METHOD_PROFILES: Dict[str, Dict[str, Any]] = {
    "saw": {"title": "SAW (2.1)", "caps": {"numeric", "ranking", "cardinal"}, "elicit": {"weights"},
            "grades": {"transparency": 10, "knowledge": 10, "effort": 10, "noncomp": 2, "uncertainty": 0, "consistency": 4},
            "source": "R9.2 (średnia z ważonych sum)"},
    "scoring": {"title": "Metoda scoringowa (2.1)", "caps": {"numeric", "qualitative", "ranking", "cardinal"},
                "elicit": {"points"},
                "grades": {"transparency": 10, "knowledge": 10, "effort": 8, "noncomp": 2, "uncertainty": 0, "consistency": 3},
                "source": "własne"},
    "fsaw": {"title": "FSAW (2.2)", "caps": {"numeric", "ranking", "cardinal"}, "elicit": {"fuzzy_weights"},
             "grades": {"transparency": 7, "knowledge": 7, "effort": 8, "noncomp": 2, "uncertainty": 6, "consistency": 4},
             "source": "własne"},
    "smart": {"title": "SMART (2.3)", "caps": {"numeric", "qualitative", "ranking", "cardinal"}, "elicit": {"swing"},
              "grades": {"transparency": 8, "knowledge": 10, "effort": 6, "noncomp": 3, "uncertainty": 0, "consistency": 5},
              "source": "R9.2"},
    "smarter": {"title": "SMARTER (2.4)", "caps": {"numeric", "qualitative", "ranking", "cardinal"}, "elicit": {"ranks"},
                "grades": {"transparency": 8, "knowledge": 10, "effort": 9, "noncomp": 3, "uncertainty": 0, "consistency": 5},
                "source": "własne (analogia do R9.2: SMART)"},
    "ahp": {"title": "AHP (3.1)", "caps": {"numeric", "qualitative", "ranking", "cardinal"}, "elicit": {"pairwise"},
            "grades": {"transparency": 6, "knowledge": 7, "effort": 4, "noncomp": 2, "uncertainty": 2, "consistency": 9},
            "source": "własne"},
    "rembrandt": {"title": "REMBRANDT (3.2)", "caps": {"numeric", "qualitative", "ranking", "cardinal"},
                  "elicit": {"pairwise"},
                  "grades": {"transparency": 5, "knowledge": 5, "effort": 4, "noncomp": 3, "uncertainty": 2, "consistency": 6},
                  "source": "własne"},
    "fuzzy_ahp": {"title": "Rozmyty AHP (3.3)", "caps": {"numeric", "qualitative", "fuzzy", "ranking", "cardinal"},
                  "elicit": {"pairwise"},
                  "grades": {"transparency": 4, "knowledge": 4, "effort": 3, "noncomp": 2, "uncertainty": 8, "consistency": 8},
                  "source": "własne"},
    "anp": {"title": "ANP (3.4)", "caps": {"numeric", "qualitative", "ranking", "cardinal", "dependence"},
            "elicit": {"pairwise"},
            "grades": {"transparency": 3, "knowledge": 3, "effort": 2, "noncomp": 2, "uncertainty": 2, "consistency": 9},
            "source": "własne"},
    "fuzzy_anp": {"title": "Rozmyta ANP (3.5)",
                  "caps": {"numeric", "qualitative", "fuzzy", "ranking", "cardinal", "dependence"},
                  "elicit": {"pairwise"},
                  "grades": {"transparency": 2, "knowledge": 2, "effort": 2, "noncomp": 2, "uncertainty": 7, "consistency": 6},
                  "source": "własne"},
    "electre_i": {"title": "ELECTRE I (5.2)", "caps": {"numeric"}, "elicit": {"weights"},
                  "grades": {"transparency": 4, "knowledge": 6, "effort": 6, "noncomp": 9, "uncertainty": 1, "consistency": 4},
                  "source": "własne (analogia do R9.2: ELECTRE III)"},
    "electre_iv": {"title": "ELECTRE Iv (5.2)", "caps": {"numeric"}, "elicit": {"weights"},
                   "grades": {"transparency": 4, "knowledge": 6, "effort": 6, "noncomp": 10, "uncertainty": 1, "consistency": 4},
                   "source": "własne (analogia do R9.2: ELECTRE III)"},
    "electre_is": {"title": "ELECTRE Is (5.2)", "caps": {"numeric"}, "elicit": {"weights"},
                   "grades": {"transparency": 3, "knowledge": 6, "effort": 6, "noncomp": 10, "uncertainty": 4, "consistency": 4},
                   "source": "własne (analogia do R9.2: ELECTRE III)"},
    "electre_iii": {"title": "ELECTRE III (5.3)", "caps": {"numeric"}, "elicit": {"weights"},
                    "grades": {"transparency": 2, "knowledge": 6, "effort": 6, "noncomp": 10, "uncertainty": 4, "consistency": 4},
                    "source": "R9.2 (transparency, knowledge, effort; brak kompletnego rankingu); pozostałe własne"},
    "electre_tri": {"title": "ELECTRE TRI (5.4)", "caps": {"numeric", "sorting"}, "elicit": {"weights"},
                    "grades": {"transparency": 3, "knowledge": 6, "effort": 5, "noncomp": 10, "uncertainty": 4, "consistency": 4},
                    "source": "własne (analogia do R9.2: ELECTRE III)"},
    "electre_i_sd": {"title": "ELECTRE I z dominacjami stochastycznymi (5.5)", "caps": {"stochastic"},
                     "elicit": {"weights"},
                     "grades": {"transparency": 3, "knowledge": 3, "effort": 4, "noncomp": 9, "uncertainty": 10, "consistency": 4},
                     "source": "własne"},
    "electre_iii_sd": {"title": "ELECTRE III z dominacjami stochastycznymi (5.6)", "caps": {"stochastic"},
                       "elicit": {"weights"},
                       "grades": {"transparency": 2, "knowledge": 3, "effort": 5, "noncomp": 10, "uncertainty": 10, "consistency": 5},
                       "source": "własne (analogia do R9.2: ELECTRE III)"},
    "promethee_i": {"title": "PROMETHEE I (6.2)", "caps": {"numeric"}, "elicit": {"weights"},
                    "grades": {"transparency": 3, "knowledge": 6, "effort": 6, "noncomp": 6, "uncertainty": 3, "consistency": 4},
                    "source": "R9.2 (PROMETHEE II: transparency, knowledge, effort); pozostałe własne"},
    "promethee_ii": {"title": "PROMETHEE II (6.2)", "caps": {"numeric", "ranking"}, "elicit": {"weights"},
                     "grades": {"transparency": 3, "knowledge": 6, "effort": 6, "noncomp": 6, "uncertainty": 3, "consistency": 4},
                     "source": "R9.2 (transparency, knowledge, effort); pozostałe własne"},
    "promethee_ii_veto": {"title": "PROMETHEE II z progami weta (6.3)", "caps": {"numeric", "ranking"},
                          "elicit": {"weights"}, "grades": {"transparency": 3, "knowledge": 6, "effort": 6, "noncomp": 9, "uncertainty": 3, "consistency": 4},
                          "source": "R9.2 (PROMETHEE II: transparency, knowledge, effort); pozostałe własne"},
    "exprom": {"title": "EXPROM II (6.4)", "caps": {"numeric", "ranking", "cardinal"}, "elicit": {"weights"},
               "grades": {"transparency": 3, "knowledge": 6, "effort": 6, "noncomp": 6, "uncertainty": 3, "consistency": 4},
               "source": "R9.2 (transparency, knowledge, effort); pozostałe własne"},
    "exprom_veto": {"title": "EXPROM II z progami weta (6.5)", "caps": {"numeric", "ranking", "cardinal"},
                    "elicit": {"weights"}, "grades": {"transparency": 3, "knowledge": 6, "effort": 6, "noncomp": 9, "uncertainty": 3, "consistency": 4},
                    "source": "R9.2 (EXPROM II: transparency, knowledge, effort); pozostałe własne"},
    "promethee_ii_sd": {"title": "PROMETHEE II z wetem i dominacjami stochastycznymi (6.6)",
                        "caps": {"stochastic", "ranking"}, "elicit": {"weights"},
                        "grades": {"transparency": 2, "knowledge": 3, "effort": 5, "noncomp": 9, "uncertainty": 10,
                                   "consistency": 5},
                        "source": "własne"},
    "exprom_ii_sd": {"title": "EXPROM II z wetem i dominacjami stochastycznymi (6.7)",
                     "caps": {"stochastic", "ranking", "cardinal"}, "elicit": {"weights"},
                     "grades": {"transparency": 2, "knowledge": 3, "effort": 5, "noncomp": 9, "uncertainty": 10,
                                "consistency": 5},
                     "source": "własne"},
    "topsis": {"title": "TOPSIS (7.1)", "caps": {"numeric", "ranking", "cardinal", "reference"}, "elicit": {"weights"},
               "grades": {"transparency": 6, "knowledge": 10, "effort": 10, "noncomp": 3, "uncertainty": 0, "consistency": 4},
               "source": "R9.2"},
    "fuzzy_topsis": {"title": "Rozmyty TOPSIS (7.2)", "caps": {"numeric", "fuzzy", "ranking", "cardinal", "reference"},
                     "elicit": {"weights"},
                     "grades": {"transparency": 5, "knowledge": 7, "effort": 8, "noncomp": 3, "uncertainty": 8, "consistency": 4},
                     "source": "własne (analogia do R9.2: TOPSIS)"},
    "vikor": {"title": "VIKOR (7.3)", "caps": {"numeric", "ranking", "cardinal", "reference"}, "elicit": {"weights"},
              "grades": {"transparency": 6, "knowledge": 7, "effort": 9, "noncomp": 7, "uncertainty": 0, "consistency": 6},
              "source": "własne"},
    "stochastic_dominance": {"title": "Dominacje stochastyczne (1.3, mcdm_cd)", "caps": {"stochastic"},
                             "elicit": set(), "no_preferences": True,
                             "grades": {"transparency": 4, "knowledge": 3, "effort": 10, "noncomp": 10, "uncertainty": 10,
                                        "consistency": 5},
                             "source": "własne"},
    "stem_dpr": {"title": "STEM-DPR (8.3, mcdm_cd)", "caps": {"stochastic", "reference"}, "elicit": {"dialog"},
                 "grades": {"transparency": 6, "knowledge": 6, "effort": 3, "noncomp": 8, "uncertainty": 10, "consistency": 6},
                 "source": "własne"},
    "insdecm": {"title": "INSDECM (8.4, mcdm_cd)", "caps": {"stochastic", "reference"}, "elicit": {"dialog"},
                "grades": {"transparency": 5, "knowledge": 4, "effort": 2, "noncomp": 9, "uncertainty": 10, "consistency": 8},
                "source": "własne"},
}

GRADE_LABELS = {"transparency": "łatwość zrozumienia i wyjaśnienia wyniku",
                "knowledge": "niska wymagana wiedza decydenta",
                "effort": "mały wysiłek i czas interakcji",
                "noncomp": "ograniczenie kompensacji",
                "uncertainty": "uwzględnienie niepewności",
                "consistency": "kontrola spójności ocen",
                "elicitation": "dopasowanie do informacji o preferencjach, którą decydent może podać",
                "reference": "punkty odniesienia (ideał, aspiracje)"}

LEVEL = {"low": 1, "medium": 3, "high": 5, "niska": 1, "średnia": 3, "wysoka": 5}
WEIGHTABLE = ("weights", "swing", "ranks", "pairwise", "points")   # da się przeliczyć na wagi liczbowe

PROFILE_FIELDS = {
    "data": "rodzaje ocen: lista z numeric, qualitative, fuzzy, stochastic (wymagane)",
    "preferences": "co decydent potrafi podać: lista z weights, swing, ranks, pairwise, fuzzy_weights, points, dialog "
                   "(domyślnie [\"weights\"])",
    "output": "best | ranking | scores | sort — wystarczy najlepszy wariant, potrzebny pełny ranking, wynik liczbowy "
              "albo przypisanie do uporządkowanych kategorii (domyślnie ranking)",
    "compensation": "full | limited — czy dobra ocena może zrównoważyć słabą (domyślnie full)",
    "reference_levels": "true, gdy decydent zna poziomy aspiracji / rezerwacji (domyślnie false)",
    "explain": "low | medium | high — jak ważne jest wyjaśnienie wyniku innym (domyślnie medium)",
    "expertise": "low | medium | high — wiedza decydenta o metodach (domyślnie medium)",
    "time": "low | medium | high — czas decydenta na interakcję (domyślnie medium)",
    "interdependence": "true, gdy kryteria (lub kryteria i warianty) wpływają na siebie i trzeba to uwzględnić "
                       "(domyślnie false)",
}


def _level(profile, key, default="medium"):
    v = str(profile.get(key, default)).lower()
    if v not in LEVEL:
        raise ProblemError(f"profil.{key}: low, medium albo high")
    return LEVEL[v]


def select(profile: Dict[str, Any], scores: Optional[Dict[str, Dict[str, float]]] = None,
           methods: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Ranking metod pakietu dla profilu problemu (model typu Gershona, odległość (9.1))."""
    data = profile.get("data")
    if isinstance(data, str):
        data = [data]
    if not data:
        raise ProblemError("profil.data: podaj rodzaje ocen (numeric, qualitative, fuzzy, stochastic)")
    data = set(data)
    unknown = data - {"numeric", "qualitative", "fuzzy", "stochastic"}
    if unknown:
        raise ProblemError(f"profil.data: nieznane rodzaje {sorted(unknown)}")
    prefs = profile.get("preferences") or ["weights"]
    prefs = {prefs} if isinstance(prefs, str) else set(prefs)
    output = profile.get("output", "ranking")
    if output not in ("best", "ranking", "scores", "sort"):
        raise ProblemError("profil.output: best, ranking, scores albo sort")
    comp = profile.get("compensation", "full")
    if comp not in ("full", "limited"):
        raise ProblemError("profil.compensation: full albo limited")
    cat = copy.deepcopy(METHOD_PROFILES)
    for name, g in (scores or {}).items():
        if name not in cat:
            raise ProblemError(f"scores: nieznana metoda {name!r}")
        cat[name]["grades"].update(g)
        cat[name]["source"] = "podane przez użytkownika"
    names = list(methods) if methods else list(cat)

    # kryteria obowiązkowe (binarne)
    crit: List[Dict[str, Any]] = []
    cols: List[List[float]] = [[] for _ in names]
    reasons: Dict[str, str] = {}

    def mandatory(label, test, why):
        crit.append({"name": label, "mandatory": True})
        for i, mth in enumerate(names):
            ok = test(cat[mth])
            cols[i].append(1.0 if ok else 0.0)
            if not ok:
                reasons.setdefault(mth, why)

    for d in sorted(data):
        if d == "numeric":
            mandatory("dane liczbowe", lambda c: "numeric" in c["caps"] or "stochastic" in c["caps"],
                      "nie przyjmuje ocen liczbowych")
        elif d == "qualitative":
            mandatory("oceny jakościowe", lambda c: "qualitative" in c["caps"], "nie obsługuje ocen jakościowych")
        elif d == "fuzzy":
            mandatory("oceny niepewne (trójki)", lambda c: "fuzzy" in c["caps"], "nie obsługuje ocen rozmytych")
        else:
            mandatory("rozkłady prawdopodobieństwa", lambda c: "stochastic" in c["caps"],
                      "nie obsługuje ocen w postaci rozkładów")
    if "stochastic" not in data:
        mandatory("dane deterministyczne", lambda c: "numeric" in c["caps"],
                  "wymaga ocen w postaci rozkładów prawdopodobieństwa")
    if output == "sort":
        mandatory("sortowanie do kategorii", lambda c: "sorting" in c["caps"],
                  "nie przypisuje wariantów do kategorii")
    else:
        mandatory("wybór / porządkowanie", lambda c: "sorting" not in c["caps"],
                  "przypisuje warianty do kategorii, nie wybiera ani nie porządkuje")
    if output in ("ranking", "scores"):
        mandatory("pełny ranking", lambda c: "ranking" in c["caps"], "nie daje pełnego rankingu wariantów")
    if profile.get("interdependence"):
        mandatory("zależności między kryteriami", lambda c: "dependence" in c["caps"],
                  "zakłada niezależność kryteriów")
    if output == "scores":
        mandatory("wynik liczbowy", lambda c: "cardinal" in c["caps"], "nie daje wyniku liczbowego")

    # kryteria punktowane 0–10
    def graded(key, weight, value_of):
        if weight <= 0:
            return
        crit.append({"name": GRADE_LABELS[key], "weight": weight, "key": key})
        for i, mth in enumerate(names):
            cols[i].append(float(value_of(cat[mth])))

    def elicitation(c):
        if c.get("no_preferences"):
            return 5                      # nie korzysta z informacji o preferencjach (porównuje rozkłady parami)
        if c["elicit"] & prefs:
            return 10
        if "weights" in c["elicit"] and prefs & set(WEIGHTABLE):
            return 6                      # wagi da się wyznaczyć z rang, rozpiętości, porównań (ROC, swing, AHP)
        return 0

    graded("elicitation", 5, elicitation)
    graded("transparency", _level(profile, "explain"), lambda c: c["grades"]["transparency"])
    graded("knowledge", 6 - _level(profile, "expertise"), lambda c: c["grades"]["knowledge"])
    graded("effort", 6 - _level(profile, "time"), lambda c: c["grades"]["effort"])
    graded("noncomp", 5 if comp == "limited" else 0, lambda c: c["grades"]["noncomp"])
    uncertain = bool(data & {"fuzzy", "stochastic"}) or "fuzzy_weights" in prefs
    graded("uncertainty", 4 if uncertain else 0, lambda c: c["grades"]["uncertainty"])
    graded("consistency", 2 if prefs & {"pairwise"} or "qualitative" in data else 1,
           lambda c: c["grades"]["consistency"])
    graded("reference", 3 if profile.get("reference_levels") else 0,
           lambda c: 10 if "reference" in c["caps"] else 0)

    prob = Problem.from_dict({
        "name": "Wybór metody",
        "variants": names,
        "criteria": [{"name": c["name"], "direction": "max", **({"mandatory": True} if c.get("mandatory")
                                                                   else {"weight": c["weight"]})} for c in crit],
        "values": cols})
    ideal = [1.0 if c.get("mandatory") else 10.0 for c in crit]
    res = compromise(prob, ideal=ideal)
    res["method"] = "select_method"
    res["notes"] = [n for n in res["notes"] if not n.startswith("Wyeliminowane")]   # powody w elimination_reasons
    res["profile"] = {"data": sorted(data), "preferences": sorted(prefs), "output": output, "compensation": comp,
                      **{k: profile[k] for k in ("reference_levels", "explain", "expertise", "time", "interdependence")
                         if k in profile}}
    res["titles"] = {mth: cat[mth]["title"] for mth in names}
    res["grade_sources"] = {mth: cat[mth]["source"] for mth in names}
    res["elimination_reasons"] = {m: reasons[m] for m in names if m in reasons}
    res["notes"].append("Oceny metod: SAW, SMART, TOPSIS, ELECTRE III, PROMETHEE II i EXPROM II (częściowo) na podstawie zbioru R9.2 "
                        "(D. Górecka); pozostałe — "
                        "oceny własne autora pakietu; można je nadpisać opcją scores.")
    top = res["ranking"][:2]
    if not top:
        res["notes"].append("Żadna metoda pakietu nie spełnia wymagań obowiązkowych — zob. elimination_reasons. "
                            "Rozważ złagodzenie wymagań (np. output = best).")
    if len(top) == 2:
        res["notes"].append(f"Zalecane: {cat[top[0]]['title']}; do sprawdzenia odporności wyniku — "
                            f"{cat[top[1]]['title']}.")
    return res
