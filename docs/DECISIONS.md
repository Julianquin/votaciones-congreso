# Decisiones

Estados: **Vigente**, **Propuesta**, **Sustituida**. Las abiertas van al final como `DA-n`.

## D-01 · Descargar un JSON por votación, no el ZIP de la sesión (Vigente, 2026-11-10)

El ZIP trae PDF, PNG, XML y JSON de todas las votaciones (~4 MB por sesión) y el de la sesión 203 traía solo PNG. Los JSON sueltos pesan ~70 KB y se descubren en la página del día. Son más peticiones (~25 por día), pero cada una es pequeña y sabemos exactamente cuáles faltan.

## D-02 · Analizar por grupo parlamentario, no por partido (Vigente, 2026-11-10)

El JSON de cada votación trae el grupo del diputado en ese momento. Para el partido habría que cruzar con el fichero de diputados, y el de «activos» tenía 137 de 350 diputados el 2026-11-10. El cruce se deja para [DA-2](#da-2--partido-dentro-del-grupo-mixto).

## D-03 · Datos e informes dentro del repositorio (Vigente, 2026-11-10)

Parquet mensual en `data/` y Markdown en `reports/`, con commit del bot. Toda la legislatura cabe en unos pocos MB. GitHub muestra el Markdown sin montar nada más, y el historial de git da trazabilidad: se ve qué cambió cuando el Congreso publicó un día atrasado. Alternativa descartada: un bucket externo (R2, como fr_scraper), que es más infraestructura para un volumen pequeño.

## D-04 · Definición de «decisivo» (Vigente, 2026-11-10)

Un grupo es decisivo en una votación si, de haberse abstenido en bloque, el resultado habría cambiado:

- aprobada por mayoría simple y posición Sí: `a_favor − sus Sí ≤ en_contra`;
- aprobada por mayoría absoluta y posición Sí: `a_favor − sus Sí < 176`;
- rechazada por mayoría simple y posición No: `a_favor > en_contra − sus No`;
- en mayoría absoluta, los No nunca son decisivos.

Se elige la abstención y no el voto contrario porque es el contrafactual más prudente. Varios grupos pueden ser decisivos a la vez.

## D-05 · Posición de grupo por mayoría interna; disidencias sin el Mixto (Vigente, 2026-11-10)

La posición del grupo es la opción más votada por sus diputados. Si dos opciones empatan en cabeza, el grupo está «Dividido» y nadie disiente. El Grupo Mixto (`GMx`) reúne partidos distintos (Podemos, BNG, CC, UPN… en la XV) y su mayoría no expresa disciplina, así que sus votos no cuentan como disidencia (`config.GRUPOS_SIN_DISCIPLINA`). Sí aparece en las tablas de grupos y de afinidad, con la advertencia.

## D-06 · Resultado calculado; mayoría absoluta por heurística (Vigente, 2026-11-10)

El portal da totales pero no dice si la votación salió aprobada. Se aplica mayoría simple (Sí > No), salvo cuando el texto contiene «orgánica» y «conjunto» (votación final de conjunto de una ley orgánica, art. 81 CE): entonces Sí ≥ 176. Ver [DA-6](#da-6--validar-la-heurística-de-mayoría-absoluta).

## D-07 · Cohesión con el índice de acuerdo de Hix, Noury y Roland (Vigente, 2026-11-10)

`AI = (1,5·máx(Sí, No, Abst.) − 0,5·total) / total`. A diferencia del índice de Rice, cuenta la abstención como opción. Es el estándar en el estudio del Parlamento Europeo.

## D-08 · El día 3 de cada mes, reintentando pendientes de 3 meses (Vigente, 2026-11-10)

El informe se hace sobre el mes anterior cerrado. Como el Congreso publica con semanas de retraso, cada corrida vuelve a pedir los días pendientes de los 3 meses previos (`--revisar 3`) y regenera sus informes. Los días completos no se vuelven a pedir.

## D-09 · Commit directo del bot, sin pull request (Vigente, 2026-11-10)

`data/` y `reports/` son salidas deterministas del portal. Revisar un PR cada mes no aporta y retrasa la publicación. El código sí pasa por los tests en cada push.

## D-10 · Cortesía con el portal (Vigente, 2026-11-10)

Una petición por segundo, 4 reintentos con espera creciente solo ante 429 y 5xx, y un User-Agent propio sin datos personales. Un 403 no se reintenta: es un bloqueo y hay que mirarlo.

## D-11 · Sin LLM en la v0.1 (Vigente, 2026-11-10)

El informe es determinista y verificable. El resumen en lenguaje natural queda en [DA-1](#da-1--resumen-del-mes-con-un-llm).

---

## Abiertas

### DA-1 · Resumen del mes con un LLM

Un párrafo que cuente lo más relevante del mes. Hay dos opciones:

- **Ollama local** (`qwen3.6`, preferencia del usuario): no puede correr en los runners de GitHub, que no tienen GPU. Exigiría que el usuario lo lance en su máquina y haga el commit.
- **API de Claude en Actions**, con un secreto `ANTHROPIC_API_KEY`: automático, con un coste pequeño por mes.

En los dos casos hay que pasarle solo las tablas ya calculadas y exigir neutralidad ([DESIGN.md](DESIGN.md)). Decide el usuario.

### DA-2 · Partido dentro del Grupo Mixto

Sirve para separar Podemos, BNG, CC, UPN… dentro del Mixto. Opciones: el fichero de diputados del portal (incompleto hoy), una tabla mantenida a mano en `conf/` o ambos. Hay que fecharla, porque los diputados cambian de grupo.

### DA-3 · Publicación como web

Hoy, Markdown en GitHub. Más adelante: GitHub Pages con gráficos (afinidad como mapa de calor, cohesión en el tiempo).

### DA-4 · Legislaturas anteriores (X–XIV)

El portal las tiene. Exige etiquetas de grupo por legislatura y decidir si se mezclan en el mismo índice.

### DA-5 · Condiciones de reutilización

Hay que confirmar el aviso legal del portal y citar la fuente como pida. Hoy el pie de cada informe cita congreso.es.

### DA-6 · Validar la heurística de mayoría absoluta

Hay que buscar en la carga histórica una votación de conjunto de ley orgánica, ver cómo se rotula de verdad y ajustar `analisis.requiere_mayoria_absoluta`. Hasta entonces el informe marca esas votaciones con «(may. abs.)» para que se vean.

### DA-7 · Si los runners de GitHub no llegan al portal

Plan B, en orden: (1) runner autoalojado en la máquina del usuario; (2) lanzar `mensual` en local y hacer commit, que es lo mismo que ya se hace con otros proyectos; (3) disparador externo, como el de Cloudflare de fr_scraper, solo si fallara por horario.
