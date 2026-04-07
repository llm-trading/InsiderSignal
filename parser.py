import logging
from typing import Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Columns when fetching all tickers (includes Company Name)
COLUMNS_ALL = [
    'X', 'Filing Date', 'Trade Date', 'Ticker', 'Company Name',
    'Insider Name', 'Title', 'Trade Type', 'Price', 'Qty',
    'Owned', 'ΔOwn', 'Value', '1d', '1w', '1m', '6m',
]
LINK_COLUMNS_ALL = ['Filing Date', 'Ticker', 'Company Name', 'Insider Name']

# Columns when fetching a specific ticker (no Company Name)
COLUMNS_TICKER = [
    'X', 'Filing Date', 'Trade Date', 'Ticker',
    'Insider Name', 'Title', 'Trade Type', 'Price', 'Qty',
    'Owned', 'ΔOwn', 'Value', '1d', '1w', '1m', '6m',
]
LINK_COLUMNS_TICKER = ['Filing Date', 'Ticker', 'Insider Name']


class OpenInsiderParser:
    """Parses OpenInsider HTML into a list of transaction dicts."""

    def parse(self, html: str, ticker: str = None) -> Tuple[list, str]:
        """
        Parse the HTML page and return transactions plus the Finviz URL.

        Args:
            html:   Raw HTML string from the OpenInsider screener page.
            ticker: If provided, uses the ticker-specific column layout
                    (no Company Name column). Pass None for the all-tickers layout.

        Returns:
            Tuple of (transactions: list[dict], finviz_url: str | None).
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract Finviz link (present on ticker-specific pages)
        finviz_url = None
        finviz_link = soup.find('a', href=lambda h: h and 'finviz.com/quote.ashx' in h)
        if finviz_link:
            finviz_url = finviz_link.get('href')
            logger.info("Found Finviz URL: %s", finviz_url)

        table = soup.find('table', {'class': 'tinytable'})
        if not table:
            logger.warning("No 'tinytable' found in HTML")
            return [], finviz_url

        column_names = COLUMNS_TICKER if ticker else COLUMNS_ALL
        link_columns = LINK_COLUMNS_TICKER if ticker else LINK_COLUMNS_ALL

        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')

        data = []
        for row in rows:
            cols = row.find_all('td')
            if not cols or len(cols) < 2:
                continue

            row_data = self._extract_row(cols, column_names, link_columns)

            if row_data.get('Ticker') or row_data.get('Insider Name'):
                data.append(row_data)

        logger.info("Parsed %d transactions", len(data))
        return data, finviz_url

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_row(self, cols: list, column_names: list, link_columns: list) -> dict:
        """Extract a single table row into a dict."""
        row_data = {}
        for i, col in enumerate(cols):
            if i >= len(column_names):
                break
            col_name = column_names[i]
            row_data[col_name] = col.get_text(strip=True)

            if col_name in link_columns:
                link = col.find('a')
                href = link.get('href') if link else None
                if href and href.startswith('/'):
                    href = f"http://openinsider.com{href}"
                row_data[f"{col_name}_link"] = href

        return row_data
