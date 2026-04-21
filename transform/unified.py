"""
Public data access layer for the app.

Views never talk to `sources/` or touch the normalization logic directly.
They call `load_data()` here and get back a small, typed bundle of DataFrames
that are guaranteed to follow the funnel model (5 events, in order).

If the source changes (Google Sheets → Airtable → Dimitri's API), this file
and this file only is the place where the app cares. The views don't change.
"""
from dataclasses import dataclass

import pandas as pd

from sources import get_active_source
from transform.events import attach_project_labels, attribute_training_to_project, normalize_events


@dataclass
class DashboardData:
    """Everything a view needs to render. Typed so editors can autocomplete."""

    fct: pd.DataFrame           # fct_events, normalized to the 5-event funnel
    experts: pd.DataFrame       # dim_expert
    projects: pd.DataFrame      # dim_project
    trainings: pd.DataFrame     # dim_training
    source_name: str            # human label of the active source
    source_freshness: str       # human label of how fresh the data is


def load_data() -> DashboardData:
    """Load data through the active source and normalize it for the views.

    Cached by Streamlit at the call-site (see app.py) — NOT here, so that this
    module stays framework-agnostic and unit-testable.
    """
    src = get_active_source()
    raw = src.load()

    fct = normalize_events(raw.fct_events)
    fct = attribute_training_to_project(fct)
    fct = attach_project_labels(fct, raw.dim_project)

    return DashboardData(
        fct=fct,
        experts=raw.dim_expert,
        projects=raw.dim_project,
        trainings=raw.dim_training,
        source_name=src.name,
        source_freshness=src.freshness(),
    )


# ---------------------------------------------------------------------------
# Small derived helpers the views reuse. Keep them here so if the shape of
# fct ever changes, the blast radius stays inside transform/.
# ---------------------------------------------------------------------------

def unique_experts_by_event(fct: pd.DataFrame) -> pd.Series:
    """Count of distinct experts that reached each funnel stage. Global.

    Counts are over ever-reached (an expert certified last month still counts
    as having `outreached`, even if that event is older than the filter window
    — the caller is responsible for filtering `fct` first if they want a
    windowed view).
    """
    return (
        fct.dropna(subset=["expert_id"])
        .groupby("event_name", observed=True)["expert_id"]
        .nunique()
    )


def unique_experts_by_event_and_project(fct: pd.DataFrame) -> pd.DataFrame:
    """Pivot: rows=event, cols=project_name, values=distinct experts."""
    return (
        fct.dropna(subset=["expert_id"])
        .groupby(["event_name", "project_name"], observed=True)["expert_id"]
        .nunique()
        .unstack(fill_value=0)
    )


def drop_off_rates(counts: pd.Series) -> pd.DataFrame:
    """Given counts-by-event in funnel order, compute step drop-offs.

    Returns one row per transition: from_stage → to_stage, with absolute loss,
    conversion % and drop-off %.
    """
    from config import FUNNEL_EVENTS, FUNNEL_LABELS

    rows = []
    # Reindex to the canonical order (fills missing stages with 0).
    counts = counts.reindex(FUNNEL_EVENTS, fill_value=0)

    for i in range(len(FUNNEL_EVENTS) - 1):
        frm = FUNNEL_EVENTS[i]
        to = FUNNEL_EVENTS[i + 1]
        frm_n = int(counts.loc[frm])
        to_n = int(counts.loc[to])
        conv = (to_n / frm_n * 100) if frm_n > 0 else 0.0
        rows.append({
            "from_stage": FUNNEL_LABELS[frm],
            "to_stage": FUNNEL_LABELS[to],
            "from_n": frm_n,
            "to_n": to_n,
            "conversion_pct": round(conv, 1),
            "drop_pct": round(100 - conv, 1),
            "lost_experts": frm_n - to_n,
        })
    return pd.DataFrame(rows)
