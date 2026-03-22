'''
This code takes the filtered json and checks for the footnote mentioned in filings with
the P codes mentioned with the footnote. So as to analyze if its a NOISE or a SIGNAL.
'''

import ollama
import json
import sys
from pathlib import Path

def load_entries(file_path):
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    with p.open('r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('rows', [])


def determine_removed_rows(entries):
    target_key = "3. Transaction Code (Instr. \n      8) | Code"
    removed = []
    kept = []

    for row in entries:
        table_rows = row.get('sec_filing_data', {}).get('table_rows', [])
        if any(tr.get(target_key) == 'P' for tr in table_rows):
            kept.append(row)
        else:
            removed.append(row)

    return kept, removed


def run_test(data_file=None, model_name='sec-analyst-qwen2.5-7B-instruct-Q4_K_M'):
    if data_file is None:
        raise ValueError('data_file path is required')

    entries = load_entries(data_file)
    kept_rows, removed_rows = determine_removed_rows(entries)

    print(f"--- Starting SEC Signal Analysis ---")
    print(f"Total rows in source: {len(entries)}")
    print(f"Kept rows (code P detected): {len(kept_rows)}")
    print(f"Removed rows (no code P): {len(removed_rows)}\n")

    for i, entry in enumerate(removed_rows, start=1):
        ticker = entry.get('Ticker', 'Unknown')
        prompt = json.dumps(entry)

        try:
            response = ollama.chat(model=model_name, messages=[
                {'role': 'user', 'content': prompt}
            ])
            
            response = response['message']['content']            
            # response = ollama.generate(model=model_name, prompt=prompt)
            # analysis_text = response.get('response') if isinstance(response, dict) else str(response)
            print(f"Removed row {i}/{len(removed_rows)} (Ticker: {ticker}) analysis:")
            print(response)
            print("-" * 60)
        except Exception as e:
            print(f"Error processing removed row {i} (Ticker: {ticker}): {e}")
            print("-" * 60)


if __name__ == '__main__':
    # Instruction to create the model first:
    # ollama create sec-analyst -f SEC_Analyst.modelfile
    # Example usage: python checkSecCorrectness.py openinsider_data_2026-03-19_17-39-58Z.json

    selected_file = sys.argv[1] if len(sys.argv) > 1 else 'openinsider_filtered.json'
    run_test(data_file=selected_file)
