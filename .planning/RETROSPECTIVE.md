# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-07-15
**Phases:** 6 | **Plans:** 21 | **Tasks:** 56

### What Was Built
- Reproducible ingestion of 5 UN SDG indicators (150+ countries, 2000–2022) into a versioned, checksummed SQLite panel with a manifest of provenance (Phase 1)
- A coverage-filtered, idempotent país×año panel with a numbers-grounded MNAR discussion and multi-level VIF/correlation EDA (Phase 2)
- Model 1: two-way fixed-effects PanelOLS for GDP-per-capita growth with pooled/RE/FE comparison, Hausman test, Pesaran-CD-driven SE choice, robustness check, and a serialized artifact (Phase 3)
- Bootstrap counterfactual simulation and a SHAP/VIF/PDP interpretability stack, proven bit-identical across independent runs (Phase 4)
- A local Streamlit/Plotly dashboard consuming only pre-computed artifacts, rehearsed cold-cache on the presentation machine (2.01s, target <5s) with pre-rendered Plan B screenshots (Phase 5)
- Model 2 (stretch): agricultural productivity (indicator 2.3.1) reusing the entire Model 1 methodology and shared modules unmodified, with documented reduced country coverage and a dashboard model switcher (Phase 6)

### What Worked
- Designing `panel_base.py`, `simulate.py`, and `interpret.py` as dependent-variable-agnostic from Phase 3/4 onward meant Phase 6's Model 2 called them **unmodified** — zero duplication, zero regression risk to Model 1's already-verified numbers.
- Hand-computable test fixtures for manually-implemented statistical tests (Hausman, Pesaran CD — neither provided by statsmodels/linearmodels) gave real confidence in econometric correctness, not just "it runs."
- Serializing fitted artifacts (`model1_gdp.pkl`, `rf_shap_model.pkl`) and having the dashboard load them instead of refitting live was the single biggest performance lever (cold-start dropped from 10.59s to 2.01s in Phase 5 once the RandomForest stopped being refit per session).
- Code review before each phase close consistently caught real Critical bugs (Phase 5: scenario-plot axis + SHAP plot overlap; Phase 6: dashboard bootstrap resampling from the wrong country population for Model 2) — none of these were caught by the existing unit tests.

### What Was Inefficient
- Phase 04-03 stalled ~9h overnight on a broken self-monitoring assumption in the execution loop (it echoed a placeholder string instead of tracking a real background process) rather than any actual code defect — caught only by noticing unchanged file timestamps the next session.
- Phase 05-05 (cold-cache rehearsal) took ~3h, far longer than any other plan, because it surfaced three separate live bugs (duplicate-element crash, unintended public network binding, live RandomForest refit) that only a rehearsal on the real presentation machine — not unit tests — could reveal.

### Patterns Established
- Shared econometric/ML modules are written parametrized on `dep_var`/`indep_vars` from their first version, so a second model (Phase 6) is a call-site, not a fork.
- All stochastic steps (bootstrap, RandomForest, any split) take an explicit seed and are verified bit-identical across two independent full runs before being considered done (REPRO-02).
- Dashboard tabs read exclusively from local `.pkl`/SQLite artifacts; nothing in `src/dashboard/` performs live model fitting or API calls — enforced with a static guard test, not just convention.

### Key Lessons
1. Plan reuse boundaries explicitly before writing the first model — panel_base.py's dependent-variable-agnostic design (decided in Phase 3) is why Phase 6 shipped in 3 plans instead of reimplementing the whole pipeline.
2. A scripted cold-cache rehearsal on the actual target machine is not optional polish for a live-demo deliverable — it found bugs (public network binding, live refit) invisible to any unit or integration test.
3. Code review immediately before phase/milestone close is worth keeping as a hard gate — it found a Critical correctness bug in both Phase 5 and Phase 6 that passing tests had missed.
4. When an executor appears stalled overnight with no error, check for a broken self-monitoring assumption (e.g., tracking a placeholder instead of the real process) before assuming the underlying task logic is broken.

### Cost Observations
- Model mix and per-session cost were not explicitly tracked this milestone.
- Sessions: not tracked at session granularity; 21 plans completed over 10 calendar days (2026-07-05 → 2026-07-15), 189 commits, ~18,657 LOC (`.py`+`.ipynb`).
- Notable: the two clear time sinks (Phase 04-03 overnight stall, Phase 05-05 rehearsal) were both caused by encountering real-world conditions (a monitoring bug, a physical presentation machine) rather than by the core statistical/ML logic — which shipped cleanly once specified.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | not tracked | 6 | Initial roadmap; established shared-module reuse pattern (panel_base.py) that paid off directly in Phase 6 |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|---------------------|
| v1.0 | not aggregated | not aggregated | PDP via sklearn only (PyALE never installed after SUS flag); interpret.py added zero new dependencies |

### Top Lessons (Verified Across Milestones)

1. Design shared modules parametrized for reuse before the second use case exists — validated once in v1.0 (Phase 3 → Phase 6); watch for repetition in future milestones.
