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

## D-06 · Resultado calculado con umbral por tipo de votación (Vigente, revisada el 2026-11-10)

El portal da totales pero no dice si la votación salió aprobada. `analisis.umbral_mayoria` aplica:

| Caso (por el texto de la votación) | Necesita |
|---|---|
| «conjunto» + reforma constitucional o «reforma del artículo N de la Constitución» (art. 167 CE) | Sí ≥ 210 (3/5) |
| «conjunto» + ley orgánica («Proyecto/Proposición de Ley Orgánica», «…, Orgánica de», «carácter orgánico»), Estatuto de Autonomía o Reglamento del Congreso | Sí ≥ 176 |
| Investidura (art. 99 CE) | Sí ≥ 176 (ver [DA-8](#da-8--segunda-votación-de-investidura)) |
| Todo lo demás | Sí > No |

Se comprobó con casos reales de la XV: la votación de conjunto de la amnistía (30-01-2024, 171–179) y la de la reforma del artículo 49. La primera versión buscaba «orgánica» en cualquier parte y marcaba como orgánicas leyes ordinarias que *modifican* una orgánica; hay un test que lo impide.

## D-12 · Las votaciones públicas por llamamiento se leen del HTML (Vigente, 2026-11-10)

Investiduras, votaciones de conjunto de leyes orgánicas, reformas constitucionales y algunas repeticiones tras empate se votan por llamamiento. El portal **no publica JSON de ellas nunca** (solo PNG), pero la página del día trae su título y sus totales. Se guardan como votaciones no nominales con `llamamiento = True` y `url` al Diario de Sesiones, donde consta el voto de cada diputado. Sin esto faltaban justo las votaciones más importantes de la legislatura, y los días quedaban «pendientes» para siempre. «No votan» se deduce (350 − votos emitidos).

## D-13 · Mapa de diputados por componentes principales (Vigente, 2026-11-10)

Matriz diputado × votación (Sí 1, No −1, Abst. 0, sin voto = media de la votación), sin votaciones unánimes, y dos primeras componentes principales. Se sitúa a quien votó en al menos la mitad. Es la versión más simple y transparente de los «puntos ideales» (NOMINATE, W-NOMINATE): no impone una escala izquierda-derecha. El signo de un eje es arbitrario: se orienta para que el PP quede en positivo y el dibujo no se dé la vuelta de un mes a otro. El mismo eje 1 ordena los grupos en el hemiciclo y en el mapa de calor, así que **ese orden sale de los datos**, no de una clasificación ideológica.

## D-14 · Grupos del Gobierno declarados por legislatura (Vigente, 2026-11-10)

`config.GOBIERNO = {15: ("GS", "GSUMAR")}`. Una votación la «pierden los grupos del Gobierno» si todos votaron lo mismo (Sí o No) y salió lo contrario. Si votan distinto entre sí, se cuenta aparte. Solo votaciones nominales.

## D-15 · Empates (Vigente, 2026-11-10)

Con mayoría simple, un empate obliga a repetir la votación (art. 88 del Reglamento). Se muestra como «Empate (se repite)», no cuenta como rechazada en el resumen ni como derrota del Gobierno. La repetición es otra votación (a menudo por llamamiento) con su propio resultado.

## D-16 · Gráficos en SVG, en claro y oscuro, y con colores no partidistas (Vigente, 2026-11-10)

- **Sí en verde azulado, No en naranja, abstención en gris.** Nunca azul/rojo: en España se leen como PP/PSOE. Paleta validada con el validador de la guía de visualización (Sí–No ΔE 13,8 en daltonismo, por encima del objetivo de 8).
- Cada gráfico en dos versiones y servido con `<picture>`: GitHub muestra la oscura a quien lee en tema oscuro.
- SVG con texto como texto (3–4 veces más ligero) y deterministas (sin fecha, sal de identificadores fija). Regenerar un informe sin cambios no produce diffs. Peso: ~0,6–1 MB por mes.
- El mapa usa paneles pequeños, uno por grupo resaltado sobre el resto en gris, en vez de 9 colores en un solo gráfico: 9 colores de grupo no se distinguen en un diagrama de dispersión.

## D-17 · Categorías de asunto declaradas (Vigente, 2026-11-10)

`config.CATEGORIAS` traduce el título del portal a 11 categorías («Decretos-ley», «Leyes: toma en consideración», «Proposiciones no de ley»…). El informe avisa de que PNL y mociones no obligan al Gobierno.

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

### DA-6 · Validar la heurística de mayoría absoluta (resuelta el 2026-11-10)

Resuelta en D-06 con casos reales. Queda abierta la segunda votación de investidura (DA-8).

### DA-8 · Segunda votación de investidura

Tras una primera votación fallida, la segunda (48 horas después) exige solo mayoría simple. El portal no la distingue con fiabilidad: «(Continuación)» aparece también en primeras votaciones, como la de Sánchez del 16-11-2023. Hoy se aplica 176 a toda investidura. En la XV da el resultado correcto (Feijóo 172 dos veces, Sánchez 179), pero una segunda votación ganada por mayoría simple saldría «rechazada». Solución posible: detectar dos investiduras del mismo candidato en días distintos.

### DA-9 · Posición de los grupos en las votaciones por llamamiento

Hoy solo hay totales. El voto de cada diputado está en el Diario de Sesiones (PDF). Leerlo permitiría tratarlas como nominales: investiduras, leyes orgánicas y repeticiones tras empate, que son las más relevantes.

### DA-7 · Si los runners de GitHub no llegan al portal

Plan B, en orden: (1) runner autoalojado en la máquina del usuario; (2) lanzar `mensual` en local y hacer commit, que es lo mismo que ya se hace con otros proyectos; (3) disparador externo, como el de Cloudflare de fr_scraper, solo si fallara por horario.
