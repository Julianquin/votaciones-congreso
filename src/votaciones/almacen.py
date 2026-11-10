"""Almacén en disco: un parquet por mes para votaciones y otro para votos, más un manifiesto.

    data/votaciones/2026-09.parquet   una fila por votación
    data/votos/2026-09.parquet        una fila por diputado y votación
    data/dias.json                    estado de cada día con votación (completo o pendiente)

La unidad de actualización es el día: guardar un día sustituye lo que hubiera de ese día
y deja intacto el resto del mes. Así se puede repetir una corrida sin duplicar nada.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import config

COLUMNAS_VOTACIONES = [
    "votacion_id", "legislatura", "sesion", "numero", "fecha", "titulo", "titulo_subgrupo",
    "texto_subgrupo", "texto_expediente", "asentimiento", "presentes", "a_favor", "en_contra",
    "abstenciones", "no_votan", "conjuntas", "llamamiento", "url",
]  # fmt: skip
COLUMNAS_VOTOS = ["votacion_id", "fecha", "asiento", "diputado", "grupo", "voto"]


# --- Meses -------------------------------------------------------------------------------
def mes_de(dia: date) -> str:
    return f"{dia:%Y-%m}"


def validar_mes(mes: str) -> str:
    try:
        a, m = mes.split("-")
        date(int(a), int(m), 1)
    except ValueError as e:
        raise ValueError(f"Mes no válido: {mes!r} (formato AAAA-MM)") from e
    return f"{int(a):04d}-{int(m):02d}"


def sumar_meses(mes: str, n: int) -> str:
    a, m = (int(x) for x in mes.split("-"))
    total = a * 12 + (m - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def nombre_mes(mes: str) -> str:
    a, m = mes.split("-")
    return f"{config.MESES[int(m) - 1]} de {a}"


# --- Parquet -----------------------------------------------------------------------------
def ruta(tabla: str, mes: str, datos: Path | None = None) -> Path:
    return (datos or config.DATOS) / tabla / f"{mes}.parquet"


def _vacia(columnas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columnas)


def _leer(tabla: str, mes: str, columnas: list[str], datos: Path | None) -> pd.DataFrame:
    p = ruta(tabla, mes, datos)
    if not p.exists():
        return _vacia(columnas)
    df = pd.read_parquet(p)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    if tabla == "votaciones" and "llamamiento" not in df.columns:  # parquet anterior al 2026-11-10
        df["llamamiento"] = False
    return df


def cargar_mes(mes: str, datos: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        _leer("votaciones", mes, COLUMNAS_VOTACIONES, datos),
        _leer("votos", mes, COLUMNAS_VOTOS, datos),
    )


def _escribir(df: pd.DataFrame, tabla: str, mes: str, datos: Path | None) -> None:
    p = ruta(tabla, mes, datos)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(p)


def guardar_dia(
    dia: date, votaciones: list[dict], votos: list[dict], datos: Path | None = None
) -> None:
    """Sustituye en el parquet del mes todo lo del día (y cualquier votación con el mismo id)."""
    if not votaciones:
        return
    mes = mes_de(dia)
    viejas, viejos = cargar_mes(mes, datos)
    nuevas = pd.DataFrame(votaciones, columns=COLUMNAS_VOTACIONES)
    nuevos = pd.DataFrame(votos, columns=COLUMNAS_VOTOS)
    ids = set(nuevas["votacion_id"])

    def sin_dia(df: pd.DataFrame) -> pd.DataFrame:
        return df[(df["fecha"] != dia) & ~df["votacion_id"].isin(ids)]

    partes_v = [d for d in (sin_dia(viejas), nuevas) if not d.empty]
    partes_x = [d for d in (sin_dia(viejos), nuevos) if not d.empty]
    v = pd.concat(partes_v, ignore_index=True).sort_values(["fecha", "sesion", "numero"])
    x = (
        pd.concat(partes_x, ignore_index=True).sort_values(["votacion_id", "grupo", "diputado"])
        if partes_x
        else nuevos
    )
    _escribir(v.reset_index(drop=True), "votaciones", mes, datos)
    _escribir(x.reset_index(drop=True), "votos", mes, datos)


def meses_guardados(datos: Path | None = None) -> list[str]:
    carpeta = (datos or config.DATOS) / "votaciones"
    return sorted(p.stem for p in carpeta.glob("*.parquet")) if carpeta.exists() else []


# --- Manifiesto --------------------------------------------------------------------------
def cargar_manifiesto(ruta_m: Path | None = None) -> dict[str, dict]:
    p = ruta_m or config.MANIFIESTO
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def guardar_manifiesto(manifiesto: dict[str, dict], ruta_m: Path | None = None) -> None:
    p = ruta_m or config.MANIFIESTO
    p.parent.mkdir(parents=True, exist_ok=True)
    ordenado = dict(sorted(manifiesto.items()))
    p.write_text(json.dumps(ordenado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def dias_pendientes(manifiesto: dict[str, dict], mes: str | None = None) -> list[str]:
    return [
        d
        for d, e in sorted(manifiesto.items())
        if not e.get("completo") and (mes is None or d.startswith(mes))
    ]


def meses_con_pendientes(manifiesto: dict[str, dict]) -> list[str]:
    return sorted({d[:7] for d in dias_pendientes(manifiesto)})
