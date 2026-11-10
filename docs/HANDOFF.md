# Handoff

_Última actualización: 2026-11-10 (gráficos, votaciones por llamamiento, Gobierno y mayorías)._

## Estado en una frase

En producción en GitHub (`Julianquin/votaciones-congreso`): Actions corrió dos veces y el portal responde desde los runners. Ya están hechos los gráficos y las secciones nuevas del informe. **Falta que la carga histórica termine y una segunda pasada** que recoja las votaciones por llamamiento y regenere todos los informes con los gráficos.

## Qué está hecho y comprobado

- Descarga desde el portal, también desde GitHub Actions. Septiembre de 2026 completo: 8 días, 119 votaciones.
- **Votaciones públicas por llamamiento** leídas del HTML: investiduras, conjunto de leyes orgánicas y repeticiones tras empate (D-12). Probado contra el portal: el 10-01-2024 pasa a completo con 12 votaciones, 4 de ellas por llamamiento. Los totales del HTML coinciden con el JSON en 21 de 21 votaciones.
- Umbral de mayoría por tipo (176, 210 o simple) comprobado con la amnistía y la reforma del art. 49 (D-06). Empates como «se repite» (D-15).
- Gráficos SVG en claro y oscuro: hemiciclo de las 4 votaciones más ajustadas, mapa de calor de afinidad y mapa de diputados (D-13, D-16). Revisados a ojo con enero de 2024 y septiembre de 2026.
- Secciones nuevas: mapa, mayorías ganadoras, votaciones perdidas por el Gobierno y tipo de asunto.
- 32 tests sin red (`make check`, ~1,5 s), con `-W error`. `ruff` limpio.
- matplotlib y numpy añadidos a `requirements.txt`; el lock del entorno único no mueve ningún pin.

## Qué no está comprobado

- Los informes con gráficos solo existen en el scratchpad de la sesión. Los de `reports/` los regenera la segunda pasada.
- Segunda votación de investidura (DA-8).

## Siguientes pasos (los lanza el usuario)

1. Esperar a que termine la carga histórica en curso.
2. Segunda pasada: `../.venv/bin/python -m src.votaciones historico --desde 2023-09`. Solo pide los días incompletos (pocas peticiones) y regenera todos los informes con gráficos.
3. Revisar `reports/` en local y hacer commit y push.

## Cómo retomar

```bash
cd ~/proyectos/votaciones-congreso
make check     # debe dar 32 passed
make sondear   # «Legislatura XV: N días con votación…»
```
