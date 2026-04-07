"""Insider behavior context enricher."""

from collections import defaultdict
from .base_enricher import BaseEnricher


def normalize_name(name):
    """Normalize insider name for comparison."""
    if not name:
        return "UNKNOWN"
    return str(name).strip().lower()


class InsiderBehaviorEnricher(BaseEnricher):
    """Enriches ticker data with insider behavior patterns (repeat buyers)."""
    
    def get_context_key(self) -> str:
        return "insider_behavior_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add insider behavior context to ticker_data."""
        transactions = ticker_data.get("insider_transactions", [])

        # Fixed schema
        ctx = {
            "has_behavior_data": False,
            "unique_insider_count": 0,
            "total_transactions": 0,
            "repeat_insider_count": 0,
            "max_transactions_by_single_insider": 0,
            "has_repeated_buys": False,
            "errors": []
        }

        errors = ctx["errors"]

        try:
            if not transactions:
                errors.append("No insider transactions available")
                ticker_data["insider_behavior_context"] = ctx
                return

            insider_map = defaultdict(int)

            # Count transactions per insider
            for tx in transactions:
                raw_name = tx.get("Insider Name")

                if not raw_name:
                    errors.append("Missing insider name in transaction")
                
                name = normalize_name(raw_name)
                insider_map[name] += 1

            if not insider_map:
                errors.append("No valid insider names found")
                ticker_data["insider_behavior_context"] = ctx
                return

            total_transactions = len(transactions)
            unique_insiders = len(insider_map)

            repeat_insiders = sum(1 for count in insider_map.values() if count > 1)
            max_tx = max(insider_map.values()) if insider_map else 0

            # Assign values
            ctx["total_transactions"] = total_transactions
            ctx["unique_insider_count"] = unique_insiders
            ctx["repeat_insider_count"] = repeat_insiders
            ctx["max_transactions_by_single_insider"] = max_tx
            ctx["has_repeated_buys"] = repeat_insiders > 0

            ctx["has_behavior_data"] = True

        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")

        # Final assignment
        ticker_data["insider_behavior_context"] = ctx
