# Textack Clean Architecture + Easy Contrib — Design Spec
Date: 2026-10-08 | Status: approved in-chat, pending file review | Approach: B Clean split Domain vs Presentation

## 1. Intent (agreed)
- Current: `main.py` 1355 lines monolith — game rules, curses rendering, audio, file I/O, word/enemy/upgrade data all mixed. No tests, minimal README, no CONTRIBUTING, no templates, no CI.
- Wanted: split into navigable `textack/` package so GitHub contributors can add words, enemies, upgrades, UI screens without reading the whole engine, plus community files that make first PRs trivial.
- Success: newcomer adds one word / enemy tweak / upgrade in <10 lines + test + docs without touching `siege` loop; `pytest` green; `python3 main.py` still plays identically.

What was said vs assumed:
- Said: "more architectured and more easy to contribute on github" → confirmed as clean arch + easy contrib.
- Assumed then confirmed: runtime stays stdlib-only (zero-install play); dev deps (pytest, ruff) allowed; `main.py` stays as thin shim.

## 2. Constraints (confirmed)
1. Runtime stdlib-only: `curses`, no `rich`/`pygame`/`websocket` at runtime. Dev-only: `pytest`, `ruff`.
2. Linux native TUI, Python 3.9+ (CI 3.9–3.13). `ESCDELAY=25`, `keypad(True)` behavior preserved.
3. Gameplay parity: damage formula, perfect window, combo, crit/double, wave scaling, boss x1.7, XP curve `xp_next*1.45+10`, ranks, 60/40/30fps quality, fail-silent sfx/storage/waifu must not change.
4. Entry: `python3 main.py` keeps working (imports `textack.__main__:main`). New canonical `python3 -m textack` also works.
5. GPL-3.0-or-later kept. No unrelated roadmap features (leaderboard, online, C engine) in this spec.

## 3. Architecture (selected: B)
Three layers, one-way dependency:

- `textack/core/` — pure logic, no `curses`, no I/O, no `time.monotonic` inside formulas. Input = plain args/dataclasses, output = plain values. Fully unit-tested.
- `textack/ui/` — curses only. Calls `core`, never implements rules. Thin screens + widgets.
- `textack/infra/` — side effects: files, subprocess audio, env/argv quality. Fail-silent, injectable paths for tests.

Rule: `core` never imports `ui`, `infra`, `curses`. `ui` may import `core` + `infra`. `infra` may import `core` types only.

Why B over A/C:
- A (light split) would leave rules tangled in rendering → tests stay impossible, contrib still scary.
- C (plugin engine abstraction, event bus, Renderer interface) is YAGNI at 1355 lines; harder for newcomers, no consumer yet for web/C port.

