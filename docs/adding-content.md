# Adding Content: 3 Copy-Paste Recipes

Each recipe is <10 lines: one edit + one test. Run
`python3 -m pytest -q` after.

## Recipe 1: Add a word

File: `textack/core/words.py` — append to the right tier
(TIER1 = basics, TIER2 = mid, TIER3 = full commands):

```python
TIER2 = ["sudo", "grep", "chmod", "chown", "ps aux", "kill", "tar -xzf", "ssh", "curl", "wget", "htop"]
```

Test — add one line to `tests/test_words.py`:

```python
def test_htop_in_tier2():
    assert "htop" in words.TIER2
```

Check: `python3 -m pytest -q tests/test_words.py`.

## Recipe 2: Add an upgrade

File: `textack/core/upgrades.py`. Add an `apply_fn` next to the
other `_`-prefixed functions, then one `Upgrade(...)` entry in the
`REGISTRY` list:

```python
def _swift(s): s.update(slow=min(0.5, s["slow"] + 0.05), speed_bonus=s["speed_bonus"] + 2)
```

```python
Upgrade("swift", "»", "SPEED", "SWIFT BOOTS", "+5% slow musuh & +2 speed", 5, _swift),
```

Signature contract: `Upgrade(id, icon, cat, name, desc, max, apply_fn)`
where `apply_fn(stats: dict) -> None` mutates the dict from
`fresh_stats()`. Applied via `apply(uid, stats)`, offered via
`roll_choices(owned, k, rng)`.

Test — add to `tests/test_upgrades.py`:

```python
def test_swift_stacks():
    s = upgrades.fresh_stats()
    upgrades.apply("swift", s)
    assert s["speed_bonus"] == 2 and abs(s["slow"] - 0.05) < 1e-9
```

Check: `python3 -m pytest -q tests/test_upgrades.py`.

## Recipe 3: Tweak an enemy

File: `textack/core/enemies.py` — edit the numbers in `for_wave`.
Example: make RAIDER hit a bit softer but tankier:

```python
c = EnemyConfig("RAIDER", 5.2, 7, 1, 70 + wave * 48, "●", "yellow")
```

(Boss ×1.7 HP and late-wave interval floor `max(2.6, ...)` still
apply on top — no extra code needed.)

Test — add to `tests/test_enemies.py`:

```python
def test_raider_rebalanced():
    c = enemies.for_wave(3)
    assert c.name == "RAIDER" and c.dmg == 7 and c.hp == 70 + 3 * 48
```

Check: `python3 -m pytest -q tests/test_enemies.py`.

## Sound / art notes

- Sound: drop `.wav` files into `sfx/` (played via
  paplay/aplay/mpv, beep fallback, silent if missing).
  Toggle with F3. No build script needed.
- Waifu art: edit `waifu.txt` (or `~/.config/textack/waifu.txt`
  override). Missing file → default art, never a crash.
