import json

def filter_json_file(file_path, output_file_path):
    # 1. Read the JSON data
    with open(file_path, 'r') as f:
        data = json.load(f)

    # 2. Process the data
    initial_count = len(data.get('rows', []))
    target_key = "3. Transaction Code (Instr. \n      8) | Code"
    
    original_rows = data.get('rows', [])
    processed_rows = []
    removed_tickers = []

    for row in original_rows:
        table_rows = row.get('sec_filing_data', {}).get('table_rows', [])
        # Check if any row in 'table_rows' has code "P"
        if any(tr.get(target_key) == "P" for tr in table_rows):
            processed_rows.append(row)
        else:
            removed_tickers.append(row.get('Ticker', 'Unknown'))

    # Update data with filtered rows
    data['rows'] = processed_rows
    final_count = len(processed_rows)

    # 3. Write modified data back to the SAME file
    with open(output_file_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Output results
    print(f"Entries before processing: {initial_count}")
    print(f"Entries after processing: {final_count}")
    print(f"Removed Tickers: {', '.join(removed_tickers) if removed_tickers else 'None'}")

# Usage
test_output_file = 'openinsider_data_2026-03-19_17-39-58Z_output.json'  # Replace with your actual file path
filter_json_file('openinsider_data_2026-03-19_17-39-58Z.json', test_output_file)
