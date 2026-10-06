# Migration Guide

How schema changes reach MySQL for the Library Management System backend.

## 1. What Alembic Is

[Alembic](https://alembic.sqlalchemy.org/) is the migration tool for
SQLAlchemy. It does three things:

1. **Versions the schema.** Every change is a small Python file in
   `backend/alembic/versions/` with an `upgrade()` and a `downgrade()`
   function. Applied revisions are recorded in the `alembic_version` table, so
   every environment can be brought to a known state.
2. **Generates migrations.** `alembic revision --autogenerate` compares the
   live database against `Base.metadata` (the models in `backend/app/models/`)
   and writes the DDL for the difference.
3. **Runs SQL without SQLAlchemy** when a DBA needs the statements:
   `alembic upgrade head --sql`.

Project layout:

```
backend/
├── alembic.ini                    # script location + logging; URL comes from .env
└── alembic/
    ├── env.py                     # loads Base.metadata and DATABASE_URL
    ├── script.py.mako             # template for new revisions
    └── versions/
        ├── 001_initial_migration.py
        └── .gitkeep
```

`alembic.ini` deliberately leaves `sqlalchemy.url` empty. `alembic/env.py`
reads `DATABASE_URL` from `backend/.env` through `app.config` and injects it,
so credentials never enter version control.

## 2. First-Time Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
# edit .env: DATABASE_URL, JWT_SECRET, MYSQL_*
mysql -u root -p -e "CREATE DATABASE library_db;"
alembic upgrade head
```

Confirm the result:

```bash
alembic current        # -> 001 (head)
alembic history        # <base> -> 001 (head)
```

## 3. Daily Commands

Run everything from `backend/`.

| Task | Command |
| --- | --- |
| Create a migration | `alembic revision --autogenerate -m "Add fine_amount to borrowing_records"` |
| Empty (data-only) migration | `alembic revision -m "Backfill member_role"` |
| Apply everything | `alembic upgrade head` |
| Apply one step | `alembic upgrade +1` |
| Apply up to a revision | `alembic upgrade 001` |
| Undo one step | `alembic downgrade -1` |
| Undo everything | `alembic downgrade base` |
| Show applied revision | `alembic current` |
| Show history with details | `alembic history --verbose` |
| Preview SQL without touching the DB | `alembic upgrade head --sql` |
| Detect model/schema drift | `alembic revision --autogenerate -m "drift check"` (an empty `pass` body means no drift) |

## 4. Creating a Migration

1. Edit the model in `backend/app/models/`.
2. Migrate the database if you want autogen to ignore the change for now:
   `alembic revision --autogenerate -m "..."` produces a new empty revision.
3. Generate the DDL:

   ```bash
   alembic revision --autogenerate -m "Add published_year to books"
   ```

4. **Read the generated file.** Alembic comments everything as
   "please adjust!". Common manual fixes:
   - rename the file to something meaningful
     (`004_add_borrowing_records.py`) and keep the `revision` id, or set it to
     a readable value such as `004` when no later revision depends on it;
   - server defaults Alembic cannot infer (`server_default=sa.text("0")`);
   - data migrations (`op.execute(...)`) between the DDL statements;
   - `op.create_index(..., unique=True)` when uniqueness is required;
   - MySQL cannot drop or alter a column in place - use
     `op.alter_column(..., existing_type=...)` carefully or
     `batch_alter_table` for a safe copy-and-swap.
5. Apply it locally, test it, and commit the revision file with the code that
   needs it:

   ```bash
   alembic upgrade head
   alembic downgrade -1 && alembic upgrade head   # prove the downgrade works
   ```

6. Open a pull request. Reviewers must be able to follow the sequence without
   running it.

## 5. Migration Conflicts

Two branches that both call `--autogenerate` against the same base create two
revisions with the same `down_revision`, and only one can be the child of that
parent. The usual symptom is:

```
KeyError: 'a1b2c3'   # or: Multiple head revisions are present
```

Resolution (never edit a revision that has already been applied to a shared
database - add a new one):

```bash
alembic history --verbose          # find the fork: two revisions share a parent
alembic heads                      # one is head, the other is the orphan
alembic merge -m "Merge auth and catalog" <revision_a> <revision_b>
```

`alembic merge` writes a `merge_*` revision with both parents and an empty
body. Then:

```bash
alembic upgrade head
```

Other situations and their fixes:

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Can't locate revision identified by '<id>'` | A database is ahead of or behind the code | `alembic current`, then `alembic upgrade head` or `alembic downgrade <id>` |
| `Multiple head revisions are present` | Two branches created revisions without merging | `alembic merge heads -m "..."` |
| Migration "succeeds" but the schema is wrong | Someone edited tables by hand | Treat the database as the truth: write a corrective migration, or reset local state with `alembic downgrade base && alembic upgrade head` |
| `Table 'users' already exists` | Tables were created with `Base.metadata.create_all()` or manually | Drop them (`alembic downgrade base` after `stamp base`) and re-run `upgrade head` |
| Fresh clone cannot migrate | `.env` missing or pointing elsewhere | Copy `.env.example` to `.env` and check `DATABASE_URL` |

Never use `alembic stamp <id>` on a shared database: it only rewrites the
recorded version without touching the schema. It is for adopting an existing
schema into version control.

## 6. Best Practices

- **One logical change per revision.** A migration named "add borrowing
  records" is reviewable; one named "misc fixes" is not.
- **Always write a real `downgrade()`.** It is the only safety net when a
  release goes wrong. Drop indexes before tables, and tables before the types
  they depend on.
- **Never edit an applied revision.** Add a new one; otherwise databases
  already migrated will diverge silently.
- **Keep migrations deterministic and data-safe.** No `DROP TABLE` without a
  backup plan, no long locks inside a transaction, and no non-idempotent data
  edits without a guard.
- **Keep model defaults in Python, not the migration.** `default=utcnow` in the
  model works for new rows; `server_default` only for columns that must be set
  by tools outside the app.
- **Run `alembic upgrade head --sql` in review** to see the exact statements
  that will hit production.
- **Test the round trip** - `alembic downgrade base` then `alembic upgrade
  head` - before merging.
- **Never commit credentials.** `DATABASE_URL` comes from `.env`, which is
  git-ignored.

## 7. Troubleshooting Checklist

1. `alembic current` - which revision does this database think it is at?
2. `alembic history --verbose` - what should it be at?
3. `alembic upgrade head --sql` - what would run, and does it look right?
4. Are models imported? `alembic/env.py` imports `app.models`; a new model
   file must be re-exported from `backend/app/models/__init__.py` or
   autogenerate will not see it.
5. Is `.env` loaded? Alembic runs with the current working directory as
   `backend/`; `config.py` resolves `backend/.env` by path.
