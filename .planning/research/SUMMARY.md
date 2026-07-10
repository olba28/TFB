# Project Research Summary

**Project:** TFB — Water Stress & Economic Outcomes (UN SDG panel econometrics thesis)
**Domain:** Solo academic data-science pipeline: API ingestion → SQLite panel storage → fixed-effects panel econometrics (`linearmodels.PanelOLS`) → ML interpretability (SHAP) → counterfactual simulation → local Streamlit/Plotly geospatial dashboard
**Researched:** 2026-07-10
**Confidence:** MEDIUM-HIGH overall (stack empirically verified by installing and running the actual code; features/architecture/pitfalls cross-checked against multiple independent sources, no single "TFB rubric" document available)

## Executive Summary

This is a bachelor's-thesis (TFB) data-science pipeline, not a production application — the "user" is an academic tribunal evaluating rigor, reproducibility, and a 10-15 minute live oral defense. Experts build this shape of project as five layered stages (ingest → store → model → simulate/interpret → present), each following well-established, independently documented patterns (Cookiecutter Data Science project layout, `linearmodels.PanelOLS` fixed-effects econometrics, post-hoc SHAP interpretability, Streamlit-as-read-only-dashboard). The recommended stack (Python 3.12, pandas 3.0.3, SQLAlchemy 2.0.51, statsmodels 0.14.6, linearmodels 7.0, scikit-learn 1.9.0, shap 0.52.0, plotly 6.9.0, streamlit 1.59.1, plus a new addition, pycountry, for M49↔ISO3 country-code resolution) was not just researched but actually installed and exercised end-to-end in this session, giving unusually high confidence that the full pipeline will run without dependency conflicts.

The recommended approach: build an immutable raw-data layer first (UN SDG API dumps + manifest, versioned locally, never edited in place), derive a clean SQLite panel table from it, fit Model 1 (GDP growth) with a shared, reusable `PanelOLS` fitting function so Model 2 (agricultural productivity) can be added later as a thin configuration rather than a rewrite, then layer counterfactual simulation, SHAP interpretability, and a purely-read-only Streamlit dashboard on top of already-serialized model artifacts. This ordering directly mirrors both the feature dependency graph and the architecture's data flow, and de-risks the two things PROJECT.md and the tribunal will scrutinize most: (1) reproducibility (raw/derived separation, pinned deps, seeds, versioned snapshots) and (2) methodological rigor (two-way fixed effects, clustered SEs, Hausman test, honest "FE controls confounding, not reverse causality" framing).

The key risks are concentrated at three points: **ingestion** (the UN SDG API returns multiple disaggregated rows per country-year and mixes regional aggregates into the country code space — both must be filtered before anything downstream trusts the panel), **modeling** (skipping two-way fixed effects or cluster-robust SEs are the two most examinable mistakes an econometrics-literate tribunal will look for), and **the live demo** (an uncached Streamlit dashboard or a heavy GeoJSON choropleth can visibly freeze during the 30%-weighted oral defense). All three are addressed with concrete, low-cost mitigations documented in PITFALLS.md and should be treated as phase-blocking checks, not later polish.

## Key Findings

### Recommended Stack

The full candidate stack was installed into an isolated environment and empirically exercised (`PanelOLS` fit weighted/unweighted with entity+time effects, SQLite round-trip via SQLAlchemy, `shap.TreeExplainer` on a scikit-learn model, `pycountry` M49→ISO3 resolution, and a Plotly choropleth build) — this is unusually strong verification for a stack report. No changes are needed to the technology choices already implied by PROJECT.md; the main new addition is `pycountry` (mandatory for the M49-numeric-to-ISO3-alpha3 crosswalk the choropleth needs) and standardizing on a SQLAlchemy `Engine` (not raw `sqlite3.Connection`) for all `to_sql`/`read_sql` calls, since pandas itself documents the raw connection path as legacy-only.

