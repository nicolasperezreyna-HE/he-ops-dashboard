# HE Ops Dashboard

> Initiative E — Ops Dashboard & Project Visibility. First draft (v1).
> Built on Streamlit. Designed so the front survives when the data source changes.

---

## What this is

A lightweight dashboard that answers three questions about the expert funnel:

- **Monitor** — what's happening right now? Counts at every stage, per project.
- **Optimize** — where are we losing experts? Drop-off between every pair of stages.
- **Compare** — how does this project / cohort compare to another?

Data model follows the 5-event funnel agreed with Thom on Apr 20, 2026:

```
Outreached → Presented → Accepted Terms → Started Training → Certified
```

---

## Architecture (why it looks the way it does)

The app has four layers, on purpose:

```
app.py                  ← Streamlit entry point, navigation, caching
   ↓
transform/unified.py    ← Normalizes raw data into the 5-event funnel model
   ↓
sources/<adapter>.py    ← Where the data comes from (swappable)
   ↓
views/                  ← Monitor, Optimize, Compare — only read from transform/
```

**The views never talk to the raw data directly.** They always go through
`transform.unified.load_data()`. The only thing that knows about Google Sheets
(or Airtable, or Dimitri's future API) is one file under `sources/`.

When the backend changes:

1. Write a new adapter at `sources/<new_source>.py` implementing `BaseSource`.
2. Change `config.SOURCE` to `"<new_source>"`.
3. Deploy. Nothing else moves.

---

## Repo layout

```
ops_dashboard/
├── app.py                     # Streamlit entry point
├── config.py                  # SOURCE switch, funnel definition
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml            # theme, no secrets
│
├── sources/                   # Data adapters
│   ├── base.py                # Abstract interface (RawTables, BaseSource)
│   ├── local_xlsx.py          # v1 — reads data/unified_dataset.xlsx
│   └── google_sheets.py       # stub, ready to implement
│
├── transform/                 # Pure data transformations
│   ├── events.py              # 6-event → 5-event mapping (certified merge)
│   └── unified.py             # load_data() + small helpers for views
│
├── views/                     # Streamlit pages
│   ├── _filters.py            # Shared sidebar widgets
│   ├── monitor.py
│   ├── optimize.py
│   └── compare.py
│
└── data/
    └── unified_dataset.xlsx   # v1 source (copy of 02_Unified_Dataset_v1.xlsx)
                               # NOT committed — contains expert PII.
```

---

## Run it locally

Requires Python 3.10+.

```bash
cd ops_dashboard
pip install -r requirements.txt
streamlit run app.py
```

Streamlit opens a browser tab at `http://localhost:8501`. Data is cached for
60 seconds per `config.DATA_CACHE_TTL_SECONDS`.

If you pull new data into `data/unified_dataset.xlsx`, either wait 60 s or
click "Clear cache" in the Streamlit menu (top-right → settings).

---

## Deploy to Streamlit Cloud (recommended for v1)

One-time setup (~15 minutes total):

1. **Push this folder to a GitHub repo.**
   - Create a repo (private is fine).
   - Do **not** commit `data/unified_dataset.xlsx` — it's excluded in `.gitignore`
     because it contains expert PII. Upload it separately once the app is deployed
     (Streamlit Cloud has a file storage mechanism, or we move to Google Sheets).
2. **Go to [share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
3. **Click "New app"**, pick the repo, branch `main`, file `app.py`.
4. **Wait ~2 minutes** for the first deploy.

### Make it private (recommended — data has expert emails)

1. In the Streamlit Cloud app settings, find **"Viewer access"**.
2. Switch from public to **"Only specific people"**.
3. Add the emails allowed to view (Nicolas, Thom, Kostas, whoever).
4. Those users log in with Google. If their email is on the list, they see the app.
   If not, access denied.

No code changes. No library added. Streamlit handles the auth.

---

## Switching from local XLSX to live Google Sheets

When we're ready for live data:

1. **Google Cloud Console → create a service account** (one-time).
2. **Share both source sheets** (HE Expert Payments 1.0 and Expert Community
   Building - Training Tracker) with the service account email, viewer access.
3. **Put the service account JSON into Streamlit Secrets.** In Streamlit Cloud:
   `Settings → Secrets` → paste under the `[gcp_service_account]` block.
4. **Implement `sources/google_sheets.py`** — the stub shows what's expected.
   Copy the join/build logic from the existing `build_unified.py` pipeline,
   just replacing `pd.read_excel(...)` with `gspread` calls.
5. **Change `config.SOURCE`** from `"local_xlsx"` to `"google_sheets"`.
6. **Uncomment** `gspread` and `google-auth` in `requirements.txt`.
7. **Redeploy.**

The views, the transform layer, and the 5-event model do not change.

---

## Switching again (future: Airtable, Dialectica API, …)

Same drill. Add `sources/<new_source>.py` with a class that inherits
`BaseSource`, returns a `RawTables` object, update `config.SOURCE`, deploy.

The only invariant is the contract in `sources/base.py`. As long as an adapter
returns the 4 tables (`fct_events`, `dim_expert`, `dim_project`, `dim_training`)
with the expected minimum columns, the rest of the app is unaffected.

---

## Known limitations / caveats (v1)

- **`terms_accepted_at_datetime` is NULL in ~98% of Maven rows.** The `Accepted
  Terms` stage uses `fuski_invited` as a proxy. This will become a real timestamp
  once the Fuski API is connected (~2 weeks out, per the Initiative E plan).
  Reported to Dimitri/Kostas.
- **Training events land without `project_id`.** `build_unified.py` does not yet
  consume the `Fuski Batches` tab, so training-grain events (Started Training,
  Certified) show up under "(no project)" when filtering by project. Mechanical
  fix, on the backlog.
- **AI Legal Training has a 0.9% cert rate.** Not a dashboard bug — it's real
  source data. The training flow may have been paused. Topic for the next sync
  with Kostas/Thom.

---

## Updating the data today (before Google Sheets is wired)

1. Re-run `build_unified.py` whenever the source sheets change.
2. Copy the fresh `02_Unified_Dataset_v1.xlsx` into `ops_dashboard/data/unified_dataset.xlsx`.
3. The Streamlit cache expires in 60 s or can be cleared manually.

---

## Contact

Owner: Nicolas Perez. Built with Claude on Apr 21, 2026.

See also:
- `../01_Schema_Design.md` — data model spec (v1.2, ByEither join canonical)
- `../03_Vibecoder_Spec.md` — original spec for the dashboard
- `../Ops_Events_Properties.pptx` — 2-slide summary of the event model for the team
