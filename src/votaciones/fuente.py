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
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
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


class ErrorAcceso(RuntimeError):
    """El portal no respondió como se esperaba (bloqueo, caída o cambio de formato)."""


@dataclass(frozen=True)
class Enlace:
    legislatura: int
    sesion: int
    fecha: date
    numero: int
    url_json: str | None  # None: la votación aparece en la página pero sin JSON todavía


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


def leer_enlaces(html: str, dia: date | None = None) -> list[Enlace]:
    """Una entrada por votación del día, con su JSON si ya está publicado."""
    vistos: dict[tuple[int, int, date, int], str | None] = {}
    for m in RE_FICHERO.finditer(html):
        fecha = datetime.strptime(m["fecha"], "%Y%m%d").date()
        if dia is not None and fecha != dia:
            continue
        clave = (int(m["leg"]), int(m["sesion"]), fecha, int(m["num"]))
        if m["ext"] == "json":
            vistos[clave] = config.BASE + m.group(0)
        else:
            vistos.setdefault(clave, None)
    return [Enlace(*clave, url) for clave, url in sorted(vistos.items())]


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
