# Arquitectura

## Estructura

```
votaciones-congreso/
├── src/votaciones/
│   ├── config.py       rutas, URLs, constantes de método, etiquetas de grupo
│   ├── fuente.py       portal del Congreso: calendario, enlaces del día, descarga (única con red)
│   ├── normalizar.py   JSON de una votación -> fila de votación + filas de votos
│   ├── almacen.py      parquet mensual, sustitución por día, manifiesto dias.json
│   ├── analisis.py     umbral, posiciones, cohesión, decisivos, afinidad, mapa (PCA),
│   │                   mayorías, Gobierno, categorías, disidencias, ausencias
│   ├── graficos.py     hemiciclo, barra de resultado, barras, mapa de calor y mapa de
│   │                   diputados (SVG claro y oscuro)
│   ├── lenguaje.py     títulos en lenguaje llano, explicación de cada tipo y glosario
│   ├── informe.py      informe principal, informe detallado e índice
│   ├── instagram.py    carrusel 1080 × 1350 y texto de la publicación (D-20)
│   └── cli.py          órdenes sondear / actualizar / informe / mensual / historico
├── tests/              sin red; JSON sintético con la forma real del portal
├── data/               lo escribe el bot (en git)
│   ├── votaciones/AAAA-MM.parquet
│   ├── votos/AAAA-MM.parquet
│   └── dias.json
├── reports/            lo escribe el bot (en git): AAAA-MM.md (principal), AAAA-MM-detalle.md,
│                       README.md e img/AAAA-MM/*.svg (~0,9 MB por mes)
├── social/             carruseles de Instagram (fuera de git)
├── notebooks/          portada_ia.ipynb: fondo de portada con Qwen-Image (lo lanza el usuario)
├── .github/workflows/  mensual.yml (cron) y tests.yml (push/PR)
└── docs/
```

## Flujo

```mermaid
flowchart TD
    subgraph Portal["congreso.es/es/opendata/votaciones"]
        P1["Página de la legislatura<br/>var diasVotaciones = [...]"]
        P2["Página del día<br/>&targetDate=dd/mm/aaaa"]
        P3["VOT_marca.json<br/>(uno por votación)"]
    end
    P1 -->|fuente.dias_con_votacion| D{¿Día completo<br/>en dias.json?}
    D -->|sí| S[Saltar]
    D -->|no o pendiente| P2
    P2 -->|fuente.leer_enlaces| E{¿Tiene JSON?}
    E -->|no, y es por llamamiento| H[normalizar_html:<br/>totales de la página]
    E -->|no, otra| M[dias.json: completo = false]
    E -->|sí| P3
    H --> A
    P3 -->|normalizar| A[almacen.guardar_dia]
    A --> PQ[(data/votaciones y data/votos)]
    A --> M2[dias.json: completo = true]
    PQ -->|analisis.analizar| I[informe.escribir]
    M -->|aviso de días pendientes| I
    I -->|graficos.generar_mes| G[reports/img/AAAA-MM/*.svg]
    I --> R[reports/AAAA-MM.md + README.md]
```

## El portal (comprobado el 2026-11-10)

No hay API: es una página Liferay con un calendario.

| Qué | Cómo |
|---|---|
| Días con votación | `GET /es/opendata/votaciones` → en el JavaScript, `var diasVotaciones = [20230919, …]`. Con `?p_p_id=votaciones&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&targetLegislatura=XV`, los de esa legislatura |
| Legislatura actual | `var idCurrentLegislatura = 15` en la misma página |
| Votaciones de un día | La misma URL con `&targetDate=30/09/2026`. Enlaza `/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion001/VOT_20260930153547.json` (y `.xml`, `.png`, `.pdf`) |
| Un ZIP por sesión | `…/Sesion202/20260930/VOT_….zip`, con JSON, XML, PDF y PNG de todas (~4 MB). **No se usa** (D-01) |
| Diputados | `/es/opendata/diputados` → `DiputadosActivos__<marca>.json` con `FORMACIONELECTORAL`. **Incompleto** el 2026-11-10: 137 de 350 |

Las marcas de tiempo de los nombres no son predecibles: siempre hay que leer la página del día.

