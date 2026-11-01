# TrustVault

TrustVault is a security-first confidential document management platform. Its
backend is being built incrementally with FastAPI, PostgreSQL, SQLAlchemy,
JWT authentication, and explicit document-level authorization.

## Current foundation

The initial schema defines users, documents, document grants, and audit events
in `app/models.py`. `app/database.py` contains the SQLAlchemy declarative base
and a consistent database naming convention. The ORM models use UUID primary
keys, foreign keys, checks, and indexes; active grants are unique per
document/user pair while revoked grants remain available as history.

The API and authentication are not implemented yet.

## Setup and verification

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

PostgreSQL connection configuration and API startup instructions will be added
with the database connection and application implementation.