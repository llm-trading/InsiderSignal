"""
HTML Report Generator for Insider Signal Intelligence
Generates ticker-level signal reports from grouped JSON data.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent / "reports"


def generate_report(grouped_json_path: str) -> str:
    """
    Generate an HTML report from grouped JSON data.
    
    Args:
        grouped_json_path: Path to the grouped JSON file
        
    Returns:
        Path to the generated HTML report
    """
    logger.info(f"Generating HTML report from {grouped_json_path}")
    
    # Load JSON data
    with open(grouped_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract timestamp from filename
    json_path = Path(grouped_json_path)
    timestamp_match = json_path.stem.split('_')[-2:]  # ['YYYYMMDD', 'HHMMSS']
    timestamp = '_'.join(timestamp_match)
    
    # Create reports directory
    REPORTS_DIR.mkdir(exist_ok=True)
    
    # Generate report filename
    report_filename = f"report_{timestamp}.html"
    report_path = REPORTS_DIR / report_filename
    
    # Generate HTML content
    html_content = _generate_html(data, timestamp)
    
    # Write HTML file
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"HTML report saved to {report_path}")
    return str(report_path)


def _generate_html(data: Dict, timestamp: str) -> str:
    """Generate complete HTML document."""
    
    tickers_data = data.get('tickers', {})
    fetch_date = data.get('fetch_date', '')
    
    # Parse timestamp for display
    try:
        dt = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
        display_date = dt.strftime('%B %d, %Y')
        display_time = dt.strftime('%H:%M:%S UTC')
    except:
        display_date = timestamp
        display_time = ''
    
    # Convert fetch_date to ET timezone for display
    data_timestamp_et = ''
    if fetch_date:
        try:
            # Parse ISO format datetime
            dt_fetch = datetime.fromisoformat(fetch_date.replace('Z', '+00:00'))
            # Format for display (will be converted to ET in JavaScript)
            data_timestamp_et = dt_fetch.strftime('%Y-%m-%dT%H:%M:%S')
        except:
            data_timestamp_et = fetch_date
    
    # Generate ticker rows
    ticker_rows = _generate_ticker_rows(tickers_data)
    
    # Count signals by type
    signal_counts = _count_signals(tickers_data)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Insider Signal Report - {display_date}</title>
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
        
        .signal-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .signal-table th {{
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
        
        .signal-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid #27272a;
            vertical-align: top;
        }}
        
        .signal-table tbody tr {{
            transition: background-color 0.2s;
        }}
        
        .signal-table tbody tr:hover {{
            background: #18181b;
        }}
        
        .ticker-icon {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 14px;
            margin-right: 12px;
        }}
        
        .signal-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .signal-strong-buy {{
            background: #065f46;
            color: #d1fae5;
            border: 1px solid #10b981;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
        }}
        
        .signal-buy {{
            background: #1e3a8a;
            color: #dbeafe;
            border: 1px solid #3b82f6;
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
        }}
        
        .signal-weak {{
            background: #3f3f46;
            color: #d4d4d8;
            border: 1px solid #52525b;
        }}
        
        .signal-noise {{
            background: #7f1d1d;
            color: #fecaca;
            border: 1px solid #dc2626;
            box-shadow: 0 0 20px rgba(220, 38, 38, 0.3);
        }}
        
        .factor-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .factor-list li {{
            padding: 4px 0;
            font-size: 12px;
            line-height: 1.5;
        }}
        
        .factor-list li:before {{
            content: "•";
            margin-right: 8px;
            font-weight: 900;
        }}
        
        .goods li:before {{
            color: #10b981;
        }}
        
        .bads li:before {{
            color: #ef4444;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            transform: translateY(-1px);
        }}
        
        .filter-btn.active {{
            border-color: currentColor;
        }}
        
        .filter-all {{
            background: #27272a;
            color: #d4d4d8;
        }}
        
        .filter-strong-buy {{
            background: #065f46;
            color: #d1fae5;
        }}
        
        .filter-buy {{
            background: #1e3a8a;
            color: #dbeafe;
        }}
        
        .filter-weak {{
            background: #3f3f46;
            color: #d4d4d8;
        }}
        
        .filter-noise {{
            background: #7f1d1d;
            color: #fecaca;
        }}
        
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: #0c0c0e; }}
        ::-webkit-scrollbar-thumb {{ background: #27272a; border-radius: 10px; }}
    </style>
</head>
<body class="p-4 md:p-6">
    <div class="max-w-7xl mx-auto">
        <header class="mb-8">
            <div class="space-y-3">
                <h1 class="text-3xl font-black text-white tracking-tighter uppercase leading-none">
                    Insider Signal Intelligence
                </h1>
                <div id="live-clock" class="text-sm font-bold text-zinc-400">
                    Loading...
                </div>
                <div id="data-timestamp" class="text-xs text-zinc-600" data-timestamp="{data_timestamp_et}">
                    Data Generated: Loading...
                </div>
            </div>
        </header>

        <div class="mb-6 flex flex-wrap gap-3">
            <button class="filter-btn filter-all active" onclick="filterSignals('all')" data-filter="all">
                All ({signal_counts['total']})
            </button>
            <button class="filter-btn filter-strong-buy" onclick="filterSignals('STRONG_BUY_SIGNAL')" data-filter="STRONG_BUY_SIGNAL">
                Strong Buy ({signal_counts['STRONG_BUY_SIGNAL']})
            </button>
            <button class="filter-btn filter-buy" onclick="filterSignals('BUY_SIGNAL')" data-filter="BUY_SIGNAL">
                Buy ({signal_counts['BUY_SIGNAL']})
            </button>
            <button class="filter-btn filter-weak" onclick="filterSignals('WEAK_SIGNAL')" data-filter="WEAK_SIGNAL">
                Weak ({signal_counts['WEAK_SIGNAL']})
            </button>
            <button class="filter-btn filter-noise" onclick="filterSignals('NOISE')" data-filter="NOISE">
                Noise ({signal_counts['NOISE']})
            </button>
        </div>

        <div class="bg-zinc-900/10 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl">
            <div class="overflow-x-auto max-h-[70vh]">
                <table class="signal-table">
                    <thead>
                        <tr>
                            <th style="width: 200px;">Entity</th>
                            <th style="width: 150px;">Latest Activity</th>
                            <th style="width: 180px;">Signal & Score</th>
                            <th style="width: 300px;">Positive Factors</th>
                            <th style="width: 300px;">Risk Factors</th>
                        </tr>
                    </thead>
                    <tbody>
{ticker_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="mt-6 text-center text-zinc-600 text-xs">
            <p>Generated from insider trading data • Signals are for informational purposes only</p>
        </footer>
    </div>

    <script>
        // Check if market is open
        function isMarketOpen() {{
            const now = new Date();
            const etTime = new Date(now.toLocaleString('en-US', {{timeZone: 'America/New_York'}}));
            
            const day = etTime.getDay(); // 0=Sunday, 6=Saturday
            const hour = etTime.getHours();
            const minute = etTime.getMinutes();
            const timeInMinutes = hour * 60 + minute;
            
            // Market hours: Mon-Fri, 9:30 AM - 4:00 PM ET
            const marketOpen = 9 * 60 + 30;  // 9:30 AM
            const marketClose = 16 * 60;      // 4:00 PM
            
            const isWeekday = day >= 1 && day <= 5;
            const isDuringHours = timeInMinutes >= marketOpen && timeInMinutes < marketClose;
            
            return isWeekday && isDuringHours;
        }}
        
        // Update live clock
        function updateLiveClock() {{
            const now = new Date();
            
            // Format ET time
            const options = {{
                timeZone: 'America/New_York',
                month: 'short',
                day: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            }};
            
            const etTime = now.toLocaleString('en-US', options);
            
            // Check market status
            const marketOpen = isMarketOpen();
            const statusDot = marketOpen ? '🟢' : '🔴';
            const statusText = marketOpen ? 
                '<span style="color: #10b981;">Market Open</span>' : 
                '<span style="color: #ef4444;">Market Closed</span>';
            
            document.getElementById('live-clock').innerHTML = 
                `${{statusDot}} LIVE • ${{etTime}} ET • ${{statusText}}`;
        }}
        
        // Update data timestamp
        function updateDataTimestamp() {{
            const timestampEl = document.getElementById('data-timestamp');
            const timestamp = timestampEl.dataset.timestamp;
            
            if (timestamp) {{
                try {{
                    const dt = new Date(timestamp);
                    const options = {{
                        timeZone: 'America/New_York',
                        month: 'short',
                        day: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: true
                    }};
                    const etTime = dt.toLocaleString('en-US', options);
                    timestampEl.textContent = `Data Generated: ${{etTime}} ET`;
                }} catch (e) {{
                    timestampEl.textContent = 'Data Generated: ' + timestamp;
                }}
            }}
        }}
        
        // Filter signals
        function filterSignals(signal) {{
            const rows = document.querySelectorAll('.signal-table tbody tr');
            const buttons = document.querySelectorAll('.filter-btn');
            
            // Update active button
            buttons.forEach(btn => {{
                if (btn.dataset.filter === signal) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});
            
            // Filter rows
            rows.forEach(row => {{
                if (signal === 'all' || row.dataset.signal === signal) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
        
        // Initialize on page load
        updateLiveClock();
        updateDataTimestamp();
        
        // Update clock every second
        setInterval(updateLiveClock, 1000);
    </script>
</body>
</html>"""
    
    return html


