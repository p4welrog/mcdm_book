import pytest

from mcdm_book import api, examples
from mcdm_book.bipolar import deciles, fraction, percentile
from mcdm_book.problem import ProblemError


def run(name, **opts):
    e = examples.get(name)
    return api.run({"method": e["method"], "problem": e["problem"], "options": {**e["options"], **opts}})


def r3(xs):
    return [round(x, 3) for x in xs]


def test_p7_5_dematel():
    st = run("P7.5")["steps"]
    assert r3(st["r"]) == [11.879, 10.7, 10.747, 10.421]
    assert r3(st["c"]) == [10.747, 10.266, 12.143, 10.591]


def test_p7_6_hybrid():
    r = run("P7.6")
    assert r["ranking"] == ["a8", "a10", "a6", "a9", "a7", "a11", "a12", "a5", "a4", "a3", "a2", "a1"]
    assert round(r["steps"]["weights"][0], 4) == 0.0743
    assert abs(sum(r["steps"]["weights"]) - 1) < 1e-9


def test_hybrid_requires_clusters():
    e = examples.get("P7.6")
    prob = {**e["problem"], "criteria": [{"name": c["name"]} for c in e["problem"]["criteria"]]}
    with pytest.raises(ProblemError):
        api.run({"method": "hybrid", "problem": prob, "options": {}})


def test_p7_7_and_p7_12_bipolar():
    st = run("P7.7")["steps"]
    assert st["S_category"] == ["S1"] * 4 and st["N_category"] == ["N2", "N1", "N1", "N1"]
    assert st["B_category"] == [None, "B1", "B1", "B1"]
    assert run("P7.7")["ranking"] == ["a4", "a2", "a3"]
    r = run("P7.12")
    assert r["steps"]["B_category"][0] == "B2′" and r["ranking"] == ["a4", "a2", "a3", "a1"]


def test_veto_test_formula_differs():
    st = run("P7.7", veto_test="formula")["steps"]
    assert st["B_category"] == ["B1"] * 4


def test_p7_8_bipolar():
    r = run("P7.8")
    st = r["steps"]
    assert st["S_category"] == ["S1", "S1", "S1", "S2", "S2", "S2", "S2"]
    assert st["N_category"] == ["N1", "N1", "N1", "N1", "N1", "N2", "N2"]
    assert st["B_category"] == ["B1", "B1", "B1", "B2", "B2", "B3", "B3"]


def test_p7_13_large_reference_system():
    r = run("P7.13")
    st = r["steps"]
    assert r3(st["weights"]) == [0.378, 0.27, 0.351]
    assert [round(x, 2) for x in st["d_N"]] == [1.0, 1.0, 1.0, 0.7, 0.1, 0.2, 0.1, 0.95, -0.05, -0.15]  # tabl. 11
    # d_S z relacji tablicy 9 (tablica 11 w druku jest z nimi niespójna)
    assert [round(x, 2) for x in st["d_S"]] == [0.9, 0.7, 0.7, -0.65, -0.45, -0.2, -0.05, 0.05, -0.9, -1.0]


def test_p7_14_decile_weights():
    st = run("P7.15")["steps"]
    assert r3(st["weights"]) == [0.374, 0.279, 0.347]
    assert st["S_category"] == ["S1"] * 8 + ["S2"] * 2                       # tabl. 2 przykładu 7.15


def test_p7_16_bipolar_sd():
    r = run("P7.16")
    st = r["steps"]
    assert st["d_S"] == pytest.approx([-0.498, -0.208, -0.408, -0.365, -0.405, -0.640, -0.688, 0.022], abs=0.0015)
    assert st["d_N"] == pytest.approx([0.132, 0.671, 0.233, 0.389, 0.315, 0.113, -0.033, 0.660], abs=0.0015)
    assert r["ranking"] == ["a8", "a2", "a4", "a5", "a3", "a1", "a6", "a7"]


def test_deciles_and_fraction():
    xs = [15, 14, 18, 19, 15, 11, 12, 13, 20, 13, 19, 9, 23, 15, 12, 12, 20, 13, 15, 11]
    assert deciles(xs)[1] == pytest.approx(11) and percentile(xs, 0.5) == pytest.approx(14.5)
    assert fraction(30, deciles(xs)) == 10


def test_selection_bipolar_profile():
    r = api.run({"method": "select_method", "profile": {"data": "numeric", "reference_levels": True}})
    assert {"bipolar", "hybrid"} <= set(r["ranking"])
    r = api.run({"method": "select_method", "profile": {"data": "numeric", "interdependence": True}})
    assert "hybrid" in r["ranking"] and "bipolar" not in r["ranking"]
