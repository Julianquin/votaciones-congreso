import json
from datetime import date

from src.votaciones import fuente

# Recorte con la forma real de la página (2026-11-10).
HTML = """
<script>
var diasVotaciones = [20260929, 20260930, 20261002];
function onChangeLegislatura(){ var idCurrentLegislatura = 15
</script>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/VOT_20260930153631.zip">zip</a>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion001/VOT_20260930153545.xml">x</a>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion001/VOT_20260930153547.json">j</a>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion002/VOT_20260930153550.png">p</a>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion201/20260929/Votacion001/VOT_20260929100000.json">j</a>
"""


def test_romano():
    assert [fuente.romano(n) for n in (10, 11, 12, 13, 14, 15)] == [
        "X", "XI", "XII", "XIII", "XIV", "XV",
    ]  # fmt: skip


def test_leer_dias_y_legislatura():
    assert fuente.leer_dias(HTML) == [date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 2)]
    assert fuente.leer_legislatura(HTML) == 15
    assert fuente.leer_dias("<html></html>") == []


def test_leer_enlaces_filtra_el_dia_y_marca_las_que_no_tienen_json():
    enlaces = fuente.leer_enlaces(HTML, date(2026, 9, 30))
    assert [(e.sesion, e.numero) for e in enlaces] == [(202, 1), (202, 2)]
    assert enlaces[0].url_json.endswith("Votacion001/VOT_20260930153547.json")
    assert enlaces[0].url_json.startswith("https://www.congreso.es/webpublica/")
    assert enlaces[1].url_json is None  # solo hay PNG: pendiente
    assert len(fuente.leer_enlaces(HTML)) == 3


def test_url_dia():
    url = fuente.url_dia(15, date(2026, 9, 30))
    assert url.endswith("&targetLegislatura=XV&targetDate=30/09/2026")


class _Respuesta:
    def __init__(self, status, contenido=b""):
        self.status_code = status
        self.content = contenido
        self.text = contenido.decode("utf-8-sig")


class _Sesion:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.headers = {}

    def get(self, url, timeout):
        return self.respuestas.pop(0)


def test_cliente_reintenta_5xx_y_quita_el_bom():
    datos = "﻿" + json.dumps({"a": "Sí"}, ensure_ascii=False)
    sesion = _Sesion([_Respuesta(503), _Respuesta(200, datos.encode("utf-8"))])
    cliente = fuente.Cliente(pausa=0, sesion=sesion)
    assert fuente.descargar_json(cliente, "u") == {"a": "Sí"}
    assert cliente.peticiones == 2


def test_cliente_no_reintenta_un_403():
    cliente = fuente.Cliente(pausa=0, sesion=_Sesion([_Respuesta(403)]))
    try:
        cliente.get("u")
    except fuente.ErrorAcceso as e:
        assert "403" in str(e)
    else:
        raise AssertionError("debía fallar")
