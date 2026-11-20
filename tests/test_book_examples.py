"""Zgodność z przykładami z książki i płyty CD. Wartości referencyjne — z druku (tolerancja wg liczby
miejsc po przecinku) albo z przeliczeń opisanych w erracie, gdy druk zawiera błąd."""
import json
import subprocess
import sys

import pytest

from mcdm_book import ProblemError, api, examples
from mcdm_book.additive import quadratic_fit, value_function
from mcdm_book.weights import rank_sum, roc

ap = pytest.approx


def run(name, **opts):
    req = examples.get(name)
    req["options"].update(opts)
    return api.run(req)


def vals(r):
    return r["scores"]["values"]


# ---- rozdz. 2 ----

def test_p2_1_saw():
    r = run("P2.1")
    assert vals(r) == ap([0.43, 0.34, 0.71, 0.30, 0.45], abs=0.005)
    assert [round(x, 2) for x in r["steps"]["normalized"][0]] == [1.00, 0.20, 0.45]
    assert r["ranking"] == ["a3", "a5", "a1", "a2", "a4"]          # druk: a5 dwukrotnie (errata P2.1)


def test_p2_2_scoring():
    r = run("P2.2")
    assert vals(r) == [43, 34, 71, 30, 45]
    assert r["ranking"] == ["a3", "a5", "a1", "a2", "a4"]


def test_p2_2_scoring_cap():
    req = examples.get("P2.2")
    req["problem"]["values"][0][0] = 11
    with pytest.raises(ProblemError):
        api.run(req)


def test_p2_3_fsaw():
    r = run("P2.3")
    assert vals(r) == ap([0.73, 0.68, 0.95, 0.44, 0.74], abs=0.005)
    assert r["steps"]["fuzzy_scores"][0] == ap([0.30, 0.67, 1.21], abs=0.005)
    assert r["ranking"] == ["a3", "a5", "a1", "a2", "a4"]


def test_p2_5_value_function():
    a, b, c = quadratic_fit([[48, 0], [58, 25], [70, 50], [86, 75], [120, 100]])
    assert (a, b, c) == (ap(-0.0174, abs=5e-5), ap(4.304, abs=5e-4), ap(-166.38, abs=5e-3))
    pts = [[48, 0], [58, 25], [70, 50], [86, 75], [120, 100]]
    assert value_function(pts, 66, "quadratic") == ap(41.89, abs=0.15)   # druk: współczynniki zaokrąglone
    assert value_function(pts, 105, "quadratic") == ap(93.705, abs=0.35)   # druk zaokrągla do 93 (errata P2.5)
    assert value_function(pts, 66, "piecewise") == ap(25 + 25 * 8 / 12)


def test_p2_7_smart():
    # kolumna u_i2 według tekstu przykładu (tablica 2 w druku błędna — errata P2.7); f3: interpolacja
    # odcinkowo-liniowa (60 → 37,5; druk odczytuje 36 z paraboli Excela)
    r = run("P2.7")
    assert r["steps"]["weights"] == ap([30 / 205, 75 / 205, 100 / 205])
    U = r["steps"]["scores_0_100"]
    assert [round(u[0], 1) for u in U] == [11.1, 0.0, 100.0, 100.0]
    assert [u[2] for u in U] == ap([0, 37.5, 25, 100])
    assert vals(r) == ap([38.2, 25.6, 63.4, 63.4], abs=0.05)
    assert r["best"] == ["a3", "a4"] and r["ranks"] == [3, 4, 1, 1]


def test_p2_11_smarter():
    r = run("P2.11")
    assert r["steps"]["weights"] == ap([2 / 18, 5 / 18, 11 / 18])        # druk: w3 = 0,28 (errata P2.11)
    # druk: 29,011; 52,778; 59,056 (u33 zaokrąglone do 33); 72,222 — P2.12 (arkusz) podaje 59,260
    assert vals(r) == ap([29.011, 52.778, 59.259, 72.222], abs=0.002)
    assert r["ranking"] == ["a4", "a3", "a2", "a1"]
    rs = run("P2.11", weights="rank_sum")
    assert rs["steps"]["weights"] == ap([1 / 6, 2 / 6, 3 / 6])


def test_weight_tables_2_1_2_2():
    t21 = {2: [0.75, 0.25], 3: [0.61, 0.28, 0.11], 4: [0.52, 0.27, 0.15, 0.06], 5: [0.46, 0.26, 0.16, 0.09, 0.04],
           6: [0.41, 0.24, 0.16, 0.10, 0.06, 0.03], 7: [0.37, 0.23, 0.16, 0.11, 0.07, 0.04, 0.02]}
    t22 = {2: [0.67, 0.33], 3: [0.50, 0.33, 0.17], 4: [0.40, 0.30, 0.20, 0.10], 5: [0.33, 0.27, 0.20, 0.13, 0.07],
           6: [0.29, 0.24, 0.19, 0.14, 0.10, 0.05], 7: [0.25, 0.21, 0.18, 0.14, 0.11, 0.07, 0.04]}
    for n in range(2, 8):
        assert roc(n) == ap(t21[n], abs=0.0051)
        assert rank_sum(n) == ap(t22[n], abs=0.0051)
        assert sum(roc(n)) == ap(1) and sum(rank_sum(n)) == ap(1)


# ---- rozdz. 7 ----

