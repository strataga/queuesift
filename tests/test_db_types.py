"""GitHub global IDs exceed 32-bit int; the Postgres schema must hold them."""

from sqlalchemy import BigInteger

from app.db import IssueRow


def test_github_id_column_is_64_bit() -> None:
    assert isinstance(IssueRow.__table__.c.github_id.type, BigInteger)
