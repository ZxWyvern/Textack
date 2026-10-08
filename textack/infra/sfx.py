from pathlib import Path
def detect_player():
    import shutil
    for b in ("paplay", "aplay", "play"):
        if shutil.which(b): return [b]
    if shutil.which("mpv"): return ["mpv", "--no-video", "--really-quiet"]
    if shutil.which("ffplay"): return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    return []
def init(base_dir=None):
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent / "sfx"
    import os
    return {"dir": base, "bin": detect_player(), "on": os.environ.get("TEXTACK_SFX", "on").lower() not in ("0", "off", "no")}
def play(stdscr, sfx, name):
    if not sfx["on"]: return
    try:
        import subprocess
        f = sfx["dir"] / f"{name}.wav"
        if sfx["bin"] and f.exists():
            subprocess.Popen([*sfx["bin"], str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            return
        if name in ("miss", "hurt", "gameover"):
            try:
                import curses; curses.beep()
            except Exception: pass
    except Exception: pass
