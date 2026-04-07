"""Position sizing context enricher."""

import math
import yfinance as yf
from .base_enricher import BaseEnricher


def parse_float(val):
    """Parse float from string with currency symbols."""
    try:
        if val is None:
            return None
        return float(
            str(val).replace("$", "")
                    .replace(",", "")
                    .replace("+", "")
                    .replace("%", "")
        )
    except:
        return None


def parse_ownership_change(val):
    """Parse ownership change, detecting 'NEW' positions."""
    if not val:
        return None, False

    val = str(val).strip()

    if val.lower() == "new":
        return None, True

    try:
        return float(val.replace("%", "").replace("+", "")), False
    except:
        return None, False


class PositionSizingEnricher(BaseEnricher):
    """Enriches ticker data with position sizing context."""
    
    def get_context_key(self) -> str:
        return "position_sizing_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add position sizing context to ticker_data."""
        transactions = ticker_data.get("insider_transactions", [])

        # Fixed schema
        ctx = {
            "has_position_data": False,
            "data_source": "none",
            "market_cap": None,
            "total_insider_value": None,
            "insider_value_to_mcap": None,
            "avg_ownership_change_pct": None,
            "weighted_ownership_change_pct": None,
            "new_position_count": 0,
            "has_new_position": False,
            "signal_status": "UNKNOWN",
            "errors": []
        }

        errors = ctx["errors"]

        try:
            if not transactions:
                errors.append("No insider transactions available")
                ticker_data["position_sizing_context"] = ctx
                return

            total_value = 0
            ownership_changes = []
            weighted_sum = 0
            total_weight = 0
            new_position_count = 0

            # Aggregate
            for tx in transactions:
                value = parse_float(tx.get("Value"))
                qty = parse_float(tx.get("Qty"))
                own_change_raw = tx.get("ΔOwn")

                own_change, is_new = parse_ownership_change(own_change_raw)

                if is_new:
                    new_position_count += 1

                if value is None:
                    errors.append("Invalid transaction value")
                elif value > 0:
                    total_value += value

                if own_change is not None:
                    ownership_changes.append(own_change)

                    if value and value > 0:
                        weighted_sum += own_change * value
                        total_weight += value

            # Assign aggregates
            if total_value > 0:
                ctx["total_insider_value"] = round(float(total_value), 5)
            else:
                errors.append("Total insider value is zero")

            if ownership_changes:
                ctx["avg_ownership_change_pct"] = round(
                    sum(ownership_changes) / len(ownership_changes), 5
                )
            else:
                errors.append("No valid ownership change data")

            if total_weight > 0:
                ctx["weighted_ownership_change_pct"] = round(
                    weighted_sum / total_weight, 5
                )
            else:
                errors.append("No valid weights for ownership change")

            ctx["new_position_count"] = new_position_count
            ctx["has_new_position"] = new_position_count > 0

            # Market cap
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                if not info:
                    errors.append("Stock info not available from yfinance")
                else:
                    market_cap = info.get("marketCap")

                    if market_cap is None or market_cap == 0:
                        errors.append("Invalid market cap value")
                    else:
                        ctx["market_cap"] = float(market_cap)

                        if total_value > 0:
                            ratio = total_value / market_cap
                            ctx["insider_value_to_mcap"] = round(float(ratio), 6)

            except Exception as e:
                errors.append(f"Error fetching market cap: {str(e)}")

            # Signal classification
            ratio = ctx["insider_value_to_mcap"]

            if ratio is not None:
                try:
                    score = math.log10(ratio + 1e-9)

                    if score > -2:          # > ~1%
                        status = "HIGH_CONVICTION"
                    elif -3 < score <= -2:  # 0.1–1%
                        status = "MODERATE"
                    elif score <= -3:       # <0.1%
                        status = "LOW"
                    else:
                        status = "UNKNOWN"

                    # Boost for NEW positions
                    if ctx["has_new_position"]:
                        if status == "MODERATE":
                            status = "HIGH_CONVICTION"
                        elif status == "LOW":
                            status = "MODERATE"

                    ctx["signal_status"] = status

                except Exception:
                    errors.append("Error computing conviction score")

            else:
                errors.append("Cannot compute signal without mcap ratio")

            ctx["has_position_data"] = True
            ctx["data_source"] = "yfinance"

        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")

        # Final assignment
        ticker_data["position_sizing_context"] = ctx
