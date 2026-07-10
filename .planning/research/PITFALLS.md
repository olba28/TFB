# Pitfalls Research

**Domain:** Panel econometrics + ML interpretability + counterfactual simulation on UN SDG cross-country data, delivered as a Streamlit/Plotly dashboard
**Researched:** 2026-07-10
**Confidence:** MEDIUM-HIGH (econometric/ML pitfalls cross-checked against established literature — Nickell 1981, clustered-SE literature, SHAP interpretability literature; UN SDG API specifics are MEDIUM — verified against official docs but not against the live API response shapes, which should be spot-checked in Phase 1)

This document goes deeper than the risks already logged in `PROJECT.md` ("Análisis de riesgos"): coverage gaps, reverse causality, contrafactual validation difficulty, indicator 2.3.1 coverage, time constraints, API changes. Those are the *what*; this file is the *how it actually breaks* and *how to catch it early*.

## Critical Pitfalls

### Pitfall 1: UN SDG API rows are not automatically one-row-per-country-year

**What goes wrong:**
The SDG API (`unstats.un.org/SDGAPI/v1/sdg/Series/Data`) returns disaggregated observations, not a clean panel. A single indicator/country/year can have multiple rows differing by `[Nature]` (estimate type), `[Reporting Type]` (national vs. global), `[Units]`, and other dimension columns. Naively loading the JSON into a dataframe and grouping by `GeoAreaCode` + `TimePeriod` produces duplicate or conflicting values, and a naive `.groupby().mean()` or `.drop_duplicates()` silently averages or discards legitimate alternative estimates instead of picking the correct series.

**Why it happens:**
The API is designed for the SDG Data Explorer's flexible dimensional model, not for direct panel construction. There is no default "the one true value" field — dimension filtering is the caller's responsibility, and the API itself is explicitly published as a test/development service where "data might contain errors."

**How to avoid:**
For each indicator, inspect all distinct dimension combinations returned before deciding on a canonical filter (e.g., `Nature = "G"` for global/official estimate, single `Reporting Type`). Write an assertion in the ingestion code: after filtering, `(country, year)` must be unique per indicator — fail loudly if not.

**Warning signs:**
Row counts per indicator that are 2-4x the expected `countries × years`; duplicate `(country, year)` pairs surviving into the merged panel; indicator values that look like averages of two very different regimes.

**Phase to address:**
Ingesta (API extraction) — before any storage/EDA work begins.

---

### Pitfall 2: Regional aggregates and non-country entities leak into the country panel

**What goes wrong:**
The SDG API's `GeoAreaCode` list mixes actual countries with regional/income-group aggregates ("World", "Sub-Saharan Africa", "Landlocked Developing Countries", "OECD members", etc.) using the same M49 coding scheme. If ingestion pulls "all areas" without filtering to the UN M49 country/area list, these aggregates enter the panel as if they were countries — they don't exist in the GDP/agriculture indicators the same way, creating either silent NaN padding or, worse, phantom high-leverage observations that distort a fixed-effects regression with ~150-180 country dummies.

**Why it happens:**
M49 codes for regions and countries are structurally identical (both are numeric codes); nothing in the raw response flags "this is an aggregate" unless you cross-reference against the official M49 country classification.

**How to avoid:**
Build a canonical "valid countries" list once, at ingestion time, from the UN M49 standard classification (`unstats.un.org/unsd/methodology/m49/`) — not by string-matching names. Filter every indicator pull against this list before it touches the panel. Store the excluded/aggregate codes separately for transparency in the memoria.

**Warning signs:**
Country count in the raw panel exceeds ~200 (there are 193 UN member states + a handful of observer/territory entities with SDG data); entities named "World", "Africa", "High income" appearing in exploratory `value_counts()` of the country column.

**Phase to address:**
Ingesta / Almacenamiento (schema + validation) — enforce as a database constraint or ingestion-time check, not a downstream EDA filter.

---

### Pitfall 3: Country identifiers merged on name strings instead of M49/ISO3 codes

**What goes wrong:**
Joining the water-stress indicator, the GDP growth indicator, and the agricultural productivity indicator on country *name* (rather than a numeric code) causes silent row loss or misjoins: "Bolivia (Plurinational State of)" vs. "Bolivia", "Türkiye" vs. "Turkey", "Democratic Republic of the Congo" vs. "Congo, Dem. Rep." never match across sources, and some countries change ISO codes over time when their statistical-area classification changes (e.g., historical splits like Sudan/South Sudan). Because the SDG API itself is internally consistent on M49 codes, this pitfall mainly bites when cross-checking against a second source (World Bank WDI, FAO AQUASTAT) for validation — an activity this project should do (see Pitfall 4).

