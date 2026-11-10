# Documento funcional

_Estado comprobado el 2026-11-10 contra el código y una descarga real del 30-09-2026._

## Objetivo

Responder cada mes, con datos oficiales y sin intervención manual, a: **¿qué ha decidido el Pleno del Congreso este mes y cómo ha votado cada grupo y cada diputado?**

Público: cualquier persona que quiera seguir la actividad parlamentaria sin leer los diarios de sesiones (periodistas, ciudadanía, investigadores). El informe tiene que entenderse sin conocer el reglamento del Congreso.

## Alcance

| Incluido | Excluido |
|---|---|
| Votaciones del Pleno y de la Diputación Permanente publicadas en el portal | Votaciones en comisión (el portal no las publica) |
| Legislatura en curso (XV) | Legislaturas X–XIV (posible, no hecho: [BACKLOG](BACKLOG.md)) |
| Voto individual de los 350 escaños | Votaciones secretas (solo totales) |
| Grupo parlamentario de cada diputado en cada votación | Partido o formación electoral ([DA-2](DECISIONS.md)) |

## Qué produce

1. **Datos** en `data/`: un parquet de votaciones y otro de votos por mes, y `dias.json` con el estado de cada día. Esquema en [ARCHITECTURE.md](ARCHITECTURE.md).
2. **Un informe por mes** en `reports/AAAA-MM.md` y un índice en `reports/README.md`.

## Definiciones

Son construcciones del proyecto, no datos oficiales. Cualquier cambio se refleja aquí y en [DECISIONS.md](DECISIONS.md).

| Término | Definición | Decisión |
|---|---|---|
| **Votación nominal** | La que publica el voto de cada diputado. Las secretas y las de asentimiento no lo son. | — |
| **Resultado** | *Aprobada* si Sí > No (mayoría simple). En la votación de conjunto de una ley orgánica, si Sí ≥ 176. Por asentimiento: aprobada. **Calculado**: el portal no publica el resultado. | D-06 |
| **Posición del grupo** | La opción (Sí, No, Abstención) que votaron más diputados del grupo. *Dividido* si hay empate en cabeza; *Sin voto* si no votó nadie. «No vota» no cuenta. | D-05 |
| **Cohesión** | Índice de acuerdo de Hix, Noury y Roland: `(1,5·máx − 0,5·total) / total` sobre los votos emitidos del grupo. 1 = unanimidad; 0 = reparto a tercios. En el informe, la media del mes. | D-07 |
| **Votó con el resultado** | El grupo votó Sí y salió aprobada, o votó No y salió rechazada. Abstenerse nunca cuenta. | — |
| **Decisivo** | Si el grupo se hubiera abstenido en bloque, el resultado habría cambiado. | D-04 |
| **Afinidad** | Proporción de votaciones nominales del mes en que dos grupos tomaron la misma posición (solo cuando ambos tienen Sí, No o Abstención). | — |
| **Voto distinto de su grupo** | Voto emitido distinto de la posición del grupo. No se cuenta en el Grupo Mixto ni cuando el grupo está dividido. | D-05 |
| **No votó** | Voto «No vota». Incluye ausencias justificadas, bajas y escaños vacantes: el portal no las distingue. | — |
| **Ajustada** | Diferencia Sí − No de 10 votos o menos (o distancia a 176 en mayoría absoluta). El resumen cuenta las de 5 o menos. | — |

## Límites que el informe declara

- El resultado es calculado. La heurística de mayoría absoluta (texto con «orgánica» y «conjunto») **no se ha comprobado aún con una votación real** de ley orgánica ([DA-6](DECISIONS.md)).
- «Decisivo» es contrafactual y mecánico: no dice que hubiera negociación ni intención.
- Un voto aislado distinto del grupo puede ser un error al pulsar. El Congreso no publica correcciones.
- La posición del Grupo Mixto es la de su mayoría, que mezcla partidos distintos.
- Los datos llegan con semanas de retraso: el informe de un mes puede salir incompleto y se rehace solo.

## Requisitos y estado

| # | Requisito | Estado |
|---|---|---|
| F-1 | Descubrir los días con votación de la legislatura | **Hecho** (`fuente.dias_con_votacion`) |
| F-2 | Descargar el JSON de cada votación de un día | **Hecho**, probado con datos reales (30-09-2026, 21 votaciones) |
| F-3 | Marcar como pendientes los días sin JSON y reintentarlos | **Hecho** (02-10-2026 sale pendiente) |
| F-4 | Guardar por mes sin duplicar al repetir | **Hecho** (test) |
| F-5 | Informe mensual con las secciones de [DESIGN.md](DESIGN.md) | **Hecho** |
| F-6 | Ejecución mensual en GitHub Actions con commit del resultado | **Escrito, sin probar**: falta crear el repositorio |
| F-7 | Carga histórica de la XV | **Orden lista** (`historico`), sin lanzar |
| F-8 | Resumen en lenguaje natural del mes | Pendiente ([DA-1](DECISIONS.md)) |
| F-9 | Partido dentro del Grupo Mixto | Pendiente ([DA-2](DECISIONS.md)) |
