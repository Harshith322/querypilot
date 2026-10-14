import os

import psycopg
import pytest

ADMIN = os.getenv("QP_TEST_ADMIN_DSN")
READONLY = os.getenv("QP_TEST_READONLY_DSN")


@pytest.fixture(scope="session")
def db():
    """Real Postgres with sample data. Skipped unless QP_TEST_ADMIN_DSN and QP_TEST_READONLY_DSN are set."""
    if not (ADMIN and READONLY):
        pytest.skip("set QP_TEST_ADMIN_DSN and QP_TEST_READONLY_DSN to run database tests")
    try:
        psycopg.connect(ADMIN, connect_timeout=3).close()
    except psycopg.OperationalError:
        pytest.skip("test database not reachable")
    from scripts.init_db import init_db

    init_db(ADMIN, sample=True)
    return {"admin": ADMIN, "readonly": READONLY}
