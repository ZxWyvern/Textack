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
