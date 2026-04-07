import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DB = CACHE_DIR / "sec_filings.db"

_CREATE_TABLE_SEC = """
CREATE TABLE IF NOT EXISTS sec_filings (
    url       TEXT PRIMARY KEY,
    data      TEXT NOT NULL,
    cached_at TEXT NOT NULL
)
"""

_CREATE_TABLE_8K = """
CREATE TABLE IF NOT EXISTS eightk_filings (
    accession_number TEXT PRIMARY KEY,
    data             TEXT NOT NULL,
    cached_at        TEXT NOT NULL
)
"""


class SecFilingCache:
    """
    SQLite-backed cache for parsed SEC filing data.

    Key  : Filing URL (Filing Date_link from the transaction)
    Value: Parsed dict (source_url, row_count, table_rows, explanation_rows)

    The DB file is stored at cache/sec_filings.db relative to this module.
    """

    def __init__(self):
        CACHE_DIR.mkdir(exist_ok=True)
        self._conn = sqlite3.connect(str(CACHE_DB))
        self._conn.execute(_CREATE_TABLE_SEC)
        self._conn.execute(_CREATE_TABLE_8K)
        self._conn.commit()
        logger.info("SEC filing cache opened: %s", CACHE_DB)

    def get(self, url: str) -> dict:
        """
        Return the cached parsed data for the given URL, or None if not cached.
        """
        if not url:
            return None
        row = self._conn.execute(
            "SELECT data FROM sec_filings WHERE url = ?", (url,)
        ).fetchone()
        if row:
            logger.info("Cache hit: %s", url)
            return json.loads(row[0])
        return None

    def set(self, url: str, data: dict) -> None:
        """
        Store parsed data for the given URL. Overwrites any existing entry.
        """
        if not url:
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO sec_filings (url, data, cached_at) VALUES (?, ?, ?)",
            (url, json.dumps(data, ensure_ascii=False), datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_8k(self, accession_number: str) -> dict:
        """
        Return the cached 8K filing data for the given accession number, or None if not cached.
        """
        if not accession_number:
            return None
        row = self._conn.execute(
            "SELECT data FROM eightk_filings WHERE accession_number = ?", (accession_number,)
        ).fetchone()
        if row:
            logger.info("8K cache hit: %s", accession_number)
            return json.loads(row[0])
        return None

    def set_8k(self, accession_number: str, data: dict) -> None:
        """
        Store 8K filing data for the given accession number. Overwrites any existing entry.
        """
        if not accession_number:
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO eightk_filings (accession_number, data, cached_at) VALUES (?, ?, ?)",
            (accession_number, json.dumps(data, ensure_ascii=False), datetime.now().isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
        logger.info("SEC filing cache closed")

    # Support use as a context manager
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
