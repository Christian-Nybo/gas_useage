# gas_useage

Streamlit dashboard for tracking household gas usage, backed by a Supabase database.

## Overview

`gas_useage` is a single-page Streamlit application that visualizes gas meter
readings stored in Supabase. It surfaces per-season usage, running totals, a
last-season overlay for year-over-year comparison, and a price/cost view. New
gas readings can be added directly from the sidebar.

## Prerequisites

- Python 3.12 (managed automatically by `uv`)
- [uv](https://docs.astral.sh/uv/) (`brew install uv` on macOS)
- A Supabase project with the schema and credentials configured (see
  *Environment / secrets* below)

## Setup

Clone the repo and let `uv` create the virtual environment and install
dependencies from `uv.lock`:

```bash
git clone https://github.com/Christian-Nybo/gas_useage.git
cd gas_useage
uv sync
```

`uv sync` performs an editable install of the `gas_useage` package, so the
`from gas_useage...` imports work without manual `PYTHONPATH` configuration.

## Run locally

```bash
uv run streamlit run src/gas_useage/app.py
```

The Streamlit dev server opens at http://localhost:8501 by default.

## Environment / secrets

Streamlit reads credentials from `.streamlit/secrets.toml` (gitignored). Copy
`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in real
values:

```toml
[supabase]
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<anon-public-key>"

[supabase_auth]
USER_EMAIL = "<service-account-email>"
USER_PASSWORD = "<service-account-password>"

[auth]
password = "<your-strong-dashboard-password>"
```

| Section | Purpose |
|---------|---------|
| `[supabase]` | Supabase project URL and anon/public API key (from your project's API settings) |
| `[supabase_auth]` | Supabase user account the app signs in as to query and write data |
| `[auth]` | Password for the owner login form in the sidebar (gates the "add reading" input) |

Never commit this file. The `.gitignore` excludes `.streamlit/secrets.toml`
and common secret-bearing files (`.env`, etc.).

### Owner login

The sidebar shows a **Password** field and **Login** button. Enter the value
set in `[auth] password` to unlock the gas reading input. After three failed
attempts the form is locked until the page is refreshed. Click **Logout** to
end the authenticated session.

## Project structure

```
gas_useage/
├── src/gas_useage/
│   ├── __init__.py
│   ├── app.py              # Streamlit entry point + UI wiring
│   ├── charts.py           # Altair chart builders (usage, cost)
│   ├── data.py             # Cached data accessors / write helpers
│   ├── db.py               # Supabase client wrapper (Sbase)
│   ├── seasons.py          # Season parsing + day-of-season math
│   ├── settings.py         # Pydantic settings (tariffs, etc.)
│   └── transforms.py       # Pure pandas transforms used by the dashboard
├── tests/                  # pytest suite (unit tests for transforms/seasons/db)
├── .github/workflows/      # CI pipeline (ruff + pytest + coverage)
├── .pre-commit-config.yaml # ruff lint/format pre-commit hooks
├── pyproject.toml          # project metadata, deps, ruff config
├── uv.lock                 # pinned resolution (commit this)
├── .gitignore
├── AGENTS.md               # AI-agent guidance (dual-audience hub)
└── README.md
```

## Deployment

**Target:** [Streamlit Community Cloud](https://share.streamlit.io) — zero infra, GitHub-native auto-deploy, free for public repos, and native support for `st.secrets` (so the existing Supabase client wrapper works as-is).

**Public URL:** `https://<app-name>.streamlit.app` *(owner to fill in after the first deploy)*

### One-time setup (manual, performed by the repo owner)

These steps are UI-driven and cannot be automated from this repository:

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns the repo.
2. Click **New app** and select:
   - **Repository:** `Christian-Nybo/gas_useage`
   - **Branch:** `main` (production branch — `development` is for CI gating only)
   - **Main file path:** `src/gas_useage/app.py`
   - **Python version:** `3.12`
3. Open **Advanced settings → Secrets** and paste the contents of your local
   `.streamlit/secrets.toml` (all three blocks: `[supabase]`, `[supabase_auth]`,
   and `[auth]` — documented in *Environment / secrets* above). Streamlit Cloud
   stores these securely; they are never read from the repo.
4. Click **Deploy**. Subsequent pushes to `main` auto-deploy.
5. Copy the resulting `*.streamlit.app` URL back into this README, replacing
   the placeholder above.

### Branch protection (manual follow-up)

CI runs on every push/PR to `main` and `development`, but enforcement of
"green CI required to merge" must be configured in the GitHub repo settings —
it cannot be set from code. The repo owner should:

1. Go to **Settings → Branches → Add branch protection rule** in the GitHub UI.
2. Add a rule for `main` and another for `development`, each requiring:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging** → select the `ci` job
   - **Require branches to be up to date before merging**

Combined with auto-deploy from `main`, the resulting flow is:
`feature → development (CI) → PR → main (CI + auto-deploy)`.

### Updating secrets

Edit them in the Streamlit Cloud dashboard's **Secrets** panel; the app
restarts automatically. Do not commit `.streamlit/secrets.toml`.


## Maintenance

### Add a new season

Format of the season are `YYYY/YYYY` where the first `YYYY` are the current year and the following `YYYY` are next year.
A new season has to be set beforehand (Before the `XXXX-07-01`)

1. Insert a new row with that in the 'gas_season' table. <br>
   Add the following into the database row: 
   1. season_name: `YYYY/YYYY`
   2. start: The last day of the old year at: 00:00:00
   3. end: The last day of the new year at: 23:59:59
2. Reload the Streamlit app.
3. Add a gas reading that will display the new year. 