**Core technologies:**
- Python 3.12 + pandas 3.0.3 — runtime and DataFrame engine; verified compatible with `linearmodels.PanelOLS` despite an unresolved-looking upstream TODO comment (empirically no breakage found)
- `linearmodels` 7.0 + `statsmodels` 0.14.6 — the only first-class Python library offering `PanelOLS` fixed-effects panel regression with entity+time effects and clustered SEs
- SQLite (stdlib) + SQLAlchemy 2.0.51 — single-file, zero-ops local panel storage; pandas' own recommended I/O path
- scikit-learn 1.9.0 + shap 0.52.0 — auxiliary tree model (`RandomForestRegressor`) fit purely to give SHAP's `TreeExplainer` a native home, presented as a corroborating lens alongside (not instead of) the causal `PanelOLS` results
- plotly 6.9.0 + streamlit 1.59.1 + pycountry 26.2.16 — local interactive choropleth dashboard; `pycountry` bridges the API's M49 numeric codes to the ISO3 codes Plotly's `locationmode="ISO-3"` requires

### Expected Features

A tribunal evaluating an applied econometrics + ML thesis has a well-defined table-stakes bar that goes beyond "it runs" — it expects visible methodological self-justification at every step (why FE, why these SEs, why this sample).

**Must have (table stakes):**
- Versioned, immutable local data snapshot (raw + processed) with documented coverage filtering (≥70% rule) and explicit missing-data-pattern discussion (MNAR risk, not just "some data was missing")
- Model 1 (PanelOLS, entity+time fixed effects) with pooled/RE baseline comparison, Hausman test, and clustered (or Driscoll-Kraay) standard errors — not a naive single-spec fit
- At least one robustness check (alternate spec or subsample), a bootstrap-CI counterfactual simulation explicitly framed as sensitivity analysis (never causal prediction), and SHAP interpretability with a stated correlated-feature caveat
- A local Streamlit/Plotly dashboard that works reliably offline during the live defense, plus reproducibility artifacts (`requirements.lock.txt`, fixed seeds) and a dedicated "Limitations/Threats to Validity" section

**Should have (differentiators):**
- Model 2 (agricultural productivity, indicator 2.3.1) fully executed as a stretch goal, reusing Model 1's methodology
- Multi-scenario counterfactual sensitivity chart (not a single point estimate) and regional/income-group heterogeneity analysis
- SHAP + ALE/partial-dependence as a complementary check against SHAP's known correlated-feature distortion

**Defer (out of scope for this thesis):**
- Formal causal identification (IV/DiD/synthetic control) — no credible instrument identified, conflicts with the chosen "sensitivity simulation, not causal prediction" framing
- Real-time/streaming ingestion, subnational granularity, per-country predictive models, online dashboard deployment, second-order effects (migration/conflict/health), or a general-purpose reusable ingestion platform

### Architecture Approach

The project follows a five-layer pipeline (ingestion → storage → transformation/EDA → modeling → simulation/interpretability → dashboard) built on an immutable-raw/regenerable-derived data principle, extending the existing skeleton (`src/ingesta/`, `data/`, `notebook/`, `figuras/`) additively rather than restructuring it. The single most important structural decision is a shared `panel_base.py` fitting/diagnostics function used by both Model 1 and Model 2, so the stretch-goal model becomes a thin configuration rather than a parallel implementation — directly de-risking the project's own "Modelo 2 if time allows" contingency.

**Major components:**
1. `src/ingesta/` — UN SDG API client with pagination/retry, writes raw JSON + provenance manifest before any transformation touches it
2. `data/panel.db` (SQLite) — single source of truth: `raw_observations` (long, immutable) + `panel` (wide, clean) tables
3. `src/etl/` — cleaning, 70%-coverage filtering, multi-indicator merge, feature engineering (idempotent, always rebuildable from raw)
4. `src/modelos/` — shared `panel_base.py` fitting helper, `model1_gdp.py`, `model2_agri.py`, `interpret.py` (SHAP, strictly post-hoc against a serialized model)
5. `src/simulacion/` + `src/dashboard/` — downstream, read-only consumers of serialized model artifacts; dashboard never trains, never calls the live API, never refits on interaction

