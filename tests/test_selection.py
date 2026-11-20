"""Wybór metody (rozdz. 9.3): programowanie kompromisowe (9.1) na zbiorach R9.2 i R9.3 oraz dobór metody pakietu."""
import pytest

from mcdm_book import ProblemError, api, examples

ap = pytest.approx


def run(name):
    return api.run(examples.get(name))


def test_r9_2_gershon():
    r = run("R9.2")
    assert r["scores"]["values"] == ap([11.6, 29.2, 15.8, 9.8, 16.0, 13.625, 14.125])
    assert r["ranking"][0] == "EXPROM II" and r["ranking"][-1] == "ELECTRE III"


def test_r9_3_tecle():
    r = run("R9.3")
    assert r["scores"]["values"] == ap([95.33, 197.94, 119.01, 92.85, 123.83, 110.90, 112.45], abs=0.005)
    assert r["ranking"][0] == "EXPROM II" and r["ranking"][-1] == "ELECTRE III"


def test_compromise_mandatory_elimination():
    p = {"variants": ["x", "y", "z"],
         "criteria": [{"name": "warunek", "mandatory": True}, {"name": "a", "weight": 1}, {"name": "b", "weight": 2}],
         "values": [[1, 10, 0], [0, 10, 10], [1, 0, 10]]}
    r = api.run({"method": "compromise", "problem": p, "options": {"ideal": [1, 10, 10]}})
    assert r["steps"]["eliminated"] == {"y": ["warunek"]}
    assert r["scores"]["values"][1] is None and r["ranks"][1] is None
    assert r["scores"]["values"][0] == ap(2) and r["scores"]["values"][2] == ap(1)
    assert r["ranking"] == ["z", "x"]


def sel(**profile):
    return api.run({"method": "select_method", "profile": profile})


def test_select_basic_profiles():
    assert sel(data=["numeric"])["ranking"][:2] == ["saw", "topsis"]
    assert sel(data=["numeric", "qualitative"], preferences=["pairwise"])["best"] == ["ahp"]
    assert sel(data=["fuzzy"])["best"] == ["fuzzy_topsis"]
    assert sel(data=["numeric"], compensation="limited", reference_levels=True)["best"] == ["vikor"]
    assert sel(data=["numeric"], preferences=["ranks"], expertise="low", time="low")["best"] == ["smarter"]
    assert "smart" in sel(data=["numeric"], preferences=["swing"])["ranking"][:2]   # SAW z wagami rozpiętości to SMART liniowy
    assert sel(data=["stochastic"], output="best", preferences=["dialog"])["best"] == ["stem_dpr"]


def test_select_eliminations_and_reasons():
    r = sel(data=["qualitative"])
    assert "saw" not in r["ranking"] and "nie obsługuje ocen jakościowych" in r["elimination_reasons"]["saw"]
    r = sel(data=["stochastic"])
    assert r["ranking"] == [] and any("Żadna metoda" in n for n in r["notes"])


def test_select_override_scores_and_errors():
    r = api.run({"method": "select_method", "profile": {"data": ["numeric"]},
                 "options": {"scores": {"vikor": {"transparency": 10, "knowledge": 10, "effort": 10}}}})
    assert r["grade_sources"]["vikor"] == "podane przez użytkownika"
    with pytest.raises(ProblemError):
        sel(data=["xyz"])
    with pytest.raises(ProblemError):
        sel(data=["numeric"], output="all")
    assert "select_method" in api.methods()
