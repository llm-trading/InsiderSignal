'''
This code take raw json and filters any rows in filings which have trade with non-P code.
'''

import json

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

# Usage
filter_json_file('openinsider_data_2026-03-19_17-39-58Z.json', 'openinsider_filtered.json')