**Why it happens:**
Name-based joins "work" on the majority of countries, so the failure is invisible until someone notices a specific country missing from a chart.

**How to avoid:**
Build one canonical crosswalk table (M49 code ↔ ISO3 ↔ display name) at ingestion time and join everything — including any secondary validation source — on the numeric code, never on the name string.

**Warning signs:**
Country count drops after a merge without an explicit `how='outer'` diff being inspected; a handful of well-known countries (e.g., Türkiye, DRC, Bolivia, Micronesia) missing from a joined table when you know they report the indicator.

**Phase to address:**
Almacenamiento (BD schema) — the crosswalk table should be a first-class table in SQLite, not an ad-hoc dict in a notebook.

---

### Pitfall 4: Trusting the API without spot-checking known values (the "TEST API" trap)

**What goes wrong:**
The public SDG API is explicitly published as a test/development environment; values can contain errors or lag behind the official Global SDG Database. Building the entire pipeline on unverified extracted values risks defending a 60-80 page memoria with a data error a reviewer catches by comparing it to a well-known figure (e.g., "Jordan's water stress is one of the highest in the world — does your extracted 6.4.2 value reflect that?").

**Why it happens:**
There's no obvious signal in a successful HTTP 200 response that the value is wrong — a plausible-looking but incorrect number is indistinguishable from a correct one without cross-referencing.

**How to avoid:**
For 4-5 well-known "textbook" cases per indicator (e.g., Jordan/Kuwait/Egypt for water stress being extremely high; a handful of high-GDP-growth vs. stagnant economies), manually cross-check extracted values against a secondary published source (FAO AQUASTAT, World Bank WDI, UN SDG Global Database front-end) and document the cross-check in the memoria's data-quality section — this materially strengthens the methodology chapter for the defense.

**Warning signs:**
None from the pipeline itself — this requires an explicit manual QA step, not an automated check.

**Phase to address:**
Limpieza / EDA — add as an explicit "data validation" sub-step before the first model is trained.

---

### Pitfall 5: Two-way fixed effects omitted — country FE alone doesn't absorb global shocks

**What goes wrong:**
PROJECT.md already commits to fixed-effects panel regression to address reverse causality/heterogeneity — but entity (country) fixed effects alone only absorb *time-invariant* country characteristics. They do **not** absorb global shocks that hit GDP growth in a given year regardless of water stress: the 2008-09 financial crisis, the 2014-16 commodity price collapse, and especially COVID-19 in 2020 (a massive, near-universal GDP growth shock across the 2000-2022 window this project uses). Without year fixed effects, the water-stress coefficient can pick up spurious correlation with these common shocks (e.g., water-stressed regions that also happen to have commodity-dependent economies get double-hit in 2020, inflating the estimated effect of water stress).

**Why it happens:**
"Fixed effects" is often used loosely to mean "country FE" only; two-way FE (entity + time) requires explicitly adding year dummies/`TimeEffects=True` in `linearmodels.PanelOLS`, which is easy to skip if not deliberately planned.

**How to avoid:**
Use `PanelOLS(..., entity_effects=True, time_effects=True)` as the baseline specification, not country-FE-only. Report both specifications (country-FE-only vs. two-way FE) as a robustness comparison — this is a natural, low-effort robustness table for the results chapter.

**Warning signs:**
Water-stress coefficient changes sign or loses significance when year dummies are added; residual plots show a common dip across all countries in 2020/2009.

**Phase to address:**
Modelo 1 (regresión de panel) — should be the baseline specification from the start, not a later robustness addendum.

---

### Pitfall 6: Default (non-clustered) standard errors overstate significance

