"""python -m mcdm_cd stem PLIK.mcf      — dialog STEM-DPR w terminalu
   python -m mcdm_cd dom PLIK.mcf       — macierze dominacji (jak arkusz „Wykryte dominacje”)"""
import sys

from .mcf import read_mcf
from .stem_dpr import ConsoleStemDM, StemDPR

LAB = {7.0: "FSD", 6.0: "SSD", 4.0: "TSD", 128.0: ""}


def main(argv):
    if len(argv) != 2 or argv[0] not in ("stem", "dom"):
        print(__doc__)
        return 2
    p = read_mcf(argv[1])
    for w in p.warnings:
        print("Uwaga:", w)
    s = StemDPR(p)
    if argv[0] == "dom":
        for k in range(p.m):
            print(f"\nDla kryterium {p.criteria[k]}")
            print(" " * 6 + "".join(v.ljust(11) for v in p.variants))
            for i in range(p.n):
                cells = [LAB.get(x, f"AFSD({x:.2f})" if x else "") for x in s.dom[k][i]]
                print(p.variants[i].ljust(6) + "".join(c.ljust(11) for c in cells))
        return 0
    r = s.run(ConsoleStemDM())
    print("\nWynik:", r.status, "" if r.solution is None else p.variants[r.solution])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
