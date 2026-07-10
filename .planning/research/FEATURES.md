# Feature Research

**Domain:** Applied econometrics + ML academic thesis (panel data, counterfactual simulation, interpretability, dashboard) — evaluated by a Bachelor's tribunal (UCMA)
**Researched:** 2026-07-10
**Confidence:** MEDIUM (cross-checked web sources on econometric/ML/reproducibility best practice; no domain-specific "TFB rubric" document was available to fetch, so tribunal-expectation claims are generalized from academic-thesis-evaluation and applied-econometrics literature, not this specific program's rubric)

## Feature Landscape

### Table Stakes (Tribunal Expects These)

Features an econometrics + ML tribunal assumes exist. Missing these reads as a methodological gap, not just a missing "nice-to-have," and is the kind of thing examiners flag in defense.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Documented, versioned local data snapshot (raw + processed) | Already required by PROJECT.md; also the top defense against "API changed/data unavailable" during evaluation | LOW | Raw data must be immutable — never edit extracts in place; keep `data/raw/` vs `data/processed/` separation |
| Documented coverage filtering & exclusions (≥70% years/indicator) | PROJECT.md risk mitigation; tribunals penalize silent sample selection more than a smaller-but-honest sample | LOW | List excluded countries + reason in an appendix table, not just in prose |
| Missing-data pattern documented explicitly (MNAR risk) | UN/World Bank-style indicators are **not missing at random** — missingness correlates with development level, which is exactly the confound this thesis is about. Students commonly forget to address this. | LOW–MEDIUM | Add a short missingness-by-region/income-group table or heatmap; state whether exclusion (current plan) could bias results toward better-reporting (typically wealthier) countries |
| EDA with descriptive stats + visual relationship exploration (global/regional/typology) | Already required; standard first analytical chapter in any panel-data thesis | LOW | |
| Panel model with country fixed effects (PanelOLS), not pooled OLS | Already required; mitigates the reverse-causality risk explicitly named in PROJECT.md | MEDIUM | `linearmodels.PanelOLS` |
| Baseline model comparison (pooled OLS vs. RE vs. FE) to justify FE choice | Examiners expect to see *why* FE was chosen, not just that it was used | LOW | One comparison table; Hausman test result justifies the choice |
| Hausman test (FE vs. RE) | Standard, near-universal diagnostic in panel econometrics theses; its absence is a red flag to any econometrics-literate reviewer | LOW | `linearmodels` supports this natively |
| Robust standard errors appropriate to a macro cross-country panel (clustered by country, or Driscoll-Kraay if cross-sectional dependence is present) | Naive/default SEs understate uncertainty when errors are heteroskedastic, serially correlated, or cross-sectionally dependent (common shocks like global recessions hit many countries' GDP and water stress at once) | MEDIUM | Test with Pesaran CD test or similar; switch to Driscoll-Kraay if CSD detected — `linearmodels` supports `cov_type='kernel'`/DK-style estimators |
| Multicollinearity check (VIF) among control variables | Prevents "high R² but garbage coefficients" — a classic examiner catch | LOW | |
| Robustness checks: alternate specification(s) (e.g., lagged independent variable, alternate control set, subsample by income group/region) | Standard expectation in applied econometrics; shows the headline result isn't an artifact of one specification | MEDIUM | At minimum 1–2 alternate specs reported side-by-side with the main model |
| Explicit "Limitations / Threats to Validity" section addressing reverse causality & endogeneity | PROJECT.md already names this risk; tribunals specifically probe for self-awareness of causal-inference limits in a thesis that uses observational cross-country data | LOW | This is a writing deliverable, not code — but must be grounded in what the model diagnostics actually showed |
| Counterfactual simulation with confidence intervals (bootstrap), explicitly framed as sensitivity analysis, not causal prediction | Already required; matches best practice (bootstrap or parametric-bootstrap-of-coefficients to get 95% CI bands) | MEDIUM | Standard approach: redraw coefficients from their asymptotic sampling distribution (or nonparametric bootstrap of the panel), recompute the counterfactual outcome per draw, report 2.5/97.5 percentiles |
| Interpretability (SHAP) with correct caveats | Already required; must explicitly state SHAP shows association given the trained model, not causation — and flag the known SHAP pitfall with correlated regressors (water stress can correlate with other socioeconomic controls) | MEDIUM | Prefer TreeSHAP if a tree-based ML model is used alongside PanelOLS; check feature correlation matrix before trusting SHAP attribution splits |
| Interactive local dashboard for the oral defense demo | Already required and scoped as local-only | MEDIUM | Streamlit + Plotly choropleth; must run reliably offline/live in front of the tribunal — no dependency on external APIs at demo time |
| Reproducibility artifacts: pinned deps (`requirements.lock.txt`), fixed random seeds, documented run steps | Already required; increasingly treated as a first-class thesis-quality criterion in data science programs, not just "good practice" | LOW | Set `random_state`/seed in every stochastic step (bootstrap, any ML model, train/test split) — must be set in multiple places to be truly reproducible |
| Model 1 (GDP growth) fully executed end-to-end | Explicit priority in PROJECT.md given time constraints | HIGH | This is the deliverable the whole pipeline exists to produce |

### Differentiators (What Would Make the Thesis Stand Out)

Not required for a passing grade, but each aligns with the Core Value ("reproducible, defensible pipeline") and adds depth an examiner will notice and reward, without contradicting Out of Scope.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Model 2 (agricultural productivity, indicator 2.3.1) fully executed, not just attempted | PROJECT.md already scopes this as "if progress allows" — treat as the primary stretch goal, reusing Model 1's methodology | MEDIUM–HIGH | Depends entirely on Model 1 being solid first; document data-coverage limitation if pursued with a reduced country set |
| Multiple counterfactual scenarios with a sensitivity/tornado-style chart (e.g., water stress −10%, −20%, −30%) instead of one point scenario | Shows the CI-bounded simulation isn't a single lucky number; demonstrates deeper sensitivity-analysis thinking, which is explicitly the safe framing PROJECT.md already chose | MEDIUM | Builds directly on the required bootstrap-CI simulation feature |
| Regional / income-group heterogeneity analysis (interaction terms or subgroup FE models) | Adds analytical depth ("does the water-stress effect differ for low- vs high-income countries?") without violating the "no individual-country predictions" exclusion — this is subgroup analysis at the panel level, not per-country prediction | MEDIUM | Natural extension of the EDA regional breakdown already planned |
| Complementary SHAP + partial dependence / ALE plots | Mitigates the known SHAP-with-correlated-features pitfall found in research; ALE is specifically recommended in the literature as the fallback when regressors are correlated | MEDIUM | Directly addresses a documented weakness of SHAP-only interpretability |
| Automated data-quality/coverage report (missingness heatmap by country × indicator × year) | Turns the "documented exclusions" table stake into a visual, reusable diagnostic artifact — useful both in the memoria and as a dashboard tab | LOW–MEDIUM | Natural byproduct of the missing-data documentation table stake |
| Polished dashboard UX: time-series animation over 2000–2022, multi-indicator side-by-side comparison, cached data loading (`st.cache_data`) for responsiveness during the live demo | Directly supports the oral defense (30% of grade); a laggy or confusing dashboard during a live 10–15 min defense is a real risk | MEDIUM | Performance matters most: cache heavy choropleth/geojson rendering so the live demo doesn't stall |
| ML model (e.g., Random Forest/Gradient Boosting) as a complementary predictive benchmark alongside the econometric panel model | `scikit-learn` is already in the stack; comparing an interpretable econometric model against a flexible ML model strengthens the "ML" half of a data-science (not pure-economics) thesis and gives SHAP a natural home | MEDIUM–HIGH | Frame clearly as a complementary predictive/interpretability exercise, not a competing causal claim — keep the causal story anchored in PanelOLS |

### Anti-Features (Tempting But Explicitly Out of Scope)

These map directly onto the "Alcance negativo" already agreed in PROJECT.md. Listed here so the roadmap doesn't accidentally reintroduce them as "obvious" additions.

| Feature | Why It Seems Appealing | Why Problematic (per PROJECT.md scope) | Alternative (already chosen) |
|---------|------------------------|------------------------------------------|-------------------------------|
| Real-time/streaming ingestion from the UN SDG API | Feels "more rigorous/live" and shows technical range | Explicit Out of Scope; adds operational fragility right before the defense demo, contradicts the reproducibility goal of a frozen, versioned dataset | Batch ingestion into a versioned local snapshot, done once (or per phase) and locked |
| Subnational / river-basin-level granularity | Would make water-stress modeling more geographically precise | Explicit Out of Scope; UN SDG API + scope is country-level; would require new data sources and break the "single traceable data source" constraint | Country-level panel only |
| Individual country-specific predictive models or per-country point forecasts | Tempting once a dashboard shows country-level choropleths — easy to overreach into "predicting country X's GDP" | Explicit Out of Scope; the model is global/panel and PROJECT.md is explicit that results must be interpreted in that panel context, not as country-specific forecasts | Dashboard shows panel-model outputs and counterfactual simulation results *per country*, but never a country-specific fitted model or forecast |
| Modeling second-order effects (migration, conflict, public health) | Water stress plausibly drives these; would look "more comprehensive" | Explicit Out of Scope; scope is economic outcomes (GDP, agricultural productivity) only, per the official proposal | Mention as future work / discussion in the memoria conclusions, not modeled |
| Deploying the dashboard online (Streamlit Community Cloud, etc.) | Would look more "shippable"/professional | Explicit Out of Scope; alumno's stated decision — local-only for the defense demo | Local Streamlit run, screen-shared/live during the oral defense |
| Formal causal-identification machinery (instrumental variables, difference-in-differences, synthetic control) to "prove" causality | Tempting once reviewers raise the reverse-causality concern — feels like the "correct" econometric answer | No valid instrument has been identified in the proposal; PROJECT.md explicitly reframes the counterfactual as a **sensitivity simulation, not causal prediction** — overreaching into causal claims without a credible identification strategy is a bigger tribunal risk than not attempting it | Fixed-effects panel model to control observed+time-invariant confounding, explicit "not causal" framing, and CI-bounded sensitivity simulation |
| AutoML / extensive hyperparameter search across many candidate ML models | Looks thorough, demonstrates ML breadth | Adds significant time cost against a fixed academic deadline for a benefit that doesn't serve the thesis's causal/interpretability goals; risks turning the "ML" component into a black-box tuning exercise that undermines the interpretability narrative | One well-chosen, well-tuned interpretable ML benchmark (e.g., Random Forest) is enough; time saved goes to Model 2 and robustness checks instead |
| A general-purpose reusable ODS/SDG data-ingestion platform (arbitrary indicators, arbitrary countries, pluggable sources) | Feels like better engineering / more reusable code | Scope is a fixed, small set of named indicators for one thesis; over-engineering a "platform" burns time that should go to modeling, diagnostics, and the memoria | A small, purpose-built ingestion script for the exact indicators in scope, documented and versioned |

## Feature Dependencies

```
Data ingestion (UN SDG API, batch)
    └──requires──> Versioned local snapshot / SQLite storage
                       └──requires──> Coverage filtering (70% rule) + missing-data documentation
                                          └──requires──> Cleaning / feature engineering
                                                             └──requires──> EDA
                                                                                └──requires──> Model 1 (PanelOLS, FE) — pooled/RE baseline comparison
                                                                                                   └──requires──> Diagnostics (Hausman, VIF, CSD test → robust/DK SEs)
                                                                                                                      └──requires──> Robustness checks (alt. specs, subsamples)
                                                                                                                      └──requires──> SHAP interpretability
                                                                                                                      └──requires──> Counterfactual simulation + bootstrap CIs
                                                                                                                                         └──requires──> Dashboard (visualizes model + simulation outputs)

Model 1 (methodology) ──enables──> Model 2 (agricultural productivity, extension)

Missing-data documentation ──enhances──> Automated coverage/missingness report (differentiator)
Regional EDA breakdown ──enhances──> Regional/income-group heterogeneity analysis (differentiator)
SHAP interpretability ──enhances──> SHAP + ALE/partial-dependence complement (differentiator, mitigates SHAP correlated-feature pitfall)
Counterfactual simulation (single scenario) ──enhances──> Multi-scenario sensitivity chart (differentiator)
Base dashboard ──enhances──> Polished dashboard UX (caching, animation, multi-indicator) (differentiator)

Formal causal-ID methods (IV/DiD/synthetic control) ──conflicts──> "Sensitivity simulation, not causal prediction" framing (already the chosen safe scope)
Real-time API ingestion ──conflicts──> Versioned, reproducible local snapshot (already the chosen constraint)
```

### Dependency Notes

- **Everything downstream requires the versioned local snapshot first:** because the sole data source is the UN SDG API and reproducibility is a hard constraint, the ingestion → versioned storage step must land before any modeling work — this is also the single point of failure PROJECT.md already identified (API changes).
- **Diagnostics (Hausman, VIF, cross-sectional-dependence test) must precede robustness checks and the final reported model:** you cannot credibly write "robust standard errors" in the memoria without first testing *which* violation (heteroskedasticity, serial correlation, cross-sectional dependence) is present — the choice of clustered vs. Driscoll-Kraay SEs depends on that test.
- **Counterfactual simulation requires a diagnosed, robustness-checked Model 1, not a raw first fit:** bootstrapping CIs around a mis-specified or non-robust model just produces confidently wrong intervals — this ordering matters for the roadmap.
- **Model 2 enables from Model 1's methodology, not from scratch:** PROJECT.md already frames Model 2 as an extension: reuse the FE/diagnostics/robustness pipeline rather than rebuilding it.
- **Formal causal-identification methods conflict with the chosen scope:** attempting IV/DiD/synthetic control without a credible instrument would contradict PROJECT.md's explicit "sensitivity simulation, not causal prediction" framing and should not be pulled into the roadmap even as a stretch goal.

## MVP Definition

Reframed for a fixed-deadline academic thesis: "v1" = what must exist for a passable, defensible Entrega 3 submission; "v1.x" = stretch value if time allows (matches PROJECT.md's own risk mitigation ordering); "v2+" = explicitly out of scope for this thesis, future-work material only.

### Launch With (Core Deliverable — must exist for a passing defense)

- [ ] Versioned local data snapshot + SQLite panel dataset — without this nothing else is reproducible or gradeable
- [ ] Documented coverage filtering (70% rule) and missing-data pattern discussion — examiners specifically probe silent sample bias
- [ ] EDA (global/regional/typology) — required first analytical chapter
- [ ] Model 1 (PanelOLS, FE) with pooled/RE baseline comparison and Hausman test — the core econometric deliverable
- [ ] Diagnostics + robust/appropriate SEs (heteroskedasticity, serial correlation, cross-sectional dependence) — non-negotiable rigor signal
- [ ] At least one robustness check (alternate spec or subsample) — shows the result isn't fragile
- [ ] Counterfactual simulation with bootstrap confidence intervals, explicitly framed as sensitivity analysis — already required and de-risked in PROJECT.md
- [ ] SHAP interpretability with correlated-feature caveat stated — already required
- [ ] Local interactive dashboard (Streamlit + Plotly choropleth) functional for the live defense demo
- [ ] Reproducibility artifacts (`requirements.lock.txt`, fixed seeds, run instructions)
- [ ] "Limitations / Threats to Validity" section addressing reverse causality — directly answers the risk PROJECT.md already flagged

### Add After Validation (Stretch — pursue once Model 1 pipeline above is solid)

- [ ] Model 2 (agricultural productivity, indicator 2.3.1) — trigger: Model 1 fully diagnosed and robustness-checked, time remains before Entrega 3
- [ ] Multi-scenario counterfactual sensitivity chart — trigger: base single-scenario simulation is working and CI-validated
- [ ] Regional/income-group heterogeneity analysis — trigger: base FE model results are stable
- [ ] Automated missingness/coverage visual report — trigger: base coverage-filtering documentation exists in table form already

### Future Consideration (Explicitly Out of Scope for This Thesis)

- [ ] Formal causal identification (IV/DiD/synthetic control) — defer indefinitely: no credible instrument identified, contradicts chosen "sensitivity simulation" framing
- [ ] Online dashboard deployment — defer: explicit alumno decision, local-only demo is sufficient and lower-risk
- [ ] Subnational/basin-level modeling, real-time ingestion, second-order effects (migration/conflict/health), general-purpose ingestion platform — all explicit Out of Scope in PROJECT.md; revisit only in a future, separate body of work (e.g., a Master's thesis), not this TFB

## Feature Prioritization Matrix

| Feature | Tribunal Value | Implementation Cost | Priority |
|---------|-----------------|----------------------|----------|
| Versioned data snapshot + SQLite panel | HIGH | LOW | P1 |
| Coverage filtering + missing-data documentation | HIGH | LOW | P1 |
| Model 1 (PanelOLS FE) + baseline comparison | HIGH | MEDIUM | P1 |
| Diagnostics (Hausman, VIF, CSD test) + robust SEs | HIGH | MEDIUM | P1 |
| Robustness checks (alt. spec/subsample) | HIGH | MEDIUM | P1 |
| Counterfactual simulation + bootstrap CIs | HIGH | MEDIUM | P1 |
| SHAP interpretability + caveats | MEDIUM–HIGH | MEDIUM | P1 |
| Local dashboard (base) | HIGH (defense demo) | MEDIUM | P1 |
| Reproducibility artifacts (pinned deps, seeds) | HIGH | LOW | P1 |
| Limitations/threats-to-validity write-up | HIGH | LOW | P1 |
| Model 2 (agricultural productivity) | MEDIUM | HIGH | P2 |
| Multi-scenario sensitivity chart | MEDIUM | LOW–MEDIUM | P2 |
| Regional/income-group heterogeneity analysis | MEDIUM | MEDIUM | P2 |
| SHAP + ALE/partial-dependence complement | MEDIUM | MEDIUM | P2 |
| Automated missingness/coverage report | LOW–MEDIUM | LOW | P3 |
| Polished dashboard UX (animation, caching, multi-indicator) | MEDIUM (demo polish) | MEDIUM | P3 |
| ML benchmark model (Random Forest/GB) alongside PanelOLS | MEDIUM | MEDIUM–HIGH | P3 |
| Formal causal identification (IV/DiD/synthetic control) | LOW (conflicts with scope) | HIGH | Do not build |
| Online dashboard deployment | LOW (conflicts with scope) | MEDIUM | Do not build |

**Priority key:**
- P1: Must have for a passing, defensible thesis
- P2: Should have, pursue if Model 1 pipeline is solid and time remains (matches PROJECT.md's own "Modelo 2 if progress allows" logic)
- P3: Nice to have, pursue only after all P1/P2 items and only if it strengthens the oral defense
- Do not build: contradicts PROJECT.md's explicit Out of Scope / chosen framing

## What Tribunals Commonly Expect That Students Forget

Synthesized from academic-thesis-rubric research and applied-econometrics best-practice/pitfall research; cross-referenced against this project's already-identified risks in PROJECT.md.

1. **Justifying the modeling choice, not just using it.** A pooled-OLS-vs-RE-vs-FE comparison table + Hausman test result is expected evidence that FE was the *right* choice, not an assumed one.
2. **Testing which SE-robustness issue is actually present**, rather than reflexively reporting "robust standard errors" without diagnosing heteroskedasticity, serial correlation, or cross-sectional dependence first. For cross-country macro panels, cross-sectional dependence (common global shocks) is easy to miss and is exactly the kind of thing an econometrics-literate examiner will probe.
3. **Being explicit that missingness in UN/World Bank-style indicators is not random** — coverage-based country exclusion is defensible, but only if the thesis states the resulting sample skews toward better-reporting (often wealthier) countries and discusses the implication for external validity.
4. **Distinguishing "sensitivity analysis" from "prediction" consistently** in every chapter (not just the counterfactual section) — students often relapse into causal language ("this shows water stress reduces GDP") in the discussion/conclusions even after correctly hedging the methodology section. This is the single biggest self-inflicted credibility risk given PROJECT.md's already-flagged reverse-causality risk.
5. **Not over-trusting SHAP.** SHAP importance rankings can be distorted or misattributed when features are correlated (a real risk here, since water-stress indicators and socioeconomic controls plausibly correlate). Examiners in applied ML increasingly know this; stating the caveat and checking the correlation matrix first heads it off.
6. **A dedicated "Limitations" section**, not limitations scattered as asides — grading rubrics for bachelor theses specifically reward structure and explicit self-critique, not just results.
7. **Reproducibility as an evaluable artifact, not just a claim** — pinned dependency versions and fixed seeds are good, but the memoria/annex should also state *how* a grader could re-run the pipeline (even if not literally re-run during grading, defensible reproducibility documentation is increasingly treated as a quality signal in data-science programs).
8. **Dashboard reliability during the live defense** — a dashboard that is analytically correct but slow/fragile during the 10–15 minute oral defense actively costs points on the 30% defense weighting; caching and offline-readiness are part of "table stakes," not polish.

## Sources

- [What are the most common mistakes students make when learning econometrics? (LinkedIn)](https://www.linkedin.com/advice/3/what-most-common-mistakes-students-make-when-learning-jtslf)
- [10 Common Mistakes in Applied Econometrics (dummies)](https://www.dummies.com/article/business-careers-money/business/economics/10-common-mistakes-in-applied-econometrics-156429/)
- [Econometric Errors in an Applied Economics Article (ResearchGate)](https://www.researchgate.net/publication/227352504_Econometric_Errors_in_an_Applied_Economics_Article)
- [10.5 The Fixed Effects Regression Assumptions and Standard Errors for Fixed Effects Regression — Introduction to Econometrics with R](https://www.econometrics-with-r.org/10.5-tferaaseffer.html)
- [Fixed-effects and Random-effects — Panel Data Using R, Princeton University Library Guide](https://libguides.princeton.edu/R-Panel)
- [Robust Standard Errors for Panel Regressions with Cross-Sectional Dependence (Hoechle, Stata Journal / IDEAS)](https://ideas.repec.org/a/tsj/stataj/v7y2007i3p281-312.html)
- [Driscoll-Kraay Standard Errors — PanelBox Documentation](https://panelbox.readthedocs.io/en/latest/inference/driscoll-kraay/)
- [Panel Data: Cross-Sectional Dependence and Driscoll-Kraay robust errors (Statalist discussion)](https://www.statalist.org/forums/forum/general-stata-discussion/general/1550660-panel-data-cross-sectional-dependence-and-driscoll-kraay-robust-errors)
- [Endogeneity bias and growth regressions (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0164070416300854)
- [Lagged Explanatory Variables and the Estimation of Causal Effects (Bellemare et al.)](http://marcfbellemare.com/wordpress/wp-content/uploads/2017/04/Bellemare-et-al.-JoP-2017.pdf)
- [Interpretable ML 3: What nobody tells you about SHAP values (Medium)](https://bury-thomas.medium.com/interpretability-ml-3-what-nobody-tells-you-about-shap-values-8295f0db3f9d)
- [Explaining individual predictions when features are dependent: More accurate approximations to Shapley values (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0004370221000539)
- [Practical guide to SHAP analysis (Clinical and Translational Science, Wiley)](https://ascpt.onlinelibrary.wiley.com/doi/10.1111/cts.70056)
- [Bootstrap confidence intervals: A comparative simulation study (arXiv)](https://arxiv.org/html/2404.12967v1)
- [10. Reproducible Research — Kempner Institute Computing Handbook](https://handbook.eng.kempnerinstitute.harvard.edu/s2_swe_for_research/reproducible_research.html)
- [Reproducibility in Data Science (Medium/TDS)](https://medium.com/data-science/reproducibility-in-data-science-c2ac9e689339)
- [Versioning, Provenance, and Reproducibility in Production Machine Learning (Christian Kästner, Medium)](https://ckaestne.medium.com/versioning-provenance-and-reproducibility-in-production-machine-learning-355c48665005)
- [Reproducible data analysis — Stanford Psychology Guide to Doing Open Science](https://poldrack.github.io/psych-open-science-guide/4_reproducibleanalysis.html)
- [Examiners' use of rubric criteria for grading bachelor theses (Assessment & Evaluation in Higher Education)](https://www.tandfonline.com/doi/full/10.1080/02602938.2020.1864287)
- [Validation of rubric-based evaluation for bachelor's theses in a food science and technology degree (Journal of Food Science)](https://ift.onlinelibrary.wiley.com/doi/10.1111/1750-3841.17044)
- [What methods are used to calculate aggregates for groups of countries? — World Bank Data Help Desk](https://datahelpdesk.worldbank.org/knowledgebase/articles/198549-what-methods-are-used-to-calculate-aggregates-for)
- [Step 3: Imputation of missing data — European Commission, Composite Indicators Toolkit](https://knowledge4policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-3-imputation-missing-data_en)
- [Streamlit and Plotly: Interactive Data Visualization Made Easy (Kanaries docs)](https://docs.kanaries.net/topics/Streamlit/streamlit-plotly)
- [Plotly Express Choropleth Map Streamlit Optimization (Streamlit Community discussion)](https://discuss.streamlit.io/t/plotly-expess-choropleth-map-streamlit-optimization/63194)
- `.planning/PROJECT.md` (official proposal scope, risks, and constraints — primary source for Out of Scope / anti-features cross-check)

---
*Feature research for: Applied econometrics + ML academic thesis (water stress / economic outcomes)*
*Researched: 2026-07-10*
