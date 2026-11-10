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
MAYORIA_ABSOLUTA = 176  # art. 81 CE: votación final de conjunto de una ley orgánica (D-06)

VOTOS_EMITIDOS = ("Sí", "No", "Abstención")
NO_VOTA = "No vota"

# El Grupo Mixto junta partidos distintos: su «posición de grupo» no expresa disciplina,
# así que no se cuentan disidencias dentro de él (D-05).
GRUPOS_SIN_DISCIPLINA = ("GMx",)

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
