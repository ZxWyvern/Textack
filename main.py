#!/usr/bin/env python3
"""Textack v1.0.00 - typing = damage. Opening ala agent TUI, 60fps, palet modern.
100% Open Source, GPL-3.0-or-later. Native Linux, stdlib only (curses).
Optimasi: redraw 60fps terjadwal, partikel di-cap, bintang adaptif, tanpa alloc berat.
"""
import curses
import os
import random
import sys
import time
from pathlib import Path

VERSION = "1.0.00"

TIER1 = ["ls", "cd", "pwd", "cat", "echo", "clear", "whoami", "mkdir", "touch", "rm"]
TIER2 = ["sudo", "grep", "chmod", "chown", "ps aux", "kill", "tar -xzf", "ssh", "curl", "wget"]
TIER3 = [
    "sudo apt update",
    "ps aux | grep nginx",
    "chmod +x main.py",
    "systemctl status sshd",
    "find /etc -name nginx",
    "tail -f /var/log/syslog",
    "df -h | grep sda",
    "ls -la ~/Documents",
]

ENEMY_ART = [
    r"      |>>>|      ",
    r"      |   |___   ",
    r"  _   |     | ___",
    r" |_|  | BENTENG |",
    r" |_|__|_________|",
]
PLAYER_ART = [
    r"  .-----------------.  ",
    r"  |  BENTENG KAMU   |  ",
    r"  |___         _____|  ",
    r"  |_|_|_______|_|_|_|  ",
]

# ---------- musuh per wave (interval + pola tergantung wave) ----------
def enemy_config(wave):
    """Return {name, interval, dmg, burst, hp, proj, col}."""
    is_boss = (wave % 5 == 0)
    if wave <= 2:
        c = {"name": "SCOUT", "interval": 6.5, "dmg": 6, "burst": 1, "hp": 60 + wave * 35, "proj": "▼", "col": "yellow"}
    elif wave <= 4:
        c = {"name": "RAIDER", "interval": 5.2, "dmg": 8, "burst": 1, "hp": 70 + wave * 42, "proj": "●", "col": "yellow"}
    elif wave <= 6:
        c = {"name": "GOLEM", "interval": 4.3, "dmg": 10, "burst": 2, "hp": 80 + wave * 48, "proj": "✦", "col": "red"}
    else:
        c = {"name": "OVERLORD", "interval": 3.5, "dmg": 12, "burst": 3, "hp": 90 + wave * 55, "proj": "✹", "col": "red"}
    if is_boss:
        c = dict(c)
        c["name"] = "BOSS " + c["name"]
        c["hp"] = int(c["hp"] * 1.7)
        c["burst"] = min(4, c["burst"] + 1)
        c["interval"] = max(2.6, c["interval"] * 0.85)
        c["dmg"] += 3
    # wave scaling halus biar makin nekan
    c["interval"] = max(2.6, c["interval"] - max(0, wave - 7) * 0.12)
    return c

# ---------- upgrade Survivor.io-style (bangun base sambil nyerang) ----------
# stats keys: dmg_mult, crit, crit_mult, perfect_win, max_hp, regen, shield,
# repair, lifesteal, xp_mult, slow, combo_guard, turret, turret_dmg, double, speed_bonus, wall
def fresh_stats():
    return {
        "dmg_mult": 1.0, "crit": 0.05, "crit_mult": 2.0, "perfect_win": 1.2,
        "max_hp": 100.0, "regen": 0.0, "shield": 0.0, "repair": 0.0,
        "lifesteal": 0.0, "xp_mult": 1.0, "slow": 0.0, "combo_guard": 0.0,
        "turret": 0, "turret_dmg": 0.0, "double": 0.0, "speed_bonus": 0, "wall": 0,
    }

UPGRADES = [
    {"id": "ammo", "icon": "▲", "cat": "ATTACK", "name": "AMMO+",
     "desc": "+15% damage tembakan", "max": 8,
     "apply": lambda s: s.update(dmg_mult=s["dmg_mult"] * 1.15)},
    {"id": "crit", "icon": "✸", "cat": "ATTACK", "name": "CRIT CORE",
     "desc": "+10% peluang crit x2", "max": 5,
     "apply": lambda s: s.update(crit=min(0.6, s["crit"] + 0.10))},
    {"id": "perfect", "icon": "◎", "cat": "ATTACK", "name": "PERFECT LENS",
     "desc": "+0.25s jendela PERFECT", "max": 5,
     "apply": lambda s: s.update(perfect_win=s["perfect_win"] + 0.25)},
    {"id": "double", "icon": "⫽", "cat": "ATTACK", "name": "DOUBLE SHOT",
     "desc": "+12% tembakan ganda", "max": 5,
     "apply": lambda s: s.update(double=min(0.6, s["double"] + 0.12))},
    {"id": "adren", "icon": "≫", "cat": "ATTACK", "name": "ADRENALIN",
     "desc": "+6 bonus kecepatan", "max": 5,
     "apply": lambda s: s.update(speed_bonus=s["speed_bonus"] + 6)},
    {"id": "wall", "icon": "▣", "cat": "DEFENSE", "name": "STEEL WALL",
     "desc": "+25 max HP & heal 25", "max": 8,
     "apply": lambda s: s.update(max_hp=s["max_hp"] + 25, wall=s["wall"] + 1)},
    {"id": "regen", "icon": "+", "cat": "DEFENSE", "name": "REGEN BAY",
     "desc": "+0.8 HP/detik", "max": 5,
     "apply": lambda s: s.update(regen=s["regen"] + 0.8)},
    {"id": "shield", "icon": "⛨", "cat": "DEFENSE", "name": "AEGIS SHIELD",
     "desc": "+12% block serangan", "max": 5,
     "apply": lambda s: s.update(shield=min(0.6, s["shield"] + 0.12))},
    {"id": "repair", "icon": "⚒", "cat": "DEFENSE", "name": "REPAIR BOT",
     "desc": "heal +4 tiap PERFECT", "max": 5,
     "apply": lambda s: s.update(repair=s["repair"] + 4)},
    {"id": "slow", "icon": "◷", "cat": "SPEED", "name": "OVERDRIVE",
     "desc": "musuh 8% lebih lambat", "max": 5,
     "apply": lambda s: s.update(slow=s["slow"] + 0.08)},
    {"id": "guard", "icon": "⎋", "cat": "SPEED", "name": "COMBO GUARD",
     "desc": "30% combo selamat saat miss", "max": 3,
     "apply": lambda s: s.update(combo_guard=min(0.9, s["combo_guard"] + 0.30))},
    {"id": "magnet", "icon": "◉", "cat": "BASE", "name": "XP MAGNET",
     "desc": "+25% XP masuk", "max": 5,
     "apply": lambda s: s.update(xp_mult=s["xp_mult"] * 1.25)},
    {"id": "turret", "icon": "⌖", "cat": "BASE", "name": "AUTO CANNON",
     "desc": "turret tembak otomatis", "max": 5,
     "apply": lambda s: (s.update(turret=s["turret"] + 1), s.update(turret_dmg=s["turret_dmg"] + 14))},
    {"id": "vamp", "icon": "♥", "cat": "BASE", "name": "GOLDEN FINGERS",
     "desc": "+1 HP tiap pukulan kena", "max": 5,
     "apply": lambda s: s.update(lifesteal=s["lifesteal"] + 1.0)},
]

