import json
import logging
from datetime import datetime
from pathlib import Path

from CONSTANTS import OPENINSIDER_WITH_FILTERS_URL, OPENINSIDER_WITH_FILTERS_TICKER_URL
from cleaner import TransactionCleaner
from fetcher import OpenInsiderFetcher
from filing_8k_fetcher import Filing8KFetcher
from filter import TransactionFilter
from grouper import TransactionGrouper
from parser import OpenInsiderParser
from sec_filing_cache import SecFilingCache
from sec_filing_fetcher import SecFilingFetcher
from enrichments import registry
from signal_generator import SignalGenerator

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"


class OpenInsiderPipeline:
    """
    Orchestrates fetching, parsing, SEC filing enrichment, filtering,
    and ticker-grouping of OpenInsider data.

    Usage:
        pipeline = OpenInsiderPipeline()
        flat, grouped = pipeline.run()         # all tickers
        flat, grouped = pipeline.run("AAPL")   # specific ticker (no SEC / filter / group)
    """

    def __init__(self):
        self._fetcher = OpenInsiderFetcher()
        self._parser = OpenInsiderParser()
        self._sec_fetcher = SecFilingFetcher()
        self._cache = SecFilingCache()
        self._filter = TransactionFilter()
        self._cleaner = TransactionCleaner()
        self._grouper = TransactionGrouper()
        self._filing_8k_fetcher = Filing8KFetcher(months_back=1, cache=self._cache)
        self._signal_generator = SignalGenerator()

    def run(self, ticker: str = None) -> tuple:
        """
        Full pipeline run.

        Args:
            ticker: Stock ticker symbol (e.g. 'AAPL'). None = fetch all filtered results.

        Returns:
            Tuple of (flat_result, grouped_result).
            grouped_result is None when a specific ticker is requested.
        """
        url = self._build_url(ticker)
        logger.info("Starting pipeline for %s", ticker or "ALL tickers")

        response = self._fetcher.fetch(url)
        transactions, finviz_url = self._parser.parse(response.text, ticker=ticker)

        flat = self._build_output(transactions, ticker, url, finviz_url)

        grouped = None
        if ticker is None:
            flat = self._enrich_with_sec_filings(flat)
            flat = self._filter.filter_by_purchase_code(flat)
            flat = self._cleaner.clean(flat)
            grouped = self._grouper.group_by_ticker(flat)
            grouped = self._enrich_with_8k_filings(grouped)
            grouped = self._enrich_with_context(grouped)
            grouped = self._generate_signals(grouped)

        logger.info("Pipeline complete — %d transactions", flat["total_transactions"])
        return flat, grouped

    def save(self, flat: dict, grouped: dict = None) -> tuple:
        """
        Save flat and (optionally) grouped results to the output directory.

        Returns:
            Tuple of (flat_path, grouped_path). grouped_path is None if not saved.
        """
        OUTPUT_DIR.mkdir(exist_ok=True)
        ticker_label = flat.get("ticker", "ALL")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        flat_path = OUTPUT_DIR / f"{ticker_label}_insider_trades_{timestamp}.json"
        self._write_json(flat, flat_path)
        logger.info("Flat JSON saved to %s", flat_path)

        grouped_path = None
        if grouped is not None:
            grouped_path = OUTPUT_DIR / f"{ticker_label}_insider_trades_grouped_{timestamp}.json"
            self._write_json(grouped, grouped_path)
            logger.info("Grouped JSON saved to %s", grouped_path)

        return flat_path, grouped_path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _enrich_with_sec_filings(self, result: dict) -> dict:
        transactions = result["transactions"]
        total = len(transactions)
        logger.info("Enriching %d transactions with SEC filing data", total)

        for i, tx in enumerate(transactions, start=1):
            filing_url = tx.get("Filing Date_link")
            logger.info("Fetching SEC filing %d/%d — %s", i, total, tx.get("Ticker", "?"))
            tx["sec_filing_data"] = self._sec_fetcher.fetch_and_parse(
                filing_url, cache=self._cache
            )

        result["transactions"] = transactions
        return result

    def _enrich_with_8k_filings(self, grouped: dict) -> dict:
        """
        Enrich grouped data with 8-K/6-K filings for each ticker.
        
        Args:
            grouped: Grouped result dict with tickers
            
        Returns:
            Updated grouped dict with 8K filing data added to each ticker
        """
        tickers_data = grouped.get("tickers", {})
        total_tickers = len(tickers_data)
        
        logger.info("Enriching %d tickers with 8-K/6-K filing data", total_tickers)
        
        for i, (ticker, ticker_data) in enumerate(tickers_data.items(), start=1):
            logger.info("Fetching 8-K/6-K filings %d/%d — %s", i, total_tickers, ticker)
            filings = self._filing_8k_fetcher.fetch_filings(ticker)
            ticker_data["eightK_filings"] = filings
        
        grouped["tickers"] = tickers_data
        return grouped

    def _enrich_with_context(self, grouped: dict) -> dict:
        """
        Enrich grouped data with all context enrichers (earnings, price, sector, etc.).
        
        Args:
            grouped: Grouped result dict with tickers
            
        Returns:
            Updated grouped dict with all enrichment contexts added
        """
        logger.info("Starting context enrichment")
        grouped = registry.enrich_all(grouped)
        logger.info("Context enrichment complete")
        return grouped

    def _generate_signals(self, grouped: dict) -> dict:
        """
        Generate buy signals from enriched data.
        
        Args:
            grouped: Grouped result dict with enriched ticker data
            
        Returns:
            Updated grouped dict with signals added to each ticker
        """
        logger.info("Starting signal generation")
        signals = self._signal_generator.score_dataset(grouped)
        
        # Add signals to each ticker
        tickers_data = grouped.get("tickers", {})
        for ticker, signal_data in signals.items():
            if ticker in tickers_data:
                tickers_data[ticker]["signals"] = signal_data
        
        grouped["tickers"] = tickers_data
        logger.info("Signal generation complete")
        return grouped

    def _build_url(self, ticker: str) -> str:
        if ticker:
            return OPENINSIDER_WITH_FILTERS_TICKER_URL.format(ticker)
        return OPENINSIDER_WITH_FILTERS_URL

    def _build_output(self, transactions: list, ticker: str, url: str, finviz_url: str) -> dict:
        unique_tickers = {t.get("Ticker") for t in transactions if t.get("Ticker")}
        return {
            "ticker": ticker.upper() if ticker else "ALL",
            "fetch_date": datetime.now().isoformat(),
            "source_url": url,
            "finviz_url": finviz_url,
            "total_transactions": len(transactions),
            "unique_tickers": len(unique_tickers),
            "transactions": transactions,
        }

    @staticmethod
    def _write_json(data: dict, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
