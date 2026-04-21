"""
Monitor view — answers: "what's happening in the funnel right now?"

Shows:
  - Headline KPIs: total experts at each stage, over the selected window.
  - Horizontal funnel chart (global).
  - Table of counts by project × event.
"""
import pandas as pd
import streamlit as st

from config import FUNNEL_EVENTS, FUNNEL_LABELS
from transform.unified import (
    DashboardData,
    unique_experts_by_event,
    unique_experts_by_event_and_project,
)
from views._filters import apply_filters, render_filters


def render(data: DashboardData) -> None:
    st.header("Monitor — where are experts in the funnel?")
    st.caption(
        "Counts are distinct experts that reached each stage within the "
        "selected date range and projects."
    )

    filters = render_filters(data, key_prefix="monitor")
    fct = apply_filters(data.fct, filters)

    if fct.empty:
        st.warning("No events in the selected range.")
        return

    # --- Headline metrics --------------------------------------------------
    counts = unique_experts_by_event(fct).reindex(FUNNEL_EVENTS, fill_value=0)
    cols = st.columns(len(FUNNEL_EVENTS))
    for col, event in zip(cols, FUNNEL_EVENTS):
        col.metric(label=FUNNEL_LABELS[event], value=int(counts.loc[event]))

    st.divider()

    # --- Funnel bar chart --------------------------------------------------
    st.subheader("Global funnel")
    funnel_df = pd.DataFrame({
        "Stage": [FUNNEL_LABELS[e] for e in FUNNEL_EVENTS],
        "Experts": [int(counts.loc[e]) for e in FUNNEL_EVENTS],
    })
    st.bar_chart(funnel_df.set_index("Stage"), horizontal=True)

    # --- Counts by project -------------------------------------------------
    st.subheader("Counts by project")
    pivot = unique_experts_by_event_and_project(fct)
    # Reindex rows to funnel order, then prettify labels for display.
    pivot = pivot.reindex(FUNNEL_EVENTS, fill_value=0)
    pivot.index = [FUNNEL_LABELS[e] for e in pivot.index]
    pivot.index.name = "Stage"
    st.dataframe(pivot, width="stretch")

    # --- Activity timeline -------------------------------------------------
    st.subheader("Events per week")
    weekly = (
        fct.assign(week=pd.to_datetime(fct["event_timestamp"]).dt.to_period("W").dt.start_time)
        .groupby(["week", "event_name"], observed=True)["expert_id"].nunique()
        .unstack(fill_value=0)
    )
    # Apply canonical column order
    weekly = weekly.reindex(columns=[e for e in FUNNEL_EVENTS if e in weekly.columns])
    weekly.columns = [FUNNEL_LABELS[c] for c in weekly.columns]
    st.line_chart(weekly)
