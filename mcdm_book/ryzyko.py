"""Połączenie metod z dominacjami stochastycznymi z pakietem `mcdm_ryzyko`.

`mcdm_ryzyko` (rozdz. 1.3, 8.3–8.4) liczy rozkłady, dominacje stochastyczne, STEM-DPR i INSDECM.
Tu: rozkłady z komórek zadania JSON, test dominacji SD_T dla metod z rozdz. 5–7 i przykładowe zadania
z płyty (pliki .mcf, rozdz. 10, przykład 8.5).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple

from mcdm_ryzyko import Kryterium, Problem as ProblemRyzyko, Relacja, Rozklad, porownaj, wczytaj_mcf

from .problem import ProblemError

DATA = Path(__file__).parent / "data"
RISKS = ("DARA", "INARA")
_TOL = 1e-9
_DOKLADNE = {"FSD", "SSD", "TSD", "SISD", "TISD1", "TISD2"}


def rozklad(v: Any, where: str) -> Rozklad:
    """Komórka zadania: {"values": [...], "probs": [...]}, {"obs": [...]} albo lista obserwacji."""
    try:
        if isinstance(v, dict):
            if "obs" in v:
                return Rozklad.z_obserwacji([float(x) for x in v["obs"]])
            return Rozklad([float(x) for x in v["values"]], [float(x) for x in v["probs"]])
        if isinstance(v, (list, tuple)) and v and all(isinstance(x, (int, float)) for x in v):
            return Rozklad.z_obserwacji([float(x) for x in v])
    except (KeyError, ValueError, TypeError) as e:
        raise ProblemError(f"{where}: niepoprawny rozkład ({e})")
    raise ProblemError(f"{where}: oczekiwano rozkładu {{\"values\": [...], \"probs\": [...]}} albo {{\"obs\": [...]}}")


def srednia(r: Rozklad) -> float:
    return float(r.wartosc_oczekiwana())


def dominance_test(risk: str, dominances: Optional[Sequence[str]]) -> Tuple[List[str], Callable]:
    """Relacje SD_T i funkcja test(F, G) → nazwa najsilniejszej relacji F nad G z listy albo None.

    Domyślnie cała grupa dla typu ryzyka (rozdz. 1.3.1): DARA — FSD, SSD, TSD; INARA — FSD, SISD, TISD1, TISD2.
    Prawie dominacje jako "AFSD:ε" / "ASSD:ε" (tabl. 1.2, wzory 1.29–1.30): stopień naruszenia ≤ ε,
    dla ASSD także μ_i ≥ μ_j.
    TSD, TISD1, TISD2 według definicji (1.23), (1.25), (1.26), bez warunku średniej.
    """
    if risk not in RISKS:
        raise ProblemError(f"risk: {', '.join(RISKS)}")
    allowed = list(dominances) if dominances else (["FSD", "SSD", "TSD"] if risk == "DARA"
                                                   else ["FSD", "SISD", "TISD1", "TISD2"])
    exact, almost = [], []
    for a in allowed:
        name, _, eps = str(a).partition(":")
        name = name.strip().upper()
        if name in ("AFSD", "ASSD"):
            try:
                almost.append((name, float(eps)))
            except ValueError:
                raise ProblemError(f"dominances: {a!r} — podaj stopień, np. \"AFSD:0.333\"")
        elif name in _DOKLADNE:
            exact.append(name)
        else:
            raise ProblemError(f"dominances: nieznana dominacja {a!r}")

    def test(x: Rozklad, y: Rozklad) -> Optional[str]:
        if x == y:
            return None
        w = porownaj(x, y)
        for nme in exact:
            if w.zachodzi(Relacja[nme]):
                return nme
        for nme, eps in almost:
            if w.afsd(eps) if nme == "AFSD" else w.assd(eps):
                e = w.eps_afsd if nme == "AFSD" else w.eps_assd
                return f"{nme}({float(e):.3f})"
        return None
    return allowed, test


# ---------------------------------------------------------------------------
# Zadania z płyty dla STEM-DPR, INSDECM i ATO-DPR
# ---------------------------------------------------------------------------

EXAMPLES = {
    "przyklad_8_1": "przyklad_8_1.mcf — przykłady 8.1–8.4 (4 kryteria, 10 wariantów)",
    "Przyklad_1": "Przyklad_1.mcf — przykład STEM-DPR z instrukcji MCDM (3 kryteria, 20 wariantów)",
    "rozdz_10": "rozdz. 10 — 14 portfeli projektów (R10.3–R10.4, tabl. 10.4; 6 kryteriów)",
    "przyklad_8_5": "przykład 8.5 (ATO-DPR) — jak 8.1, z zamienionymi rozkładami f1 wariantów a6 i a8",
}


def example(name: str) -> ProblemRyzyko:
    """Zadanie z płyty jako `mcdm_ryzyko.Problem`."""
    if name in ("przyklad_8_1", "Przyklad_1"):
        return wczytaj_mcf(DATA / f"{name}.mcf")
    if name == "przyklad_8_5":
        p = wczytaj_mcf(DATA / "przyklad_8_1.mcf")
        oceny = [[p.ocena(i, k) for k in range(p.n)] for i in range(p.m)]
        a6, a8 = p.indeks_wariantu("a6"), p.indeks_wariantu("a8")
        oceny[a6][0], oceny[a8][0] = oceny[a8][0], oceny[a6][0]
        return ProblemRyzyko(p.kryteria, p.warianty, oceny)
    if name == "rozdz_10":
        d = json.loads((DATA / "rozdz_10.json").read_text(encoding="utf-8"))
        oceny = [[Rozklad(v, pr) for v, pr in row] for row in d["dist"]]
        return ProblemRyzyko([Kryterium(c) for c in d["criteria"]], d["variants"], oceny)
    raise ValueError(f"Nieznany przykład {name}")
