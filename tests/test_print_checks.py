"""Panel „Wynik pakietu a druk”: komplet wpisów i poprawność pól."""
from mcdm_book import examples, print_checks

ERRATA = {f"h-Przyklady-CD-do-rozdz-{n}" for n in range(1, 9)} | {f"h-Zbiory-CD-do-rozdz-{n}" for n in (9, 10, 11, 12, 13, 16)} \
    | set(print_checks._BOOK.values())


def test_every_example_has_check():
    ids = [e["id"] for e in examples.listing()]
    assert sorted(ids) == sorted(print_checks.CHECKS)


def test_fields():
    for k, c in print_checks.CHECKS.items():
        assert c["status"] in print_checks.STATUS, k
        assert c["summary"] and c["points"], k
        assert all(kind in ("ok", "diff", "conv", "info") and text for kind, text in c["points"]), k
        assert c["errata"] in ERRATA, k
        if c["status"] == "diff":
            assert any(kind == "diff" for kind, _ in c["points"]), k
        if c["status"] == "ok":
            assert not any(kind == "diff" for kind, _ in c["points"]), k


def test_get():
    c = print_checks.get("P6.7")
    assert c["id"] == "P6.7" and c["status"] == "diff" and c["status_label"] == "rozbieżności z drukiem"
    assert print_checks.get("nie-ma") is None
