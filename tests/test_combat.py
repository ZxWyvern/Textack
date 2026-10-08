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
def test_miss_damage_matches_siege_counter():
    # siege counter was inlined as ecfg.dmg + wave + randint(0, 4); must stay identical.
    assert combat.miss_damage(7, 3, 2) == 7 + 3 + 2
    assert combat.miss_damage(7, 3) == 7 + 3
