# textack/core/state.py
from dataclasses import dataclass, field

from textack.core.upgrades import fresh_stats


@dataclass
class GameState:
    wave: int = 1; level: int = 1; xp: float = 0.0; xp_next: float = 30.0
    combo: int = 0; best_combo: int = 0; shots: int = 0; hits: int = 0
    stats: dict = field(default_factory=fresh_stats)
    owned: dict = field(default_factory=dict); base_lv: int = 0
