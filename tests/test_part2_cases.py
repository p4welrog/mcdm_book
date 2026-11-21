"""Część II książki (rozdz. 9–16): przypadki zastosowań odtworzone pakietem.

Wartości oczekiwane pochodzą z druku albo z płyty; rozbieżności z drukiem są opisane w README
(„Zgodność z książką” → „Część II”) i sprawdzane tu wprost."""
import pytest

from mcdm_book import api
from mcdm_book.examples import EXAMPLES
from mcdm_cd.insdecm import Insdecm, ScriptedInsdecmDM
from mcdm_cd.mcf import example
from mcdm_cd.stem_dpr import ScriptedStemDM, StemDPR


def run(key, **opt):
    e = EXAMPLES[key]
    return api.run({"method": e["method"], "problem": e["problem"], "options": {**e["options"], **opt}})


def scores(r):
    return dict(zip(r["variants"], r["scores"]["values"]))


ORDER_95 = ["a3", "a7", "a8", "a6", "a10", "a5", "a9", "a2", "a1", "a4"]


def test_r9_5_promethee_ii_veto():
    """Tabl. 9.6 / R9.5, tabl. 24: kolejność jak w druku, Φ w ±0,003 (zaokrąglenia pośrednie σ do 3 miejsc)."""
    r = run("R9.5")
    assert r["ranking"] == ORDER_95
    printed = [-1.299, -1.234, 3.340, -4.572, -1.054, 0.932, 3.057, 2.630, -1.192, -0.608]
    for x, y in zip(r["scores"]["values"], printed):
        assert x == pytest.approx(y, abs=0.0035)
    # zbiory D (tabl. 22): f9 w D(a1, aj) dla wszystkich 9 projektów; pełne weto (d9 = 1) wobec 8 (poza a5)
    D = r["steps"]["D_sets"]
    assert sum("f9" in (D[0][j] or "") for j in range(10)) == 9
    d9 = [r["steps"]["discordance"][8][0][j] for j in range(10)]
    assert sum(x == pytest.approx(1) for x in d9) == 8 and d9[4] < 1


def test_r9_5_exprom_ii_veto():
    """Tabl. 9.6 / R9.5, tabl. 37."""
    r = run("R9.5E")
    assert r["ranking"] == ORDER_95
    printed = [-2.102, -1.195, 3.898, -5.857, -0.926, 1.313, 3.719, 3.008, -1.088, -0.770]
    for x, y in zip(r["scores"]["values"], printed):
        assert x == pytest.approx(y, abs=0.0035)


def test_r11_anp_erp():
    """R11.1 → R11.3 i tabl. 11.13: priorytety 0,3035; 0,4415; 0,2550 (przeliczenie 0,2551)."""
    r = run("R11")
    assert r["ranking"] == ["IM5", "IFS", "SAP"]
    for x, y in zip(r["scores"]["values"], [0.3035, 0.4415, 0.2550]):
        assert x == pytest.approx(y, abs=0.00015)
    lim = r["steps"]["priorities_all"]
    r113 = {"F": 0.0928, "FX": 0.0619, "S": 0.1167, "SA": 0.0921, "UF": 0.0341, "R": 0.1373, "SI": 0.0179,
            "SR": 0.0282, "TA": 0.1448, "FOC": 0.0216, "IT": 0.0151, "MS": 0.0127, "SS": 0.0143, "TC": 0.0630,
            "IFS": 0.0448, "IM5": 0.0651, "SAP": 0.0376}
    for e, v in r113.items():
        assert lim[e] == pytest.approx(v, abs=0.00006)


def test_r15_promethee_ii_not_reproducible():
    """Tabl. 15.6 nie odtwarza się z danych tabl. 15.4: a24 i a42 (w druku poz. 1 i 4) wypadają poza ósemkę."""
    r = run("R15")
    s = scores(r)
    assert r["ranking"][:8] == ["a37", "a41", "a2", "a26", "a8", "a68", "a67", "a66"]
    assert s["a24"] == pytest.approx(-0.0065, abs=0.0001)
    assert s["a42"] == pytest.approx(-0.0236, abs=0.0002)
    assert abs(sum(s.values())) < 1e-9


