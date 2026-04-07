import logging
from datetime import datetime, timedelta

from CONSTANTS import CLUSTER_ROLLING_WINDOW

logger = logging.getLogger(__name__)

_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S")


def _parse_trade_date(date_str: str):
    """Try to parse a Trade Date string into a date object. Returns None on failure."""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


class TransactionGrouper:
    """
    Groups a flat list of transactions by ticker symbol and computes a
    cluster_transaction_count for each group using CLUSTER_ROLLING_WINDOW.

    Input (flat result dict):
        {
            "ticker": "ALL",
            "fetch_date": "...",
            "source_url": "...",
            "finviz_url": "...",
            "total_transactions": N,
            "unique_tickers": M,
            "transactions": [ {...}, ... ]
        }

    Output (grouped result dict):
        {
            "ticker": "ALL",
            "fetch_date": "...",
            "source_url": "...",
            "finviz_url": "...",
            "total_tickers": M,
            "tickers": {
                "NSP": {
                    "company_name": "Insperity, Inc.",
                    "transaction_count": 2,
                    "cluster_transaction_count": 2,
                    "transactions": [ {...}, {...} ]
                },
                ...
            }
        }
    """

    def group_by_ticker(self, result: dict) -> dict:
        """
        Transform the flat result into a ticker-grouped structure with
        cluster_transaction_count per group.

        Args:
            result: Pipeline output dict containing a 'transactions' list.

        Returns:
            New dict with transactions grouped under each ticker symbol.
        """
        transactions = result.get("transactions", [])
        groups: dict = {}

        for tx in transactions:
            symbol = tx.get("Ticker", "UNKNOWN")
            if symbol not in groups:
                groups[symbol] = {
                    "company_name": tx.get("Company Name", ""),
                    "transaction_count": 0,
                    "cluster_transaction_count": 0,
                    "insider_transactions": [],
                }
            groups[symbol]["insider_transactions"].append(tx)
            groups[symbol]["transaction_count"] += 1

        # Compute cluster_transaction_count for each group
        for symbol, group in groups.items():
            group["cluster_transaction_count"] = self._cluster_count(
                group["insider_transactions"], CLUSTER_ROLLING_WINDOW
            )

        logger.info(
            "Grouped %d transactions into %d tickers (rolling window: %d days)",
            len(transactions),
            len(groups),
            CLUSTER_ROLLING_WINDOW,
        )

        return {
            "ticker": result.get("ticker", "ALL"),
            "fetch_date": result.get("fetch_date"),
            "source_url": result.get("source_url"),
            "finviz_url": result.get("finviz_url"),
            "total_tickers": len(groups),
            "tickers": groups,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cluster_count(transactions: list, window_days: int) -> int:
        """
        Count how many transactions fall within [latest_trade_date - window_days,
        latest_trade_date] across the group.

        Transactions whose Trade Date cannot be parsed are excluded from the count.
        """
        dates = [
            _parse_trade_date(tx.get("Trade Date", ""))
            for tx in transactions
        ]
        valid_dates = [d for d in dates if d is not None]

        if not valid_dates:
            return 0

        latest = max(valid_dates)
        cutoff = latest - timedelta(days=window_days)

        return sum(1 for d in valid_dates if d >= cutoff)
