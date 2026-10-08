# textack/ui/screens/outro.py
"""Outro screen — verbatim move from main.py:1280-1319 show_outro."""
import curses
import time

from textack import VERSION
from textack.infra.storage import load_best
from textack.ui import fx
from textack.ui.widgets import safe_add


def show(stdscr, P):
    """Layar selesai: fade out game -> fade in credit -> fade out. Skippable."""
    stdscr.nodelay(True)
    stdscr.timeout(33)
    fx.fade_out(stdscr, dur=0.45)
    fx.fade_in_blank(stdscr, dur=0.3)
    best = load_best()
    t0 = time.monotonic()
    hold = 2.8
    last = t0
    while True:
        now = time.monotonic()
        _dt = min(0.05, now - last)
        last = now
        h, w = stdscr.getmaxyx()
        cx = w // 2
        t = now - t0
        # skip dengan tombol
        if stdscr.getch() != -1 or t >= hold:
            break
        # ramp brightness: dim -> normal -> bold (ilusi fade in)
        if t < 0.35:
            attr_main, attr_sub = P["dim"], P["dim"]
        elif t < 0.7:
            attr_main, attr_sub = P["fg"], P["dim"]
        else:
            attr_main, attr_sub = P["cyan"], P["fg"]
        pulse = curses.A_BOLD if (now * 2.5) % 1 < 0.6 else 0
        stdscr.erase()
        safe_add(stdscr, h // 2 - 3, cx - 9, "— SIEGE SELESAI —", attr_sub)
        # credit utama dengan glow halus
        credit = "made by rewsaqy • 2026"
        safe_add(stdscr, h // 2 - 1, cx - len(credit) // 2, credit, attr_main | pulse)
        safe_add(stdscr, h // 2, cx - 14, f"TEXTACK v{VERSION} • 100% open source • GPL-3.0", attr_sub)
        if best["wave"] > 0:
            safe_add(stdscr, h // 2 + 2, cx - 14, f"best wave {best['wave']} • {best['wpm']:.0f} WPM", P["dim"])
        safe_add(stdscr, h - 2, cx - 12, "tekan tombol untuk lewat…", P["dim"])
        stdscr.refresh()
        time.sleep(0.033)
    fx.fade_out(stdscr, dur=0.5)
