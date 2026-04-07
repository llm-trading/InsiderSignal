"""Abstract base class for all enrichers."""

from abc import ABC, abstractmethod
import logging


class BaseEnricher(ABC):
    """
    Abstract base class for all enrichers.
    Enforces consistent interface and error handling.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_context_key(self) -> str:
        """Return the key name for this enrichment in ticker_data."""
        pass
    
    @abstractmethod
    def enrich(self, ticker: str, ticker_data: dict) -> None:
        """
        Enrich ticker_data in-place with context.
        
        Args:
            ticker: Stock ticker symbol
            ticker_data: Dict containing ticker information
        """
        pass
    
    def safe_enrich(self, ticker: str, ticker_data: dict) -> None:
        """
        Wrapper that handles errors gracefully.
        Logs success/failure and adds errors to context.
        """
        try:
            self.enrich(ticker, ticker_data)
            self.logger.info(f"✓ {ticker}")
            self.logger.debug(f"Successfully enriched {ticker} with {self.get_context_key()}")
        except Exception as e:
            self.logger.error(f"✗ {ticker}: {str(e)}")
            self.logger.debug(f"Full traceback for {ticker}:", exc_info=True)
            
            # Add error to context
            context_key = self.get_context_key()
            if context_key not in ticker_data:
                ticker_data[context_key] = {"errors": []}
            if "errors" not in ticker_data[context_key]:
                ticker_data[context_key]["errors"] = []
            ticker_data[context_key]["errors"].append(f"Enrichment failed: {str(e)}")
