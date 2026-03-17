from seleniumbase import SB
import json

url = "http://www.sec.gov/Archives/edgar/data/875657/000093343026000002/xslF345X03/primary_doc.xml"

def clean_text(value):
    if value is None:
        return ""
    return value.strip().encode("ascii", "ignore").decode("ascii")

print("[INFO] Fetching URL via SeleniumBase", url)

with SB(uc=True, headless2=False) as sb:
    sb.open(url)
    sb.wait_for_element("body", timeout=30)
    xml_content = sb.get_page_source()

# parse xml_content as before
from bs4 import BeautifulSoup
soup = BeautifulSoup(xml_content, "html.parser")

table = None
for t in soup.find_all("table"):
    heading = t.find("th")
    if heading and "Table I - Non-Derivative Securities Acquired" in heading.get_text():
        table = t
        break

if table is None:
    raise ValueError("Unable to locate Table I in XML at " + url)

def parse_table_headers(table):
    thead = table.find('thead')
    if not thead:
        return []

    rows = thead.find_all('tr')
    if not rows:
        return []

    # remove top title row if it's the Table I caption row
    if len(rows) > 1 and 'table i' in rows[0].get_text().lower():
        rows = rows[1:]

    row_count = len(rows)
    matrix = [[] for _ in range(row_count)]

    for r, row in enumerate(rows):
        col_idx = 0
        for th in row.find_all('th'):
            while col_idx < len(matrix[r]) and matrix[r][col_idx] is not None:
                col_idx += 1

            text = clean_text(th.get_text())
            colspan = int(th.get('colspan', 1)) if th.get('colspan') else 1
            rowspan = int(th.get('rowspan', 1)) if th.get('rowspan') else 1

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

    num_cols = max(len(rw) for rw in matrix) if matrix else 0
    headers = []
    for c in range(num_cols):
        parts = []
        for r in range(row_count):
            val = matrix[r][c] if c < len(matrix[r]) else None
            if val and (not parts or parts[-1] != val):
                parts.append(val)
        headers.append(' | '.join(parts))
    return headers


header_cells = parse_table_headers(table)
# Define data rows from tbody (skip only header rows in thead)
if table.find('tbody'):
    table_rows = table.find('tbody').find_all('tr')
else:
    # if no tbody, skip header rows inside the table
    all_rows = table.find_all('tr')
    header_tr_count = len(table.find('thead').find_all('tr')) if table.find('thead') else 0
    table_rows = all_rows[header_tr_count:]

rows = []
for tr in table_rows:
    cells = tr.find_all("td")
    if not cells:
        continue
    row = {}
    for i, td in enumerate(cells):
        txt = clean_text(td.get_text(" ", strip=True))
        hrefs = [a.get("href") for a in td.find_all("a", href=True)]
        key = header_cells[i] if i < len(header_cells) else f"col_{i}"
        row[key] = txt
        if hrefs:
            row[f"{key}_href"] = hrefs[0] if len(hrefs) == 1 else hrefs
    rows.append(row)

# Locate and extract a potential "Explanation of Responses" table
explanation_data = []
for t in soup.find_all('table'):
    first_td = t.find('td', class_='MedSmallFormText')
    if first_td and 'Explanation of Responses:' in first_td.get_text():
        for tr in t.find_all('tr'):
            td_fn = tr.find('td', class_='FootnoteData')
            td_formtext = tr.find('td', class_='FormText')
            if td_fn:
                text = clean_text(td_fn.get_text(' ', strip=True))
                if text:
                    explanation_data.append(text)
            elif td_formtext:
                text = clean_text(td_formtext.get_text(' ', strip=True))
                if text:
                    explanation_data.append(text)
        break

out = {
    "source_url": url,
    "table_rows": rows,
    "row_count": len(rows),
    "explanation_rows": explanation_data,
}
with open("sec_filings_tableI.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("[INFO] Wrote sec_filings_tableI.json with", len(rows), "rows", "and", len(explanation_data), "explanation entries")