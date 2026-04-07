import time
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


class OpenInsiderFetcher:
    """Fetches a URL and returns the HTTP response."""

    def __init__(self, max_retries: int = 3, timeout: int = 60):
        self.max_retries = max_retries
        self.timeout = timeout

    def fetch(self, url: str) -> requests.Response:
        """Fetch the given URL with retry logic. Returns the Response object."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("Fetching URL (attempt %d/%d)", attempt, self.max_retries)
                response = requests.get(url, headers=HEADERS, timeout=self.timeout)
                response.raise_for_status()
                logger.info("Received %d bytes", len(response.content))
                return response
            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    wait = attempt * 5
                    logger.warning("Timeout on attempt %d. Retrying in %ds...", attempt, wait)
                    time.sleep(wait)
                else:
                    raise
            except requests.exceptions.RequestException as exc:
                if attempt < self.max_retries:
                    wait = attempt * 5
                    logger.warning("Request error: %s. Retrying in %ds...", exc, wait)
                    time.sleep(wait)
                else:
                    raise
