"""JSON de una votación del Congreso -> una fila de votación y una fila por diputado.

Formato del JSON (comprobado el 2026-11-10, sesión 202 de la XV):

    {"informacion": {"sesion": 202, "numeroVotacion": 1, "fecha": "30/9/2026",
                     "titulo": "Proposiciones no de Ley.", "textoExpediente": "...",
                     "tituloSubGrupo": "", "textoSubGrupo": "", "votacionesConjuntas": []},
     "totales": {"asentimiento": "No", "presentes": 346, "afavor": 137, "enContra": 175,
                 "abstenciones": 34, "noVotan": 4},
     "votaciones": [{"asiento": "6", "diputado": "Apellidos, Nombre", "grupo": "GSUMAR",
                     "voto": "No"}, ...]}

El voto vale «Sí», «No», «Abstención» o «No vota».
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fuente import Enlace


def texto(x) -> str:
    return unicodedata.normalize("NFC", str(x or "")).strip()


def entero(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def leer_fecha(s: str) -> date:
    d, m, a = texto(s).split("/")
    return date(int(a), int(m), int(d))


def votacion_id(legislatura: int, sesion: int, numero: int) -> str:
    return f"L{legislatura:02d}-S{sesion:03d}-V{numero:03d}"


def normalizar(
    datos: dict, legislatura: int, url: str | None = None, fecha: date | None = None
) -> tuple[dict, list[dict]]:
    """Devuelve (fila de la votación, filas de votos individuales).

    ``fecha`` es la de la carpeta del portal; si se da, manda sobre la del JSON, para que
    una votación quede siempre en el día bajo el que se publicó.
    """
    inf = datos["informacion"]
    tot = datos.get("totales") or {}
    sesion = entero(inf.get("sesion"))
    numero = entero(inf.get("numeroVotacion"))
    vid = votacion_id(legislatura, sesion, numero)
    dia = fecha or leer_fecha(inf["fecha"])

    fila = {
        "votacion_id": vid,
        "legislatura": legislatura,
        "sesion": sesion,
        "numero": numero,
        "fecha": dia,
        "titulo": texto(inf.get("titulo")).rstrip("."),
        "titulo_subgrupo": texto(inf.get("tituloSubGrupo")),
        "texto_subgrupo": texto(inf.get("textoSubGrupo")),
        "texto_expediente": texto(inf.get("textoExpediente")),
        "asentimiento": texto(tot.get("asentimiento")).lower().startswith("s"),
        "presentes": entero(tot.get("presentes")),
        "a_favor": entero(tot.get("afavor")),
        "en_contra": entero(tot.get("enContra")),
        "abstenciones": entero(tot.get("abstenciones")),
        "no_votan": entero(tot.get("noVotan")),
        "conjuntas": len(inf.get("votacionesConjuntas") or []),
        "llamamiento": False,
        "url": url or "",
    }
    votos = [
        {
            "votacion_id": vid,
            "fecha": dia,
            "asiento": texto(v.get("asiento")),
            "diputado": texto(v.get("diputado")),
            "grupo": texto(v.get("grupo")),
            "voto": texto(v.get("voto")),
        }
        for v in datos.get("votaciones") or []
    ]
    return fila, votos


def normalizar_html(e: Enlace, diputados: int = 350) -> dict:
    """Votación pública por llamamiento: sin JSON; título y totales salen de la página del día.

    El voto de cada diputado solo está en el Diario de Sesiones (``url`` enlaza a él), así que
    la votación cuenta como no nominal. «No votan» se deduce: escaños menos votos emitidos.
    """
    si, no, abst = (e.totales.get(k, 0) for k in ("si", "no", "abstenciones"))
    epigrafes = [
        re.sub(r"\s*\(pública por llamamiento\)\.?", "", texto(x), flags=re.I).rstrip(".")
        for x in e.epigrafes
    ]
    return {
        "votacion_id": votacion_id(e.legislatura, e.sesion, e.numero),
        "legislatura": e.legislatura,
        "sesion": e.sesion,
        "numero": e.numero,
        "fecha": e.fecha,
        "titulo": texto(e.tipo).rstrip("."),
        "titulo_subgrupo": epigrafes[-1] if len(epigrafes) > 1 else "",
        "texto_subgrupo": texto(e.detalle_texto),
        "texto_expediente": epigrafes[0] if epigrafes else texto(e.detalle_texto),
        "asentimiento": False,
        "presentes": si + no + abst,
        "a_favor": si,
        "en_contra": no,
        "abstenciones": abst,
        "no_votan": max(diputados - si - no - abst, 0),
        "conjuntas": 0,
        "llamamiento": True,
        "url": e.url_detalle,
    }
