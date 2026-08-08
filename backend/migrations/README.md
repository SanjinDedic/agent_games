# Migrations

Empty on purpose.

`backend/entrypoint.sh` applies every `*.sql` here in filename order on each
container start, under `psql -v ON_ERROR_STOP=1`. Files must therefore be
idempotent forever — they re-run on every boot, and one that errors aborts
pre-start on *every* subsequent start, with `docker compose down -v` the only way
out.

The previous set was deleted when the schema became single-tenant. No replacement
was written: the new `UNIQUE(team.name)` and `UNIQUE(league.name)` constraints
cannot be added to a database that already holds duplicates, so any migrated
volume would end up with the institution columns dropped but the constraints
missing — a schema that looks upgraded while still allowing the duplicates that
make `/auth/login` ambiguous. A fresh volume is the supported path:

    docker compose down -v && docker compose up

Add a dated file here for the next schema change to an existing database. Note
that `init_db`'s `create_all` only ever creates *missing tables* — it never
ALTERs one — so a new column on an existing table needs a file here.
