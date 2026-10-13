"""Real-connector checks in the isolated test database."""
from app.database.mysql_client import mysql_client


def test_physical_connections_are_reused_and_sessions_are_reset():
    ids = set()
    for _ in range(15):
        with mysql_client.get_cursor() as cursor:
            cursor.execute("SELECT CONNECTION_ID() AS id, DATABASE() AS db, @pool_test AS marker")
            row = cursor.fetchone()
            assert row["db"] == "pharmavigil_test"
            assert row["marker"] is None
            ids.add(row["id"])
            cursor.execute("SET @pool_test = 1")
    assert len(ids) == 5
