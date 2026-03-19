import json
from utils import fetch_openinsider_rows, fetch_sec_filing_data
from datetime import datetime, UTC
from CONSTANTS import OPENINSIDER_WITH_FILTERS_URL

def main():
    fetched_timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    filename_timestamp = fetched_timestamp.replace(':', '-').replace('T', '_')
    OUTPUT_JSON = f'openinsider_data_{filename_timestamp}.json'
    out_data = fetch_openinsider_rows(url=OPENINSIDER_WITH_FILTERS_URL)

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Saved aggregated data to {OUTPUT_JSON} with {len(out_data['rows'])} rows")


if __name__ == '__main__':
    main()
