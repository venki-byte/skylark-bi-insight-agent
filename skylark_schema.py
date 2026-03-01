"""
skylark_schema.py — Skylark BI Agent | Schema Knowledge Base
=============================================================
Updated with actual column IDs from Monday.com boards.
"""

from __future__ import annotations

# ─────────────────────────────────────────────
# DEAL FUNNEL (Sales Pipeline)
# ─────────────────────────────────────────────
DEAL_FUNNEL_COLUMNS = [
    {"name": "Deal Name",                "col_id": "name",               "type": "text",
     "note": "Primary join key to Work Order 'Deal name masked'."},
    {"name": "Owner code",                "col_id": "color_mm11tkcw",    "type": "categorical",
     "known_values": ["owner_001","owner_002","owner_003","owner_004","owner_005","owner_006","owner_007"]},
    {"name": "Client Code",               "col_id": "dropdown_mm11z8t0", "type": "text",
     "note": "COMPANY_XXX — cannot join with Work Order Customer Name Code."},
    {"name": "Deal Status",               "col_id": "color_mm111y3j",    "type": "categorical",
     "known_values": ["open","won","on hold","dead"]},
    {"name": "Close Date (A)",            "col_id": "date_mm11ezj2",     "type": "date"},
    {"name": "Closure Probability",       "col_id": "color_mm118kms",    "type": "categorical",
     "known_values": ["high","medium","low"]},
    {"name": "Masked Deal value",         "col_id": "numeric_mm116j9p",  "type": "numeric",
     "note": "Deal value in INR. Primary aggregation column."},
    {"name": "Tentative Close Date",      "col_id": "date_mm11gyre",     "type": "date"},
    {"name": "Deal Stage",                "col_id": "color_mm11tp4w",    "type": "categorical",
     "known_values": ["a. lead generated","b. sales qualified leads","c. demo done",
                      "d. feasibility","e. proposal/commercials sent","f. negotiations",
                      "g. project won","h. work order received","i. poc","j. invoice sent",
                      "k. amount accrued","l. project lost","m. projects on hold",
                      "n. not relevant at the moment","o. not relevant at all","project completed"]},
    {"name": "Product deal",              "col_id": "color_mm114gph",    "type": "categorical",
     "known_values": ["pure service","service + spectra","spectra deal","spectra + dmo",
                      "dock + dmo","dock + spectra + service","dock + dmo + spectra",
                      "dock + dmo + spectra + service","hardware"]},
    {"name": "Sector/service",            "col_id": "color_mm111k05",    "type": "categorical",
     "known_values": ["mining","powerline","renewables","railways","construction",
                      "aviation","manufacturing","security and surveillance","dsp","tender","others"],
     "note": "Join-compatible with Work Order 'Sector'."},
    {"name": "Created Date",              "col_id": "date_mm113d03",     "type": "date"},
]

