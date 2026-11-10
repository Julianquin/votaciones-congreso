# Diseño del informe

## Para quién y qué pregunta responde

Para **cualquier ciudadano** que no sigue el Congreso y quiere saber, en cinco minutos, **qué se decidió el mes pasado y quién votó qué**. Tiene que entenderse sin saber qué es una «toma en consideración» y poder leerse en el móvil desde GitHub. Para quien quiera más hay un segundo informe técnico (D-19).

## Informe principal (`reports/AAAA-MM.md`)

Cada sección es una pregunta que se haría cualquiera:

| Sección | Qué lleva |
|---|---|
| En pocas palabras | 4–5 frases: cuántas veces se votó y cuánto salió; cuántas eran leyes y cuántas peticiones que no obligan; cuántas perdió el Gobierno; la más reñida; si los diputados votan con su grupo |
| Las votaciones más importantes del mes | 5, una por asunto (D-19). Cada una con: título en lenguaje llano (D-18); fecha, tipo y qué significa ese tipo en una frase; hemiciclo con título propio, que se entiende aunque se comparta la imagen sola, o barra de 350 escaños si fue por llamamiento; «✔ Salió adelante por 2 votos»; quién votó a favor, en contra, se abstuvo o se repartió |
| ¿Qué grupos votaron más veces lo que finalmente salió? | Barras horizontales, de mayor a menor, con el porcentaje escrito |
| ¿Quién vota con quién? | Mapa de calor con el número en cada casilla |
| ¿Qué tipo de cosas se votaron? | Tabla con una columna «Qué es» |
| Palabras que conviene saber | Glosario de 7 términos |

Reglas de redacción propias de este nivel: frases cortas; «salió adelante» y no «aprobada»; «no votó» y no «no vota»; nada de siglas sin explicar salvo las de los partidos; ningún porcentaje sin decir de qué es.

## Informe detallado (`reports/AAAA-MM-detalle.md`)

De lo general a lo particular. La tabla completa, que es lo más largo, va al final.

| Sección | Pregunta | Por qué está ahí |
|---|---|---|
| Aviso de pendientes | ¿Está completo este mes? | Antes que cualquier cifra: si faltan días, todo lo demás es provisional |
| Resumen | ¿Qué pasó en una línea? | Volumen, aprobadas/rechazadas, ajustadas y quién votó más con el resultado |
| Cómo votó cada grupo | ¿Quién gana, quién es decisivo, quién está unido? | La tabla central del producto |
| Mapa de diputados | ¿Cómo se agrupa de verdad el Congreso? | Bloques, diputados que van por libre y el Mixto partido, sin imponer ideología |
| Afinidad entre grupos | ¿Quién vota con quién? | Mapa de calor, con la tabla desplegable como vista accesible |
| Quién sacó adelante las votaciones | ¿Con qué socios se aprueban las cosas? | La geometría variable de la legislatura, en una tabla |
| Votaciones que perdieron los grupos del Gobierno | ¿Dónde perdió el Gobierno? | Con el tipo de asunto, para separar leyes de PNL |
| Votaciones más ajustadas | ¿Dónde se decidió por poco? | Hemiciclo de las 4 más ajustadas: se ve quién decidió y quién faltó |
| Qué se votó, por tipo | ¿Qué clase de asuntos pasan o no? | Distingue PNL y mociones (no vinculantes) de leyes y convalidaciones |
| Votos distintos de su grupo | ¿Quién rompió la disciplina? | Con la advertencia del error al pulsar |
| Diputados que más veces no votaron | ¿Quién faltó? | Con la advertencia de bajas y vacantes |
| Todas las votaciones | El detalle, día a día | Cada número enlaza al JSON oficial: el informe se puede verificar entero |

## Criterios de redacción

- **Describir, no valorar.** «El PP y Vox votaron Sí; el PSOE votó No», y no «el PSOE bloqueó». Nada de adjetivos sobre grupos ni personas.
- **Ninguna causa.** El informe no sabe por qué alguien votó algo.
- **Cada métrica con su definición al pie de su tabla**, en una frase. La definición formal está en [DOCUMENTO_FUNCIONAL.md](DOCUMENTO_FUNCIONAL.md).
- **El resultado es calculado** y la mayoría absoluta se marca con «(may. abs.)». Las secretas, con «(secreta)».
- **Nombres de grupo cortos y conocidos** (PP, PSOE, Vox, Sumar, ERC, Junts, Bildu, PNV, Mixto), ordenados por tamaño, siempre en el mismo orden en todas las tablas.
- **Asuntos recortados a 160 caracteres** con «…». El texto completo está en el JSON enlazado.
- Porcentajes sin decimales, con espacio antes de «%».

## Formato

- Markdown de GitHub, con el bloque `> [!WARNING]` para los días pendientes.
- Las barras `|` y los saltos de línea del texto oficial se escapan para no romper las tablas (hay un test).
- Un mes sin plenos (agosto) también tiene informe, de una línea, para que no parezca que la automatización se paró.

## Gráficos

| Gráfico | Forma | Por qué |
|---|---|---|
| Hemiciclo | 350 puntos en semicírculo, un hueco entre grupos, color = voto; título y fecha arriba; «✔ Aprobada» y la regla («Hacían falta más síes que noes») en el centro | Es como se ve el Congreso y lo que mejor entiende cualquiera |
| Barra de resultado | 350 escaños en una barra (Sí, No, abstención, no votó) con la marca de los 176 | Para las votaciones por llamamiento, que no tienen voto por diputado |
| Votaron lo que salió | Barras horizontales de un solo color, ordenadas, con el valor escrito | La comparación más sencilla posible entre grupos |
| Afinidad | Mapa de calor del triángulo inferior, rampa de un solo tono, número en cada celda | Magnitud = rampa secuencial; el número evita depender del color |
| Mapa de diputados | Paneles pequeños, uno por grupo, resaltado sobre el resto en gris; el área del punto crece con los diputados que coinciden | 9 colores de grupo no se distinguen en dispersión; los diputados que votan igual caen en el mismo punto |

Colores, formato y peso en [D-16](DECISIONS.md). Los grupos van ordenados por el eje 1 del mapa (D-13) en los tres gráficos, y por tamaño en las tablas.

## Lo que no hace (todavía)

- **Evolución en el tiempo** de la cohesión y la afinidad ([BACKLOG](BACKLOG.md)).
- **Comparar con el mes anterior.**
- **Resumen en prosa** ([DA-1](DECISIONS.md)).