### Critical Pitfalls

1. **UN SDG API rows are not automatically one-row-per-country-year** (multiple dimension combinations per indicator) — assert `(country, year)` uniqueness after explicit dimension filtering, before any storage/EDA work.
2. **Regional aggregates leak into the country panel** because M49 codes for regions and countries look identical — build a canonical countries-only list (via `pycountry`/UN M49 standard) and filter at ingestion time, not downstream.
3. **Two-way fixed effects omitted** — country-FE-only does not absorb global shocks (2008-09, COVID-19); use `entity_effects=True, time_effects=True` as the baseline spec from the start, and report country-FE-only as a robustness comparison, not the other way around.
4. **Default (non-clustered) standard errors overstate significance** — always fit with `cov_type='clustered', cluster_entity=True`; this is a near-universal, easily-checked tribunal red flag if skipped.
5. **Uncached Streamlit dashboard / heavy GeoJSON choropleth freezes during the live defense** — precompute all simulation/SHAP artifacts, cache SQLite reads (`st.cache_data`) and the fitted model (`st.cache_resource`), and use a simplified low-resolution boundary or Plotly's built-in `locationmode='ISO-3'`; rehearse with a cold cache on the actual presentation machine.

## Implications for Roadmap

Based on combined research, the feature dependency graph, and the architecture's layered data flow, the following phase structure is suggested. Order follows the hard dependency chain already identified in FEATURES.md (ingestion → storage → cleaning → EDA → Model 1 → diagnostics → robustness/SHAP/simulation → dashboard), with Model 2 explicitly deferred as a P2 extension.

### Phase 1: Data Ingestion & Versioned Storage
**Rationale:** Everything downstream requires the versioned local snapshot first; this is also the single point of failure PROJECT.md already flags (API changes/instability), so it must be de-risked immediately.
**Delivers:** UN SDG API client (pagination, retry/backoff), raw JSON dumps + provenance manifest per indicator, `raw_observations` SQLite table, canonical M49/ISO3 country crosswalk (`pycountry`)-filtered country list.
**Addresses:** "Versioned local data snapshot," "documented coverage filtering," reproducibility artifacts (FEATURES.md P1 items).
**Avoids:** Pitfall 1 (dimension duplication), Pitfall 2 (regional aggregates leaking in), Pitfall 3 (name-based country joins), Pitfall 4 (untrusted API values — add a manual spot-check step here).

### Phase 2: Panel Construction & EDA
**Rationale:** Cleaning, coverage filtering, and merging must be logged and idempotent before any model touches the data; EDA generates the hypotheses that inform model specification and is the tribunal's expected first analytical chapter.
**Delivers:** `panel` (wide, clean) SQLite table via `src/etl/` (clean, merge, features), documented 70%-coverage exclusions and missing-data pattern discussion, EDA notebook (global/regional/typology descriptive stats + correlation/VIF matrix).
**Uses:** pandas 3.0.3, SQLAlchemy 2.0.51, `src/etl/clean.py|merge.py|features.py`.
**Implements:** ARCHITECTURE.md's "immutable raw layer + regenerable derived layers" pattern (Pattern 1).
**Avoids:** Pitfall 12 (silent panel shrinkage on merge — log row/country counts before/after every merge).

### Phase 3: Model 1 — Panel Fixed-Effects Regression (GDP Growth)
**Rationale:** This is the core econometric deliverable and the thesis's central methodological claim; must be built with the correct baseline specification from day one, not patched later, since two-way FE and clustered SEs are foundational, not add-ons.
**Delivers:** Shared `panel_base.py` fitting/diagnostics helper, `model1_gdp.py` (two-way FE `PanelOLS`, clustered SEs), pooled/RE baseline comparison, Hausman test, VIF check, at least one robustness check (alt. spec/subsample), serialized `model1_gdp.pkl`.
**Uses:** linearmodels 7.0, statsmodels 0.14.6.
**Avoids:** Pitfall 5 (missing two-way FE), Pitfall 6 (non-clustered SEs), Pitfall 7 (overstated reverse-causality mitigation — draft the limitations paragraph here, not at the end).

