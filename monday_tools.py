"""
monday_tools.py — Skylark BI Agent | Data Layer v5.0
=====================================================
KEY FIX in v5.0:
  Monday.com item names (Deal Name, Deal name masked) are TOP-LEVEL fields,
  NOT column_values. They CANNOT be filtered via GraphQL query_params rules.
  Any name-based search MUST fetch all rows and filter in Python.

Retrieval strategy:
  - Name search + aggregate  → fetch ALL rows, filter by name in Python, sum
  - Name search (rows only)  → fetch ALL rows, filter by name in Python
  - Column filter (status/text columns) → server-side query_params (fast)
  - Full board aggregate     → fetch only target column, all rows, sum in Python
  - Full board fetch         → all rows, all columns
"""

from __future__ import annotations

import os
import re
import logging
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

MONDAY_URL    = "https://api.monday.com/v2"
API_VERSION   = "2024-01"
PAGE_SIZE     = 500
TIMEOUT       = 30

MONDAY_API_TOKEN     = os.getenv("MONDAY_API_TOKEN", "")
DEAL_FUNNEL_BOARD_ID = os.getenv("DEAL_FUNNEL_BOARD_ID", "")
WORK_ORDER_BOARD_ID  = os.getenv("WORK_ORDER_BOARD_ID", "")

HEADERS = {
    "Authorization": MONDAY_API_TOKEN,
    "Content-Type":  "application/json",
    "API-Version":   API_VERSION,
}

# ─────────────────────────────────────────────
# NORMALIZATION  (applied once per raw value)
# ─────────────────────────────────────────────

_STRIP_NON_NUMERIC = re.compile(r"[^\d.]")
_MASKED_RE         = re.compile(r"\(masked\)", re.IGNORECASE)
_DATE_FORMATS      = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d-%b-%Y")

_NUMERIC_KW = ("amount","value","price","revenue","billed",
               "receivable","collected","invoice","gst","quantity")
_DATE_KW    = ("date","month")


