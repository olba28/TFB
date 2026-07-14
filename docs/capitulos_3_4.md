## 3. Metodologia

### 3.1 Fuentes de datos y estrategia de obtención vía API ODS de la ONU

El presente trabajo se basa exclusivamente en indicadores públicos de los Objetivos de Desarrollo Sostenible (ODS) de la ONU, obtenidos mediante la API SDG (`https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data`), lo que garantiza trazabilidad y reproducibilidad completas frente a cualquier fuente alternativa. Se seleccionan cinco indicadores fijos que cubren simultáneamente la dimensión hídrica y la dimensión económica del análisis: `6.4.2` (nivel de estrés hídrico, relación entre la extracción de agua dulce y los recursos hídricos renovables disponibles), `6.4.1` (eficiencia en el uso del agua), `8.1.1` (tasa de crecimiento anual del PIB real per cápita), `8.2.1` (tasa de crecimiento anual del PIB real por persona empleada, entendida como productividad laboral) y `2.3.1` (productividad agrícola, medida como el valor de la producción por unidad de trabajo). El periodo cubierto es 2000-2022 (23 años), definido de antemano como constante fija en el cliente HTTP y nunca derivado de la respuesta de la API, por razones de seguridad frente a inyección de parámetros.

El acceso a la API se implementa en `src/ingesta/client.py` mediante una sesión `requests.Session` configurada con una política de reintentos delegada por completo a `urllib3.util.retry.Retry` -- nunca un bucle manual de `try/except` -- con `total=3` reintentos, `backoff_factor=1` (produciendo la secuencia de espera 1s/2s/4s) y `status_forcelist=[429, 500, 502, 503, 504]`. La paginación se resuelve leyendo el campo `totalPages` únicamente de la primera respuesta de cada indicador -- nunca asumiendo un número de páginas compartido entre indicadores, dado que cada uno reporta un volumen de observaciones distinto -- e insertando una pausa fija de 0.5 segundos entre páginas sucesivas para no saturar el servicio.

Cada indicador exige un filtro de dimensión propio antes de considerarse la serie "cabecera" (`HEADLINE_DIMENSIONS`): `6.4.2` y `6.4.1` requieren `Activity=TOTAL`; `2.3.1` requiere `Sex=BOTHSEX`; `8.1.1` y `8.2.1` no añaden dimensión adicional más allá de `Reporting Type=G`. Un hallazgo relevante durante la ingesta real fue que el indicador `2.3.1` multiplexa dos series distintas bajo la misma combinación de dimensiones -- productividad de pequeños productores (`PD_AGR_SSFP`) y de grandes productores (`PD_AGR_LSFP`) -- distinguibles solo por el campo `series` de la API, no anticipado en la fase de investigación previa. Se adopta `PD_AGR_SSFP` como serie cabecera de `2.3.1`, decisión alineada con el propio enunciado de la meta ODS 2.3 ("duplicar la productividad agrícola... de los pequeños productores de alimentos"), aprobada explícitamente por el usuario en un punto de control durante la Fase 1.

La correspondencia entre países y códigos se resuelve mediante un cruce M49-ISO3 (`src/ingesta/countries.py`), construido a partir del propio endpoint `GeoArea/Tree` de la ONU y del fichero oficial `m49_countries.csv` (columnas `M49 Code`/`ISO-alpha3 Code`) -- nunca mediante `pycountry` ni listas del Banco Mundial, para mantener una única fuente de verdad ONU-nativa (D-13). Un código `geoAreaCode` se considera país incluido si y solo si resuelve a un nodo hoja con `type == "Country"` en `GeoArea/Tree` -- una regla objetiva aplicada uniformemente, sin lista de excepciones manual para territorios en disputa. Todo nodo excluido (agregados regionales, continentes) y toda fila de observación que no supere el cruce se registra en un log de exclusión documentado (`data/raw/exclusion_log.json`), nunca se descarta en silencio. Un detalle técnico crítico es la normalización de códigos: `GeoArea/Tree` devuelve enteros sin relleno, `Indicator/Data` devuelve cadenas numéricas sin relleno y el CSV M49 usa cadenas de 3 dígitos con ceros a la izquierda; los tres se normalizan mediante `str(code).zfill(3)` antes de cualquier cruce, corrección necesaria tras verificarse en vivo que su ausencia producía cero filas supervivientes en los 5 indicadores.

