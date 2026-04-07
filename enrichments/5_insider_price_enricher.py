"""Insider price vs current price enricher."""

import yfinance as yf
import pandas as pd
from .base_enricher import BaseEnricher


def parse_float(val):
    """Parse float from string with currency symbols."""
    try:
        if val is None:
            return None
        return float(str(val).replace("$", "").replace(",", "").replace("+", ""))
    except:
        return None


class InsiderPriceEnricher(BaseEnricher):
    """Enriches ticker data with insider price comparison context."""
    
    def get_context_key(self) -> str:
        return "insider_price_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add insider price context to ticker_data."""
        transactions = ticker_data.get("insider_transactions", [])

        # Fixed schema
        price_context = {
            "has_price_comparison": False,
            "data_source": "yfinance",
            "avg_insider_buy_price": None,
            "current_price": None,
            "price_diff_pct": None,
            "volatility_30d": None,
            "z_score": None,
            "signal_status": "UNKNOWN",
            "errors": []
        }

        errors = price_context["errors"]

        try:
            if not transactions:
                errors.append("No insider transactions available")
                ticker_data["insider_price_context"] = price_context
                return

            ticker_symbol = transactions[0].get("Ticker")

            if not ticker_symbol:
                errors.append("Ticker not found in transactions")
                ticker_data["insider_price_context"] = price_context
                return

            # VALUE-WEIGHTED insider price
            total_value = 0
            total_qty = 0

            for tx in transactions:
                value = parse_float(tx.get("Value"))
                qty = parse_float(tx.get("Qty"))

                if value is None or qty is None:
                    errors.append("Invalid Value/Qty in transaction")
                    continue

                if qty == 0:
                    errors.append("Transaction quantity is zero")
                    continue

                total_value += value
                total_qty += qty

            if total_qty == 0:
                errors.append("Total transaction quantity is zero")
                ticker_data["insider_price_context"] = price_context
                return

            avg_price = total_value / total_qty
            price_context["avg_insider_buy_price"] = round(float(avg_price), 5)

            # Market data
            stock = yf.Ticker(ticker_symbol)
            hist = stock.history(period="2mo")

            if hist is None or hist.empty:
                errors.append("Price data not available from yfinance")
                ticker_data["insider_price_context"] = price_context
                return

            hist = hist.reset_index()
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
            hist = hist.sort_values("Date").reset_index(drop=True)

            if len(hist) < 30:
                errors.append("Insufficient data for volatility calculation")
                ticker_data["insider_price_context"] = price_context
                return

            current_price = hist.iloc[-1]["Close"]

            if pd.isna(current_price):
                errors.append("Current price is NaN")
                ticker_data["insider_price_context"] = price_context
                return

            price_context["current_price"] = round(float(current_price), 5)

            # Diff
            if avg_price == 0:
                errors.append("Average insider price is zero")
                ticker_data["insider_price_context"] = price_context
                return

            diff = (current_price - avg_price) / avg_price
            price_context["price_diff_pct"] = round(float(diff), 5)

            # Volatility (std of daily returns)
            returns = hist["Close"].pct_change().dropna()

            if returns.empty:
                errors.append("Returns series is empty")
                ticker_data["insider_price_context"] = price_context
                return

            volatility = returns.std()

            if pd.isna(volatility) or volatility == 0:
                errors.append("Invalid volatility (NaN or zero)")
                ticker_data["insider_price_context"] = price_context
                return

            price_context["volatility_30d"] = round(float(volatility), 5)

            # Z-score
            z_score = diff / volatility
            price_context["z_score"] = round(float(z_score), 5)

            # Classification
            if z_score <= -2:
                status = "STRONG_UNDERVALUE"
            elif -2 < z_score <= -1:
                status = "UNDERVALUED"
            elif -1 < z_score < 1:
                status = "FAIR"
            elif z_score >= 1:
                status = "OVERVALUED"
            else:
                status = "UNKNOWN"

            price_context["signal_status"] = status
            price_context["has_price_comparison"] = True

        except Exception as e:
            errors.append(f"yfinance error: {str(e)}")

        # Final assignment
        ticker_data["insider_price_context"] = price_context
