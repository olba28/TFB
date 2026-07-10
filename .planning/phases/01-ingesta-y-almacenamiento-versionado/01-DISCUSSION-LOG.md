# Phase 1: Ingesta y Almacenamiento Versionado - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 1-Ingesta y Almacenamiento Versionado
**Areas discussed:** Paginación y reintentos, Manifiesto y almacenamiento crudo, Esquema SQLite, Lista canónica de países y crosswalk M49↔ISO3

---

## Paginación y reintentos

| Question | Option | Selected |
|----------|--------|----------|
| ¿Cuántos reintentos y qué backoff? | 3 reintentos, backoff exponencial (1s,2s,4s) | ✓ |
| | Reintentos ilimitados, backoff fijo | |
| | Sin reintentos automáticos | |
| ¿Cómo manejar paginación? | Iterar automáticamente por páginas (totalElements/pageSize) | ✓ |
| | pageSize muy alto de una vez | |
| | Paginación manual por indicador | |
| ¿Cómo verificar reintento/paginación (Success Criteria #4)? | Test unitario con mocking (unittest.mock/responses) | ✓ |
| | Prueba manual documentada | |
| | Test de integración real | |
| ¿Delay/throttle entre llamadas? | Delay fijo pequeño (0.5-1s) | ✓ |
| | Sin delay | |
| | Delay adaptativo por headers | |

**Notes:** Ninguna nota adicional del usuario más allá de las respuestas seleccionadas.

---

## Manifiesto y almacenamiento crudo

| Question | Option | Selected |
|----------|--------|----------|
| ¿Granularidad del manifiesto? | Un manifiesto por indicador | ✓ |
| | Un manifiesto global único | |
| | Un manifiesto por ejecución (fecha) | |
| ¿Estructura de data/raw/? | Por indicador: data/raw/{indicador}/{fecha}.json | ✓ |
| | Por fecha: data/raw/{fecha}/{indicador}.json | |
| | Plano: data/raw/{indicador}_{fecha}.json | |
| ¿Re-descarga si ya existe? | Idempotente: solo descarga si no existe o se fuerza | ✓ |
| | Siempre re-descarga | |
| ¿Campos mínimos del manifiesto? | Fecha, URL, parámetros, nº filas, checksum | ✓ |
| | Solo fecha, URL y parámetros | |

**Notes:** Ninguna nota adicional del usuario más allá de las respuestas seleccionadas.

---

## Esquema SQLite

| Question | Option | Selected |
|----------|--------|----------|
| ¿Ubicación del fichero SQLite? | data/panel.db | ✓ |
| | data/db/panel.sqlite | |
| | src/ingesta/panel.db | |
| ¿Columnas de raw_observations? | country_code, indicator_code, year, value, dimension, source_manifest_id | ✓ |
| | country_code, indicator_code, year, value | |
| ¿Cómo aplicar unicidad (país, año, indicador)? | UNIQUE constraint + assert en pipeline | ✓ |
| | Solo assert en Python | |
| | Solo UNIQUE constraint en SQLite | |
| ¿Relación panel ↔ raw_observations? | Vista/tabla derivada regenerable (pivot) | ✓ |
| | Tabla independiente mantenida manualmente | |

**Notes:** Ninguna nota adicional del usuario más allá de las respuestas seleccionadas.

---

## Lista canónica de países y crosswalk M49↔ISO3

| Question | Option | Selected |
|----------|--------|----------|
| ¿Fuente de la lista canónica? | Lista oficial M49 de la ONU (país vs. región) | ✓ |
| | pycountry sovereign states + excepciones manuales | |
| | Lista del Banco Mundial | |
| ¿Territorios/casos disputados? | Incluir solo si tienen ISO3 y no son agregado regional | ✓ |
| | Excluir todos los no soberanos | |
| | Decidir caso por caso al ver los datos | |
| ¿Ubicación en el código? | src/ingesta/countries.py | ✓ |
| | data/reference/countries.csv | |
| ¿Documentar exclusiones? | Log/tabla de exclusiones generada en la ingesta | ✓ |
| | Sin registro explícito | |

**Notes:** El log de exclusiones (D-16) se identificó como precedente directo de la tabla de exclusiones por cobertura que exige PANEL-02 en Fase 2.

---

## Claude's Discretion

- Nombre exacto de la función/módulo del cliente API y organización interna de `src/ingesta/`.
- Formato exacto del checksum (sha256 vs md5).
- Mecanismo concreto para generar `requirements.lock.txt`.

## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 1.
