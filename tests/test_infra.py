# tests/test_infra.py
from textack.infra import quality, storage


def test_corrupt_best_returns_defaults(tmp_path):
    p = tmp_path / "best.txt"; p.write_text("oops not numbers\n")
    assert storage.load_best(p) == {"wave": 0, "wpm": 0.0}
def test_save_roundtrip(tmp_path):
    p = tmp_path / "best.txt"
    storage.save_best(p, 3, 55.5)
    assert storage.load_best(p) == {"wave": 3, "wpm": 55.5}
def test_quality_low_flag():
    assert quality.from_env(["--low"], {}) == 2
    assert quality.effective_interval(5.0, 0.08) >= 5.0
