# Tests

Unit tests for the `gas_useage` package. Run with:

```bash
uv run pytest
```

## Conventions

- **GIVEN-WHEN-THEN comments are required in every test.** Each test must
  include `# GIVEN ...`, `# WHEN ...`, `# THEN ...` comments naming the
  precondition, action, and observable outcome. Keep them up to date with
  the assertions.

- **File names mirror source modules.** `tests/test_<module>.py` for each
  `src/gas_useage/<module>.py` we cover. Module-less helpers (Protocol
  fakes, row factories) live in `conftest.py`.

- **Group with `class TestX`** when there are four or more tests for the
  same function. Single-function tests can be top-level.

- **No real Supabase access.** Tests must not make network calls. Use
  `monkeypatch` to replace `get_db` with a `MagicMock`, or use the
  `FakeDataSource` stub in `conftest.py`.

- **Streamlit UI testing via monkeypatch.** Streamlit-coupled functions
  (`check_password`, `render_cost_chart`, etc.) are tested by replacing
  `st.session_state`, `st.sidebar`, `st.secrets`, and `st.rerun` with
  plain dicts/mocks. Do not call `streamlit run` or render real UI.

- **Bypass `@st.cache_data` with `__wrapped__`**. Cached functions expose
  their unwrapped body as `fn.__wrapped__`. Use this in tests so the cache
  layer is skipped and `monkeypatch` side-effects are visible.

- **Freeze the clock for date arithmetic.** Patch `gas_useage.seasons.datetime`
  with a `datetime` subclass that overrides `now()`. Subclassing preserves
  `strptime` and other classmethods the code under test relies on. See
  `_freeze_seasons_clock` in `test_seasons.py`.

- **Pure functions only for transforms.** Test the pandas transforms and
  pure helpers directly — no mocking required.

## Coverage policy

- Floor: `fail_under = 90` (configured in `pyproject.toml`).
- Omitted from measurement: `__init__.py`, `__main__.py`, `app.py`,
  `charts.py`, `db.py`. The Streamlit entry point and Altair chart builders
  are excluded; their behaviour is covered indirectly through integration
  or visual testing.

## Fixtures

- `make_gas_row(...)` — row factory matching the `gas_reading_differences`
  view shape. Keyword args override defaults.
- `two_season_df` — pandas DataFrame with two seasons of readings
  (`2023/2024` ending at `running_sum=300.0`, `2024/2025` from a fresh
  baseline).
- `DataSource` — `Protocol` matching `Sbase.query`.
- `FakeDataSource(tables=...)` — in-memory stub returning canned rows by
  table name.
