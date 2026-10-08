from pathlib import Path
DEFAULT = ["     ✿   ♡   ✿     ", '      .-"""-.      ', "     / .--. \\     ", "    | (o)(o) |    ", "     \\  __  /     ", "     _| || |_     ", "    / | || | \\    ", "   |  | || |  |   ", "   |  \\_||_/  |   ", "    \\   __   /    ", "     |______|     ", "    _|      |_    "]
FACES = {"idle": "(・‿・)", "happy": "(≧▽≦)", "sad": "(>_<)", "hurt": "(T_T)", "excited": "(☆▽☆)"}
LINES = {"happy": ["sugoi! kena!", "nice shot, senpai!", "combo naik!"], "sad": ["baka... miss!", "fokus, senpai!", "combo reset..."], "hurt": ["itai! lindungi aku!", "benteng kita!", "kyaa!"], "excited": ["level up! makin kuat!", "power naik!", "yosha!"]}
TIPS = ["ketik cepat = damage", "PERFECT < jendela emas", "combo = crit ganda", "F2 quality • F3 suara", "combo guard selamatkanmu"]
def load_art(extra_paths=None):
    cands = []
    try: cands.append(Path(__file__).resolve().parent.parent.parent / "waifu.txt")
    except Exception: pass
    cands.append(Path.home() / ".config" / "textack" / "waifu.txt")
    for p in (extra_paths or []): cands.insert(0, Path(p))
    for p in cands:
        try:
            if p.exists():
                lines = [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if not ln.startswith("#")]
                lines = [ln for ln in lines if ln.strip()]
                if lines: return [ln[:34] for ln in lines[:18]]
        except Exception: pass
    return list(DEFAULT)
