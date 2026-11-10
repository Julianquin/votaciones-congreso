# Backlog

Cada tarea dice quién la desbloquea.

## Ahora

- [ ] Recompilar el lock del entorno único (`./instalar.sh --recompilar`): **usuario**.
- [ ] Crear el repositorio en GitHub y subir el código: **usuario**.
- [ ] Lanzar «Informe mensual» a mano con `2026-09` y comprobar que el portal responde desde GitHub: **usuario**. Si no responde, ver [DA-7](DECISIONS.md).
- [ ] Carga histórica de la XV (`historico --desde 2023-09`, ~1 h) y commit de `data/` y `reports/`: **usuario**.

## Siguiente

- [ ] Validar la heurística de mayoría absoluta con una votación real de ley orgánica ([DA-6](DECISIONS.md)): **agente**, tras la carga histórica.
- [ ] Comparar con el mes anterior: cohesión y afinidad que suben o bajan: **agente**.
- [ ] Resumen del mes en prosa ([DA-1](DECISIONS.md)): **usuario** elige Ollama local o API de Claude.
- [ ] Etiquetar las votaciones por tipo con más detalle a partir de `texto_expediente` (proyecto de ley, proposición de ley, real decreto-ley, PNL, moción, enmienda a la totalidad): **agente**.

## Más adelante

- [ ] Partido dentro del Grupo Mixto ([DA-2](DECISIONS.md)): **usuario** decide la fuente.
- [ ] Web en GitHub Pages con gráficos ([DA-3](DECISIONS.md)).
- [ ] Legislaturas X–XIV ([DA-4](DECISIONS.md)): etiquetas de grupo por legislatura.
- [ ] Aviso del informe nuevo por Telegram, como el monitor de fr_scraper: **usuario** da el bot y el chat.
- [ ] Enlazar cada votación con su iniciativa en el Congreso: el JSON no trae el número de expediente; habría que buscarlo por texto.

## Ideas

- Ficha por diputado: su historial de votos distintos de su grupo y de ausencias.
- Mayorías: qué combinaciones de grupos sacan adelante las votaciones aprobadas.
- Votaciones sobre el mismo asunto en distintas fases (totalidad → dictamen → conjunto).
