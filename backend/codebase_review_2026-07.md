# Codebase Review — Areas for Improvement

_Reviewed: 2026-07-08. Scope: `backend/` (FastAPI + Celery + SQLModel) and `frontend/src/` (React/Redux). Excludes `.venv/`, generated files, and the scratch content under `docs/`._

This is a well-structured project: the Celery fork-per-task isolation, the AI client/failover abstraction, the institution-ownership guards, and the process-boundary security model are all thoughtfully done and heavily commented. The findings below are improvements, ordered by priority. Nothing here is on fire.

---

## Priority 1 — Security

### 1.1 Full JWT tokens written to logs and stdout
`backend/routes/auth/auth_router.py:64-65` logs and `print()`s the complete team token on every login:
```python
logger.info(f"Generated token for team {credentials.name}: {team_token}")
print(f"Generated token for team {credentials.name}: {team_token}")
```
`auth_core.py:83` also logs the first 20 chars of every bearer token on every authenticated request. Tokens are bearer credentials valid for hours (30 days for agents). Anyone with log access can replay them. **Fix:** delete these lines; never log token material. The `print()` also bypasses logging config entirely and writes to the gunicorn access log.

### 1.2 CORS `allow_origins=["*"]` with `allow_credentials=True`
`backend/api.py:121-127`. This combination is rejected by browsers per the Fetch spec and signals an over-permissive config. Auth is via `Authorization` header (not cookies), so `allow_credentials` isn't even needed. **Fix:** set an explicit allowlist of frontend origins (from `FRONTEND_URL`), and drop `allow_credentials` unless cookies are introduced.

### 1.3 Internal exception detail leaked to clients
Almost every route does `except Exception as e: return ...(message=f"...: {str(e)}")` (17 handlers in `user_router.py` alone). This returns raw exception strings — DB errors, stack detail, internal paths — to unauthenticated or low-privilege callers. **Fix:** log the exception server-side, return a generic message to the client. Reserve detailed messages for known, safe exception types.

### 1.4 AST safety check is a name-only denylist
`backend/routes/user/code_validation.py` blocks a fixed list of names (`eval`, `exec`, `open`, `os`, …) but does not stop `getattr(__builtins__, "ev"+"al")`, `().__class__.__mro__`, `__subclasses__()`, or `object.__globals__` traversal. `base_game.add_player` then `exec`s the code with **full `__builtins__`** in the namespace (`base_game.py:162-179`). The real containment is the worker process/container isolation (500MB, 50 pids, no swap, fork-per-task) — which is genuinely solid — but the AST layer gives a false sense of a second barrier it doesn't provide. **Fix:** either document the AST check as advisory-only (defense against accidents, not attackers), or harden it: block `__`-dunder attribute access and `getattr`/`setattr`, and exec with a restricted `__builtins__`.

### 1.5 Every role check implicitly trusts the service role
`verify_role` in `auth_core.py:46` appends `ROLE_SERVICE` to the allowed set for **every** endpoint. Service tokens are minted with a 365-day lifetime (`auth_config.py:29`). One leaked service token is a skeleton key to all roles for a year. `create_service_token` appears unused in the current code — if service-to-service calls are gone, remove the role and the blanket allowance entirely.

### 1.6 Inconsistent / weak password policy
The 8-char minimum is enforced only on `invoice_signup` (`payments_router.py:319`). The card `institution_signup`, admin `create_institution`, team creation, and school signup enforce nothing. Committed defaults (`admin/admin`, `institution/institution` in `.env` and `init_db.py:88`) are fine for dev but are a foot-gun if a deploy ever ships without overriding `ADMIN_PASSWORD`/`INSTITUTION_PASSWORD`. **Fix:** centralize a password validator; assert the prod secrets differ from defaults at startup.

---

## Priority 2 — Correctness & Robustness

### 2.1 Naive/aware datetime mixing, and deprecated `datetime.utcnow()` FIXED
The code repeatedly patches timezone mismatches at read time:
```python
if expiry_date.tzinfo is None:
    expiry_date = AUSTRALIA_SYDNEY_TZ.localize(expiry_date)
```
(appears in `user_db.py`, `auth_db.py`, and elsewhere). Meanwhile model defaults use `datetime.utcnow` (`db_models.py:167,256,…`) — a **naive** UTC value, and **deprecated in Python 3.14** (this project targets 3.14). Mixing Sydney-aware writes with naive-UTC defaults is why the localize-guards exist. **Fix:** standardize on aware UTC everywhere (`datetime.now(timezone.utc)`), store timezone-aware, convert to Sydney only at the presentation layer. Replace all `datetime.utcnow`.

### 2.2 `Team.name` is globally unique — blocks name reuse across institutions FIXED
`db_models.py:149`: `name: str = Field(unique=True, index=True)` plus a separate `UniqueConstraint("name", "league_id")`. The global unique constraint is the binding one, so two different institutions can never have a team called "Team A". This is almost certainly unintended for a multi-tenant platform and will surface as confusing "team already exists" errors. **Fix:** drop the column-level `unique=True`; keep the composite constraint (scope it to institution/league). Requires a migration.

**Resolution:** dropped the column-level `unique=True` (the index stays, non-unique) and scoped uniqueness to `(name, institution_id)` — a name is a team's stable identity within its institution as it moves between leagues — keeping `(name, league_id)` as a secondary guard for teams whose league has no institution (`institution_id` NULL, which Postgres unique treats as distinct). Migration `2026-07-08_team_name_scope.sql`. Downstream name lookups that assumed global uniqueness were fixed: team login now matches on name + password across all teams sharing a name (was a crashing `.one_or_none()`); simulation-result attribution is scoped by `league_id`; the school-team counter and signup pre-check are scoped to the institution.

