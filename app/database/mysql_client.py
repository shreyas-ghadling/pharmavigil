"""
MySQL Database Driver and Client Helper for Pharmavigil
Enforces parameterized queries, transaction controls, and custom exception handling.
"""

from contextlib import contextmanager
from threading import Lock
from time import monotonic, sleep
from typing import Any, Dict, List, Optional, Tuple
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector.errors import PoolError
from mysql.connector import Error as MySQLError

from app.config import config
from app.utils.exceptions import DatabaseConnectionError


class MySQLClient:
    """Encapsulates MySQL connection management and defensive query execution."""

    def __init__(self):
        self.host = config.mysql.host
        self.port = config.mysql.port
        self.user = config.mysql.user
        self.password = config.mysql.password
        self.database = config.mysql.database
        self._pool = None
        self._pool_settings = None
        self._pool_lock = Lock()

    def _get_pool(self):
        # Initialize only on first use. Rebuild when test/setup code changes the DB.
        settings = (self.host, self.port, self.user, self.password, self.database)
        with self._pool_lock:
            if self._pool is None or self._pool_settings != settings:
                pool = MySQLConnectionPool(
                    pool_size=5,
                    pool_reset_session=True,
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    autocommit=False,
                )
                self._pool = pool
                self._pool_settings = settings
            return self._pool

    def get_connection(self):
        """Borrows a connection; close() resets it and returns it to the pool."""
        try:
            pool = self._get_pool()
            deadline = monotonic() + 10
            while True:
                try:
                    return pool.get_connection()
                except PoolError:
                    # Brief bursts should wait for a borrower, not fail immediately.
                    if monotonic() >= deadline:
                        raise
                    sleep(0.05)
        except MySQLError as err:
            raise DatabaseConnectionError(
                f"MySQL Connection Error on {self.host}:{self.port}/{self.database}: {err.msg}",
                original_exception=err
            ) from err

    @contextmanager
    def get_cursor(self, dictionary: bool = True):
        """Context manager providing a transactional cursor with auto-commit/rollback."""
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor(dictionary=dictionary)
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                conn.close()

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """
        Executes a parameterized SELECT query and returns a list of dictionaries.
        Guarantees protection against SQL injection.
        """
        try:
            with self.get_cursor(dictionary=True) as cursor:
                cursor.execute(query, params or ())
                result = cursor.fetchall()
                return result
        except DatabaseConnectionError:
            raise
        except MySQLError as err:
            raise RuntimeError(f"Database query execution error: {err.msg}") from err

    def execute_one(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
        """Executes a parameterized SELECT query expecting a single row."""
        try:
            with self.get_cursor(dictionary=True) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except DatabaseConnectionError:
            raise
        except MySQLError as err:
            raise RuntimeError(f"Database single-row query error: {err.msg}") from err

    def execute_update(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> int:
        """
        Executes an INSERT/UPDATE/DELETE query with parameters.
        Returns the number of affected rows.
        """
        try:
            with self.get_cursor(dictionary=False) as cursor:
                cursor.execute(query, params or ())
                return cursor.rowcount
        except DatabaseConnectionError:
            raise
        except MySQLError as err:
            raise RuntimeError(f"Database update execution error: {err.msg}") from err

    def call_stored_procedure(
        self, proc_name: str, args: Tuple[Any, ...]
    ) -> Tuple[Any, ...]:
        """
        Executes a MySQL Stored Procedure with IN and OUT parameters.
        Returns the output argument tuple.
        """
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            result_args = cursor.callproc(proc_name, args)
            conn.commit()
            return result_args
        except MySQLError as err:
            conn.rollback()
            raise RuntimeError(f"Stored procedure execution failed for '{proc_name}': {err.msg}") from err
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                conn.close()


# Singleton client instance
mysql_client = MySQLClient()
