# Handoff

_Última actualización: 2026-11-10 (informe principal para cualquier ciudadano)._

## Estado en una frase

En producción en GitHub (`Julianquin/votaciones-congreso`), con la XV completa en `data/` (34 meses, ninguno pendiente). El informe se rehízo en dos niveles: uno principal para cualquier ciudadano y otro detallado (D-19). **Falta regenerar `reports/` con el código nuevo y hacer commit.**

## Qué está hecho y comprobado

- Descarga desde el portal, también desde GitHub Actions. Septiembre de 2026 completo: 8 días, 119 votaciones.
- **Votaciones públicas por llamamiento** leídas del HTML: investiduras, conjunto de leyes orgánicas y repeticiones tras empate (D-12). Probado contra el portal: el 10-01-2024 pasa a completo con 12 votaciones, 4 de ellas por llamamiento. Los totales del HTML coinciden con el JSON en 21 de 21 votaciones.
- Umbral de mayoría por tipo (176, 210 o simple) comprobado con la amnistía y la reforma del art. 49 (D-06). Empates como «se repite» (D-15).
- Gráficos SVG en claro y oscuro: hemiciclo de las 4 votaciones más ajustadas, mapa de calor de afinidad y mapa de diputados (D-13, D-16). Revisados a ojo con enero de 2024 y septiembre de 2026.
- Secciones nuevas: mapa, mayorías ganadoras, votaciones perdidas por el Gobierno y tipo de asunto.
- Informe principal en lenguaje llano (D-18, D-19), generado para los 34 meses sin errores (29 s, ~30 MB de SVG en total). Revisados a mano septiembre de 2026, enero de 2024 (amnistía y empates) y noviembre de 2023 (investidura).
- 43 tests sin red (`make check`, ~1,5 s), con `-W error`. `ruff` limpio.
- matplotlib y numpy añadidos a `requirements.txt`; el lock del entorno único no mueve ningún pin.

## Qué no está comprobado

- Segunda votación de investidura (DA-8).

## Siguientes pasos (los lanza el usuario)

1. `../.venv/bin/python -m src.votaciones informe`: regenera los 34 meses sin red (~30 s). Borra los `hemiciclo-*.svg` antiguos.
2. Revisar un mes en `reports/` y hacer commit con `git add -A reports`, para que entren también los borrados.

## Cómo retomar

```bash
cd ~/proyectos/votaciones-congreso
make check     # debe dar 43 passed
make sondear   # «Legislatura XV: N días con votación…»
```
