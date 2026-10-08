import importlib


def test_version_exists():
    import textack
    assert textack.VERSION == "1.0.00"


def test_main_importable():
    m = importlib.import_module("textack.__main__")
    assert callable(getattr(m, "main"))
