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
