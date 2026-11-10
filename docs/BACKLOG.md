# Backlog

Cada tarea dice quién la desbloquea.

## Ahora

- [ ] Terminar la carga histórica y lanzar la segunda pasada (`historico --desde 2023-09`), que recoge las votaciones por llamamiento y regenera los informes con gráficos. Después, commit de `data/` y `reports/`: **usuario**.

## Siguiente

- [ ] Resumir el contenido de cada votación destacada en una frase llana («Pide bajar el IRPF por la inflación»). Las reglas de D-18 solo quitan fórmulas; esto pide un LLM ([DA-1](DECISIONS.md)): **usuario** elige.
- [ ] Evitar que una misma reforma ocupe varias destacadas (noviembre de 2023: cuatro votaciones de la reforma del Reglamento con textos distintos): **agente**.

- [ ] **Evolución en el tiempo**: informe de la legislatura con la cohesión de cada grupo mes a mes y la afinidad de pares clave (Junts–PSOE, Junts–PP, PNV–PSOE) a lo largo de la XV: **agente**, con la carga histórica.
- [ ] Mapa de diputados de toda la legislatura (más votaciones, más fiable que el mensual): **agente**.
- [ ] Voto individual de las votaciones por llamamiento desde el Diario de Sesiones ([DA-9](DECISIONS.md)): **agente**.
- [ ] Segunda votación de investidura ([DA-8](DECISIONS.md)): **agente**.
- [ ] Resumen del mes en prosa ([DA-1](DECISIONS.md)): **usuario** elige Ollama local o API de Claude.
- [x] ~~Validar la heurística de mayoría absoluta~~ (2026-11-10, D-06).
- [x] ~~Etiquetar las votaciones por tipo~~ (2026-11-10, D-17).
- [x] ~~Gráficos en el informe~~ (2026-11-10, D-16).

## Más adelante

- [ ] Partido dentro del Grupo Mixto ([DA-2](DECISIONS.md)): **usuario** decide la fuente.
- [ ] Web en GitHub Pages: buscador por diputado y votación, hemiciclo con detalle al pasar el ratón ([DA-3](DECISIONS.md)).
- [ ] Legislaturas X–XIV ([DA-4](DECISIONS.md)): etiquetas de grupo por legislatura.
- [ ] Aviso del informe nuevo por Telegram, como el monitor de fr_scraper: **usuario** da el bot y el chat.
- [ ] Enlazar cada votación con su iniciativa en el Congreso: el JSON no trae el número de expediente; habría que buscarlo por texto.

## Ideas

- Ficha por diputado: su historial de votos distintos de su grupo y de ausencias.
- Votaciones sobre el mismo asunto en distintas fases (totalidad → dictamen → conjunto).
