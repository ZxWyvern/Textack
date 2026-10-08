# textack/ui/screens/siege.py
"""Siege loop — verbatim move from main.py:619-1237 siege().

Render/particle/star/shake code pixel-identical; math delegated to core:
enemies.for_wave, words.pick_word, combat.resolve_hit (PRE-increment combo),
combat.combo_step, progression.rank_for/gain_xp/next_threshold,
upgrades.fresh_stats/roll_choices/apply, quality.effective_interval,
infra.storage/sfx/waifu. Upgrade objects use attr access via _get helper
(same pattern as upgrade.py). Game-over path stays in siege (T6 deferred:
no outro after siege); loop.py nagih-loop unchanged.
"""
import curses
import os
import random
import sys
import time

from textack import VERSION
from textack.core import combat, enemies, progression, upgrades, words
from textack.infra import quality
from textack.infra import sfx as sfx_mod
from textack.infra import storage, waifu
from textack.ui import widgets
from textack.ui.screens import upgrade as upgrade_screen

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


def _get(u, k):
    """Ledger ruling: Upgrade object (u.id) or dict (u['id'])."""
    if isinstance(u, dict):
        return u[k]
    return getattr(u, k)


def show(stdscr, P):
    stdscr.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    # quality: default MED (aman low-end). F2 = ganti manual, auto-turun kalau berat.
    qi = quality.from_env(sys.argv[1:], os.environ)
    frame_ms = max(1, int(1000 / quality.QLEVELS[qi]["fps"]))
    stdscr.timeout(frame_ms)
    ema_dt = 1.0 / quality.QLEVELS[qi]["fps"]
    qcheck_t = 0.0
    fps_show = float(quality.QLEVELS[qi]["fps"])

    wave = 1
    stats = upgrades.fresh_stats()
    owned = {}
    base_lv = 0
    ecfg = enemies.for_wave(1)
    enemy_max = float(ecfg.hp)
    player_max = float(stats["max_hp"])
    enemy_hp = float(enemy_max)
    player_hp = float(player_max)
    disp_e = float(enemy_max)
    disp_p = float(player_max)

    target = words.pick_word(wave)
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
    sfx = sfx_mod.init()
    waifu_art = waifu.load_art()
    wmood = "idle"
    wmood_t = 0.0
    wline = 0

    def set_mood(m, dur):
        nonlocal wmood, wmood_t, wline
        wmood = m
        wmood_t = dur
        wline = random.randrange(99)

    MAXP = quality.QLEVELS[qi]["maxp"]
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
        MAXP = quality.QLEVELS[qi]["maxp"]
        frame_ms = max(1, int(1000 / quality.QLEVELS[qi]["fps"]))
        stdscr.timeout(frame_ms)
        # pangkas bintang & partikel ke budget baru (langsung ringan)
        hq, wq = stdscr.getmaxyx()
        want = min(60, max(8, (wq * hq) // quality.QLEVELS[qi]["stars_div"]))
        if len(stars) > want:
            del stars[want:]
        if len(particles) > MAXP:
            del particles[0: len(particles) - MAXP]

    def interval_eff():
        return quality.effective_interval(ecfg.interval, stats["slow"])

    def new_wave(w):
        nonlocal enemy_max, enemy_hp, disp_e, target, buf, word_start, enemy_timer, ecfg, banner, banner_t
        ecfg = enemies.for_wave(w)
        enemy_max = float(ecfg.hp)
        enemy_hp = float(enemy_max)
        disp_e = float(enemy_max)
        target = words.pick_word(w)
        buf = ""
        word_start = time.monotonic()
        enemy_timer = 0.0
        banner = f"WAVE {w} — {ecfg.name}"
        banner_t = 1.6

    def add_particle(p):
        if len(particles) >= MAXP:
            # buang paling tua biar fps stabil (optimasi mantap)
            del particles[0: len(particles) - MAXP + 1]
        particles.append(p)

    def spawn_explosion(x, y, color, n=22):
        n = max(3, min(40, int(n * quality.QLEVELS[qi]["boom"])))
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
              "sp": random.uniform(2, 10)} for _ in range(min(60, max(8, (w0 * h0) // quality.QLEVELS[qi]["stars_div"])))]

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
            if ema_dt > 1.0 / (quality.QLEVELS[qi]["fps"] * 0.75) and qi < 2:
                set_quality(qi + 1)
                msg = f"Mode hemat aktif ({quality.QLEVELS[qi]['name']}) biar mulus di device ini"
                msg_t = 2.0
            elif ema_dt < 1.0 / (quality.QLEVELS[qi]["fps"] * 1.6) and qi > 0 and qi == 2:
                pass  # tetap LOW kalau user/device low-end, tidak naik otomatis

        key = stdscr.getch()
        while key != -1:
            if key == 27:
                return
            elif key == curses.KEY_F2:
                # F2 = putar quality manual (tidak ganggu ketikan, F-key > 255)
                set_quality((qi + 1) % 3)
                msg = f"Quality: {quality.QLEVELS[qi]['name']} {quality.QLEVELS[qi]['fps']}fps (F2 ganti)"
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
                    r = combat.resolve_hit(target, buf, elapsed, combo, stats, wave)
                    combo += 1
                    best_combo = max(best_combo, combo)
                    dmg, tag, wpm = r.dmg, r.tag, r.wpm
                    perfect = r.perfect
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
                    sfx_mod.play(stdscr, sfx, "shoot")
                    set_mood("happy", 1.4)
                    # lifesteal + repair on perfect (base sustain)
                    if stats["lifesteal"] > 0:
                        player_hp = min(stats["max_hp"], player_hp + stats["lifesteal"])
                    if perfect and stats["repair"] > 0:
                        player_hp = min(stats["max_hp"], player_hp + stats["repair"])
                    # XP Survivor-style
                    xp += progression.gain_xp(len(target), wave, stats["xp_mult"], wave % 5 == 0)
                    avg = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
                    storage.save_best(storage.DEFAULT_BEST, wave, avg)
                else:
                    # combo guard: peluang combo selamat
                    kept = combat.combo_step(False, combo, stats["combo_guard"])
                    if combo > 0 and kept == combo:
                        msg = f"Hampir! combo x{combo} selamat (GUARD)"
                        combo = kept  # tahan
                    else:
                        combo = 0
                        msg = f"Meleset! '{buf}' != '{target}' — combo reset!"
                    counter = ecfg.dmg + wave + random.randint(0, 4)
                    projectiles.append({"x": cx + random.randint(-6, 6), "y": 8.0, "vy": 26.0,
                                        "char": ecfg.proj, "attr": P[ecfg.col],
                                        "pending": float(counter), "side": "enemy",
                                        "label": f"-{counter}"})
                    msg_t = 1.6
                    shake_t = 0.35
                    shake_mag = 2
                    sfx_mod.play(stdscr, sfx, "miss")
                    set_mood("sad", 1.4)
                target = words.pick_word(wave)
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
            for b in range(ecfg.burst):
                chip = ecfg.dmg + random.randint(0, 3)
                projectiles.append({"x": cx + random.randint(-8, 8) + b * 2, "y": 8.0 - b * 1.2, "vy": 24.0,
                                    "char": ecfg.proj, "attr": P[ecfg.col],
                                    "pending": float(chip), "side": "enemy", "label": f"-{chip}"})
            msg = f"{ecfg.name} menyerang x{ecfg.burst}! Cepat ketik!"
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
                sfx_mod.play(stdscr, sfx, "turret")

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
                sfx_mod.play(stdscr, sfx, "hit")
            else:
                # shield: peluang block penuh
                if random.random() < stats["shield"]:
                    spawn_explosion(p["x"], h - 8, P["cyan"], n=10)
                    floaters.append({"x": p["x"] + 1, "y": h - 10.0, "text": "BLOCK",
                                     "life": 1.0, "max": 1.0, "attr": P["cyan"]})
                    sfx_mod.play(stdscr, sfx, "block")
                    set_mood("happy", 1.0)
                else:
                    player_hp -= p["pending"]
                    spawn_explosion(p["x"], h - 8, P["red"], n=14)
                    floaters.append({"x": p["x"] + 1, "y": h - 10.0, "text": p.get("label", ""),
                                     "life": 1.0, "max": 1.0, "attr": P["red"]})
                    shake_t = 0.3
                    shake_mag = 2
                    sfx_mod.play(stdscr, sfx, "hurt")
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
            xp_next = progression.next_threshold(xp_next)
            pending_lv += 1
        while pending_lv > 0:
            pending_lv -= 1
            choices = upgrades.roll_choices(owned, k=3)
            if not choices:
                break
            # ledakan fresh sebelum pilih
            spawn_explosion(cx, h // 2, P["yellow"], n=30)
            floaters.append({"x": cx - 4, "y": h // 2 - 1.0, "text": f"LEVEL {level}!",
                             "life": 1.2, "max": 1.2, "attr": P["yellow"]})
            # render satu frame biar ledakan kelihatan sebelum overlay
            stdscr.refresh()
            pick = upgrade_screen.show(stdscr, P, choices, level, owned)
            u = choices[pick]
            upgrades.apply(_get(u, "id"), stats)
            owned[_get(u, "id")] = owned.get(_get(u, "id"), 0) + 1
            base_lv += 1
            sfx_mod.play(stdscr, sfx, "select")
            set_mood("excited", 2.2)
            if _get(u, "id") == "wall":
                player_hp = min(stats["max_hp"], player_hp + 25)
            player_max = float(stats["max_hp"])
            spawn_explosion(cx, h - 8, P["green"], n=30)
            floaters.append({"x": cx - 6, "y": h - 10.0, "text": f"+ {_get(u, 'name')}",
                             "life": 1.4, "max": 1.4, "attr": P["green"]})
            msg = f"UPGRADE: {_get(u, 'name')} — {_get(u, 'desc')}"
            msg_t = 2.2
            # reset timer input biar adil setelah milih
            word_start = time.monotonic()
            last = time.monotonic()

        if enemy_hp <= 0:
            acc = (hits / shots * 100) if shots else 100
            avg_wpm = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
            storage.save_best(storage.DEFAULT_BEST, wave, avg_wpm)
            spawn_explosion(cx, 8, P["yellow"], n=40)
            sfx_mod.play(stdscr, sfx, "waveclear")
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
                    widgets.safe_add(stdscr, int(pt["y"]), int(pt["x"]), pt["char"], pt["attr"])
                widgets.safe_add(stdscr, h2 // 2 - 1, w2 // 2 - 14, f"WAVE {wave} HANCUR!", P["yellow"])
                widgets.safe_add(stdscr, h2 // 2, w2 // 2 - 20, f"{acc:.0f}% | {avg_wpm:.0f} WPM | combo max {best_combo} | Enter lanjut", P["cyan"])
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
            msg = f"WAVE {wave} {ecfg.name} — {progression.rank_for(avg_wpm, best_combo)} mode ON!"
            msg_t = 2.5
            best_combo = 0
            last = time.monotonic()
            continue

        if player_hp <= 0:
            stdscr.nodelay(False)
            stdscr.erase()
            acc = (hits / shots * 100) if shots else 100
            avg_wpm = (correct_chars_total / 5) / (time_total / 60) if time_total > 0 else 0
            storage.save_best(storage.DEFAULT_BEST, wave, avg_wpm)
            rk = progression.rank_for(avg_wpm, best_combo)
            sfx_mod.play(stdscr, sfx, "gameover")
            widgets.safe_add(stdscr, h // 2 - 2, cx - 12, "BENTENGMU HANCUR", P["red"])
            widgets.safe_add(stdscr, h // 2 - 1, cx - 24, f"wave {wave} | {hits}/{shots} | {acc:.0f}% | {avg_wpm:.0f} WPM | {rk}", P["fg"])
            widgets.safe_add(stdscr, h // 2 + 1, cx - 16, "Enter coba lagi, q keluar", P["dim"])
            widgets.safe_add(stdscr, h // 2 + 2, cx - 20, "sedikit lagi… 1 wave lagi pasti bisa", P["magenta"])
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
            stats = upgrades.fresh_stats()
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
            widgets.safe_add(stdscr, int(s["y"]) % max(1, h), int(s["x"]) % max(1, w), ".", P["cyan_dim"])

        avg_live = (correct_chars_total / 5) / (time_total / 60) if time_total > 0.5 else 0
        rk_live = progression.rank_for(avg_live, combo)
        # ── ZONA ATAS: musuh (terpisah jelas dari status player) ──
        widgets.safe_add(stdscr, 0, 2, f"TEXTACK v{VERSION}  W{wave} COMBO x{combo} {rk_live}", P["fg"])
        widgets.safe_add(stdscr, 1, 2, f"▼ {ecfg.name} {widgets.hp_bar_str(enemy_hp, disp_e, enemy_max, min(34, w-30))}", P["red"])
        # combo meter + quality/sfx mungil (1 addstr digabung biar hemat)
        cw = min(16, w - 10)
        cfill = int(cw * min(1, combo / 10))
        sfx_s = "♪" if sfx["on"] else "×"
        widgets.safe_add(stdscr, 0, max(0, w - cw - 28), f"[{'█'*cfill}{'·'*(cw-cfill)}] {quality.QLEVELS[qi]['name']} {sfx_s}", P["magenta"])

        bob = int((now * 2) % 2)
        ey = 6 + shy + bob
        # telegraph murah: musuh kedip bold saat mau nyerang (>80% timer)
        tele = (enemy_timer / interval_eff()) > 0.8
        ecol = P[ecfg.col] | (curses.A_BOLD if tele else 0)
        for i, line in enumerate(ENEMY_ART):
            widgets.safe_add(stdscr, ey + i, cx - len(line) // 2 + shx, line, ecol)
        # nama + interval musuh (transparan biar taktik)
        widgets.safe_add(stdscr, ey + len(ENEMY_ART) + 1, cx - 14 + shx, f"{ecfg.name} HP{int(max(0,enemy_hp))} ATK/{interval_eff():.1f}s", ecol)
        # banner wave slide-in (murah: 1-2 addstr, lerp posisi)
        if banner_t > 0:
            bx = int(cx - len(banner) // 2 + (banner_t * 14))
            balpha = P["yellow"] | curses.A_BOLD if (now * 4) % 1 < 0.7 else P["yellow"]
            widgets.safe_add(stdscr, ey - 2, max(1, min(bx, w - len(banner) - 1)), banner, balpha)

        ty = ey + len(ENEMY_ART) + 3
        # target 3-segmen (hemat: 3-4 addstr, bukan per-huruf)
        tx = cx - len(target) // 2
        widgets.safe_add(stdscr, ty, tx - 2, "> ", P["fg"])
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
            widgets.safe_add(stdscr, ty, tx, target[:n_ok], P["green"])
        if first_bad >= 0:
            widgets.safe_add(stdscr, ty, tx + first_bad, target[first_bad: first_bad + 1], P["red"] | curses.A_BOLD)
            if first_bad + 1 < len(target):
                widgets.safe_add(stdscr, ty, tx + first_bad + 1, target[first_bad + 1:], P["fg"])
        else:
            rest = target[n_ok:]
            if rest:
                widgets.safe_add(stdscr, ty, tx + n_ok, rest[0], curses.A_REVERSE)
                if len(rest) > 1:
                    widgets.safe_add(stdscr, ty, tx + n_ok + 1, rest[1:], P["fg"])
        tfrac = max(0, min(1, elapsed_word / interval_eff()))
        tw = min(30, w - 10)
        tfill = int(tw * (1 - tfrac))
        # timer berubah warna hijau->kuning->merah (feedback adiktif)
        tcol = P["green"] if tfrac < 0.5 else (P["yellow"] if tfrac < 0.8 else P["red"])
        widgets.safe_add(stdscr, ty + 1, cx - tw // 2, "[" + "━" * tfill + " " * (tw - tfill) + "]", tcol)

        for p in projectiles:
            widgets.safe_add(stdscr, int(p["y"]), int(p["x"]), p["char"], p["attr"])
        for pt in particles:
            a = pt["attr"] | (curses.A_DIM if pt["life"] < pt["max"] * 0.4 else curses.A_BOLD)
            widgets.safe_add(stdscr, int(pt["y"]), int(pt["x"]), pt["char"], a)
        for f in floaters:
            alpha = curses.A_BOLD if f["life"] > f["max"] * 0.4 else curses.A_DIM
            widgets.safe_add(stdscr, int(f["y"]), int(f["x"]), f["text"], f["attr"] | alpha)

        py = h - 7
        # ── ZONA BAWAH: status player nempel benteng sendiri (terpisah dari musuh) ──
        widgets.safe_add(stdscr, py - 2, 2, f"▲ KAMU {widgets.hp_bar_str(player_hp, disp_p, player_max, min(34, w-30))}", P["green"])
        xw = min(14, max(6, w - 60))
        xfill = int(xw * min(1, xp / max(1, xp_next)))
        turret_s = f" ⌖{stats['turret']}" if stats["turret"] else ""
        widgets.safe_add(stdscr, py - 1, 2, f"LV{level} [{'█'*xfill}{'·'*(xw-xfill)}] BASE{base_lv}{turret_s} DMGx{stats['dmg_mult']:.1f}", P["magenta"])
        # base visual naik level: armor ekstra + cannon kalau punya turret
        base_attr = P["green"] | (curses.A_BOLD if base_lv >= 5 else 0)
        for i, line in enumerate(PLAYER_ART):
            widgets.safe_add(stdscr, py + i, cx - len(line) // 2, line, base_attr)
        if stats["wall"] > 0:
            armor = "▣" * min(6, stats["wall"]) + f" Lv{stats['wall']}"
            widgets.safe_add(stdscr, py + 4 if py + 4 < h else h - 1, cx - len(armor) // 2, armor, P["cyan"])
        if stats["turret"] > 0:
            blink = "⌖" if (now * 3) % 1 < 0.7 else "◉"
            widgets.safe_add(stdscr, py - 1, cx + 12, f"{blink}x{stats['turret']}", P["magenta"])
        # ── panel waifu operator (kanan, hanya layar lebar biar tidak sempit) ──
        if w >= 102 and h >= 24:
            px = w - 36
            widgets.safe_add(stdscr, py - 2, px, "◆ AIKA · operator", P["cyan"])
            for i, ln in enumerate(waifu_art):
                widgets.safe_add(stdscr, py - 1 + i, px, ln, P["magenta"] if i < 5 else P["fg"])
            wy = py - 1 + len(waifu_art)
            if wy < h - 3:
                face = waifu.FACES.get(wmood, "(・‿・)")
                widgets.safe_add(stdscr, wy, px, f"AIKA {face}", P["yellow"] | curses.A_BOLD)
                if wmood == "idle":
                    say = waifu.TIPS[int(now / 4) % len(waifu.TIPS)]
                else:
                    pool = waifu.LINES.get(wmood, ["..."])
                    say = pool[wline % len(pool)]
                widgets.safe_add(stdscr, wy + 1, px, f"「{say}」", P["dim"])
        # heartbeat murah: sudut layar kedip saat HP < 30% (4 addstr saja)
        if player_hp < player_max * 0.3 and player_hp > 0:
            hb = P["red"] | curses.A_BOLD if (now * 3) % 1 < 0.5 else P["dim"]
            widgets.safe_add(stdscr, 0, 0, "♥", hb)
            widgets.safe_add(stdscr, 0, w - 1, "♥", hb)
            widgets.safe_add(stdscr, h - 1, 0, "♥", hb)
            widgets.safe_add(stdscr, h - 1, w - 1, "♥", hb)

        caret = "█" if (now * 4) % 1 < 0.6 else " "
        prompt = f"> {buf}{caret}"
        widgets.safe_add(stdscr, h - 2, max(0, cx - max(len(prompt), len(target)) // 2 - 2), prompt, P["fg"])
        if msg_t > 0:
            widgets.safe_add(stdscr, h - 3, 2, msg[: max(0, w - 4)], P["cyan"])
        else:
            live_wpm = (len(buf) / 5) / (elapsed_word / 60) if elapsed_word > 0.2 else 0
            widgets.safe_add(stdscr, h - 3, 2, f"{elapsed_word:.1f}s | {live_wpm:.0f} WPM | {combo}x | Enter=tembak", P["dim"])

        stdscr.refresh()
