"""UniComBOS (rozdz. 4.2, przykład 4.9; rozdz. 13): R13.1, R13.2, rys. 13.4–13.7."""
import pytest

from mcdm_book import api
from mcdm_book import data_r13 as D
from mcdm_book.examples import EXAMPLES
from mcdm_book.problem import ProblemError


def run(problem, **opt):
    return api.run({"method": "unicombos", "problem": problem, "options": {"auto_single": False, **opt}})


def test_r13_final_ranking():
    """S. 253: Sarni Stok, Ogrody, Piast, King Cross Praga (graf liniowy jak rys. 17 przykładu 4.9)."""
    e = EXAMPLES["R13"]
    r = api.run({"method": e["method"], "problem": e["problem"], "options": e["options"]})
    assert r["ranking"] == ["Sarni Stok", "Ogrody", "Piast", "King Cross Praga"]
    assert r["steps"]["edges"] == [["Sarni Stok", "Ogrody"], ["Ogrody", "Piast"], ["Piast", "King Cross Praga"]]
    # Piast ≻ KCP dopiero z dwóch pytań trzykryterialnych (rys. 13.7)
    assert "(f3, f4, f12)" in r["steps"]["explanation"]["Piast ≻ King Cross Praga"]


def test_r13_1_single_criterion_only():
    """Same porównania jednokryterialne (R13.1, rys. 13.4) nie wskazują najlepszego wariantu."""
    r = run(D.problem(1))
    assert r["best"] == D.R13_VARIANTS and r["steps"]["edges"] == []


def test_fig_13_4_f1():
    """Rys. 13.4: f1 — 4,07 mln preferowane nad pozostałe, 2,50 ~ 2,60 (różnica zbyt mała)."""
    f1 = [c for c in D.R13_1 if c["criteria"] == ["f1"]]
    assert [c["answer"] for c in f1] == [">", ">", ">", "=", ">", ">"]
    assert f1[3]["first"] == [2501592.72] and f1[3]["second"] == [2596405.10]


def test_fig_13_6_best_found_during_r13_2():
    """S. 251, rys. 13.6: w trakcie porównań dwukryterialnych wyłania się Sarni Stok (po 8 porównaniach R13.2:
    Sarni Stok → Ogrody, King Cross Praga, Piast); do końca R13.2 uporządkowania pełnego brak (KCP–Piast)."""
    p = D.problem(1)
    p["comparisons"] = D.R13_1 + D.R13_2[:7]
    assert run(p)["best"] != ["Sarni Stok"]
    p["comparisons"] = D.R13_1 + D.R13_2[:8]
    r = run(p)
    assert r["best"] == ["Sarni Stok"]
    assert r["steps"]["edges"] == [["Sarni Stok", "Ogrody"], ["Sarni Stok", "King Cross Praga"],
                                   ["Sarni Stok", "Piast"]]
    r2 = run(D.problem(2))
    assert r2["best"] == ["Sarni Stok"] and r2["steps"]["relations"][2][3] == "R"
    assert any(q["variants"] == ["King Cross Praga", "Piast"] for q in r2["steps"]["suggested_questions"])


def test_fig_13_5_is_first_panel_of_r13_2():
    """Rys. 13.5 = rys. 1 zbioru R13.2 (6 porównań, wszystkie: górny wariant preferowany)."""
    first = D.R13_2[:6]
    assert [c["criteria"] for c in first] == [["f2", "f5"], ["f3", "f7"], ["f4", "f10"], ["f6", "f11"],
                                               ["f8", "f12"], ["f9", "f14"]]
    assert all(c["answer"] == ">" for c in first)


def test_fig_13_7_repeated_questions():
    """Rys. 13.7: każde z dwóch pytań trzykryterialnych zadane trzy razy (permutacje kryteriów) — spójnie."""
    r = run(D.problem(3))
    assert any("100, 101, 102; 103, 104, 105" in n for n in r["notes"])
    p = D.problem(3)
    p["comparisons"][-1] = dict(p["comparisons"][-1], answer="<")
    with pytest.raises(ProblemError, match="niespójne"):
        run(p)


def test_contradiction_detected():
    """Sprzeczna odpowiedź (cykl preferencji jednostek) jest zgłaszana."""
    p = D.problem(1)
    p["comparisons"] = D.R13_1 + [{"criteria": ["f2"], "first": [23.23], "second": [33.32], "answer": ">"}]
    with pytest.raises(ProblemError):
        run(p)


def test_auto_single_and_order():
    """Bez porównań jednokryterialnych: z kierunku (liczby) i z pola "order" (oceny słowne)."""
    p = {"variants": ["x", "y"], "criteria": [{"name": "cena", "direction": "min"},
                                             {"name": "kolor", "order": ["biały", "czarny"]}],
         "values": [[10, "biały"], [12, "czarny"]]}
    r = api.run({"method": "unicombos", "problem": p, "options": {}})
    assert r["ranking"] == ["x", "y"] and r["best"] == ["x"]
    p["values"][0][1] = "czarny"; p["values"][1][1] = "biały"
    r = api.run({"method": "unicombos", "problem": p, "options": {}})
    assert r["steps"]["relations"][0][1] == "R"
    p["comparisons"] = [{"criteria": ["cena", "kolor"], "first": [10, "czarny"], "second": [12, "biały"], "answer": "<"}]
    r = api.run({"method": "unicombos", "problem": p, "options": {}})
    assert r["ranking"] == ["y", "x"]
