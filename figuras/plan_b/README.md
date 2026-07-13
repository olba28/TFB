# Plan B — Backup del dashboard (DASH-05 / D-08)

Índice de las capturas de respaldo (Plan B) para la demo en vivo del dashboard durante la
defensa oral. Si el dashboard en vivo (`streamlit run src/dashboard/app.py`) falla durante
la defensa, estas capturas —tomadas con datos reales— sirven como recorrido de respaldo
coherente de las 4 pestañas (D-06).

## Capturas requeridas (una por pestaña)

| Archivo | Pestaña |
|---------|---------|
| `01_mapa_e_indicadores.png` | Mapa e indicadores |
| `02_modelo_1.png` | Modelo 1 |
| `03_simulacion.png` | Simulación |
| `04_interpretabilidad_shap.png` | Interpretabilidad (SHAP) |

Formato: PNG o PDF (p. ej. "Print to PDF" del navegador es válido); mantener los nombres
exactos de arriba (con extensión `.png` o `.pdf` según el mecanismo de captura elegido).

## Reglas de captura (UI-SPEC — Plan B Screenshot Contract, DASH-05)

- Capturar cada una de las 4 pestañas **después** de que todos los datos/gráficos hayan
  renderizado por completo (sin spinner de Streamlit, sin indicador "Running..." visible)
  — una captura a mitad de carga se ve poco profesional ante un tribunal.
- Usar el mismo tamaño de ventana del navegador para las 4 capturas (recomendado:
  maximizada/ancho completo, acorde con `st.set_page_config(layout="wide")`), de forma
  que el set de respaldo se vea como un recorrido consistente y no como cuatro recortes
  dispares.
- Para la pestaña "Mapa e indicadores", capturar con ambos choropleths mostrando el
  **mismo año** seleccionado (no uno a mitad de animación y el otro reiniciado) — refuerza
  el encuadre "lado a lado, mismo año" de D-02.
- Guardar las capturas bajo `figuras/plan_b/` (sigue la convención ya existente de
  `figuras/` en el repo para outputs exportados).

## Cold-start time

Cold-start time: 2.01s (target <5s, cold cache, presentation machine) -- medido tras dos rondas de optimización durante el ensayo (ver commits `9d6ae4b`, `bfb5c25`, `1494e5b`): SHAP recompute cargaba un RandomForest pre-entrenado en vez de reajustarlo en vivo, y el bootstrap contrafactual se redujo a 8 réplicas demo.

(Se completa durante el ensayo de la Tarea 2 — reemplazar el placeholder anterior por el
tiempo medido de primer renderizado completo con caché en frío.)

## Nota sobre `kaleido`

`kaleido` (captura automática de figuras Plotly) **no** está instalado deliberadamente.
El mecanismo elegido para el Plan B es la captura manual del navegador (screenshot o
"Print to PDF"), que no requiere ninguna dependencia nueva ni Chrome/Chromium instalado
como parte del proyecto — ver RESEARCH.md Open Question 1. Esta decisión es consistente
con el precedente de la Fase 4 de no instalar PyALE cuando una alternativa ya disponible
(`sklearn.inspection.PartialDependenceDisplay`) cubría la necesidad sin añadir dependencias.

## Ensayo (rehearsal)

El ensayo de caché en frío y la producción de estas capturas se realizan como checkpoints
manuales (Tareas 2 y 3 del plan `05-05-PLAN.md`) sobre la máquina real de presentación,
ejecutando la app completa (`src/dashboard/app.py`) contra los artefactos de producción
reales (`data/panel.db`, `data/modelos/*.pkl`) — no fixtures de test.
