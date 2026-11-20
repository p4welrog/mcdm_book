"""AHP, REMBRANDT, rozmyty AHP — zgodność z przykładami 3.3, 3.4, 3.7, 3.10 oraz poprawność solvera LP."""
import random
from math import log, sqrt

import pytest

from mcdm_book import ProblemError, api, examples
from mcdm_book.ahp import consistency, priority_vector, reciprocal_matrix
from mcdm_book.lp import LPError, linprog_max

ap = pytest.approx
A33 = [[1, 3, 7, 3, 7, 1 / 2], [1 / 3, 1, 5, 1 / 3, 4, 1 / 5], [1 / 7, 1 / 5, 1, 1 / 7, 1 / 4, 1 / 7],
       [1 / 3, 3, 7, 1, 5, 1 / 3], [1 / 7, 1 / 4, 4, 1 / 5, 1, 1 / 5], [2, 5, 7, 3, 5, 1]]


def run(name, **opts):
    req = examples.get(name)
    req["options"].update(opts)
    return api.run(req)


def test_p3_3_saaty_and_power():
    s = priority_vector(A33, "saaty")
    assert s["column_sums"] == ap([3.952, 12.450, 31.000, 7.676, 22.250, 2.376], abs=0.001)   # druk: σ4 = 6,876 (errata)
    assert s["w"] == ap([0.273, 0.106, 0.029, 0.174, 0.057, 0.362], abs=0.0005)
    assert s["lambda_max"] == ap(6.572, abs=0.001)
    pw = priority_vector(A33, "power")                       # ε = 0,001
    assert pw["w"] == ap([0.280, 0.102, 0.027, 0.174, 0.051, 0.366], abs=0.0006)
    assert pw["lambda_max"] == ap(6.552, abs=0.004)
    ev = priority_vector(A33, "eigen")
    assert ev["lambda_max"] == ap(6.5469, abs=1e-4)
    assert ev["w"] == ap([0.2802, 0.1016, 0.0271, 0.1738, 0.0508, 0.3665], abs=1e-4)


def test_consistency_table_3_1():
    c = consistency(3.007, 3)
    assert c["gamma"] == ap(0.006, abs=0.0005) and c["consistent"]
    assert consistency(6.547, 6)["gamma"] == ap(0.088, abs=0.0005)
    assert consistency(6.572, 6)["gamma"] == ap(0.092, abs=0.0005)
    assert not consistency(7.0, 6)["consistent"]


def test_consistent_matrix_exact():
    w = [0.5, 0.3, 0.2]
    A = [[a / b for b in w] for a in w]
    for m in ("saaty", "eigen", "geometric"):
        r = priority_vector(A, m)
        assert r["w"] == ap(w) and r["lambda_max"] == ap(3)


def test_p3_4_ahp():
    r = run("P3.4")
    st = r["steps"]
    assert st["criteria_weights"] == ap([0.088, 0.669, 0.243], abs=0.0005)
    mats = {m["name"]: m for m in st["matrices"]}
    assert mats["f1"]["w"] == ap([0.484, 0.162, 0.052, 0.212, 0.063, 0.027], abs=0.0005)
    assert mats["f2"]["lambda_max"] == ap(6.572, abs=0.001)
    assert mats["f3"]["w"] == ap([0.156, 0.185, 0.141, 0.126, 0.207, 0.185], abs=0.0005)
    assert r["scores"]["values"] == ap([0.263, 0.130, 0.058, 0.166, 0.094, 0.289], abs=0.001)
    assert r["ranking"] == ["a6", "a1", "a4", "a2", "a5", "a3"]
    assert run("P3.4", method="eigen")["ranking"] == r["ranking"]


def test_ahp_matrix_input():
    notes = []
    A = reciprocal_matrix([[1, "1/3", None], [None, 1, "2"], [5, None, 1]], 3, "M", notes)
    assert A[1][0] == 3 and A[0][2] == ap(0.2) and A[2][1] == 0.5 and not notes
    reciprocal_matrix([[1, 3], [2, 1]], 2, "M", notes)
    assert any("proporcjonalna" in n for n in notes)
    with pytest.raises(ProblemError):
        reciprocal_matrix([[1, None], [None, 1]], 2, "M", [])


def test_ahp_inconsistent_note():
    p = {"variants": ["x", "y", "z"], "criteria": [{"name": "k", "weight": 1}],
         "comparisons": {"k": [[1, 9, "1/9"], [None, 1, 9], [None, None, 1]]}}
    r = api.run({"method": "ahp", "problem": p})
    assert any("γ" in n and "niezgodne" in n for n in r["notes"])


