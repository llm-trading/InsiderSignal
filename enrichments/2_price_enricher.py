"""Price context enricher."""

import yfinance as yf
import pandas as pd
from .base_enricher import BaseEnricher


class PriceEnricher(BaseEnricher):
    """Enriches ticker data with price context (drawdown, 52w range)."""
    
    def get_context_key(self) -> str:
        return "price_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add price context to ticker_data."""
        # Fixed schema
        price_context = {
            "has_price_data": False,
            "data_source": "none",
            "current_price": None,
            "stock_drawdown_30d": None,
            "distance_from_52w_low": None,
            "distance_from_52w_high": None,
            "errors": []
        }

        errors = price_context["errors"]

        try:
            stock = yf.Ticker(ticker)

            # Fetch 1 year data
            hist = stock.history(period="1y")

            if hist is None or hist.empty:
                errors.append("Price data not available from yfinance")
                ticker_data["price_context"] = price_context
                return

            hist = hist.reset_index()
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
            hist = hist.sort_values("Date").reset_index(drop=True)

            price_context["has_price_data"] = True
            price_context["data_source"] = "yfinance"

            # Current price
            try:
                current_price = hist.iloc[-1]["Close"]
                if pd.isna(current_price):
                    errors.append("Current price is NaN")
                else:
                    price_context["current_price"] = float(current_price)
            except Exception:
                errors.append("Failed to fetch current price")

            # 30-day drawdown (trading days)
            if len(hist) >= 30:
                try:
                    price_30d_ago = hist.iloc[-30]["Close"]

                    if pd.isna(price_30d_ago):
                        errors.append("30-day historical price is NaN")
                    elif price_30d_ago == 0:
                        errors.append("30-day historical price is zero")
                    elif price_context["current_price"] is not None:
                        drawdown = (
                            price_context["current_price"] - price_30d_ago
                        ) / price_30d_ago
                        price_context["stock_drawdown_30d"] = round(float(drawdown), 5)
                except Exception:
                    errors.append("Error calculating 30-day drawdown")
            else:
                errors.append("Insufficient data for 30-day drawdown")

            # 52-week range
            try:
                low_52w = hist["Low"].min()
                high_52w = hist["High"].max()

                if pd.isna(low_52w) or low_52w == 0:
                    errors.append("Invalid 52-week low value")
                elif price_context["current_price"] is not None:
                    price_context["distance_from_52w_low"] = round(
                        (price_context["current_price"] - low_52w) / low_52w, 5
                    )

                if pd.isna(high_52w) or high_52w == 0:
                    errors.append("Invalid 52-week high value")
                elif price_context["current_price"] is not None:
                    price_context["distance_from_52w_high"] = round(
                        (price_context["current_price"] - high_52w) / high_52w, 5
                    )

            except Exception:
                errors.append("Error calculating 52-week range metrics")

        except Exception as e:
            errors.append(f"yfinance error: {str(e)}")

        # Final assignment
        ticker_data["price_context"] = price_context
