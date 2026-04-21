"""
Optimize view — answers: "where are we losing experts?"

Shows:
  - Step-by-step conversion and drop-off between every adjacent pair of
    funnel events (global).
  - Drop-off heatmap by project (which project bleeds at which step).
"""
import pandas as pd
import streamlit as st

from config import FUNNEL_EVENTS, FUNNEL_LABELS
from transform.unified import (
    DashboardData,
    drop_off_rates,
    unique_experts_by_event,
    unique_experts_by_event_and_project,
)
from views._filters import apply_filters, render_filters


def render(data: DashboardData) -> None:
    st.header("Optimize — where are we losing experts?")
    st.caption(
        "Step-by-step conversion between adjacent funnel stages. Drop-off = "
        "experts who reached the earlier stage but never the next one, "
        "within the selected window."
    )

    filters = render_filters(data, key_prefix="optimize")
    fct = apply_filters(data.fct, filters)

    if fct.empty:
        st.warning("No events in the selected range.")
        return

    # --- Global drop-off ----------------------------------------------------
    st.subheader("Global step conversion")
    counts = unique_experts_by_event(fct)
    drops = drop_off_rates(counts)

    show = drops.rename(columns={
        "from_stage": "From",
        "to_stage": "To",
        "from_n": "Experts @ from",
        "to_n": "Experts @ to",
        "conversion_pct": "Conversion %",
        "drop_pct": "Drop-off %",
        "lost_experts": "Lost",
    })
    st.dataframe(show, width="stretch", hide_index=True)

    st.bar_chart(
        drops.assign(label=drops["from_stage"] + " → " + drops["to_stage"])
        .set_index("label")[["drop_pct"]],
        horizontal=True,
    )

    st.divider()

    # --- Per-project drop-off heatmap --------------------------------------
    st.subheader("Drop-off % by project and step")
    st.caption("Higher bar = more experts lost at that step for that project. NaN = no experts reached the 'from' stage.")
    pivot = unique_experts_by_event_and_project(fct).reindex(FUNNEL_EVENTS, fill_value=0)

    rows = []
    for project in pivot.columns:
        proj_counts = pivot[project]
        for i in range(len(FUNNEL_EVENTS) - 1):
            frm, to = FUNNEL_EVENTS[i], FUNNEL_EVENTS[i + 1]
            frm_n = int(proj_counts.loc[frm])
            to_n = int(proj_counts.loc[to])
            drop = (1 - (to_n / frm_n)) * 100 if frm_n > 0 else None
            rows.append({
                "Project": project,
                "Step": f"{FUNNEL_LABELS[frm]} → {FUNNEL_LABELS[to]}",
                "Drop-off %": round(drop, 1) if drop is not None else None,
                "Lost": (frm_n - to_n) if frm_n > 0 else 0,
            })
    heat_df = pd.DataFrame(rows)

    # Render each step as a ProgressColumn — no Styler, no jinja2 dependency.
    step_order = [
        f"{FUNNEL_LABELS[FUNNEL_EVENTS[i]]} → {FUNNEL_LABELS[FUNNEL_EVENTS[i+1]]}"
        for i in range(len(FUNNEL_EVENTS) - 1)
    ]
    heat_pivot = heat_df.pivot(index="Project", columns="Step", values="Drop-off %").reindex(columns=step_order)

    column_config = {
        step: st.column_config.ProgressColumn(
            step, min_value=0, max_value=100, format="%.1f%%"
        )
        for step in step_order
    }
    st.dataframe(heat_pivot, width="stretch", column_config=column_config)

    with st.expander("Row-level data"):
        st.dataframe(heat_df, width="stretch", hide_index=True)
