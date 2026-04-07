# HTML Report Generation System

## Overview

The HTML report generation system automatically creates beautiful, interactive reports from insider trading signal data. Reports are generated at the end of each pipeline run and organized in a master index page.

## File Structure

```
InsiderSignal/optimized_pipeline/
├── index.html                      # Master index listing all reports
├── generate_html_report.py         # Report generator script
├── generate_index.py               # Index generator script
├── main.py                         # Updated to call generators
├── reports/                        # Generated reports directory
│   ├── report_20260407_022628.html
│   ├── report_20260406_153045.html
│   └── ...
└── output/                         # Source JSON files
    └── ALL_insider_trades_grouped_*.json
```

## Features

### Individual Reports (`reports/report_*.html`)

Each report displays ticker-level insider trading signals with:

- **Entity Column**: Ticker symbol, company name, and color-coded icon
- **Latest Activity**: Most recent trade date and insider count
- **Signal & Score**: Color-coded signal badge (Strong Buy, Buy, Weak, Noise) with numeric score
- **Positive Factors**: Bulleted list of "goods" (green bullets)
- **Risk Factors**: Bulleted list of "bads" (red bullets)

**Interactive Features**:
- Filter buttons to show/hide signals by type
- Sortable by signal score (highest first)
- Responsive design for mobile/desktop
- Dark theme with hover effects

**Signal Color Coding**:
- 🟢 **Strong Buy** (≥0.75): Green glow, high conviction signals
- 🔵 **Buy** (≥0.60): Blue glow, solid buy signals
- ⚪ **Weak Signal** (≥0.45): Gray, marginal signals
- 🔴 **Noise** (<0.45): Red glow, low-quality signals

### Master Index (`index.html`)

The index page lists all generated reports:

- **Date Grouping**: Reports grouped by date with rowspan
- **Chronological Order**: Newest reports first
- **Multiple Reports Per Day**: Sub-rows for multiple runs
- **Direct Links**: Click to open individual reports
- **Report Count**: Shows total number of reports

## Usage

### Automatic Generation (Recommended)

Reports are automatically generated when running the pipeline:

```bash
cd InsiderSignal/optimized_pipeline
python main.py
```

This will:
1. Run the complete pipeline
2. Generate grouped JSON with signals
3. Create HTML report in `reports/`
4. Update `index.html`

### Manual Generation

Generate a report from existing JSON:

```bash
python generate_html_report.py output/ALL_insider_trades_grouped_20260407_022628.json
```

Update the index after manual report generation:

```bash
python generate_index.py
```

## Viewing Reports

### Local Viewing

Open the index page in your browser:

```bash
# Windows
start index.html

# Mac/Linux
open index.html
```

Click on any report link to view the detailed signal analysis.

### Web Server (Optional)

For better performance with large reports, serve via HTTP:

```bash
# Python 3
python -m http.server 8000

# Then open: http://localhost:8000/index.html
```

## Report Content

### Signal Factors Explained

**Positive Factors (Goods)**:
- High conviction relative to market cap
- Buying after negative earnings reactions
- Stock in drawdown (potential bottom)
- Current price below insider buy price
- Sector weakness (contrarian signal)
- Cluster buying (multiple insiders)
- Repeated buying by same insider

**Risk Factors (Bads)**:
- Low conviction relative to company size
- Buying after strong positive moves
- Stock not significantly discounted
- Price moved significantly above insider buys
- Sector already strong
- Single insider (weak confirmation)
- Weak overall consensus

### Signal Score Calculation

Scores are computed using a three-layer hybrid factor aggregation:

1. **Conviction (C)**: Transaction size and ownership change
2. **Credibility (Q)**: Insider role and history
3. **Timing (T)**: Earnings reaction timing
4. **Coordination (K)**: Multiple insider activity
5. **Positioning (P)**: Price levels and sector context

Final score = Weighted combination with interaction boosts

## Customization

### Styling

Edit the `<style>` section in either generator script to customize:
- Colors and themes
- Font sizes and spacing
- Table layouts
- Button styles

### Signal Thresholds

Modify thresholds in `generate_html_report.py`:

```python
def classify(score: float) -> str:
    if score >= 0.75:  # Adjust these thresholds
        return "STRONG_BUY_SIGNAL"
    elif score >= 0.60:
        return "BUY_SIGNAL"
    # ...
```

### Report Columns

Add/remove columns by modifying:
1. `_generate_html()` - Table header
2. `_generate_ticker_row()` - Table cells

## Troubleshooting

### No Reports Showing

- Check that `reports/` directory exists
- Verify report filenames match pattern: `report_YYYYMMDD_HHMMSS.html`
- Run `python generate_index.py` to rebuild index

### Broken Links

- Ensure reports are in `reports/` subdirectory
- Check that index.html is in `optimized_pipeline/` root
- Verify relative paths: `reports/report_*.html`

### Missing Signals

- Confirm grouped JSON has `signals` key for each ticker
- Check that signal generation ran successfully in pipeline
- Review pipeline logs for errors

### Styling Issues

- Ensure internet connection for Tailwind CSS CDN
- Check browser console for JavaScript errors
- Try clearing browser cache

## Integration with Pipeline

The HTML generators are integrated into `main.py`:

```python
# Generate HTML reports (only for grouped data)
if grouped_path:
    try:
        from generate_html_report import generate_report
        from generate_index import update_index
        
        logger.info("Generating HTML reports...")
        report_path = generate_report(str(grouped_path))
        logger.info(f"Report generated: {report_path}")
        
        index_path = update_index()
        logger.info(f"Index updated: {index_path}")
    except Exception as e:
        logger.error(f"Failed to generate HTML reports: {e}", exc_info=True)
```

Reports are only generated for full pipeline runs (not single-ticker queries).

## Performance

- **Report Size**: ~125KB per report (50 tickers)
- **Generation Time**: <1 second per report
- **Browser Load**: Instant for <100 tickers
- **Filter Performance**: Real-time JavaScript filtering

## Future Enhancements

Potential improvements:
- Export to PDF functionality
- Historical signal tracking charts
- Email notification system
- Mobile app integration
- Real-time updates via WebSocket
- Advanced filtering (date range, score range)
- Comparison between reports
- Downloadable CSV exports

## Support

For issues or questions:
1. Check pipeline logs in `logs/` directory
2. Verify JSON structure in `output/` directory
3. Test generators independently with sample data
4. Review browser console for JavaScript errors

## License

Part of the Insider Signal Intelligence project.