def _get_latest_date(ticker_data: Dict) -> str:
    """Get the latest trade date from transactions."""
    transactions = ticker_data.get('insider_transactions', [])
    if not transactions:
        return '0000-00-00'  # Sort to bottom if no transactions
    
    dates = [tx.get('Trade Date', '') for tx in transactions]
    dates = [d for d in dates if d]
    
    if not dates:
        return '0000-00-00'
    
    return max(dates)


def _generate_ticker_rows(tickers_data: Dict) -> str:
    """Generate table rows for all tickers."""
    rows = []
    
    # Sort tickers by latest activity date (most recent first), then by signal score
    sorted_tickers = sorted(
        tickers_data.items(),
        key=lambda x: (
            _get_latest_date(x[1]),  # Primary: latest date
            x[1].get('signals', {}).get('ticker_signal', {}).get('ticker_score', 0)  # Secondary: score
        ),
        reverse=True
    )
    
    for ticker, ticker_data in sorted_tickers:
        row = _generate_ticker_row(ticker, ticker_data)
        rows.append(row)
    
    return '\n'.join(rows)


def _generate_ticker_row(ticker: str, ticker_data: Dict) -> str:
    """Generate a single ticker row."""
    
    company_name = ticker_data.get('company_name', '')
    signals = ticker_data.get('signals', {})
    ticker_signal = signals.get('ticker_signal', {})
    analysis = signals.get('analysis', {})
    transactions = ticker_data.get('insider_transactions', [])
    
    # Get signal classification and score
    signal_class = ticker_signal.get('signal', 'NOISE')
    signal_score = ticker_signal.get('ticker_score', 0.0)
    
    # Map signal to CSS class
    signal_css_map = {
        'STRONG_BUY_SIGNAL': 'signal-strong-buy',
        'BUY_SIGNAL': 'signal-buy',
        'WEAK_SIGNAL': 'signal-weak',
        'NOISE': 'signal-noise'
    }
    signal_css = signal_css_map.get(signal_class, 'signal-noise')
    
    # Map signal to display name
    signal_name_map = {
        'STRONG_BUY_SIGNAL': 'Strong Buy',
        'BUY_SIGNAL': 'Buy',
        'WEAK_SIGNAL': 'Weak Signal',
        'NOISE': 'Noise'
    }
    signal_name = signal_name_map.get(signal_class, 'Unknown')
    
    # Get latest trade date and insider count
    latest_date = 'N/A'
    insider_count = len(set(tx.get('Insider Name', '') for tx in transactions))
    
    if transactions:
        dates = [tx.get('Trade Date', '') for tx in transactions]
        dates = [d for d in dates if d]
        if dates:
            latest_date = max(dates)
    
    # Generate ticker icon (first letter)
    icon_letter = ticker[0] if ticker else '?'
    icon_colors = [
        'bg-blue-600', 'bg-emerald-600', 'bg-purple-600', 
        'bg-orange-600', 'bg-pink-600', 'bg-cyan-600'
    ]
    icon_color = icon_colors[hash(ticker) % len(icon_colors)]
    
    # Generate factor lists
    goods = analysis.get('goods', [])
    bads = analysis.get('bads', [])
    
    goods_html = _generate_factor_list(goods, 'goods')
    bads_html = _generate_factor_list(bads, 'bads')
    
    row = f"""                        <tr data-signal="{signal_class}">
                            <td>
                                <div class="flex items-center">
                                    <div class="ticker-icon {icon_color} text-white">
                                        {icon_letter}
                                    </div>
                                    <div>
                                        <div class="font-bold text-white text-sm">{ticker}</div>
                                        <div class="text-zinc-500 text-xs">{company_name[:40]}{'...' if len(company_name) > 40 else ''}</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div class="text-sm font-semibold text-zinc-300">{latest_date}</div>
                                <div class="text-xs text-zinc-500">{insider_count} insider{'s' if insider_count != 1 else ''}</div>
                            </td>
                            <td>
                                <div class="signal-badge {signal_css}">
                                    <span>{signal_name}</span>
                                    <span class="font-black">{signal_score:.2f}</span>
                                </div>
                            </td>
                            <td>
{goods_html}
                            </td>
                            <td>
{bads_html}
                            </td>
                        </tr>"""
    
    return row


def _generate_factor_list(factors: List[str], css_class: str) -> str:
    """Generate HTML for a factor list."""
    if not factors:
        return '                                <p class="text-zinc-600 text-xs italic">None</p>'
    
    items = '\n'.join([f'                                    <li>{factor}</li>' for factor in factors])
    return f'                                <ul class="factor-list {css_class}">\n{items}\n                                </ul>'


def _count_signals(tickers_data: Dict) -> Dict[str, int]:
    """Count signals by type."""
    counts = {
        'STRONG_BUY_SIGNAL': 0,
        'BUY_SIGNAL': 0,
        'WEAK_SIGNAL': 0,
        'NOISE': 0,
        'total': 0
    }
    
    for ticker_data in tickers_data.values():
        signals = ticker_data.get('signals', {})
        ticker_signal = signals.get('ticker_signal', {})
        signal_class = ticker_signal.get('signal', 'NOISE')
        
        if signal_class in counts:
            counts[signal_class] += 1
        counts['total'] += 1
    
    return counts


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python generate_html_report.py <grouped_json_path>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    report_path = generate_report(json_path)
    print(f"Report generated: {report_path}")
