"""
Global configuration for the Ops Dashboard.

This file is the single switch that decides where the data comes from.
When Dimitri migrates the source of truth (Airtable, a warehouse, a Dialectica API...),
the only thing that changes here is SOURCE. The rest of the app keeps working.

Author: Nicolas Perez + Claude
Last updated: 2026-04-21
"""
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Which data source is currently active.
# Must match one of the adapter names in sources/ (sources/<name>.py).
#
# Options today:
#   - "local_xlsx"    : reads the local 02_Unified_Dataset_v1.xlsx (v1, offline)
#   - "google_sheets" : reads live from the 2 source Google Sheets (stub)
#
# Future:
#   - "airtable"        : when Dimitri migrates the source of truth
#   - "dialectica_api"  : if Dimitri exposes an endpoint
# ---------------------------------------------------------------------------
SOURCE = "local_xlsx"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
LOCAL_XLSX_PATH = DATA_DIR / "unified_dataset.xlsx"

# Fallback: when the dataset is not shipped with the repo (public deploy,
# PII-sensitive data) the user uploads it via the UI. Streamlit Cloud's
# container filesystem is writable under /tmp; on local Windows/macOS this
# resolves to the OS temp dir. Persists until the container restarts.
UPLOADED_XLSX_PATH = Path(tempfile.gettempdir()) / "he_ops_uploaded_dataset.xlsx"

# ---------------------------------------------------------------------------
# Funnel definition — the 5 events agreed with Thom (Apr 20, 2026).
#
# The source dataset (v1.2 of the schema) has 6 granular events. The funnel
# agreed with Thom merges completed_training + certificate_issued into a
# single "Certified" step. The mapping lives in transform/events.py.
#
# Order matters: this is the stage ordering for drop-off and current_stage.
# ---------------------------------------------------------------------------
FUNNEL_EVENTS = [
    "outreached",
    "presented",
    "accepted_terms",   # proxy today = fuski_invited; will be real once Fuski API lands
    "started_training", # = joined_fuski
    "certified",        # = completed_training OR certificate_issued (merged)
]

FUNNEL_LABELS = {
    "outreached":       "Outreached",
    "presented":        "Presented",
    "accepted_terms":   "Accepted Terms",
    "started_training": "Started Training",
    "certified":        "Certified",
}

# ---------------------------------------------------------------------------
# App settings (cosmetic)
# ---------------------------------------------------------------------------
APP_TITLE = "HE Ops Dashboard"
APP_ICON = ":bar_chart:"

# Streamlit cache TTL for data loads (seconds).
# Low for local dev, should be higher (e.g. 300-600) when pointing at live Google Sheets
# to avoid hammering the API.
DATA_CACHE_TTL_SECONDS = 60