## 4. Components / Package map
```
main.py                      # thin shim (≤15 lines): from textack.__main__ import main; main()
textack/__init__.py          # VERSION = "1.0.00"
textack/__main__.py          # main() + curses.wrapper(game_loop), isatty guard
textack/core/
  words.py                   # TIER1/2/3, WORD_REGISTRY, pick_word(wave, rng) -> str, add_word()
  enemies.py                 # EnemyConfig dataclass, for_wave(wave) -> EnemyConfig (pure port of enemy_config)
  upgrades.py                # Stats dataclass/fresh_stats(), Upgrade dataclass, REGISTRY, roll_choices(owned,k,rng), apply(id,stats)
  combat.py                  # resolve_hit(target, buf, elapsed, combo, stats, wave, is_boss) -> HitResult(dmg,tag,wpm,speed_bonus); miss_damage(); combo_step()
  progression.py             # gain_xp(), level_thresholds, rank_for(wpm,combo)
  state.py                   # GameState dataclass (wave, stats, owned, xp, xp_next, level, combo, best_combo, shots/hits, totals)
textack/ui/
  palette.py                 # init_palette() -> dict
  widgets.py                 # safe_add(stdscr,y,x,s,attr), hp_bar_str(cur,disp,total,width)
  fx.py                      # fade_out/in_blank
  screens/
    opening.py               # show_opening(stdscr,P) -> play/howto/quit
    howto.py                 # show_howto
    upgrade.py               # show_upgrade_overlay(stdscr,P,choices,level,owned) -> index
    siege.py                 # siege(stdscr,P) — orchestrator only, delegates math to core
    outro.py                 # show_outro
textack/infra/
  storage.py                 # load_best(path)/save_best(path,wave,wpm), BEST_FILE default ~/.cache/textack/best.txt
  sfx.py                     # detect_player(), init(dir), play(stdscr,sfx,name) non-blocking fail-silent
  waifu.py                   # load_art(paths), FACES, LINES, TIPS, mood helpers
  quality.py                 # QLEVELS, from_env(argv,env) -> idx, effective_interval(base,slow)
assets/
  waifu.txt                  # moved from root (keep root copy for compat during migration, then git mv)
  sfx/*.wav                  # optional, gitignored if binary missing; docs explain
web/index.html               # KEEP at root for now (GitHub Pages source); do not move in this spec
tests/
  test_words.py              # tier gating wave1/2/3+, determinism via seeded rng
  test_enemies.py            # SCOUT≤2, RAIDER≤4, GOLEM≤6, OVERLORD>6, boss x1.7/burst/interval, scaling cap 2.6
  test_upgrades.py           # each apply() delta, max caps, roll respects owned/max
  test_combat.py             # base+speed+mult, perfect/crit/double tags, combo mult cap 10, guard probability bounds
  test_progression.py        # xp curve, rank thresholds NEWBIE→KERNEL PANIC
  test_storage.py            # tmp_path roundtrip, corrupt file → defaults
  test_widgets.py            # hp_bar_str segments, no-curses safe_add via fake stdscr
docs/
  ARCHITECTURE.md            # layer diagram + import rule + where-to-add table
  adding-content.md          # copy-paste: add word / enemy tweak / new upgrade in 5 steps
CONTRIBUTING.md              # 5-min quickstart, structure map, test/lint commands, PR checklist
.github/
  workflows/ci.yml           # ubuntu, py3.9–3.13, pip install -e .[dev], pytest -q, ruff check
  pull_request_template.md
  ISSUE_TEMPLATE/bug_report.md, feature_request.md, content_add.md
pyproject.toml               # [project] name textack, requires-python ≥3.9, no runtime deps; [dev] pytest, ruff; [tool.pytest, tool.ruff]
README.md                    # update: play, dev setup, structure map, contrib links
LICENSE                      # unchanged
tools/make_sfx.py            # noted as referenced-but-missing; stub doc or remove reference
```

Content registry pattern (example):
```python
# textack/core/upgrades.py
@dataclass(frozen=True)
class Upgrade: id: str; icon: str; cat: str; name: str; desc: str; max: int; apply: Callable[[Stats], None]
REGISTRY: dict[str, Upgrade] = {}
def register(u: Upgrade): REGISTRY[u.id] = u
```
Contributor adds 1 `register(...)` + 1 test, never touches `siege.py`.

## 5. Data flow
1. `game_loop` → `opening` → `howto?` → `siege(stdscr,P)` → `outro` on quit.
2. Inside `siege`: input bytes → `buf`; on Enter → `core.combat.resolve_hit(...)` returns `HitResult`; loop appends projectile with `pending=dmg`.
3. Miss → `core.combat.miss_damage(ecfg,wave)` + `combo_step(hit=False, guard=stats.combo_guard)`.
4. Timers: `enemy_timer >= infra.quality.effective_interval(ecfg.interval, stats.slow)` → spawn burst.
5. XP: `core.progression.gain_xp(len(target), wave, stats.xp_mult, is_boss)` → while `xp>=xp_next` → `ui.screens.upgrade` overlay → `core.upgrades.apply(pick, stats)`.
6. Wave clear / death: same as today, `infra.storage.save_best()` best-effort, `infra.sfx.play()` best-effort.
7. Render: `ui.widgets.safe_add` + `hp_bar_str` only; no rule math in render.

State ownership: `GameState` dataclass created in `siege`, passed explicitly; no module globals. `random` passed as `rng` param in core for seeded tests; `time.monotonic` stays in `ui` layer only.

