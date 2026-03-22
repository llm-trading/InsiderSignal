import json
from utils import fetch_openinsider_rows, filter_json_file
from datetime import datetime, UTC
from CONSTANTS import OPENINSIDER_WITH_FILTERS_URL
from utils_SN_filter import enrich_sec_data, enriched_json_to_html
import os
from pathlib import Path

def create_export_path(base_dir: str = 'tmp') -> tuple[Path, str]:
    """Create export directory and generate timestamped filename."""
    utc_now = datetime.now(UTC).replace(microsecond=0)
    timestamp = utc_now.isoformat().replace('+00:00', 'Z')
    filename_timestamp = timestamp.replace(':', '-').replace('T', '_')
    
    export_dir = Path(base_dir)
    export_dir.mkdir(exist_ok=True)
    
    output_json = f'openinsider_data_{filename_timestamp}.json'
    return export_dir, output_json

def save_json(data: dict, path: Path):
    """Save JSON data with consistent formatting."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    """Main pipeline for fetching, processing, and exporting OpenInsider data."""
    export_dir, output_json = create_export_path()
    
    # Full pipeline
    raw_data = fetch_openinsider_rows(url=OPENINSIDER_WITH_FILTERS_URL)
    raw_path = export_dir / output_json
    
    # Save raw data
    save_json(raw_data, raw_path)
    print(f"[INFO] Saved raw data: {output_json} ({len(raw_data['rows'])} rows)")
    
    # Filter data
    filter_json_file(raw_path, export_dir / f'filtered_{output_json}')
    
    # Enrich filtered data
    with open(export_dir / f'filtered_{output_json}', 'r', encoding='utf-8') as f:
        sec_data = json.load(f)
    
    enriched_data = enrich_sec_data(sec_data['rows'])
    sec_data['rows'] = enriched_data
    enriched_path = export_dir / f'enriched_{output_json}'
    
    # Save enriched data and generate HTML
    save_json(sec_data, enriched_path)
    enriched_json_to_html(enriched_path, Path('index.html'))
    
    print(f"[INFO] Pipeline complete. Output: {enriched_path}")


if __name__ == '__main__':
    # TODO: once the script stablizes, will stop generating these many jsons, now its for debugging purpose
    main()
