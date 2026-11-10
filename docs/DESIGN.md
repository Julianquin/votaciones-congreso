# Diseño del informe

## Para quién y qué pregunta responde

Para alguien que no sigue el Congreso a diario y quiere saber, en cinco minutos, **qué se decidió el mes pasado y cómo se posicionó cada grupo**. Debe poder leerse en el móvil desde GitHub y sin herramientas.

## Orden de las secciones

De lo general a lo particular. Lo que más se consulta va primero, y la tabla completa, que es lo más largo, al final.

| Sección | Pregunta | Por qué está ahí |
|---|---|---|
| Aviso de pendientes | ¿Está completo este mes? | Antes que cualquier cifra: si faltan días, todo lo demás es provisional |
| Resumen | ¿Qué pasó en una línea? | Volumen, aprobadas/rechazadas, ajustadas y quién votó más con el resultado |
| Cómo votó cada grupo | ¿Quién gana, quién es decisivo, quién está unido? | La tabla central del producto |
| Afinidad entre grupos | ¿Quién vota con quién? | Muestra mayorías de geometría variable sin interpretarlas |
| Votaciones más ajustadas | ¿Dónde se decidió por poco? | Donde un grupo pequeño o una ausencia pesa |
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

## Lo que no hace (todavía)

- **Gráficos.** La afinidad y la cohesión en el tiempo pedirían imagen ([DA-3](DECISIONS.md)).
- **Comparar con el mes anterior.**
- **Resumen en prosa** ([DA-1](DECISIONS.md)).
