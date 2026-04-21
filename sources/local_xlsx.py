"""
Local XLSX adapter — v1 data source.

Reads `data/unified_dataset.xlsx` (the output of the existing build_unified.py
pipeline) and returns the 4 DataFrames the app needs. Zero network calls,
zero credentials. Good for offline dev and for the first Streamlit Cloud deploy
while we wait on service-account setup for Google Sheets.
"""
from datetime import datetime

import pandas as pd

from config import LOCAL_XLSX_PATH, UPLOADED_XLSX_PATH
from sources.base import BaseSource, RawTables


def _resolve_path():
    """Return the first existing path out of: bundled data/, then /tmp upload.

    This lets the same adapter work in two modes:
      - local dev: the full xlsx lives at ./data/unified_dataset.xlsx
      - public deploy: the xlsx is PII-sensitive and not in the repo; the user
        uploads it through the UI (app.py) which writes it to UPLOADED_XLSX_PATH.
    """
    for candidate in (LOCAL_XLSX_PATH, UPLOADED_XLSX_PATH):
        if candidate.exists():
            return candidate
    return None


class Source(BaseSource):
    name = "local_xlsx"

    def load(self) -> RawTables:
        path = _resolve_path()
        if path is None:
            raise FileNotFoundError(
                f"Expected dataset at {LOCAL_XLSX_PATH} or {UPLOADED_XLSX_PATH}. "
                "Re-generate with build_unified.py and copy into data/, or upload "
                "via the dashboard UI."
            )

        # errors='coerce' on timestamps protects us from occasional bad rows
        # (the source has a few out-of-range dates that crash pd.to_datetime).
        fct = pd.read_excel(path, sheet_name="fct_events")
        fct["event_timestamp"] = pd.to_datetime(fct["event_timestamp"], errors="coerce")
        fct["event_date"] = pd.to_datetime(fct["event_date"], errors="coerce").dt.date
        fct = fct.dropna(subset=["event_timestamp"])

        dim_expert = pd.read_excel(path, sheet_name="dim_expert")
        dim_project = pd.read_excel(path, sheet_name="dim_project")
        dim_training = pd.read_excel(path, sheet_name="dim_training")

        return RawTables(
            fct_events=fct,
            dim_expert=dim_expert,
            dim_project=dim_project,
            dim_training=dim_training,
        )

    def freshness(self) -> str:
        path = _resolve_path()
        if path is None:
            return "missing"
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        suffix = " (uploaded)" if path == UPLOADED_XLSX_PATH else ""
        return f"local file{suffix}, last modified {mtime:%Y-%m-%d %H:%M}"
