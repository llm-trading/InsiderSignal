import logging

logger = logging.getLogger(__name__)

TRANSACTION_CODE_KEY = "3. Transaction Code (Instr. \n      8) | Code"


class TransactionFilter:
    """
    Filters transactions whose SEC filing contains no open-market Purchase ('P') rows.

    A transaction is kept only if at least one row in sec_filing_data.table_rows
    has a transaction code that starts with 'P'. Non-P rows are removed from
    table_rows; the entire transaction is dropped if none remain.
    """

    def filter_by_purchase_code(self, result: dict) -> dict:
        """
        Remove non-Purchase transactions in-place and update result metadata.

        Args:
            result: The pipeline output dict (with 'transactions' list).

        Returns:
            Updated result dict with only P-code transactions retained.
        """
        transactions = result.get("transactions", [])
        original_count = len(transactions)
        kept = []
        dropped_tickers = []

        for tx in transactions:
            sec_data = tx.get("sec_filing_data", {})
            table_rows = sec_data.get("table_rows", [])

            p_rows = [
                row for row in table_rows
                if str(row.get(TRANSACTION_CODE_KEY, "")).strip().startswith("P")
            ]

            if p_rows:
                sec_data["table_rows"] = p_rows
                sec_data["row_count"] = len(p_rows)
                kept.append(tx)
            else:
                dropped_tickers.append(tx.get("Ticker", "?"))

        unique_tickers = {t.get("Ticker") for t in kept if t.get("Ticker")}
        result["transactions"] = kept
        result["total_transactions"] = len(kept)
        result["unique_tickers"] = len(unique_tickers)

        logger.info(
            "Filter complete — kept %d/%d transactions (dropped %d: %s)",
            len(kept),
            original_count,
            len(dropped_tickers),
            ", ".join(sorted(set(dropped_tickers))) or "none",
        )
        return result