def roll_upgrade_choices(owned, k=3):
    avail = [u for u in UPGRADES if owned.get(u["id"], 0) < u["max"]]
    random.shuffle(avail)
    return avail[:k]

# ---------- waifu operator (ASCII, bisa diganti via waifu.txt) ----------
WAIFU_DEFAULT = [
    "     ✿   ♡   ✿     ",
    "      .-\"\"\"-.      ",
    "     / .--. \\     ",
    "    | (o)(o) |    ",
    "     \\  __  /     ",
    "     _| || |_     ",
    "    / | || | \\    ",
    "   |  | || |  |   ",
    "   |  \\_||_/  |   ",
    "    \\   __   /    ",
    "     |______|     ",
    "    _|      |_    ",
]
WAIFU_FACE = {"idle": "(・‿・)", "happy": "(≧▽≦)", "sad": "(>_<)", "hurt": "(T_T)", "excited": "(☆▽☆)"}
WAIFU_LINES = {
    "happy": ["sugoi! kena!", "nice shot, senpai!", "combo naik!"],
    "sad": ["baka... miss!", "fokus, senpai!", "combo reset..."],
    "hurt": ["itai! lindungi aku!", "benteng kita!", "kyaa!"],
    "excited": ["level up! makin kuat!", "power naik!", "yosha!"],
}
WAIFU_TIPS = [
    "ketik cepat = damage",
    "PERFECT < jendela emas",
    "combo = crit ganda",
    "F2 quality • F3 suara",
    "combo guard selamatkanmu",
]

def load_waifu_art():
    """Custom art: Textack/waifu.txt atau ~/.config/textack/waifu.txt (baris # = komen)."""
    cands = [Path(__file__).resolve().parent / "waifu.txt",
             Path.home() / ".config" / "textack" / "waifu.txt"]
    for p in cands:
        try:
            if p.exists():
                lines = [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
                         if not ln.startswith("#")]
                lines = [ln for ln in lines if ln.strip()]
                if lines:
                    return [ln[:34] for ln in lines[:18]]
        except Exception:
            pass
    return WAIFU_DEFAULT

# ---------- suara (wav via paplay/aplay/mpv, fallback beep) ----------
def sfx_detect_player():
    import shutil
    for b in ("paplay", "aplay", "play"):
        if shutil.which(b):
            return [b]
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet"]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    return []

def sfx_init():
    base = Path(__file__).resolve().parent / "sfx"
    return {"dir": base, "bin": sfx_detect_player(), "on": True}

