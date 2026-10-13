"""Pool lifecycle and transaction safety, without external databases."""
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from unittest.mock import MagicMock

import pytest
from mysql.connector.errors import PoolError

from app.database.mysql_client import MySQLClient
pool_module = import_module("app.database.mysql_client")


def test_pool_is_lazy_shared_and_resets_sessions(monkeypatch):
    factory = MagicMock()
    monkeypatch.setattr(pool_module, "MySQLConnectionPool", factory)
    client = MySQLClient()
    factory.assert_not_called()
    with ThreadPoolExecutor(max_workers=8) as executor:
        connections = list(executor.map(lambda _: client.get_connection(), range(16)))
    factory.assert_called_once()
    assert factory.call_args.kwargs["pool_size"] == 5
    assert factory.call_args.kwargs["pool_reset_session"] is True
    assert factory.call_args.kwargs["autocommit"] is False
    assert len(connections) == 16


def test_database_switch_uses_a_new_pool(monkeypatch):
    factory = MagicMock(side_effect=[MagicMock(), MagicMock()])
    monkeypatch.setattr(pool_module, "MySQLConnectionPool", factory)
    client = MySQLClient()
    client.get_connection()
    client.database = "pharmavigil_test"
    client.get_connection()
    assert factory.call_count == 2
    assert factory.call_args.kwargs["database"] == "pharmavigil_test"


@pytest.mark.parametrize("fail", [False, True])
def test_borrower_commits_or_rolls_back_and_returns_connection(monkeypatch, fail):
    client = MySQLClient()
    connection = MagicMock()
    monkeypatch.setattr(client, "get_connection", lambda: connection)
    if fail:
        with pytest.raises(ValueError):
            with client.get_cursor():
                raise ValueError("invalid operation")
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
    else:
        with client.get_cursor():
            pass
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
    connection.cursor.return_value.close.assert_called_once()
    connection.close.assert_called_once()


def test_busy_pool_waits_for_a_returned_connection(monkeypatch):
    pool = MagicMock()
    available = MagicMock()
    pool.get_connection.side_effect = [PoolError("busy"), available]
    client = MySQLClient()
    monkeypatch.setattr(client, "_get_pool", lambda: pool)
    monkeypatch.setattr(pool_module, "sleep", lambda _: None)
    assert client.get_connection() is available


def test_busy_pool_has_a_bounded_wait(monkeypatch):
    pool = MagicMock()
    pool.get_connection.side_effect = PoolError("busy")
    client = MySQLClient()
    monkeypatch.setattr(client, "_get_pool", lambda: pool)
    monkeypatch.setattr(pool_module, "monotonic", MagicMock(side_effect=[0, 11]))
    from app.utils.exceptions import DatabaseConnectionError
    with pytest.raises(DatabaseConnectionError):
        client.get_connection()