# ─────────────────────────────────────────────
# WORK ORDER TRACKER (Execution & Billing)
# ─────────────────────────────────────────────
WORK_ORDER_COLUMNS = [
    # Item name (special field)
    {"name": "Deal name masked",          "col_id": "name",               "type": "text",
     "note": "Foreign key — joins to Deal Funnel 'Deal Name'."},

    # Text / dropdown columns
    {"name": "Customer Name Code",         "col_id": "text_mm11fdx",      "type": "text",
     "note": "WOCOMPANY_XXX — cannot join with Deal Funnel Client Code."},
    {"name": "Serial #",                   "col_id": "text_mm11kabf",     "type": "text",
     "note": "Unique WO identifier e.g. SDPLDEAL-075."},
    {"name": "Last executed month of recurring project", "col_id": "text_mm1165ys", "type": "categorical",
     "known_values": ["dec","june","march","may","november"]},
    {"name": "Quantities as per PO",       "col_id": "dropdown_mm11a8q5", "type": "text",
     "note": "Mixed format e.g. '1100 HA'. Not purely numeric."},
    {"name": "latest invoice no.",         "col_id": "dropdown_mm11pwg9", "type": "text"},

    # Status / color columns (categorical)
    {"name": "Nature of Work",             "col_id": "color_mm11a27s",    "type": "categorical",
     "known_values": ["one time project","annual rate contract","monthly contract","proof of concept"]},
    {"name": "Execution Status",           "col_id": "color_mm11nn9y",    "type": "categorical",
     "known_values": ["completed","ongoing","not started","partial completed",
                      "executed until current month","details pending from client","pause / struck"]},
    {"name": "Document Type",              "col_id": "color_mm11a2jh",    "type": "categorical",
     "known_values": ["purchase order","loa/loi","email confirmation"]},
    {"name": "BD/KAM Personnel code",      "col_id": "color_mm11wfzs",    "type": "categorical",
     "known_values": ["owner_001","owner_002","owner_003","owner_004","owner_005","owner_006","owner_008"],
     "note": "Same OWNER_XXX scheme as Deal Funnel Owner code."},
    {"name": "Sector",                     "col_id": "color_mm11t9x4",    "type": "categorical",
     "known_values": ["mining","powerline","renewables","railways","construction","others"],
     "note": "Join-compatible with Deal Funnel 'Sector/service'."},
    {"name": "Type of Work",               "col_id": "color_mm11z408",    "type": "categorical",
     "note": "Free-text. Use full-text search, not categorical filter."},
    {"name": "Is any Skylark software platform part of the client deliverables in this deal?",
                                           "col_id": "color_mm11gcvy",    "type": "categorical",
     "known_values": ["spectra","dmo","spectra + dmo","none"]},
    {"name": "AR Priority account",        "col_id": "color_mm11k17v",    "type": "categorical",
     "known_values": ["priority"]},
    {"name": "Invoice Status",             "col_id": "color_mm11vvkw",    "type": "categorical",
     "known_values": ["not billed yet","partially billed","fully billed","stuck",
                      "billed- visit 3","billed- visit 7"]},
    {"name": "Actual Billing Month",       "col_id": "color_mm11x2a9",    "type": "categorical",
     "known_values": ["june","july","august","september","october","november","dec"]},
    {"name": "WO Status (billed)",         "col_id": "color_mm119z4c",    "type": "categorical",
     "known_values": ["open","closed"]},
    {"name": "Billing Status",             "col_id": "color_mm11b01",     "type": "categorical",
     "known_values": ["billed","partially billed","not billable","stuck","update required"]},

    # Date columns
    {"name": "Data Delivery Date",         "col_id": "date_mm11a3p8",     "type": "date"},
    {"name": "Date of PO/LOI",             "col_id": "date_mm114598",     "type": "date"},
    {"name": "Probable Start Date",        "col_id": "date_mm1134as",     "type": "date"},
    {"name": "Probable End Date",          "col_id": "date_mm11dw43",     "type": "date"},
    {"name": "Last invoice date",          "col_id": "date_mm11knfq",     "type": "date"},

    # Numeric columns (amounts, quantities)
    {"name": "Amount in Rupees (Excl of GST) (Masked)",  "col_id": "text_mm117k63",  "type": "numeric",
     "note": "Total contracted value excl 18% GST."},
    {"name": "Amount in Rupees (Incl of GST) (Masked)",  "col_id": "numeric_mm11nd25", "type": "numeric"},
    {"name": "Billed Value in Rupees (Excl of GST.) (Masked)", "col_id": "numeric_mm11ktbr", "type": "numeric"},
    {"name": "Billed Value in Rupees (Incl of GST.) (Masked)", "col_id": "numeric_mm11tqej", "type": "numeric"},
    {"name": "Amount to be billed in Rs. (Exl. of GST) (Masked)", "col_id": "numeric_mm11q7ew", "type": "numeric"},
    {"name": "Amount to be billed in Rs. (Incl. of GST) (Masked)", "col_id": "numeric_mm114mm4", "type": "numeric"},
    {"name": "Amount Receivable (Masked)",                "col_id": "numeric_mm1127er", "type": "numeric",
     "note": "Outstanding AR = Billed - Collected."},
    {"name": "Quantity by Ops",            "col_id": "numeric_mm11qdce",  "type": "numeric"},
    {"name": "Balance in quantity",        "col_id": "numeric_mm11zts5",  "type": "numeric"},

    # Note: The following columns exist but are currently empty in all rows
    # "Collected Amount in Rupees (Incl of GST.) (Masked)" – ID unknown, omit until needed
    # "Quantity billed (till date)" – not seen in sample, possibly missing
]