def sfx_play(stdscr, sfx, name):
    """Non-blocking, dijamin tidak nge-lag game. Gagal = diam/beep."""
    if not sfx["on"]:
        return
    try:
        import subprocess
        f = sfx["dir"] / f"{name}.wav"
        if sfx["bin"] and f.exists():
            subprocess.Popen([*sfx["bin"], str(f)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True)
            return
        if name in ("miss", "hurt", "gameover"):
            try:
                curses.beep()
            except Exception:
                pass
    except Exception:
        pass

LOGO_SMALL = [
    "▀█▀ █▀▀ ▀▄▀ ▀█▀ ▄▀█ █▀▀ █▄▀",
    " █  ██▄ █ █  █  █▀█ █▄▄ █ █",
]
TAGLINE = "typing = damage  //  siege the fortress"

BEST_FILE = Path.home() / ".cache" / "textack" / "best.txt"

# ---------- util ----------

def pick_word(wave):
    if wave <= 1:
        pool = TIER1
    elif wave == 2:
        pool = TIER1 + TIER2
    else:
        pool = TIER1 + TIER2 + TIER3
    return random.choice(pool)

def load_best():
    try:
        t = BEST_FILE.read_text().strip().split()
        return {"wave": int(t[0]), "wpm": float(t[1])} if len(t) >= 2 else {"wave": 0, "wpm": 0.0}
    except Exception:
        return {"wave": 0, "wpm": 0.0}

def save_best(wave, wpm):
    try:
        BEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        cur = load_best()
        if wave > cur["wave"] or (wave == cur["wave"] and wpm > cur["wpm"]):
            BEST_FILE.write_text(f"{wave} {wpm:.1f}\n")
    except Exception:
        pass

def rank_for(wpm, combo):
    if combo >= 10 or wpm >= 90:
        return "KERNEL PANIC"
    if combo >= 7 or wpm >= 70:
        return "ROOT"
    if combo >= 5 or wpm >= 55:
        return "SYSADMIN"
    if combo >= 3 or wpm >= 40:
        return "POWER USER"
    if wpm >= 25:
        return "SCRIPT KIDDIE"
    return "NEWBIE"

# ---------- mode hemat CPU (auto quality, low-end friendly) ----------
# level 0=HIGH 60fps, 1=MED 40fps, 2=LOW 30fps. Render sama bagusnya,
# bedanya density partikel/bintang. Animasi tetap dt-based jadi mulus.
QLEVELS = [
    {"name": "HIGH", "fps": 60, "maxp": 180, "stars_div": 45, "boom": 1.0},
    {"name": "MED", "fps": 40, "maxp": 120, "stars_div": 70, "boom": 0.7},
    {"name": "LOW", "fps": 30, "maxp": 70, "stars_div": 110, "boom": 0.45},
]
def quality_from_env():
    a = sys.argv[1:] + [os.environ.get("TEXTACK_Q", "")]
    if "--low" in a or "low" in a:
        return 2
    if "--med" in a or "med" in a:
        return 1
    if "--high" in a or "high" in a:
        return 0
    return 1  # default MED: aman di low-end, tetap mulus

def safe_add(stdscr, y, x, s, attr=0):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or not s:
        return
    if x >= w or x + len(s) <= 0:
        return
    if x < 0:
        s = s[-x:]
        x = 0
    if x + len(s) >= w:
        s = s[: w - x - 1]
        if not s:
            return
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass

def hp_bar_str(cur, disp, total, width):
    total = max(1, total)
    pa = max(0, min(1, cur / total))
    pd = max(0, min(1, disp / total))
    fa = int(width * pa)
    fd = int(width * pd)
    # optimasi: build via list, bukan += per char
    out = ["#"] * fa + ["="] * max(0, fd - fa) + ["-"] * max(0, width - max(fa, fd))
    return f"[{''.join(out)}] {int(cur)}/{total}"

def init_palette():
    """Palet modern Tokyonight-ish. Fallback 8 warna kalau terminal jadul."""
    P = {}
    try:
        curses.start_color()
        curses.use_default_colors()
    except curses.error:
        pass
    colors = getattr(curses, "COLORS", 8) or 8
    try:
        if colors >= 256:
            # pair id 10+ biar tidak tabrakan
            def mk(i, fg):
                try:
                    curses.init_pair(i, fg, -1)
                except curses.error:
                    pass
            mk(10, 189)  # fg lavender-white
            mk(11, 75)   # cyan 7dcfff
            mk(12, 141)  # magenta bb9af7
            mk(13, 150)  # green 9ece6a
            mk(14, 221)  # yellow e0af68
            mk(15, 204)  # red f7768e
            mk(16, 240)  # dim gray
            mk(17, 81)   # cyan terang
            try:
                P["fg"] = curses.color_pair(10)
                P["cyan"] = curses.color_pair(11) | curses.A_BOLD
                P["magenta"] = curses.color_pair(12) | curses.A_BOLD
                P["green"] = curses.color_pair(13) | curses.A_BOLD
                P["yellow"] = curses.color_pair(14) | curses.A_BOLD
                P["red"] = curses.color_pair(15) | curses.A_BOLD
                P["dim"] = curses.color_pair(16) | curses.A_DIM
                P["cyan_dim"] = curses.color_pair(11) | curses.A_DIM
                P["flash"] = curses.color_pair(10) | curses.A_REVERSE
            except curses.error:
                pass
        else:
            raise ValueError("basic")
    except Exception:
        pass
    if not P:
        try:
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_CYAN, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        except curses.error:
            pass
        P = {
            "fg": curses.A_NORMAL, "cyan": curses.color_pair(4) | curses.A_BOLD,
            "magenta": curses.color_pair(5) | curses.A_BOLD,
            "green": curses.color_pair(1) | curses.A_BOLD,
            "yellow": curses.color_pair(3) | curses.A_BOLD,
            "red": curses.color_pair(2) | curses.A_BOLD,
            "dim": curses.A_DIM, "cyan_dim": curses.color_pair(4) | curses.A_DIM,
            "flash": curses.A_REVERSE,
        }
    return P

# ---------- opening ala agent TUI ----------

def show_opening(stdscr, P):
    """Boot cinematic + menu. Return 'play' / 'howto' / 'quit'. 60fps, skip dengan tombol."""
    h, w = stdscr.getmaxyx()
    cx = w // 2
    best = load_best()
    t0 = time.monotonic()
    boot_dur = 2.2
    logs = [
        "$ textack --boot --native",
        "✔ kernel link ok",
        "✔ fortress loaded",
        "✔ keymap id-qwerty ready",
        "✔ 60fps renderer ready",
    ]
    menu = ["▶  Siege Benteng  (Enter)", "Cara main  (H)", "Keluar  (Q)"]
    sel = 0
    sel_y = 0.0
    phase = "boot"  # boot -> menu
    last = time.monotonic()

    # bintang ringan untuk opening (max 40, adaptif)
    nstar = min(40, max(10, (w * h) // 80))
    stars = [{"x": random.random() * w, "y": random.random() * h, "sp": random.uniform(3, 12)} for _ in range(nstar)]

    stdscr.nodelay(True)
    stdscr.timeout(33)

    while True:
        now = time.monotonic()
        dt = min(0.05, now - last)
        last = now
        h, w = stdscr.getmaxyx()
        cx = w // 2
        t = now - t0

        # input
        key = stdscr.getch()
        while key != -1:
            if phase == "boot":
                # tombol apapun -> skip ke menu
                phase = "menu"
                break
            else:
                if key in (curses.KEY_UP, ord("k")):
                    sel = (sel - 1) % len(menu)
                elif key in (curses.KEY_DOWN, ord("j")):
                    sel = (sel + 1) % len(menu)
                elif key in (10, 13):  # enter
                    return ["play", "howto", "quit"][sel]
                elif key in (ord("h"), ord("H")):
                    return "howto"
                elif key in (ord("q"), ord("Q"), 27):
                    return "quit"
            key = stdscr.getch()

        if phase == "boot" and t >= boot_dur:
            phase = "menu"

        # update bintang + seleksi halus (lerp)
        for s in stars:
            s["x"] -= s["sp"] * dt
            if s["x"] < 0:
                s["x"] += w
                s["y"] = random.random() * h
        sel_y += (sel - sel_y) * min(1, dt * 12)

        stdscr.erase()
        # top bar ala agent
        safe_add(stdscr, 0, 2, "● TEXTACK v" + VERSION, P["green"])
        safe_add(stdscr, 0, max(0, w - 26), "linux native • 60fps", P["dim"])
        safe_add(stdscr, 1, 0, "─" * max(0, w - 1), P["dim"])

        for s in stars:
            safe_add(stdscr, int(s["y"]), int(s["x"]), ".", P["cyan_dim"])

        if phase == "boot":
            prog = min(1.0, t / boot_dur)
            # logo shimmer: reveal per huruf halus
            ly = h // 2 - 4
            reveal = int(len(LOGO_SMALL[0]) * min(1, t / 1.4))
            grad = [P["cyan"], P["magenta"], P["green"], P["yellow"]]
            for r, line in enumerate(LOGO_SMALL):
                vis = line[:reveal]
                safe_add(stdscr, ly + r, cx - len(line) // 2, vis, grad[r % len(grad)])
            safe_add(stdscr, ly + 2, cx - len(TAGLINE) // 2, TAGLINE[: int(len(TAGLINE) * min(1, t / 1.8))], P["dim"])
            # logs ketik cepat
            by = ly + 4
            nlogs = min(len(logs), int(t / 0.3) + 1)
            for i in range(nlogs):
                safe_add(stdscr, by + i, cx - 16, logs[i][: w - 4], P["fg"] if i == 0 else P["dim"])
            # progress bar halus
            bw = min(40, w - 10)
            fill = int(bw * prog)
            # pulse di ujung bar
            pulse = "━" if (now * 6) % 1 < 0.5 else "─"
            safe_add(stdscr, by + nlogs + 1, cx - bw // 2, "[" + "━" * fill + pulse + " " * max(0, bw - fill - 1) + f"] {int(prog*100)}%", P["cyan"])
            safe_add(stdscr, h - 2, cx - 14, "tekan tombol untuk skip…", P["dim"])
        else:
            ly = h // 2 - 7
            grad = [P["cyan"], P["magenta"], P["green"], P["yellow"]]
            for r, line in enumerate(LOGO_SMALL):
                # glow halus: brightness osilasi sin
                glow = curses.A_BOLD if (now * 2 + r) % 2 < 1.2 else 0
                # gradien per kolom biar hidup
                x0 = cx - len(line) // 2
                for ci, ch in enumerate(line):
                    if ch == " ":
                        continue
                    a = grad[(ci // 6 + r) % len(grad)] | glow
                    safe_add(stdscr, ly + r, x0 + ci, ch, a)
            safe_add(stdscr, ly + 2, cx - len(TAGLINE) // 2, TAGLINE, P["dim"])
            # best + rank (bikin nagih)
            if best["wave"] > 0:
                safe_add(stdscr, ly + 4, cx - 20, f"BEST wave {best['wave']} • {best['wpm']:.0f} WPM • {rank_for(best['wpm'], 5)}", P["yellow"])
            else:
                safe_add(stdscr, ly + 4, cx - 20, "belum ada rekor — jadilah legenda pertama", P["dim"])
            # menu dengan highlight geser halus
            my = ly + 6
            for i, item in enumerate(menu):
                y = my + i * 2
                x = cx - 16
                if abs(sel_y - i) < 0.6:
                    # bar seleksi
                    safe_add(stdscr, y, x - 2, "━" * 34, P["cyan_dim"])
                    safe_add(stdscr, y, x, item, P["cyan"] | curses.A_REVERSE if "COLOR" else P["cyan"])
                else:
                    safe_add(stdscr, y, x, "  " + item.replace("▶  ", ""), P["dim"] if i != sel else P["fg"])
            # selector panah halus (interpolasi posisi)
            safe_add(stdscr, int(my + sel_y * 2), cx - 19, "▶", P["green"])
            # footer adiktif
            pulse_on = (now * 2.2) % 1 < 0.65
            hint = "ENTER mulai  •  ↑↓ pilih  •  combo = crit" if pulse_on else "1 kata lagi…  combo sayang berhenti"
            safe_add(stdscr, h - 3, cx - len(hint) // 2, hint, P["magenta"])
            safe_add(stdscr, h - 2, 2, "GPL-3.0 • stdlib only • :q keluar kapan saja", P["dim"])

        stdscr.refresh()

def show_howto(stdscr, P):
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

# ---------- upgrade overlay (pilih 1 dari 3, Survivor-style) ----------
def show_upgrade_overlay(stdscr, P, choices, level, owned):
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
            lv = owned.get(u["id"], 0)
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
            cat_col = {"ATTACK": P["red"], "DEFENSE": P["green"], "SPEED": P["cyan"], "BASE": P["magenta"]}.get(u["cat"], P["fg"])
            safe_add(stdscr, by + 1, bx + 2, f"{u['icon']} [{u['cat']}]", cat_col)
            safe_add(stdscr, by + 2, bx + 2, f"{i+1}. {u['name']}"[: cw - 4], P["cyan"] | curses.A_BOLD if is_sel else P["fg"])
            safe_add(stdscr, by + 3, bx + 2, u["desc"][: cw - 4], fill_attr)
            safe_add(stdscr, by + 4, bx + 2, f"Lv {lv} → {lv+1}/{u['max']}", P["yellow"] if is_sel else P["dim"])
            if wide:
                safe_add(stdscr, by + 5, bx + 2, "ENTER untuk ambil", P["dim"])
        stdscr.refresh()
        time.sleep(0.033)

# ---------- siege (gameplay) ----------

def siege(stdscr, P):
    stdscr.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    # quality: default MED (aman low-end). F2 = ganti manual, auto-turun kalau berat.
    qi = quality_from_env()
    frame_ms = max(1, int(1000 / QLEVELS[qi]["fps"]))
    stdscr.timeout(frame_ms)
    ema_dt = 1.0 / QLEVELS[qi]["fps"]
    qcheck_t = 0.0
    fps_show = float(QLEVELS[qi]["fps"])

    wave = 1
    stats = fresh_stats()
    owned = {}
    base_lv = 0
    ecfg = enemy_config(1)
    enemy_max = float(ecfg["hp"])
    player_max = float(stats["max_hp"])
    enemy_hp = float(enemy_max)
    player_hp = float(player_max)
    disp_e = float(enemy_max)
    disp_p = float(player_max)

    target = pick_word(wave)
    buf = ""
    word_start = time.monotonic()
    combo = 0
    best_combo = 0
    shots = hits = 0
    correct_chars_total = 0
    time_total = 0.0
    # XP / level Survivor-style
    xp = 0.0
    xp_next = 30.0
    level = 1
    pending_lv = 0
    turret_t = 0.0
    banner = ""
    banner_t = 0.0
    last_flash_on = False
    # suara + waifu operator
    sfx = sfx_init()
    sfx["on"] = os.environ.get("TEXTACK_SFX", "on").lower() not in ("0", "off", "no")
    waifu_art = load_waifu_art()
    wmood = "idle"
    wmood_t = 0.0
    wline = 0

    def set_mood(m, dur):
        nonlocal wmood, wmood_t, wline
        wmood = m
        wmood_t = dur
        wline = random.randrange(99)

    MAXP = QLEVELS[qi]["maxp"]
    projectiles = []
    particles = []
    floaters = []
    stars = []
    shake_t = 0.0
    shake_mag = 0
    enemy_timer = 0.0
    msg = "Ketik + Enter untuk menembak! :q keluar (F2 quality • F3 suara)"
    msg_t = 3.0
    flash = 0.0
    last = time.monotonic()

    def set_quality(nqi):
        nonlocal qi, MAXP, frame_ms, stars
        qi = max(0, min(2, nqi))
        MAXP = QLEVELS[qi]["maxp"]
        frame_ms = max(1, int(1000 / QLEVELS[qi]["fps"]))
        stdscr.timeout(frame_ms)
        # pangkas bintang & partikel ke budget baru (langsung ringan)
        hq, wq = stdscr.getmaxyx()
        want = min(60, max(8, (wq * hq) // QLEVELS[qi]["stars_div"]))
        if len(stars) > want:
            del stars[want:]
        if len(particles) > MAXP:
            del particles[0: len(particles) - MAXP]

    def interval_eff():
        return max(2.4, ecfg["interval"] * (1.0 + stats["slow"]))

    def new_wave(w):
        nonlocal enemy_max, enemy_hp, disp_e, target, buf, word_start, enemy_timer, ecfg, banner, banner_t
        ecfg = enemy_config(w)
        enemy_max = float(ecfg["hp"])
        enemy_hp = float(enemy_max)
        disp_e = float(enemy_max)
        target = pick_word(w)
        buf = ""
        word_start = time.monotonic()
        enemy_timer = 0.0
        banner = f"WAVE {w} — {ecfg['name']}"
        banner_t = 1.6

    def add_particle(p):
        if len(particles) >= MAXP:
            # buang paling tua biar fps stabil (optimasi mantap)
            del particles[0: len(particles) - MAXP + 1]
        particles.append(p)

    def spawn_explosion(x, y, color, n=22):
        n = max(3, min(40, int(n * QLEVELS[qi]["boom"])))
        for _ in range(n):
            add_particle({
                "x": x, "y": float(y),
                "vx": random.uniform(-18, 18),
                "vy": random.uniform(-10, 10),
                "life": random.uniform(0.3, 0.8), "max": 0.8,
                "char": random.choice(["*", ".", "+", "o", "#"]),
                "attr": color,
            })

    new_wave(1)
    # bintang adaptif layar + quality (animasi murah, 1 addstr per bintang)
    h0, w0 = stdscr.getmaxyx()
    stars = [{"x": random.random() * max(1, w0), "y": random.random() * max(1, h0),
              "sp": random.uniform(2, 10)} for _ in range(min(60, max(8, (w0 * h0) // QLEVELS[qi]["stars_div"])))]

    while True:
        now = time.monotonic()
        dt = min(0.05, now - last)
        last = now
        h, w = stdscr.getmaxyx()
        cx = w // 2
        # auto quality: EMA frame time, cek tiap 2 detik (hemat CPU di low-end)
        ema_dt = ema_dt * 0.95 + dt * 0.05
        fps_show = fps_show * 0.95 + (1.0 / max(dt, 1e-3)) * 0.05
        qcheck_t += dt
        if qcheck_t >= 2.0:
            qcheck_t = 0.0
            if ema_dt > 1.0 / (QLEVELS[qi]["fps"] * 0.75) and qi < 2:
                set_quality(qi + 1)
                msg = f"Mode hemat aktif ({QLEVELS[qi]['name']}) biar mulus di device ini"
                msg_t = 2.0
            elif ema_dt < 1.0 / (QLEVELS[qi]["fps"] * 1.6) and qi > 0 and qi == 2:
                pass  # tetap LOW kalau user/device low-end, tidak naik otomatis

        key = stdscr.getch()
        while key != -1:
            if key == 27:
                return
            elif key == curses.KEY_F2:
                # F2 = putar quality manual (tidak ganggu ketikan, F-key > 255)
                set_quality((qi + 1) % 3)
                msg = f"Quality: {QLEVELS[qi]['name']} {QLEVELS[qi]['fps']}fps (F2 ganti)"
                msg_t = 2.0
            elif key == curses.KEY_F3:
                sfx["on"] = not sfx["on"]
                msg = f"Suara: {'ON' if sfx['on'] else 'OFF'} (F3 ganti)"
                msg_t = 2.0
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                buf = buf[:-1]
            elif key in (curses.KEY_ENTER, 10, 13):
                elapsed = max(0.05, now - word_start)
                if buf.strip() == ":q":
                    return
                shots += 1
                time_total += elapsed
                if buf == target:
                    wpm = (len(target) / 5) / (elapsed / 60)
                    base = len(target) * 3
                    perfect = elapsed < stats["perfect_win"]
                    speed_bonus = max(0, int(25 - elapsed * 4)) + int(stats["speed_bonus"]) + (15 if perfect else 0)
                    combo += 1
                    best_combo = max(best_combo, combo)
                    mult = (1 + min(combo, 10) * 0.1) * stats["dmg_mult"]
                    dmg = int((base + speed_bonus) * mult)
                    # crit + double (animasi fresh: label beda)
                    is_crit = random.random() < stats["crit"]
                    is_double = random.random() < stats["double"]
                    if is_crit:
                        dmg = int(dmg * stats["crit_mult"])
                    if is_double:
                        dmg = int(dmg * 2)
                    tag = ""
                    if perfect:
                        tag += " PERFECT"
                    if is_crit:
                        tag += " CRIT"
                    if is_double:
                        tag += " x2"
                    hits += 1
                    correct_chars_total += len(target)
                    projectiles.append({"x": cx, "y": h - 8.0, "vy": -34.0,
                                        "char": "▲", "attr": P["green"],
                                        "pending": float(dmg), "side": "player",
                                        "label": f"-{dmg}{tag} {wpm:.0f}wpm"})
                    # muzzle flash murah: 4 partikel pendek di moncong base
                    for _ in range(4):
                        add_particle({"x": cx + random.uniform(-1.5, 1.5), "y": float(h - 8),
                                              "vx": random.uniform(-6, 6), "vy": random.uniform(-14, -4),
                                              "life": 0.22, "max": 0.22,
                                              "char": random.choice(["*", "+", "."]), "attr": P["yellow"]})
                    msg = f"KENA -{dmg}{tag} | {elapsed:.2f}s | {wpm:.0f} WPM | combo {combo}"
                    msg_t = 1.6
                    enemy_timer = 0.0
                    sfx_play(stdscr, sfx, "shoot")
                    set_mood("happy", 1.4)
                    # lifesteal + repair on perfect (base sustain)
                    if stats["lifesteal"] > 0:
                        player_hp = min(stats["max_hp"], player_hp + stats["lifesteal"])
                    if perfect and stats["repair"] > 0:
                        player_hp = min(stats["max_hp"], player_hp + stats["repair"])
                    # XP Survivor-style
                    boss_mult = 2.0 if wave % 5 == 0 else 1.0
                    xp += (len(target) * 2 + wave * 2) * stats["xp_mult"] * boss_mult
                    avg = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
                    save_best(wave, avg)
                else:
                    # combo guard: peluang combo selamat
                    if random.random() < stats["combo_guard"]:
                        msg = f"Hampir! combo x{combo} selamat (GUARD)"
                        combo = max(combo, combo)  # tahan
                    else:
                        combo = 0
                        msg = f"Meleset! '{buf}' != '{target}' — combo reset!"
                    counter = ecfg["dmg"] + wave + random.randint(0, 4)
                    projectiles.append({"x": cx + random.randint(-6, 6), "y": 8.0, "vy": 26.0,
                                        "char": ecfg["proj"], "attr": P[ecfg["col"]],
                                        "pending": float(counter), "side": "enemy",
                                        "label": f"-{counter}"})
                    msg_t = 1.6
                    shake_t = 0.35
                    shake_mag = 2
                    sfx_play(stdscr, sfx, "miss")
                    set_mood("sad", 1.4)
                target = pick_word(wave)
                buf = ""
                word_start = now
            elif 32 <= key <= 126:
                if len(buf) < 60:
                    buf += chr(key)
            key = stdscr.getch()

        elapsed_word = now - word_start
        # regen base tiap detik (Survivor sustain)
        if stats["regen"] > 0 and player_hp > 0:
            player_hp = min(stats["max_hp"], player_hp + stats["regen"] * dt)
        enemy_timer += dt
        if enemy_timer >= interval_eff():
            enemy_timer = 0.0
            # burst sesuai wave: makin tinggi wave makin banyak proyektil
            for b in range(ecfg["burst"]):
                chip = ecfg["dmg"] + random.randint(0, 3)
                projectiles.append({"x": cx + random.randint(-8, 8) + b * 2, "y": 8.0 - b * 1.2, "vy": 24.0,
                                    "char": ecfg["proj"], "attr": P[ecfg["col"]],
                                    "pending": float(chip), "side": "enemy", "label": f"-{chip}"})
            msg = f"{ecfg['name']} menyerang x{ecfg['burst']}! Cepat ketik!"
            msg_t = 1.2
        # auto cannon base (DPS pasif ala Survivor.io)
        if stats["turret"] > 0 and enemy_hp > 0:
            turret_t += dt
            t_interval = max(3.0, 8.0 - 0.6 * stats["turret"])
            if turret_t >= t_interval:
                turret_t = 0.0
                tdmg = stats["turret_dmg"] + wave * 2
                projectiles.append({"x": cx + 10, "y": h - 8.0, "vy": -30.0,
                                    "char": "⌖", "attr": P["magenta"],
                                    "pending": float(tdmg), "side": "player",
                                    "label": f"turret -{int(tdmg)}"})
                sfx_play(stdscr, sfx, "turret")

        if msg_t > 0:
            msg_t -= dt
        if shake_t > 0:
            shake_t -= dt
        if flash > 0:
            flash -= dt
        if banner_t > 0:
            banner_t -= dt
        if wmood_t > 0:
            wmood_t -= dt
            if wmood_t <= 0:
                wmood = "idle"

        disp_e += (enemy_hp - disp_e) * min(1, dt * 6)
        disp_p += (player_hp - disp_p) * min(1, dt * 6)
        if abs(enemy_hp - disp_e) < 0.05:
            disp_e = enemy_hp
        if abs(player_hp - disp_p) < 0.05:
            disp_p = player_hp

        for s in stars:
            s["x"] -= s["sp"] * dt
            if s["x"] < 0:
                s["x"] += w
                s["y"] = random.random() * h

        for p in projectiles:
            p["y"] += p["vy"] * dt
        arrived, keep = [], []
        for p in projectiles:
            if p["side"] == "player" and p["y"] <= 8.5:
                arrived.append(p)
            elif p["side"] == "enemy" and p["y"] >= h - 8.5:
                arrived.append(p)
            else:
                keep.append(p)
        projectiles = keep
        for p in arrived:
            if p["side"] == "player":
                enemy_hp -= p["pending"]
                spawn_explosion(p["x"], 8, P["green"])
                floaters.append({"x": p["x"] + 2, "y": 9.0, "text": p.get("label", ""),
                                 "life": 1.0, "max": 1.0, "attr": P["green"]})
                shake_t = 0.18
                shake_mag = 1
                flash = 0.07
                sfx_play(stdscr, sfx, "hit")
            else:
                # shield: peluang block penuh
                if random.random() < stats["shield"]:
                    spawn_explosion(p["x"], h - 8, P["cyan"], n=10)
                    floaters.append({"x": p["x"] + 1, "y": h - 10.0, "text": "BLOCK",
                                     "life": 1.0, "max": 1.0, "attr": P["cyan"]})
                    sfx_play(stdscr, sfx, "block")
                    set_mood("happy", 1.0)
                else:
                    player_hp -= p["pending"]
                    spawn_explosion(p["x"], h - 8, P["red"], n=14)
                    floaters.append({"x": p["x"] + 1, "y": h - 10.0, "text": p.get("label", ""),
                                     "life": 1.0, "max": 1.0, "attr": P["red"]})
                    shake_t = 0.3
                    shake_mag = 2
                    sfx_play(stdscr, sfx, "hurt")
                    set_mood("hurt", 1.2)

        for pt in particles:
            pt["life"] -= dt
            pt["x"] += pt["vx"] * dt
            pt["y"] += pt["vy"] * dt
            pt["vy"] += 22 * dt
        if len(particles) > MAXP:
            del particles[0: len(particles) - MAXP]
        else:
            particles = [p for p in particles if p["life"] > 0]
        for f in floaters:
            f["life"] -= dt
            f["y"] -= 3.5 * dt
        floaters = [f for f in floaters if f["life"] > 0]

        # sync max HP dari upgrade wall
        player_max = float(stats["max_hp"])
        if disp_p > player_max + 1:
            disp_p = player_max

        # LEVEL UP -> overlay upgrade Survivor-style (bisa beruntun)
        while xp >= xp_next:
            xp -= xp_next
            level += 1
            xp_next = xp_next * 1.45 + 10
            pending_lv += 1
        while pending_lv > 0:
            pending_lv -= 1
            choices = roll_upgrade_choices(owned, k=3)
            if not choices:
                break
            # ledakan fresh sebelum pilih
            spawn_explosion(cx, h // 2, P["yellow"], n=30)
            floaters.append({"x": cx - 4, "y": h // 2 - 1.0, "text": f"LEVEL {level}!",
                             "life": 1.2, "max": 1.2, "attr": P["yellow"]})
            # render satu frame biar ledakan kelihatan sebelum overlay
            stdscr.refresh()
            pick = show_upgrade_overlay(stdscr, P, choices, level, owned)
            u = choices[pick]
            u["apply"](stats)
            owned[u["id"]] = owned.get(u["id"], 0) + 1
            base_lv += 1
            sfx_play(stdscr, sfx, "select")
            set_mood("excited", 2.2)
            if u["id"] == "wall":
                player_hp = min(stats["max_hp"], player_hp + 25)
            player_max = float(stats["max_hp"])
            spawn_explosion(cx, h - 8, P["green"], n=30)
            floaters.append({"x": cx - 6, "y": h - 10.0, "text": f"+ {u['name']}",
                             "life": 1.4, "max": 1.4, "attr": P["green"]})
            msg = f"UPGRADE: {u['name']} — {u['desc']}"
            msg_t = 2.2
            # reset timer input biar adil setelah milih
            word_start = time.monotonic()
            last = time.monotonic()

        if enemy_hp <= 0:
            acc = (hits / shots * 100) if shots else 100
            avg_wpm = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
            save_best(wave, avg_wpm)
            spawn_explosion(cx, 8, P["yellow"], n=40)
            sfx_play(stdscr, sfx, "waveclear")
            set_mood("excited", 2.5)
            t0 = time.monotonic()
            while time.monotonic() - t0 < 1.8:
                h2, w2 = stdscr.getmaxyx()
                stdscr.erase()
                for pt in particles:
                    pt["life"] -= 0.016
                    pt["x"] += pt["vx"] * 0.016
                    pt["y"] += pt["vy"] * 0.016
                particles = [p for p in particles if p["life"] > 0]
                for pt in particles:
                    safe_add(stdscr, int(pt["y"]), int(pt["x"]), pt["char"], pt["attr"])
                safe_add(stdscr, h2 // 2 - 1, w2 // 2 - 14, f"WAVE {wave} HANCUR!", P["yellow"])
                safe_add(stdscr, h2 // 2, w2 // 2 - 20, f"{acc:.0f}% | {avg_wpm:.0f} WPM | combo max {best_combo} | Enter lanjut", P["cyan"])
                stdscr.refresh()
                time.sleep(0.033)
            stdscr.nodelay(False)
            stdscr.timeout(-1)
            stdscr.getch()
            stdscr.nodelay(True)
            stdscr.timeout(frame_ms)
            wave += 1
            player_max = float(stats["max_hp"])
            player_hp = float(player_max)
            disp_p = float(player_max)
            new_wave(wave)
            msg = f"WAVE {wave} {ecfg['name']} — {rank_for(avg_wpm, best_combo)} mode ON!"
            msg_t = 2.5
            best_combo = 0
            last = time.monotonic()
            continue

        if player_hp <= 0:
            stdscr.nodelay(False)
            stdscr.erase()
            acc = (hits / shots * 100) if shots else 100
            avg_wpm = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
            save_best(wave, avg_wpm)
            rk = rank_for(avg_wpm, best_combo)
            sfx_play(stdscr, sfx, "gameover")
            safe_add(stdscr, h // 2 - 2, cx - 12, "BENTENGMU HANCUR", P["red"])
            safe_add(stdscr, h // 2 - 1, cx - 24, f"wave {wave} | {hits}/{shots} | {acc:.0f}% | {avg_wpm:.0f} WPM | {rk}", P["fg"])
            safe_add(stdscr, h // 2 + 1, cx - 16, "Enter coba lagi, q keluar", P["dim"])
            safe_add(stdscr, h // 2 + 2, cx - 20, "sedikit lagi… 1 wave lagi pasti bisa", P["magenta"])
            stdscr.refresh()
            stdscr.timeout(-1)
            k = stdscr.getch()
            if k == -1 or (k != 10 and k != 13 and chr(k).lower() != "y" and k != ord(" ")):
                # q / esc / apapun selain enter = tanya sekali lagi secara simpel: q keluar
                try:
                    if chr(k).lower() == "q":
                        return
                except Exception:
                    pass
                # Enter / space = retry
                if k not in (10, 13, ord(" ")):
                    return
            wave = 1
            stats = fresh_stats()
            owned = {}
            base_lv = 0
            level = 1
            xp = 0.0
            xp_next = 30.0
            pending_lv = 0
            turret_t = 0.0
            enemy_timer = 0.0
            shots = hits = 0
            correct_chars_total = 0
            time_total = 0.0
            combo = 0
            best_combo = 0
            player_max = float(stats["max_hp"])
            player_hp = float(player_max)
            disp_p = float(player_max)
            projectiles.clear()
            particles.clear()
            floaters.clear()
            new_wave(1)
            stdscr.nodelay(True)
            stdscr.timeout(frame_ms)
            last = time.monotonic()
            continue

        # render (ringan: bkgd hanya saat status flash berubah, shake hanya saat goyang)
        stdscr.erase()
        flash_on = flash > 0
        if flash_on != last_flash_on:
            last_flash_on = flash_on
            try:
                stdscr.bkgd(" ", P["flash"] if flash_on else curses.A_NORMAL)
            except curses.error:
                pass

        if shake_t > 0:
            shx = random.randint(-shake_mag, shake_mag)
            shy = random.randint(-1, 1)
        else:
            shx = 0
            shy = 0

        for s in stars:
            safe_add(stdscr, int(s["y"]) % max(1, h), int(s["x"]) % max(1, w), ".", P["cyan_dim"])

        avg_live = (correct_chars_total / 5) / (time_total / 60) if time_total > 0.5 else 0
        rk_live = rank_for(avg_live, combo)
        # ── ZONA ATAS: musuh (terpisah jelas dari status player) ──
        safe_add(stdscr, 0, 2, f"TEXTACK v{VERSION}  W{wave} COMBO x{combo} {rk_live}", P["fg"])
        safe_add(stdscr, 1, 2, f"▼ {ecfg['name']} {hp_bar_str(enemy_hp, disp_e, enemy_max, min(34, w-30))}", P["red"])
        # combo meter + quality/sfx mungil (1 addstr digabung biar hemat)
        cw = min(16, w - 10)
        cfill = int(cw * min(1, combo / 10))
        sfx_s = "♪" if sfx["on"] else "×"
        safe_add(stdscr, 0, max(0, w - cw - 28), f"[{'█'*cfill}{'·'*(cw-cfill)}] {QLEVELS[qi]['name']} {sfx_s}", P["magenta"])

        bob = int((now * 2) % 2)
        ey = 6 + shy + bob
        # telegraph murah: musuh kedip bold saat mau nyerang (>80% timer)
        tele = (enemy_timer / interval_eff()) > 0.8
        ecol = P[ecfg["col"]] | (curses.A_BOLD if tele else 0)
        for i, line in enumerate(ENEMY_ART):
            safe_add(stdscr, ey + i, cx - len(line) // 2 + shx, line, ecol)
        # nama + interval musuh (transparan biar taktik)
        safe_add(stdscr, ey + len(ENEMY_ART) + 1, cx - 14 + shx, f"{ecfg['name']} HP{int(max(0,enemy_hp))} ATK/{interval_eff():.1f}s", ecol)
        # banner wave slide-in (murah: 1-2 addstr, lerp posisi)
        if banner_t > 0:
            bx = int(cx - len(banner) // 2 + (banner_t * 14))
            balpha = P["yellow"] | curses.A_BOLD if (now * 4) % 1 < 0.7 else P["yellow"]
            safe_add(stdscr, ey - 2, max(1, min(bx, w - len(banner) - 1)), banner, balpha)

        ty = ey + len(ENEMY_ART) + 3
        # target 3-segmen (hemat: 3-4 addstr, bukan per-huruf)
        tx = cx - len(target) // 2
        safe_add(stdscr, ty, tx - 2, "> ", P["fg"])
        n_ok = 0
        first_bad = -1
        for i in range(min(len(buf), len(target))):
            if buf[i] == target[i]:
                n_ok += 1
            else:
                first_bad = i
                break
        else:
            if len(buf) >= len(target):
                n_ok = len(target)
        if n_ok > 0:
            safe_add(stdscr, ty, tx, target[:n_ok], P["green"])
        if first_bad >= 0:
            safe_add(stdscr, ty, tx + first_bad, target[first_bad: first_bad + 1], P["red"] | curses.A_BOLD)
            if first_bad + 1 < len(target):
                safe_add(stdscr, ty, tx + first_bad + 1, target[first_bad + 1:], P["fg"])
        else:
            rest = target[n_ok:]
            if rest:
                safe_add(stdscr, ty, tx + n_ok, rest[0], curses.A_REVERSE)
                if len(rest) > 1:
                    safe_add(stdscr, ty, tx + n_ok + 1, rest[1:], P["fg"])
        tfrac = max(0, min(1, elapsed_word / interval_eff()))
        tw = min(30, w - 10)
        tfill = int(tw * (1 - tfrac))
        # timer berubah warna hijau->kuning->merah (feedback adiktif)
        tcol = P["green"] if tfrac < 0.5 else (P["yellow"] if tfrac < 0.8 else P["red"])
        safe_add(stdscr, ty + 1, cx - tw // 2, "[" + "━" * tfill + " " * (tw - tfill) + "]", tcol)

        for p in projectiles:
            safe_add(stdscr, int(p["y"]), int(p["x"]), p["char"], p["attr"])
        for pt in particles:
            a = pt["attr"] | (curses.A_DIM if pt["life"] < pt["max"] * 0.4 else curses.A_BOLD)
            safe_add(stdscr, int(pt["y"]), int(pt["x"]), pt["char"], a)
        for f in floaters:
            alpha = curses.A_BOLD if f["life"] > f["max"] * 0.4 else curses.A_DIM
            safe_add(stdscr, int(f["y"]), int(f["x"]), f["text"], f["attr"] | alpha)

        py = h - 7
        # ── ZONA BAWAH: status player nempel benteng sendiri (terpisah dari musuh) ──
        safe_add(stdscr, py - 2, 2, f"▲ KAMU {hp_bar_str(player_hp, disp_p, player_max, min(34, w-30))}", P["green"])
        xw = min(14, max(6, w - 60))
        xfill = int(xw * min(1, xp / max(1, xp_next)))
        turret_s = f" ⌖{stats['turret']}" if stats["turret"] else ""
        safe_add(stdscr, py - 1, 2, f"LV{level} [{'█'*xfill}{'·'*(xw-xfill)}] BASE{base_lv}{turret_s} DMGx{stats['dmg_mult']:.1f}", P["magenta"])
        # base visual naik level: armor ekstra + cannon kalau punya turret
        base_attr = P["green"] | (curses.A_BOLD if base_lv >= 5 else 0)
        for i, line in enumerate(PLAYER_ART):
            safe_add(stdscr, py + i, cx - len(line) // 2, line, base_attr)
        if stats["wall"] > 0:
            armor = "▣" * min(6, stats["wall"]) + f" Lv{stats['wall']}"
            safe_add(stdscr, py + 4 if py + 4 < h else h - 1, cx - len(armor) // 2, armor, P["cyan"])
        if stats["turret"] > 0:
            blink = "⌖" if (now * 3) % 1 < 0.7 else "◉"
            safe_add(stdscr, py - 1, cx + 12, f"{blink}x{stats['turret']}", P["magenta"])
        # ── panel waifu operator (kanan, hanya layar lebar biar tidak sempit) ──
        if w >= 102 and h >= 24:
            px = w - 36
            safe_add(stdscr, py - 2, px, "◆ AIKA · operator", P["cyan"])
            for i, ln in enumerate(waifu_art):
                safe_add(stdscr, py - 1 + i, px, ln, P["magenta"] if i < 5 else P["fg"])
            wy = py - 1 + len(waifu_art)
            if wy < h - 3:
                face = WAIFU_FACE.get(wmood, "(・‿・)")
                safe_add(stdscr, wy, px, f"AIKA {face}", P["yellow"] | curses.A_BOLD)
                if wmood == "idle":
                    say = WAIFU_TIPS[int(now / 4) % len(WAIFU_TIPS)]
                else:
                    pool = WAIFU_LINES.get(wmood, ["..."])
                    say = pool[wline % len(pool)]
                safe_add(stdscr, wy + 1, px, f"「{say}\"", P["dim"])
        # heartbeat murah: sudut layar kedip saat HP < 30% (4 addstr saja)
        if player_hp < player_max * 0.3 and player_hp > 0:
            hb = P["red"] | curses.A_BOLD if (now * 3) % 1 < 0.5 else P["dim"]
            safe_add(stdscr, 0, 0, "♥", hb)
            safe_add(stdscr, 0, w - 1, "♥", hb)
            safe_add(stdscr, h - 1, 0, "♥", hb)
            safe_add(stdscr, h - 1, w - 1, "♥", hb)

        caret = "█" if (now * 4) % 1 < 0.6 else " "
        prompt = f"> {buf}{caret}"
        safe_add(stdscr, h - 2, max(0, cx - max(len(prompt), len(target)) // 2 - 2), prompt, P["fg"])
        if msg_t > 0:
            safe_add(stdscr, h - 3, 2, msg[: max(0, w - 4)], P["cyan"])
        else:
            live_wpm = (len(buf) / 5) / (elapsed_word / 60) if elapsed_word > 0.2 else 0
            safe_add(stdscr, h - 3, 2, f"{elapsed_word:.1f}s | {live_wpm:.0f} WPM | {combo}x | Enter=tembak", P["dim"])

        stdscr.refresh()

def fade_out(stdscr, dur=0.45):
    """Fade out halus: overlay ░→▒→▓→█ lalu ke hitam. Optimasi: fill per baris."""
    h, w = stdscr.getmaxyx()
    if h < 3 or w < 10:
        stdscr.erase()
        stdscr.refresh()
        return
    steps = ["░", "▒", "▓", "█"]
    per = dur / max(1, len(steps))
    for ch in steps:
        line = (ch * max(0, w - 1))
        for y in range(h):
            try:
                stdscr.addstr(y, 0, line, curses.A_DIM)
            except curses.error:
                pass
        stdscr.refresh()
        time.sleep(per)
    stdscr.erase()
    stdscr.refresh()
    time.sleep(0.08)

def fade_in_blank(stdscr, dur=0.35):
    """Fade in dari hitam: █→▓→▒→░→transparan."""
    h, w = stdscr.getmaxyx()
    if h < 3 or w < 10:
        return
    steps = ["█", "▓", "▒", "░"]
    per = dur / max(1, len(steps))
    for ch in steps:
        line = (ch * max(0, w - 1))
        for y in range(h):
            try:
                stdscr.addstr(y, 0, line, curses.A_DIM)
            except curses.error:
                pass
        stdscr.refresh()
        time.sleep(per)
    stdscr.erase()
    stdscr.refresh()

def show_outro(stdscr, P):
    """Layar selesai: fade out game -> fade in credit -> fade out. Skippable."""
    stdscr.nodelay(True)
    stdscr.timeout(33)
    fade_out(stdscr, dur=0.45)
    fade_in_blank(stdscr, dur=0.3)
    best = load_best()
    t0 = time.monotonic()
    hold = 2.8
    last = t0
    while True:
        now = time.monotonic()
        dt = min(0.05, now - last)
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
    fade_out(stdscr, dur=0.5)

def game_loop(stdscr):
    P = init_palette()
    # WAJIB: terjemahkan tombol panah/F-key jadi KEY_*.
    # Tanpa ini, panah = byte ESC+[+huruf dan byte ESC (=27) memicu keluar game.
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    while True:
        act = show_opening(stdscr, P)
        if act == "quit":
            show_outro(stdscr, P)
            return
        if act == "howto":
            nxt = show_howto(stdscr, P)
            if nxt == "menu":
                continue
        siege(stdscr, P)
        # balik ke menu setelah siege keluar (bikin loop nagih)
        continue

def main():
    if not sys.stdin.isatty():
        print("Jalankan di terminal asli: textack")
        sys.exit(1)
    # optimasi env: hindari delay ESC di curses
    os.environ.setdefault("ESCDELAY", "25")
    try:
        curses.wrapper(game_loop)
    except KeyboardInterrupt:
        pass
    print("made by rewsaqy • 2026")

if __name__ == "__main__":
    main()
