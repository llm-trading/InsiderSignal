import re
import copy
import json


# ---------------------------
# Helpers
# ---------------------------

def extract_footnotes(entry):
    notes = entry.get("sec_filing_data", {}).get("explanation_rows", {}).get("foot_notes", {})
    remarks = entry.get("sec_filing_data", {}).get("explanation_rows", {}).get("Remarks", "")

    all_text = " ".join(notes.values()) + " " + (remarks or "")
    return all_text.lower()


def get_ownership_type(entry):
    try:
        return entry["sec_filing_data"]["table_rows"][0].get(
            "6. Ownership Form: Direct (D) or Indirect (I) (Instr. \n      4)", ""
        )
    except:
        return ""


def is_new_position(entry):
    return "new" in entry.get("Own", "").lower()


# ---------------------------
# Core Signal Detection
# ---------------------------

def analyze_noise(entry):
    text = extract_footnotes(entry)

    reasons = []

    # Hard noise (strong rejection)
    if "10b5-1" in text:
        reasons.append("10b5-1 plan (pre-scheduled, non-discretionary)")

    if any(k in text for k in ["rsu", "restricted stock", "vesting", "award", "grant"]):
        reasons.append("Compensation-based transaction (RSU/vesting/grant)")

    if any(k in text for k in ["conversion", "converted", "ipo"]):
        reasons.append("Structural conversion (IPO/preferred conversion)")

    # Soft noise (contextual)
    if any(k in text for k in ["trust", "partnership", "estate", "indirect"]):
        reasons.append("Indirect ownership (reduced conviction)")

    if "weighted average price" in text:
        reasons.append("Executed via multiple trades (less conviction signal)")

    return reasons


def compute_signal(entry):
    noise_reasons = analyze_noise(entry)
    ownership = get_ownership_type(entry)

    score = 0
    tags = []

    # ---------------------------
    # Hard Filters (Noise override)
    # ---------------------------
    hard_noise_flags = [
        "10b5-1",
        "compensation",
        "conversion"
    ]

    if any("10b5-1" in r for r in noise_reasons):
        return "NOISE", -5, noise_reasons

    if any("Compensation" in r for r in noise_reasons):
        return "NOISE", -5, noise_reasons

    if any("conversion" in r.lower() for r in noise_reasons):
        return "NOISE", -4, noise_reasons

    # ---------------------------
    # Positive Signals
    # ---------------------------

    # New position (VERY strong)
    if is_new_position(entry):
        score += 4
        tags.append("NEW_POSITION")

    # Direct ownership
    if ownership == "D":
        score += 2
        tags.append("DIRECT_OWNERSHIP")
    elif ownership == "I":
        score -= 1
        tags.append("INDIRECT_OWNERSHIP")

    # Insider seniority
    title = entry.get("Title", "").lower()

    if any(k in title for k in ["ceo", "chief", "chair"]):
        score += 3
        tags.append("TOP_EXECUTIVE")
    elif "cfo" in title or "coo" in title:
        score += 2
        tags.append("SENIOR_EXECUTIVE")
    elif "dir" in title:
        score += 1
        tags.append("DIRECTOR")

    # ---------------------------
    # Soft penalties
    # ---------------------------

    if any("weighted average price" in r.lower() for r in noise_reasons):
        score -= 0.5

    if any("indirect ownership" in r.lower() for r in noise_reasons):
        score -= 0.5

    # ---------------------------
    # Final Classification
    # ---------------------------

    if score >= 5:
        label = "STRONG_BUY_SIGNAL"
    elif score >= 3:
        label = "BUY_SIGNAL"
    elif score >= 1:
        label = "WEAK_SIGNAL"
    else:
        label = "NOISE"

    return label, score, noise_reasons


# ---------------------------
# Main Processor
# ---------------------------

def enrich_sec_data(data):
    enriched = []

    for entry in data:
        try:
            new_entry = copy.deepcopy(entry)

            label, score, reasons = compute_signal(entry)

            new_entry["signal_label"] = label
            new_entry["signal_score"] = round(score, 2)
            new_entry["signal_reasons"] = reasons
        except Exception as e:
            print(f"Error processing entry {entry}: {e}")

        enriched.append(new_entry)

    return enriched


