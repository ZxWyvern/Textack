# textack/ui/screens/howto.py
"""Howto screen — verbatim move from main.py:502-535 show_howto."""
from textack.ui.widgets import safe_add


def show(stdscr, P):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        lines = [
            "CARA MAIN — 30 detik langsung bisa",
            "",
            "1. Kata muncul di atas benteng musuh, misal: sudo apt update",
            "2. Ketik PERSIS SAMA + Enter secepatnya = tembakan ▲",
            "3. Makin cepat = damage makin besar. Beruntun = COMBO crit.",
            "4. Salah ketik = musuh serang balik ke bentengmu.",
            "5. Diam terlalu lama = musuh nyicil. Jangan AFK.",
            "6. Tiap pukulan = XP. Naik LEVEL = pilih 1 dari 3 UPGRADE",
            "   ATTACK / DEFENSE / SPEED / BASE (14 macam, ala Survivor.io).",
            "7. Musuh per wave beda: SCOUT→RAIDER→GOLEM→OVERLORD→BOSS.",
            "   Makin tinggi wave: interval makin cepat + burst x1-x4.",
            "",
            "RANK: NEWBIE → SCRIPT KIDDIE → SYSADMIN → ROOT → KERNEL PANIC",
            "EDUKASI: semua kata = perintah Linux asli. Makin main makin hafal.",
            "",
            "[Enter] mulai siege   [Q] kembali",
        ]
        y0 = max(1, h // 2 - len(lines) // 2)
        for i, ln in enumerate(lines):
            a = P["cyan"] if i == 0 else (P["dim"] if i >= 8 else P["fg"])
            safe_add(stdscr, y0 + i, max(2, w // 2 - 32), ln[: w - 4], a)
        stdscr.refresh()
        k = stdscr.getch()
        if k in (10, 13):
            return "play"
        if k in (ord("q"), ord("Q"), 27):
            return "menu"