### 3.2 Diseño del pipeline de ingesta y almacenamiento

El almacenamiento se realiza en un único fichero SQLite (`data/panel.db`), decisión justificada por su coste de configuración nulo, su facilidad de entrega/versionado ante el tribunal y su adecuación al alcance de un TFB individual. El esquema (`src/db.py`) define dos tablas centrales. `raw_observations` es la fuente de verdad inmutable y de solo-adición: una fila por combinación `(country_code, indicator_code, year)`, con columnas `value` (nullable -- una observación faltante se almacena como `NULL`, nunca se elimina la fila), `dimension` (la combinación de dimensiones original de la API) y `source_manifest_id` (referencia al manifiesto de procedencia). La duplicidad se previene por partida doble: una comprobación explícita en `insert_observations` antes de cualquier inserción, y una restricción `UNIQUE(country_code, year, indicator_code)` a nivel de esquema. `panel` es una tabla derivada (`db.rebuild_panel`), siempre regenerada por completo desde `raw_observations` mediante un pivote `indicator_code -> columnas` -- nunca editada a mano.

El versionado de los datos crudos se resuelve mediante manifiestos de procedencia (`src/ingesta/manifest.py`), no mediante control de versiones de Git sobre los ficheros de datos en sí. Cada descarga produce un fichero `data/raw/<indicador>/<fecha>.json` junto a un sidecar `<fecha>.manifest.json` con cinco campos fijos: fecha, URL, parámetros de consulta, número de filas y checksum SHA-256 del fichero descargado. El manifiesto se escribe únicamente después de que la fila haya superado el filtro de dimensión, el cruce de país y la inserción en `raw_observations` -- escribirlo antes arriesgaría que un fallo a mitad de pipeline hiciera que ejecuciones futuras omitieran silenciosamente ese indicador para siempre, dado que la comprobación de idempotencia (`manifest_exists`) solo verifica la presencia del manifiesto, no si los datos realmente llegaron a la base de datos.

El fichero `.gitignore` del repositorio documenta explícitamente qué se versiona y qué se regenera: los ficheros `data/**/*.json` y `data/**/*.csv` quedan excluidos de Git salvo los propios manifiestos (`!data/**/*.manifest.json`), la base de datos `data/panel.db` queda excluida (regenerable desde `data/raw/` + el código fuente) y los modelos serializados (`*.pkl`, `*.joblib`) tampoco se versionan. Esta política permite entregar un repositorio ligero y trazable ante el tribunal: los datos brutos y la base de datos se reconstruyen ejecutando el propio pipeline, mientras que los manifiestos -- que documentan qué se descargó, cuándo y con qué parámetros -- sí quedan versionados como evidencia de procedencia. Las cinco descargas de indicador reales de este TFB están fechadas el 2026-07-11, con los siguientes volúmenes de filas crudas registrados en sus manifiestos: `6.4.2` con 19.182 filas, `6.4.1` con 18.837 filas, `8.1.1` con 5.682 filas, `8.2.1` con 5.220 filas y `2.3.1` con 4.883 filas (antes de cualquier filtro de dimensión/país). Tras el filtrado de dimensión cabecera y el cruce de país/ISO3, `raw_observations` almacena un total de 18.086 filas: `8.1.1` con 4.790, `6.4.2` con 4.186, `8.2.1` con 4.300, `6.4.1` con 3.910 y `2.3.1` con 900 filas.

### 3.3 Análisis exploratorio y selección de features

La tabla `panel_clean` (`src/panel_build.py`, notebook `2_1_construccion_panel_eda.ipynb`) es un pivote fiel de `raw_observations`, enriquecido con las columnas de referencia de país (`region`, `subregion`, `is_ldc`, `is_lldc`, `is_sids`), regenerada íntegramente en cada ejecución -- nunca editada a mano, siguiendo la misma convención ya establecida por `db.rebuild_panel`. En su estado real contiene 4.923 filas país-año, correspondientes a 215 países distintos. Las estadísticas descriptivas globales sobre los 5 indicadores son:

