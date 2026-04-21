"""
HE Ops Dashboard — Streamlit entrypoint.

Run locally:
    streamlit run app.py

Architecture, in 30 seconds:
    sources/   : adapters that fetch raw data. Swap these when the backend changes.
    transform/ : pure functions that turn raw data into the funnel model.
    views/     : three Streamlit pages (Monitor / Optimize / Compare).
    config.py  : the single switch for which source is active.

Views never touch sources or raw data. They go through transform.unified.load_data().
That's the seam that protects the front when Dimitri's source of truth lands.
"""
import streamlit as st

from config import APP_ICON, APP_TITLE, DATA_CACHE_TTL_SECONDS
from transform.unified import DashboardData, load_data
from views import compare, monitor, optimize


st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")


# Streamlit caches the result so we don't re-read the xlsx (or re-hit Google)
# on every interaction. The TTL is set in config.py — short for local dev,
# longer in production to avoid API rate limits.
@st.cache_data(ttl=DATA_CACHE_TTL_SECONDS, show_spinner="Loading data...")
def _cached_load() -> DashboardData:
    return load_data()


def main() -> None:
    st.title(APP_TITLE)
    st.caption(
        "Initiative E · Ops Dashboard & Project Visibility · first draft (v1). "
        "Data model: 5-event funnel agreed with Thom (Apr 20, 2026)."
    )

    data = _cached_load()

    tab_monitor, tab_optimize, tab_compare, tab_about = st.tabs([
        "Monitor", "Optimize", "Compare", "About",
    ])
    with tab_monitor:
        monitor.render(data)
    with tab_optimize:
        optimize.render(data)
    with tab_compare:
        compare.render(data)
    with tab_about:
        _render_about(data)


def _render_about(data: DashboardData) -> None:
    st.header("About this dashboard")
    st.markdown(f"""
**Data source:** `{data.source_name}` ({data.source_freshness})

**Funnel (5 events, agreed with Thom on Apr 20, 2026):**

1. **Outreached** — CST associate first contacted the expert for the project.
2. **Presented** — Expert accepted being presented to the client.
3. **Accepted Terms** — Expert signed Terms of Engagement. *V1 proxy = `fuski_invited`*
   because Maven's `terms_accepted_at_datetime` is NULL in 98% of rows. This becomes
   real once the Fuski API is connected (~2 weeks).
4. **Started Training** — Expert joined the Fuski platform to start training.
5. **Certified** — Expert completed training and received the certificate.
   This step merges `completed_training` + `certificate_issued` from the source
   into a single business event.

**Three questions the dashboard answers:**

- **Monitor** — what's happening right now? (counts per stage, per project)
- **Optimize** — where are we losing experts? (drop-off between stages)
- **Compare** — how does one project/cohort compare to another?

**Known caveats (v1):**

- `terms_accepted_at_datetime` is NULL in 98% of Maven rows. Using `fuski_invited`
  as a proxy. Reported to Dimitri/Kostas.
- `build_unified.py` does not yet consume the `Fuski Batches` tab, so training
  events arrive without `project_id`. Impact: training-grain events are bucketed
  under "(no project)" until the fix lands.

Architecture is source-agnostic: changing `config.SOURCE` is the only change
needed when Dimitri's source of truth becomes available.
""")


if __name__ == "__main__":
    main()