### 2.3 Boot-time auto-init races across gunicorn workers FIXED
`check_database_status()` runs in the FastAPI lifespan (`api.py:104`), and prod runs 3 gunicorn workers — so 3 processes may concurrently detect an empty DB and call `initialize_database()` / `create_all`. The test path is guarded, but production isn't. **Fix:** move schema init to a one-shot pre-start command (a deploy hook or entrypoint), not the request-serving process lifespan. At minimum, take a Postgres advisory lock around init.

---

## Priority 3 — Duplication & Dead Code

### 3.1 `AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")` redefined ~10 times RESOLVED
Across `auth_core`, `auth_db`, `user_db`, `admin_db`, `institution_db`, `demo_db`, `demo_router`, `conftest`, etc. **Fix:** define once in a shared module (e.g. `backend/config.py`) and import.

### 3.2 Duplicated S3 client construction
`backend/routes/support/support_s3.py:_build_client` and `backend/routes/admin/admin_backup.py:_get_s3_client` are near-identical boto3-client factories with the same credential-check logic. Consolidate into one S3 helper module.

### 3.3 Simulation-result formatting duplicated FIXED
`utils.process_simulation_results` exists and is used in several places, but `user_db.get_published_result` (lines 153-183) re-implements the same `total_points`/`table`/`feedback` assembly inline. `utils.transform_result` overlaps too and appears unused. **Fix:** route all result shaping through one function; delete `transform_result` if dead.

### 3.4 Dev/POC/benchmark modules ship in the production image
`Dockerfile` does `COPY . /agent_games/`, so `backend/threading_test.py`, `backend/celery_easy/` (a Celery POC with its own separate app), `backend/tests/benchmark_greedy_pig.py`, `backend/agent_script.py` (a sample client with a hardcoded prod URL), and `backend/server_stress_test/` all land in prod. **Fix:** move these out of the deployed package (a top-level `dev/` or `scripts/`), or exclude via `.dockerignore`. `agent_script.py` in particular reads like a sample that belongs in `docs/`.

### 3.5 `get_all_leagues` imported but unused
`user_router.py:34` imports `get_all_leagues`; the leagues endpoint uses `get_leagues_for_user` instead. Minor — remove the import (and the function if nothing else references it).

### 3.6 `docs/` is a scratch directory, not documentation
It holds `tmp_l4_*.py`, base64 validation blobs, personal emails (`email_*.md`), and an `add_swap.sh`. Real docs (game_instructions, tutorials) are mixed in. Consider splitting genuine docs from scratch/working files so the folder is trustworthy.

---

## Priority 4 — API Contract & Performance

### 4.1 Business errors return HTTP 200 with a status field
Most failures return `ErrorResponseModel(status="error", …)` at HTTP 200. Auth uses yet another string (`status="failed"` in `auth_router.py`). So the frontend can't rely on HTTP status and must inspect two different string values. Meanwhile `get_current_user` correctly raises `HTTPException(401)`. **Fix:** pick one convention — ideally proper HTTP status codes (400/403/404/409) plus a consistent body — and standardize the `status` string. `ErrorResponseModel` also lacks a `data` field while callers sometimes want one.

### 4.2 N+1 query patterns
- `user_db.get_latest_submissions_for_league` issues one query per team in a loop (lines 291-302).
- `get_all_published_results` (lines 188-205) loads every league, then walks `league.simulation_results` and each `result.team` in Python — lazy-loaded per row.
These are fine at classroom scale but will degrade as leagues/teams grow. **Fix:** use joins / `selectinload`, or a single grouped query.

### 4.3 Missing indexes on filtered FKs
`SimulationResultItem.team_id` and `SimulationResult.league_id` are frequent filter/join targets (`institution_db`, `admin_db`) but aren't indexed in `db_models.py`. Add indexes via migration.

---

## Priority 5 — Minor / Hygiene

- **`find_project_root` uses a mutable default argument** evaluated at import (`config.py:3`). Works today, but it's the classic Python trap; make it a module-level constant instead.
- **`verify_password` on agent teams** returns `False` for null hashes (good), but agent teams authenticate only via API key — the password path on `Team` is effectively dead weight worth a comment or removal.
- **Frontend token in `sessionStorage`** (`store.js:19`) is XSS-exposed. Acceptable for a bearer-header SPA, but worth a conscious note; the whole Redux state (including the token) is serialized there on every action.
- **`ResponseModel.data` is `Optional[dict]`** but several endpoints put lists or scalars in `data` (e.g. token dicts, arrays) — the type annotation is looser than reality; tighten or document.
- **No linter/formatter config** committed for either side (no ruff/black/eslint config found). Adding one would catch several of the above (unused imports, bare excepts) automatically.
- **`hint_available` determinism** (`hint_service.py:68`) carries a hand-written warning that it must stay deterministic across resubmits. That invariant is fragile and untested-looking; a targeted test would lock it down.

---

## Suggested order of attack

1. Strip token logging (1.1) and tighten CORS (1.2) — minutes, real exposure.
2. Stop leaking exception strings (1.3) — one shared error helper.
3. Fix the datetime standardization (2.1) and the `Team.name` constraint (2.2) — both need migrations, both are latent bugs.
4. De-duplicate the timezone constant and S3 clients (3.1, 3.2), remove dev modules from the image (3.4).
5. Add a linter to prevent regressions.
