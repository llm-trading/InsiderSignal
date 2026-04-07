"""Insider history context enricher."""

from datetime import date, timedelta, datetime
from .base_enricher import BaseEnricher
from sec_filing_fetcher import SecFilingFetcher
from sec_filing_cache import SecFilingCache
from utils import fetch_openinsider_table


TRANSACTION_CODE_KEY = "3. Transaction Code (Instr. \n      8) | Code"


def parse_trade_date(date_string):
    """Parse trade date from various formats."""
    if not date_string:
        return None
    
    try:
        return datetime.strptime(date_string.strip(), "%Y-%m-%d").date()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(date_string.strip().split()[0], "%Y-%m-%d").date()
    except ValueError:
        pass
    
    return None


def is_valid_purchase_transaction(filing_data):
    """Validate if SEC filing contains actual purchase transactions (code 'P')."""
    if not filing_data or filing_data.get("error"):
        return False
    
    table_rows = filing_data.get("table_rows", [])
    
    for row in table_rows:
        code = str(row.get(TRANSACTION_CODE_KEY, "")).strip()
        if code.startswith("P"):
            return True
    
    return False


class InsiderHistoryEnricher(BaseEnricher):
    """Enriches ticker data with historical insider behavior metrics."""
    
    def __init__(self):
        super().__init__()
        self.sec_fetcher = SecFilingFetcher()
        self.cache = SecFilingCache()
    
    def get_context_key(self) -> str:
        return "insider_history_context"
    
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """Add insider history context to ticker_data."""
        # Fixed schema
        insider_history_context = {
            "has_history_data": False,
            "insiders": [],
            "errors": []
        }
        
        errors = insider_history_context["errors"]
        
        try:
            transactions = ticker_data.get("insider_transactions", [])
            
            if not transactions:
                errors.append("No insider transactions available")
                ticker_data["insider_history_context"] = insider_history_context
                return
            
            # Build exclusion set
            known_filing_urls = set()
            for transaction in transactions:
                sec_url = transaction.get("sec_filing_data", {}).get("source_url")
                if sec_url:
                    known_filing_urls.add(sec_url)
            
            self.logger.debug(f"Built exclusion set: {len(known_filing_urls)} known filing URLs")
            
            # Process each unique insider
            valid_insiders = []
            processed_links = set()
            reference_date = date.today()
            
            for transaction in transactions:
                insider_name = transaction.get("Insider Name", "")
                insider_link = transaction.get("Insider Name_link", "")
                
                if not insider_link or insider_link in processed_links:
                    continue
                
                processed_links.add(insider_link)
                
                # Get metrics for this insider
                metrics = self._calculate_insider_metrics(
                    insider_link,
                    insider_name,
                    reference_date,
                    known_filing_urls
                )
                
                if metrics:
                    valid_insiders.append(metrics)
                else:
                    errors.append(f"{insider_name}: No valid transactions after filtering")
            
            # Set final state
            if valid_insiders:
                insider_history_context["has_history_data"] = True
                insider_history_context["insiders"] = valid_insiders
            else:
                if not errors:
                    errors.append("No valid insider data after processing all insiders")
        
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            self.logger.debug(f"Full traceback:", exc_info=True)
        
        # Final assignment
        ticker_data["insider_history_context"] = insider_history_context
    
    def _calculate_insider_metrics(self, insider_link, insider_name, reference_date, known_filing_urls):
        """Calculate metrics for a single insider with deduplication."""
        self.logger.debug(f"Fetching history for {insider_name}")
        
        try:
            # PHASE 1: Fetch insider profile page
            raw_data = fetch_openinsider_table(insider_link)
            
            if not raw_data or not raw_data.get("rows"):
                self.logger.debug(f"No transaction data found for {insider_name}")
                return None
            
            all_transactions = raw_data.get("rows", [])
            self.logger.debug(f"Fetched {len(all_transactions)} total transactions")
            
            # PHASE 2: PRE-FILTERING
            twelve_months_ago = reference_date - timedelta(days=365)
            six_months_ago = reference_date - timedelta(days=180)
            
            filtered_transactions = []
            
            for transaction in all_transactions:
                trade_type = transaction.get("TradeType", "")
                trade_date_str = transaction.get("TradeDate", "")
                ticker = transaction.get("Ticker", "")
                filing_link = transaction.get("FilingDate_href", "")
                
                # Filter 1: Skip duplicates
                if filing_link and filing_link in known_filing_urls:
                    continue
                
                # Filter 2: Skip non-purchases
                if not ("P - Purchase" in trade_type or trade_type.strip().startswith("P")):
                    continue
                
                # Filter 3: Skip old transactions
                trade_date = parse_trade_date(trade_date_str)
                if not trade_date or trade_date < twelve_months_ago:
                    continue
                
                filtered_transactions.append({
                    "date": trade_date,
                    "ticker": ticker,
                    "filing_link": filing_link,
                    "trade_type": trade_type
                })
            
            if not filtered_transactions:
                return None
            
            filtered_transactions.sort(key=lambda x: x["date"])
            
            # PHASE 3: SEC FILING VALIDATION
            validated_transactions = []
            
            for transaction in filtered_transactions:
                filing_link = transaction.get("filing_link", "")
                
                if not filing_link:
                    validated_transactions.append(transaction)
                    continue
                
                # Fetch SEC filing to verify transaction code
                filing_data = self.sec_fetcher.fetch_and_parse(filing_link, cache=self.cache)
                
                if is_valid_purchase_transaction(filing_data):
                    validated_transactions.append(transaction)
            
            if not validated_transactions:
                return None
            
            # PHASE 4: Calculate metrics
            total_buys_6m = sum(
                1 for t in validated_transactions 
                if t["date"] >= six_months_ago
            )
            
            total_buys_12m = len(validated_transactions)
            
            past_purchases = [t for t in validated_transactions if t["date"] < reference_date]
            if past_purchases:
                most_recent = max(past_purchases, key=lambda x: x["date"])
                days_since_last_buy = (reference_date - most_recent["date"]).days
            else:
                days_since_last_buy = None
            
            if len(validated_transactions) > 1:
                gaps = []
                for i in range(1, len(validated_transactions)):
                    gap = (validated_transactions[i]["date"] - validated_transactions[i-1]["date"]).days
                    gaps.append(gap)
                avg_days_between_buys = round(sum(gaps) / len(gaps), 1)
            else:
                avg_days_between_buys = None
            
            unique_companies = set(t["ticker"] for t in validated_transactions if t["ticker"])
            unique_companies_bought = len(unique_companies)
            
            return {
                "name": insider_name,
                "insider_link": insider_link,
                "total_buys_6m": total_buys_6m,
                "total_buys_12m": total_buys_12m,
                "days_since_last_buy": days_since_last_buy,
                "avg_days_between_buys": avg_days_between_buys,
                "unique_companies_bought": unique_companies_bought
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process {insider_name}: {str(e)}")
            return None
