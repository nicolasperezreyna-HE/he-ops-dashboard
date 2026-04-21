"""
Abstract interface that every data source must implement.

Contract:
    Every adapter must return 4 DataFrames with the columns documented below.
    The rest of the app only depends on this contract, not on where the data
    came from. If Dimitri's future source delivers the same shape, we swap
    the adapter and nothing else changes.

All timestamps must be tz-naive datetimes. Strings are normalized elsewhere
(transform/ layer).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class RawTables:
    """Container for the 4 DataFrames a source must provide."""

    fct_events: pd.DataFrame        # one row per event (expert x project x event)
    dim_expert: pd.DataFrame        # one row per expert
    dim_project: pd.DataFrame       # one row per project
    dim_training: pd.DataFrame      # one row per training (T1-T4)


class BaseSource(ABC):
    """Abstract base class for a data source adapter."""

    # Subclasses set this to a short human-readable label for the UI footer.
    name: str = "base"

    @abstractmethod
    def load(self) -> RawTables:
        """Load the 4 tables and return them. Must be idempotent.

        Expected columns (minimum — extras are fine, the transform layer
        only consumes the ones it needs):

        fct_events:
            event_name          str (one of: outreached, presented,
                                              fuski_invited, joined_fuski,
                                              completed_training, certificate_issued)
            event_timestamp     datetime
            event_date          date
            expert_id           str
            project_id          str | None
            cst_owner           str | None
            client_name         str | None
            office_name         str | None
            source_system       str

        dim_expert:
            expert_id           str
            expert_name         str
            expert_email        str
            domain              str | None
            subdomain           str | None
            geography           str | None
            current_funnel_stage str | None
            is_certified        bool

        dim_project:
            project_id          str
            project_name        str
            client_name         str | None
            project_domain      str | None
            is_active           bool

        dim_training:
            training_id         str
            training_name       str
        """
        raise NotImplementedError

    def freshness(self) -> str:
        """Return a human-readable string describing how fresh the data is.

        Overridden by live sources (Google Sheets, Airtable) to show last
        sync time. Defaults to 'unknown' for static sources.
        """
        return "unknown"
