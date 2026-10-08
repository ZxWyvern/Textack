# textack/core/combat.py
from __future__ import annotations

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
