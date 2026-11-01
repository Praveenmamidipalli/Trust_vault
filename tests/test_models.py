from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Document, DocumentGrant, User


@pytest.fixture
def engine():
    test_engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


def test_all_model_tables_create(engine):
    assert set(inspect(engine).get_table_names()) == {
        "audit_events",
        "document_grants",
        "documents",
        "users",
    }


def test_role_and_active_grant_constraints(engine):
    owner = User(
        username="alice",
        email="alice@example.test",
        password_hash="hash",
        role="OWNER",
    )
    reader = User(
        username="bob",
        email="bob@example.test",
        password_hash="hash",
        role="VIEWER",
    )
    with Session(engine) as session:
        invalid_user = User(
            username="mallory",
            email="mallory@example.test",
            password_hash="hash",
            role="SUPERUSER",
        )
        session.add(invalid_user)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        session.add_all((owner, reader))
        session.flush()
        doc = Document(
            owner_id=owner.id,
            filename="confidential.pdf",
            category="confidential",
            storage_key="documents/opaque-key",
            content_type="application/pdf",
            file_size=10,
        )
        session.add(doc)
        session.flush()
        active_grant = DocumentGrant(
            document_id=doc.id,
            user_id=reader.id,
            permission="read",
            granted_by=owner.id,
        )
        session.add(active_grant)
        session.flush()

        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(
                    DocumentGrant(
                        document_id=doc.id,
                        user_id=reader.id,
                        permission="edit",
                        granted_by=owner.id,
                    )
                )
                session.flush()

        active_grant.revoked_at = datetime.now(timezone.utc)
        session.flush()
        session.add(
            DocumentGrant(
                document_id=doc.id,
                user_id=reader.id,
                permission="read",
                granted_by=owner.id,
            )
        )
        session.flush()