@pytest.mark.parametrize("s,edges,levels", [
    (0.94, 2, [["a1", "a2", "a3", "a4", "a5", "a7", "a8", "a9", "a10", "a11"], ["a6", "a12"]]),
    (0.91, 5, [["a3", "a4", "a5", "a7", "a8", "a9", "a10", "a11"], ["a2", "a6", "a12"], ["a1"]]),
    # s = 0,86: w druku a5 na poziomie 1; przewyższają go a4 i a10 → poziom 3 (errata, s. 289)
    (0.86, 10, [["a3", "a7", "a8", "a9", "a10", "a11"], ["a2", "a4", "a6", "a12"], ["a1", "a5"]]),
    (0.72, 38, [["a8", "a10"], ["a6", "a9", "a11"], ["a7"], ["a3", "a12"], ["a1", "a2", "a4", "a5"]]),
])
def test_r16_electre_i(s, edges, levels):
    """S. 288–290 i tabl. 16.5 (kol. 1); łuki dwukierunkowe nie blokują poziomu (reguła odtwarzająca druk)."""
    r = run("R16", s=s)
    assert len(r["steps"]["edges"]) == edges
    lv = r["steps"]["levels_top_down"]
    got = [[v for v, x in zip(r["variants"], lv) if x == L] for L in sorted(set(lv))]
    assert got == levels


# --- rozdz. 10: STEM-DPR i INSDECM (pakiet mcdm_cd) ---

@pytest.fixture(scope="module")
def r10():
    return example("rozdz_10")


def test_r10_data(r10):
    """Wartości oczekiwane = R10.5 (f1, f2 z binowanych rozkładów: ±0,03); rozkład a1 względem f3 = tabl. 10.5."""
    mu = [[r10.dist[i][k].mean() for k in range(6)] for i in range(14)]
    assert mu[0][0] == pytest.approx(483.93, abs=0.03)
    assert mu[5][1] == pytest.approx(-345.37, abs=0.03)
    assert mu[3][3] == pytest.approx(-26.55, abs=0.01)
    assert mu[6][5] == pytest.approx(56.33, abs=0.01)
    assert sorted(r10.dist[0][2].values) == [-42, -19, -18]


def test_r10_stem_dpr_book(r10):
    """Tabl. 10.6–10.7: d tylko z FSD i SSD; iteracja 1 → a8, f4 ≥ −25, iteracja 2 → a6."""
    s = StemDPR(r10, relations=("FSD", "SSD"))
    res = s.run(ScriptedStemDM([("f4", -25)], accept_after=2))
    it1, it2 = res.iterations
    assert it1.trial == 7 and it1.d == [6, 6, 1, 0, 5, 2]          # w druku d_86 = 6 (errata, s. 208)
    assert [i + 1 for i in it2.active_variants] == [3, 6, 7, 8, 10, 12]
    assert it2.trial == 5 and it2.d == [1, 1, 0, 3, 1, 3]
    assert it2.means[1] == pytest.approx(-345.37, abs=0.03)          # w druku −345,53 (errata, s. 209)
    assert res.status == "final" and res.solution == 5


def test_r10_stem_dpr_mcdm_default(r10):
    """Domyślnie (jak MCDM 1.00: TSD i AFSD w d) wynik liczbowy różni się od druku, wybór a8 bez zmian."""
    s = StemDPR(r10)
    t = s.trial_variant()
    assert t == 7 and s.d[t][0] == pytest.approx(6.89, abs=0.01)


def _ins(r10, first):
    init = {"f1": {8: 485}, "f3": {12: None}, "f4": {12: None}, "f5": {12: None}, "f6": {12: None}}
    p2 = dict(init, f2={8: -430})
    s = Insdecm(r10)
    return s.run(ScriptedInsdecmDM(initial=init, script=[
        {"condition": first}, {"params": p2, "condition": ("f2", 8, 0.6)},
        {"condition": ("f3", 12, -30)}, {"condition": None}]))


