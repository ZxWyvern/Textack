# textack/ui/screens/upgrade.py
"""Upgrade overlay — verbatim move from main.py:538-615 show_upgrade_overlay.

Supports both Upgrade objects (T3 roll_choices) and dicts via get_field helper.
"""
import curses
import time

from textack.ui.widgets import get_field, safe_add


def show(stdscr, P, choices, level, owned):
    """Pause game, tampilkan 3 kartu upgrade dengan animasi slide+glow. Return index."""
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    sel = 0
    t0 = time.monotonic()
    # animasi slide-in: offset awal
    while True:
        now = time.monotonic()
        t = now - t0
        h, w = stdscr.getmaxyx()
        cx = w // 2
        # input
        stdscr.nodelay(True)
        stdscr.timeout(33)
        key = stdscr.getch()
        # konsumsi semua
        while key != -1:
            if key in (curses.KEY_LEFT, ord("h"), ord("a")):
                sel = (sel - 1) % len(choices)
            elif key in (curses.KEY_RIGHT, ord("l"), ord("d")):
                sel = (sel + 1) % len(choices)
            elif key in (curses.KEY_UP, ord("k")):
                sel = (sel - 1) % len(choices)
            elif key in (curses.KEY_DOWN, ord("j")):
                sel = (sel + 1) % len(choices)
            elif key in (ord("1"), ord("2"), ord("3")):
                idx = key - ord("1")
                if 0 <= idx < len(choices):
                    stdscr.nodelay(True)
                    stdscr.timeout(33)
                    return idx
            elif key in (10, 13, ord(" ")):
                stdscr.nodelay(True)
                stdscr.timeout(33)
                return sel
            key = stdscr.getch()

        stdscr.erase()
        # backdrop gelap + judul dengan pulse
        pulse = curses.A_BOLD if (now * 3) % 1 < 0.6 else 0
        safe_add(stdscr, max(1, h // 2 - 9), cx - 12, f"✦ LEVEL {level} UP! PILIH UPGRADE ✦", P["yellow"] | pulse)
        safe_add(stdscr, max(1, h // 2 - 8), cx - 20, "base makin kuat sambil tetap nyerang  •  1/2/3 atau ←→ + Enter", P["dim"])

        # layout kartu: horizontal kalau lebar, vertikal kalau sempit
        wide = w >= 90
        cw, ch = (24, 9) if wide else (min(52, w - 6), 7)
        # slide-in halus: offset mengecil seiring t
        slide = max(0, int(12 - t * 30))
        for i, u in enumerate(choices):
            lv = owned.get(get_field(u, "id"), 0)
            if wide:
                bx = cx + (i - 1) * (cw + 3) - cw // 2
                by = h // 2 - 5 + (slide if i == 1 else slide // 2)
            else:
                bx = cx - cw // 2
                by = h // 2 - 5 + i * (ch + 1) + slide
            is_sel = (i == sel)
            border_attr = (P["cyan"] | pulse) if is_sel else P["dim"]
            fill_attr = P["fg"] if is_sel else P["dim"]
            # border kartu
            top = "┏" + "━" * (cw - 2) + "┓"
            bot = "┗" + "━" * (cw - 2) + "┛"
            safe_add(stdscr, by, bx, top, border_attr)
            for r in range(1, ch - 1):
                safe_add(stdscr, by + r, bx, "┃", border_attr)
                safe_add(stdscr, by + r, bx + cw - 1, "┃", border_attr)
            safe_add(stdscr, by + ch - 1, bx, bot, border_attr)
            # isi kartu
            cat_col = {"ATTACK": P["red"], "DEFENSE": P["green"], "SPEED": P["cyan"], "BASE": P["magenta"]}.get(get_field(u, "cat"), P["fg"])
            safe_add(stdscr, by + 1, bx + 2, f"{get_field(u, 'icon')} [{get_field(u, 'cat')}]", cat_col)
            safe_add(stdscr, by + 2, bx + 2, f"{i+1}. {get_field(u, 'name')}"[: cw - 4], P["cyan"] | curses.A_BOLD if is_sel else P["fg"])
            safe_add(stdscr, by + 3, bx + 2, get_field(u, "desc")[: cw - 4], fill_attr)
            safe_add(stdscr, by + 4, bx + 2, f"Lv {lv} → {lv+1}/{get_field(u, 'max')}", P["yellow"] if is_sel else P["dim"])
            if wide:
                safe_add(stdscr, by + 5, bx + 2, "ENTER untuk ambil", P["dim"])
        stdscr.refresh()
        time.sleep(0.033)
