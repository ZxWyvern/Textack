# tests/test_progression.py
from textack.core import progression


def test_ranks():
    assert progression.rank_for(10, 0) == "NEWBIE"
    assert progression.rank_for(25, 0) == "SCRIPT KIDDIE"
    assert progression.rank_for(40, 3) == "POWER USER"
    assert progression.rank_for(90, 0) == "KERNEL PANIC"
    assert progression.rank_for(0, 10) == "KERNEL PANIC"
def test_rank_boundaries():
    assert progression.rank_for(54, 0) == "POWER USER"
    assert progression.rank_for(55, 0) == "SYSADMIN"
    assert progression.rank_for(69, 0) == "SYSADMIN"
    assert progression.rank_for(70, 0) == "ROOT"
    assert progression.rank_for(0, 5) == "SYSADMIN"
    assert progression.rank_for(0, 7) == "ROOT"
def test_xp_curve():
    assert progression.next_threshold(30.0) == 30.0 * 1.45 + 10