def test_r10_insdecm_condition_as_printed(r10):
    """S. 209–210: warunek P{ξ_i1 ≥ 485} ≥ 0,7 daje {a4, a9}, a nie 10 wariantów z druku (errata)."""
    res = _ins(r10, ("f1", 8, 0.7))
    assert [i + 1 for i in res.iterations[1].active] == [4, 9]
    assert res.iterations[2].active == []


def test_r10_insdecm_book_sets(r10):
    """Zbiór A(2) z druku (odtwarza go μ_i1 ≥ 482); dalej A(3), A(4) i P(4) jak w tabl. 10.11–10.13."""
    res = _ins(r10, ("f1", 1, 482))
    P1 = res.iterations[0].P.as_dict()
    assert P1[(0, 1)] == pytest.approx((435.36, 494.95), abs=0.03)
    assert P1[(2, 12)] == (-58.0, -24.0) and P1[(5, 12)] == (16.0, 43.5)
    assert [i + 1 for i in res.iterations[1].active] == [1, 3, 4, 5, 6, 8, 9, 10, 12, 14]
    assert [i + 1 for i in res.iterations[2].active] == [1, 3, 6, 8, 10, 12]
    assert [i + 1 for i in res.solutions] == [6, 8]
    P4 = res.iterations[3].P.as_dict()
    assert P4[(2, 12)] == (-28.5, -24.0) and P4[(3, 12)] == (-39.0, -25.5)
    assert P4[(4, 12)] == (-28.5, -18.0) and P4[(5, 12)] == (29.0, 39.5)


def test_r12_bipolar_parameters():
    """Rozdz. 12: τ z decyli R12.2 = 75, 76, 57, 72, 55, 85, 62 (druk: τ6 = 84), ρ = 0,69, wagi tabl. 12.6
    (f6: 0,18 zamiast 0,17); progi weta = 3. decyl zwycięzców z danych (druk: decyle tabl. 12.3)."""
    r = run("R12")
    st = r["steps"]
    assert st["mu"] == [75, 76, 57, 72, 55, 85, 62]
    assert round(st["omega"], 2) == 0.69
    assert [round(w, 2) for w in st["weights"]] == [0.16, 0.16, 0.12, 0.15, 0.11, 0.18, 0.13]
    v = [-x for x in st["v"]]
    v[2] = -v[2]                                                         # ROE maksymalizowane
    assert v == pytest.approx([14.770, 1.3755, 0.0626, 0.7423, 0.4725, 0.8379, 0.0435], abs=1e-3)


def test_r12_bipolar_ranking_differs_from_cd():
    """R12.4 (program autora) nie odtwarza się z R12.1–R12.2: mianowniki 150 i 195 zamiast 149 i 194,
    kategoria S1 bez OLAWA; zgodna pierwsza pozycja (ELZAB) i kategoria S1 dla ELZAB, JELFA."""
    r = run("R12")
    st = r["steps"]
    assert r["ranking"][0] == "ELZAB"
    s1 = [v for v, c in zip(r["variants"], st["S_category"]) if c == "S1"]
    assert s1 == ["ELZAB", "JELFA", "OLAWA"]
    assert round(st["d_S"][r["variants"].index("ELZAB")] * 149) == 103   # R12.4: 0,78 = 117/150


# ---------------------------------------------------------------------------
# Rozdz. 15.5.4 — AHP z porównaniami z różnic ocen (tabl. 15.7–15.8)
# ---------------------------------------------------------------------------

