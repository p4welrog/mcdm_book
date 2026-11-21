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
