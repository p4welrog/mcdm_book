import pytest

from mcdm_book import api, examples
from mcdm_book.electre import distillation, final_ranking
from mcdm_book.problem import ProblemError


def run(name, **opts):
    e = examples.get(name)
    return api.run({"method": e["method"], "problem": e["problem"], "options": {**e["options"], **opts}})


def edges(r):
    return {tuple(e) for e in r["steps"]["edges"]}


def r2(M):
    return [[round(x, 2) for x in row] for row in M]


def test_p5_10_electre_i():
    r = run("P5.10")
    assert edges(r) == {("a1", "a5"), ("a1", "a6"), ("a1", "a9"), ("a2", "a3"), ("a2", "a9"), ("a4", "a5"),
                        ("a6", "a9"), ("a7", "a3"), ("a7", "a4"), ("a7", "a5"), ("a7", "a6"), ("a7", "a9"),
                        ("a8", "a1"), ("a8", "a2"), ("a8", "a9"), ("a9", "a3")}
    assert r["steps"]["levels_top_down"] == [2, 2, 5, 2, 3, 3, 1, 1, 4]      # rys. 1
    assert r["steps"]["levels_bottom_up"] == [2, 3, 5, 4, 5, 3, 2, 1, 4]     # rys. 2: książka stawia a7 razem z a8 na szczycie
    assert r["best"] == ["a7", "a8"]
    C = r2(r["steps"]["concordance"])
    assert C[0] == [1.0, 0.5, 0.92, 0.59, 0.83, 0.92, 0.59, 0.08, 0.92]
    assert C[8][6] == 0.08                                                    # druk 0,50 (errata)


def test_p5_11_p5_12_veto_per_criterion():
    expected = {("a1", "a5"), ("a1", "a9"), ("a2", "a3"), ("a2", "a9"), ("a4", "a5"), ("a6", "a9"), ("a7", "a4"),
                ("a7", "a5"), ("a7", "a6"), ("a7", "a9"), ("a8", "a1"), ("a8", "a2"), ("a8", "a9"), ("a9", "a3")}
    for name in ("P5.11", "P5.12"):
        r = run(name)
        assert edges(r) == expected
        assert r["steps"]["levels_top_down"] == [2, 2, 4, 2, 3, 2, 1, 1, 3]


def test_p5_13_electre_iii():
    r = run("P5.13")
    S = r2(r["steps"]["credibility"])
    assert S == [[1.0, 0.0, 0.83, 0.0, 0.83, 0.73], [0.12, 1.0, 0.0, 0.46, 0.0, 0.0], [0.0] * 2 + [1.0] + [0.0] * 3,
                 [0.62, 0.94, 0.0, 1.0, 0.67, 0.0], [0.79, 0.0, 0.83, 0.0, 1.0, 0.52], [0.96, 0.0, 0.94, 0.0, 0.92, 1.0]]
    st = r["steps"]
    assert st["descending_classes"] == [["a6"], ["a4"], ["a1", "a5"], ["a2", "a3"]]
    assert st["ascending_classes"] == [["a4", "a6"], ["a1", "a2", "a5"], ["a3"]]
    assert r["scores"]["values"] == [3, 4, 5, 2, 3, 1]                       # tabl. 26
    rel = st["final_relations"]
    assert rel[0][4] == "I" and rel[3][5] == "P-" and rel[5][3] == "P"


def test_p5_14_program():
    r = run("P5.14")
    assert r["steps"]["descending_classes"] == [["a6"], ["a4"], ["a1", "a5"], ["a3"], ["a2"]]
    assert r["steps"]["ascending_classes"] == [["a4", "a6"], ["a1", "a5"], ["a3"], ["a2"]]
    assert r["ranking"] == ["a6", "a4", "a1", "a5", "a3", "a2"]


def test_p5_15_p5_16_tri():
    exp = {"a1": "dobre", "a2": "średnie", "a3": "słabe", "a4": "średnie", "a5": "średnie", "a6": "średnie"}
    for name in ("P5.15", "P5.16"):
        assert run(name)["categories"] == exp
    st = run("P5.15")["steps"]
    # program ELECTRE TRI (P5.17, rys. 8)
    assert [[round(x, 3) for x in row] for row in st["sigma_a_b"]] == [
        [0.96, 0.92], [1.0, 0.079], [0.71, 0.0], [0.887, 0.62], [1.0, 0.71], [0.92, 0.0]]
    assert [[round(x, 3) for x in row] for row in st["sigma_b_a"]] == [
        [0.0, 1.0], [0.0, 0.92], [0.83, 0.887], [0.5, 0.96], [0.222, 0.835], [0.0, 0.79]]


def test_p5_19_electre_i_sd():
    r = run("P5.19")
    st = r["steps"]
    assert r2(st["concordance_sum"]) == [[0, 0.25, 0.65, 0.35, 0.25], [0.75, 0, 0.4, 0.35, 0.25],
                                         [0.35, 0.6, 0, 0.35, 0.6], [0.65, 0.65, 0.65, 0, 0.65],
                                         [0.75, 1.0, 0.75, 0.35, 0]]
    assert edges(r) == {("a2", "a1"), ("a5", "a1"), ("a5", "a2"), ("a5", "a3")}       # rys. 9
    assert edges(run("P5.19", include_unclear=False)) == {("a2", "a1"), ("a5", "a1"), ("a5", "a2")}
    r65 = run("P5.19", s=0.65, include_unclear=False)
    assert edges(r65) >= {("a4", "a5"), ("a5", "a2"), ("a2", "a1"), ("a1", "a3")}


def test_p5_20_electre_iii_sd():
    r = run("P5.20")
    S = [[round(x, 4) for x in row] for row in r["steps"]["credibility"]]
    assert S[1][3] == 0.0541 and S[4][0] == 0.1242 and S[4][2] == 0.2 and S[2][1] == 0.07   # druk 0,0070
    assert r["steps"]["descending_classes"] == [["a4"], ["a5"], ["a1", "a2", "a3"]]
    assert r["steps"]["ascending_classes"] == [["a4"], ["a1", "a3", "a5"], ["a2"]]
    assert r["scores"]["values"] == [3, 4, 3, 1, 2]


def test_threshold_alpha_beta():
    e = examples.get("P5.13")
    p = dict(e["problem"])
    p["criteria"] = [dict(c, p=[0, c["p"]], q=[0, c["q"]], v=[0, c["v"]]) for c in p["criteria"]]
    r = api.run({"method": "electre_iii", "problem": p})
    assert r["ranking"] == run("P5.13")["ranking"]


def test_final_ranking_incomparable():
    rel, lv = final_ranking([1, 2], [2, 1])
    assert rel[0][1] == "R" and lv == [1, 1]


def test_distillation_single():
    cl, _ = distillation([[1.0]], True)
    assert cl == [[0]]


def test_errors():
    e = examples.get("P5.10")
    with pytest.raises(ProblemError):
        api.run({"method": "electre_i", "problem": e["problem"], "options": {"s": 0.8}})
    with pytest.raises(ProblemError):
        api.run({"method": "electre_tri", "problem": e["problem"]})
    with pytest.raises(ProblemError):
        api.run({"method": "electre_iii", "problem": e["problem"]})          # brak progu p
