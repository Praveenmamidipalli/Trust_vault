# TrustVault

TrustVault is a security-first confidential document management platform.
The planned backend uses FastAPI, PostgreSQL, SQLAlchemy, JWT authentication,
Argon2 password hashing, and explicit document-level authorization.

## Implementation status

**Current: initial database models and authentication primitives.** The
SQLAlchemy models define users, documents, document grants, and audit events
with UUID identifiers, foreign keys, checks, indexes, and uniqueness
constraints for active grants. Authentication helpers use Argon2 password
hashing, short-lived JWTs, and database-backed active-user checks. Model and
authentication tests run against SQLite, and the schema has been compiled
with SQLAlchemy's PostgreSQL dialect.

The authentication API routes, document authorization service, document
endpoints, and a live PostgreSQL connection have **not** been implemented or
verified yet. The current authentication tests use a small protected test
route to exercise the real bearer-token dependency; they do not demonstrate
the requested document HTTP authorization rules.

## Requirements

- Python 3.10 or newer
- PostgreSQL is planned; no running PostgreSQL server is needed for the
  current model tests

## Installation (Windows PowerShell)

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Do not put real passwords, JWT secrets, or database credentials in source
files. Local `.env` files and private document/storage files are excluded by
`.gitignore`; `.env.example` contains placeholders only. Set `DATABASE_URL`
and a random `JWT_SECRET_KEY` of at least 32 bytes in the process environment.
For example, generate a secret with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Tests

Run the current automated test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The PostgreSQL DDL can be checked without connecting to a server:

```powershell
.\.venv\Scripts\python.exe -c "from sqlalchemy.dialects import postgresql; from sqlalchemy.schema import CreateTable; from app.models import User, Document, DocumentGrant, AuditEvent; [CreateTable(model.__table__).compile(dialect=postgresql.dialect()) for model in (User, Document, DocumentGrant, AuditEvent)]; print('PostgreSQL DDL compiled')"
```

## Project layout

```text
app/       Application package and SQLAlchemy models
tests/     Automated tests
docs/      Project documentation
scripts/   Development scripts
```