# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## Sin publicar

### Añadido

- 2026-11-10: creación del proyecto.
  - Descarga incremental por día desde el portal de datos abiertos del Congreso, con días pendientes y reintentos (`src/votaciones/fuente.py`, `almacen.py`).
  - Análisis mensual: resultado calculado, posición de cada grupo, cohesión (Hix), afinidad, grupos decisivos, votos distintos del grupo y ausencias (`analisis.py`).
  - Informe mensual en Markdown e índice (`informe.py`).
  - CLI con `sondear`, `actualizar`, `informe`, `mensual` e `historico`.
  - Workflows de GitHub Actions: `mensual.yml` (día 3 de cada mes, con commit del bot) y `tests.yml`.
  - 19 tests sin red y documentación en `docs/`.
