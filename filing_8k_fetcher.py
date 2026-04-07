import logging
import os
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict

from edgar import Company, set_identity

logger = logging.getLogger(__name__)

# Set EDGAR identity
identity = os.getenv('EDGAR_IDENTITY', 'InsiderSignal Bot insider.signal@example.com')
set_identity(identity)

# Item classification dictionary
ITEM_CLASSIFICATION = {
    "1.01": {"description": "Material Agreement", "action": "KEEP", "logic": "New contracts or partnerships often precede growth."},
    "1.02": {"description": "Termination of Agreement", "action": "IGNORE", "logic": "Negative news; usually leads to selling, not buying."},
    "1.03": {"description": "Bankruptcy", "action": "IGNORE", "logic": "Too much risk; buying here is usually 'catching a knife.'"},
    "1.04": {"description": "Mine Safety", "action": "IGNORE", "logic": "Highly industry-specific; rarely a broad market signal."},
    "1.05": {"description": "Cybersecurity Incidents", "action": "KEEP", "logic": "Buying 3-10 days after a 'hack' report shows internal confidence in recovery."},
    "2.01": {"description": "Completion of M&A", "action": "KEEP", "logic": "Confirms the 'new' company is ready to operate."},
    "2.02": {"description": "Results of Ops (Earnings)", "action": "GOLD", "logic": "Primary Blackout Trigger. Best time to watch for buys."},
    "2.03": {"description": "Financial Obligation", "action": "IGNORE", "logic": "Usually just taking on debt; not a growth signal."},
    "2.04": {"description": "Triggering Events (Debt)", "action": "IGNORE", "logic": "Red flag; suggests financial distress."},
    "2.05": {"description": "Costs (Exit/Disposal)", "action": "IGNORE", "logic": "Restructuring noise."},
    "2.06": {"description": "Material Impairments", "action": "IGNORE", "logic": "Writing off assets; usually negative."},
    "3.01": {"description": "Delisting", "action": "IGNORE", "logic": "Massive red flag."},
    "3.02": {"description": "Unregistered Sales", "action": "IGNORE", "logic": "Dilution of shares; usually bad for price."},
    "3.03": {"description": "Modification of Rights", "action": "IGNORE", "logic": "Administrative/Legal changes."},
    "4.01": {"description": "Change in Accountant", "action": "IGNORE", "logic": "Often a sign of internal audit drama."},
    "4.02": {"description": "Non-Reliance (Error)", "action": "IGNORE", "logic": "Major red flag; financial statements were wrong."},
    "5.01": {"description": "Change in Control", "action": "KEEP", "logic": "Signals a potential buyout or major pivot."},
    "5.02": {"description": "Management Changes", "action": "IGNORE", "logic": "The Trap. New hires buy to 'look good.' Discard."},
    "5.03": {"description": "Articles/Bylaws", "action": "IGNORE", "logic": "Purely legal/administrative."},
    "5.04": {"description": "Trading Suspension", "action": "IGNORE", "logic": "Usually related to employee benefit plans."},
    "5.05": {"description": "Code of Ethics", "action": "IGNORE", "logic": "Compliance paperwork."},
    "5.07": {"description": "Shareholder Votes", "action": "IGNORE", "logic": "Routine annual meeting results."},
    "7.01": {"description": "Reg FD Disclosure", "action": "IGNORE", "logic": "Catch-all for 'Fair Disclosure' press releases."},
    "8.01": {"description": "Other Events", "action": "IGNORE", "logic": "'Kitchen sink' for minor news."},
    "9.01": {"description": "Financial Exhibits", "action": "IGNORE", "logic": "Just the attachments for the other items."}
}


