"""PROMETHEE i EXPROM (rozdz. 6) — zgodność z przykładami 6.1–6.16."""
import pytest

from mcdm_book import ProblemError, api, examples
from mcdm_book.problem import Problem
from mcdm_book.promethee import credibility, partial_order, preference_function

ap = pytest.approx


def run(name, **opts):
    req = examples.get(name)
    req["options"].update(opts)
    return api.run(req)


def flat(M):
    return [x for r in M for x in r]


def test_p6_1_generalized_criteria():
    """Tabl. 3 przykładu 6.1 (G1–G6 dla par wariantów), dane P6.5 bez wag."""
    from mcdm_book.examples import _C_65, _X_65
    p = Problem.from_dict({"variants": ["a1", "a2", "a3", "a4"], "criteria": _C_65, "values": _X_65})
    G = [[[preference_function(c)["G"](_X_65[i][k] - _X_65[j][k]) for j in range(4)] for i in range(4)]
         for k, c in enumerate(p.criteria)]
    assert flat(G[1]) == ap([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])
    assert flat(G[2]) == ap([0, .25, 0, .75, 0, 0, 0, .5, .5, .75, 0, 1, 0, 0, 0, 0])
    assert flat(G[3]) == ap([0, 0, 0, 1, .5, 0, .5, 1, 0, 0, 0, 1, 0, 0, 0, 0])
    assert flat(G[4]) == ap([0, 0, 0, 0, 1, 0, 0, .75, .25, 0, 0, 0, 0, 0, 0, 0])
    assert flat(G[5]) == ap([0, .865, .393, 0, 0, 0, 0, 0, 0, .393, 0, 0, .865, .999, .989, 0], abs=1e-3)
    # G1 (a4, a1): druk 1, z danych 0 (f1(a4) = 5 < 6 = f1(a1))
    assert G[0][3][0] == 0


def test_p6_2_promethee_i():
    r = run("P6.2")
    st = r["steps"]
    assert flat(st["pi"]) == ap(flat([[0, .35, .15, 0, .2, .35, .3], [.6, 0, .4, .6, 0, .2, .4],
                                      [.7, .25, 0, .7, .1, .45, .25], [0, .3, .15, 0, .15, .3, .3],
                                      [.6, .55, .4, .6, 0, .75, .55], [.4, .32, .4, .4, 0, 0, .4],
                                      [.6, 0, .4, .6, 0, .2, 0]]))                                   # tabl. 10
    assert st["phi_plus"] == ap([.225, .3667, .4083, .2, .575, .32, .3], abs=1e-4)
    assert st["phi_minus"] == ap([.4833, .295, .3167, .4833, .075, .375, .3667], abs=1e-4)
    rel = st["relations"]
    assert rel[0][3] == "P" and rel[1][2] == "R" and rel[5][6] == "R" and rel[4][0] == "P"        # tabl. 14
    assert r["ranks"] == [4, 2, 2, 5, 1, 3, 3] and r["best"] == ["a5"]                           # rys. 1
    assert sorted(map(tuple, st["hasse"])) == sorted([("a5", "a2"), ("a5", "a3"), ("a2", "a6"), ("a2", "a7"),
                                                     ("a3", "a6"), ("a3", "a7"), ("a6", "a1"), ("a7", "a1"),
                                                     ("a1", "a4")])


def test_p6_4_and_p6_5_promethee_ii():
    r = run("P6.4")
    assert r["scores"]["values"] == ap([-.25, .2, -.1, .25, -.1])
    assert r["ranks"] == [5, 2, 3, 1, 3]
    r = run("P6.5")                                                                                   # Decision Lab
    st = r["steps"]
    assert st["phi_plus"] == ap([.4172, .1750, .3262, .3235], abs=1e-4)
    assert st["phi_minus"] == ap([.1993, .3839, .2422, .4167], abs=1e-4)
    assert r["ranking"] == ["a1", "a3", "a4", "a2"]
    assert run("P6.4", divide=False)["scores"]["values"] == ap([-1, .8, -.4, 1, -.4])


def test_p6_7_veto():
    r = run("P6.7")
    st = r["steps"]
    assert flat(st["concordance"]) == ap(flat([[0, .5, .5, 0, .5], [.5, 0, .6333, .5, .6], [.5, .3, 0, .5, .15],
                                               [.2, .5, .5, 0, .5], [.5, .3, .5, .5, 0]]), abs=1e-4)  # tabl. 6
    # wg wzoru (6.20): przewaga aʲ nad aⁱ wetuje „aⁱ przewyższa aʲ”
    assert r["scores"]["values"] == ap([-.2, -.3, -.5, .2, .8])
    assert r["ranking"] == ["a5", "a4", "a1", "a2", "a3"]
    # druk (tabl. 7–9 liczą d z f(aⁱ) − f(aʲ)): σ(a2, a5) = 0,6; σ(a3, a5) = 0,15
    r = run("P6.7", veto_direction="example")
    assert r["scores"]["values"] == ap([0, .6, .15, 0, -.75])
    assert r["ranks"] == [3, 1, 2, 3, 5]