## 6. Error handling
- Storage corrupt/missing → defaults `{"wave":0,"wpm":0.0}`, never crash; `save_best` mkdir best-effort try/except (as today).
- `waifu.txt` missing/empty → `WAIFU_DEFAULT`; overlong lines truncated 34×18 (as today).
- sfx binary/wav missing or `TEXTACK_SFX=off` → silent; `Popen(..., start_new_session=True)` wrapped try/except; `miss/hurt/gameover` fallback `curses.beep()` best-effort.
- Terminal too small → `safe_add` clips; `fade_*` early-return if `h<3 or w<10`; waifu panel only if `w>=102 and h>=24`.
- `curses` init failures → `init_palette` falls back 8-color; `curs_set(0)`/`bkgd` wrapped.

## 7. Testing
- Scope: all `core/` + `infra.storage` + `ui.widgets.hp_bar_str`. No curses loop tests.
- Method: `pytest`, seeded `random.Random(0)` injected; `tmp_path` for storage; fake `stdscr` (getmaxyx/addstr) for `safe_add`.
- Cases: wave gating, boss scaling, each upgrade delta + cap, combat tags/mult, XP curve, rank edges (24/25, 39/40, 54/55, 69/70, 89/90, combo 3/5/7/10), storage corrupt, hp bar fill math.
- Gates: `pytest -q` + `ruff check textack tests` in CI; `python -m compileall` smoke; manual play checklist (`python3 main.py` boot→menu→howto→siege wave1→upgrade overlay→wave2→death→retry→quit→outro).
- Non-goals: pixel-perfect TUI snapshots, audio playback asserts, perf benchmarks (keep 60fps notes as comments).

## 8. Contributor experience
- `CONTRIBUTING.md`: prerequisites (python3.9+, Linux), `pip install -e .[dev]`, `pytest -q`, `ruff check`, how to run, structure map, branch→PR flow, DCO-free (GPL note).
- `docs/adding-content.md`: 3 recipes (word, upgrade, enemy balance) each = file to edit + snippet + test to add + screenshot/log line to paste in PR.
- Templates: bug (version, terminal, repro, log), content_add (type, snippet, balance reason, test), feature; PR template (what/why, tests, manual play, screenshots for UI).
- Labels to create: `good first issue`, `content`, `bug`, `enhancement`, `docs`.
- README: keep fun tone, add Dev + Contrib sections, move install `ln -s` note, link Pages demo.
- CI must be green on first external PR; keep stdlib runtime so `git clone && python3 main.py` still zero-install.

## 9. Migration / compat
- Step 1 (this plan): pure move — copy functions verbatim into new modules, keep names/signatures, `main.py` re-exports. No behavior change, `git mv` where possible.
- Step 2: introduce `Stats`/`GameState` dataclasses + `rng` params with defaults (`rng=random`) so old call sites keep working.
- Keep root `waifu.txt` + root `index.html` in place in this spec; XDG `~/.config/textack/waifu.txt` and `~/.cache/textack/best.txt` paths unchanged. Asset relocation is explicitly out of scope to avoid breaking Pages/players.
- Out of scope: leaderboard, netplay, C engine, Windows support. `tools/make_sfx.py` (referenced in README but missing from repo): remove dangling README reference or add stub script with docs — decided during implementation, default = remove reference if file absent.

## 10. Risks / open items (decided: no TBDs left for implementation)
- Curses import on non-Linux CI → tests must never import `curses` via `core`; `ui` imports guarded in tests (skip if missing).
- `UPGRADES` lambdas with `s.update` → convert to explicit functions for pickling/docs; keep behavior identical.
- Large `siege()` (~700 lines) stays large initially; follow-up split (input/update/render helpers) allowed but not required for parity.
- `index.html` move may break Pages URL; confirm Pages source setting before moving.

## 11. Acceptance
- [ ] `python3 main.py` and `python3 -m textack` boot identically; wave1→upgrade→wave2→death→retry→quit→outro manual pass.
- [ ] `pytest -q` green, `ruff check` clean on py3.9–3.13 CI.
- [ ] New contributor can add upgrade/word by editing 1 registry file + 1 test, following `docs/adding-content.md` without help.
- [ ] `CONTRIBUTING.md`, templates, CI, `ARCHITECTURE.md`, `pyproject.toml` present; README links them.