class Filing8KFetcher:
    """
    Fetches 8-K/6-K filings for a given ticker symbol.
    
    For each ticker, attempts to fetch 8-K filings first. If none found,
    falls back to 6-K filings. Returns structured filing data with item
    classifications.
    """
    
    def __init__(self, months_back: int = 1, cache=None):
        """
        Initialize the 8K filing fetcher.
        
        Args:
            months_back: Number of months to look back from current date
            cache: Optional SecFilingCache instance for caching 8K filings
        """
        self.months_back = months_back
        self.cache = cache
    
    def fetch_filings(self, ticker: str) -> List[Dict]:
        """
        Fetch 8-K filings for a ticker. If none found, fetch 6-K filings.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        
        Returns:
            List of dictionaries containing filing information
        """
        try:
            start_date = (datetime.now() - relativedelta(months=self.months_back)).strftime('%Y-%m-%d')
            
            logger.info(f"Fetching 8-K filings for {ticker} from {start_date}")
            company = Company(ticker)
            
            # Try 8-K filings first
            filings_8k = company.get_filings(form="8-K").filter(date=f"{start_date}:")
            
            results = []
            
            if filings_8k and len(list(filings_8k)) > 0:
                logger.info(f"Found {len(list(filings_8k))} 8-K filing(s) for {ticker}")
                for filing in company.get_filings(form="8-K").filter(date=f"{start_date}:"):
                    filing_data = self._process_8k_filing(filing)
                    if filing_data:
                        results.append(filing_data)
            else:
                # Try 6-K filings
                logger.info(f"No 8-K filings found for {ticker}. Trying 6-K filings...")
                filings_6k = company.get_filings(form="6-K").filter(date=f"{start_date}:")
                
                if filings_6k and len(list(filings_6k)) > 0:
                    logger.info(f"Found {len(list(filings_6k))} 6-K filing(s) for {ticker}")
                    for filing in company.get_filings(form="6-K").filter(date=f"{start_date}:"):
                        filing_data = self._process_6k_filing(filing)
                        if filing_data:
                            results.append(filing_data)
                else:
                    logger.info(f"No 6-K filings found for {ticker}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {str(e)}")
            return []
    
    def _process_8k_filing(self, filing) -> Dict:
        """Process an 8-K filing and extract relevant information."""
        try:
            # Check cache first
            if self.cache:
                cached = self.cache.get_8k(filing.accession_number)
                if cached:
                    return cached
            
            filing_date = filing.filing_date.strftime('%Y-%m-%d') if hasattr(filing.filing_date, 'strftime') else str(filing.filing_date)
            
            # Get reporting date
            if hasattr(filing, 'period_of_report') and filing.period_of_report:
                if hasattr(filing.period_of_report, 'strftime'):
                    reporting_date = filing.period_of_report.strftime('%Y-%m-%d')
                else:
                    reporting_date = str(filing.period_of_report)
            else:
                reporting_date = filing_date
            
            # Get items and enrich with classification
            items = {}
            is_priority = False
            try:
                filing_obj = filing.obj()
                items_raw = filing_obj.items if hasattr(filing_obj, 'items') else []
                
                for item in items_raw:
                    match = re.search(r'(\d+\.\d+)', item)
                    if match:
                        item_num = match.group(1)
                        classification = ITEM_CLASSIFICATION.get(item_num, {
                            "description": "Unknown Item",
                            "action": "IGNORE"
                        })
                        items[item_num] = classification
                        
                        if classification.get('action') in ['GOLD', 'KEEP']:
                            is_priority = True
            except:
                items = {}
            
            result = {
                'accession_number': filing.accession_number,
                'filing_date': filing_date,
                'reporting_date': reporting_date,
                'filing_type': '8-K',
                'is_priority': is_priority,
                'items': items
            }
            
            # Cache the result
            if self.cache:
                self.cache.set_8k(filing.accession_number, result)
            
            return result
        except Exception as e:
            logger.error(f"Error processing 8-K filing: {str(e)}")
            return None
    
    def _process_6k_filing(self, filing) -> Dict:
        """Process a 6-K filing and extract relevant information."""
        try:
            # Check cache first
            if self.cache:
                cached = self.cache.get_8k(filing.accession_number)
                if cached:
                    return cached
            
            filing_date = filing.filing_date.strftime('%Y-%m-%d') if hasattr(filing.filing_date, 'strftime') else str(filing.filing_date)
            
            # Get reporting date
            if hasattr(filing, 'period_of_report') and filing.period_of_report:
                if hasattr(filing.period_of_report, 'strftime'):
                    reporting_date = filing.period_of_report.strftime('%Y-%m-%d')
                else:
                    reporting_date = str(filing.period_of_report)
            else:
                reporting_date = filing_date
            
            # 6-K filings don't have items
            result = {
                'accession_number': filing.accession_number,
                'filing_date': filing_date,
                'reporting_date': reporting_date,
                'filing_type': '6-K',
                'is_priority': False,
                'items': {}
            }
            
            # Cache the result
            if self.cache:
                self.cache.set_8k(filing.accession_number, result)
            
            return result
        except Exception as e:
            logger.error(f"Error processing 6-K filing: {str(e)}")
            return None