T158 = {"a24": .0377, "a42": .0365, "a26": .0296, "a37": .0295, "a41": .0285, "a2": .0272, "a68": .0264, "a8": .0257,
        "a67": .0253, "a39": .0252, "a29": .025, "a52": .0248, "a57": .0245, "a59": .0243, "a19": .0243, "a66": .024,
        "a43": .0237, "a13": .0235, "a21": .0234, "a23": .0225, "a65": .0225, "a38": .0224, "a28": .0224,
        "a70": .0222, "a7": .022, "a12": .0214, "a74": .0205, "a11": .0203, "a20": .0201, "a15": .0193,
        "a31": .0187, "a14": .0168, "a55": .0167, "a48": .0166, "a32": .0159, "a62": .0141, "a69": .0139,
        "a40": .0135, "a35": .0134, "a16": .013, "a25": .0123, "a27": .0123, "a44": .0122, "a47": .0108,
        "a50": .0107, "a18": .0097, "a1": .0097, "a72": .0087, "a73": .0076, "a17": .0075, "a6": .0052}


def test_r15_ahp_weights():
    """Tabl. 15.5: wektor własny 0,570; 0,097; 0,333 (druk: 0,57; 0,10; 0,33), γ ≈ 0,02."""
    r = run("R15A")
    w = r["steps"]["criteria_weights"]
    assert w == pytest.approx([0.5695, 0.0974, 0.3331], abs=1e-4)
    assert r["steps"]["matrices"][0]["gamma"] < 0.03


def test_r15_ahp_difference_matrix():
    """Tabl. 15.7 z zamienionymi nagłówkami: zakresy w [0; 1] dla f1 i f3, do 82 dla f2 (sprzedaż)."""
    r = run("R15A")
    V = r["variants"]
    M1 = r["steps"]["matrices"][1]["matrix"]            # f1: a24 (0,98) vs a6 (0,30): różnica 0,68 → 7
    assert M1[V.index("a24")][V.index("a6")] == 7 and M1[V.index("a6")][V.index("a24")] == pytest.approx(1 / 7)
    M2 = r["steps"]["matrices"][2]["matrix"]            # f2: a21 (82) vs a25 (0) → 9; 63 − 9 = 54 → 6
    assert M2[V.index("a21")][V.index("a25")] == 9 and M2[V.index("a15")][V.index("a24")] == 6
    M3 = r["steps"]["matrices"][3]["matrix"]            # f3: 0,9 − 0,8 = 0,1 → 1 (zaokrąglenie różnicy)
    assert M3[V.index("a8")][V.index("a2")] == 1