### Phase 4: Interpretability, Simulation & Robustness Deepening
**Rationale:** Both SHAP and counterfactual simulation require a diagnosed, robustness-checked Model 1 — not a raw first fit — since bootstrapping CIs or computing SHAP against a mis-specified model produces confidently wrong results.
**Delivers:** `src/modelos/interpret.py` (SHAP via TreeExplainer on an auxiliary sklearn model, correlation/VIF-informed caveats), `src/simulacion/contrafactual.py` (bootstrap-CI counterfactual simulation with empirical-range bounds-checking), results tables written to `data/resultados/`.
**Uses:** scikit-learn 1.9.0, shap 0.52.0.
**Avoids:** Pitfall 8 (extrapolation beyond data support), Pitfall 9 (understated CIs — use block/cluster bootstrap), Pitfall 10 (SHAP on correlated regressors), Pitfall 11 (wrong/expensive SHAP explainer).

### Phase 5: Dashboard & Defense Readiness
**Rationale:** The dashboard is a pure, read-only consumer of already-computed artifacts and exists to serve a specific 10-15 minute live event (30% of grade) — it must be built and rehearsed as a demo-reliability artifact, not just a feature checklist.
**Delivers:** Streamlit app (`src/dashboard/app.py`, `plots.py`) with cached data loading, choropleth (simplified boundary or `locationmode='ISO-3'`), scenario explorer, SHAP summary view; cold-cache timing rehearsal on presentation hardware; pre-rendered fallback screenshots/video.
**Uses:** plotly 6.9.0, streamlit 1.59.1.
**Avoids:** Pitfall 14 (uncached Streamlit reruns), Pitfall 15 (heavy GeoJSON choropleth).

### Phase 6 (Stretch, P2): Model 2 — Agricultural Productivity Extension
**Rationale:** Explicitly scoped in PROJECT.md as "if progress allows"; only pursue once Model 1's full pipeline (diagnostics, robustness, simulation, SHAP, dashboard) is solid, reusing `panel_base.py` rather than rebuilding.
**Delivers:** `model2_agri.py` reusing shared fitting/diagnostics code, documented country-coverage limitations if the sample narrows for indicator 2.3.1, dashboard/simulation/SHAP extended to cover Model 2 outputs.
**Addresses:** FEATURES.md P2 differentiator ("Model 2 fully executed, not just attempted").

### Phase Ordering Rationale