def normalize_value(raw: Any, col_title: str) -> Any:
    """Normalize a cell value once. Returns float | ISO date str | lowercase str | None."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text.lower() in {"", "none", "n/a", "null", "update required", "na", "-"}:
        return None

    col = col_title.lower()

    if any(k in col for k in _NUMERIC_KW):
        cleaned = _STRIP_NON_NUMERIC.sub("", _MASKED_RE.sub("", text))
        if cleaned in ("", "."):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return text.lower()

    if any(k in col for k in _DATE_KW):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return text.lower()

    return text.lower()


# ─────────────────────────────────────────────
# RAW API
# ─────────────────────────────────────────────

def _post(query: str, variables: dict) -> dict:
    if not MONDAY_API_TOKEN:
        raise RuntimeError("MONDAY_API_TOKEN not set in .env")
    try:
        r = requests.post(
            MONDAY_URL,
            json={"query": query, "variables": variables},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Monday.com API timed out.")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Monday.com network error: {e}")

    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(f"Monday GraphQL error: {payload['errors'][0].get('message')}")
    return payload


# ─────────────────────────────────────────────
# GRAPHQL QUERIES
# ─────────────────────────────────────────────

# Full row fetch (all columns) — paginated
_FULL_QUERY = """
query ($boardId: [ID!]!, $limit: Int!, $cursor: String) {
  boards(ids: $boardId) {
    items_page(limit: $limit, cursor: $cursor) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          column { title id }
        }
      }
    }
  }
}
"""

# Single-column fetch — paginated (lightweight, used for aggregation)
_SINGLE_COL_QUERY = """
query ($boardId: [ID!]!, $colId: [String!]!, $limit: Int!, $cursor: String) {
  boards(ids: $boardId) {
    items_page(limit: $limit, cursor: $cursor) {
      cursor
      items {
        name
        column_values(ids: $colId) {
          text
          column { title }
        }
      }
    }
  }
}
"""

# Server-side column filter (only for non-name columns like status, text columns)
_COL_FILTER_QUERY = """
query ($boardId: [ID!]!, $colId: String!, $colVal: [String!]!, $limit: Int!, $cursor: String) {
  boards(ids: $boardId) {
    items_page(
      limit: $limit
      cursor: $cursor
      query_params: {
        rules: [{ column_id: $colId, compare_value: $colVal, operator: contains_terms }]
      }
    ) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          column { title id }
        }
      }
    }
  }
}
"""


# ─────────────────────────────────────────────
# ITEM PARSER
# ─────────────────────────────────────────────

def _parse_items(raw_items: list[dict]) -> list[dict]:
    """Convert raw Monday items to normalized flat dicts."""
    result = []
    for item in raw_items:
        row: dict[str, Any] = {
            "item_id":   item.get("id"),
            "item_name": item.get("name", "").strip().lower(),
        }
        for cv in item.get("column_values", []):
            title = cv["column"]["title"]
            row[title] = normalize_value(cv.get("text"), title)
        result.append(row)
    return result


# ─────────────────────────────────────────────
# CORE FETCH — All rows, all columns
# ─────────────────────────────────────────────

def _fetch_all_rows(board_id: str) -> list[dict]:
    """Fetch every row from a board via cursor pagination. Returns parsed items."""
    all_items = []
    cursor = None
    page = 0

    while True:
        page += 1
        try:
            payload = _post(_FULL_QUERY, {
                "boardId": [board_id], "limit": PAGE_SIZE, "cursor": cursor
            })
        except RuntimeError as e:
            return [{"error": str(e)}]

        page_data = payload["data"]["boards"][0]["items_page"]
        items = page_data.get("items", [])
        all_items.extend(items)
        cursor = page_data.get("cursor")
        log.info("  page %d | +%d rows (total %d)", page, len(items), len(all_items))
        if not cursor or not items:
            break

    return _parse_items(all_items)


# ─────────────────────────────────────────────
# CORE FETCH — Single column, all rows (for aggregation)
# ─────────────────────────────────────────────

def _fetch_column_values(board_id: str, column_id: str) -> list[tuple[str, Any]]:
    """
    Fetch (item_name, column_value) pairs for ONE column across ALL rows.
    Returns list of (name_lower, numeric_value).
    """
    results = []
    cursor = None

    while True:
        try:
            payload = _post(_SINGLE_COL_QUERY, {
                "boardId": [board_id], "colId": [column_id],
                "limit": PAGE_SIZE, "cursor": cursor
            })
        except RuntimeError as e:
            log.error("Error fetching column values: %s", e)
            return []

        page_data = payload["data"]["boards"][0]["items_page"]
        items = page_data.get("items", [])
        cursor = page_data.get("cursor")

        for item in items:
            name = item.get("name", "").strip().lower()
            for cv in item.get("column_values", []):
                col_title = cv["column"]["title"]
                val = normalize_value(cv.get("text", ""), col_title)
                results.append((name, val))

        if not cursor or not items:
            break

    return results


# ─────────────────────────────────────────────
# CORE FETCH — Server-side column filter (non-name columns only)
# ─────────────────────────────────────────────

def _fetch_filtered_rows(board_id: str, col_id: str, col_value: str) -> list[dict]:
    """
    Server-side filter for status/text columns. Fast, works for any board size.
    Do NOT use for item name — use _fetch_all_rows + Python filter instead.
    """
    all_items = []
    cursor = None

    while True:
        try:
            payload = _post(_COL_FILTER_QUERY, {
                "boardId": [board_id], "colId": col_id,
                "colVal": [col_value.lower()],
                "limit": PAGE_SIZE, "cursor": cursor,
            })
        except RuntimeError as e:
            return [{"error": str(e)}]

        page_data = payload["data"]["boards"][0]["items_page"]
        items = page_data.get("items", [])
        all_items.extend(items)
        cursor = page_data.get("cursor")
        if not cursor or not items:
            break

    return _parse_items(all_items)


# ─────────────────────────────────────────────
# AGGREGATION ENGINE
# ─────────────────────────────────────────────

def _aggregate(
    board_id: str,
    agg_col_id: str,
    agg_func: str,
    name_filter: str | None = None,
) -> dict:
    """
    Compute SUM or COUNT for a numeric column.

    If name_filter is set: fetch all (name, value) pairs and filter by name in Python.
    This is necessary because Monday item names are NOT filterable via GraphQL rules.

    Returns a clean result dict.
    """
    log.info("Aggregate | board=%s | col=%s | func=%s | name_filter=%s",
             board_id, agg_col_id, agg_func, name_filter)

    pairs = _fetch_column_values(board_id, agg_col_id)

    if not pairs:
        return {"error": "No data returned from board."}

    col_title = agg_col_id  # fallback

    # Filter by name if requested (Python-side, since Monday doesn't support name filtering in GraphQL)
    if name_filter:
        name_lower = name_filter.strip().lower()
        pairs = [(n, v) for n, v in pairs if name_lower in n]
        log.info("  After name filter '%s': %d rows", name_lower, len(pairs))

    # Get col title from first result that has it
    # (col title comes from normalize_value context — use the col_id as fallback)
    numeric_vals = [v for _, v in pairs if isinstance(v, (int, float))]

    if agg_func.upper() == "COUNT":
        result = len(pairs)
    else:
        result = sum(numeric_vals)

    return {
        "agg_func":     agg_func.upper(),
        "column_id":    agg_col_id,
        "result":       round(result, 2),
        "row_count":    len(pairs),
        "name_filter":  name_filter,
    }


# ─────────────────────────────────────────────
# UNIQUE VALUE FETCHER
# ─────────────────────────────────────────────

def get_unique_values(board: str, column_id: str) -> dict:
    """Fetch all live unique values for a categorical column."""
    board_id = DEAL_FUNNEL_BOARD_ID if board == "deal_funnel" else WORK_ORDER_BOARD_ID
    if not board_id:
        return {"error": f"Board ID not configured for '{board}'"}

    log.info("Unique values | board=%s | col=%s", board, column_id)
    pairs = _fetch_column_values(board_id, column_id)

    unique = sorted({str(v) for _, v in pairs if v is not None})
    null_count = sum(1 for _, v in pairs if v is None)

    return {
        "board": board, "column_id": column_id,
        "unique_values": unique,
        "unique_count": len(unique),
        "null_count": null_count,
        "total_rows": len(pairs),
    }


# ─────────────────────────────────────────────
# AI TOOL WRAPPERS
# ─────────────────────────────────────────────

def get_deal_funnel(
    search_key: str | None = None,
    search_value: str | None = None,
    aggregate_column_id: str | None = None,
    aggregate_func: str = "SUM",
) -> list[dict] | dict:
    """
    Query the Deal Funnel board.

    Routing:
      aggregate_column_id + search_key="name" → name-filtered aggregate (Python-side filter)
      aggregate_column_id only                → full board aggregate
      search_key="name" + search_value        → fetch all, filter by name in Python
      search_key=<other col_id> + search_value → server-side column filter
      no params                               → full board fetch
    """
    board_id = DEAL_FUNNEL_BOARD_ID
    if not board_id:
        return {"error": "DEAL_FUNNEL_BOARD_ID not set."}

    if aggregate_column_id:
        name_filter = search_value if search_key == "name" else None
        return _aggregate(board_id, aggregate_column_id, aggregate_func, name_filter)

    if search_key and search_value:
        if search_key == "name":
            # Item name is NOT a GraphQL-filterable column — must fetch all and filter
            log.info("Name search (Python-side) | value=%s", search_value)
            all_rows = _fetch_all_rows(board_id)
            name_lower = search_value.strip().lower()
            return [r for r in all_rows if name_lower in (r.get("item_name") or "")]
        else:
            return _fetch_filtered_rows(board_id, search_key, search_value)

    return _fetch_all_rows(board_id)


def get_work_orders(
    search_key: str | None = None,
    search_value: str | None = None,
    aggregate_column_id: str | None = None,
    aggregate_func: str = "SUM",
) -> list[dict] | dict:
    """
    Query the Work Order Tracker board.

    Routing:
      aggregate_column_id + search_key="name" → name-filtered aggregate (Python-side filter)
      aggregate_column_id only                → full board aggregate
      search_key="name" + search_value        → fetch all, filter by name in Python
      search_key=<other col_id> + search_value → server-side column filter
      no params                               → full board fetch
    """
    board_id = WORK_ORDER_BOARD_ID
    if not board_id:
        return {"error": "WORK_ORDER_BOARD_ID not set."}

    if aggregate_column_id:
        name_filter = search_value if search_key == "name" else None
        return _aggregate(board_id, aggregate_column_id, aggregate_func, name_filter)

    if search_key and search_value:
        if search_key == "name":
            log.info("Name search (Python-side) | value=%s", search_value)
            all_rows = _fetch_all_rows(board_id)
            name_lower = search_value.strip().lower()
            return [r for r in all_rows if name_lower in (r.get("item_name") or "")]
        else:
            return _fetch_filtered_rows(board_id, search_key, search_value)

    return _fetch_all_rows(board_id)


# ─────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_args: dict) -> list[dict] | dict:
    if tool_name == "get_unique_values":
        return get_unique_values(
            board=tool_args.get("board", ""),
            column_id=tool_args.get("column_id", ""),
        )

    fn_map = {"get_deal_funnel": get_deal_funnel, "get_work_orders": get_work_orders}
    fn = fn_map.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool '{tool_name}'"}

    return fn(
        search_key          = tool_args.get("search_key") or None,
        search_value        = tool_args.get("search_value") or None,
        aggregate_column_id = tool_args.get("aggregate_column_id") or None,
        aggregate_func      = tool_args.get("aggregate_func", "SUM"),
    )


# ─────────────────────────────────────────────
# TOOL DEFINITIONS (passed to LLM)
# ─────────────────────────────────────────────

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "get_deal_funnel",
        "description": (
            "Query the Deal Funnel (sales pipeline) board. "
            "Always use col_ids from the schema, never column names. "
            "For totals/sums on the full board: set aggregate_column_id only. "
            "For totals for a specific deal/entity by name: set search_key='name', "
            "search_value=<entity name>, AND aggregate_column_id=<col_id>. "
            "For listing rows by name: set search_key='name', search_value=<name>. "
            "For filtering by a status/category column: set search_key=<col_id>, search_value=<value>. "
            "For full board overview: no params."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_key":          {"type": "string", "description": "Use 'name' to filter by item name. Use a col_id like 'status', 'status1', 'text' for column filters."},
                "search_value":        {"type": "string", "description": "The value to search/filter for. Lowercase."},
                "aggregate_column_id": {"type": "string", "description": "col_id of the numeric column to sum/count (e.g. 'numbers' for deal value)."},
                "aggregate_func":      {"type": "string", "description": "SUM or COUNT. Default SUM."},
            },
            "required": [],
        },
    },
    {
        "name": "get_work_orders",
        "description": (
            "Query the Work Order Tracker board. "
            "Always use col_ids from the schema, never column names. "
            "For totals/sums on the full board: set aggregate_column_id only. "
            "For totals for a specific project/entity by name: set search_key='name', "
            "search_value=<entity name>, AND aggregate_column_id=<col_id>. "
            "For listing rows by name: set search_key='name', search_value=<name>. "
            "For filtering by a status/category column: set search_key=<col_id>, search_value=<value>. "
            "For full board overview: no params. "
            "Key numeric col_ids: 'numbers'=Amount Excl GST, 'numbers0'=Amount Incl GST, "
            "'numbers1'=Billed Excl GST, 'numbers2'=Billed Incl GST, "
            "'numbers3'=Collected Amount, 'numbers6'=Amount Receivable."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_key":          {"type": "string", "description": "Use 'name' to filter by item name. Use a col_id for column filters."},
                "search_value":        {"type": "string", "description": "The value to search/filter for. Lowercase."},
                "aggregate_column_id": {"type": "string", "description": "col_id of numeric column to sum/count. For amount excl GST use 'numbers'."},
                "aggregate_func":      {"type": "string", "description": "SUM or COUNT. Default SUM."},
            },
            "required": [],
        },
    },
    {
        "name": "get_unique_values",
        "description": (
            "Fetch all current unique values for a categorical column from Monday LIVE. "
            "Call this before filtering on any categorical column. "
            "board must be 'deal_funnel' or 'work_orders'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "board":     {"type": "string", "description": "Which board: 'deal_funnel' or 'work_orders'."},
                "column_id": {"type": "string", "description": "col_id to get unique values for."},
            },
            "required": ["board", "column_id"],
        },
    },
]


# ─────────────────────────────────────────────
# SMOKE TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("\n1. Filtered aggregate — total Amount Excl GST for alias_160")
    result = get_work_orders(
        search_key="name", search_value="alias_160",
        aggregate_column_id="numbers"
    )
    print(json.dumps(result, indent=2))
    # Expected: ~5,414,711.99

    print("\n2. Name search — all rows for alias_160")
    rows = get_work_orders(search_key="name", search_value="alias_160")
    print(f"  Rows returned: {len(rows) if isinstance(rows, list) else rows}")

    print("\n3. Full board aggregate — total WO amount")
    print(json.dumps(get_work_orders(aggregate_column_id="numbers"), indent=2))