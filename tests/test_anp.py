"""ANP i rozmyta ANP — zgodność z przykładami 3.12–3.14 oraz własności supermacierzy granicznej."""
import pytest

from mcdm_book import ProblemError, api, examples
from mcdm_book.anp import TFN, chang, limit_matrix, possibility

ap = pytest.approx


def flat(M):
    return [x for r in M for x in r]


def run(name, **opts):
    req = examples.get(name)
    req["options"].update(opts)
    return api.run(req)


def test_p3_12_anp():
    r = run("P3.12")
    st = r["steps"]
    assert flat(st["cluster_weights"]) == ap([0, 0.25, 0.5, 5 / 6, 0, 0.5, 1 / 6, 0.75, 0], abs=1e-4)   # tabl. 8
    W = st["weighted_supermatrix"]                                                                       # tabl. 16
    assert [row[3] for row in W] == ap([0, 0, 0, 0, 0.875, 0.125], abs=1e-4)
    assert [row[0] for row in W] == ap([0, 0, 0.6944, 0.1389, 0.125, 0.0417], abs=1e-4)
    G = st["limit_supermatrix"]                                                                          # tabl. 17
    for j in range(6):
        assert [G[i][j] for i in range(6)] == ap([0, 0.2129, 0.0389, 0.3417, 0.3285, 0.0779], abs=1e-4)
    assert st["raw"] == ap([0.3285, 0.0779], abs=1e-4)
    assert r["scores"]["values"] == ap([0.8084, 0.1916], abs=1e-4)                                      # tabl. 18
    assert r["ranking"] == ["a1", "a2"]
    assert any("f4 (0.7500)" in n for n in r["notes"])


def test_p3_12_influences_equivalent_to_dependency_matrix():
    req = examples.get("P3.12")
    pr = req["problem"]
    del pr["dependency_matrix"]
    pr["influences"] = {"f1": ["f3", "f4", "a1", "a2"], "f2": ["f4", "a1", "a2"], "f3": ["f2", "a1", "a2"],
                        "f4": ["a1", "a2"], "a1": ["f2", "f4"], "a2": ["f2", "f3"]}
    assert api.run(req)["scores"]["values"] == ap([0.8084, 0.1916], abs=1e-4)


def test_p3_12_cesaro_equals_power():
    a, b = run("P3.12"), run("P3.12", limit="cesaro")
    assert b["steps"]["limit_mode"] == "cesaro"
    assert a["scores"]["values"] == ap(b["scores"]["values"], abs=1e-9)


def test_chang_p3_14():
    F = [[TFN(1, 1, 1), TFN(1 / 5, 1 / 3, 1)], [TFN(1, 3, 5), TFN(1, 1, 1)]]      # AT: AS vs W
    res = chang(F, self_degree=True)
    assert res["S"][0] == ap([3 / 20, 1 / 4, 5 / 8])
    assert res["S"][1] == ap([1 / 4, 3 / 4, 15 / 8])
    assert res["d"] == ap([0.4286, 1, 1], abs=1e-4)
    assert res["w"] == ap([0.1765, 0.4118, 0.4118], abs=1e-4)
    assert possibility(TFN(6 / 49, 1 / 6, 7 / 27), TFN(12 / 28, 30 / 36, 56 / 36)) == 0


def test_p3_14_fuzzy_anp():
    r = run("P3.14")
    V = r["steps"]["cluster_weights"]                                                                    # tabl. 6
    assert flat(V) == ap([0.5, 0.1765, 1 / 3, 0.5, 0.4118, 1 / 3, 0, 0.4118, 1 / 3], abs=1e-4)
    # druk (tabl. 7): 0,8230; 0,1769 — z danych przykładu wynika 0,8285; 0,1715 (ranking zgodny)
    assert r["scores"]["values"] == ap([0.8285, 0.1715], abs=1e-4)
    assert r["ranking"] == ["a1", "a2"]


def test_p3_13_bocr_multiplicative():
    r = run("P3.13")                                                                                     # rys. 15
    assert r["scores"]["values"] == ap([0.655617, 0.535939, 1.539473, 1.030697], abs=2e-5)
    assert r["ranking"] == ["dostawca Y", "dostawca Z", "obecny dostawca", "dostawca X"]


def test_p3_13_bocr_additive():
    # wagi b, o, c, r nie są podane w przykładzie; odtworzone z rys. 14 (suma ≈ 1)
    req = examples.get("P3.13")
    req["options"]["formula"] = "additive"
    req["problem"]["bocr_weights"] = {"B": 0.5362, "O": 0.2668, "C": 0.1247, "R": 0.0724}
    r = api.run(req)
    assert r["scores"]["values"] == ap([0.43891, 0.311547, 0.519144, 0.52313], abs=2e-4)               # rys. 14
    assert r["ranking"] == ["dostawca Z", "dostawca Y", "obecny dostawca", "dostawca X"]


def test_hierarchy_as_anp_equals_ahp():
    """Hierarchia cel → kryteria → warianty z pętlami w ujściach (sinks = loop) daje wynik AHP (P3.4, f1, f2)."""
    ahp_req = examples.get("P3.4")
    ahp_req["options"] = {"method": "eigen"}
    pr = ahp_req["problem"]
    cc = [[1, "1/7"], [7, 1]]
    ahp_req["problem"] = {"variants": pr["variants"], "criteria": ["f1", "f2"], "criteria_comparisons": cc,
                          "comparisons": {k: pr["comparisons"][k] for k in ("f1", "f2")}}
    ahp_res = api.run(ahp_req)
    net = {"variants": pr["variants"], "criteria": ["cel", "f1", "f2"],
           "clusters": {"Cel": ["cel"], "Kryteria": ["f1", "f2"]},
           "influences": {"cel": ["f1", "f2"], "f1": pr["variants"], "f2": pr["variants"]},
           "comparisons": {"cel": {"Kryteria": cc}, "f1": {"Warianty": pr["comparisons"]["f1"]},
                           "f2": {"Warianty": pr["comparisons"]["f2"]}}}
    r = api.run({"method": "anp", "problem": net, "options": {"sinks": "loop"}})
    assert r["scores"]["values"] == ap(ahp_res["scores"]["values"], abs=1e-9)
    assert "cel" in r["steps"]["read"]


def test_cyclic_network_uses_cesaro():
    # dwa elementy wpływające na siebie nawzajem: Ω̄ = [[0, 1], [1, 0]] — potęgi oscylują
    L = limit_matrix([[0.0, 1.0], [1.0, 0.0]])
    assert L["mode"] == "cesaro"
    assert flat(L["G"]) == ap([0.5] * 4)
    with pytest.raises(ProblemError):
        limit_matrix([[0.0, 1.0], [1.0, 0.0]], "power")


def test_errors():
    req = examples.get("P3.12")
    req["problem"]["comparisons"]["f4"]["AS"] = [[1, 2], [None, 1]]       # f4 wpływa tylko na warianty
    with pytest.raises(ProblemError, match="nie wpływa"):
        api.run(req)
    req = examples.get("P3.14")
    req["method"] = "anp"
    with pytest.raises(ProblemError, match="fuzzy_anp"):
        api.run(req)
    req = examples.get("P3.12")
    req["problem"]["clusters"] = {"AS": ["f1", "f2"], "AT": ["f3"]}
    with pytest.raises(ProblemError, match="komponentu"):
        api.run(req)
