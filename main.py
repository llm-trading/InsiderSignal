"""
Entry point for the OpenInsider pipeline.

Usage:
    python main.py           # fetch all filtered insider trades + SEC enrichment + filter
    python main.py AAPL      # fetch trades for a specific ticker only
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

from pipeline import OpenInsiderPipeline


class _SuppressCDPFilter(logging.Filter):
    """Drop the noisy SeleniumBase UC/CDP mode banner lines."""

    _SUPPRESSED = (
        "CDP Mode",
        "UC Mode",
        "open() in UC Mode",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(s in msg for s in self._SUPPRESSED)


def _configure_logging():
    """Configure two-tier logging: console (INFO) + file (DEBUG)."""
    
    # Create logs directory
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{timestamp}.log"
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything
    
    # Console handler (INFO level - clean output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler (DEBUG level - detailed output)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    cdp_filter = _SuppressCDPFilter()
    logging.getLogger("seleniumbase").setLevel(logging.WARNING)
    logging.getLogger("seleniumbase").addFilter(cdp_filter)
    logging.getLogger("undetected_chromedriver").setLevel(logging.WARNING)
    logging.getLogger("undetected_chromedriver").addFilter(cdp_filter)
    logging.getLogger("uc").setLevel(logging.WARNING)
    logging.getLogger("uc").addFilter(cdp_filter)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpxthrottlecache").setLevel(logging.WARNING)
    logging.getLogger("edgar").setLevel(logging.WARNING)
    
    # Log the file location
    logging.info(f"Detailed logs: {log_file}")


logger = logging.getLogger(__name__)


def main():
    _configure_logging()

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else None

    pipeline = OpenInsiderPipeline()
    flat, grouped = pipeline.run(ticker=ticker)
    flat_path, grouped_path = pipeline.save(flat, grouped)

    logger.info(
        "Done — %d transactions for %s | flat: %s%s",
        flat["total_transactions"],
        flat["ticker"],
        flat_path,
        f" | grouped: {grouped_path}" if grouped_path else "",
    )

    # Generate HTML reports (only for grouped data)
    if grouped_path:
        try:
            from generate_html_report import generate_report
            from generate_index import update_index
            
            logger.info("Generating HTML reports...")
            report_path = generate_report(str(grouped_path))
            logger.info(f"Report generated: {report_path}")
            
            index_path = update_index()
            logger.info(f"Index updated: {index_path}")
        except Exception as e:
            logger.error(f"Failed to generate HTML reports: {e}", exc_info=True)


if __name__ == "__main__":
    main()
