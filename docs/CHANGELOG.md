# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## Sin publicar

### Añadido

- 2026-11-10: informe principal para cualquier ciudadano (D-19). El técnico pasa a `AAAA-MM-detalle.md`.
  - «En pocas palabras», las 5 votaciones más importantes del mes con hemiciclo, tipo de votación explicado y quién votó qué, barras de qué grupos votaron más veces lo que salió, quién vota con quién, tipos de asunto y glosario.
  - Títulos en lenguaje llano (`lenguaje.py`, D-18).
  - Hemiciclo con título, fecha, «✔ Aprobada / ✘ Rechazada» y la regla de mayoría; barra de 350 escaños para las votaciones por llamamiento.
  - Categoría «Leyes: veto del Senado».

- 2026-11-10: gráficos y secciones nuevas del informe.
  - Votaciones públicas por llamamiento (investiduras, conjunto de leyes orgánicas, repeticiones tras empate) leídas del HTML del día; nueva columna `llamamiento` (D-12).
  - Hemiciclo de las votaciones más ajustadas, mapa de calor de afinidad y mapa de diputados por componentes principales, en SVG claro y oscuro (`graficos.py`, D-13, D-16).
  - Secciones «Mapa de diputados», «Quién sacó adelante las votaciones» y «Votaciones que perdieron los grupos del Gobierno» (D-14); tipo de asunto por categorías (D-17).
  - Dependencias: numpy y matplotlib.
- 2026-11-10: creación del proyecto.
  - Descarga incremental por día desde el portal de datos abiertos del Congreso, con días pendientes y reintentos (`src/votaciones/fuente.py`, `almacen.py`).
  - Análisis mensual: resultado calculado, posición de cada grupo, cohesión (Hix), afinidad, grupos decisivos, votos distintos del grupo y ausencias (`analisis.py`).
  - Informe mensual en Markdown e índice (`informe.py`).
  - CLI con `sondear`, `actualizar`, `informe`, `mensual` e `historico`.
  - Workflows de GitHub Actions: `mensual.yml` (día 3 de cada mes, con commit del bot) y `tests.yml`.
  - 19 tests sin red y documentación en `docs/`.

### Cambiado

- 2026-11-10: el resultado usa un umbral por tipo de votación (176, 210 o mayoría simple) en lugar de la heurística «orgánica + conjunto», que marcaba como orgánicas leyes ordinarias que modifican una orgánica (D-06).
- 2026-11-10: los empates salen como «Empate (se repite)» y no como rechazadas (D-15).
- 2026-11-10: los días pendientes de hace más de 90 días se avisan como «no publicados», no como «aún no publicados».

### Corregido

- 2026-11-10: el lector de la página del día arrastraba los títulos de una votación a la siguiente.