def test_p3_7_rembrandt():
    r = run("P3.7")
    st = r["steps"]
    assert st["criteria_weights"] == ap([0.101, 0.643, 0.255], abs=0.0006)
    assert st["criteria"]["v"] == ap([0.397, 2.520, 1.0], abs=0.003)
    c = {m["name"]: m["w"] for m in st["matrices"]}
    assert c["f1"] == ap([0.554, 0.139, 0.041, 0.196, 0.049, 0.021], abs=0.0006)
    assert c["f2"] == ap([0.294, 0.083, 0.029, 0.208, 0.055, 0.330], abs=0.0006)
    assert c["f3"] == ap([0.443, 0.039, 0.047, 0.197, 0.052, 0.222], abs=0.0006)
    # druk: c = 0,349; 0,072; … nie daje się odtworzyć; agregacja geometryczna (3.31) wg erraty:
    assert r["scores"]["values"] == ap([0.371, 0.077, 0.036, 0.218, 0.057, 0.241], abs=0.002)
    assert r["ranking"] == ["a1", "a6", "a4", "a2", "a5", "a3"]
    assert any("antysymetryczna" in n for n in r["notes"])
    assert run("P3.7", gamma_variants=log(2))["ranking"] == r["ranking"]


def test_p3_10_fuzzy_ahp():
    r = run("P3.10")
    lv = r["steps"]["matrices"][0]["levels"]
    exp = [(0.71, 1.43), (0.72, 1.33), (0.73, 1.24), (0.74, 1.16), (0.74, 1.08), (0.75, 1.00)]   # tabl. 1
    for l, (w1, lam) in zip(lv, exp):
        assert l["w"][0] == ap(w1, abs=0.005) and l["lambda"] == ap(lam, abs=0.005)
    assert lv[4]["cuts"][0]["interval"] == ap([2.6, 3.2])          # druk: [2,2; 3,4] (errata P3.10)
    assert lv[0]["w"][0] == ap(5 / 7)
    assert r["scores"]["values"] == ap([0.74, 0.26], abs=0.005)


def test_fuzzy_ahp_crisp_consistent_reduces_to_ratios():
    w = [0.5, 0.3, 0.2]
    M = [[a / b for b in w] for a in w]
    p = {"variants": ["x", "y", "z"], "criteria": [{"name": "k", "weight": 1}], "comparisons": {"k": M}}
    r = api.run({"method": "fuzzy_ahp", "problem": p, "options": {"alphas": [1]}})
    assert r["scores"]["values"] == ap(w, abs=1e-9)


def test_lp_small():
    x, v = linprog_max([3, 5], [[1, 0], [0, 2], [3, 2]], [4, 12, 18])
    assert x == ap([2, 6]) and v == ap(36)
    x, v = linprog_max([1, 1], [[1, 2]], [4], [[1, -1]], [1])
    assert v == ap(3) and x == ap([2, 1])
    with pytest.raises(LPError):
        linprog_max([1, 0], [[-1, 1]], [0])
    with pytest.raises(LPError):
        linprog_max([1], [[1]], [1], [[1]], [2])


def test_lp_against_scipy():
    sp = pytest.importorskip("scipy.optimize")
    rnd = random.Random(7)
    for _ in range(200):
        n, m = rnd.randint(2, 5), rnd.randint(1, 6)
        c = [rnd.uniform(-1, 2) for _ in range(n)]
        A = [[rnd.uniform(-1, 3) for _ in range(n)] for _ in range(m)]
        b = [rnd.uniform(0.5, 5) for _ in range(m)]
        A.append([1] * n)
        b.append(10)
        Aeq = [[1] * n] if rnd.random() < 0.5 else []
        beq = [rnd.uniform(1, 3)] if Aeq else []
        ref = sp.linprog([-x for x in c], A_ub=A, b_ub=b, A_eq=Aeq or None, b_eq=beq or None, method="highs")
        if ref.status != 0:
            with pytest.raises(LPError):
                linprog_max(c, A, b, Aeq, beq)
            continue
        x, v = linprog_max(c, A, b, Aeq, beq)
        assert v == ap(-ref.fun, abs=1e-7)


def test_single_criterion_matrix():
    p = {"variants": ["x", "y"], "criteria": [{"name": "k"}], "criteria_comparisons": [[1]],
         "comparisons": {"k": [[1, [1, 3, 4]], [None, 1]]}}
    r = api.run({"method": "fuzzy_ahp", "problem": p})
    assert r["steps"]["criteria_weights"] == [1.0] and r["best"] == ["x"]
    p["comparisons"]["k"] = [[1, 3], [None, 1]]
    assert api.run({"method": "ahp", "problem": p})["scores"]["values"] == ap([0.75, 0.25])
