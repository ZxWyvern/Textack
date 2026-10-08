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