**What goes wrong:**
With country fixed effects, residuals are almost always serially correlated within a country (a shock to Jordan's economy in year t is correlated with year t+1). Standard (non-robust, non-clustered) standard errors from `PanelOLS` assume i.i.d. errors and will understate the true standard errors, making the water-stress coefficient look more statistically significant than it is — a classic and well-documented panel-data mistake in the applied econometrics literature (biases are "substantial" when SEs aren't clustered, per the clustered-SE literature this project's own reference, Wooldridge, covers).

**Why it happens:**
`linearmodels` and `statsmodels` default to classical or heteroskedasticity-robust SEs, not cluster-robust; clustering must be explicitly requested (`cov_type='clustered', cluster_entity=True`), and it's an easy step to skip when the model "runs fine" without it.

**How to avoid:**
Always fit with `cov_type='clustered', cluster_entity=True` (cluster by country) as the default reporting standard error, and mention this choice explicitly in the methodology chapter (this is exactly the kind of methodological rigor a tribunal evaluating CE3/CE4 competencies will check for).

**Warning signs:**
p-values that look "too good" (e.g., p < 0.001 on a modest-N panel); standard errors that shrink noticeably when cluster-robust is turned off vs. on — if they're similar, that itself is worth reporting.

**Phase to address:**
Modelo 1 — same phase as Pitfall 5, both are baseline-specification choices, not later fixes.

---

### Pitfall 7: Fixed effects control for reverse causality's *time-invariant* component only — not the dynamic component

**What goes wrong:**
PROJECT.md's stated mitigation for reverse causality ("poorer countries → more water stress, not necessarily the reverse") is fixed-effects panel regression. This is a real but *partial* fix: country FE removes confounding from characteristics that don't change over time (geography, baseline institutions), but it does **not** remove reverse causality that operates *within* a country over time — e.g., a bad economic year could itself reduce agricultural investment and worsen water-use efficiency the following year, still generating simultaneity bias in the water-stress coefficient. Overstating what FE buys you is a common thesis-defense vulnerability: a sharp examiner will ask "how does fixed effects solve reverse causality?" and "FE removes country-level confounders, not simultaneity" is the correct, precise answer.

**Why it happens:**
"Fixed effects controls for endogeneity" is a common simplification in applied papers that glosses over the entity-vs-time distinction in what's actually being identified.

**How to avoid:**
1. Use lagged predictors (water stress at t-1 predicting GDP growth at t) as the primary specification, not contemporaneous — this reduces (but doesn't eliminate) simultaneity and is defensible as "water stress measured before the outcome period."
2. Explicitly write a paragraph in the methodology/limitations chapter distinguishing "controls for time-invariant confounding" from "solves reverse causality" — this is the single most examinable methodological point in the whole thesis given it's flagged in the official proposal.
3. Consider a simple Granger-style robustness check: does lagged GDP growth predict *future* water stress? If yes, that's suggestive evidence of reverse dynamics worth discussing.

**Warning signs:**
None automatic — this is a conceptual/write-up risk, not a code bug. Catch it by explicitly drafting the limitations paragraph early, not the night before submission.

**Phase to address:**
Modelo 1 (specification choice: lagged predictor) and the write-up/discussion — flag for the memoria's "Limitaciones" section regardless of phase.

---

### Pitfall 8: Counterfactual simulation extrapolates beyond the data support

**What goes wrong:**
"What if water stress were reduced by X percentage points?" is only a meaningful sensitivity simulation for X values that keep the simulated country within (or close to) the range of water-stress values actually observed across the panel. If a highly water-stressed country (e.g., 150%+ extraction ratio) is simulated down to a level no country in the dataset has ever exhibited, the linear model is extrapolating into unobserved territory — the "effect" reported is an artifact of the fitted line's slope, not evidence about what would actually happen. This is the exact mechanism PROJECT.md's risk register gestures at ("difícil de validar empíricamente") but the concrete failure mode — extrapolation outside common support — is worth making explicit and testable.

**Why it happens:**
Linear panel models will happily produce a prediction for any input value; nothing stops the simulation code from feeding in a hypothetical that's far outside the training distribution, and the output looks numerically identical (a point estimate + CI) whether it's interpolation or extrapolation.

**How to avoid:**
Before running any counterfactual scenario, compute the empirical range (and ideally a density/percentile) of the water-stress variable across the whole panel (or, better, within the country's region/income-group peer set). Programmatically flag or clip scenarios that fall outside, say, the 1st-99th percentile of observed values, and explicitly label those results as "outside observed range — indicative only" wherever displayed (including the dashboard).

**Warning signs:**
Simulated water-stress values below 0% or implausibly close to 0% for countries that have never been near that level; counterfactual GDP effects that grow implausibly large as the hypothetical reduction increases (a sign the model is extrapolating linearly with no diminishing-returns structure).

**Phase to address:**
Simulación de escenarios contrafactuales.

---

### Pitfall 9: Confidence intervals on the counterfactual understate real uncertainty

**What goes wrong:**
The confidence interval PROJECT.md commits to reporting alongside the counterfactual (correctly, as a sensitivity-analysis framing rather than a causal claim) will, if computed only from the water-stress coefficient's own standard error, ignore several other sources of uncertainty: parameter uncertainty in the *other* covariates that are held fixed during the simulation, specification uncertainty (the CI looks different under the two-way FE vs. country-FE-only spec from Pitfall 5), and the fact that the linear functional form itself is an assumption, not a verified law. A narrow, precise-looking CI on a scenario that is fundamentally a "what-if" thought experiment can be *more* misleading to a tribunal than a wide one, because it signals false precision.

**Why it happens:**
Reporting the standard analytical CI from the regression coefficient is the path of least resistance and is what most textbook examples show; propagating full model uncertainty into a simulated scenario is a genuinely harder (but well-established) technique.

**How to avoid:**
Use a block/cluster bootstrap (resample countries with replacement, refit the panel model each time, recompute the simulated counterfactual each time) to build an empirical distribution of the simulated effect, rather than a single analytical CI. This is more defensible, is a natural showcase of technical competency (CE3/CE4), and is computationally cheap enough at this data scale (150-180 countries × 23 years) to run in minutes.

**Warning signs:**
CI width barely changes across different specifications; CI is symmetric and suspiciously narrow relative to the magnitude of the point estimate.

**Phase to address:**
Simulación de escenarios contrafactuales.

---

### Pitfall 10: SHAP values on correlated regressors misrepresent water stress's "true" importance

**What goes wrong:**
Water stress is very likely correlated with other regressors in the model — GDP per capita level (richer countries often have more water infrastructure and thus different exposure), regional dummies/fixed effects, and possibly the water-use-efficiency-by-sector control variable itself. SHAP's Shapley-value decomposition splits credit among correlated features in a way that can make water stress look artificially *less* important than it "should," or attribute its effect to a correlated proxy instead — directly undermining the thesis's central claim if the analysis isn't checked. This is a well-documented, actively researched failure mode of SHAP (and Shapley-value-based attribution generally), not a project-specific edge case.

**Why it happens:**
SHAP computes marginal contributions via feature coalitions; with correlated inputs, "coalitions" that swap one correlated feature for another produce similar predictions, so credit gets diffused rather than assigned to the "true" driver.

**How to avoid:**
1. Compute and report a correlation matrix / VIF (variance inflation factor) for the model's regressors *before* presenting SHAP results, so any diffusion is visible and explainable.
2. If water stress correlates strongly (|r| > ~0.5-0.6) with another regressor, consider grouping them for SHAP reporting purposes, or report SHAP alongside the raw regression coefficient (which is a more standard, less coalition-sensitive measure of "importance" in a linear model) rather than relying on SHAP alone.
3. Never phrase SHAP output as "water stress causes X% of GDP variation" in the memoria — SHAP explains the *fitted model's* predictions, not the causal data-generating process. Use language like "the model attributes an average marginal contribution of..." consistently.

**Warning signs:**
Water stress has low SHAP importance despite the regression coefficient being large and significant, or vice versa — a mismatch between SHAP ranking and coefficient significance is itself a signal to investigate correlation structure, not to simply report the discrepancy.

**Phase to address:**
Análisis de interpretabilidad (SHAP) — and the correlation/VIF check should actually happen earlier, during EDA, so it's available context before SHAP is even run.

---

### Pitfall 11: Wrong SHAP explainer / expensive KernelExplainer on the full panel

**What goes wrong:**
`shap` is in `requirements.txt` alongside `scikit-learn`, suggesting SHAP may be applied to both the linear panel model and possibly a comparison ML model (e.g., random forest). Each model type needs a matched explainer: `LinearExplainer` for the linear model, `TreeExplainer` for tree-based models. Defaulting to the general-purpose `KernelExplainer` (which works on any model but is a slow, sampling-based approximation) on the full merged panel (~150-180 countries × up to 23 years × several features) can take a very long time to compute and, worse, introduce approximation noise that's mistaken for a genuine finding.

**Why it happens:**
`KernelExplainer` is the most commonly copy-pasted SHAP example online because it works on any `predict` function without needing to know the model internals — it's the path of least resistance, not the correct choice.

**How to avoid:**
Match the explainer to the model type explicitly (`LinearExplainer`/`TreeExplainer`), and if `KernelExplainer` is unavoidable for some model, use a small representative background sample (e.g., k-means-summarized background of ~50-100 rows via `shap.sample` or `shap.kmeans`) rather than the full dataset, and compute SHAP values only for a representative subset of country-years for exploratory work, running the full panel once for final results.

**Warning signs:**
SHAP computation taking many minutes to hours; SHAP values that change noticeably between two runs with the same data (a sign of sampling noise from too-small a background/nsamples setting).

**Phase to address:**
Análisis de interpretabilidad (SHAP).

---

### Pitfall 12: Unbalanced panel shrinks silently when merging indicators

**What goes wrong:**
Water stress (6.4.2), GDP growth, and agricultural productivity (2.3.1) each have different country/year coverage. A default inner join across all three to build "the panel" can silently drop far more countries/years than expected — and because pandas merges don't warn on row loss, this can go unnoticed until someone asks "why does the model only have 60 countries?" late in the process. This compounds with the already-planned 70%-coverage filter (PROJECT.md) — the *order* of filtering vs. merging matters and changes which countries survive.

**Why it happens:**
`pd.merge(..., how='inner')` is the default mental model for "combine these datasets," and its silent row-dropping behavior is invisible without an explicit before/after row-count and country-count check.

**How to avoid:**
After every merge step, log `(n_rows, n_countries, n_years)` and compare to the pre-merge counts. Decide and document explicitly whether the 70%-coverage filter is applied per-indicator (before merging) or on the merged panel (after) — these give different results, and the choice should be a deliberate, stated methodological decision, not an accident of merge order.

**Warning signs:**
Final panel country count far below the ~150-180 expected from the proposal; large, unexplained jumps in country count between EDA notebook cells.

**Phase to address:**
Limpieza / feature engineering (panel construction) — the coverage-filter logic from PROJECT.md's mitigation should live here as an explicit, logged, and testable function.

---

### Pitfall 13: Data leakage in any ML train/test split via random row-wise splitting

**What goes wrong:**
If a scikit-learn model is used anywhere (comparison model, robustness check, or feature importance benchmark against SHAP), a random row-wise train/test split on panel data leaks information: rows from the same country appear in both train and test (the model "sees" the country's fixed characteristics during training and just interpolates for test years), producing artificially good validation metrics that don't reflect genuine predictive/generalization performance.

**Why it happens:**
`train_test_split(df, test_size=0.2)` is the default scikit-learn pattern taught everywhere and works fine for i.i.d. data, but panel/longitudinal data violates the i.i.d. assumption it depends on.

**How to avoid:**
Use a structured split appropriate to the research question: leave-one-country-out (or k-fold by country) if testing generalization across countries, or a time-based split (train on 2000-2016, test on 2017-2022) if testing forecast-style generalization. Choose based on what claim the ML comparison is meant to support, and state the choice explicitly.

**Warning signs:**
Suspiciously high R²/accuracy on a held-out "test" set relative to the panel model's explanatory power; test performance that doesn't degrade at all for countries with sparse data.

**Phase to address:**
Modelo 1/Modelo 2 (if any ML comparison model is included) — flag even if scikit-learn ends up used only for auxiliary purposes (e.g., preprocessing), since the panel-structure hazard is the same wherever an ML validation loop appears.

---

### Pitfall 14: Streamlit's rerun-on-every-interaction model without caching kills demo performance

**What goes wrong:**
Streamlit reruns the entire script top-to-bottom on every widget interaction (slider move, dropdown change). Without `@st.cache_data` (for data loading/transformation) and `@st.cache_resource` (for the fitted model object), every interaction with the counterfactual slider or country selector re-reads from SQLite, re-merges the panel, and potentially re-runs model inference — on a laptop, during a live 15-minute defense, this can produce multi-second freezes that look like the app has crashed. Combined with a full-resolution world choropleth (Pitfall 15), an uncached dashboard is a real risk to the oral defense specifically, not just a nice-to-have optimization.

**Why it happens:**
Streamlit's execution model is genuinely surprising to newcomers — the "just rerun everything" default is what makes Streamlit simple to write but is also exactly what makes naive apps slow.

**How to avoid:**
Cache the SQLite read + panel construction with `@st.cache_data`, cache the fitted PanelOLS model object and any precomputed SHAP values with `@st.cache_resource`, and precompute counterfactual simulation results for a reasonable grid of scenario values ahead of time rather than fitting/predicting live on every slider move. Rehearse the demo on the actual presentation machine beforehand with a *cold* cache to see the real worst-case first-load time, not just the warm-cache experience during development.

**Warning signs:**
Visible lag (>1-2s) between a widget interaction and the UI updating during development, on a dataset that's still much smaller than the full 150+ country panel; the app being noticeably faster the second time a chart is viewed than the first (a symptom of accidentally-working caching that isn't applied everywhere).

**Phase to address:**
Dashboard geoespacial — but the caching strategy should be designed alongside the data-access layer (SQLite schema), not bolted on at the end.

---

### Pitfall 15: Full-resolution world boundary GeoJSON makes the choropleth sluggish

**What goes wrong:**
Plotly choropleth maps rendering 150+ country polygons can take many seconds to render and feel sluggish on pan/zoom/hover when using a high-resolution boundary file (e.g., 10m-resolution Natural Earth or similar), independent of the underlying data size. This is a documented, common complaint in the Plotly/Streamlit community, not a hypothetical.

**Why it happens:**
High-resolution boundary GeoJSON files (often several MB, with thousands of vertices per country for coastline detail) are the default choice when someone searches "world map geojson," because they look good in a static map — but they're overkill for a country-level, non-zoomed-in choropleth.

**How to avoid:**
Use a simplified low-resolution boundary file (e.g., 110m-resolution Natural Earth admin-0 countries, well under 1MB) since country-level fill color is the only thing being communicated — coastline detail adds no informational value here. Alternatively use Plotly's built-in `locationmode='ISO-3'` with the default lightweight base map rather than a custom GeoJSON overlay, if the built-in country set matches the project's need.

**Warning signs:**
Choropleth taking multiple seconds to first-render even with cached data; browser/renderer visibly stuttering during zoom or hover.

**Phase to address:**
Dashboard geoespacial.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Hardcoding a country list instead of filtering programmatically against the M49 standard | Faster first EDA pass | Silently breaks when API data updates or a renamed/split country appears; not reproducible | Only for a throwaway first exploration notebook — never in the final ingestion pipeline |
| Skipping row-count/uniqueness assertions in ingestion parsing | Faster to first plot | Silent duplicate rows inflate panel N and bias regression precision (false confidence in significance) | Never for the final ingestion pipeline; acceptable to skip only in a disposable scratch script |
| Running plain OLS (pooled, no fixed effects) as a first pass | Fast sanity check of sign/magnitude | If mistaken for or reported as the final model, reintroduces the exact reverse-causality/omitted-variable bias the proposal flags as mitigated | Acceptable only as an explicitly-labeled "naive baseline" comparison row in a robustness table, never as the headline result |
| Copy-pasting API calls per indicator without retry/backoff/timeout handling | Quick to write | Transient network errors during a long batch pull silently produce partial data that looks complete | Never for the final versioned local copy of the data — this is the exact scenario PROJECT.md's "copia local versionada" mitigation exists to prevent |
| Using `KernelExplainer` for all SHAP work regardless of model type | Works without thinking about explainer/model matching | Slow, sampling-noisy results that undermine the interpretability chapter's credibility | Acceptable only for quick exploratory checks on a small subsample, never for final reported SHAP figures |
| Computing counterfactual simulation live inside the Streamlit callback (no precomputation) | Fewer moving parts to build | Live demo-time risk (Pitfall 14): freezes or crashes exactly when the tribunal is watching | Acceptable during early development iteration only; must be replaced by precomputed/cached results before the defense |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| UN SDG API pagination | Assuming a single response page contains all data for an indicator; not checking `totalElements` vs. rows returned | Loop through `pageNumber` until the retrieved row count matches the API's reported total; log and assert on the final count |
| UN SDG API dimension filtering | Pulling raw series without filtering `Nature`/`Reporting Type`/other dimensions, producing duplicate country-year rows | Explicitly select and document one dimension combination per indicator; assert `(country, year)` uniqueness after filtering |
| UN SDG API data trustworthiness | Treating a 200 OK response as ground truth without cross-checking | Spot-check 4-5 well-known countries per indicator against a secondary source (World Bank WDI, FAO AQUASTAT) and document the check |
| Cross-source country identifiers | Joining on country name strings across indicators or against a secondary validation source | Build one canonical M49/ISO3/name crosswalk table; join everything on the numeric code exclusively |
| SQLite panel storage | No composite primary key on `(country_code, year, indicator)`; re-running ingestion appends duplicate rows instead of upserting | Enforce a composite primary key or unique constraint at table-creation time; use `INSERT OR REPLACE`/upsert logic for re-runs |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Recomputing panel merge/pivot on every Streamlit rerun | UI lag growing with number of interactive widgets; visible freeze on slider drag | `@st.cache_data` on data loading/merging functions; precompute derived tables once | Already noticeable well before the full 150+ country panel is loaded; guaranteed to be a problem at full scale on a laptop |
| Full-resolution (10m) world boundary GeoJSON in the choropleth | Multi-second initial render; stuttering pan/zoom | Use simplified (110m) boundary file or Plotly's built-in `locationmode='ISO-3'` | At 150+ countries with high-vertex-count polygons, essentially guaranteed |
| Live (uncached) counterfactual simulation + SHAP recomputation in dashboard callbacks | Multi-second to tens-of-seconds delay per interaction; demo-time freeze risk | Precompute a scenario grid and SHAP values ahead of time; cache fitted model with `@st.cache_resource` | Breaks as soon as inference/SHAP is inside a callback rather than precomputed — independent of country count |
| `KernelExplainer` SHAP on the full merged panel with default settings | SHAP computation running for minutes+ | Use matched explainer (`LinearExplainer`/`TreeExplainer`) or a small `shap.sample`/`shap.kmeans` background | At full panel scale (~3,000+ country-year rows × multiple features) with the general-purpose explainer |

## Security Mistakes

This is a local-only academic project with no user data and a public, unauthenticated data source, so classic web-app security risks (auth, injection, secrets) are largely not applicable. The domain-relevant risks are narrower:

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoded absolute local paths (e.g., personal `G:\` drive paths, Windows usernames) embedded in scripts, notebooks, or committed config | Minor privacy leak if the repo is shared/submitted; breaks reproducibility on another machine | Use relative paths from the repo root everywhere; keep any personal reference paths (like the proposal document location) out of committed code |
| Committing raw SQLite database file with no `.gitignore` discipline, mixing large binary data with source control history | Bloats repo history, makes the final deliverable harder to package/submit cleanly | Keep the versioned "local copy of the data" as a documented, separate data artifact (per PROJECT.md's own mitigation), track schema/scripts in git, decide deliberately whether the `.db` file itself belongs in version control |

## UX Pitfalls

The dashboard's primary "user" is the tribunal during a 10-15 minute live oral defense — UX failures here have outsized consequences relative to a normal project.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| No loading indicator during a multi-second choropleth/simulation recompute | Tribunal perceives the app as frozen or broken mid-defense | Wrap slow operations in `st.spinner`; more importantly, eliminate the slowness via caching/precomputation (Pitfalls 14-15) so a spinner is rarely even needed |
| Cramming every model output (both regressions, both indicators, SHAP, counterfactual, raw data table) onto one screen | Evaluators get lost in a 15-minute window; core finding gets buried | Curate 3-4 focused views (map, scenario slider, SHAP summary, one comparative chart) with a clear default landing view that shows the headline finding first |
| No offline fallback if the live app hangs, crashes, or the presentation machine has an issue | Live defense failure is unrecoverable in the moment and directly costs points in the 30% oral-defense weighting | Prepare a pre-rendered screenshot/short-video backup of the key dashboard views embedded in the presentation slides, rehearsed as the fallback path |
| Miscalibrated color scale on the water-stress choropleth (e.g., a generic sequential palette that doesn't reflect the domain's meaningful thresholds) | Viewers misjudge severity — water stress has recognized thresholds (e.g., ~25% low, ~70% high per FAO/UN-Water framing referenced in the proposal's own sources) that a naive min-max color scale obscures | Use a domain-informed diverging/sequential scale with documented breakpoints matching the literature the memoria already cites (FAO & UN-Water 2024) |

## "Looks Done But Isn't" Checklist

- [ ] **Ingestion pipeline:** Often missing retry/backoff and a reproducibility check — verify by re-running ingestion twice and confirming identical row counts and checksums on the versioned local copy.
- [ ] **Panel dataset:** Often missing an explicit, logged record of which countries/years were excluded and why — verify an exclusion log exists and its numbers match whatever coverage statement appears in the memoria.
- [ ] **Model 1 (PIB):** Often missing robustness checks beyond the single baseline spec — verify at least a two-way-FE vs. entity-FE-only comparison and clustered vs. non-clustered SE comparison are both reported.
- [ ] **Counterfactual simulation:** Often missing bounds-checking against the observed data range — verify simulation code explicitly flags or clips scenarios outside the empirical percentile range.
- [ ] **SHAP analysis:** Often missing a correlation/VIF check reported before SHAP claims — verify the correlation matrix appears in the EDA/interpretability chapter, not just the SHAP plot alone.
- [ ] **Dashboard:** Often only tested on the developer's machine with a warm cache — verify a cold-start timing test on the actual presentation machine before the defense date.
- [ ] **Country coverage claim:** Often stated as "150+ countries" without the number being traceable to actual code output — verify the exact final country count and exclusion criteria are printed/logged and match the memoria's stated figure exactly.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|-----------------|
| Discovering random (non-panel-aware) train/test splitting after ML modeling is done | MEDIUM | Rerun with leave-one-country-out or time-based split; compare metrics side-by-side and report both in the methodology as a transparency note |
| Discovering unbalanced-panel confounding late (country count/coverage doesn't match what was assumed during modeling) | MEDIUM-HIGH | Rebuild the panel with the documented 70%-coverage filter applied at a clearly-stated stage (pre- or post-merge); rerun both models; treat the discrepancy as a documented methodological refinement, not a hidden fix |
| Discovering country-code merge errors (missing/misjoined countries) after substantial analysis or write-up exists | HIGH — could invalidate country-level figures close to a deadline | Build the canonical M49/ISO3 crosswalk table early (Ingesta phase) and add an automated test asserting country count against the known UN member-state list, specifically to catch this long before it's expensive to fix |
| Dashboard underperforming or breaking during a rehearsal before the live defense | MEDIUM if caught in rehearsal, HIGH if caught live | Treat as a prevention priority, not a recovery one: rehearse on the actual presentation hardware with a cold cache at least once before the defense window (Oct 2026), with a pre-rendered fallback ready regardless |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| API dimension duplication (P1) | Ingesta | Assert `(country, year)` uniqueness per indicator post-filter |
| Regional aggregates leaking into panel (P2) | Ingesta / Almacenamiento | Country count check against M49 country/area list |
| Name-based country joins (P3) | Almacenamiento | Crosswalk table exists as a first-class SQLite table; all joins reference it |
| Untrusted API values (P4) | Limpieza / EDA | Manual cross-check log for 4-5 known countries per indicator |
| Missing two-way fixed effects (P5) | Modelo 1 | Robustness table comparing entity-FE-only vs. two-way FE |
| Non-clustered standard errors (P6) | Modelo 1 | Methodology chapter states `cluster_entity=True`; SE comparison reported |
| Overstated reverse-causality mitigation (P7) | Modelo 1 + write-up | Explicit limitations paragraph distinguishing FE's actual identification claim |
| Counterfactual extrapolation beyond data support (P8) | Simulación contrafactual | Scenario bounds-check against empirical percentile range, flagged in output |
| Understated counterfactual CIs (P9) | Simulación contrafactual | Bootstrap-based CI reported alongside or instead of analytical CI |
| SHAP on correlated regressors (P10) | Interpretabilidad (SHAP), informed by EDA | Correlation/VIF table precedes SHAP results in the memoria |
| Wrong/expensive SHAP explainer (P11) | Interpretabilidad (SHAP) | Explainer type matched to model type documented in code/methodology |
| Silent panel shrinkage on merge (P12) | Limpieza / feature engineering | Logged row/country counts before and after each merge step |
| ML train/test leakage (P13) | Modelo 1/2 (if ML comparison used) | Split strategy documented and justified (leave-one-country-out or time-based) |
| Uncached Streamlit reruns (P14) | Dashboard geoespacial | Cold-start timing test on presentation hardware |
| Heavy GeoJSON choropleth (P15) | Dashboard geoespacial | Render-time benchmark with simplified boundary file |

## Sources

- UN Statistics Division SDG API documentation and SDMX-SDG API manual (`unstats.un.org/sdgs/files/SDMX_SDG_API_MANUAL.pdf`, `unstats.un.org/SDGMetadataAPI/`) — official API is explicitly published as a test/development service — MEDIUM confidence
- UN M49 standard country/area classification methodology (`unstats.un.org/unsd/methodology/m49/`) — ISO3/M49 code mismatch behavior on country splits/dissolutions — MEDIUM confidence
- Nickell (1981) dynamic panel bias; applied literature on clustered standard errors and serial correlation in fixed-effects panel regressions (Journal of Quantitative Criminology, arXiv panel-econometrics literature) — cross-checked against multiple sources — MEDIUM confidence, consistent with Baltagi/Wooldridge (already in the project's own reference list)
- SHAP interpretability literature on correlated-feature attribution and the causal-vs-associational distinction (multiple 2024-2026 arXiv papers on Causal SHAP, "8 Pitfalls to Avoid When Interpreting ML Models") — cross-checked against multiple independent sources — MEDIUM confidence, consistent with Molnar (already in the project's own reference list)
- Streamlit/Plotly community forum threads on choropleth rendering performance and caching (`discuss.streamlit.io`, `community.plotly.com`, Plotly's own geospatial performance blog post) — cross-checked across multiple independent threads reporting the same failure mode — MEDIUM confidence
- Domain knowledge of applied panel econometrics practice (two-way fixed effects, cluster-robust SE, leave-one-country-out validation) and standard Streamlit caching semantics — general knowledge, cross-checked against the sources above

---
*Pitfalls research for: Panel econometrics + ML interpretability + counterfactual simulation (UN SDG data, Streamlit/Plotly dashboard)*
*Researched: 2026-07-10*
