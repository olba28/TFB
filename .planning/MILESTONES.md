# Milestones

## v1.0 MVP (Shipped: 2026-07-15)

**Phases completed:** 6 phases, 21 plans, 56 tasks

**Key accomplishments:**

- Project-scoped .venv with pinned requirements.lock.txt (REPRO-01), pytest/pytest-cov dev tooling, pyproject.toml pytest config, and empty src/ingesta + tests/ package skeletons; .gitignore activated and corrected for manifest tracking.
- UN SDG API client with urllib3.Retry-backed retry/backoff and dynamic per-indicator pagination, plus a pure file-I/O provenance manifest module (write/load/exists) — both fully unit-tested with zero live network calls.
- Reusable `countries.py` module (M49 canonical country list, M49-to-ISO3 crosswalk, documented exclusion log) built against the human-acquired official UN M49 CSV, satisfying INGEST-03's "no regional aggregate leaks into the panel" requirement.
- `src/db.py` storage layer: raw_observations enforces one row per (country, year, indicator) via UNIQUE + pre-insert assert; panel is a regenerable pivot rebuilt with `if_exists='replace'`, never hand-edited.
- `fetch_data.py` orchestrator composing the client/manifest/countries/db modules with a per-indicator dimension+series filter, live-run into `data/panel.db` (18,086 raw_observations rows, 4,923 panel rows, 215 countries, zero M49 leakage), approved by the user at the Task 3 checkpoint.
- Sandboxed the test that was silently corrupting versioned raw JSON, added an autouse write-guard for data/raw/, and restored all 5 indicators via a clean live re-ingestion (18,086 raw_observations / 4,923 panel rows, checksums verified against manifests)
- Captured UN development-status country typology (LDC/LLDC/SIDS, sourced entirely from GeoArea/Tree) and built an idempotent 70%-coverage-filtered clean panel (4,923 rows, matching Phase 1 exactly) that preserves every real observation unmodified while documenting 529 (country, indicator) exclusions separately
- Notebook with descriptive statistics, a numbers-grounded MNAR discussion (SIDS countries show ~2x the missingness of non-SIDS), and 12 VIF/correlation tables (global + 8 regions + 3 typology flags) informing Phase 3's Model 1 specification
- `src/panel_base.py` -- a dependent-variable-agnostic PanelOLS fit/diagnose module with country-level coverage exclusion, pooled/RE/FE comparison, and manually-implemented Hausman + Pesaran CD diagnostic tests, unit-tested with 13 pytest tests including a hand-computable Pesaran fixture.
- `notebook/3_1_modelo1_pib.ipynb` -- the real-data application of Plan 03-01's `panel_base.py`: a two-way fixed-effects fit of GDP-per-capita growth (8.1.1) on water stress (6.4.2) across 171 countries/3,933 observations, with a Pesaran-CD-driven Driscoll-Kraay SE choice, a Hausman-justified FE-vs-RE comparison, a COVID-excluded robustness check, and a reverse-causality/endogeneity limitations section, plus the serialized `data/modelos/model1_gdp.pkl` model.
- `src/simulate.py`: block-bootstrap counterfactual simulation (entity-relabeled, `SeedSequence`-seeded, non-extrapolation exclusion) plus interaction-term regional/typology heterogeneity, both dependent-variable-agnostic for Phase 6 reuse
- `src/interpret.py`: multivariate RandomForest (n_jobs=1, oob_score=True) feeding shap.TreeExplainer and sklearn PartialDependenceDisplay, preceded by a statsmodels VIF table -- zero new dependencies
- `notebook/4_1_interpretabilidad_simulacion.ipynb`: real-panel counterfactual simulation, heterogeneity analysis, and RF/SHAP/VIF/PDP interpretability stack, with `rf_shap_model.pkl` serialized and REPRO-02 proven bit-identical across two independent full executions
- Active-model registry (D-07), UI-SPEC Streamlit theme config, and Wave 0 pytest fixtures establishing `src/dashboard/` ahead of app/data/plots implementation.
- Pure, Streamlit-free Plotly builders (`build_choropleth`, `build_scenario_plot`, `build_pdp`) in `src/dashboard/plots.py`, isolating all figure construction — including DASH-04's animated, fixed-color-range choropleth — from Streamlit rendering.
- `src/dashboard/data.py` implements the full `st.cache_resource`/`st.cache_data` split (DASH-02) for Engine/model loaders and live-recomputed bootstrap/SHAP wrappers, reading only local `panel.db`/`.pkl` artifacts (DASH-01) — proven by `tests/dashboard/test_caching.py` inspecting Streamlit's own cache-decorator metadata rather than timing.
- `src/dashboard/app.py`, the single-page 4-tab Streamlit controller wiring `data.py`'s cached loaders + `plots.py`'s pure builders + `models.py`'s active-model registry into a wide-layout dashboard with side-by-side choropleth comparison (DASH-03/D-02), verified end-to-end via `AppTest` with no real `panel.db`/`.pkl` access.
- Cold-cache dashboard rehearsal on the presentation machine dropped from 10.59s to a measured 2.01s (well under the <5s DASH-05 target) after root-causing and fixing three live bugs — a duplicate-element crash, an unintended public network binding, and a RandomForest being refit from scratch on every session instead of loading the already-fitted artifact — plus four verified real-data Plan B screenshots as the oral-defense fallback.
- Added `filter_by_min_years` to `src/panel_base.py` -- a pure, country-level, >=N-observed-years coverage filter for Model 2's sparse 2.3.1 indicator, coexisting with (never wrapping) the existing 70%-of-years `filter_by_exclusions`.
- `src/model2_agri.py` extends the entire Model 1 methodology (two-way FE PanelOLS, Hausman/Pesaran diagnostics, sin-COVID robustness, 1000-replica bootstrap, is_ldc heterogeneity, SHAP) to indicator 2.3.1 by calling `panel_base`/`simulate`/`interpret` unmodified with `dep_var="2.3.1"`, and documents the reduced 39-country coverage in a dedicated `model2_coverage` table.
- Streamlit sidebar `st.sidebar.selectbox("Modelo activo", key="active_model_name")` switches all 4 dashboard tabs between Model 1 and Model 2, with `cached_bootstrap`/`cached_shap` now parameterized on `active_model_name` and a D-08 reduced-coverage caption rendered only for Model 2.

---
