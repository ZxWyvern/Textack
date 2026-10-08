import os
import sys


def main():
    if not sys.stdin.isatty():
        print("Jalankan di terminal asli: textack")
        sys.exit(1)
    os.environ.setdefault("ESCDELAY", "25")
    try:
        import curses

        from textack.ui.screens.loop import game_loop
        curses.wrapper(game_loop)
    except KeyboardInterrupt:
        pass
    print("made by rewsaqy • 2026")


if __name__ == "__main__":
    main()
