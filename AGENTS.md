# AGENTS.md - notes for coding agents

## Project

`trickkiste` is a grab bag of small Python helpers (3.10+), managed with
`uv`. It has *no* runtime dependencies, keep it that way: Checkmk's system
tests `pip install` / `pip uninstall` it as a sample wheel, and uninstall
leaves dependencies behind (a date library was dropped for that, use
`datetime.fromtimestamp(ts).astimezone()` for local time). `rich` and
`textual` are dev-only on purpose (see `pyproject.toml`), consumers of the
TUI parts must depend on them themselves.

| Module              | Content                                                 |
|---------------------|---------------------------------------------------------|
| `misc.py`           | durations/dates (`dur_str`, `parse_age`, ...), string   |
|                     | splitting, async decorators (`async_retry`, ...)        |
| `logging_helper.py` | `setup_logging`, rich-markup log format, log filters,   |
|                     | `set_log_levels` (pattern-matched argument forms)       |
| `base_tui_app.py`   | `TuiBaseApp` (Textual app with a log pane),             |
|                     | `RichLogHandler`, `HeatBar`                             |
| `tui_widgets.py`    | splitters, `StatusBar`, clipboard, `clean_line`,        |
|                     | `scanner`, `ConfirmScreen`, alerting log handler,       |
|                     | a tool's frame (`tool_frame`, `FramedApp`: header,      |
|                     | feedback button + `FeedbackScreen`), `package_version`  |
| `std_suppress.py`   | `suppress <timeout> <cmd...>` console script            |
| `examples/`         | `fancytui.py` showcases every TUI feature (keys in its  |
|                     | docstring) - extend it when adding widgets              |

## Checks

Headless check of the example (Textual pilot, no terminal needed):
`app.run_test(size=(120, 40))`, `pilot.press(...)`, `app.save_screenshot()`.

    uv run pre-commit run --all-files     # ruff, mypy, doctests, unit tests
    uv run pytest -m unit                 # tests in test/
    uv run pytest --doctest-modules trickkiste

- `test/` is excluded from ruff lint and mypy (pre-commit config), but
  not from `ruff format`.
- Tests are plain sync functions; async code runs via `asyncio.run(...)`
  and Textual via `App.run_test()` inside it - no pytest-asyncio.
- Every test module sets `pytestmark = pytest.mark.unit`.
- `conftest.py` (repo root) pins `TZ=Europe/Berlin` + `time.tzset()`,
  doctests print local times. Keep it when adding date doctests.
- Logging is global state: tests touching it save/restore root handlers
  and levels in fixtures. `logging.addLevelName` leaks between tests.

## Pitfalls (learned the hard way)

- Markup escaping of log records happens exactly once, in
  `markup_escape_filter`. `RichLogHandler` adds it in `__init__`;
  `Filterer.addFilter` ignores duplicates, so `setup_logging_handler`
  adding it again is harmless. Never escape in `emit` again (`\[red]`).
- Log filters must survive non-str `record.msg` (`log.info(42)`) and
  unknown level names - an exception in a filter propagates out of the
  caller's logging call.
- Filters mutate the shared `LogRecord` (msg, name, funcName): every later
  handler sees the changed record.
- `std_suppress.print_after` gets one `None` per producer stream; it must
  wait for all of them.
- `if x := f() and g(x)` binds `f() and g(x)` - parenthesise the walrus.
- Ruff has no `# ruff: <rule>` comment directive (RUF103).
- Exception and stack text are no rich markup: both `FluidRichHandler` and
  `RichLogHandler` format `without_exc(record)` as markup and print
  `exc_text(...)` as plain `Text`. Feeding a traceback containing `[/]` to
  rich raises `MarkupError`. Errors in `emit` go to `handleError`.
- Committing: pre-commit refuses to run (and `git commit` fails) while
  `.pre-commit-config.yaml` has unstaged changes - commit it first or
  park it. Hooks call `uv run` without `--frozen` on the stashed tree, so
  they lint with the ruff of the *committed* `uv.lock`: a `noqa` for a rule
  only a newer ruff knows fails as RUF100 until the lock update is in.
- `setup_logging_handler` keeps its positional parameters on purpose
  (external callers), hence `noqa: PLR0917`.
- `uv.lock` updates may bring new ruff rules (RUF036, CPY001, PLR0917
  came with ruff 0.17) and rich behaviour changes (`Text.from_ansi` now
  keeps `\n`).