def enriched_json_to_html(inputfile='openinsider_enriched.json', outputfile='index.html'):

    # Load the enriched data
    # Fix: Access the ['rows'] list to avoid the TypeError
    with open(inputfile, 'r') as f:
        raw_data = json.load(f)

    # Check if the data is a dictionary containing 'rows' or just a list
    data_list = raw_data['rows'] if isinstance(raw_data, dict) and 'rows' in raw_data else raw_data

    # Calculate counts (Ensure this runs before generating html_content)
    counts = {'ALL': len(data_list), 'STRONG_BUY_SIGNAL': 0, 'BUY_SIGNAL': 0, 'WEAK_SIGNAL': 0, 'NOISE': 0}
    for item in data_list:
        label = str(item.get('signal_label', 'WEAK_SIGNAL')).upper()
        counts[label] = counts.get(label, 0) + 1

    table_rows_html = ""
    for item in data_list:
        # Handle list of reasons (ensure it exists and isn't a string)
        reasons = item.get('signal_reasons', [])
        if isinstance(reasons, str): reasons = [reasons]
        reasons_list = "".join([f"<li>{r}</li>" for r in reasons])
        
        # Label styling - Solid High-Contrast Colors (No Pastels)
        label = item.get('signal_label', 'NEUTRAL').upper()
        score = item.get('signal_score', '0')
        
        # label_style = ""
        # if label == 'STRONG SIGNAL': label_style = "bg-emerald-600 text-white shadow-[0_0_10px_rgba(16,185,129,0.2)]"
        # elif label == 'SIGNAL': label_style = "bg-blue-600 text-white shadow-[0_0_10px_rgba(37,99,235,0.2)]"
        # elif label == 'NEUTRAL': label_style = "bg-zinc-700 text-zinc-300"
        # else: label_style = "bg-rose-600 text-white shadow-[0_0_10px_rgba(225,29,72,0.2)]"

        color_mapping = {
            'STRONG_BUY_SIGNAL': 'bg-emerald-600 text-white shadow-[0_0_10px_rgba(16,185,129,0.2)]',
            'BUY_SIGNAL': 'bg-blue-600 text-white shadow-[0_0_10px_rgba(37,99,235,0.2)]',
            'WEAK_SIGNAL': 'bg-zinc-700 text-zinc-300',
            'NOISE': 'bg-rose-600 text-white shadow-[0_0_10px_rgba(225,29,72,0.2)]'
        }

        # Get the score and set the color coding based on the score range
        score = item.get('signal_score', '0')
        label_style = color_mapping.get(label, 'bg-zinc-700 text-zinc-300')

        table_rows_html += f"""
        <tr class="table-row border-b border-zinc-800/60 hover:bg-zinc-800/40 transition-all duration-150" data-label="{label}">
            <td class="py-2 px-4">
                <div class="flex items-center gap-3">
                    <div class="w-7 h-7 rounded bg-zinc-800 flex items-center justify-center font-black text-zinc-500 border border-zinc-700 text-[10px]">
                        {item.get('Ticker', '??')[0]}
                    </div>
                    <div>
                        <div class="font-black text-zinc-100 text-sm leading-none tracking-tighter">{item.get('Ticker', 'N/A')}</div>
                        <div class="text-[9px] text-blue-400 font-bold mt-0.5 uppercase tracking-wider">{item.get('InsiderName', 'Unknown')}</div>
                    </div>
                </div>
            </td>
            <td class="py-2 px-4">
                <div class="text-[11px] font-bold text-zinc-200">{item.get('Price', '$0.00')}</div>
                <div class="text-[9px] text-zinc-500 font-semibold uppercase tracking-tighter">{item.get('Qty', '0')} shares</div>
            </td>
            <td class="py-2 px-4">
                <div class="text-xs font-black text-zinc-100 tracking-tight">{item.get('Value', '$0')}</div>
                <div class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">{item.get('Own', '0%')} own</div>
            </td>
            <td class="py-2 px-4">
                <div class="inline-flex items-center px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-widest mb-1 {label_style}">
                    {label} • {score}
                </div>
                <ul class="text-[10px] text-zinc-400 leading-tight space-y-0.5 list-none">
                    {reasons_list}
                </ul>
            </td>
            <td class="py-2 px-4 text-right">
                <a href="{item.get('FilingDate_href', '#')}" target="_blank" class="text-zinc-600 hover:text-white transition-colors">
                    <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                </a>
            </td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insider Intelligence Terminal</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; background-color: #0c0c0e; color: #d4d4d8; margin: 0; padding: 0; }}
            * {{ font-style: normal !important; }}
            
            .glossy-btn {{
                background: linear-gradient(180deg, rgba(63, 63, 70, 0.4) 0%, rgba(30, 30, 35, 0.7) 100%);
                border: 1px solid rgba(82, 82, 91, 0.4);
                box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.03);
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .glossy-btn:hover {{
                background: linear-gradient(180deg, rgba(82, 82, 91, 0.5) 0%, rgba(63, 63, 70, 0.8) 100%);
                border-color: rgba(113, 113, 122, 0.5);
                color: white;
            }}
            .glossy-btn.active {{
                background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
                border-color: #60a5fa;
                color: white;
                box-shadow: 0 0 12px rgba(59, 130, 246, 0.2), inset 0 1px 0 0 rgba(255, 255, 255, 0.2);
            }}

            .legend-segment {{ height: 5px; border-radius: 1px; flex: 1; }}
            .sticky-thead th {{ position: sticky; top: 0; z-index: 10; background: #0c0c0e; }}
            ::-webkit-scrollbar {{ width: 5px; }}
            ::-webkit-scrollbar-track {{ background: #0c0c0e; }}
            ::-webkit-scrollbar-thumb {{ background: #27272a; border-radius: 10px; }}
        </style>
    </head>
    <body class="p-4 md:p-6">
        <div class="max-w-6xl mx-auto">
            <header class="mb-6 flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6">
                <div class="space-y-1.5">
                    <h1 class="text-2xl font-black text-white tracking-tighter uppercase leading-none">Insider Signal Intelligence</h1>
                    <div class="flex items-center gap-3">
                        <div class="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-black text-emerald-400 uppercase tracking-widest">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Live Dataset
                        </div>
                        <p class="text-zinc-600 text-[10px] font-bold uppercase tracking-[0.2em]">High-Density Terminal</p>
                    </div>
                </div>

                <div class="w-full lg:w-80 space-y-2 p-3 bg-zinc-900/30 border border-zinc-800/50 rounded-lg shadow-inner">
                    <div class="flex justify-between items-center text-[9px] font-black text-zinc-500 uppercase tracking-widest">
                        <span>Conviction Score</span>
                        <span>Confidence Index</span>
                    </div>
                    <div class="flex gap-1">
                        <div class="legend-segment bg-rose-600"></div>
                        <div class="legend-segment bg-zinc-700"></div>
                        <div class="legend-segment bg-blue-600"></div>
                        <div class="legend-segment bg-emerald-600"></div>
                    </div>
                    <div class="flex justify-between text-[8px] font-black text-zinc-600 uppercase tracking-tighter">
                        <span>Noise: <1</span>
                        <span>Neutral: >=1</span>
                        <span>Signal: >=3</span>
                        <span>Strong: >=5</span>
                    </div>
                </div>
            </header>

            <div class="flex flex-wrap gap-2 mb-6">
                <button onclick="applyFilter('ALL')" class="filter-btn active glossy-btn px-4 py-1.5 rounded-md text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                    All ({counts['ALL']})
                </button>
                <button onclick="applyFilter('STRONG_BUY_SIGNAL')" class="filter-btn glossy-btn px-4 py-1.5 rounded-md text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                    Strong ({counts['STRONG_BUY_SIGNAL']})
                </button>
                <button onclick="applyFilter('BUY_SIGNAL')" class="filter-btn glossy-btn px-4 py-1.5 rounded-md text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                    Signal ({counts['BUY_SIGNAL']})
                </button>
                <button onclick="applyFilter('WEAK_SIGNAL')" class="filter-btn glossy-btn px-4 py-1.5 rounded-md text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                    Neutral ({counts['WEAK_SIGNAL']})
                </button>
                <button onclick="applyFilter('NOISE')" class="filter-btn glossy-btn px-4 py-1.5 rounded-md text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                    Noise ({counts['NOISE']})
                </button>
            </div>

            <div class="bg-zinc-900/10 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl">
                <div class="overflow-x-auto max-h-[70vh]">
                    <table class="w-full text-left border-collapse" id="insider-table">
                        <thead class="sticky-thead">
                            <tr class="border-b border-zinc-800">
                                <th class="py-2.5 px-4 text-[9px] font-black uppercase tracking-widest text-zinc-600">Entity</th>
                                <th class="py-2.5 px-4 text-[9px] font-black uppercase tracking-widest text-zinc-600">Execution</th>
                                <th class="py-2.5 px-4 text-[9px] font-black uppercase tracking-widest text-zinc-600">Delta</th>
                                <th class="py-2.5 px-4 text-[9px] font-black uppercase tracking-widest text-zinc-600">Conviction Logic</th>
                                <th class="py-2.5 px-4 text-[9px] font-black uppercase tracking-widest text-zinc-600 text-right">Filing</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-zinc-800/40">{table_rows_html}</tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
        function applyFilter(label) {{
            const rows = document.querySelectorAll('.table-row');
            const buttons = document.querySelectorAll('.filter-btn');
            
            buttons.forEach(btn => {{
                if (btn.getAttribute('onclick').includes("'" + label + "'")) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});

            rows.forEach(row => {{
                row.style.display = (label === 'ALL' || row.getAttribute('data-label') === label) ? 'table-row' : 'none';
            }});
        }}
        </script>
    </body>
    </html>
    """

    with open(outputfile, 'w', encoding='utf-8') as f:
        f.write(html_content)