"""Active-model registry for the Phase 5 dashboard (DASH-01, D-07).

Every dashboard tab that needs to know which fitted model / predictor set to
load does so by looking up :data:`ACTIVE_MODELS`, never by hardcoding a
``dep_var``/``pkl_path`` literal inline. This mirrors the parametric-reuse
philosophy already established by ``src/panel_base.py`` (D-05, Phase 3) and
``src/simulate.py``/``src/interpret.py`` (D-12, Phase 4): those modules make
every *function* dependent-variable-agnostic via explicit parameters; this
registry makes every dashboard *component* model-agnostic via a single
dict lookup instead.

Why this exists (D-07): Phase 6 adds Model 2 (productividad agrícola,
``dep_var="2.3.1"``) by appending one more entry to ``ACTIVE_MODELS`` -- it
never needs to restructure ``src/dashboard/app.py`` or any tab-rendering
code, because every tab already reads its ``dep_var``/``indep_var``/
``feature_vars``/``pkl_path`` from this registry rather than from literals
scattered through the app.

Every ``pkl_path`` value here MUST point only to a local, project-produced
artifact under ``data/modelos/`` (DASH-01) -- these are files serialized and
round-trip-verified by earlier phases (Phase 3: ``model1_gdp.pkl``; Phase 4:
``rf_shap_model.pkl``), never a network source and never a user upload. No
``st.file_uploader`` for ``.pkl`` is introduced anywhere in this phase (see
05-PLAN.md threat T-5-02).

This module is pure configuration -- it imports nothing from ``streamlit``
and must import cleanly under plain ``pytest`` with no Streamlit runtime.
"""

from __future__ import annotations

ACTIVE_MODELS: dict[str, dict[str, object]] = {
    "Modelo 1 (PIB per cápita)": {
        "dep_var": "8.1.1",
        "indep_var": "6.4.2",
        "feature_vars": [
            "6.4.2",
            "6.4.1",
            "8.2.1",
            "is_ldc",
            "is_lldc",
            "is_sids",
            "region",
        ],
        "pkl_path": "data/modelos/model1_gdp.pkl",
        "rf_shap_pkl_path": "data/modelos/rf_shap_model.pkl",
    },
    # Fase 6 (D-07): Modelo 2 (productividad agrícola), producido por
    # src/model2_agri.py (06-02-SUMMARY.md) -- misma metodología, mismos
    # feature_vars que Modelo 1, cobertura reducida a 39 países (D-01).
    "Modelo 2 (Productividad agrícola)": {
        "dep_var": "2.3.1",
        "indep_var": "6.4.2",
        "feature_vars": [
            "6.4.2",
            "6.4.1",
            "8.2.1",
            "is_ldc",
            "is_lldc",
            "is_sids",
            "region",
        ],
        "pkl_path": "data/modelos/model2_agri.pkl",
        "rf_shap_pkl_path": "data/modelos/rf_shap_model_m2.pkl",
    },
}

INDICATOR_LABELS: dict[str, str] = {
    "6.4.2": "Estrés hídrico (6.4.2)",
    "6.4.1": "Eficiencia del uso del agua (6.4.1)",
    "8.1.1": "Crecimiento del PIB per cápita (8.1.1)",
    "8.2.1": "Productividad laboral (8.2.1)",
    "2.3.1": "Productividad agrícola (2.3.1)",
}
