from datetime import date

from src.votaciones import almacen, analisis, cli, graficos, informe
from src.votaciones.normalizar import normalizar

from .conftest import con_votos, votacion_json


def guardar(dia: date, *jsons):
    filas, votos = [], []
    for j in jsons:
        f, v = normalizar(j, 15, "https://www.congreso.es/x.json", dia)
        filas.append(f)
        votos.extend(v)
    almacen.guardar_dia(dia, filas, votos)


def test_meses():
    assert almacen.sumar_meses("2026-01", -1) == "2025-12"
    assert almacen.sumar_meses("2025-12", 1) == "2026-01"
    assert cli.mes_anterior(date(2026, 3, 3)) == "2026-02"
    assert almacen.validar_mes("2026-9") == "2026-09"
    assert almacen.nombre_mes("2026-09") == "septiembre de 2026"


def test_guardar_dia_sustituye_sin_duplicar(datos_tmp):
    d1, d2 = date(2026, 9, 29), date(2026, 9, 30)
    todos_si = con_votos(*["Sí"] * 9)
    guardar(d1, votacion_json(sesion=201, numero=1, votos=todos_si))
    guardar(d2, votacion_json(sesion=202, numero=1, votos=todos_si))
    guardar(d2, votacion_json(sesion=202, numero=1, votos=todos_si),
            votacion_json(sesion=202, numero=2, votos=todos_si))  # fmt: skip
    v, votos = almacen.cargar_mes("2026-09")
    assert list(v["votacion_id"]) == ["L15-S201-V001", "L15-S202-V001", "L15-S202-V002"]
    assert len(votos) == 27
    assert v["fecha"].iloc[0] == d1  # vuelve como date, no como Timestamp
    assert almacen.meses_guardados() == ["2026-09"]


def test_manifiesto_y_pendientes(datos_tmp):
    m = {"2026-09-30": {"completo": True}, "2026-10-02": {"completo": False}}
    almacen.guardar_manifiesto(m)
    m = almacen.cargar_manifiesto()
    assert almacen.dias_pendientes(m) == ["2026-10-02"]
    assert almacen.meses_con_pendientes(m) == ["2026-10"]
    assert almacen.dias_pendientes(m, "2026-09") == []


def test_informe_completo(datos_tmp):
    dia = date(2026, 9, 30)
    guardar(
        dia,
        votacion_json(sesion=202, numero=1, votos=con_votos("Sí", "Sí", "No", "No", "No", "Sí",
                                                            "Sí", "Sí", "No")),
        votacion_json(sesion=202, numero=2, texto="Texto con | barra\ny salto",
                      votos=con_votos(*["No"] * 9)),
        votacion_json(sesion=202, numero=3, asentimiento="Sí"),
    )  # fmt: skip
    v, votos = almacen.cargar_mes("2026-09")
    a = analisis.analizar("2026-09", v, votos, ["2026-09-29"])
    md = informe.componer_detalle(a)
    for titulo in ("## Resumen", "## Cómo votó cada grupo", "## Afinidad entre grupos",
                   "## Todas las votaciones", "### 30 de septiembre (sesión 202)"):  # fmt: skip
        assert titulo in md
    assert "[!WARNING]" in md and "29 de septiembre" in md
    assert "Texto con \\| barra y salto" in md  # la barra no rompe la tabla
    assert "Aprobada por asentimiento" in md
    assert "**3 votaciones** en 1 día de pleno (sesión 202)" in md
    p = informe.escribir(a)
    indice = informe.escribir_indice({"2026-09-29": {"completo": False}})
    assert p.name == "2026-09.md"
    assert "[septiembre de 2026](2026-09.md) | 3 | 1 día pendiente" in indice.read_text()


def test_informe_mes_sin_votaciones(datos_tmp):
    v, votos = almacen.cargar_mes("2026-08")
    a = analisis.analizar("2026-08", v, votos)
    assert "No hubo votaciones en el Pleno este mes." in informe.componer_detalle(a)
    assert "Este mes no hubo votaciones en el Pleno." in informe.componer(a)


def test_hemiciclo_tiene_un_asiento_por_diputado():
    for n in (9, 120, 350, 358):
        assert len(graficos.posiciones_hemiciclo(n)) == n


def test_graficos_deterministas_y_en_el_informe(datos_tmp):
    import random

    random.seed(1)
    dia = date(2026, 9, 30)
    opciones = ["Sí", "No", "Abstención"]
    jsons = [
        votacion_json(sesion=202, numero=n, votos=con_votos(*random.choices(opciones, k=9)))
        for n in range(1, 16)
    ]
    jsons.append(votacion_json(sesion=202, numero=16, votos=con_votos(*["Sí"] * 4, *["No"] * 5)))
    guardar(dia, *jsons)
    v, votos = almacen.cargar_mes("2026-09")
    a = analisis.analizar("2026-09", v, votos)
    p = informe.escribir(a)
    carpeta = p.parent / "img" / "2026-09"
    primera = {f.name: f.read_bytes() for f in carpeta.glob("*.svg")}
    esperados = {"mapa.svg", "mapa-oscuro.svg", "afinidad.svg", "afinidad-oscuro.svg",
                 "ganadora.svg", "ganadora-oscuro.svg"}  # fmt: skip
    assert esperados <= set(primera)
    assert any(n.startswith("votacion-") for n in primera)
    informe.escribir(a)
    segunda = {f.name: f.read_bytes() for f in carpeta.glob("*.svg")}
    assert primera == segunda  # sin fechas ni ids aleatorios: no ensucia git
    md = p.read_text()
    assert "# Qué votó el Congreso en septiembre de 2026" in md
    assert "## Las votaciones más importantes del mes" in md
    assert 'srcset="img/2026-09/ganadora-oscuro.svg"' in md
    assert "(2026-09-detalle.md)" in md
    detalle = (p.parent / "2026-09-detalle.md").read_text()
    assert "## Mapa de diputados" in detalle and "## Quién sacó adelante las votaciones" in detalle
    assert 'srcset="img/2026-09/mapa-oscuro.svg"' in detalle


def test_carrusel_de_instagram(datos_tmp):
    import random

    from PIL import Image

    from src.votaciones import instagram

    random.seed(2)
    opciones = ["Sí", "No", "Abstención"]
    jsons = [
        votacion_json(sesion=202, numero=n, votos=con_votos(*random.choices(opciones, k=9)))
        for n in range(1, 13)
    ]
    guardar(date(2026, 9, 30), *jsons)
    carpeta = instagram.generar("2026-09", salida=datos_tmp / "social")
    pngs = sorted(carpeta.glob("*.png"))
    assert pngs[0].name == "01-portada.png" and pngs[-1].name.endswith("-cierre.png")
    for p in pngs:
        with Image.open(p) as img:
            assert img.size == (1080, 1350)
    assert "IA" not in (carpeta / "pie.txt").read_text()
    # Con ilustración de portada, el texto lo declara.
    fondo = datos_tmp / "fondo.png"
    Image.new("RGB", (1104, 1472), "#557766").save(fondo)
    carpeta = instagram.generar("2026-09", fondo=fondo, salida=datos_tmp / "social")
    assert "generada con IA" in (carpeta / "pie.txt").read_text()
