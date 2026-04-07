"""Central registry for all enrichers."""

import logging
from typing import List, Tuple
from .base_enricher import BaseEnricher

logger = logging.getLogger(__name__)


class EnrichmentRegistry:
    """
    Central registry for all enrichers.
    Manages enrichment order and execution.
    """
    
    def __init__(self):
        self._enrichers: List[Tuple[int, BaseEnricher]] = []
    
    def register(self, order: int, enricher: BaseEnricher) -> None:
        """
        Register an enricher with execution order.
        
        Args:
            order: Execution order (1, 2, 3, etc.)
            enricher: Enricher instance to register
        """
        self._enrichers.append((order, enricher))
        self._enrichers.sort(key=lambda x: x[0])  # Sort by order
        logger.info(f"Registered: [{order}] {enricher.__class__.__name__}")
    
    def enrich_all(self, grouped_data: dict) -> dict:
        """
        Run all registered enrichers on grouped data.
        
        Args:
            grouped_data: Grouped pipeline output with 'tickers' dict
            
        Returns:
            Enriched grouped data
        """
        tickers_data = grouped_data.get("tickers", {})
        total_tickers = len(tickers_data)
        total_enrichers = len(self._enrichers)
        
        logger.info(f"Starting enrichment: {total_enrichers} steps × {total_tickers} tickers")
        
        for order, enricher in self._enrichers:
            enricher_name = enricher.__class__.__name__
            logger.info(f"[Step {order}/{total_enrichers}] {enricher_name}")
            
            for ticker_idx, (ticker, ticker_data) in enumerate(tickers_data.items(), 1):
                logger.info(f"  [{ticker_idx}/{total_tickers}] {ticker}")
                enricher.safe_enrich(ticker, ticker_data)
        
        logger.info("✓ All enrichments complete")
        return grouped_data


# Global registry instance
registry = EnrichmentRegistry()
