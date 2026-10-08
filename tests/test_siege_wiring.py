# tests/test_siege_wiring.py
def test_siege_uses_core():
    import pathlib
    src = pathlib.Path("textack/ui/screens/siege.py").read_text(encoding="utf-8")
    assert "from textack.core" in src and "resolve_hit" in src
    assert "curses" in src  # ui layer allowed
