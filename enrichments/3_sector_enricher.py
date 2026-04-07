"""Sector context enricher."""

import yfinance as yf
import pandas as pd
from .base_enricher import BaseEnricher


# Mapping sector → ETF proxy
SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Financial": "XLF",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC"
}


def get_30d_return(hist, errors, label):
    """Calculate 30-day return from price history."""
    if hist is None or hist.empty:
        errors.append(f"{label} price data not available")
        return None

    hist = hist.sort_index()

    if len(hist) < 30:
        errors.append(f"Insufficient data for {label} 30D return")
        return None

    try:
        current = hist["Close"].iloc[-1]
        past = hist["Close"].iloc[-30]

        if pd.isna(current) or pd.isna(past):
            errors.append(f"{label} price contains NaN")
            return None

        if past == 0:
            errors.append(f"{label} past price is zero")
            return None

        return round(float((current - past) / past), 5)

    except Exception:
        errors.append(f"Error calculating {label} 30D return")
        return None


class SectorEnricher(BaseEnricher):
    """Enriches ticker data with sector context."""
    
    def get_context_key(self) -> str:
        return "sector_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add sector context to ticker_data."""
        # Default schema
        sector_context = {
            "has_sector_data": False,
            "data_source": "none",
            "sector_name": "UNKNOWN",
            "sector_etf": None,
            "sector_return_30d": None,
            "stock_return_30d": None,
            "stock_vs_sector_30d": None,
            "errors": []
        }

        errors = sector_context["errors"]

        try:
            stock = yf.Ticker(ticker)

            # Get sector info
            try:
                info = stock.info
                if not info:
                    errors.append("Stock info not available from yfinance")
                    ticker_data["sector_context"] = sector_context
                    return

                sector_name = info.get("sector", "UNKNOWN")

                if sector_name == "UNKNOWN":
                    errors.append("Sector not found in stock info")

                sector_context["sector_name"] = sector_name

            except Exception as e:
                errors.append(f"Error fetching stock info: {str(e)}")
                ticker_data["sector_context"] = sector_context
                return

            # Map to ETF
            sector_etf = SECTOR_ETF_MAP.get(sector_name)

            if not sector_etf:
                errors.append(f"No ETF mapping found for sector: {sector_name}")
                ticker_data["sector_context"] = sector_context
                return

            sector_context["sector_etf"] = sector_etf

            # Fetch price data
            try:
                stock_hist = stock.history(period="2mo")
                sector_hist = yf.Ticker(sector_etf).history(period="2mo")
            except Exception as e:
                errors.append(f"Error fetching price history: {str(e)}")
                ticker_data["sector_context"] = sector_context
                return

            # Compute returns
            stock_return = get_30d_return(stock_hist, errors, "stock")
            sector_return = get_30d_return(sector_hist, errors, "sector")

            if stock_return is not None:
                sector_context["stock_return_30d"] = stock_return

            if sector_return is not None:
                sector_context["sector_return_30d"] = sector_return

            if stock_return is not None and sector_return is not None:
                sector_context["stock_vs_sector_30d"] = round(
                    stock_return - sector_return, 5
                )

            sector_context["has_sector_data"] = True
            sector_context["data_source"] = "yfinance"

        except Exception as e:
            errors.append(f"yfinance error: {str(e)}")

        # Final assignment
        ticker_data["sector_context"] = sector_context
