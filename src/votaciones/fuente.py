"""Acceso al portal de datos abiertos del Congreso.

El portal no tiene API: es una página Liferay con un calendario. Lo que se usa de ella
(comprobado el 2026-11-10):

- La página trae en su JavaScript ``var diasVotaciones = [20230919, ...]``: todos los días
  con votación de la legislatura elegida, y ``var idCurrentLegislatura = 15``.
- La página de un día (``&targetDate=dd/mm/aaaa``) enlaza un fichero por votación en
  ``/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion001/VOT_<marca>.json``.
  La marca de tiempo del nombre no se puede adivinar: hay que leer la página del día.
- Hay días que aparecen en el calendario sin JSON publicados todavía (solo PNG). Se marcan
  como pendientes y se vuelven a pedir en la siguiente corrida.
- Las votaciones **públicas por llamamiento** (investiduras, votaciones de conjunto de leyes
  orgánicas, reformas constitucionales) no tienen JSON nunca, pero la página trae su título y
  sus totales («Si: 171», «No: 179»). Se leen del HTML como votaciones no nominales.

Jerarquía de la página de un día: h4 = tipo de asunto («PUNTO UNICO. Dictámenes de…»),
h5 = expediente y, si lo hay, subgrupo, h6 = detalle, luego «Si/No/Abstenciones» y los ficheros.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime

import requests

from . import config

log = logging.getLogger(__name__)

RE_DIAS = re.compile(r"var\s+diasVotaciones\s*=\s*\[([^\]]*)\]")
RE_LEGISLATURA = re.compile(r"var\s+idCurrentLegislatura\s*=\s*(\d+)")
RE_FICHERO = re.compile(
    r"/webpublica/opendata/votaciones/Leg(?P<leg>\d+)/Sesion(?P<sesion>\d+)/(?P<fecha>\d{8})"
    r"/Votacion(?P<num>\d+)/[A-Za-z0-9_]+\.(?P<ext>json|xml|png|pdf)"
)
# Piezas de la página de un día, en el orden en que aparecen.
RE_PIEZA = re.compile(
    r"<(?P<h>h[3-6])[^>]*>(?P<texto>.*?)</(?P=h)>"
    r"|<p>\s*(?P<opcion>S[ií]|No|Abstenciones)\s*:\s*(?P<n>\d+)\s*</p>"
    r'|href="(?P<detalle>[^"]+)"[^>]*>\s*Detalle'
    r"|" + RE_FICHERO.pattern,
    re.S,
)
RE_PUNTO = re.compile(r"^(PUNTO\s+[^.]*|[IVXLC]+)\.\s*", re.I)  # «PUNTO UNICO.», «III.»


class ErrorAcceso(RuntimeError):
    """El portal no respondió como se esperaba (bloqueo, caída o cambio de formato)."""


@dataclass(frozen=True)
class Enlace:
    legislatura: int
    sesion: int
    fecha: date
    numero: int
    url_json: str | None  # None: la votación aparece en la página pero sin JSON (todavía)
    # Lo que dice la página de esa votación (h4, h5…, h6 y totales). Solo se usa cuando no
    # hay JSON; con JSON manda el JSON.
    tipo: str = ""
    epigrafes: tuple[str, ...] = ()
    detalle_texto: str = ""
    totales: dict = field(default_factory=dict, compare=False, hash=False)
    url_detalle: str = ""

    @property
    def llamamiento(self) -> bool:
        textos = (*self.epigrafes, self.detalle_texto)
        return any("llamamiento" in t.lower() for t in textos)


def romano(n: int) -> str:
    valores = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    salida = []
    for valor, letra in valores:
        while n >= valor:
            salida.append(letra)
            n -= valor
    return "".join(salida)


def url_legislatura(legislatura: int) -> str:
    return f"{config.URL_PORTLET}&targetLegislatura={romano(legislatura)}"


def url_dia(legislatura: int, dia: date) -> str:
    return f"{url_legislatura(legislatura)}&targetDate={dia:%d/%m/%Y}"


# --- Lectura del HTML (sin red; lo usan los tests) ---------------------------------------
def leer_dias(html: str) -> list[date]:
    m = RE_DIAS.search(html)
    if not m:
        return []
    numeros = [x.strip() for x in m.group(1).split(",") if x.strip()]
    return sorted(datetime.strptime(x, "%Y%m%d").date() for x in numeros)


def leer_legislatura(html: str) -> int | None:
    m = RE_LEGISLATURA.search(html)
    return int(m.group(1)) if m else None


def limpiar(fragmento: str) -> str:
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def leer_enlaces(html: str, dia: date | None = None) -> list[Enlace]:
    """Una entrada por votación del día: su JSON si ya está publicado y lo que dice la página."""
    tipo, epigrafes, detalle_texto = "", [], ""
    totales: dict[str, int] = {}
    url_detalle = ""
    # Tras una votación, un h5 nuevo no se suma a los anteriores: sustituye al último
    # (subgrupo) o, si solo había uno, a ese (siguiente expediente).
    tras_votacion = False
    vistas: dict[tuple[int, int, date, int], dict] = {}
    for m in RE_PIEZA.finditer(html):
        if m["h"]:
            texto = limpiar(m["texto"])
            if m["h"] in ("h3", "h4"):
                tipo = RE_PUNTO.sub("", texto).rstrip(".") if m["h"] == "h4" else ""
                epigrafes, detalle_texto = [], ""
            elif m["h"] == "h5":
                if tras_votacion and epigrafes:
                    epigrafes.pop()
                epigrafes.append(texto)
                detalle_texto = ""
            else:
                detalle_texto = texto
            totales, url_detalle = {}, ""
            tras_votacion = False
        elif m["opcion"]:
            clave = {"no": "no", "abstenciones": "abstenciones"}.get(m["opcion"].lower(), "si")
            totales[clave] = int(m["n"])
        elif m["detalle"]:
            url_detalle = m["detalle"]
        else:
            fecha = datetime.strptime(m["fecha"], "%Y%m%d").date()
            if dia is not None and fecha != dia:
                continue
            clave = (int(m["leg"]), int(m["sesion"]), fecha, int(m["num"]))
            info = vistas.setdefault(
                clave,
                {"url_json": None, "tipo": tipo, "epigrafes": tuple(epigrafes),
                 "detalle_texto": detalle_texto, "totales": dict(totales),
                 "url_detalle": url_detalle},
            )  # fmt: skip
            if m["ext"] == "json":
                info["url_json"] = config.BASE + m.group(0)
            tras_votacion = True
    return [Enlace(*clave, **info) for clave, info in sorted(vistas.items())]


# --- Red ---------------------------------------------------------------------------------
class Cliente:
    """Sesión HTTP con pausa entre peticiones y reintentos con espera creciente."""

    def __init__(
        self,
        pausa: float = config.PAUSA,
        reintentos: int = config.REINTENTOS,
        timeout: float = config.TIMEOUT,
        sesion: requests.Session | None = None,
    ):
        self.sesion = sesion or requests.Session()
        self.sesion.headers["User-Agent"] = config.USER_AGENT
        self.pausa = pausa
        self.reintentos = reintentos
        self.timeout = timeout
        self.peticiones = 0
        self._ultima = 0.0

    def get(self, url: str) -> requests.Response:
        error: Exception | None = None
        for intento in range(1, self.reintentos + 1):
            espera = self.pausa - (time.monotonic() - self._ultima)
            if espera > 0:
                time.sleep(espera)
            self._ultima = time.monotonic()
            self.peticiones += 1
            try:
                r = self.sesion.get(url, timeout=self.timeout)
            except requests.RequestException as e:
                error = e
            else:
                if r.status_code == 200:
                    return r
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise ErrorAcceso(f"HTTP {r.status_code} en {url}")
                error = ErrorAcceso(f"HTTP {r.status_code}")
            if intento < self.reintentos:
                log.warning("Fallo %s (intento %d): %s", url, intento, error)
                time.sleep(self.pausa * 2**intento)
        raise ErrorAcceso(f"{url}: {error}")


def dias_con_votacion(cliente: Cliente, legislatura: int | None = None) -> tuple[int, list[date]]:
    """Legislatura consultada y lista de días con votación según el calendario del portal."""
    url = config.URL_VOTACIONES if legislatura is None else url_legislatura(legislatura)
    html = cliente.get(url).text
    leg = legislatura or leer_legislatura(html)
    dias = leer_dias(html)
    if leg is None or not dias:
        raise ErrorAcceso(
            "La página de votaciones no trae diasVotaciones o idCurrentLegislatura: "
            "o el portal ha bloqueado la petición o ha cambiado su formato."
        )
    return leg, dias


def votaciones_del_dia(cliente: Cliente, legislatura: int, dia: date) -> list[Enlace]:
    return leer_enlaces(cliente.get(url_dia(legislatura, dia)).text, dia)


def descargar_json(cliente: Cliente, url: str) -> dict:
    # El portal sirve algunos ficheros con BOM.
    return json.loads(cliente.get(url).content.decode("utf-8-sig"))
