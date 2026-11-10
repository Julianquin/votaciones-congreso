# AGENTS.md: instrucciones para agentes de IA

Este archivo es para agentes (Claude Code, Codex, Cursor…) que trabajen en este repositorio. Las personas deben empezar por [README.md](README.md).

## Antes de tocar nada

**Toda la documentación está en [docs/](docs/).** En la raíz solo quedan `README.md` y este archivo.

1. Lee [HANDOFF.md](docs/HANDOFF.md): dice en qué estado quedó el trabajo.
2. Dónde está cada cosa: [ARCHITECTURE.md](docs/ARCHITECTURE.md). El porqué: [DECISIONS.md](docs/DECISIONS.md). No reabras una decisión sin un motivo nuevo.
3. Qué debe hacer el sistema y qué está hecho de verdad: [DOCUMENTO_FUNCIONAL.md](docs/DOCUMENTO_FUNCIONAL.md).
4. Escribe siempre **en español**: código, comentarios, mensajes de la CLI y documentación.
5. **Todo diagrama de flujo va en Mermaid**, nunca en ASCII. Los árboles de directorios pueden ir en texto.

## Qué no se negocia

- **Neutralidad política.** Los informes describen cómo se votó, no valoran. Nada de adjetivos sobre grupos o diputados («traición», «rebelde», «bloqueo»), nada de atribuir intenciones y nada de lenguaje causal («X votó no porque…»). La redacción está en [DESIGN.md](docs/DESIGN.md).
- **Cada cifra con su definición.** Cohesión, afinidad, decisivo y disidencia son construcciones del proyecto, no datos oficiales. Si cambias una, cambia también su definición en `DOCUMENTO_FUNCIONAL.md` y su entrada en `DECISIONS.md`.
- **El resultado de una votación es calculado.** El portal no lo publica. No lo presentes como oficial.
- **Los juicios se declaran.** Qué grupos se excluyen de las disidencias, qué mayoría se aplica o qué margen cuenta como «ajustado» están en `src/votaciones/config.py`, en constantes del informe o en `DECISIONS.md`, nunca escondidos en el código.
- **data/ y reports/ los escribe el bot.** No los edites a mano: se regeneran desde el portal.

## Entorno

- Hay **un solo entorno Python** para todo `~/proyectos`: `~/proyectos/.venv` (Python 3.12). **No crees un venv propio del proyecto.**
- **Nunca uses `pip install` suelto.** Para añadir una dependencia:
  1. Añádela a [requirements.txt](requirements.txt). `~/proyectos/entorno/requirements.in` lo incluye con `-r`.
  2. Antes de instalar, compila el lock en un archivo aparte **partiendo de una copia del lock actual** y compáralo. **No puede moverse ningún pin existente** (`torch`, `transformers==4.57.3`, `huggingface-hub==0.36.2`, `anthropic==1.15.0`).
  3. `cd ~/proyectos/entorno && ./instalar.sh --recompilar` (lo lanza el usuario).
- GitHub Actions instala `requirements.txt` directamente, sin lock: mantén las cotas inferiores realistas.
- `make` usa `../.venv/bin/python` sin activar nada.

## Qué puedes ejecutar y qué no

El usuario lanza él los procesos largos y hace él los commits. Tú le pasas los comandos listos para copiar, sin líneas `Co-Authored-By`.

**Puedes ejecutar tú:**
- `make check` (lint + tests: sin red, menos de 1 s).
- `make sondear` (1 petición al portal).
- `actualizar --dia AAAA-MM-DD` contra el portal **solo redirigiendo `config.DATOS`, `config.INFORMES` y `config.MANIFIESTO` a una carpeta temporal**, para no ensuciar `data/`. Son ~25 peticiones.
- `informe --mes AAAA-MM`: no toca la red.

**Los lanza el usuario:**
- `historico` (carga inicial: ~3.900 peticiones, ~1 h).
- `mensual` o `actualizar --mes` contra `data/` real.
- Cualquier `git add`, `git commit` o `git push`.

## Trampas

**Portal:**
- Los ficheros se llaman `VOT_<marca de tiempo>.json` y la marca **no se puede adivinar**: hay que leer la página del día. Detalle en [ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Un día puede salir en el calendario sin JSON (solo PNG) durante semanas. Eso es «pendiente», no «sin votaciones». No lo borres del manifiesto.
- Algunos JSON traen BOM: leer con `utf-8-sig` (`fuente.descargar_json` ya lo hace).
- Las votaciones secretas (suplicatorios) traen totales pero `votaciones: []`. Cuentan como votación, no como nominal.
- Las **públicas por llamamiento** (investiduras, conjunto de leyes orgánicas, repeticiones tras empate) no tienen JSON nunca. Se leen del HTML del día (D-12). Si cambias `fuente.leer_enlaces`, prueba con el test `HTML_DIA` y con una página real.
- Un empate con mayoría simple **no es un rechazo**: se repite (D-15).
- El fichero de diputados «activos» del portal estaba incompleto el 2026-11-10 (137 de 350). No te fíes de él para cruzar partidos sin comprobar la cobertura.

**Datos:**
- `almacen.guardar_dia` sustituye todo el día. Si un día vuelve sin votaciones (portal caído a medias), **no escribe nada**, a propósito: así no se borran datos buenos.
- Los códigos de grupo cambian entre legislaturas. Un código sin etiqueta en `config.ETIQUETAS_GRUPO` sale tal cual en el informe.
- `fecha` vuelve de parquet como `datetime.date` porque `almacen._leer` la convierte. Si lees los parquet por tu cuenta, conviértela tú.

**Lenguaje llano** (`lenguaje.py`, D-18):
- Solo se quitan fórmulas administrativas y se acortan nombres de grupo. **Nunca** se resume ni se reinterpreta el contenido de una iniciativa: lo que no encaja en una fórmula se deja como está.
- Los grupos de una fórmula se limitan a nombres de grupo reales (`lenguaje.G`). Si los abres a «cualquier cosa antes de una coma», se rompen títulos como el de la amnistía.
- Las explicaciones de cada tipo (`EXPLICACIONES`) y el glosario son afirmaciones sobre el reglamento: si cambias una, comprueba que sigue siendo cierta.

**Gráficos:**
- Los colores de Sí/No no pueden ser azul/rojo (D-16). Si tocas la paleta, pásala por el validador de la guía de visualización.
- Los SVG deben ser deterministas: hay un test que genera dos veces y compara bytes. No metas fechas ni aleatoriedad.
- El signo de los ejes del mapa es una convención (PP a la derecha). No escribas que el eje 1 «es» izquierda-derecha.

**GitHub Actions:**
- El portal responde desde los runners de GitHub (comprobado el 2026-11-10).
- El mes de entrada del `workflow_dispatch` pasa por variable de entorno y `almacen.validar_mes`. No lo interpoles en el script de shell.
