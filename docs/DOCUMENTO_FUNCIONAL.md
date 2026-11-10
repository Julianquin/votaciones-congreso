# Documento funcional

_Estado comprobado el 2026-11-10 contra el código y descargas reales (30-09-2026, 10-01-2024, 30-01-2024)._

## Objetivo

Responder cada mes, con datos oficiales y sin intervención manual, a: **¿qué ha decidido el Pleno del Congreso este mes y cómo ha votado cada grupo y cada diputado?**

Público: cualquier persona que quiera seguir la actividad parlamentaria sin leer los diarios de sesiones (periodistas, ciudadanía, investigadores). El informe tiene que entenderse sin conocer el reglamento del Congreso.

## Alcance

| Incluido | Excluido |
|---|---|
| Votaciones del Pleno y de la Diputación Permanente publicadas en el portal | Votaciones en comisión (el portal no las publica) |
| Legislatura en curso (XV) | Legislaturas X–XIV (posible, no hecho: [BACKLOG](BACKLOG.md)) |
| Voto individual de los 350 escaños | Voto individual en las secretas y en las públicas por llamamiento (solo totales; [DA-9](DECISIONS.md)) |
| Grupo parlamentario de cada diputado en cada votación | Partido o formación electoral ([DA-2](DECISIONS.md)) |

## Qué produce

1. **Datos** en `data/`: un parquet de votaciones y otro de votos por mes, y `dias.json` con el estado de cada día. Esquema en [ARCHITECTURE.md](ARCHITECTURE.md).
2. **Dos informes por mes**: `reports/AAAA-MM.md`, para cualquier ciudadano, y `reports/AAAA-MM-detalle.md`, técnico. Además, un índice en `reports/README.md` (D-19).

## Definiciones

Son construcciones del proyecto, no datos oficiales. Cualquier cambio se refleja aquí y en [DECISIONS.md](DECISIONS.md).

| Término | Definición | Decisión |
|---|---|---|
| **Votación nominal** | La que publica el voto de cada diputado. Las secretas, las de asentimiento y las públicas por llamamiento no lo son. | — |
| **Votación por llamamiento** | Se vota de viva voz, diputado a diputado (investiduras, leyes orgánicas, reformas constitucionales, repeticiones). Solo hay totales. | D-12 |
| **Resultado** | *Aprobada* si Sí > No, o si Sí alcanza el umbral cuando la votación lo exige: 176 (ley orgánica, Estatuto, Reglamento, investidura) o 210 (reforma constitucional). Por asentimiento: aprobada. **Calculado**: el portal no publica el resultado. | D-06 |
| **Empate** | Sí = No con mayoría simple. Se repite la votación: no es un rechazo. | D-15 |
| **Posición del grupo** | La opción (Sí, No, Abstención) que votaron más diputados del grupo. *Dividido* si hay empate en cabeza; *Sin voto* si no votó nadie. «No vota» no cuenta. | D-05 |
| **Cohesión** | Índice de acuerdo de Hix, Noury y Roland: `(1,5·máx − 0,5·total) / total` sobre los votos emitidos del grupo. 1 = unanimidad; 0 = reparto a tercios. En el informe, la media del mes. | D-07 |
| **Votó con el resultado** | El grupo votó Sí y salió aprobada, o votó No y salió rechazada. Abstenerse nunca cuenta. | — |
| **Decisivo** | Si el grupo se hubiera abstenido en bloque, el resultado habría cambiado. | D-04 |
| **Afinidad** | Proporción de votaciones nominales del mes en que dos grupos tomaron la misma posición (solo cuando ambos tienen Sí, No o Abstención). | — |
| **Voto distinto de su grupo** | Voto emitido distinto de la posición del grupo. No se cuenta en el Grupo Mixto ni cuando el grupo está dividido. | D-05 |
| **No votó** | Voto «No vota». Incluye ausencias justificadas, bajas y escaños vacantes: el portal no las distingue. | — |
| **Ajustada** | Diferencia Sí − No de 10 votos o menos (o a esa distancia del umbral). El resumen cuenta las de 5 o menos. | — |
| **Mapa de diputados** | Dos primeras componentes principales del voto. Cerca = votaron parecido. Los ejes no tienen significado político propio. | D-13 |
| **Mayoría ganadora** | En cada votación nominal aprobada, el conjunto de grupos cuya posición fue Sí. | — |
| **Votación perdida por el Gobierno** | Los grupos del Gobierno (PSOE y Sumar en la XV) votaron lo mismo y salió lo contrario. | D-14 |
| **Tipo de asunto** | Categoría deducida del título del portal. | D-17 |

## Límites que el informe declara

- El resultado es calculado. Las reglas de mayoría se comprobaron con votaciones reales, salvo la segunda votación de investidura ([DA-8](DECISIONS.md)).
- En las votaciones por llamamiento no hay posición de grupo: no entran en cohesión, afinidad, mayorías, Gobierno ni mapa.
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
| F-10 | Votaciones públicas por llamamiento (totales desde el HTML) | **Hecho**, probado con datos reales (10-01-2024: 4 de 12 votaciones) |
| F-11 | Gráficos: hemiciclo de las ajustadas, mapa de calor de afinidad y mapa de diputados, en claro y oscuro | **Hecho** |
| F-12 | Mayorías ganadoras, votaciones perdidas por el Gobierno y tipo de asunto | **Hecho** |
| F-13 | Empates marcados como tales | **Hecho** |
| F-14 | Evolución mes a mes (cohesión y afinidad en el tiempo) | Pendiente |
| F-15 | Informe principal en lenguaje llano con las 5 votaciones más importantes, hemiciclo con título y quién votó qué | **Hecho**; generado para los 34 meses de la XV sin errores |
| F-17 | Carrusel de Instagram del mes (`instagram`) | **Hecho**; ejemplo de septiembre de 2026 revisado a ojo |
| F-18 | Fondo de portada con IA (`notebooks/portada_ia.ipynb`) | **Escrito, sin ejecutar**: el modelo no se ha corrido en esta máquina |
| F-16 | Títulos oficiales en lenguaje llano | **Hecho** para las fórmulas habituales (D-18); el resto se deja tal cual |
