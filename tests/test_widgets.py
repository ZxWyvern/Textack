# tests/test_widgets.py
from textack.ui import widgets


class FakeScr:
    def __init__(self, h=24, w=80): self.h, self.w, self.calls = h, w, []
    def getmaxyx(self): return (self.h, self.w)
    def addstr(self, y, x, s, attr=0): self.calls.append((y, x, s))
def test_hp_bar_segments():
    s = widgets.hp_bar_str(50, 70, 100, 10)
    assert s.startswith("[") and "50/100" in s
def test_safe_add_clips_negative():
    f = FakeScr()
    widgets.safe_add(f, 0, -3, "hello")
    assert f.calls and f.calls[0][2] == "lo"
def test_safe_add_offscreen_no_crash():
    f = FakeScr(h=5, w=10)
    widgets.safe_add(f, 99, 99, "x")
    assert f.calls == []
