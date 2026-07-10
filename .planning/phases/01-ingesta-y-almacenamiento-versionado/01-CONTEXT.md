# Phase 1: Ingesta y Almacenamiento Versionado - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Cliente de la API SDG de la ONU con paginación automática y reintentos ante fallos transitorios, filtrado de dimensiones (p. ej. `Activity: TOTAL`) y de agregados regionales M49, copia local versionada de los 5 indicadores en JSON crudo con manifiesto de procedencia, y almacenamiento del panel en SQLite (`raw_observations` larga e inmutable + `panel` ancha derivada). Cubre INGEST-01 a INGEST-05 y REPRO-01 (`requirements.lock.txt`).

Esta fase NO incluye limpieza/feature engineering del panel más allá del pivot indicador→columnas, ni el filtrado por cobertura del 70% (eso es Fase 2).

</domain>

<decisions>
## Implementation Decisions

### Paginación y reintentos
- **D-01:** 3 reintentos con backoff exponencial (1s, 2s, 4s) ante fallos transitorios de la API.
- **D-02:** El cliente itera automáticamente por páginas usando el campo `totalElements`/`pageSize` de la respuesta de la API, sin asumir un tamaño de página fijo.
- **D-03:** El comportamiento de reintento/paginación (Success Criteria #4 del roadmap) se verifica con un test unitario que mockea `requests` (`unittest.mock` o `responses`) simulando un fallo 500 y una respuesta paginada — no una prueba manual ni un test de integración real contra la API.
- **D-04:** Se introduce un delay fijo pequeño (0.5–1s) entre llamadas a la API para evitar bloqueos, dado el volumen (5 indicadores × 150+ países).

### Manifiesto y almacenamiento crudo
- **D-05:** Un manifiesto de procedencia por indicador (no uno global ni uno por ejecución).
- **D-06:** Estructura de carpetas `data/raw/{indicador}/{fecha}.json` — permite comparar versiones del mismo indicador a lo largo del tiempo.
- **D-07:** La descarga es idempotente: el script comprueba el manifiesto antes de llamar a la API y solo descarga si no existe una copia o si se fuerza explícitamente.
- **D-08:** El manifiesto registra: fecha de descarga, URL, parámetros de consulta, número de filas y checksum del fichero descargado.

### Esquema SQLite
- **D-09:** El fichero de base de datos vive en `data/panel.db`.
- **D-10:** `raw_observations` incluye las columnas: `country_code` (ISO3), `indicator_code`, `year`, `value`, `dimension` (valor original de la dimensión de la API, p. ej. `Activity`), `source_manifest_id` (referencia al manifiesto de origen).
- **D-11:** La unicidad (país, año, indicador) — Success Criteria #1 del roadmap — se aplica con un `UNIQUE constraint` en SQLite **y** un `assert` explícito en el pipeline de carga antes de insertar (doble verificación: esquema + código).
- **D-12:** `panel` (tabla ancha) es una vista/tabla derivada, regenerable siempre desde `raw_observations` mediante pivot indicador→columnas. Nunca se edita a mano — coherente con el pipeline idempotente que construirá la Fase 2.

### Lista canónica de países y crosswalk M49↔ISO3
- **D-13:** La lista canónica de países sale de la clasificación oficial M49 de la ONU (distinción "country/area" vs. agregados regionales), no de pycountry ni de la lista del Banco Mundial — alineada con la propia fuente de datos (API SDG).
- **D-14:** Territorios/casos disputados o no soberanos (Kosovo, Taiwán, Palestina, Hong Kong) se incluyen si la API los reporta con código país (ISO3) y no como agregado regional M49 — criterio objetivo aplicado uniformemente, sin lista de excepciones manual.
- **D-15:** La lista canónica y el crosswalk M49↔ISO3 viven en `src/ingesta/countries.py` (constante + función de filtrado) — módulo reutilizable por la Fase 2 sin duplicar lógica.
- **D-16:** El pipeline de ingesta genera un log/tabla de exclusiones (qué códigos M49/regiones se descartaron y por qué) como insumo documentado para la memoria — no un filtrado silencioso. Este registro es un precedente directo para la tabla de exclusiones por cobertura que exige PANEL-02 en Fase 2.

### Claude's Discretion
- Nombre exacto de la función/módulo del cliente API, organización interna de `src/ingesta/` (p. ej. `fetch.py`, `client.py`, `manifest.py` como ficheros separados vs. un solo módulo).
- Formato exacto del checksum (sha256 vs md5) — cualquiera es válido mientras sea determinista y verificable.
- Mecanismo concreto para generar `requirements.lock.txt` (script dedicado vs. instrucción en README) — REPRO-01 solo exige que el fichero exista y refleje `pip freeze`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documentos del proyecto
- `.planning/PROJECT.md` — contexto completo, indicadores clave, riesgos y mitigaciones ya decididos (incluye la decisión de copia local versionada como mitigación a cambios de la API).
- `.planning/REQUIREMENTS.md` §"Ingesta y Almacenamiento" — INGEST-01 a INGEST-05 y REPRO-01, con su criterio de aceptación exacto.
- `.planning/ROADMAP.md` §"Phase 1" — Goal y 5 Success Criteria verificables que esta fase debe cumplir.
- `G:\Mi unidad\UCMA\tfb\TFB Pablo Martínez Entrega 2.docx` — propuesta oficial del TFB entregada a la UCMA; fuente original de los 5 indicadores y del análisis de riesgos (documento externo al repo, mencionado en PROJECT.md).

### Mapas de codebase (para research/planning)
- `.planning/codebase/STACK.md` — dependencias ya fijadas (requests, pandas, etc.), sin lockfile aún.
- `.planning/codebase/ARCHITECTURE.md` — capa de ingesta (`src/ingesta/`), patrón de manifiesto sugerido, anti-patrones a evitar (config embebida, descarga manual).
- `.planning/codebase/INTEGRATIONS.md` — estado actual de la integración con la API SDG (endpoint aún no documentado en el repo).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ingesta/` existe como carpeta esqueleto (vacía) — ubicación ya designada para el cliente API, manifiesto y `countries.py`.
- `requirements.txt` ya fija `requests` como cliente HTTP — no se necesita elegir librería.

### Established Patterns
- Patrón de manifiesto ya sugerido en ARCHITECTURE.md (`data/[fecha]/manifest.json`) — esta fase lo refina a granularidad por indicador (D-05, D-06) en vez de por fecha global.
- Anti-patrón documentado a evitar explícitamente: "Manual Data Download" (ARCHITECTURE.md) — toda descarga debe pasar por `src/ingesta/`, nunca manual.

### Integration Points
- La Fase 2 (Construcción del Panel y EDA) consumirá `raw_observations` y reutilizará `src/ingesta/countries.py` para el filtrado por cobertura (PANEL-02).
- El log de exclusiones de M49 (D-16) es la base directa de la tabla de exclusiones que exige PANEL-02 en Fase 2.

</code_context>

<specifics>
## Specific Ideas

- El alumno ya ha usado la API SDG de la ONU en trabajos previos — sin dudas expresadas sobre el endpoint o formato de respuesta en sí, el foco de la discusión fue el diseño del cliente (paginación, reintentos) y del almacenamiento (manifiesto, esquema SQLite, lista de países), no la familiaridad con la API.

</specifics>

<deferred>
## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 1.

</deferred>

---

*Phase: 1-Ingesta y Almacenamiento Versionado*
*Context gathered: 2026-07-10*
