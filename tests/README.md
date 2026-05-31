# Tests

Unit tests for the `gas_useage` package. Run with `uv run pytest`.

## Conventions

- **GIVEN-WHEN-THEN comments are required in every test.** Each test must
  include `# GIVEN ...`, `# WHEN ...`, `# THEN ...` comments naming the
  precondition, action, and observable outcome. They are the test's
  contract — keep them up to date with the assertions.

- **File names mirror source modules.** `tests/test_<module>.py` for each
  `src/gas_useage/<module>.py` we cover. Module-less helpers (Protocol
  fakes, row factories) live in `conftest.py`.

- **Group with `class TestX`** when there are four or more tests for the
  same function. Single-function tests can be top-level.

- **No real Supabase access.** Tests must not import the `supabase` SDK,
  read `st.secrets`, or make any network call. The `DataSource` Protocol
  + `FakeDataSource` stub in `conftest.py` cover the data-access seam.

- **No Streamlit.** Tests must not call `streamlit run`, render UI, or
  exercise `st.metric` / `st.cache_data` / `st.sidebar` behaviour. The
  Streamlit-coupled modules (`app.py`, `data.py`, `db.py`, `charts.py`)
  are excluded from coverage.

- **Freeze the clock for date arithmetic.** Helpers in `seasons.py` call
  `datetime.now()`. Tests patch `gas_useage.seasons.datetime` with a
  `datetime` subclass that overrides `now()`. Subclassing (not mocking)
  preserves `strptime` and other classmethods the code under test relies
  on. See `_freeze_seasons_clock` in `test_seasons.py` and `test_usage.py`.

- **Pure functions only.** Test the pandas transforms and pure helpers.
  UI rendering and caching behaviour are deliberately out of scope.

## Coverage policy

- Initial floor: `fail_under = 55` (configured in `pyproject.toml`).
- Omitted: `__init__.py`, `__main__.py`, `app.py`, `data.py`, `db.py`,
  `charts.py`. These are either the Streamlit entry, the cached data
  layer, the supabase wrapper, or the chart-building module that is
  out of scope for this issue.
- Long-term target: 75% once refactor work surfaces more pure functions.

## Fixtures

- `make_gas_row(...)` — row factory matching the `gas_reading_differences`
  view shape. Keyword args override defaults.
- `two_season_df` — pandas DataFrame with two seasons of readings
  (`2023/2024` ending at `running_sum=300.0`, `2024/2025` from a fresh
  baseline).
- `DataSource` — `Protocol` matching `Sbase.query`.
- `FakeDataSource(tables=...)` — in-memory stub returning canned rows by
  table name, or `None` for missing tables.
