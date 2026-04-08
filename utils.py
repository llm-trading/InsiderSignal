"""Shared utilities for enrichment pipeline."""

import time
import logging
from bs4 import BeautifulSoup
from seleniumbase import SB
from datetime import datetime
import math


logger = logging.getLogger(__name__)

# Suppress SeleniumBase/UC CDP mode messages
logging.getLogger("seleniumbase").setLevel(logging.WARNING)
logging.getLogger("undetected_chromedriver").setLevel(logging.WARNING)
logging.getLogger("uc").setLevel(logging.WARNING)


def clean_string(value):
    """Strip and remove non-ASCII characters."""
    if value is None:
        return ''
    return str(value).strip().encode('ascii', 'ignore').decode('ascii')


def parse_openinsider_table(html: str) -> dict:
    """
    Parse OpenInsider HTML table into structured data.
    
    Args:
        html: Raw HTML string from OpenInsider page
        
    Returns:
        Dict with 'rows' list containing transaction data
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='tinytable')
    
    if not table:
        logger.warning("No tinytable found in HTML")
        return {'rows': []}
    
    # Parse data rows
    data_rows = []
    tbody = table.find('tbody') or table
    
    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td')
        if not tds or len(tds) < 2:
            continue
        
        row_data = {}
        for i, td in enumerate(tds):
            text = clean_string(td.get_text())
            
            # Map columns by position (OpenInsider insider history table)
            if i == 1:  # Filing Date
                row_data['FilingDate'] = text
                link = td.find('a', href=True)
                if link:
                    href = link['href']
                    if href.startswith('/'):
                        href = f'http://openinsider.com{href}'
                    row_data['FilingDate_href'] = href
            elif i == 2:  # Trade Date
                row_data['TradeDate'] = text
            elif i == 3:  # Ticker
                row_data['Ticker'] = text
            elif i == 7:  # Trade Type
                row_data['TradeType'] = text
        
        if row_data:
            data_rows.append(row_data)
    
    logger.debug(f"Parsed {len(data_rows)} rows from OpenInsider table")
    return {'rows': data_rows}


def fetch_openinsider_table(url: str) -> dict:
    """
    Fetch OpenInsider page and parse table (for insider history).
    
    Args:
        url: OpenInsider URL (typically insider profile page)
        
    Returns:
        Dict with 'rows' list containing transaction data
    """
    logger.debug(f"Fetching OpenInsider page: {url}")
    
    try:
        with SB(uc=True, headless2=True) as sb:
            sb.open(url)
            sb.wait_for_element('table.tinytable', timeout=30)
            time.sleep(3)
            html = sb.get_page_source()
        
        return parse_openinsider_table(html)
        
    except Exception as e:
        logger.error(f"Failed to fetch OpenInsider page: {str(e)}")
        return {'rows': []}


def compute_time_decay(trade_date_str, current_date=None, decay_lambda=0.05):
    if trade_date_str is None:
        return 1.0  # fallback (no penalty)

    try:
        trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
        current_date = current_date or datetime.utcnow()

        days = (current_date - trade_date).days
        days = max(days, 0)

        return math.exp(-decay_lambda * days)

    except:
        return 1.0  # fail-safe