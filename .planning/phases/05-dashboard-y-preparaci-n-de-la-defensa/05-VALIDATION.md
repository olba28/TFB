---
phase: 5
slug: dashboard-y-preparaci-n-de-la-defensa
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-13
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (pinned, `requirements.lock.txt`), `pytest-cov` 7.1.0 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options] testpaths = ["tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/dashboard -x` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~10-15 seconds (fixture-based unit tests + `AppTest` headless render — NOT a full live `streamlit run` rehearsal, which is a separate manual gate for DASH-05) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/dashboard -x`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite green, plus the DASH-05 `checkpoint:human-verify` (cold-cache rehearsal + Plan B captures) completed with evidence
- **Max feedback latency:** 15 seconds (unit/AppTest tier); the DASH-05 rehearsal is a separate, slower, end-of-phase manual gate

---

## Per-Task Verification Map

*Task IDs are assigned by the planner (Step 8) and not yet known at research/validation-strategy time. Rows below map each phase requirement to its automated test — the planner must attach a real `{phase}-{plan}-{task}` ID to whichever task implements each behavior.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | DASH-01 | T-5-01 / V5 | Dashboard source contains no call to the UN SDG API client (`src/ingesta`) or any live HTTP request at render time — only `src/db.py::get_engine()` and local `.pkl` loads | unit (static) | `pytest tests/dashboard/test_no_live_api.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | DASH-02 | — / N/A | `data.py` loaders are wrapped in `st.cache_resource` (Engine, models) or `st.cache_data` (DataFrames/results) — verified by inspecting the decorator attributes, not by timing | unit | `pytest tests/dashboard/test_caching.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1+ | DASH-03 | — / N/A | Two independent choropleths render side by side with distinct `key=` selectors (`indicator_left`/`indicator_right`) — no `DuplicateWidgetID` | integration (`AppTest`) | `pytest tests/dashboard/test_app.py::test_side_by_side_comparison -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1+ | DASH-04 | — / N/A | `build_choropleth()` sets `animation_frame="year"` covering all 23 years (2000–2022) and an explicit `range_color` fixed to the indicator's global min/max | unit | `pytest tests/dashboard/test_plots.py::test_choropleth_has_all_years -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | last | DASH-05 | — / N/A | Cold-cache rehearsal on the actual presentation machine completes render in a demo-acceptable time, and Plan B screenshots/PDF exist for every tab with real data loaded | manual-only (requires physical rehearsal hardware, not automatable) | `checkpoint:human-verify` — rehearsal + visual inspection of captures in `figuras/plan_b/` | ❌ W0 (checklist, no test) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/dashboard/__init__.py`
- [ ] `tests/dashboard/conftest.py` — fixture of an in-memory/temp `panel.db` with minimal data (a handful of countries/years) plus toy `.pkl` model fixtures, so tests never depend on the full production artifacts
- [ ] `tests/dashboard/test_no_live_api.py` — covers DASH-01
- [ ] `tests/dashboard/test_caching.py` — covers DASH-02
- [ ] `tests/dashboard/test_app.py` — covers DASH-03 via `streamlit.testing.v1.AppTest`
- [ ] `tests/dashboard/test_plots.py` — covers DASH-04, pure `plots.py` functions testable without launching Streamlit
- [ ] Framework install: none — `pytest` already in `requirements.lock.txt`; `streamlit.testing.v1.AppTest` ships inside the already-pinned `streamlit` package, no new dependency

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Cold-cache first render completes in an acceptable time for a live demo (target: <5s) on the actual presentation machine | DASH-02, DASH-05 | Wall-clock timing on real hardware with a cold cache cannot be simulated by a unit test; the presentation machine may differ from the dev machine | Clear Streamlit's cache (`streamlit cache clear` or fresh process), run `streamlit run src/dashboard/app.py`, time the first full render (`time.perf_counter` logging already recommended in RESEARCH.md), document the result |
| Plan B screenshots/PDF are legible and cover all four tabs with real data | DASH-05 | Visual legibility and completeness of a rendered capture is a human judgment, not an automatable assertion | Open each generated capture in `figuras/plan_b/`, confirm all four tabs ("Mapa e indicadores", "Modelo 1", "Simulación", "Interpretabilidad (SHAP)") are represented with real (non-placeholder) data |
| Chrome/Chromium availability on the presentation machine, if Plan B capture is automated via `kaleido` | DASH-05 | Environment availability on hardware not yet accessible during planning/execution — RESEARCH.md flags this as an open question, confirmed only on the dev machine | During the DASH-05 rehearsal, confirm Chrome/Edge is present on the presentation machine before relying on `kaleido`; fall back to manual browser screenshot/"Print to PDF" if absent (no additional dependency needed) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
