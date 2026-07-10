BACKEND — THE RESPONSE CONTRACT

Success transport
FROM: HTTP 200 always
TO: HTTP 200 (data) — status line is the signal

Success body
FROM: ResponseModel(status="success", message=…, data={…})
TO: the payload unwrapped — {…} at top level

Success status field
FROM: "success"
TO: None (not present)

Success message field
FROM: always present
TO: kept only where it's the actual result (delete/toggle/clear/backup ⇒ message), dropped where data is the result

Error transport
FROM: HTTP 200
TO: 401/403/404/409 (real HTTP status codes)

Error body
FROM: ErrorResponseModel(status="error", message=…)
TO: FastAPI's default error shape

Unexpected error
FROM: caught by except Exception
TO: uncaught → 500 (visible to monitoring)

response_model=
FROM: ResponseModel on every route
TO: removed (raw dict) — see note below


BACKEND — WHERE THE ERROR CODE IS DECIDED

Three tiers, in order of preference:

1. Domain exception + one central handler in api.py. The DB/domain exception is defined once; @app.exception_handler(...) maps type → code once. This is the default and works without try/except.
   - InvalidCredentialsError → 401, InstitutionNotFoundError → 409, AgentTeamError → 400, SupportError → 404.
   - Rule for adding one: verify the exception is raised only by code the target router reaches (or is caught locally elsewhere), so the handler's blast radius is contained.

2. One typed exception must not map to two codes. If a single class (old InstitutionError) was raised for both "missing" and "duplicate", split it into subclasses. That's incidental complexity, not intentional.

3. Inline raise HTTPException(400, …) only for request-shape problems the router itself owns and the framework doesn't already cover — e.g. a query param that must parse to an enum (submitter_type, status).

What you do not write anymore: except Exception → return ErrorResponseModel — the anti-pattern the whole change removes.


THE ROUTE BODY SHAPE

FROM (≈6 lines of ceremony per route):
try:
    data = do_work(session, x)
    return ResponseModel(status="success", message=…, data=data)
except SomeError as e:
    return ErrorResponseModel(status="error", message=…)
except Exception as e:
    logger.error(...)
    return ErrorResponseModel(status="error", message="…")

TO (the body is the happy path):
return do_work(session, x)            # data endpoint
return {"message": do_work(...)}      # action endpoint whose result is a message


FRONTEND CONTRACT

Branch
FROM: if (data.status === "success")
TO: if (response.ok)

Payload access
FROM: data.data.X
TO: data.X

Error text
FROM: data.message
TO: data.detail

Success message (where kept)
FROM: data.message
TO: data.message (unchanged)

Fetch shape
FROM: .then(r => r.json()).then(data => …)
TO: .then(async r => { const data = await r.json(); }) — needed to see r.ok


TESTS

Success
FROM: status_code == 200; data["status"]=="success"; data["data"]["X"]
TO: status_code == 200; data["X"]

Business failure
FROM: status_code == 200; "…" in data["message"]
TO: status_code == <4xx>; "…" in response.json()["detail"]

Validation (422) & auth (401/403)
FROM: already correct
TO: unchanged
