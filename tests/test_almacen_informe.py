from datetime import date

from src.votaciones import almacen, analisis, cli, informe
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
    md = informe.componer(a)
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
    md = informe.componer(analisis.analizar("2026-08", v, votos))
    assert "No hubo votaciones en el Pleno este mes." in md