**Estructura de la página de un día** (la usa `fuente.leer_enlaces`): `h4` = tipo de asunto («PUNTO UNICO. Dictámenes de…», «III. Mociones…»), `h5` = expediente y, si lo hay, subgrupo, `h6` = detalle; después `<p>Si: 171</p><p>No: 179</p><p>Abstenciones: 0</p>`, el enlace «Detalle» (PDF o Diario de Sesiones) y los ficheros de `VotacionNNN/`. Tras una votación, un `h5` nuevo sustituye al último, no se acumula. Los totales del HTML coinciden con los del JSON en las 21 votaciones del 30-09-2026.

**Votaciones por llamamiento.** El texto dice «(Pública por llamamiento)». No tienen JSON, solo PNG, y nunca lo tendrán: la investidura del 27-09-2023 sigue así en noviembre de 2026. Ver D-12.

**Retraso de publicación.** El 10-11-2026 el calendario marcaba el 02-10-2026 como día con votaciones, pero solo había PNG. El JSON del 30-09 sí estaba.

**Volumen.** La XV tenía 147 días con votación hasta el 02-10-2026 y unas 20–30 votaciones por día. La carga completa son unas 3.900 peticiones (~1 h con la pausa de 1 s). En parquet, los votos de un día ocupan ~17 KB.

## Esquema de datos

**`data/votaciones/AAAA-MM.parquet`**: una fila por votación.

| Columna | Tipo | Nota |
|---|---|---|
| `votacion_id` | str | `L15-S202-V001` |
| `legislatura`, `sesion`, `numero` | int | |
| `fecha` | date | La de la carpeta del portal |
| `titulo` | str | Tipo de asunto: «Proposiciones no de Ley», «Mociones consecuencia de interpelaciones urgentes»… |
| `titulo_subgrupo`, `texto_subgrupo` | str | P. ej. «Votación separada por puntos.» / «Punto 1.» |
| `texto_expediente` | str | El asunto en sí |
| `asentimiento` | bool | |
| `presentes`, `a_favor`, `en_contra`, `abstenciones`, `no_votan` | int | Totales oficiales. Cuadran con la suma de votos individuales (comprobado con 20 votaciones) |
| `conjuntas` | int | Nº de votaciones conjuntas que trae el JSON |
| `llamamiento` | bool | Pública por llamamiento: sin votos individuales, totales del HTML. Los parquet anteriores al 2026-11-10 no la traen; `almacen` la rellena con False |
| `url` | str | JSON de origen o, si es por llamamiento, Diario de Sesiones |

**`data/votos/AAAA-MM.parquet`**: una fila por diputado y votación nominal: `votacion_id`, `fecha`, `asiento`, `diputado` («Apellidos, Nombre»), `grupo` (código: `GP`, `GS`, `GVOX`, `GSUMAR`, `GMx`, `GJxCAT`, `GR`, `GEH Bildu`, `GV (EAJ-PNV)`) y `voto` («Sí», «No», «Abstención», «No vota»).

**`data/dias.json`**: `{"2026-09-30": {"legislatura": 15, "votaciones": 21, "sin_json": 0, "completo": true, "comprobado": "…"}}`.

## GitHub Actions

```mermaid
sequenceDiagram
    participant Cron as cron (día 3, 07:00 UTC)
    participant Job as Job «informe»
    participant Portal as congreso.es
    participant Repo as Repositorio
    Cron->>Job: lanza (o workflow_dispatch con mes)
    Job->>Portal: sondear (1 petición)
    Job->>Portal: mensual: mes anterior + días pendientes de los 3 meses previos
    Job->>Job: regenera informes de los meses tocados + índice
    Job->>Repo: commit «datos: …» si cambió algo, pull --rebase, push
```

- `permissions: contents: write` para el commit con `GITHUB_TOKEN`.
- `concurrency` evita dos corridas a la vez.
- El paso `sondear` falla con código 2 si el portal no responde o cambia de formato. GitHub avisa por correo al dueño del repo cuando falla un workflow programado.
- GitHub desactiva los workflows programados de un repo **público** tras 60 días sin actividad. El commit mensual del bot cuenta como actividad, salvo que haya meses sin cambios seguidos.
