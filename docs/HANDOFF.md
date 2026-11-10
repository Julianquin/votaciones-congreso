# Handoff

_Última actualización: 2026-11-10 (creación del proyecto)._

## Estado en una frase

El código está completo y probado en local con datos reales de un día, pero **todavía no hay repositorio en GitHub, ni datos en `data/`, ni ninguna corrida en Actions**.

## Qué está hecho y comprobado

- Descubrimiento de días, enlaces y descarga contra el portal real: el 30-09-2026 dio 21 votaciones y el 02-10-2026 salió pendiente (solo PNG). La prueba se hizo en una carpeta temporal; `data/` sigue vacío.
- Los totales oficiales cuadran con la suma de votos individuales en las 20 votaciones nominales de ese día.
- El portal acepta el User-Agent propio desde WSL.
- Informe generado con esos datos: secciones, tablas, avisos y enlaces correctos.
- 19 tests sin red (`make check`, menos de 1 s), `ruff` limpio y sin avisos de pandas (`-W error`).
- Proyecto dado de alta en `~/proyectos/entorno/requirements.in`. Se comprobó compilando sobre una copia del lock que **no se mueve ningún pin**.

## Qué no está comprobado

- **Que el portal responda desde los runners de GitHub.** Es el primer riesgo. Plan B en [DA-7](DECISIONS.md).
- La heurística de mayoría absoluta ([DA-6](DECISIONS.md)).
- `mensual` e `historico` de punta a punta: están hechos con funciones probadas, pero no se han lanzado enteros.

## Siguientes pasos (los lanza el usuario)

1. `cd ~/proyectos/entorno && ./instalar.sh --recompilar`: solo cambian comentarios del lock.
2. `git init`, primer commit y crear el repositorio en GitHub.
3. En GitHub: Actions → «Informe mensual» → *Run workflow* con `2026-09`. Si `sondear` falla, ir a DA-7.
4. Carga histórica en local: `../.venv/bin/python -m src.votaciones historico --desde 2023-09` (~1 h), revisar `reports/` y hacer commit.

## Cómo retomar

```bash
cd ~/proyectos/votaciones-congreso
make check     # debe dar 19 passed
make sondear   # «Legislatura XV: N días con votación…»
```
