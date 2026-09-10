import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import is_postgres_url, is_sqlite_url


def test_detecta_sqlite():
    assert is_sqlite_url("sqlite:///./viabilidades.db")
    assert not is_postgres_url("sqlite:///./viabilidades.db")


def test_detecta_postgres():
    url = "postgresql+psycopg2://u:p@localhost:5432/db"
    assert is_postgres_url(url)
    assert not is_sqlite_url(url)
