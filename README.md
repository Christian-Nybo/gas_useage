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

Streamlit reads credentials from `.streamlit/secrets.toml` (gitignored). Create
the file at the repo root with the following sections:

```toml
[supabase]
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<anon-or-service-role-key>"

[supabase_auth]
USER_EMAIL = "<account-email>"
USER_PASSWORD = "<account-password>"
```

Never commit this file. The `.gitignore` excludes `.streamlit/secrets.toml`
and common secret-bearing files (`.env`, etc.).

## Project structure

```
gas_useage/
├── src/gas_useage/
│   ├── __init__.py
│   ├── app.py           # Streamlit entry point + UI/business logic
│   └── db.py            # Supabase client wrapper (Sbase)
├── pyproject.toml       # project metadata, deps, ruff config
├── uv.lock              # pinned resolution (commit this)
├── .gitignore
├── AGENTS.md            # AI-agent guidance (dual-audience hub)
└── README.md
```
