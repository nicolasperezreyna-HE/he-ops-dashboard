"""
Local XLSX adapter — v1 data source.

Reads `data/unified_dataset.xlsx` (the output of the existing build_unified.py
pipeline) and returns the 4 DataFrames the app needs. Zero network calls,
zero credentials. Good for offline dev and for the first Streamlit Cloud deploy
while we wait on service-account setup for Google Sheets.
"""
from datetime import datetime

import pandas as pd

from config import LOCAL_XLSX_PATH
from sources.base import BaseSource, RawTables


class Source(BaseSource):
    name = "local_xlsx"

    def load(self) -> RawTables:
        path = LOCAL_XLSX_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Expected dataset at {path}. "
                "Re-generate with build_unified.py or copy it into data/."
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
        if not LOCAL_XLSX_PATH.exists():
            return "missing"
        mtime = datetime.fromtimestamp(LOCAL_XLSX_PATH.stat().st_mtime)
        return f"local file, last modified {mtime:%Y-%m-%d %H:%M}"