| Indicador | count | mean | std | min | 25% | 50% | 75% | max |
|---|---|---|---|---|---|---|---|---|
| 6.4.2 | 4041 | 56,59 | 236,17 | 0,01 | 3,58 | 10,46 | 34,96 | 3850,50 |
| 6.4.1 | 3530 | 41,62 | 101,07 | 0,17 | 4,88 | 13,17 | 40,60 | 1394,86 |
| 8.1.1 | 4790 | 2,17 | 6,23 | -55,20 | 0,00 | 2,20 | 4,60 | 95,80 |
| 8.2.1 | 4300 | 1,67 | 5,37 | -53,89 | -0,43 | 1,61 | 3,87 | 92,45 |
| 2.3.1 | 173 | 50,35 | 37,59 | 1,90 | 10,50 | 50,80 | 77,40 | 147,10 |

El criterio de cobertura mínima aplicado por `compute_coverage`/`build_exclusion_table` (`panel_build.py`) exige un mínimo de 17 de los 23 años posibles (70% de cobertura, `YEARS_REQUIRED = 17`) con dato no nulo para que un país sobreviva, por indicador. Este umbral se documenta en una tabla dedicada `panel_exclusions` (529 combinaciones país-indicador excluidas en total), nunca modificando el valor real ya reportado en `panel_clean` -- la exclusión se documenta por separado, no se destruye el dato original, precisamente para no imposibilitar comprobaciones de robustez posteriores sobre la submuestra excluida. Por indicador, las exclusiones se reparten así: `2.3.1` con 248 países excluidos (de un universo de 248 en `country_reference`, es decir, **cero países superan el umbral del 70%** para este indicador, dado que se reporta en oleadas discretas cada varios años, no anualmente), `6.4.1` con 102, `6.4.2` con 76, `8.2.1` con 61 y `8.1.1` con 42.

El patrón de valores faltantes por indicador es marcadamente desigual: 2,7% en `8.1.1`, 12,7% en `8.2.1`, 17,9% en `6.4.2`, 28,3% en `6.4.1` y 96,5% en `2.3.1`. Este patrón **no es plausible como MCAR** (missing completely at random, Rubin 1976 [CITA POR VERIFICAR]): varía sistemáticamente por región (Oceanía 61,7% de media entre indicadores, Europa y Norteamérica 46,5%, América Latina y el Caribe 39,9%, frente a Sub-Sahariana con 23,4%) y por tipología de país. La evidencia más clara de riesgo MNAR (missing not at random) es la de los pequeños estados insulares en desarrollo (SIDS): 49,9% de valores faltantes promedio frente a 26,3% en los países no-SIDS, consistente con la hipótesis de que su capacidad estadística limitada afecta simultáneamente el reporte de indicadores hídricos y económicos. El patrón no es uniforme en los tres ejes de tipología -- los países LDC (25,9%) y LLDC (21,8%) muestran de hecho *menor* tasa de valores faltantes que sus contrapartes (33,1% y 33,3% respectivamente), reflejando que la relación entre vulnerabilidad y capacidad estadística no es lineal entre clasificaciones. La implicación metodológica para el Modelo 1 es que cualquier análisis de casos completos (listwise deletion) sobrerrepresenta sistemáticamente a los países con mejor capacidad estadística, un sesgo que debe reconocerse al interpretar los coeficientes, no solo al reportar el tamaño muestral.

La matriz de correlación global (casos completos en los 5 indicadores simultáneamente, n=171 filas) y su tabla de VIF asociada (con constante añadida vía `statsmodels.tools.add_constant`, práctica estándar sin la cual los valores de VIF cambian) son:

| | 6.4.2 | 6.4.1 | 8.1.1 | 8.2.1 | 2.3.1 |
|---|---|---|---|---|---|
| 6.4.2 | 1,000 | -0,092 | -0,064 | -0,035 | 0,268 |
| 6.4.1 | -0,092 | 1,000 | -0,050 | -0,010 | 0,348 |
| 8.1.1 | -0,064 | -0,050 | 1,000 | 0,703 | -0,317 |
| 8.2.1 | -0,035 | -0,010 | 0,703 | 1,000 | -0,208 |
| 2.3.1 | 0,268 | 0,348 | -0,317 | -0,208 | 1,000 |