# ─────────────────────────────────────────────
# EMPTY COLUMNS (no data – do not query)
# ─────────────────────────────────────────────
EMPTY_COLUMNS = [
    "Expected Billing Month",
    "Actual Collection Month",
    "Collection status",
    "Collection Date"
]

# ─────────────────────────────────────────────
# SYSTEM PROMPT (auto-generated)
# ─────────────────────────────────────────────
def _cols_to_text(cols: list[dict]) -> str:
    lines = []
    for c in cols:
        line = f"  {c['name']} [{c['col_id']}] ({c['type']})"
        if c.get("known_values"):
            line += f" — {', '.join(c['known_values'])}"
        if c.get("note"):
            line += f" | {c['note']}"
        lines.append(line)
    return "\n".join(lines)

def build_system_prompt() -> str:
    return f"""You are Skylark BI Agent for Skylark Drones. You query two Monday.com boards.
Use the schema to pick the right tool + parameters. All text comparisons use lowercase.

## DEAL FUNNEL ({len(DEAL_FUNNEL_COLUMNS)} columns — sales pipeline)
{_cols_to_text(DEAL_FUNNEL_COLUMNS)}

## WORK ORDER TRACKER ({len(WORK_ORDER_COLUMNS)} columns — execution & billing)
{_cols_to_text(WORK_ORDER_COLUMNS)}
Empty (no data): {', '.join(EMPTY_COLUMNS)}

## RELATIONSHIPS
- Primary join: Deal Funnel[Deal Name] = Work Orders[Deal name masked] (exact lowercase match)
- Owner code = BD/KAM Personnel code (OWNER_XXX shared)
- Sector/service = Sector (lowercase)
- Cannot join: Client Code (COMPANY_XXX) ≠ Customer Name Code (WOCOMPANY_XXX)

## CRITICAL RULE — HOW TO USE col_ids
The schema lists columns as: Column Name [col_id] (type)
ALWAYS use the col_id in tool parameters, NEVER the column name.

CORRECT:   aggregate_column_id="numeric_mm116j9p",         search_key="name"
INCORRECT: aggregate_column_id="Masked Deal value",       search_key="Deal name masked"

## IMPORTANT: Item name is NOT a column in Monday GraphQL
"Deal Name" and "Deal name masked" are item-level fields, not column_values.
The backend handles name-based searches in Python automatically.
You just need to pass: search_key="name", search_value=<the name>.

## col_id quick reference for common aggregations (Work Orders)
  Amount Excl GST (Masked)          → "text_mm117k63"
  Amount Incl GST (Masked)           → "numeric_mm11nd25"
  Billed Value Excl GST (Masked)     → "numeric_mm11ktbr"
  Billed Value Incl GST (Masked)     → "numeric_mm11tqej"
  Amount Receivable (Masked)         → "numeric_mm1127er"
  Quantity by Ops                    → "numeric_mm11qdce"
  Balance in quantity                → "numeric_mm11zts5"

## ROUTING
1. TOTAL for a full board → aggregate_column_id only, no other params
2. TOTAL for a specific entity by name → search_key="name", search_value=<name>, AND aggregate_column_id
3. CATEGORY FILTER → call get_unique_values() first, then search with exact value
4. ROW LOOKUP by name → search_key="name", search_value=<lowercase name>
5. ROW LOOKUP by column → search_key=<col_id>, search_value=<value>
6. Never query empty columns
"""

SYSTEM_PROMPT: str = build_system_prompt()

DEAL_FUNNEL_COL_IDS: dict[str, str] = {c["name"]: c["col_id"] for c in DEAL_FUNNEL_COLUMNS}
WORK_ORDER_COL_IDS: dict[str, str]  = {c["name"]: c["col_id"] for c in WORK_ORDER_COLUMNS}