"""Earnings context enricher."""

import yfinance as yf
import pandas as pd
from datetime import timedelta
from .base_enricher import BaseEnricher


def extract_reporting_date_and_signal(eightk_filings, errors):
    """Extract reporting date and signal strength from 8-K filings."""
    if not eightk_filings:
        errors.append("No 8-K filings present")
        return None, "NONE"

    gold_dates = []
    keep_dates = []

    for filing in eightk_filings:
        if not filing.get("is_priority", False):
            continue

        reporting_date = filing.get("reporting_date")
        if not reporting_date:
            errors.append("Missing reporting_date in a priority filing")
            continue

        items = filing.get("items", {})

        for item in items.values():
            action = item.get("action")

            if action == "GOLD":
                gold_dates.append(reporting_date)
            elif action == "KEEP":
                keep_dates.append(reporting_date)

    # Decision logic
    if gold_dates:
        return max(gold_dates), "GOLD"

    if keep_dates:
        return max(keep_dates), "KEEP"

    errors.append("No GOLD or KEEP actions found in priority filings")
    return None, "NONE"


class EarningsEnricher(BaseEnricher):
    """Enriches ticker data with earnings context."""
    
    def get_context_key(self) -> str:
        return "earnings_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add earnings context to ticker_data."""
        # Fixed schema
        earnings_context = {
            "has_earnings_8k": False,
            "reporting_date": None,
            "earnings_signal_strength": "NONE",
            "price_change_1d_post_earnings": None,
            "price_change_3d_post_earnings": None,
            "errors": []
        }

        errors = earnings_context["errors"]

        # Step 1: Extract reporting date + signal
        eightk_filings = ticker_data.get("eightK_filings", [])

        reporting_date, signal = extract_reporting_date_and_signal(
            eightk_filings, errors
        )

        earnings_context["earnings_signal_strength"] = signal

        if not reporting_date:
            errors.append("Reporting date not found")
            ticker_data["earnings_context"] = earnings_context
            return

        earnings_context["has_earnings_8k"] = True

        reporting_date = pd.to_datetime(reporting_date)
        earnings_context["reporting_date"] = reporting_date.strftime("%Y-%m-%d")

        # Step 2: Price reaction
        try:
            stock = yf.Ticker(ticker)

            # Increased buffer to ensure enough trading days
            start = reporting_date - timedelta(days=7)
            end = reporting_date + timedelta(days=10)

            price_df = stock.history(start=start, end=end)

            if price_df.empty:
                errors.append("Price data not available from yfinance")
                ticker_data["earnings_context"] = earnings_context
                return

            price_df = price_df.reset_index()
            price_df["Date"] = pd.to_datetime(price_df["Date"]).dt.tz_localize(None)
            price_df = price_df.sort_values("Date").reset_index(drop=True)

            def get_closest_idx(target_date):
                return (price_df["Date"] - target_date).abs().idxmin()

            # AMC → next trading day (T+1)
            base_idx = get_closest_idx(reporting_date + timedelta(days=1))

            def safe_get(idx, label):
                if 0 <= idx < len(price_df):
                    return price_df.loc[idx, "Close"]
                else:
                    errors.append(f"Missing price index for {label}")
                    return None

            close_prev = safe_get(base_idx - 1, "previous day close")
            close_1d = safe_get(base_idx, "1D post earnings")

            # Trading-day accurate future extraction (T+3)
            base_date = price_df.loc[base_idx, "Date"]
            future_prices = price_df[price_df["Date"] > base_date].reset_index(drop=True)

            close_3d = None
            if len(future_prices) >= 2:
                close_3d = future_prices.loc[1, "Close"]  # T+3
            else:
                errors.append("Insufficient future trading days for 3D post earnings")

            if close_prev is not None and close_1d is not None:
                earnings_context["price_change_1d_post_earnings"] = round(
                    (close_1d - close_prev) / close_prev, 5
                )

            if close_prev is not None and close_3d is not None:
                earnings_context["price_change_3d_post_earnings"] = round(
                    (close_3d - close_prev) / close_prev, 5
                )

        except Exception as e:
            errors.append(f"yfinance error: {str(e)}")

        # Final assignment
        ticker_data["earnings_context"] = earnings_context
