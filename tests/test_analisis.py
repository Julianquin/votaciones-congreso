from datetime import date

import pandas as pd
import pytest

from src.votaciones import analisis
from src.votaciones.normalizar import normalizar

from .conftest import con_votos, votacion_json


def mes(*jsons):
    filas, votos = [], []
    for j in jsons:
        f, v = normalizar(j, 15)
        filas.append(f)
        votos.extend(v)
    return pd.DataFrame(filas), pd.DataFrame(votos)


def test_normalizar_lee_el_formato_del_portal():
    j = votacion_json(sesion=202, numero=3, votos=con_votos(*["Sí"] * 9), subgrupo="Punto 1.")
    f, v = normalizar(j, 15, "http://x")
    assert f["votacion_id"] == "L15-S202-V003"
    assert f["fecha"] == date(2026, 9, 30)
    assert f["titulo"] == "Proposiciones no de Ley"  # sin el punto final
    assert f["texto_expediente"] == "Proposición no de Ley de prueba."  # sin el salto final
    assert f["a_favor"] == 9 and f["asentimiento"] is False
    assert len(v) == 9 and v[0]["grupo"] == "A"
    f2, _ = normalizar(j, 15, fecha=date(2026, 10, 1))
    assert f2["fecha"] == date(2026, 10, 1)


def test_posicion_cohesion_y_empates():
    # A: Sí Sí No | B: No No | C: Sí No (empate) | Mixto: no votan
    v, votos = mes(votacion_json(votos=con_votos("Sí", "Sí", "No", "No", "No", "Sí", "No",
                                                 "No vota", "No vota")))  # fmt: skip
    tg = analisis.tabla_grupos(v, votos).set_index("grupo")
    assert tg.loc["A", "posicion"] == "Sí"
    assert tg.loc["B", "posicion"] == "No"
    assert tg.loc["C", "posicion"] == "Dividido"
    assert tg.loc["GMx", "posicion"] == "Sin voto"
    assert tg.loc["B", "cohesion"] == pytest.approx(1.0)
    # Hix: (1,5·2 − 0,5·3) / 3 = 0,5
    assert tg.loc["A", "cohesion"] == pytest.approx(0.5)


def test_resultado_decisivo_y_ganadora():
    # Sí = 5 (A×3, C×2), No = 2 (B), Abst. = 2 (Mixto): aprobada.
    v, votos = mes(votacion_json(votos=con_votos("Sí", "Sí", "Sí", "No", "No", "Sí", "Sí",
                                                 "Abstención", "Abstención")))  # fmt: skip
    r = analisis.resultados(v).iloc[0]
    assert bool(r["aprobada"]) and r["margen"] == 3
    tg = analisis.tabla_grupos(v, votos).set_index("grupo")
    # Sin los 3 Sí de A quedaría 2–2: no aprobada. Sin los 2 de C, 3–2: sigue aprobada.
    assert tg.loc["A", "decisivo"] and not tg.loc["C", "decisivo"]
    assert tg.loc["A", "ganadora"] and not tg.loc["B", "ganadora"]


def test_decisivo_en_una_rechazada():
    # Sí = 3 (A), No = 4 (B×2, C×2), Mixto abstiene: rechazada. Sin los No de B: 3–2, aprobada.
    v, votos = mes(votacion_json(votos=con_votos("Sí", "Sí", "Sí", "No", "No", "No", "No",
                                                 "Abstención", "Abstención")))  # fmt: skip
    tg = analisis.tabla_grupos(v, votos).set_index("grupo")
    assert not bool(tg.loc["A", "aprobada"])
    assert tg.loc["B", "decisivo"] and tg.loc["C", "decisivo"]


def test_mayoria_absoluta_en_ley_organica():
    texto = "Proyecto de Ley Orgánica de prueba. Votación de conjunto."
    v, _ = mes(votacion_json(votos=con_votos(*["Sí"] * 9), texto=texto))
    r = analisis.resultados(v).iloc[0]
    assert bool(r["mayoria_absoluta"])
    assert not bool(r["aprobada"])  # 9 Sí no llegan a 176
    v2, _ = mes(votacion_json(votos=con_votos(*["Sí"] * 9), texto="Proyecto de Ley Orgánica."))
    assert not bool(analisis.resultados(v2).iloc[0]["mayoria_absoluta"])  # no es de conjunto


def test_asentimiento_cuenta_como_aprobada_sin_votos():
    v, _ = mes(votacion_json(asentimiento="Sí"))
    r = analisis.resultados(v).iloc[0]
    assert bool(r["asentimiento"]) and bool(r["aprobada"])


def test_afinidad_disidencias_y_ausencias():
    v, votos = mes(
        votacion_json(numero=1, votos=con_votos("Sí", "Sí", "No", "No", "No", "Sí", "Sí",
                                                "Sí", "No")),
        votacion_json(numero=2, votos=con_votos("No", "No", "No", "No", "No vota", "Sí", "Sí",
                                                "No", "No")),
    )  # fmt: skip
    a = analisis.analizar("2026-09", v, votos)
    assert a.orden[0] == "A"  # el grupo más grande primero
    assert a.afinidad.loc["A", "B"] == pytest.approx(0.5)
    assert a.afinidad.loc["A", "C"] == pytest.approx(0.5)
    # A3 votó No contra el Sí de su grupo; el Mixto (M1 Sí, M2 No) no cuenta.
    assert list(a.disidencias["diputado"]) == ["A3"]
    aus = a.ausencias.set_index("diputado")
    assert aus.loc["B2", "no_vota"] == 1 and aus.loc["B2", "proporcion"] == pytest.approx(0.5)


def test_analizar_mes_vacio():
    from src.votaciones import almacen

    v, votos = almacen._vacia(almacen.COLUMNAS_VOTACIONES), almacen._vacia(almacen.COLUMNAS_VOTOS)
    a = analisis.analizar("2026-08", v, votos)
    assert a.votaciones.empty and a.resumen.empty
