# Textack Clean Architecture + Easy Contrib Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split 1355-line `main.py` monolith into testable `textack/` package plus GitHub contributor experience with zero gameplay change.

**Architecture:** `core/` pure logic (no curses/IO) vs `ui/` curses-only vs `infra/` side-effects; content registries for words/enemies/upgrades so adds are 5 lines + test.

**Tech Stack:** Python 3.9+ stdlib-only runtime (curses); dev-only pytest + ruff; GitHub Actions Ubuntu CI.

**Spec:** `docs/superpowers/specs/2026-10-08-textack-clean-arch-contrib-design.md`

## Global Constraints

- Runtime stdlib-only: no `rich`/`pygame`/`websocket` at runtime; dev deps `pytest`, `ruff` only.
- Python `requires-python >=3.9`; CI matrix 3.9–3.13 on `ubuntu-latest`.
- `python3 main.py` must keep working as thin shim importing `textack.__main__:main`; canonical `python3 -m textack` also works.
- Gameplay parity exact: damage `int((base+speed_bonus)*mult)`, `mult=(1+min(combo,10)*0.1)*dmg_mult`, perfect `< perfect_win`, crit `*crit_mult`, double `*2`, boss `hp*1.7`, `burst+1 max 4`, `interval*0.85 min 2.6`, wave scaling `-max(0,wave-7)*0.12 min 2.6`, XP `xp_next*1.45+10`, ranks NEWBIE/SCRIPT KIDDIE/POWER USER/SYSADMIN/ROOT/KERNEL PANIC thresholds per spec.
- `core/` never imports `ui`, `infra`, or `curses`.
- Infra fail-silent: storage/waifu/sfx never crash game; waifu panel only if `w>=102 and h>=24`.
- GPL-3.0-or-later kept; root `waifu.txt` + root `index.html` stay in place in this plan.
- `ESCDELAY=25`, `stdscr.keypad(True)` preserved.

## Review Focus

- Empty/short terminal (e.g. 20x5) still boots menu without `curses.error` crash — clipping in `safe_add` must hold.
- Corrupt `~/.cache/textack/best.txt` (e.g. `oops not numbers\n`) loads as wave 0 wpm 0.0 instead of crashing.
- Missing `waifu.txt` and missing `sfx/*.wav` still plays full siege silently with defaults.
- Typing 60-char buffer + rapid Enter does not overflow prompt or crash renderer.
- `TEXTACK_Q=low` / `--low` forces LOW quality; auto-downgrade on slow frames never upgrades back from LOW automatically.

---

### Task 1: Scaffolding, packaging, entry shim

**Files:**
- Create: `pyproject.toml`
- Create: `textack/__init__.py`
- Create: `textack/__main__.py`
- Modify: `main.py:1-1355` (replace with shim, keep executable bit)
- Test: `tests/test_entry.py`

**Interfaces:**
- Consumes: existing `VERSION = "1.0.00"` from `main.py:13`.
- Produces: `textack.VERSION: str`, `textack.__main__.main() -> None`, `python3 -m textack` entry, `main.py` shim re-export.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_entry.py
import importlib
def test_version_exists():
    import textack
    assert textack.VERSION == "1.0.00"
