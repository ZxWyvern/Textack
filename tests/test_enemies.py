# tests/test_enemies.py
from textack.core import enemies
def test_scout_wave1():
    c = enemies.for_wave(1)
    assert c.name == "SCOUT" and c.burst == 1
def test_boss_scaling():
    c = enemies.for_wave(5)
    assert c.name.startswith("BOSS") and c.burst == 3
    assert c.interval >= 2.6
def test_late_wave_cap():
    c = enemies.for_wave(30)
    assert c.interval >= 2.4
