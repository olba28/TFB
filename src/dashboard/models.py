from __future__ import annotations

from typing import TypedDict


class ModelConfig(TypedDict):
    dep_var: str
    indep_var: str
    feature_vars: list[str]
    pkl_path: str
    rf_shap_pkl_path: str
    reduced_coverage: bool


ACTIVE_MODELS: dict[str, ModelConfig] = {
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
        "reduced_coverage": False,
    },
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
        "reduced_coverage": True,
    },
}

INDICATOR_LABELS: dict[str, str] = {
    "6.4.2": "Estrés hídrico (6.4.2)",
    "6.4.1": "Eficiencia del uso del agua (6.4.1)",
    "8.1.1": "Crecimiento del PIB per cápita (8.1.1)",
    "8.2.1": "Productividad laboral (8.2.1)",
    "2.3.1": "Productividad agrícola (2.3.1)",
}
