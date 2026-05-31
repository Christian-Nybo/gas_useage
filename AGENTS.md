# AI Agent Guide - gas_useage

**Repository:** [Christian-Nybo/gas_useage](https://github.com/Christian-Nybo/gas_useage) - Streamlit dashboard for household gas usage tracking, backed by Supabase.

The instructions in this file are optimized and intended for AGENTS.
For a human audience: start at [README.md](README.md).

**Dual-audience structure:**
- `AGENTS.md` (this file) = agent task execution (condensed)
- `README.md` = human-oriented project documentation
- `pyproject.toml` = project metadata, deps, lint/format config (source of truth)

**BEFORE RESPONDING:**
- User asking for personal understanding (how/why/what/where do *I* X)? -> Read `README.md`. Give the human-centric answer.
- User requesting action? -> Use this file plus the linked sections.
- User asking how the agent works (how/why/where/what do *you* X)? -> Give the agent-centric answer.

**Don't load everything at once.** Use this index to find what you need (progressive loading).

**Do full discovery first.** Don't create or edit before discovery. Read `pyproject.toml` and `src/gas_useage/*.py` before changing dependencies or source layout.

---

## I'm Working On...

### Running the app locally
- Install deps: `uv sync`
- Launch: `uv run streamlit run src/gas_useage/app.py`
- The app blocks the terminal (HTTP server). Do not invoke it from an
  autonomous workflow that expects exit-on-completion -- use `uv run python -c
  "from gas_useage.db import Sbase"` for import-only verification.

### Adding or upgrading dependencies
- Runtime: `uv add '<pkg>~=<version>'` (use `~=` for compat pins)
- Dev (linters, type checkers, test runners): `uv add --dev '<pkg>'`
- After any add/remove, commit both `pyproject.toml` and `uv.lock`.
- Never edit `pyproject.toml` `[project].dependencies` by hand -- let `uv` write it.

### Linting and formatting
- Lint: `uv run ruff check` (must exit 0 before commit)
- Auto-fix: `uv run ruff check --fix`
- Format: `uv run ruff format src`
- Format check (CI-friendly): `uv run ruff format --check src`
- Config lives in `pyproject.toml` under `[tool.ruff]`. Selected rules:
  `E, W, F, I, B, UP, ANN201, ANN202`. `E501` (line length) is ignored;
  `line-length = 100`.

### Editing source code
- All source lives under `src/gas_useage/`. Use absolute imports
  (`from gas_useage.db import Sbase`), never relative-from-parent hacks
  (`sys.path.append(...)`).
- The package is installed editable via `uv sync` -- changes take effect on
  next interpreter start, no reinstall needed.
- Public functions and methods must have a return-type annotation (ANN201/202
  are enforced by ruff). Parameter annotations are reviewer-enforced, not
  ruff-enforced.

### Secrets and credentials
- Streamlit reads from `.streamlit/secrets.toml` (gitignored).
- Never commit secrets. Never echo them in logs or test output.
- The `Sbase` class in `src/gas_useage/db.py` pulls
  `[supabase]` and `[supabase_auth]` sections at module-import time --
  importing `gas_useage.app` without secrets present will raise
  `StreamlitSecretNotFoundError`. Test imports against `gas_useage.db` if you
  need to avoid that side effect.

### Git workflow
- This project uses GitHub (not GitLab). Use `gh` for PRs and issue work.
- Default development branch: `development`. Pull requests target
  `development` unless the user says otherwise.
- Feature branches follow `sub/<issue-number>-<short-slug>` for sub-issues of
  the codebase-improvements epic.
- Commit-message style is short imperative ("add X", "fix Y", "update Z") --
  inspect `git log` before composing a message.

---

## Tool Selection

### Read vs Glob vs Grep

**Use Read when:**
- You know exact file paths (< 5 files)
- You need full file content with context

**Use Glob when:**
- You know the file pattern but not exact locations: `src/**/*.py`

**Use Grep when:**
- Searching for content/patterns inside files
- Existence checks: e.g. `rg 'sys\.path' src/` to confirm no leakage

---

## Critical Prohibitions

**BEFORE executing these operations, check this section.**

### Package management
- **Never edit `pyproject.toml` `[project].dependencies` by hand.** Use
  `uv add` / `uv remove`.
- **Never commit a stale `uv.lock`.** Re-run `uv sync` after pulling.
- **Never use `pip install` in this repo.** `uv` is the only supported
  installer. There is no `requirements.txt`.

### Source layout
- **Never re-introduce `sys.path.append(...)` hacks.** The `src/` layout +
  editable install make them unnecessary.
- **Never move source files out of `src/gas_useage/`.** Hatchling is configured
  to package exactly that directory.

### Secrets
- **Never commit `.streamlit/secrets.toml`, `.env`, or any file containing
  Supabase credentials.** `.gitignore` blocks the common cases; double-check
  `git status` before commit.
- **Never log secret values.** When debugging, log the secret *keys* present
  in `st.secrets`, not the values.

### Git
- **Never force-push** to `main` or `development`.
- **Never `git push --no-verify`** unless the user explicitly requests it.
- **Never commit `__pycache__/`, `.venv/`, `.idea/`, or `.DS_Store`.**

---

## Repository

- **Repo:** https://github.com/Christian-Nybo/gas_useage
- **Default branch (PR target):** `development`
- **Issue tracker:** GitHub Issues (use `gh issue ...`)
- **CLI:** `gh` for PRs, issues, releases (no `glab` here -- this is GitHub).
