"""
Map the 6 granular events in the unified dataset to the 5-event funnel
agreed with Thom on Apr 20, 2026.

Why we remap here and not at the source
---------------------------------------
The source dataset (schema v1.2) stores 6 events because that's how they
land from Maven + Fuski. The operational funnel that the team tracks uses
5 steps — `certified` collapses `completed_training` and `certificate_issued`
into a single "expert is ready to work" milestone.

Doing the remap here keeps the source adapter faithful to the raw data
(auditable, no magic) while giving the views a clean, business-aligned
model to plot.

When the source of truth migrates to Dimitri's system, he may emit the 5
events directly. In that case, this module degrades to a no-op pass-through
(see `normalize_events`).

Funnel order
------------
    outreached → presented → accepted_terms → started_training → certified

Mapping
-------
    outreached              → outreached
    presented               → presented
    fuski_invited           → accepted_terms        (proxy today, real once Fuski API lands)
    joined_fuski            → started_training
    completed_training      → certified
    certificate_issued      → certified             (de-duped: earliest of the two per expert)
"""
import pandas as pd

from config import FUNNEL_EVENTS

# Mapping of source event_name -> funnel event_name.
SOURCE_TO_FUNNEL = {
    # Already in the funnel model
    "outreached":          "outreached",
    "presented":           "presented",
    "accepted_terms":      "accepted_terms",
    "started_training":    "started_training",
    "certified":           "certified",
    # v1.2 source names
    "fuski_invited":       "accepted_terms",
    "joined_fuski":        "started_training",
    "completed_training":  "certified",
    "certificate_issued":  "certified",
}


def normalize_events(fct_events: pd.DataFrame) -> pd.DataFrame:
    """Apply the 6 → 5 event mapping and deduplicate the merged `certified` event.

    Rules:
      - Map each source event to its funnel equivalent.
      - Drop rows whose source event is not in the mapping (defensive).
      - For `certified`, keep ONE event per (expert_id, project_id) pair — the
        earliest timestamp. This prevents double-counting when both
        `completed_training` and `certificate_issued` exist for the same expert.
      - All other events are left alone (already 1 row per expert/project/event).
    """
    df = fct_events.copy()

    # Map. Unknown events become NaN and are dropped.
    df["event_name"] = df["event_name"].map(SOURCE_TO_FUNNEL)
    df = df.dropna(subset=["event_name"])

    # Dedupe the merged `certified` event.
    # project_id can be NULL for training-grain events; fill with a sentinel
    # so groupby treats them as comparable.
    mask_cert = df["event_name"] == "certified"
    cert = df[mask_cert].copy()
    other = df[~mask_cert].copy()

    if not cert.empty:
        cert["_pid"] = cert["project_id"].fillna("__no_project__")
        cert = cert.sort_values("event_timestamp")
        cert = cert.drop_duplicates(subset=["expert_id", "_pid"], keep="first")
        cert = cert.drop(columns=["_pid"])

    out = pd.concat([other, cert], ignore_index=True)

    # Enforce the event_name is a categorical with the canonical order.
    # This makes every groupby downstream respect the funnel order automatically.
    out["event_name"] = pd.Categorical(
        out["event_name"], categories=FUNNEL_EVENTS, ordered=True
    )
    out = out.sort_values("event_timestamp").reset_index(drop=True)
    return out


def attribute_training_to_project(fct: pd.DataFrame) -> pd.DataFrame:
    """Best-effort attribution of training-grain events to a project.

    Why this exists
    ---------------
    The source pipeline (build_unified.py) does not yet consume the
    `Fuski Batches` tab, so training-grain events (accepted_terms,
    started_training, certified) arrive with `project_id = NULL`. Without
    this attribution, any per-project view of the last 3 funnel stages
    shows 0.

    Rule
    ----
    For each expert:
      1. Collect every project they were `outreached` OR `presented` for
         (presentation-grain events always carry a real project_id).
      2. If the expert has exactly one such project, attribute every
         NULL-project training event of that expert to that project.
      3. If they have multiple, attribute to the MOST RECENT one (by
         outreach/presentation timestamp).
      4. If none, leave project_id as NULL (rare — unattached training).

    When the real fix lands in build_unified.py (consuming Fuski Batches),
    this function becomes harmless — every training event will already
    have a project_id, so steps 1-3 find nothing to fill.
    """
    if fct.empty:
        return fct

    df = fct.copy()

    # Build a map: expert_id -> (project_id of their most recent outreach/presentation)
    presentation_mask = df["project_id"].notna()
    if not presentation_mask.any():
        return df

    pres = (
        df.loc[presentation_mask, ["expert_id", "project_id", "event_timestamp"]]
        .dropna(subset=["expert_id"])
        .sort_values("event_timestamp")
    )
    # Last project_id per expert = most recent outreach/presentation.
    expert_to_project = pres.groupby("expert_id")["project_id"].last()

    # Fill NULL project_ids for training events using the map.
    null_mask = df["project_id"].isna() & df["expert_id"].notna()
    df.loc[null_mask, "project_id"] = df.loc[null_mask, "expert_id"].map(expert_to_project)

    # Track which rows were attributed (so the UI can surface the caveat).
    df["project_attributed"] = False
    df.loc[null_mask & df["project_id"].notna(), "project_attributed"] = True

    return df


def attach_project_labels(fct: pd.DataFrame, dim_project: pd.DataFrame) -> pd.DataFrame:
    """Left-join project_name and project_domain onto fct_events.

    Training-grain events that couldn't be attributed (no matching outreach/
    presentation) stay under '(no project)'.
    """
    fct = fct.merge(
        dim_project[["project_id", "project_name", "project_domain"]],
        on="project_id", how="left", suffixes=("", "_proj"),
    )
    fct["project_name"] = fct["project_name"].fillna("(no project)")
    fct["project_domain"] = fct["project_domain"].fillna("(unknown)")
    return fct
