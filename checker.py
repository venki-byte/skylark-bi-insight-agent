#!/usr/bin/env python3
"""
Monday.com Enhanced Schema Checker
----------------------------------
Verifies that the column IDs in skylark_schema.py match the actual IDs in Monday.
Also lists all columns with their real IDs and sample values to help you update the schema.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Import your schema to get the expected column definitions
from skylark_schema import WORK_ORDER_COLUMNS, DEAL_FUNNEL_COLUMNS

load_dotenv()

# Configuration
API_TOKEN = os.getenv("MONDAY_API_TOKEN")
WORK_ORDER_BOARD_ID = os.getenv("WORK_ORDER_BOARD_ID")
DEAL_FUNNEL_BOARD_ID = os.getenv("DEAL_FUNNEL_BOARD_ID")

API_URL = "https://api.monday.com/v2"
HEADERS = {
    "Authorization": API_TOKEN,
    "Content-Type": "application/json",
    "API-Version": "2024-01"
}

# Helper for colored output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color=Colors.OKGREEN, bold=False):
    if bold:
        print(f"{Colors.BOLD}{color}{text}{Colors.ENDC}")
    else:
        print(f"{color}{text}{Colors.ENDC}")

def run_query(query, variables=None):
    if not API_TOKEN:
        print_color("❌ MONDAY_API_TOKEN is not set in .env", Colors.FAIL, bold=True)
        sys.exit(1)

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            print_color(f"❌ GraphQL Error: {data['errors'][0]['message']}", Colors.FAIL)
            return None
        return data
    except requests.exceptions.Timeout:
        print_color("❌ Request timed out", Colors.FAIL)
    except requests.exceptions.RequestException as e:
        print_color(f"❌ Request failed: {e}", Colors.FAIL)
    return None

def get_board_columns(board_id):
    query = """
    query ($boardId: ID!) {
      boards(ids: [$boardId]) {
        columns {
          id
          title
          type
        }
      }
    }
    """
    data = run_query(query, {"boardId": board_id})
    if data and data.get("data", {}).get("boards"):
        return data["data"]["boards"][0]["columns"]
    return []

def fetch_sample_items(board_id, limit=5):
    query = """
    query ($boardId: [ID!]!, $limit: Int!) {
      boards(ids: $boardId) {
        items_page(limit: $limit) {
          items {
            id
            name
            column_values {
              column { id title }
              text
            }
          }
        }
      }
    }
    """
    data = run_query(query, {"boardId": [board_id], "limit": limit})
    if data and data.get("data", {}).get("boards"):
        return data["data"]["boards"][0]["items_page"]["items"]
    return []

def build_column_map(actual_columns):
    """Return dict mapping column title -> actual column id."""
    return {col["title"]: col["id"] for col in actual_columns}

def check_schema(board_name, schema_columns, actual_columns, sample_items):
    """
    Compare schema col_id with actual column ID for each column in schema.
    Print mismatches and suggestions.
    """
    actual_map = build_column_map(actual_columns)
    print_color(f"\n📋 Schema vs Actual for {board_name}", Colors.HEADER, bold=True)
    print("-" * 60)

    all_good = True
    for col in schema_columns:
        name = col["name"]
        schema_id = col["col_id"]
        actual_id = actual_map.get(name)
        if actual_id is None:
            print_color(f"  ❌ Column '{name}' not found in actual board!", Colors.FAIL)
            all_good = False
        elif schema_id == actual_id:
            print_color(f"  ✅ {name}: {schema_id} matches", Colors.OKGREEN)
        else:
            print_color(f"  ⚠️  {name}: schema '{schema_id}' → actual '{actual_id}'", Colors.WARNING)
            all_good = False

    if all_good:
        print_color("\n  ✅ All schema column IDs are correct!", Colors.OKGREEN, bold=True)

    # Also show sample values for key numeric columns
    print_color("\n📊 Sample values for key columns (first item):", Colors.OKBLUE)
    if sample_items:
        item = sample_items[0]
        for col in schema_columns:
            if "numeric" in col["type"]:
                # Find value in sample
                for cv in item["column_values"]:
                    if cv["column"]["title"] == col["name"]:
                        val = cv["text"]
                        print(f"  {col['name']}: {val}")
                        break

def main():
    if not API_TOKEN:
        print_color("❌ MONDAY_API_TOKEN missing in .env", Colors.FAIL, bold=True)
        return

    print_color("\n🔍 MONDAY.COM ENHANCED SCHEMA CHECKER", Colors.HEADER, bold=True)
    print_color("=" * 60, Colors.HEADER)

    # Check Work Order board
    if WORK_ORDER_BOARD_ID:
        print_color(f"\n📊 BOARD: Work Order Tracker (ID: {WORK_ORDER_BOARD_ID})", Colors.OKBLUE, bold=True)
        actual_cols = get_board_columns(WORK_ORDER_BOARD_ID)
        if actual_cols:
            samples = fetch_sample_items(WORK_ORDER_BOARD_ID, limit=1)
            check_schema("Work Order Tracker", WORK_ORDER_COLUMNS, actual_cols, samples)
        else:
            print("  Could not retrieve columns.")
    else:
        print_color("\n⚠️  WORK_ORDER_BOARD_ID not set", Colors.WARNING)

    # Check Deal Funnel board
    if DEAL_FUNNEL_BOARD_ID:
        print_color(f"\n📊 BOARD: Deal Funnel (ID: {DEAL_FUNNEL_BOARD_ID})", Colors.OKBLUE, bold=True)
        actual_cols = get_board_columns(DEAL_FUNNEL_BOARD_ID)
        if actual_cols:
            samples = fetch_sample_items(DEAL_FUNNEL_BOARD_ID, limit=1)
            check_schema("Deal Funnel", DEAL_FUNNEL_COLUMNS, actual_cols, samples)
        else:
            print("  Could not retrieve columns.")
    else:
        print_color("\n⚠️  DEAL_FUNNEL_BOARD_ID not set", Colors.WARNING)

    print_color("\n✅ Check complete.", Colors.OKGREEN, bold=True)

if __name__ == "__main__":
    main()