from seleniumbase import SB
import os
import re
import time
from bs4 import BeautifulSoup
import json
from CONSTANTS import OPENINSIDER_WITH_FILTERS_URL, INTERMEDIATE_HTML

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


def parse_saved_openinsider_html(intermediate_html=INTERMEDIATE_HTML):
    print(f'[INFO] Parsing saved HTML from {intermediate_html}')
    with open(intermediate_html, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')
    table = soup.find('table', class_='tinytable')
    if not table:
        raise ValueError(f'[ERROR] Could not find table.tinytable in {intermediate_html}')

    header_cells = parse_table_headers(table)

    data_rows = []
    tbody = table.find('tbody')
    if not tbody:
        table_rows = table.find_all('tr')[1:]
    else:
        table_rows = tbody.find_all('tr')

    for tr in table_rows:
        cell_values = []
        cell_links = []
        for td in tr.find_all('td'):
            text = clean_string(td.get_text())
            cell_values.append(text)
            links = [a.get('href') for a in td.find_all('a', href=True)]
            cell_links.append([clean_string(l) for l in links])

        if not cell_values:
            continue

        row_data = {}
        if header_cells and len(cell_values) == len(header_cells):
            for idx, header in enumerate(header_cells):
                row_data[header] = cell_values[idx]
                if cell_links[idx]:
                    row_data[f'{header}_href'] = cell_links[idx] if len(cell_links[idx]) > 1 else cell_links[idx][0]
        else:
            for idx, value in enumerate(cell_values):
                key = f'col_{idx}'
                row_data[key] = value
                if cell_links[idx]:
                    row_data[f'{key}_href'] = cell_links[idx] if len(cell_links[idx]) > 1 else cell_links[idx][0]

        data_rows.append(row_data)

    finviz_href = ''
    results_div = soup.find('div', id='results')
    if results_div:
        finviz_link = results_div.find('a', href=True, string=lambda t: t and 'finviz' in t.lower())
        if finviz_link:
            finviz_href = finviz_link['href'].strip()

    return {
        'source_finviz_href': finviz_href,
        'rows': data_rows,
    }


def fetch_openinsider_rows(url=OPENINSIDER_WITH_FILTERS_URL, intermediate_html=INTERMEDIATE_HTML):
    print(f'[INFO] Loading OpenInsider screener page: {url}')
    with SB(uc=True, headless2=True) as sb:
        sb.open(url)
        sb.wait_for_element('table.tinytable', timeout=30)
        time.sleep(3)

        html_snapshot = sb.get_page_source()
        with open(intermediate_html, 'w', encoding='utf-8') as f:
            f.write(html_snapshot)

        print(f'[INFO] Saved HTML snapshot to {intermediate_html}')

    parsed_data = parse_saved_openinsider_html(intermediate_html)

    for idx, row in enumerate(parsed_data['rows'], start=1):
        filing_url = row.get('FilingDate_href') or ''
        if not filing_url:
            for key, value in row.items():
                if key.endswith('_href') and value:
                    filing_url = value
                    break

        if filing_url:
            row['sec_filing_data'] = fetch_sec_filing_data(filing_url)
            print(f'[INFO] Enriched row {idx} with SEC filing data (from {filing_url})')
        else:
            row['sec_filing_data'] = {'error': 'no filing URL found'}
            print(f'[WARNING] No filing URL for row {idx}')

    if os.path.exists(intermediate_html):
        try:
            os.remove(intermediate_html)
            print(f'[INFO] Removed {intermediate_html}')
        except OSError as exc:
            print(f'[WARNING] Could not remove {intermediate_html}: {exc}')

    return parsed_data


def filter_json_file(file_path, output_file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading file: {e}")
        return

    target_key = "3. Transaction Code (Instr. \n      8) | Code"
    original_rows = data.get('rows', [])
    processed_rows = []
    removed_tickers = []

    for row in original_rows:
        sec_data = row.get('sec_filing_data', {})
        table_rows = sec_data.get('table_rows', [])

        # Filter: keep only table_rows where the code is "P" or starts with "P ("
        filtered_table_rows = [
            tr for tr in table_rows 
            if str(tr.get(target_key, "")).strip().startswith("P")
        ]

        # Calculate the new count of valid 'P' rows
        new_row_count = len(filtered_table_rows)

        # Only keep the entire entry if row_count > 0
        if new_row_count > 0:
            row['sec_filing_data']['table_rows'] = filtered_table_rows
            row['sec_filing_data']['row_count'] = new_row_count
            processed_rows.append(row)
        else:
            ticker = row.get('Ticker', 'Unknown')
            removed_tickers.append(ticker)

    # Update main data object
    data['rows'] = processed_rows

    with open(output_file_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Summary Output
    print(f"--- Processing Complete ---")
    print(f"Initial Filings: {len(original_rows)}")
    print(f"Final Filings (with 'P' codes): {len(processed_rows)}")
    print(f"Dropped Filings: {len(removed_tickers)}")
    if removed_tickers:
        print(f"Sample of removed tickers: {', '.join(list(set(removed_tickers))[:10])}")