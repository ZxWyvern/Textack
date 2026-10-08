from pathlib import Path
DEFAULT_BEST = Path.home() / ".cache" / "textack" / "best.txt"
def load_best(path=DEFAULT_BEST):
    try:
        t = Path(path).read_text().strip().split()
        return {"wave": int(t[0]), "wpm": float(t[1])} if len(t) >= 2 else {"wave": 0, "wpm": 0.0}
    except Exception:
        return {"wave": 0, "wpm": 0.0}
def save_best(path, wave, wpm):
    try:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        cur = load_best(path)
        if wave > cur["wave"] or (wave == cur["wave"] and wpm > cur["wpm"]):
            path.write_text(f"{wave} {wpm:.1f}\n")
    except Exception:
        pass
