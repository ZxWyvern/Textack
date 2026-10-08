# textack/ui/widgets.py
def safe_add(stdscr, y, x, s, attr=0):
    import curses
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or not s:
        return
    if x >= w or x + len(s) <= 0:
        return
    if x < 0:
        s = s[-x:]
        x = 0
    if x + len(s) >= w:
        s = s[: w - x - 1]
        if not s:
            return
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass

def hp_bar_str(cur, disp, total, width):
    total = max(1, total)
    pa = max(0, min(1, cur / total))
    pd = max(0, min(1, disp / total))
    fa = int(width * pa)
    fd = int(width * pd)
    # optimasi: build via list, bukan += per char
    out = ["#"] * fa + ["="] * max(0, fd - fa) + ["-"] * max(0, width - max(fa, fd))
    return f"[{''.join(out)}] {int(cur)}/{total}"
