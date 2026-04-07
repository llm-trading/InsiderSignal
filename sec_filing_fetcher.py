import re
import logging
from bs4 import BeautifulSoup
from seleniumbase import SB

logger = logging.getLogger(__name__)


class SecFilingFetcher:
    """
    Fetches and parses a single SEC Form 4 filing page from openinsider.com.

    Uses SeleniumBase (undetected-chrome, headless) to avoid bot detection
    when fetching many filing URLs in quick succession.
    """

    def fetch_and_parse(self, filing_url: str, cache=None) -> dict:
        """
        Fetch the filing page and return structured data.

        Checks the cache first (if provided). On a miss, fetches via Selenium,
        parses the result, and stores it in the cache before returning.

        Args:
            filing_url: Absolute or root-relative URL to the openinsider filing page.
            cache:      Optional SecFilingCache instance for read-through caching.

        Returns:
            Dict with keys: source_url, row_count, table_rows, explanation_rows.
            On failure: Dict with keys: error, filing_url, message.
        """
        if not filing_url:
            return {"error": "no filing URL provided"}

        if filing_url.startswith("/"):
            filing_url = "https://openinsider.com" + filing_url

        # Cache read
        if cache is not None:
            cached = cache.get(filing_url)
            if cached is not None:
                return cached

        logger.info("Fetching SEC filing: %s", filing_url)
        try:
            with SB(uc=True, headless2=True) as sb:
                sb.open(filing_url)
                sb.wait_for_element("body", timeout=30)
                html = sb.get_page_source()
        except Exception as exc:
            logger.error("Failed to fetch filing %s: %s", filing_url, exc)
            return {"error": "fetch_failed", "filing_url": filing_url, "message": str(exc)}

        soup = BeautifulSoup(html, "html.parser")
        table_rows = self._parse_table_i(soup)
        explanation = self._parse_explanation_rows(soup)

        result = {
            "source_url": filing_url,
            "row_count": len(table_rows),
            "table_rows": table_rows,
            "explanation_rows": explanation,
        }

        # Cache write
        if cache is not None:
            cache.set(filing_url, result)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_table_i(self, soup: BeautifulSoup) -> list:
        """Find 'Table I - Non-Derivative Securities Acquired' and extract rows."""
        table = None
        for t in soup.find_all("table"):
            heading = t.find("th")
            if heading and "Table I - Non-Derivative Securities Acquired" in heading.get_text():
                table = t
                break

        if not table:
            logger.warning("Table I not found in filing page")
            return []

        headers = self._parse_table_headers(table)

        tbody = table.find("tbody")
        raw_rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

        rows = []
        for tr in raw_rows:
            tds = tr.find_all("td")
            if not tds:
                continue
            row_data = {}
            for i, td in enumerate(tds):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_data[key] = self._clean(td.get_text(" ", strip=True))
            rows.append(row_data)

        return rows

    def _parse_table_headers(self, table) -> list:
        """Parse multi-row / colspan/rowspan table headers into flat list."""
        thead = table.find("thead")
        if not thead:
            return []

        rows = thead.find_all("tr")
        if not rows:
            return []

        # Skip decorative first row if present
        if len(rows) > 1 and "table i" in rows[0].get_text().lower():
            rows = rows[1:]

        row_count = len(rows)
        matrix = [[] for _ in range(row_count)]

        for r, row in enumerate(rows):
            col_idx = 0
            for th in row.find_all("th"):
                while col_idx < len(matrix[r]) and matrix[r][col_idx] is not None:
                    col_idx += 1

                text = self._clean(th.get_text())
                colspan = int(th.get("colspan", 1))
                rowspan = int(th.get("rowspan", 1))

                for dr in range(rowspan):
                    rr = r + dr
                    if rr >= row_count:
                        continue
                    for dc in range(colspan):
                        cc = col_idx + dc
                        while len(matrix[rr]) <= cc:
                            matrix[rr].append(None)
                        if matrix[rr][cc] is None:
                            matrix[rr][cc] = text

                col_idx += colspan

        num_cols = max((len(rw) for rw in matrix), default=0)
        headers = []
        for c in range(num_cols):
            parts = []
            for r in range(row_count):
                val = matrix[r][c] if c < len(matrix[r]) else None
                if val and (not parts or parts[-1] != val):
                    parts.append(val)
            headers.append(" | ".join(parts))

        return headers

    def _parse_explanation_rows(self, soup: BeautifulSoup) -> dict:
        """Extract and normalise the 'Explanation of Responses' section."""
        raw_rows = []
        for t in soup.find_all("table"):
            first_td = t.find("td", class_="MedSmallFormText")
            if first_td and "Explanation of Responses:" in first_td.get_text():
                for tr in t.find_all("tr"):
                    td_fn = tr.find("td", class_="FootnoteData")
                    td_ft = tr.find("td", class_="FormText")
                    if td_fn:
                        val = self._clean(td_fn.get_text(" ", strip=True))
                        if val:
                            raw_rows.append(val)
                    elif td_ft:
                        val = self._clean(td_ft.get_text(" ", strip=True))
                        if val:
                            raw_rows.append(val)
                break

        return self._normalize_explanation_rows(raw_rows)

    def _normalize_explanation_rows(self, explanation_rows: list) -> dict:
        """
        Convert raw explanation text lines into structured footnotes + remarks.

        Returns:
            {
                "foot_notes": {"1": "...", "unlabeled": [...]},
                "Remarks": "..."
            }
        """
        foot_notes = {}
        remarks_parts = []
        in_remarks = False

        for row in explanation_rows:
            text = self._clean(row)
            if not text:
                continue

            if not in_remarks and text.lower().startswith("remarks:"):
                in_remarks = True
                remainder = text[len("Remarks:"):].strip()
                if remainder:
                    remarks_parts.append(remainder)
                continue

            if in_remarks:
                remarks_parts.append(text)
                continue

            m = re.match(r"^\s*[\[\(]?(\d+)[\]\.\)]\s*([\s\S]*)", text, re.DOTALL)
            if m:
                foot_notes[m.group(1)] = m.group(2).strip()
                continue

            foot_notes.setdefault("unlabeled", []).append(text)

        return {
            "foot_notes": foot_notes,
            "Remarks": " ".join(remarks_parts).strip(),
        }

    @staticmethod
    def _clean(value) -> str:
        """Strip and remove non-ASCII characters."""
        if value is None:
            return ""
        return str(value).strip().encode("ascii", "ignore").decode("ascii")