def test_p7_1_topsis():
    r = run("P7.1")
    assert r["steps"]["ideal"] == ap([0.150, 0.075, 0.209, 0.105], abs=0.0005)
    assert r["steps"]["anti_ideal"] == ap([0.015, 0.017, 0.057, 0.010], abs=0.0005)
    assert r["steps"]["d_plus"] == ap([0.134, 0.115, 0.143, 0.158, 0.156, 0.160, 0.125, 0.141, 0.145], abs=0.0005)
    assert r["steps"]["d_minus"] == ap([0.115, 0.129, 0.144, 0.084, 0.155, 0.135, 0.118, 0.154, 0.089], abs=0.0005)
    assert vals(r) == ap([0.46, 0.53, 0.50, 0.35, 0.50, 0.46, 0.49, 0.52, 0.38], abs=0.005)
    assert r["ranking"][:2] == ["a2", "a8"] and r["ranking"][-2:] == ["a9", "a4"]   # druk: errata P7.1


def test_p7_3_fuzzy_topsis():
    r = run("P7.3")
    assert r["steps"]["ideal"][0] == ap([0.21, 0.21, 0.25], abs=0.005)
    assert r["steps"]["anti_ideal"][2] == ap([0.07, 0.10, 0.13], abs=0.005)
    # druk liczy z zaokrąglonych wartości pośrednich
    assert r["steps"]["d_plus"] == ap([0.348, 0.381, 0.345, 0.472, 0.353, 0.416, 0.325, 0.267, 0.441], abs=0.006)
    assert vals(r) == ap([0.498, 0.452, 0.497, 0.323, 0.484, 0.391, 0.523, 0.608, 0.361], abs=0.004)
    assert r["ranking"] == ["a8", "a7", "a1", "a3", "a5", "a2", "a6", "a9", "a4"]


def test_r14_fuzzy_topsis_reference_levels():
    r = run("R14")
    assert vals(r) == ap([0.2706, 0.6507, 0.1656, 0.3391, 0.5145, 0.5376], abs=0.0001)
    assert r["steps"]["normalized"][0][0] == ap([0.16, 0.19, 0.33], abs=0.005)
    assert r["steps"]["normalized"][1][1] == ap([0.54, 0.57, 0.60], abs=0.005)
    rb = run("R14", cost_norm="min_u")          # wzór (7.10) z druku: wartości ok. 2× większe (errata)
    assert rb["steps"]["normalized"][1][0] == ap([0.67, 1.00, 2.00], abs=0.005)


def test_p7_4_vikor():
    r = run("P7.4")
    st = r["steps"]
    assert st["S"] == ap([0.57, 0.66, 0.29, 0.70, 0.55], abs=0.005)
    assert st["R"] == ap([0.33, 0.30, 0.24, 0.60, 0.26], abs=0.005)
    assert st["Q"] == ap([0.47, 0.53, 0.00, 1.00, 0.34], abs=0.006)
    assert st["ranking_Q"] == ["a3", "a5", "a1", "a2", "a4"]
    assert st["ranking_S"] == ["a3", "a5", "a1", "a2", "a4"]   # druk: kolumny R i S zamienione (errata P7.4)
    assert st["ranking_R"] == ["a3", "a5", "a2", "a1", "a4"]
    assert st["DQ"] == 0.25 and st["W1"] and st["W2"] and r["best"] == ["a3"]


def test_vikor_rules():
    p = {"variants": ["x", "y", "z", "u"], "criteria": [{"name": "A", "weight": 0.5}, {"name": "B", "weight": 0.5}],
         "values": [[10, 0], [0, 10], [5, 5], [6, 4]]}
    r = api.run({"method": "vikor", "problem": p})
    st = r["steps"]
    Q = dict(zip(p["variants"], st["Q"]))
    a1 = st["ranking_Q"][0]
    assert not st["W1"]
    assert set(r["best"]) == {v for v in p["variants"] if Q[v] - Q[a1] < st["DQ"]}
    assert len(r["best"]) >= 2


# ---- interfejs ----

def test_cost_criteria_and_errors():
    p = {"variants": ["a", "b"], "criteria": [{"name": "koszt", "direction": "min", "weight": 1}],
         "values": [[10], [20]]}
    for m in ("saw", "topsis", "vikor"):
        assert api.run({"method": m, "problem": p})["best"] == ["a"]
    assert "error" in api.run_safe({"method": "saw", "problem": {**p, "values": [[1], [2, 3]]}})
    assert "error" in api.run_safe({"method": "nope", "problem": p})
    assert "error" in api.run_safe({"method": "saw", "problem": p, "options": {"foo": 1}})
    r = api.run({"method": "saw", "problem": {**p, "criteria": [{"name": "k", "direction": "min", "weight": 2}]}})
    assert any("znormalizowano" in n for n in r["notes"])


def test_cli(tmp_path):
    f = tmp_path / "z.json"
    f.write_text(json.dumps(examples.get("P7.1")), encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "mcdm_book", "run", str(f), "--option", "metric=1"],
                         capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert r["method"] == "topsis" and r["steps"]["metric"] == 1
    assert len(json.loads(subprocess.run([sys.executable, "-m", "mcdm_book", "methods"], capture_output=True,
                                         text=True, check=True).stdout)) == 8


def test_all_examples_json_serializable():
    for e in examples.listing():
        json.dumps(api.run(examples.get(e["id"])))
