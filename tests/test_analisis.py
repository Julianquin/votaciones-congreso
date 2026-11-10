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


@pytest.mark.parametrize(
    ("texto", "subgrupo", "umbral"),
    [
        ("Proyecto de Ley Orgánica de prueba.", "Votación de conjunto.", 176),
        ("Proyecto de Ley Orgánica de prueba.", "Votación del dictamen.", 0),
        ("Proposición de Ley del Grupo X, Orgánica de reforma de la Ley Orgánica 1/2020.",
         "Votación de conjunto.", 176),
        # Una ley ordinaria que modifica una orgánica no es orgánica.
        ("Proyecto de Ley por la que se modifica la Ley Orgánica 1/2025.", "Votación de conjunto.",
         0),
        ("Votación de conjunto de la Proposición de Reforma del artículo 49 de la Constitución.",
         "", 210),
        ("Proposición de reforma del Reglamento del Congreso.", "Votación de conjunto.", 176),
        ("Propuesta de don X como candidato a la Presidencia del Gobierno. (Pública por "
         "llamamiento)", "", 0),
    ],
)  # fmt: skip
def test_umbral_de_mayoria(texto, subgrupo, umbral):
    v, _ = mes(votacion_json(votos=con_votos(*["Sí"] * 9), texto=texto, subgrupo=subgrupo))
    assert analisis.resultados(v).iloc[0]["umbral"] == umbral


def test_investidura_exige_mayoria_absoluta():
    titulo = "Debate sobre la investidura del candidato a la Presidencia del Gobierno."
    v, _ = mes(votacion_json(votos=con_votos(*["Sí"] * 9), titulo=titulo))
    r = analisis.resultados(v).iloc[0]
    assert r["umbral"] == 176 and not bool(r["aprobada"])  # 9 Sí no llegan a 176


def test_empate_no_es_rechazo():
    v, _ = mes(votacion_json(votos=con_votos("Sí", "Sí", "Sí", "No", "No", "No", "Sí",
                                                 "No", "No vota")))  # fmt: skip
    r = analisis.resultados(v).iloc[0]
    assert bool(r["empate"]) and not bool(r["aprobada"])


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


GOB = [("S1", "GS"), ("S2", "GS"), ("S3", "GS"), ("U1", "GSUMAR"), ("P1", "GP"), ("P2", "GP"),
       ("P3", "GP"), ("P4", "GP"), ("V1", "GVOX")]  # fmt: skip


def con_gob(*votos):
    return [(d, g, v) for (d, g), v in zip(GOB, votos, strict=True)]


def test_gobierno_mayorias_y_categorias():
    v, votos = mes(
        # Gobierno Sí y pierde (4 Sí contra 5 No).
        votacion_json(numero=1,
                      votos=con_gob("Sí", "Sí", "Sí", "Sí", "No", "No", "No", "No", "No")),
        # Gobierno No y gana.
        votacion_json(numero=2, votos=con_gob("No", "No", "No", "No", "Sí", "Sí", "No", "No", "Sí"),
                      titulo="Mociones consecuencia de interpelaciones urgentes."),
        # Gobierno dividido.
        votacion_json(numero=3,
                      votos=con_gob("Sí", "Sí", "Sí", "No", "Sí", "Sí", "Sí", "Sí", "Sí")),
    )  # fmt: skip
    a = analisis.analizar("2026-09", v, votos)
    g = a.gobierno.set_index("votacion_id")
    assert list(g["posicion"]) == ["Sí", "No", "Dividido"]
    assert list(g["pierde"]) == [True, False, False]
    assert list(a.mayorias["grupos"]) == [("GP", "GS", "GVOX")]  # la única aprobada (nº 3)
    assert list(a.votaciones["categoria"]) == [
        "Proposiciones no de ley", "Mociones", "Proposiciones no de ley",
    ]  # fmt: skip
    assert analisis.categoria("Convalidación o derogación de Reales Decretos-leyes") == (
        "Decretos-ley (convalidación)"
    )
    assert analisis.categoria("Algo nuevo") == "Otros"


def test_mapa_separa_bloques_y_orienta_al_pp_a_la_derecha():
    votaciones = []
    for n in range(12):
        bloque_a = "Sí" if n % 3 else "No"
        bloque_b = "No" if n % 3 else "Sí"
        votos = [(f"P{i}", "GP", bloque_a) for i in range(4)]
        votos += [(f"S{i}", "GS", bloque_b) for i in range(4)]
        votos += [("Raro", "GS", bloque_a if n % 2 else bloque_b)]
        votaciones.append(votacion_json(numero=n + 1, votos=votos))
    v, votos = mes(*votaciones)
    m = analisis.mapa_diputados(votos)
    pts = m.puntos.set_index("diputado")
    assert pts.loc["P0", "x"] > 0 > pts.loc["S0", "x"]
    assert pts.loc["S0", "x"] < pts.loc["Raro", "x"] < pts.loc["P0", "x"]
    assert m.varianza[0] > 0.5
    assert analisis.orden_espacial(m, ["GP", "GS"]) == ["GS", "GP"]
