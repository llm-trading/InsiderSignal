from seleniumbase import SB
import json
from bs4 import BeautifulSoup
import re

url = "http://www.sec.gov/Archives/edgar/data/1788451/000127328126000003/xslF345X03/form4-01312026_010122.xml"
# url = "http://www.sec.gov/Archives/edgar/data/812011/000081201126000017/xslF345X03/wk-form4_1773697795.xml"

def clean_string(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip().encode('ascii', 'ignore').decode('ascii')
    return str(value).strip().encode('ascii', 'ignore').decode('ascii')


def parse_table_headers(table):
    if not table:
        return []

    thead = table.find('thead')
    if not thead:
        return []

    rows = thead.find_all('tr')
    if not rows:
        return []

    if len(rows) > 1 and 'table i' in rows[0].get_text().lower():
        rows = rows[1:]

    row_count = len(rows)
    matrix = [[] for _ in range(row_count)]

    for r, row in enumerate(rows):
        col_idx = 0
        for th in row.find_all('th'):
            while col_idx < len(matrix[r]) and matrix[r][col_idx] is not None:
                col_idx += 1

            text = clean_string(th.get_text())
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

    num_cols = max((len(rw) for rw in matrix), default=0)
    headers = []
    for c in range(num_cols):
        parts = []
        for r in range(row_count):
            val = matrix[r][c] if c < len(matrix[r]) else None
            if val and (not parts or parts[-1] != val):
                parts.append(val)
        headers.append(' | '.join(parts))

    return headers


def normalize_explanation_rows(explanation_rows):
    foot_notes = {}
    remarks_parts = []
    in_remarks = False

    for row in explanation_rows:
        text = clean_string(row)
        if not text:
            continue

        if not in_remarks and text.lower().startswith('remarks:'):
            in_remarks = True
            remainder = text[len('Remarks:'):].strip()
            if remainder:
                remarks_parts.append(remainder)
            continue

        if in_remarks:
            remarks_parts.append(text)
            continue
        import pdb; pdb.set_trace()
        m = re.match(r'^\s*[\[\(]?(\d+)[\]\.\)]\s*([\s\S]*)', text, re.DOTALL)
        if m:
            foot_note_id = m.group(1)
            foot_note_text = m.group(2).strip()
            if foot_note_text:
                foot_notes[foot_note_id] = foot_note_text
            continue

        # If text does not match a numbered footnote and we are not in Remarks,
        # append it to a special key in case the source has unlabelled extra notes.
        foot_notes.setdefault('unlabeled', []).append(text)

    return {
        'foot_notes': foot_notes,
        'Remarks': ' '.join(remarks_parts).strip() if remarks_parts else ''
    }


def fetch_sec_filing_data(filing_url):
    if not filing_url:
        return {'error': 'no filing URL provided'}

    if filing_url.startswith('/'):
        filing_url = 'https://openinsider.com' + filing_url

    print(f'[INFO] Fetching SEC filing page: {filing_url}')
    try:
        with SB(uc=True, headless2=True) as sb:
            sb.open(filing_url)
            sb.wait_for_element('body', timeout=30)
            xml_content = sb.get_page_source()
    except Exception as exc:
        return {'error': 'fetch_failed', 'filing_url': filing_url, 'message': str(exc)}

    soup = BeautifulSoup(xml_content, 'html.parser')
    table = None

    for t in soup.find_all('table'):
        heading = t.find('th')
        if heading and 'Table I - Non-Derivative Securities Acquired' in heading.get_text():
            table = t
            break

    if not table:
        return {'source_url': filing_url, 'error': 'Table I not found'}

    header_cells = parse_table_headers(table)
    if table.find('tbody'):
        table_rows = table.find('tbody').find_all('tr')
    else:
        all_trs = table.find_all('tr')
        table_rows = all_trs[1:] if len(all_trs) > 1 else []

    extracted_rows = []
    for tr in table_rows:
        tds = tr.find_all('td')
        if not tds:
            continue
        row_data = {}
        for i, td in enumerate(tds):
            key = header_cells[i] if i < len(header_cells) else f'col_{i}'
            row_data[key] = clean_string(td.get_text(' ', strip=True))
        extracted_rows.append(row_data)

    explanation_rows = []
    for t in soup.find_all('table'):
        first_td = t.find('td', class_='MedSmallFormText')
        if first_td and 'Explanation of Responses:' in first_td.get_text():
            for tr in t.find_all('tr'):
                td_fn = tr.find('td', class_='FootnoteData')
                td_formtext = tr.find('td', class_='FormText')
                if td_fn:
                    value = clean_string(td_fn.get_text(' ', strip=True))
                    if value:
                        explanation_rows.append(value)
                elif td_formtext:
                    value = clean_string(td_formtext.get_text(' ', strip=True))
                    if value:
                        explanation_rows.append(value)
            break

    return {
        'source_url': filing_url,
        'row_count': len(extracted_rows),
        'table_rows': extracted_rows,
        'explanation_rows': normalize_explanation_rows(explanation_rows),
    }

out = fetch_sec_filing_data(url)
with open("sec_filings_tableI.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("[INFO] Wrote sec_filings_tableI.json with", len(out['table_rows']), "rows", "and", len(out['explanation_rows']), "explanation entries")