- Ingestion/storage must precede everything else because it is the single external dependency and reproducibility anchor (PROJECT.md's own top risk).
- Diagnostics (Hausman, VIF, CSD test) must precede robustness checks and the final reported model — you cannot credibly claim "robust SEs" without first testing which violation is present.
- Simulation and SHAP both require a diagnosed, serialized Model 1, not a raw fit — architecture enforces this via the "post-hoc, load-the-pickle" pattern (never refit inside `simulacion/` or `interpret.py`).
- Dashboard is deliberately last among the core phases because it is a pure artifact consumer — building it before model outputs exist would create rework, and its main risk (demo performance) is best mitigated once real data volumes are known.
- Model 2 is explicitly sequenced after all of Model 1's downstream work (not in parallel) because PROJECT.md frames it as a stretch goal contingent on time remaining, and the shared `panel_base.py` abstraction only pays off once Model 1's specification is stable.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Model 1):** SHAP-vs-PanelOLS decoupling strategy (`KernelExplainer` on `PanelOLS.predict` vs. auxiliary sklearn model) is flagged in ARCHITECTURE.md as a decision to make explicitly during modeling — worth a `--research-phase` pass to confirm the chosen approach before committing code.
- **Phase 4 (Interpretability/Simulation):** Bootstrap methodology for the counterfactual CI (block/cluster bootstrap over countries, refit per draw) is more involved than a standard analytical CI and benefits from a focused implementation check.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Ingestion):** UN SDG API usage pattern, pagination, dimension-filtering gotcha, and M49→ISO3 crosswalk are all already concretely documented and live-verified in STACK.md/PITFALLS.md.
- **Phase 5 (Dashboard):** Streamlit caching split (`st.cache_data`/`st.cache_resource`) and Plotly choropleth setup are well-documented, standard patterns with no open questions.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Empirically installed and executed (PanelOLS fit, SQLite round-trip, SHAP, choropleth) in an isolated environment on 2026-07-10, not just documentation review |
| Features | MEDIUM | Cross-checked against academic-thesis-rubric and applied-econometrics best-practice literature; no official UCMA TFB rubric document was available, so tribunal-expectation claims are generalized, not confirmed against this specific program |
| Architecture | MEDIUM | Individual layers (Cookiecutter Data Science shape, PanelOLS/SHAP/Streamlit patterns) are each well-documented and cross-verified across multiple sources; the exact composition for this specific pipeline shape has no single canonical template |
| Pitfalls | MEDIUM-HIGH | Econometric/ML pitfalls (two-way FE, clustered SEs, SHAP correlated-feature distortion) are grounded in established literature (Nickell 1981, Wooldridge, SHAP interpretability papers); UN SDG API-specific behaviors (dimension duplication, pagination limits) were live-verified in the stack research session |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- No official UCMA TFB grading rubric was located — feature/table-stakes claims are generalized from academic-thesis-evaluation literature; validate against the actual program rubric or tutor guidance early, ideally before Phase 3 diagnostics are finalized.
- The SHAP-on-PanelOLS decoupling strategy (auxiliary sklearn model vs. `KernelExplainer` wrapping `PanelOLS.predict`) is a real open methodological decision, not yet made — flagged as a Phase 3 research item above; resolve during phase planning, not mid-execution.
- Indicator 2.3.1 (agricultural productivity) country/year coverage was not live-tested against the API in this research pass — PROJECT.md already flags this as a risk; verify actual coverage numbers early in Phase 1 ingestion before committing to Model 2 scope in Phase 6.

## Sources

### Primary (HIGH confidence)
- `https://unstats.un.org/SDGAPI/swagger/v1/swagger.json` and live queries against `https://unstats.un.org/SDGAPI/v1/sdg/` — endpoint/parameter/response-schema, pagination limits, dimensions gotcha (directly observed)
- Isolated virtual environment install + executed smoke tests (PanelOLS fit, SQLite round-trip, SHAP TreeExplainer, pycountry M49→ISO3, Plotly choropleth) — run directly in this research session
- `https://pypi.org/pypi/<package>/json` for all core/supporting libraries — official release metadata and `requires_python` constraints
- `.planning/PROJECT.md` and `.planning/codebase/ARCHITECTURE.md`/`STRUCTURE.md` — primary project scope, risks, and existing skeleton (direct repo inspection)

### Secondary (MEDIUM confidence)
- Cookiecutter Data Science official docs and multiple independent reproducible-data-science project-structure guides — project layout pattern
- `linearmodels`/`statsmodels`/SHAP official docs and tutorials — PanelOLS/MultiIndex workflow, SHAP explainer placement
- Streamlit official caching docs — `st.cache_data` vs `st.cache_resource` split
- Nickell (1981), clustered-SE and cross-sectional-dependence literature (Hoechle, Driscoll-Kraay), SHAP correlated-feature-attribution literature (2024-2026 papers) — econometric/ML pitfall grounding
- Academic-thesis-rubric research (Assessment & Evaluation in Higher Education; food-science bachelor-thesis rubric validation study) — generalized tribunal-expectation claims

### Tertiary (LOW confidence)
- `linearmodels` GitHub source comment re: pandas 3 compatibility — superseded by direct empirical verification, which found no actual breakage

---
*Research completed: 2026-07-10*
*Ready for roadmap: yes*
