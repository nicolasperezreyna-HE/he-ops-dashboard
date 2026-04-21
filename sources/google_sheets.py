"""
Google Sheets adapter — live data source.

STATUS: stub. Not wired yet. Kept in the repo so the architecture is visible.

When we are ready to flip the switch:

    1. Create a service account in Google Cloud (one-time, Nicolas's account).
    2. Share "HE Expert Payments 1.0" and
       "Expert Community Building - Training Tracker (2)" with the service
       account email, read-only.
    3. Put the service account JSON in Streamlit Secrets under
       [gcp_service_account] (local dev: .streamlit/secrets.toml).
    4. Copy the logic from build_unified.py into _build_unified() below, but
       reading sheets via gspread instead of local xlsx.
    5. Change config.SOURCE to "google_sheets".

No code in the rest of the app changes.
"""
from datetime import datetime

from sources.base import BaseSource, RawTables


class Source(BaseSource):
    name = "google_sheets"

    # TODO: populate with actual sheet IDs when we wire the connection
    MAVEN_SHEET_ID = "TBD"
    TRACKER_SHEET_ID = "TBD"

    def load(self) -> RawTables:
        raise NotImplementedError(
            "google_sheets adapter is not implemented yet.\n"
            "To enable it:\n"
            "  1. Set up a Google service account and share both sheets with it.\n"
            "  2. Store credentials in Streamlit Secrets under [gcp_service_account].\n"
            "  3. Implement _read_sheet() and _build_unified() in this file.\n"
            "  4. Set config.SOURCE = 'google_sheets'."
        )

    def freshness(self) -> str:
        # When implemented, return the last fetch time from a cache.
        return datetime.now().strftime("live read, fetched %Y-%m-%d %H:%M")