| Indicador | VIF global |
|---|---|
| 6.4.2 | 1,127 |
| 6.4.1 | 1,195 |
| 8.1.1 | 2,107 |
| 8.2.1 | 1,981 |
| 2.3.1 | 1,409 |

Se calculan 12 tablas de VIF en total (1 global, 8 regionales, 3 por tipología). A nivel regional, el patrón global de baja colinealidad se rompe drásticamente en submuestras pequeñas: Europa (n=104 filas completas) muestra VIF de hasta 3,28 (`8.2.1`), mientras que América Latina y el Caribe (n=7 filas completas, tamaño muestral extremadamente pequeño) exhibe VIF de 71,3 (`6.4.2`), 196,2 (`6.4.1`) y 305,6 (`2.3.1`) -- una advertencia explícita de que la matriz de correlación agregada usada aguas abajo (selección de controles del Modelo 1, aviso de sesgo por correlación de SHAP en la Fase 4) no es representativa de todas las subregiones. Sub-Sahariana (n=44), en cambio, mantiene VIF cercano a 1 en los 5 indicadores. Por tipología, `is_ldc` (n=44) e `is_lldc` (n=31) muestran VIF moderado (máximo 1,90), mientras que `is_sids` solo dispone de 2 filas completas (insuficiente para una estimación fiable de VIF).

La tipología de país (`is_ldc`, `is_lldc`, `is_sids`) se obtiene enteramente del propio endpoint `GeoArea/Tree` de la ONU (`src/ingesta/typology.py`), no de las categorías de ingreso del Banco Mundial -- una investigación durante la Fase 2 confirmó que `GeoArea/Tree` incluye las *etiquetas* de los grupos de ingreso del Banco Mundial pero sin membresía real de país bajo ellas (decisión [Phase 02-01] registrada en `STATE.md`). Cada uno de los tres indicadores de estatus de desarrollo se resuelve recorriendo el árbol desde el código raíz correspondiente (LDC: 199; LLDC: 432; SIDS: 722) hasta cada hoja de tipo país, con valor por defecto `False` para todo país no encontrado bajo esa raíz.

### 3.4 Modelo 1 (predicción del crecimiento del PIB per cápita)

El Modelo 1 (`notebook/3_1_modelo1_pib.ipynb`, reutilizando `src/panel_base.py` sin modificarlo) especifica un `PanelOLS` de efectos fijos bidireccionales (entidad país + tiempo año) con variable dependiente `8.1.1` (crecimiento del PIB real per cápita) y variable independiente `6.4.2` (estrés hídrico). El filtro de exclusión por cobertura (`filter_by_exclusions`) deja una muestra de 171 países y 3.933 observaciones país-año (dentro del 10% de la expectativa de la fase de investigación previa, ~171 países / ~3.879 observaciones); el ajuste final del modelo, tras la eliminación interna de filas con valores perdidos por `PanelOLS`, opera sobre 3.879 observaciones efectivas.

La elección del tipo de error estándar no es arbitraria: se decide mediante el test de dependencia transversal de Pesaran (Pesaran, 2004 [CITA POR VERIFICAR]), calculado manualmente en `panel_base.pesaran_cd_test` (ni `linearmodels` ni `statsmodels` implementan este test para datos de panel). El resultado real sobre los residuos del ajuste provisional es CD = 3,2042, p = 0,0014, lo que **rechaza H0** (no hay dependencia transversal) al 5% y selecciona errores estándar Driscoll-Kraay (`cov_type="kernel"`, `kernel="bartlett"`) para el resto del análisis, en lugar de errores clusterizados por entidad. Se documenta explícitamente el matiz metodológico heredado de la Fase 3: un ajuste de efectos fijos bidireccionales induce mecánicamente una pequeña correlación negativa entre residuos de distintos países (efecto de *time-demeaning*, De Hoyos y Sarafidis, 2006 [CITA POR VERIFICAR]), que puede empujar el test de Pesaran hacia el rechazo incluso sin dependencia transversal genuina -- efecto más marcado con N pequeño. Con N=171 países, sustancialmente mayor que el caso sintético N=30 donde se documentó por primera vez este artefacto, el efecto debería ser más débil, pero el resultado se reporta con esta salvedad como contexto.

El ajuste final (Driscoll-Kraay) produce los siguientes resultados reales:

| Parámetro | Coeficiente | Error estándar | t-stat | p-valor | IC 2,5% | IC 97,5% |
|---|---|---|---|---|---|---|
| 6.4.2 | -0,0001 | 0,0006 | -0,2227 | 0,8238 | -0,0014 | 0,0011 |

R² (within) = 6,779e-05; R² global = -0,0003; F-test de poolability = 5,8039 (p = 0,0000, rechazando la hipótesis de que un modelo pooled sea adecuado frente a efectos fijos); 171 entidades, 23 periodos temporales. El coeficiente de `6.4.2` **no resulta estadísticamente significativo** al 5% en esta especificación.

La comparación de especificaciones (`compare_specifications`, todas con `cov_type="unadjusted"` para aislar diferencias entre estimadores, no de metodología de errores estándar) es:

| | Pooled OLS | Random Effects | PanelOLS (FE) |
|---|---|---|---|
| N observaciones | 3879 | 3879 | 3879 |
| R² | 0,0045 | 0,0017 | 1,3e-05 |
| Coeficiente 6.4.2 | -0,0016 (t=-4,17) | -0,0012 (t=-2,44) | -0,0001 (t=-0,22) |
| F-statistic | 17,406 | 6,670 | 0,0479 |
| p-valor (F-stat) | 0,0000 | 0,0098 | 0,8268 |

El test de Hausman (Hausman, 1978 [CITA POR VERIFICAR]), implementado manualmente en `panel_base.hausman_test` con ambos lados (FE y RE) ajustados con el mismo `cov_type="kernel"` elegido arriba -- condición metodológicamente necesaria para la validez de la comparación -- produce H = 0,2566 (df=1), p = 0,6125, **no rechazando H0**: FE y RE no difieren significativamente en esta muestra. Independientemente de este resultado, la especificación de efectos fijos es la elegida para el Modelo 1 por decisión ya fijada durante la discusión de la Fase 3 (no un punto de decisión en vivo); el test de Hausman se reporta como la justificación documentada exigida por el criterio de éxito de la fase.

La comprobación de robustez (submuestra 2000-2019, excluyendo los años 2020-2022 por los shocks atípicos de la pandemia -- no una variante con controles adicionales, alternativa considerada y explícitamente descartada durante la discusión de fase) produce:

| | Coeficiente (6.4.2) | p-valor | Significativo (5%) |
|---|---|---|---|
| Modelo base (2000-2022) | -0,00014 | 0,8238 | No |
| Robustez (2000-2019) | -0,00044 | 0,4694 | No |

El signo del coeficiente se mantiene (razón de magnitudes robustez/base: 3,14x) y la conclusión de no significancia estadística al 5% se mantiene también al excluir los años COVID -- el resultado se considera **cualitativamente consistente** entre ambas ventanas temporales.

**Limitaciones y amenazas a la validez.** El coeficiente estimado sobre el estrés hídrico no debe interpretarse como evidencia de causalidad unidireccional hacia el crecimiento del PIB per cápita. Es plausible que la relación opere también en sentido contrario: un peor desempeño económico puede limitar la capacidad de un país para invertir en infraestructura hídrica (desalinización, redes de distribución, tratamiento de aguas), agravando su propio estrés hídrico medido -- un riesgo de causalidad inversa ya identificado en la propuesta oficial del TFB. Los efectos fijos de país y año absorben heterogeneidad no observada constante en el tiempo (o común a todos los países en un año dado), pero no resuelven por sí solos un problema de causalidad inversa contemporánea. De forma análoga, variables omitidas -- calidad institucional, exposición climática general más allá de `6.4.2`, shocks de política económica específicos -- podrían correlacionarse simultáneamente con el estrés hídrico y con el crecimiento del PIB si varían dentro de un país a lo largo del tiempo de forma correlacionada con el regresor de interés. Por estas dos razones, cualquier simulación contrafactual posterior (sección 3.6/4.3) se trata explícitamente como **análisis de sensibilidad, no como predicción causal**: el modelo de panel con efectos fijos es la mejor aproximación disponible dentro del alcance de este TFB para controlar heterogeneidad no observada, pero no elimina el riesgo de causalidad inversa ni de endogeneidad por variables omitidas, y los resultados deben leerse con esa cautela ante el tribunal.

<!-- gsd:write-continue -->
