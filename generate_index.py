"""
Index Generator for Insider Signal Intelligence
Generates/updates the master index.html file listing all reports.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent / "reports"
INDEX_PATH = Path(__file__).parent / "index.html"


def update_index() -> str:
    """
    Generate or update the master index.html file.
    
    Scans the reports directory and creates an index page
    listing all reports grouped by date.
    
    Returns:
        Path to the generated index.html file
    """
    logger.info("Updating master index.html")
    
    # Scan reports directory
    reports = _scan_reports()
    
    if not reports:
        logger.warning("No reports found in reports directory")
    
    # Group reports by date
    grouped_reports = _group_reports_by_date(reports)
    
    # Generate HTML content
    html_content = _generate_index_html(grouped_reports)
    
    # Write index file
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Index updated: {INDEX_PATH} ({len(reports)} reports)")
    return str(INDEX_PATH)


def _scan_reports() -> List[Dict]:
    """
    Scan reports directory for HTML files.
    
    Returns:
        List of report metadata dicts
    """
    if not REPORTS_DIR.exists():
        return []
    
    reports = []
    
    for report_file in REPORTS_DIR.glob("report_*.html"):
        try:
            # Parse filename: report_YYYYMMDD_HHMMSS.html
            stem = report_file.stem  # report_YYYYMMDD_HHMMSS
            parts = stem.split('_')
            
            if len(parts) >= 3:
                date_str = parts[1]  # YYYYMMDD
                time_str = parts[2]  # HHMMSS
                
                # Parse datetime
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                
                reports.append({
                    'filename': report_file.name,
                    'datetime': dt,
                    'date_str': date_str,
                    'time_str': time_str
                })
        except Exception as e:
            logger.warning(f"Failed to parse report filename {report_file.name}: {e}")
    
    # Sort by datetime (newest first)
    reports.sort(key=lambda x: x['datetime'], reverse=True)
    
    return reports


def _group_reports_by_date(reports: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group reports by date.
    
    Args:
        reports: List of report metadata dicts
        
    Returns:
        Dict mapping date strings to lists of reports
    """
    grouped = defaultdict(list)
    
    for report in reports:
        date_key = report['datetime'].strftime('%Y-%m-%d')
        grouped[date_key].append(report)
    
    return dict(grouped)


def _generate_index_html(grouped_reports: Dict[str, List[Dict]]) -> str:
    """Generate the complete index HTML."""
    
    # Generate table rows
    table_rows = _generate_table_rows(grouped_reports)
    
    # Count total reports
    total_reports = sum(len(reports) for reports in grouped_reports.values())
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Insider Signal Intelligence - Reports</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {{ 
            font-family: 'Inter', sans-serif; 
            background-color: #0c0c0e; 
            color: #d4d4d8; 
            margin: 0; 
            padding: 0; 
        }}
        * {{ font-style: normal !important; }}
        
        .report-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .report-table th {{
            background: #18181b;
            padding: 12px 16px;
            text-align: left;
            font-weight: 800;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.1em;
            color: #71717a;
            border-bottom: 2px solid #27272a;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        .report-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid #27272a;
        }}
        
        .report-table tbody tr:hover {{
            background: #18181b;
        }}
        
        .date-cell {{
            font-weight: 700;
            color: #e4e4e7;
            font-size: 14px;
        }}
        
        .time-cell {{
            color: #71717a;
            font-size: 12px;
            font-family: 'Courier New', monospace;
        }}
        
        .report-link {{
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        
        .report-link:hover {{
            color: #93c5fd;
        }}
        
        .report-link svg {{
            width: 14px;
            height: 14px;
        }}
        
        .sub-row {{
            background: #09090b;
        }}
        
        .sub-row td {{
            padding-left: 48px;
            padding-top: 8px;
            padding-bottom: 8px;
        }}
        
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: #0c0c0e; }}
        ::-webkit-scrollbar-thumb {{ background: #27272a; border-radius: 10px; }}
    </style>
</head>
<body class="p-4 md:p-6">
    <div class="max-w-6xl mx-auto">
        <header class="mb-8">
            <div class="space-y-2">
                <h1 class="text-3xl font-black text-white tracking-tighter uppercase leading-none">
                    Insider Signal Reports
                </h1>
                <div class="flex items-center gap-3">
                    <div class="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-black text-emerald-400 uppercase tracking-widest">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Live Archive
                    </div>
                    <p class="text-zinc-600 text-[10px] font-bold uppercase tracking-[0.2em]">Daily Report Index • {total_reports} Reports</p>
                </div>
            </div>
        </header>

        <div class="bg-zinc-900/10 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl">
            <div class="overflow-x-auto max-h-[75vh]">
                <table class="report-table">
                    <thead>
                        <tr>
                            <th style="width: 200px;">Date</th>
                            <th style="width: 150px;">Time (UTC)</th>
                            <th>Report</th>
                        </tr>
                    </thead>
                    <tbody>
{table_rows if table_rows else '                        <tr><td colspan="3" class="text-center text-zinc-600 py-8">No reports available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="mt-6 text-center text-zinc-600 text-xs">
            <p>Reports are generated automatically from insider trading data</p>
        </footer>
    </div>
</body>
</html>"""
    
    return html


def _generate_table_rows(grouped_reports: Dict[str, List[Dict]]) -> str:
    """Generate table rows for all reports."""
    
    if not grouped_reports:
        return ''
    
    rows = []
    
    # Sort dates (newest first)
    sorted_dates = sorted(grouped_reports.keys(), reverse=True)
    
    for date_key in sorted_dates:
        reports = grouped_reports[date_key]
        
        # Sort reports within date by time (newest first)
        reports.sort(key=lambda x: x['datetime'], reverse=True)
        
        # Format date for display
        try:
            dt = datetime.strptime(date_key, '%Y-%m-%d')
            display_date = dt.strftime('%B %d, %Y')
        except:
            display_date = date_key
        
        # Generate rows for this date
        for i, report in enumerate(reports):
            time_display = report['datetime'].strftime('%H:%M:%S')
            report_link = f"reports/{report['filename']}"
            
            if i == 0:
                # First row for this date - include date cell with rowspan
                row = f"""            <tr>
                <td class="date-cell" rowspan="{len(reports)}">{display_date}</td>
                <td class="time-cell">{time_display}</td>
                <td>
                    <a href="{report_link}" class="report-link" target="_blank">
                        View Report
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                            <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                        </svg>
                    </a>
                </td>
            </tr>"""
            else:
                # Subsequent rows - sub-row style
                row = f"""            
                <tr class="sub-row">
                    <td class="time-cell">{time_display}</td>
                    <td>
                        <a href="{report_link}" class="report-link" target="_blank">
                            View Report
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                            </svg>
                        </a>
                    </td>
                </tr>"""
            
            rows.append(row)
    
    return '\n'.join(rows)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    index_path = update_index()
    print(f"Index updated: {index_path}")
