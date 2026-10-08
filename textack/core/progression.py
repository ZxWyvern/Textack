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
