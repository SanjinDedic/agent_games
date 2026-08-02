# Deliberately empty: a package-level re-export of user_router would drag the
# whole FastAPI route stack (~25MB) into any import of a single submodule
# (e.g. user_db). Import user_router from backend.routes.user.user_router
# directly.
