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


# Recorte real del 30-01-2024 (amnistía): votación con JSON y la de conjunto, por llamamiento,
# que solo tiene PNG. Y la estructura del 10-01-2024: un expediente por bloque.
HTML_DIA = """
<h4>PUNTO UNICO. Dictámenes de Comisiones sobre iniciativas legislativas.</h4>
<h5> Proposición de Ley Orgánica de amnistía para la normalización institucional.</h5>
<h5> Votación del dictamen.</h5>
<h6 class="con_est"><i class="fas"></i> Votación del dictamen.</h6>
<div class="result_vot"><p>Si: 177</p><p>No: 172</p><p>Abstenciones: 0</p>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion018/20240130/Votacion009/VOT_20240130190000.json">JSON</a></div>
<img src="/webpublica/opendata/votaciones/Leg15/Sesion018/20240130/Votacion009/VOT_20240130185959.png"/>
<h5> Votación de conjunto (pública por llamamiento)</h5>
<h6 class="con_est"> Votación de conjunto de la Proposición de Ley Orgánica de amnistía, por tener la misma carácter orgánico. (Pública por llamamiento)</h6>
<div class="result_vot"><p>Si: 171</p><p>No: 179</p><p>Abstenciones: 0</p>
<a href="https://www.congreso.es/public_oficiales/L15/CONG/DS/PL/DSCD-15-PL-20.PDF?#page=22" target="_blank" class="btn">
Detalle
</a></div>
<img src="/webpublica/opendata/votaciones/Leg15/Sesion018/20240130/Votacion010/VOT_20240517123810.png"/>
<h4>PUNTO SEGUNDO. Convalidación o derogación de Reales Decretos-leyes.</h4>
<h5> Real Decreto-ley 6/2023.</h5>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion018/20240130/Votacion011/VOT_20240130200000.json">JSON</a>
<h5> Real Decreto-ley 7/2023.</h5>
<a href="/webpublica/opendata/votaciones/Leg15/Sesion018/20240130/Votacion012/VOT_20240130200001.json">JSON</a>
"""


def test_leer_enlaces_recoge_las_votaciones_por_llamamiento():
    from src.votaciones.normalizar import normalizar_html

    enlaces = {e.numero: e for e in fuente.leer_enlaces(HTML_DIA, date(2024, 1, 30))}
    assert enlaces[9].url_json and not enlaces[9].llamamiento
    e = enlaces[10]
    assert e.url_json is None and e.llamamiento
    assert e.totales == {"si": 171, "no": 179, "abstenciones": 0}
    assert e.tipo == "Dictámenes de Comisiones sobre iniciativas legislativas"
    assert e.url_detalle.endswith("DSCD-15-PL-20.PDF?#page=22")
    f = normalizar_html(e)
    assert f["votacion_id"] == "L15-S018-V010" and f["llamamiento"]
    assert (f["a_favor"], f["en_contra"], f["no_votan"]) == (171, 179, 0)
    assert f["texto_expediente"].startswith("Proposición de Ley Orgánica de amnistía")
    assert f["titulo_subgrupo"] == "Votación de conjunto"  # sin la coletilla
    # Un expediente nuevo tras una votación no arrastra el anterior.
    assert enlaces[11].epigrafes == ("Real Decreto-ley 6/2023.",)
    assert enlaces[12].epigrafes == ("Real Decreto-ley 7/2023.",)
