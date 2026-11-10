"""Datos de prueba sintéticos con la forma exacta del JSON del portal (sin red)."""

from __future__ import annotations

import pytest

from src.votaciones import config


def votacion_json(
    sesion=1,
    numero=1,
    fecha="30/9/2026",
    votos=None,
    titulo="Proposiciones no de Ley.",
    texto="Proposición no de Ley de prueba.",
    subgrupo="",
    asentimiento="No",
):
    """votos: lista de (diputado, grupo, voto). Los totales se calculan a partir de ellos."""
    votos = votos or []
    cuenta = {v: sum(1 for *_, x in votos if x == v) for v in ("Sí", "No", "Abstención", "No vota")}
    return {
        "informacion": {
            "sesion": sesion, "numeroVotacion": numero, "fecha": fecha, "titulo": titulo,
            "textoExpediente": texto + "\n", "tituloSubGrupo": subgrupo, "textoSubGrupo": "",
            "votacionesConjuntas": [],
        },
        "totales": {
            "asentimiento": asentimiento, "presentes": len(votos) - cuenta["No vota"],
            "afavor": cuenta["Sí"], "enContra": cuenta["No"],
            "abstenciones": cuenta["Abstención"], "noVotan": cuenta["No vota"],
        },
        "votaciones": [
            {"asiento": str(i), "diputado": d, "grupo": g, "voto": v}
            for i, (d, g, v) in enumerate(votos, start=1)
        ],
    }  # fmt: skip


# Un pleno de juguete: A (3), B (2), C (2) y el Mixto (2).
PLENO = [("A1", "A"), ("A2", "A"), ("A3", "A"), ("B1", "B"), ("B2", "B"),
         ("C1", "C"), ("C2", "C"), ("M1", "GMx"), ("M2", "GMx")]  # fmt: skip


def con_votos(*votos: str):
    return [(d, g, v) for (d, g), v in zip(PLENO, votos, strict=True)]


@pytest.fixture
def datos_tmp(tmp_path, monkeypatch):
    """Redirige data/ y reports/ a una carpeta temporal."""
    monkeypatch.setattr(config, "DATOS", tmp_path / "data")
    monkeypatch.setattr(config, "INFORMES", tmp_path / "reports")
    monkeypatch.setattr(config, "MANIFIESTO", tmp_path / "data" / "dias.json")
    return tmp_path
