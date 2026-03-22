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


with open("openinsider_filtered.json", "r") as f:
    sec_data = json.load(f)

# import pdb; pdb.set_trace()
enriched_data = enrich_sec_data(sec_data['rows'])

sec_data['rows'] = enriched_data
with open("openinsider_enriched.json", "w") as f:
    json.dump(sec_data, f, indent=2)