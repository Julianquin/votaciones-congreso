"""Rutas, URLs y parámetros fijos del proyecto.

Los juicios de método (qué cuenta como «disidencia», qué grupos se excluyen, qué
mayoría se aplica) están aquí y en docs/DECISIONS.md, no escondidos en el código.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
INFORMES = RAIZ / "reports"
MANIFIESTO = DATOS / "dias.json"

# --- Portal de datos abiertos del Congreso -----------------------------------------------
BASE = "https://www.congreso.es"
URL_VOTACIONES = f"{BASE}/es/opendata/votaciones"
# El portlet de Liferay que pinta el calendario; se le añade &targetLegislatura=XV
# y, para un día concreto, &targetDate=dd/mm/aaaa (así lo hace el JavaScript de la página).
URL_PORTLET = f"{URL_VOTACIONES}?p_p_id=votaciones&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"

# Sin datos personales: el portal no pide identificarse y no hace falta dar un correo.
USER_AGENT = "votaciones-congreso/0.1 (analisis de datos abiertos del Congreso)"
PAUSA = 1.0  # segundos entre peticiones
REINTENTOS = 4
TIMEOUT = 40

# --- Método ------------------------------------------------------------------------------
ZONA = "Europe/Madrid"
DIPUTADOS = 350
MAYORIA_ABSOLUTA = 176  # ley orgánica (art. 81 CE), investidura (art. 99 CE): D-06
TRES_QUINTOS = 210  # reforma constitucional (art. 167 CE): D-06

MARGEN_AJUSTADA = 10  # votos de diferencia (o de distancia al umbral) para «ajustada»

VOTOS_EMITIDOS = ("Sí", "No", "Abstención")
NO_VOTA = "No vota"

# El Grupo Mixto junta partidos distintos: su «posición de grupo» no expresa disciplina,
# así que no se cuentan disidencias dentro de él (D-05).
GRUPOS_SIN_DISCIPLINA = ("GMx",)

# Grupos que forman el Gobierno en cada legislatura (D-14). Es un juicio declarado: el
# informe cuenta «derrotas del Gobierno» cuando todos ellos votan igual y pierden.
GOBIERNO = {15: ("GS", "GSUMAR")}

# Mapa de diputados (D-13): grupo que se orienta a la derecha del eje (convención para que el
# dibujo no cambie de sentido de un mes a otro; el signo de un eje no significa nada).
GRUPOS_REFERENCIA_EJES = ("GP",)
MAPA_MIN_PARTICIPACION = 0.5  # quien votó en menos de la mitad no se sitúa
MAPA_MIN_VOTACIONES = 10  # con menos votaciones con desacuerdo no se dibuja

# Tipo de asunto a partir del título del portal: (expresión regular, categoría). Gana la
# primera que encaje. Las PNL y las mociones no obligan al Gobierno.
CATEGORIAS = (
    (r"investidura", "Investidura"),
    (r"reales decretos-leyes", "Decretos-ley (convalidación)"),
    (r"enmiendas del senado", "Leyes: enmiendas del Senado"),
    (r"debates? de totalidad", "Enmiendas a la totalidad"),
    (r"toma en consideración", "Leyes: toma en consideración"),
    (r"iniciativas legislativas|lectura única|avocación|reforma del reglamento",
     "Leyes: dictamen y votación final"),
    (r"convenios internacionales", "Tratados internacionales"),
    (r"proposiciones no de ley", "Proposiciones no de ley"),
    (r"mociones", "Mociones"),
    (r"estabilidad presupuestaria|reequilibrio|cuenta general|presupuestos",
     "Presupuestos y estabilidad"),
    (r"comisi|subcomisi|dación de cuentas|suplicatorio", "Organización de la Cámara"),
)  # fmt: skip
NO_VINCULANTES = ("Proposiciones no de ley", "Mociones")

# Código del JSON -> etiqueta corta para los informes. Un código desconocido se muestra tal cual.
ETIQUETAS_GRUPO = {
    "GP": "PP",
    "GS": "PSOE",
    "GVOX": "Vox",
    "GSUMAR": "Sumar",
    "GR": "ERC",
    "GJxCAT": "Junts",
    "GEH Bildu": "Bildu",
    "GV (EAJ-PNV)": "PNV",
    "GMx": "Mixto",
}

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


def etiqueta(grupo: str) -> str:
    return ETIQUETAS_GRUPO.get(grupo, grupo)
