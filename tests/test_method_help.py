"""Pomoc do metod: wpis dla każdej metody strony."""
from mcdm_book import api, method_help


def test_every_method_has_help():
    ms = set(api.methods()) - {"select_method"}
    assert ms == set(method_help.HELP)


def test_fields():
    for k, h in method_help.HELP.items():
        assert h["use"] and h["result"], k
        assert all(isinstance(t, str) and t for t in h["tips"]), k
