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

from . import additive, ahp, anp, bipolar, electre, hybrid, macbeth, promethee, reference, selection, zapros
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
    "macbeth": {"fn": macbeth.macbeth, "chapter": "4.1", "title": "MACBETH",
                "needs": "kryteria z polem \"macbeth\": {levels (poziomy jakościowe lub liczbowe; brak = porównanie "
                         "wariantów), judgements (oceny różnic: 0 = równie atrakcyjne, 1–6 = bardzo mała … ekstremalna, "
                         "[s, t], \"positive\"; wiersz lepszy od kolumny), upper, lower} albo gotowe oceny 0–100 w values; "
                         "\"criteria_judgements\" (kryteria + opcjonalnie element odniesienia [ all lower ]) albo wagi",
                "options": {}},
    "macbeth_scale": {"fn": macbeth.macbeth_scale, "chapter": "4.1", "title": "Skala MACBETH (jedna macierz ocen)",
                      "needs": "elementy jako warianty, \"judgements\" — macierz ocen różnic atrakcyjności",
                      "options": {"upper": "element = 100 (domyślnie najlepszy)", "lower": "element = 0 (najgorszy)"}},
    "zapros": {"fn": zapros.zapros, "chapter": "4.2.2", "title": "ZAPROS",
               "needs": "kryteria z polem \"scale\" (oceny od najlepszej), values = oceny; \"jos\" (grupy ocen wg rang "
                        "wspólnej skali porządkowej) albo \"y_comparisons\" (porównania wektorów ze zbioru Y)",
               "options": {}},
    "zapros_iii": {"fn": zapros.zapros_iii, "chapter": "4.2.3", "title": "ZAPROS III",
                   "needs": "kryteria z polem \"scale\"; \"jscv\" (wariacje od najmniej dotkliwej, np. \"C1>C2\") albo "
                            "\"jsqv\" (skale dla par kryteriów) albo \"qv_comparisons\" (tablice porównań wariacji)",
                   "options": {}},
    "electre_i": {"fn": electre.electre_i, "chapter": "5.2", "title": "ELECTRE I",
                  "needs": "oceny liczbowe na wspólnej skali, wagi; próg zgodności s i wspólny próg weta v",
                  "options": {"s": "próg zgodności (0,5–1)", "v": "wspólny próg weta"}},
    "electre_iv": {"fn": electre.electre_iv, "chapter": "5.2", "title": "ELECTRE Iv",
                   "needs": "oceny liczbowe, wagi; progi weta v kryteriów (liczba albo [α, β] = α·f + β)",
                   "options": {"s": "próg zgodności (0,5–1)"}},
    "electre_is": {"fn": electre.electre_is, "chapter": "5.2", "title": "ELECTRE Is",
                   "needs": "oceny liczbowe, wagi; progi q, p, v kryteriów (pseudokryteria)",
                   "options": {"s": "próg zgodności (0,5–1)"}},
    "electre_iii": {"fn": electre.electre_iii, "chapter": "5.3", "title": "ELECTRE III",
                    "needs": "oceny liczbowe, wagi; progi q, p (wymagane), v kryteriów — liczby albo [α, β] = α·f + β",
                    "options": {"alpha": "s(λ) = α·λ + β, domyślnie α = −0,15", "beta": "domyślnie β = 0,30"}},
    "electre_tri": {"fn": electre.electre_tri, "chapter": "5.4", "title": "ELECTRE TRI (sortowanie)",
                    "needs": "oceny liczbowe, wagi; progi q, p, v; \"profiles\" — profile graniczne od najniższego; "
                             "opcjonalnie \"categories\" — nazwy kategorii od najgorszej",
                    "options": {"cut": "poziom cięcia λ (0,5–1, domyślnie 0,75)",
                                "procedure": "pessimistic | optimistic | both (domyślnie both: wynik pesymistyczny)"}},
    "electre_i_sd": {"fn": electre.electre_i_sd, "chapter": "5.5",
                     "title": "ELECTRE I z dominacjami stochastycznymi",
                     "needs": "oceny jako rozkłady {values, probs} lub {obs}; wagi",
                     "options": {"s": "próg zgodności (domyślnie 1; obniżać, dopóki s > 0,5)", "risk": promethee.RISKS,
                                 "dominances": "jak w promethee_ii_sd",
                                 "include_unclear": "włącz pary niejasne (c_E < s ≤ c_E + c_N) do relacji"}},
    "electre_iii_sd": {"fn": electre.electre_iii_sd, "chapter": "5.6",
                       "title": "ELECTRE III z dominacjami stochastycznymi",
                       "needs": "oceny jako rozkłady; wagi; progi p, v (opcjonalnie q) — liczby albo [α, β] = α·μ + β (5.39)",
                       "options": {"risk": promethee.RISKS, "dominances": "jak w promethee_ii_sd",
                                   "alpha": "s(λ) = α·λ + β, domyślnie α = −0,15", "beta": "domyślnie β = 0,30"}},
    "promethee_i": {"fn": promethee.promethee_i, "chapter": "6.2", "title": "PROMETHEE I (ranking częściowy)",
                    "needs": "oceny liczbowe, kierunki, wagi; w kryteriach type (1–6) i progi q, p, s (tabl. 6.1)",
                    "options": {"divide": "dzielenie przepływów przez m − 1 (domyślnie true)"},
                    "criterion_types": promethee.TYPES},
    "promethee_ii": {"fn": promethee.promethee_ii, "chapter": "6.2", "title": "PROMETHEE II",
                     "needs": "jak PROMETHEE I", "options": {"divide": "dzielenie przepływów przez m − 1 (domyślnie true)"},
                     "criterion_types": promethee.TYPES},
    "promethee_ii_veto": {"fn": promethee.promethee_ii_veto, "chapter": "6.3", "title": "PROMETHEE II z progami weta",
                          "needs": "oceny liczbowe, kierunki, wagi; w kryteriach progi q, p, v",
                          "options": {"veto_direction": promethee.VETO_DIRECTIONS,
                                      "divide": "dzielenie przepływów przez m − 1 (domyślnie false, jak 6.23)"}},
    "exprom": {"fn": promethee.exprom, "chapter": "6.4", "title": "EXPROM (I i II)",
               "needs": "jak PROMETHEE; opcjonalnie L (granica silnej preferencji) w kryteriach",
               "options": {"ranking": "complete (EXPROM II, domyślnie) | partial (EXPROM I)",
                           "divide": "dzielenie przepływów przez m − 1 (domyślnie true)"},
               "criterion_types": promethee.TYPES},
    "exprom_veto": {"fn": promethee.exprom_veto, "chapter": "6.5", "title": "EXPROM II z progami weta",
                    "needs": "oceny liczbowe, kierunki, wagi; w kryteriach progi q, p, v",
                    "options": {"veto_direction": promethee.VETO_DIRECTIONS,
                                "divide": "dzielenie przepływów przez m − 1 (domyślnie false, jak 6.38)"}},
    "promethee_ii_sd": {"fn": promethee.promethee_ii_sd, "chapter": "6.6",
                        "title": "PROMETHEE II z progami weta i dominacjami stochastycznymi",
                        "needs": "oceny jako rozkłady {values, probs} lub {obs}; wagi; progi p, v (opcjonalnie q) — "
                                 "liczby albo [α, β] (α + β·μ)",
                        "options": {"risk": promethee.RISKS,
                                    "dominances": "lista uznawanych dominacji, np. [\"FSD\", \"SSD\", \"AFSD:0.333\", "
                                                  "\"ASSD:0.2\"] (prawie dominacje ze stopniem ε)",
                                    "divide": "dzielenie przepływów przez m − 1 (domyślnie false)"}},
    "exprom_ii_sd": {"fn": promethee.exprom_ii_sd, "chapter": "6.7",
                     "title": "EXPROM II z progami weta i dominacjami stochastycznymi",
                     "needs": "jak PROMETHEE II z dominacjami stochastycznymi",
                     "options": {"risk": promethee.RISKS, "dominances": "jak w promethee_ii_sd",
                                 "divide": "dzielenie przepływów przez m − 1 (domyślnie false)"}},
    "dematel": {"fn": hybrid.dematel, "chapter": "7.4", "title": "DEMATEL (zależności między elementami)",
                "needs": "elementy systemu jako warianty, \"influence\" — macierz ocen wpływu 0–4 (wiersz → kolumna) "
                         "albo lista macierzy ekspertów; criteria może być puste",
                "options": {}},
    "hybrid": {"fn": hybrid.hybrid, "chapter": "7.4", "title": "Metoda hybrydowa DEMATEL–ANP–VIKOR",
               "needs": "oceny liczbowe; kryteria z polem \"cluster\"; \"cluster_influence\" i \"criteria_influence\" — "
                        "macierze ocen wpływu 0–4 (grupy, kryteria); wagi wyznacza metoda",
               "options": {"alpha": "próg α-cięcia macierzy T grup (7.30)", "alpha_criteria": "próg α dla T kryteriów",
                           "q": "VIKOR: waga strategii większości (0,5)", "ideal": "VIKOR: f* (lista)",
                           "anti_ideal": "VIKOR: f_* (lista)", "w2": "both | either",
                           "limit": "auto | power | cesaro"}},
    "bipolar": {"fn": bipolar.bipolar, "chapter": "7.5", "title": "BIPOLAR",
                "needs": "oceny liczbowe, wagi, progi q i weta v (najmniejsza dopuszczalna ocena); \"good\", \"bad\" — "
                         "obiekty referencyjne „dobre” i „złe” (wiersze ocen)",
                "options": {"s": "próg zgodności (0–1)", "weights": "given | deciles (7.83) | objects (przykład 7.13)",
                            "veto_decile": "progi weta = q-ty decyl obiektów „dobrych” (7.87)",
                            "local_preference": "funkcje lokalnej preferencji (7.76)–(7.80)",
                            "position": "classic (7.52)–(7.53) | counts (7.81)–(7.82) — pełny ranking",
                            "modify": "good | bad — modyfikacja zbioru referencyjnego (7.67), (7.69)",
                            "b2_prime": "kategoria B2′ (7.70)", "veto_test": "formula | example (jak przykłady 7.7–7.12)"}},
    "bipolar_sd": {"fn": bipolar.bipolar_sd, "chapter": "7.6", "title": "BIPOLAR z dominacjami stochastycznymi",
                   "needs": "oceny i obiekty referencyjne jako rozkłady {values, probs} lub {obs}; wagi; progi q, p, "
                            "v (najmniejsza dopuszczalna wartość oczekiwana)",
                   "options": {"risk": promethee.RISKS, "dominances": "jak w promethee_ii_sd"}},
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
