"""
Compare view — answers: "how does this project/cohort compare to another?"

Shows:
  - Side-by-side funnels (small multiples) for selected projects.
  - Conversion at each stage, per project, in a single table.
  - Benchmark line: global average vs. per-project conversion.
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
    st.header("Compare — how do projects stack up?")
    st.caption(
        "Select which projects to compare. Each column is one project's funnel; "
        "the table at the bottom shows conversion at every step."
    )

    filters = render_filters(data, key_prefix="compare")
    fct = apply_filters(data.fct, filters)

    if fct.empty:
        st.warning("No events in the selected range.")
        return

    pivot = unique_experts_by_event_and_project(fct).reindex(FUNNEL_EVENTS, fill_value=0)

    # If the sidebar multiselect narrowed projects to a subset, keep that subset.
    # Otherwise let the user pick a subset here.
    all_projects = list(pivot.columns)
    selected = st.multiselect(
        "Projects to compare",
        options=all_projects,
        default=all_projects[:3] if len(all_projects) > 3 else all_projects,
        key="compare_projects_to_compare",
    )
    if not selected:
        st.info("Pick at least one project.")
        return

    # --- Small multiples: one funnel bar chart per project -----------------
    st.subheader("Funnels side by side")
    cols = st.columns(len(selected))
    for col, project in zip(cols, selected):
        with col:
            st.markdown(f"**{project}**")
            series = pivot[project].reindex(FUNNEL_EVENTS, fill_value=0)
            df = pd.DataFrame({
                "Stage": [FUNNEL_LABELS[e] for e in FUNNEL_EVENTS],
                "Experts": series.values,
            }).set_index("Stage")
            st.bar_chart(df, horizontal=True)
            top = int(series.iloc[0]) if len(series) else 0
            bot = int(series.iloc[-1]) if len(series) else 0
            end_to_end = (bot / top * 100) if top > 0 else 0.0
            st.caption(
                f"End-to-end: {bot}/{top} ({end_to_end:.1f}%)"
            )

    st.divider()

    # --- Conversion table: one row per project, one column per step --------
    st.subheader("Step-by-step conversion, per project")
    rows = []
    for project in selected:
        series = pivot[project]
        row = {"Project": project}
        for i in range(len(FUNNEL_EVENTS) - 1):
            frm, to = FUNNEL_EVENTS[i], FUNNEL_EVENTS[i + 1]
            frm_n = int(series.loc[frm])
            to_n = int(series.loc[to])
            conv = (to_n / frm_n * 100) if frm_n > 0 else 0.0
            row[f"{FUNNEL_LABELS[frm]} → {FUNNEL_LABELS[to]}"] = round(conv, 1)
        # End-to-end
        top = int(series.iloc[0])
        bot = int(series.iloc[-1])
        row["End-to-end"] = round((bot / top * 100) if top > 0 else 0.0, 1)
        rows.append(row)

    out = pd.DataFrame(rows).set_index("Project")
    step_cols = [c for c in out.columns if "→" in c] + ["End-to-end"]
    column_config = {
        c: st.column_config.ProgressColumn(c, min_value=0, max_value=100, format="%.1f%%")
        for c in step_cols
    }
    st.dataframe(out, width="stretch", column_config=column_config)

    # --- Global benchmark --------------------------------------------------
    st.subheader("vs. global benchmark")
    global_counts = unique_experts_by_event(fct)
    global_drops = drop_off_rates(global_counts)
    bench = pd.DataFrame({
        "Step": [f"{r['from_stage']} → {r['to_stage']}" for _, r in global_drops.iterrows()],
        "Global conversion %": global_drops["conversion_pct"].values,
    }).set_index("Step")
    st.bar_chart(bench, horizontal=True)
    st.caption("Reads as: of experts who reached the 'from' stage, what % reached the 'to' stage.")
