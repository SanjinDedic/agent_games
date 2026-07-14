"""Grant the application role everything it needs on a DigitalOcean managed Postgres.

Run ONCE (or any time the grants look wrong — it is idempotent) as the cluster
admin role, before the first deploy against the managed database:

    DOADMIN_DATABASE_URL='postgresql://doadmin:PASS@HOST:25060/agent_games?sslmode=require' \
        uv run python -m backend.scripts.grant_managed_db

Why this is needed: DO creates the app role with no privileges on the database,
and since Postgres 15 the `public` schema no longer grants CREATE to PUBLIC. So
`init_db`'s `create_all` fails with "permission denied for schema public" until
the app role is granted CREATE there. Everything the app touches afterwards is
created BY the app role, which therefore owns it — no further grants required.

The grants below stay useful anyway: they cover objects created by doadmin
(a manual psql fix, a pg_restore run as admin) so the app role does not lose
access to them.
"""

import argparse
import os
import sys
from urllib.parse import urlparse

import psycopg
from psycopg import sql


def build_statements(role: str, dbname: str) -> list[sql.Composed]:
    """The full grant set, in dependency order. Every statement is idempotent."""
    r = sql.Identifier(role)
    d = sql.Identifier(dbname)
    return [
        # Connect to the database at all.
        sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO {}").format(d, r),
        # The one that actually matters: create_all needs CREATE on public.
        sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(r),
        # Objects that already exist and are owned by someone else (doadmin).
        sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {}").format(r),
        sql.SQL("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {}").format(r),
        # Same, for objects doadmin creates in future (e.g. an admin pg_restore).
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {}"
        ).format(r),
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {}"
        ).format(r),
    ]


def verify(conn, role: str, dbname: str) -> bool:
    """Print the privileges that must hold for a deploy to succeed."""
    checks = [
        ("CONNECT on database", "SELECT has_database_privilege(%s, %s, 'CONNECT')", (role, dbname)),
        ("USAGE on schema public", "SELECT has_schema_privilege(%s, 'public', 'USAGE')", (role,)),
        ("CREATE on schema public", "SELECT has_schema_privilege(%s, 'public', 'CREATE')", (role,)),
    ]
    ok = True
    with conn.cursor() as cur:
        for label, query, params in checks:
            cur.execute(query, params)
            granted = cur.fetchone()[0]
            print(f"  [{'ok' if granted else 'FAIL'}] {role}: {label}")
            ok = ok and granted
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--admin-url",
        default=os.environ.get("DOADMIN_DATABASE_URL"),
        help="libpq URL for the cluster admin (doadmin), pointing at the app database. "
        "Defaults to $DOADMIN_DATABASE_URL. Never commit this — it is a superuser-ish credential.",
    )
    parser.add_argument(
        "--role",
        default="agent_games_user",
        help="Application role to grant (default: agent_games_user)",
    )
    args = parser.parse_args()

    if not args.admin_url:
        parser.error("no admin URL: pass --admin-url or set DOADMIN_DATABASE_URL")

    # The app database is whatever the admin URL points at — connecting there as
    # doadmin is what lets us grant inside its `public` schema.
    dbname = urlparse(args.admin_url).path.lstrip("/")
    if not dbname:
        parser.error("--admin-url must include the database name (e.g. .../agent_games)")

    print(f"==> connecting to {dbname} as cluster admin")
    with psycopg.connect(args.admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (args.role,))
            if cur.fetchone() is None:
                print(
                    f"ERROR: role {args.role!r} does not exist. Create it in the DO "
                    "control panel (Users & Databases) first.",
                    file=sys.stderr,
                )
                return 1

        for statement in build_statements(args.role, dbname):
            rendered = statement.as_string(conn)
            print(f"==> {rendered}")
            with conn.cursor() as cur:
                cur.execute(statement)

        # Best-effort: membership lets doadmin manage/drop objects the app role
        # owns (handy for a manual restore). DO's doadmin is not a superuser, so
        # this can be refused — the app does not depend on it.
        try:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("GRANT {} TO doadmin").format(sql.Identifier(args.role)))
            print(f"==> GRANT {args.role} TO doadmin")
        except psycopg.Error as e:
            print(f"    (skipped GRANT {args.role} TO doadmin: {e})")

        print("==> verifying")
        if not verify(conn, args.role, dbname):
            print("FAILED: some privileges are still missing", file=sys.stderr)
            return 1

    print(f"==> done. {args.role} can now run init_db against {dbname}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
