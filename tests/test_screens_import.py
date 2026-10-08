# tests/test_screens_import.py
def test_screens_importable():
    from textack.ui.screens import opening, howto, upgrade, outro, loop
    for m in (opening, howto, upgrade, outro, loop):
        assert hasattr(m, "show") or hasattr(m, "game_loop")