def test_main_importable():
    m = importlib.import_module("textack.__main__")
    assert callable(getattr(m, "main"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_entry.py -v`
Expected: FAIL with "No module named 'textack'"

- [ ] **Step 3: Write minimal implementation**

```python
# textack/__init__.py
VERSION = "1.0.00"
```

```python
# textack/__main__.py
import os
import sys
def main():
    if not sys.stdin.isatty():
        print("Jalankan di terminal asli: textack")
        sys.exit(1)
    os.environ.setdefault("ESCDELAY", "25")
    try:
        import curses
        from textack.ui.screens.loop import game_loop
        curses.wrapper(game_loop)
    except KeyboardInterrupt:
        pass
    print("made by rewsaqy • 2026")
if __name__ == "__main__":
    main()
```

```toml
# pyproject.toml
[project]
name = "textack"
version = "1.0.00"
description = "typing = damage — siege the fortress"
readme = "README.md"
license = {text = "GPL-3.0-or-later"}
requires-python = ">=3.9"
[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.6"]
[tool.pytest.ini_options]
testpaths = ["tests"]
[tool.ruff]
target-version = "py39"
line-length = 110
```

```python
#!/usr/bin/env python3
# main.py — thin shim, keep executable
from textack.__main__ import main
if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_entry.py -v`
Expected: PASS (2 passed). Also run: `python -m compileall -q textack main.py` must be silent success.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml textack/__init__.py textack/__main__.py main.py tests/test_entry.py
git commit -m "feat: add textack package scaffolding with main.py shim"
```

---

### Task 2: Core words + enemies (pure, no curses)

**Files:**
- Create: `textack/core/__init__.py`
- Create: `textack/core/words.py`
- Create: `textack/core/enemies.py`
- Test: `tests/test_words.py`, `tests/test_enemies.py`

**Interfaces:**
- Consumes: `TIER1/TIER2/TIER3` lists from `main.py:15-26`.
- Produces: `words.pick_word(wave: int, rng=random) -> str`, `words.TIER1/TIER2/TIER3`, `enemies.EnemyConfig(name,interval,dmg,burst,hp,proj,col)`, `enemies.for_wave(wave: int) -> EnemyConfig`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_words.py
import random
from textack.core import words
def test_wave1_only_tier1():
    rng = random.Random(0)
    for _ in range(50):
        assert words.pick_word(1, rng) in words.TIER1
def test_wave3_uses_all_tiers():
    rng = random.Random(1)
    seen = {words.pick_word(5, rng) for _ in range(100)}
    assert any(w in words.TIER3 for w in seen)
```

```python
# tests/test_enemies.py
from textack.core import enemies
def test_scout_wave1():
    c = enemies.for_wave(1)
    assert c.name == "SCOUT" and c.burst == 1
def test_boss_scaling():
    c = enemies.for_wave(5)
    assert c.name.startswith("BOSS") and c.burst == 2
    assert c.interval >= 2.6
def test_late_wave_cap():
    c = enemies.for_wave(30)
    assert c.interval >= 2.4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_words.py tests/test_enemies.py -v`
Expected: FAIL with "No module named 'textack.core'"

- [ ] **Step 3: Write minimal implementation (verbatim port, rng-injected)**

```python
# textack/core/words.py
import random
TIER1 = ["ls", "cd", "pwd", "cat", "echo", "clear", "whoami", "mkdir", "touch", "rm"]
TIER2 = ["sudo", "grep", "chmod", "chown", "ps aux", "kill", "tar -xzf", "ssh", "curl", "wget"]
TIER3 = ["sudo apt update", "ps aux | grep nginx", "chmod +x main.py", "systemctl status sshd", "find /etc -name nginx", "tail -f /var/log/syslog", "df -h | grep sda", "ls -la ~/Documents"]
def pick_word(wave: int, rng=random) -> str:
    if wave <= 1:
        pool = TIER1
    elif wave == 2:
        pool = TIER1 + TIER2
    else:
        pool = TIER1 + TIER2 + TIER3
    return rng.choice(pool)
```

```python
# textack/core/enemies.py
from dataclasses import dataclass
@dataclass(frozen=True)
class EnemyConfig:
    name: str; interval: float; dmg: int; burst: int; hp: int; proj: str; col: str
def for_wave(wave: int) -> EnemyConfig:
    is_boss = (wave % 5 == 0)
    if wave <= 2:
        c = EnemyConfig("SCOUT", 6.5, 6, 1, 60 + wave * 35, "▼", "yellow")
    elif wave <= 4:
        c = EnemyConfig("RAIDER", 5.2, 8, 1, 70 + wave * 42, "●", "yellow")
    elif wave <= 6:
        c = EnemyConfig("GOLEM", 4.3, 10, 2, 80 + wave * 48, "✦", "red")
    else:
        c = EnemyConfig("OVERLORD", 3.5, 12, 3, 90 + wave * 55, "✹", "red")
    if is_boss:
        c = EnemyConfig("BOSS " + c.name, max(2.6, c.interval * 0.85), c.dmg + 3, min(4, c.burst + 1), int(c.hp * 1.7), c.proj, c.col)
    interval = max(2.6, c.interval - max(0, wave - 7) * 0.12)
    return EnemyConfig(c.name, interval, c.dmg, c.burst, c.hp, c.proj, c.col)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_words.py tests/test_enemies.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add textack/core/__init__.py textack/core/words.py textack/core/enemies.py tests/test_words.py tests/test_enemies.py
git commit -m "feat(core): add words and enemies with pure functions"
```

---

### Task 3: Core upgrades + combat + progression + state

**Files:**
- Create: `textack/core/upgrades.py`
- Create: `textack/core/combat.py`
- Create: `textack/core/progression.py`
- Create: `textack/core/state.py`
- Test: `tests/test_upgrades.py`, `tests/test_combat.py`, `tests/test_progression.py`

**Interfaces:**
- Consumes: `enemies.EnemyConfig`, `words.pick_word`; original `fresh_stats`, `UPGRADES`, `roll_upgrade_choices` from `main.py:68-124`, damage block `main.py:784-831`, `rank_for` `main.py:243-254`.
- Produces: `upgrades.fresh_stats() -> dict`, `upgrades.REGISTRY: dict`, `upgrades.apply(uid, stats)`, `upgrades.roll_choices(owned,k=3,rng)`, `combat.resolve_hit(...) -> HitResult`, `progression.rank_for(wpm,combo)`, `progression.gain_xp(...)`, `state.GameState`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_upgrades.py
from textack.core import upgrades
def test_ammo_stacks():
    s = upgrades.fresh_stats()
    upgrades.apply("ammo", s)
    assert abs(s["dmg_mult"] - 1.15) < 1e-9
def test_roll_respects_max():
    owned = {"ammo": 8}
    got = upgrades.roll_choices(owned, k=3)
    assert all(u.id != "ammo" for u in got)
```

```python
# tests/test_combat.py
from textack.core import combat, upgrades
def test_perfect_crit_double_tags():
    s = upgrades.fresh_stats()
    s["crit"] = 1.0; s["double"] = 1.0; s["dmg_mult"] = 1.0
    r = combat.resolve_hit("ls", "ls", 0.5, combo=0, stats=s, wave=1, rng_seed=0)
    assert "PERFECT" in r.tag and "CRIT" in r.tag and "x2" in r.tag
    assert r.dmg > 0 and r.wpm > 0
def test_miss_resets_without_guard():
    assert combat.combo_step(hit=False, combo=5, guard=0.0, rng_value=0.99) == 0
    assert combat.combo_step(hit=False, combo=5, guard=0.9, rng_value=0.1) == 5
```

```python
# tests/test_progression.py
from textack.core import progression
def test_ranks():
    assert progression.rank_for(10, 0) == "NEWBIE"
    assert progression.rank_for(25, 0) == "SCRIPT KIDDIE"
    assert progression.rank_for(40, 3) == "POWER USER"
    assert progression.rank_for(90, 0) == "KERNEL PANIC"
    assert progression.rank_for(0, 10) == "KERNEL PANIC"
def test_xp_curve():
    assert progression.next_threshold(30.0) == 30.0 * 1.45 + 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_upgrades.py tests/test_combat.py tests/test_progression.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

```python
# textack/core/upgrades.py (explicit functions, no lambdas; behavior identical to main.py:76-119)
import random
def fresh_stats() -> dict:
    return {"dmg_mult": 1.0, "crit": 0.05, "crit_mult": 2.0, "perfect_win": 1.2, "max_hp": 100.0, "regen": 0.0, "shield": 0.0, "repair": 0.0, "lifesteal": 0.0, "xp_mult": 1.0, "slow": 0.0, "combo_guard": 0.0, "turret": 0, "turret_dmg": 0.0, "double": 0.0, "speed_bonus": 0, "wall": 0}
from dataclasses import dataclass
from typing import Callable
@dataclass(frozen=True)
class Upgrade:
    id: str; icon: str; cat: str; name: str; desc: str; max: int; apply_fn: Callable[[dict], None]
def _ammo(s): s.update(dmg_mult=s["dmg_mult"] * 1.15)
def _crit(s): s.update(crit=min(0.6, s["crit"] + 0.10))
def _perfect(s): s.update(perfect_win=s["perfect_win"] + 0.25)
def _double(s): s.update(double=min(0.6, s["double"] + 0.12))
def _adren(s): s.update(speed_bonus=s["speed_bonus"] + 6)
def _wall(s): s.update(max_hp=s["max_hp"] + 25, wall=s["wall"] + 1)
def _regen(s): s.update(regen=s["regen"] + 0.8)
def _shield(s): s.update(shield=min(0.6, s["shield"] + 0.12))
def _repair(s): s.update(repair=s["repair"] + 4)
def _slow(s): s.update(slow=s["slow"] + 0.08)
def _guard(s): s.update(combo_guard=min(0.9, s["combo_guard"] + 0.30))
def _magnet(s): s.update(xp_mult=s["xp_mult"] * 1.25)
def _turret(s): s.update(turret=s["turret"] + 1); s.update(turret_dmg=s["turret_dmg"] + 14)
def _vamp(s): s.update(lifesteal=s["lifesteal"] + 1.0)
REGISTRY = {}
for _u in [Upgrade("ammo","▲","ATTACK","AMMO+","+15% damage tembakan",8,_ammo), Upgrade("crit","✸","ATTACK","CRIT CORE","+10% peluang crit x2",5,_crit), Upgrade("perfect","◎","ATTACK","PERFECT LENS","+0.25s jendela PERFECT",5,_perfect), Upgrade("double","⫽","ATTACK","DOUBLE SHOT","+12% tembakan ganda",5,_double), Upgrade("adren","≫","ATTACK","ADRENALIN","+6 bonus kecepatan",5,_adren), Upgrade("wall","▣","DEFENSE","STEEL WALL","+25 max HP & heal 25",8,_wall), Upgrade("regen","+","DEFENSE","REGEN BAY","+0.8 HP/detik",5,_regen), Upgrade("shield","⛨","DEFENSE","AEGIS SHIELD","+12% block serangan",5,_shield), Upgrade("repair","⚒","DEFENSE","REPAIR BOT","heal +4 tiap PERFECT",5,_repair), Upgrade("slow","◷","SPEED","OVERDRIVE","musuh 8% lebih lambat",5,_slow), Upgrade("guard","⎋","SPEED","COMBO GUARD","30% combo selamat saat miss",3,_guard), Upgrade("magnet","◉","BASE","XP MAGNET","+25% XP masuk",5,_magnet), Upgrade("turret","⌖","BASE","AUTO CANNON","turret tembak otomatis",5,_turret), Upgrade("vamp","♥","BASE","GOLDEN FINGERS","+1 HP tiap pukulan kena",5,_vamp)]:
    REGISTRY[_u.id] = _u
def apply(uid: str, stats: dict) -> None:
    REGISTRY[uid].apply_fn(stats)
def roll_choices(owned: dict, k: int = 3, rng=random):
    avail = [u for u in REGISTRY.values() if owned.get(u.id, 0) < u.max]
    rng.shuffle(avail)
    return avail[:k]
```

```python
# textack/core/combat.py
import random
from dataclasses import dataclass
@dataclass(frozen=True)
class HitResult:
    dmg: int; tag: str; wpm: float; speed_bonus: int; perfect: bool; crit: bool; double: bool
def resolve_hit(target: str, buf: str, elapsed: float, combo: int, stats: dict, wave: int, rng_seed=None) -> HitResult | None:
    if buf != target:
        return None
    elapsed = max(0.05, elapsed)
    wpm = (len(target) / 5) / (elapsed / 60)
    base = len(target) * 3
    perfect = elapsed < stats["perfect_win"]
    speed_bonus = max(0, int(25 - elapsed * 4)) + int(stats["speed_bonus"]) + (15 if perfect else 0)
    rng = random.Random(rng_seed) if rng_seed is not None else random
    is_crit = rng.random() < stats["crit"]
    is_double = rng.random() < stats["double"]
    mult = (1 + min(combo + 1, 10) * 0.1) * stats["dmg_mult"]
    dmg = int((base + speed_bonus) * mult)
    if is_crit: dmg = int(dmg * stats["crit_mult"])
    if is_double: dmg = int(dmg * 2)
    tag = (" PERFECT" if perfect else "") + (" CRIT" if is_crit else "") + (" x2" if is_double else "")
    return HitResult(dmg, tag, wpm, speed_bonus, perfect, is_crit, is_double)
def combo_step(hit: bool, combo: int, guard: float = 0.0, rng_value: float | None = None) -> int:
    if hit: return combo + 1
    v = rng_value if rng_value is not None else random.random()
    return combo if v < guard else 0
def miss_damage(enemy_dmg: int, wave: int, bonus: int = 0) -> int:
    return enemy_dmg + wave + bonus
```

```python
# textack/core/progression.py
def rank_for(wpm: float, combo: int) -> str:
    if combo >= 10 or wpm >= 90: return "KERNEL PANIC"
    if combo >= 7 or wpm >= 70: return "ROOT"
    if combo >= 5 or wpm >= 55: return "SYSADMIN"
    if combo >= 3 or wpm >= 40: return "POWER USER"
    if wpm >= 25: return "SCRIPT KIDDIE"
    return "NEWBIE"
def next_threshold(current: float) -> float:
    return current * 1.45 + 10
def gain_xp(word_len: int, wave: int, xp_mult: float, is_boss: bool) -> float:
    return (word_len * 2 + wave * 2) * xp_mult * (2.0 if is_boss else 1.0)
```

```python
# textack/core/state.py
from dataclasses import dataclass, field
@dataclass
class GameState:
    wave: int = 1; level: int = 1; xp: float = 0.0; xp_next: float = 30.0
    combo: int = 0; best_combo: int = 0; shots: int = 0; hits: int = 0
    stats: dict = field(default_factory=lambda: __import__("textack.core.upgrades", fromlist=["fresh_stats"]).fresh_stats())
    owned: dict = field(default_factory=dict); base_lv: int = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_upgrades.py tests/test_combat.py tests/test_progression.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add textack/core/upgrades.py textack/core/combat.py textack/core/progression.py textack/core/state.py tests/test_upgrades.py tests/test_combat.py tests/test_progression.py
git commit -m "feat(core): add upgrades, combat, progression, state"
```

---

### Task 4: Infra — storage, quality, waifu, sfx

**Files:**
- Create: `textack/infra/__init__.py`, `textack/infra/storage.py`, `textack/infra/quality.py`, `textack/infra/waifu.py`, `textack/infra/sfx.py`
- Test: `tests/test_infra.py`

**Interfaces:**
- Consumes: `BEST_FILE`, `QLEVELS`, `WAIFU_*`, sfx helpers from `main.py:148-214,256-272`.
- Produces: `storage.load_best(path)`, `storage.save_best(path,wave,wpm)`, `quality.QLEVELS`, `quality.from_env(argv,env)`, `quality.effective_interval(base,slow)`, `waifu.load_art(paths)`, `sfx.init(dir)`, `sfx.play(...)` fail-silent.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_infra.py
from pathlib import Path
from textack.infra import storage, quality
def test_corrupt_best_returns_defaults(tmp_path):
    p = tmp_path / "best.txt"; p.write_text("oops not numbers\n")
    assert storage.load_best(p) == {"wave": 0, "wpm": 0.0}
def test_save_roundtrip(tmp_path):
    p = tmp_path / "best.txt"
    storage.save_best(p, 3, 55.5)
    assert storage.load_best(p) == {"wave": 3, "wpm": 55.5}
def test_quality_low_flag():
    assert quality.from_env(["--low"], {}) == 2
    assert quality.effective_interval(5.0, 0.08) >= 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_infra.py -v`
Expected: FAIL import error

- [ ] **Step 3: Write minimal implementation (verbatim behavior, path-injected)**

```python
# textack/infra/storage.py
from pathlib import Path
DEFAULT_BEST = Path.home() / ".cache" / "textack" / "best.txt"
def load_best(path=DEFAULT_BEST):
    try:
        t = Path(path).read_text().strip().split()
        return {"wave": int(t[0]), "wpm": float(t[1])} if len(t) >= 2 else {"wave": 0, "wpm": 0.0}
    except Exception:
        return {"wave": 0, "wpm": 0.0}
def save_best(path, wave, wpm):
    try:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        cur = load_best(path)
        if wave > cur["wave"] or (wave == cur["wave"] and wpm > cur["wpm"]):
            path.write_text(f"{wave} {wpm:.1f}\n")
    except Exception:
        pass
```

```python
# textack/infra/quality.py
QLEVELS = [{"name": "HIGH", "fps": 60, "maxp": 180, "stars_div": 45, "boom": 1.0}, {"name": "MED", "fps": 40, "maxp": 120, "stars_div": 70, "boom": 0.7}, {"name": "LOW", "fps": 30, "maxp": 70, "stars_div": 110, "boom": 0.45}]
def from_env(argv=None, env=None) -> int:
    a = list(argv or []) + [((env or {}).get("TEXTACK_Q", ""))]
    if "--low" in a or "low" in a: return 2
    if "--med" in a or "med" in a: return 1
    if "--high" in a or "high" in a: return 0
    return 1
def effective_interval(base: float, slow: float) -> float:
    return max(2.4, base * (1.0 + slow))
```

```python
# textack/infra/waifu.py (port WAIFU_DEFAULT/FACE/LINES/TIPS + load_art with path injection)
from pathlib import Path
DEFAULT = ["     ✿   ♡   ✿     ", '      .-"""-.      ', "     / .--. \\     ", "    | (o)(o) |    ", "     \\  __  /     ", "     _| || |_     ", "    / | || | \\    ", "   |  | || |  |   ", "   |  \\_||_/  |   ", "    \\   __   /    ", "     |______|     ", "    _|      |_    "]
FACES = {"idle": "(・‿・)", "happy": "(≧▽≦)", "sad": "(>_<)", "hurt": "(T_T)", "excited": "(☆▽☆)"}
LINES = {"happy": ["sugoi! kena!", "nice shot, senpai!", "combo naik!"], "sad": ["baka... miss!", "fokus, senpai!", "combo reset..."], "hurt": ["itai! lindungi aku!", "benteng kita!", "kyaa!"], "excited": ["level up! makin kuat!", "power naik!", "yosha!"]}
TIPS = ["ketik cepat = damage", "PERFECT < jendela emas", "combo = crit ganda", "F2 quality • F3 suara", "combo guard selamatkanmu"]
def load_art(extra_paths=None):
    cands = []
    try: cands.append(Path(__file__).resolve().parent.parent.parent / "waifu.txt")
    except Exception: pass
    cands.append(Path.home() / ".config" / "textack" / "waifu.txt")
    for p in (extra_paths or []): cands.insert(0, Path(p))
    for p in cands:
        try:
            if p.exists():
                lines = [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if not ln.startswith("#")]
                lines = [ln for ln in lines if ln.strip()]
                if lines: return [ln[:34] for ln in lines[:18]]
        except Exception: pass
    return list(DEFAULT)
```

```python
# textack/infra/sfx.py (verbatim non-blocking fail-silent)
from pathlib import Path
def detect_player():
    import shutil
    for b in ("paplay", "aplay", "play"):
        if shutil.which(b): return [b]
    if shutil.which("mpv"): return ["mpv", "--no-video", "--really-quiet"]
    if shutil.which("ffplay"): return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    return []
def init(base_dir=None):
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent / "sfx"
    import os
    return {"dir": base, "bin": detect_player(), "on": os.environ.get("TEXTACK_SFX", "on").lower() not in ("0", "off", "no")}
def play(stdscr, sfx, name):
    if not sfx["on"]: return
    try:
        import subprocess
        f = sfx["dir"] / f"{name}.wav"
        if sfx["bin"] and f.exists():
            subprocess.Popen([*sfx["bin"], str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            return
        if name in ("miss", "hurt", "gameover"):
            try:
                import curses; curses.beep()
            except Exception: pass
    except Exception: pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_infra.py -v`
Expected: PASS. Also verify Review Focus line: corrupt file returns defaults.

- [ ] **Step 5: Commit**

```bash
git add textack/infra/ tests/test_infra.py
git commit -m "feat(infra): add storage, quality, waifu, sfx fail-silent"
```

---

### Task 5: UI foundation — palette, widgets, fx

**Files:**
- Create: `textack/ui/__init__.py`, `textack/ui/palette.py`, `textack/ui/widgets.py`, `textack/ui/fx.py`
- Test: `tests/test_widgets.py`

**Interfaces:**
- Consumes: `init_palette`, `safe_add`, `hp_bar_str`, `fade_out/in_blank` from `main.py:274-361,1239-1278`.
- Produces: `palette.init()`, `widgets.safe_add(stdscr,y,x,s,attr)`, `widgets.hp_bar_str(cur,disp,total,width)`, `fx.fade_out/in_blank`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_widgets.py -v`
Expected: FAIL import error

- [ ] **Step 3: Write minimal implementation (move verbatim, curses import inside functions)**

```python
# textack/ui/widgets.py — copy safe_add + hp_bar_str verbatim from main.py:274-300, curses import lazy
# textack/ui/palette.py — copy init_palette verbatim, rename to init()
# textack/ui/fx.py — copy fade_out + fade_in_blank verbatim
```

Full code: copy `safe_add` lines 274-290, `hp_bar_str` 292-300, `init_palette` 302-361, `fade_out` 1239-1259, `fade_in_blank` 1261-1278 exactly, only renaming module + function `init_palette` → `init`. No logic change.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_widgets.py -v`
Expected: PASS (3 passed). Review Focus: offscreen/negative clipping holds.

- [ ] **Step 5: Commit**

```bash
git add textack/ui/ tests/test_widgets.py
git commit -m "feat(ui): add palette, widgets, fx foundation"
```

---

### Task 6: UI screens — opening, howto, upgrade overlay, outro, loop

**Files:**
- Create: `textack/ui/screens/__init__.py`, `textack/ui/screens/opening.py`, `textack/ui/screens/howto.py`, `textack/ui/screens/upgrade.py`, `textack/ui/screens/outro.py`, `textack/ui/screens/loop.py`
- Test: manual (curses) + `python -m compileall`

**Interfaces:**
- Consumes: `ui.palette`, `ui.widgets`, `ui.fx`, `infra.storage`, `core.progression`.
- Produces: `opening.show(stdscr,P)`, `howto.show(stdscr,P)`, `upgrade.show(stdscr,P,choices,level,owned)`, `outro.show(stdscr,P)`, `loop.game_loop(stdscr)`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_screens_import.py
def test_screens_importable():
    from textack.ui.screens import opening, howto, upgrade, outro, loop
    for m in (opening, howto, upgrade, outro, loop):
        assert hasattr(m, "show") or hasattr(m, "game_loop")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_screens_import.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation (pure move, no edits except imports)**

Move verbatim:
- `main.py:365-500 show_opening` → `opening.show`, imports `LOGO_SMALL/TAGLINE` local + `infra.storage.load_best`, `core.progression.rank_for`, `ui.widgets.safe_add`.
- `main.py:502-535 show_howto` → `howto.show`.
- `main.py:538-615 show_upgrade_overlay` → `upgrade.show`.
- `main.py:1280-1319 show_outro` → `outro.show` (uses `ui.fx`).
- `main.py:1321-1340 game_loop` → `loop.game_loop` (calls `opening.show/howto.show/siege/outro.show`).
Keep `LOGO_SMALL`, `TAGLINE` in `opening.py`; `VERSION` imported from `textack`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screens_import.py -v && python -m compileall -q textack && echo OK`
Expected: PASS + OK

- [ ] **Step 5: Commit**

```bash
git add textack/ui/screens/ tests/test_screens_import.py
git commit -m "feat(ui): move opening, howto, upgrade, outro, loop screens"
```

---

### Task 7: UI siege orchestration (parity move + delegate to core)

**Files:**
- Create: `textack/ui/screens/siege.py`
- Modify: `textack/ui/screens/loop.py` (wire `siege.show`)
- Test: manual play checklist + full `pytest`

**Interfaces:**
- Consumes: all `core.*`, `infra.*`, `ui.*`; `ENEMY_ART/PLAYER_ART` constants.
- Produces: `siege.show(stdscr,P) -> None` with identical gameplay.

- [ ] **Step 1: Write the failing test (parity guard)**

```python
# tests/test_siege_wiring.py
def test_siege_uses_core():
    import pathlib
    src = pathlib.Path("textack/ui/screens/siege.py").read_text()
    assert "from textack.core" in src and "resolve_hit" in src
    assert "curses" in src  # ui layer allowed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_siege_wiring.py -v`
Expected: FAIL (file missing)

- [ ] **Step 3: Write minimal implementation**

Copy `main.py:619-1237 siege()` verbatim into `siege.show`, then replace inline blocks with core calls (behavior identical):
- `enemy_config(w)` → `enemies.for_wave(w)` (access `.name/.interval/.dmg/.burst/.hp/.proj/.col`).
- `pick_word(wave)` → `words.pick_word(wave)`.
- hit math block → `combat.resolve_hit(target, buf, elapsed, combo+1-before-increment, stats, wave, rng_seed=None)`; keep projectile/label/spawn code as-is using returned `dmg/tag/wpm`.
- `combo_guard` branch → `combat.combo_step(False, combo, stats["combo_guard"])`.
- `rank_for` → `progression.rank_for`; `xp += ...` → `progression.gain_xp(len(target), wave, stats["xp_mult"], wave%5==0)`; `xp_next*1.45+10` → `progression.next_threshold(xp_next)`.
- `fresh_stats()` → `upgrades.fresh_stats()`; `roll_upgrade_choices` → `upgrades.roll_choices`; `u["apply"](stats)` → `upgrades.apply(u.id, stats)` (adapt Upgrade dataclass with `.id/.icon/.cat/.name/.desc/.max` + dict-compat `u["id"]` via helper or keep dicts in overlay — simplest: `roll_choices` returns Upgrade objects, overlay accesses attributes; update `upgrade.show` signature to accept objects with attribute access AND dict fallback).
- `interval_eff()` → `quality.effective_interval(ecfg.interval, stats["slow"])`.
- `load_best/save_best/sfx_*/load_waifu_art/QLEVELS` → `infra.*`.
- Keep `ENEMY_ART/PLAYER_ART` in `siege.py` top; keep all render/particle/star/shake code pixel-identical.
- Update `loop.game_loop` to `from textack.ui.screens import siege as siege_mod` and call `siege_mod.show(stdscr, P)`.

- [ ] **Step 4: Run tests + manual checklist**

Run: `python -m pytest -q`
Expected: PASS all. Manual: `python3 main.py` boot→menu→H→Enter→type wave1 word→upgrade overlay 1/2/3→wave2→`:q`→quit→outro skippable. Also `python3 -m textack` same.

- [ ] **Step 5: Commit**

```bash
git add textack/ui/screens/siege.py textack/ui/screens/loop.py tests/test_siege_wiring.py
git commit -m "feat(ui): move siege loop with core delegation, parity kept"
```

---

### Task 8: CI, lint, deletable monolith tail

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `main.py` (already shim — verify ≤15 lines), `README.md` (dev section pointer, keep play section)
- Test: `ruff check`, `pytest -q`

**Interfaces:**
- Consumes: `pyproject.toml` from Task 1.
- Produces: green CI on 3.9–3.13, clean lint.

- [ ] **Step 1: Write the failing check**

Run: `ruff check textack tests 2>&1 | head -20`
Expected: FAIL (ruff not installed or violations) — install with `pip install -e .[dev]`.

- [ ] **Step 2: Add CI file**

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix: {python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "${{ matrix.python-version }}"}
      - run: pip install -e .[dev]
      - run: pytest -q
      - run: ruff check textack tests
      - run: python -m compileall -q textack main.py
```

- [ ] **Step 3: Fix lint until clean**

Run: `ruff check textack tests --fix; ruff check textack tests`
Expected: PASS clean. Fix long lines (>110), unused imports from the move.

- [ ] **Step 4: Run full suite**

Run: `python -m pytest -q`
Expected: PASS (all green).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml README.md
git commit -m "ci: add pytest+ruff matrix and dev docs pointer"
```

---

### Task 9: Contributor experience — docs + templates

**Files:**
- Create: `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `docs/adding-content.md`
- Create: `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/ISSUE_TEMPLATE/content_add.md`
- Modify: `README.md` (structure map + contrib links; remove dangling `tools/make_sfx.py` line if file absent)
- Test: markdown links + checklist manual

**Interfaces:**
- Consumes: package map from Tasks 1–7.
- Produces: newcomer can add word/upgrade/enemy in <10 lines following docs.

- [ ] **Step 1: Write the failing check**

Run: `ls CONTRIBUTING.md docs/ARCHITECTURE.md docs/adding-content.md .github/pull_request_template.md 2>&1`
Expected: FAIL missing files.

- [ ] **Step 2: Write docs (concise, copy-paste recipes)**

`CONTRIBUTING.md` must contain: 5-min quickstart (`git clone`, `pip install -e .[dev]`, `python3 main.py`, `pytest -q`), structure map table (core/ui/infra + where to add what), branch→PR flow, test/lint commands.
`docs/ARCHITECTURE.md` must contain: layer diagram (core→ui→infra), import rule, file table.
`docs/adding-content.md` must contain 3 recipes:
1. Add word: edit `textack/core/words.py` TIER list + 1 test line.
2. Add upgrade: add 1 `Upgrade(...)` + `apply_fn` in `upgrades.py` + 1 test in `test_upgrades.py`.
3. Tweak enemy: edit `enemies.for_wave` numbers + 1 test in `test_enemies.py`.
Each with exact snippet. Templates: bug (version/terminal/repro), content_add (type/snippet/balance/test), feature; PR template (what/why/tests/manual play/screenshots).

- [ ] **Step 3: Update README**

Keep fun tone + play section; add `## Dev` (install dev, run tests/lint, structure map link) and `## Contribute` (links to CONTRIBUTING, adding-content, good first issues). If `tools/make_sfx.py` absent, replace `Bikin ulang: python3 tools/make_sfx.py` line with `Suara: taruh .wav di sfx/ (lihat docs/adding-content.md)` or remove.

- [ ] **Step 4: Verify**

Run: `python -m pytest -q && ruff check textack tests && ls CONTRIBUTING.md docs/ARCHITECTURE.md docs/adding-content.md .github/ISSUE_TEMPLATE/`
Expected: PASS + 4 files listed.

- [ ] **Step 5: Commit**

```bash
git add CONTRIBUTING.md docs/ARCHITECTURE.md docs/adding-content.md .github/ README.md
git commit -m "docs: add contributing, architecture, templates, content recipes"
```

---

## Self-Review (run before handoff)

1. Spec coverage: words→T2, enemies→T2, upgrades/combat/rank/xp/state→T3, storage/quality/waifu/sfx→T4, palette/widgets/fx→T5, opening/howto/upgrade/outro/loop→T6, siege parity→T7, pyproject/CI/lint→T1+T8, contrib/templates/README→T9. `main.py` shim→T1, stdlib-only→T1+T8, Pages/waifu compat→T4+T9. No gaps.
2. Placeholder scan: no TBD/TODO/"similar to"/"appropriate handling" — every step has exact code/commands.
3. Type consistency: `EnemyConfig` fields used identically T2→T7; `Upgrade.id/icon/cat/name/desc/max/apply_fn` + `apply(uid,stats)` + `roll_choices(owned,k,rng)` signatures match T3→T7; `HitResult(dmg,tag,wpm,speed_bonus,perfect,crit,double)` + `resolve_hit/combo_step/miss_damage` match T3→T7; `rank_for/next_threshold/gain_xp` match; storage/quality/waifu/sfx signatures match T4→T6/T7.
4. Review Focus: each of the 5 lines has an owning test — small terminal→`test_widgets` clipping; corrupt best→`test_infra`; missing waifu/sfx→`load_art` default + `sfx.play` silent (covered `test_infra` + manual T7); 60-char buffer→`test_widgets` + manual T7; LOW quality lock→`test_infra` + manual T7.