def test_r15_ahp_not_reproduced():
    """Tabl. 15.8 nieodtwarzalna co do wartości: mediana |różnicy| 0,0005, ρ Spearmana 0,989, ale a42, a24, a39
    (f3 ≤ 0,1) wychodzą wyraźnie niżej (0,0261; 0,0341; 0,0227). Ósemka pakietu: a24, a26, a37, a41, a2, a68,
    a42, a67 (druk: a8 zamiast a67). Dosłowne nagłówki tabl. 15.7 dają ρ = 0,70."""
    r = run("R15A")
    s = scores(r)
    diffs = sorted(abs(s[v] - T158[v]) for v in s)
    assert diffs[len(diffs) // 2] < 0.0006
    assert s["a42"] == pytest.approx(0.0261, abs=2e-4) and s["a24"] == pytest.approx(0.0341, abs=2e-4)
    assert set(r["ranking"][:8]) == {"a24", "a26", "a37", "a41", "a2", "a68", "a42", "a67"}
    assert r["ranking"][0] == "a24"


# ---------------------------------------------------------------------------
# Rozdz. 9.5 — RPO WSL: punkty ważone (R9.7–R9.8), mierniki zgodności (R9.6, R9.10–R9.11)
# ---------------------------------------------------------------------------

def test_r9_7_weighted_points():
    """„Ocena łączna” R9.7 = 0,4·Σ w f (f1–f9) + 0,6·Σ w f (f10–f16) poza 11 projektami Eksperta I i 6 Eksperta II.
    Ekspert I a13: z tabl. 9.9 (f10 = 4, w R9.7: 3) wychodzi 26,6 jak w druku; a23: f14 = 5 poza skalą 0–4
    (z 4 → 28,7 jak w druku); a38: f12 = 4,5 (z 3 → 26,2); a48: f16 = 0 (z 4 → 26,3); a9: f15 = 0,5 (z 1 → 29,3)."""
    from mcdm_book.data_r9 import R9_7_I_TOTAL, R9_7_II_TOTAL
    bad = {}
    for key, tot in (("R9.7I", R9_7_I_TOTAL), ("R9.7II", R9_7_II_TOTAL)):
        s = run(key)["scores"]["values"]
        bad[key] = [i + 1 for i, (a, b) in enumerate(zip(s, tot)) if abs(a - b) > 0.051]
    assert bad["R9.7I"] == [1, 2, 9, 13, 23, 31, 38, 39, 40, 48, 54]
    assert bad["R9.7II"] == [1, 8, 11, 15, 16, 36]
    e = EXAMPLES["R9.7I"]
    for proj, k, val, printed in ((13, 9, 4, 26.6), (23, 13, 4, 28.7), (38, 11, 3, 26.2), (48, 15, 4, 26.3),
                                  (9, 14, 1, 29.3)):
        row = list(e["problem"]["values"][proj - 1])
        row[k] = val
        assert sum(c["weight"] * x for c, x in zip(e["problem"]["criteria"], row)) == pytest.approx(printed, abs=1e-9)


def test_r9_8_positions_from_printed_totals():
    """R9.8 / R9.10 (kolumna S): pozycje z „oceny łącznej” z druku (rangi z remisami), nie z ocen kryteriów;
    jedyna różnica — Ekspert II a20 (29,2: pozycja 18, druk 17 razem z a16)."""
    from mcdm_book.data_r9 import R9_10_S_I, R9_10_S_II, R9_7_I_TOTAL, R9_7_II_TOTAL
    from mcdm_book.problem import ranks
    assert ranks(R9_7_I_TOTAL) == R9_10_S_I
    diff = [(i + 1, a, b) for i, (a, b) in enumerate(zip(ranks(R9_7_II_TOTAL), R9_10_S_II)) if a != b]
    assert diff == [(20, 18, 17)]


def test_r9_11_agreement_indices():
    """R9.11 z pozycji R9.10 dokładnie: 59,22 % / 74,01 %, 65,89 % / 76,50 %, 80,67 % / 89,27 %, 84,11 % / 92,15 %."""
    from mcdm_book.data_r9 import R9_10_EIII_I, R9_10_EIII_II, R9_10_S_I, R9_10_S_II
    cases = [((R9_10_EIII_I, R9_10_EIII_II), (59.22, 74.01)), ((R9_10_S_I, R9_10_S_II), (65.89, 76.50)),
             ((R9_10_S_I, R9_10_EIII_I), (80.67, 89.27)), ((R9_10_S_II, R9_10_EIII_II), (84.11, 92.15))]
    for pos, (z2, z3) in cases:
        r = api.run({"method": "agreement", "positions": [list(pos[0]), list(pos[1])]})
        assert round(100 * r["position_agreement"], 2) == z2
        assert round(100 * r["order_agreement"], 2) == z3


def test_r9_9_electre_iii_positions_consistent():
    """R9.9 a R9.10 (EIII): R9.9 dla Eksperta II podaje projekt 7 na poz. 1 i 2, projekt 32 na poz. 15 i 38,
    pomija 3 i 34; R9.10 — projekty 3, 9, 13 na poz. 2 i 28, 34, 36, 42, 50 na poz. 38. Pozycje R9.10 są
    rangami z remisami (pozycja = 1 + liczba projektów wyżej)."""
    from mcdm_book.data_r9 import R9_10_EIII_I, R9_10_EIII_II
    for P in (R9_10_EIII_I, R9_10_EIII_II):
        assert all(p == 1 + sum(q < p for q in P) for p in P)
    assert [i + 1 for i, p in enumerate(R9_10_EIII_II) if p == 2] == [3, 9, 13]
    assert [i + 1 for i, p in enumerate(R9_10_EIII_II) if p == 38] == [28, 34, 36, 42, 50]