def test_p6_8_exprom():
    r = run("P6.8")
    st = r["steps"]
    assert flat(st["TP"]) == ap(flat([[0, 1, .16, .46], [.59, 0, .35, .6], [1, 1, 0, .55], [.81, 1, .77, 0]]),
                                abs=6e-3)                                                             # tabl. 13
    assert r["scores"]["values"] == ap([-.26, -.49, .43, .32], abs=6e-3)                             # tabl. 14
    assert r["ranking"] == ["a3", "a4", "a1", "a2"]
    r = run("P6.8", ranking="partial")
    assert r["best"] == ["a3", "a4"] and r["steps"]["relations"][2][3] == "R"


def test_p6_10_exprom_veto():
    r = run("P6.10", veto_direction="example")                                                       # druk: tabl. 16
    assert flat(r["steps"]["pi"]) == ap([0] * 25)
    assert r["scores"]["values"] == ap([0, .6, .15, 0, -.75])
    r = run("P6.10")
    assert r["scores"]["values"] == ap([-.2815, -.3237, -.5938, .2815, .9174], abs=1e-4)
    assert r["ranking"] == ["a5", "a4", "a1", "a2", "a3"]


def test_p6_11_promethee_sd():
    r = run("P6.11")
    st = r["steps"]
    assert flat(st["concordance"]) == ap(flat([[0, 0, .157, .091, .25], [.242, 0, .12, .245, 0],
                                               [.224, .07, 0, .315, .25], [.4625, .4, .5875, 0, .53],
                                               [.554, .32, .4, .245, 0]]), abs=1e-3)                  # tabl. 12
    assert st["credibility"][1][3] == ap(.0541, abs=1e-4) and st["credibility"][4][0] == ap(.1242, abs=1e-4)
    assert r["scores"]["values"] == ap([-.6457, -.3739, -.5205, 1.9259, -.3858], abs=1e-4)
    assert r["ranking"] == ["a4", "a2", "a5", "a3", "a1"]
    assert st["dominance"][2][0][3] is None                    # TISD2 niezgodna z DARA (tabl. 7) — pominięta


def test_p6_12_ordinal_almost_dominance():
    r = run("P6.12")
    assert r["scores"]["values"] == ap([-1.003, 1.343, -.092, .034, .137, -1.450, -2.635, 3.666], abs=1e-3)
    assert r["steps"]["dominance"][0][5][2].startswith("AFSD")                                        # tabl. 3
    assert r["steps"]["dominance"][1][7][3].startswith("AFSD")                                        # tabl. 4
    # bez prawie dominacji wynik jest inny
    assert run("P6.12", dominances=None)["scores"]["values"][7] == ap(3.471, abs=1e-3)


def test_p6_14_and_p6_16_exprom_sd():
    r = run("P6.14")
    st = r["steps"]
    assert flat(st["pi"]) == ap(flat([[0, 0, 0, 0, .2045], [0] * 5, [0, 0, 0, 0, .1591],
                                      [.36, .25, .4, 0, .2273], [0] * 5]), abs=1e-4)                  # tabl. 23
    assert r["scores"]["values"] == ap([-.8012, -.6239, -.7614, 3.1632, -.9767], abs=1e-4)
    r = run("P6.16")                                                                                  # tabl. 21 (±0,002)
    assert r["scores"]["values"] == ap([-1.232, 4.661, -6.005, -3.251, 2.134, 2.728, 1.490, -.525], abs=2.5e-3)
    assert r["ranking"] == ["a2", "a6", "a5", "a7", "a8", "a1", "a4", "a3"]


def test_helpers_and_errors():
    assert credibility(0.5, [0.2, 0.4]) == 0.5
    assert credibility(0.5, [1.0]) == 0
    po = partial_order([.5, .5, .1], [.1, .1, .5])
    assert po["relations"][0][1] == "I" and po["levels"] == [1, 1, 2]
    req = examples.get("P6.2")
    req["problem"]["criteria"][0].pop("p")
    with pytest.raises(ProblemError, match="'p'"):
        api.run(req)
    req = examples.get("P6.7")
    req["problem"]["criteria"][0]["v"] = 8                              # v < p
    with pytest.raises(ProblemError, match="v > p"):
        api.run(req)
    req = examples.get("P6.11")
    req["options"]["dominances"] = ["XSD"]
    with pytest.raises(ProblemError, match="nieznana dominacja"):
        api.run(req)
    # kryterium minimalizowane = odwrócenie znaku
    req = examples.get("P6.4")
    for c in req["problem"]["criteria"]:
        c["direction"] = "min"
    req["problem"]["values"] = [[-x for x in row] for row in req["problem"]["values"]]
    assert api.run(req)["scores"]["values"] == ap([-.25, .2, -.1, .25, -.1])
