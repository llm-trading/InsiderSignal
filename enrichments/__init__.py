"""Enrichment system initialization and auto-registration."""

import importlib
from .enrichment_registry import registry

# Dynamically import enrichers (module names start with numbers)
earnings_module = importlib.import_module('.1_earnings_enricher', package='enrichments')
price_module = importlib.import_module('.2_price_enricher', package='enrichments')
sector_module = importlib.import_module('.3_sector_enricher', package='enrichments')
history_module = importlib.import_module('.4_insider_history_enricher', package='enrichments')
insider_price_module = importlib.import_module('.5_insider_price_enricher', package='enrichments')
sizing_module = importlib.import_module('.6_position_sizing_enricher', package='enrichments')
behavior_module = importlib.import_module('.7_insider_behavior_enricher', package='enrichments')

# Get enricher classes
EarningsEnricher = earnings_module.EarningsEnricher
PriceEnricher = price_module.PriceEnricher
SectorEnricher = sector_module.SectorEnricher
InsiderHistoryEnricher = history_module.InsiderHistoryEnricher
InsiderPriceEnricher = insider_price_module.InsiderPriceEnricher
PositionSizingEnricher = sizing_module.PositionSizingEnricher
InsiderBehaviorEnricher = behavior_module.InsiderBehaviorEnricher

# Auto-register all enrichers in execution order
registry.register(1, EarningsEnricher())
registry.register(2, PriceEnricher())
registry.register(3, SectorEnricher())
registry.register(4, InsiderHistoryEnricher())
registry.register(5, InsiderPriceEnricher())
registry.register(6, PositionSizingEnricher())
registry.register(7, InsiderBehaviorEnricher())

# Export registry for use in pipeline
__all__ = ['registry']
