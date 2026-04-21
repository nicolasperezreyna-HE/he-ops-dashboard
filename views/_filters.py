"""
Shared sidebar filter widgets.

Every view calls `render_filters()` to get a consistent set of cross-cutting
filters (date range, projects). The returned `Filters` object is passed to
`apply_filters()` to narrow `fct` before rendering.
"""
from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd
import streamlit as st

from transform.unified import DashboardData


@dataclass
class Filters:
    date_start: date | None
    date_end: date | None
    projects: List[str]        # empty list = all projects


def render_filters(data: DashboardData, key_prefix: str = "") -> Filters:
    """Render date + project filters in the Streamlit sidebar.

    `key_prefix` keeps widget keys unique when a view is rendered after another
    view (Streamlit requires unique keys per widget).
    """
    st.sidebar.subheader("Filters")

    # Date range — default to min/max of the data
    fct = data.fct
    if fct.empty:
        date_min = date_max = date.today()
    else:
        dates = pd.to_datetime(fct["event_timestamp"], errors="coerce").dropna()
        date_min = dates.min().date()
        date_max = dates.max().date()

    date_range = st.sidebar.date_input(
        "Event date range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        key=f"{key_prefix}_date_range",
    )
    # date_input can return a tuple or a single value depending on user interaction
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d_start, d_end = date_range
    else:
        d_start = d_end = date_range if isinstance(date_range, date) else date_min

    # Project filter
    all_projects = sorted(data.projects["project_name"].dropna().unique().tolist())
    selected = st.sidebar.multiselect(
        "Projects",
        options=all_projects,
        default=all_projects,
        key=f"{key_prefix}_projects",
    )
    if set(selected) == set(all_projects):
        selected = []  # treat "all" the same as empty = no filter

    st.sidebar.caption(
        f"Source: {data.source_name} · {data.source_freshness}"
    )
    return Filters(date_start=d_start, date_end=d_end, projects=selected)


def apply_filters(fct: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Narrow fct by the sidebar filters. Returns a new DataFrame."""
    out = fct
    if f.date_start is not None:
        out = out[pd.to_datetime(out["event_timestamp"]).dt.date >= f.date_start]
    if f.date_end is not None:
        out = out[pd.to_datetime(out["event_timestamp"]).dt.date <= f.date_end]
    if f.projects:
        out = out[out["project_name"].isin(f.projects)]
    return out
