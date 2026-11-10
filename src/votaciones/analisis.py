"""Métricas de un mes de votaciones. Todas las definiciones están en docs/DECISIONS.md.

Entradas: el DataFrame de votaciones y el de votos de almacen.cargar_mes. Nada de red.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import config

EMITIDOS = list(config.VOTOS_EMITIDOS)


# --- Resultado de cada votación ----------------------------------------------------------
def requiere_mayoria_absoluta(v: pd.DataFrame) -> pd.Series:
    """Heurística (D-06): votación de conjunto sobre una ley orgánica."""
    t = (
        v["titulo"] + " " + v["titulo_subgrupo"] + " " + v["texto_subgrupo"] + " "
        + v["texto_expediente"]
    ).str.lower()  # fmt: skip
    return t.str.contains("orgánica", regex=False) & t.str.contains("conjunto", regex=False)


def resultados(v: pd.DataFrame) -> pd.DataFrame:
    """Añade mayoria_absoluta, aprobada y margen. El portal no publica el resultado: se calcula."""
    v = v.copy()
    v["mayoria_absoluta"] = requiere_mayoria_absoluta(v) & ~v["asentimiento"]
    simple = v["a_favor"] > v["en_contra"]
    absoluta = v["a_favor"] >= config.MAYORIA_ABSOLUTA
    v["aprobada"] = v["asentimiento"] | simple.where(~v["mayoria_absoluta"], absoluta)
    v["margen"] = (v["a_favor"] - v["en_contra"]).where(
        ~v["mayoria_absoluta"], v["a_favor"] - config.MAYORIA_ABSOLUTA
    )
    return v


# --- Grupos ------------------------------------------------------------------------------
def conteos_grupo(votos: pd.DataFrame) -> pd.DataFrame:
    """Índice (votacion_id, grupo); columnas Sí, No, Abstención, No vota y miembros."""
    c = votos.groupby(["votacion_id", "grupo"])["voto"].value_counts().unstack(fill_value=0)
    for col in [*EMITIDOS, config.NO_VOTA]:
        if col not in c.columns:
            c[col] = 0
    c = c[[*EMITIDOS, config.NO_VOTA]].astype(int)
    c.columns.name = None
    c["miembros"] = votos.groupby(["votacion_id", "grupo"]).size()
    return c


def posicion(c: pd.DataFrame) -> pd.Series:
    """Opción más votada dentro del grupo; «Dividido» si hay empate y «Sin voto» si nadie votó."""
    em = c[EMITIDOS]
    maximo = em.max(axis=1)
    empatadas = em.eq(maximo, axis=0).sum(axis=1)
    pos = em.idxmax(axis=1).where(empatadas == 1, "Dividido")
    return pos.where(maximo > 0, "Sin voto").rename("posicion")


def cohesion(c: pd.DataFrame) -> pd.Series:
    """Índice de acuerdo de Hix, Noury y Roland (2005): 1 unanimidad, 0 reparto a tercios."""
    em = c[EMITIDOS]
    total = em.sum(axis=1)
    return ((1.5 * em.max(axis=1) - 0.5 * total) / total.where(total > 0)).rename("cohesion")


def tabla_grupos(v: pd.DataFrame, votos: pd.DataFrame) -> pd.DataFrame:
    """Una fila por (votación, grupo) con conteos, posición, cohesión, si ganó y si fue decisivo."""
    c = conteos_grupo(votos)
    c["posicion"] = posicion(c)
    c["cohesion"] = cohesion(c)
    r = resultados(v).set_index("votacion_id")[
        ["a_favor", "en_contra", "aprobada", "mayoria_absoluta"]
    ]
    c = c.join(r, on="votacion_id")
    c["ganadora"] = ((c["posicion"] == "Sí") & c["aprobada"]) | (
        (c["posicion"] == "No") & ~c["aprobada"]
    )
    # Decisivo (D-04): si el grupo se hubiera abstenido en bloque, el resultado cambiaría.
    sin_si = c["a_favor"] - c["Sí"]
    decide_si = (c["posicion"] == "Sí") & c["aprobada"] & (
        (sin_si <= c["en_contra"]).where(~c["mayoria_absoluta"], sin_si < config.MAYORIA_ABSOLUTA)
    )  # fmt: skip
    decide_no = (
        (c["posicion"] == "No") & ~c["aprobada"] & ~c["mayoria_absoluta"]
        & (c["a_favor"] > c["en_contra"] - c["No"])
    )  # fmt: skip
    c["decisivo"] = decide_si | decide_no
    return c.reset_index()


def orden_grupos(votos: pd.DataFrame) -> list[str]:
    """Grupos de mayor a menor según sus miembros en la última votación del mes."""
    if votos.empty:
        return []
    ultima = votos["votacion_id"].max()
    tam = votos[votos["votacion_id"] == ultima].groupby("grupo").size()
    todos = votos.groupby("grupo").size()
    tam = tam.reindex(todos.index, fill_value=0)
    return sorted(todos.index, key=lambda g: (-tam[g], g))


def resumen_grupos(tg: pd.DataFrame, orden: list[str]) -> pd.DataFrame:
    tg = tg[tg["posicion"].isin(EMITIDOS)]
    agg = tg.groupby("grupo").agg(
        diputados=("miembros", "last"),
        votaciones=("votacion_id", "nunique"),
        cohesion=("cohesion", "mean"),
        ganadora=("ganadora", "mean"),
        decisivo=("decisivo", "sum"),
        si=("posicion", lambda s: (s == "Sí").sum()),
        no=("posicion", lambda s: (s == "No").sum()),
        abstencion=("posicion", lambda s: (s == "Abstención").sum()),
    )
    return agg.reindex([g for g in orden if g in agg.index])


def afinidad(tg: pd.DataFrame, orden: list[str]) -> pd.DataFrame:
    """Proporción de votaciones en que dos grupos tomaron la misma posición (Sí/No/Abstención)."""
    p = tg.pivot(index="votacion_id", columns="grupo", values="posicion")
    grupos = [g for g in orden if g in p.columns]
    m = pd.DataFrame(index=grupos, columns=grupos, dtype=float)
    for a in grupos:
        for b in grupos:
            ambos = p[a].isin(EMITIDOS) & p[b].isin(EMITIDOS)
            m.loc[a, b] = (
                (p.loc[ambos, a] == p.loc[ambos, b]).mean() if ambos.any() else float("nan")
            )
    return m


# --- Diputados ---------------------------------------------------------------------------
def disidencias(votos: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    """Votos emitidos distintos de la posición del grupo (fuera del Mixto, D-05)."""
    x = votos.merge(tg[["votacion_id", "grupo", "posicion"]], on=["votacion_id", "grupo"])
    return x[
        x["voto"].isin(EMITIDOS)
        & x["posicion"].isin(EMITIDOS)
        & (x["voto"] != x["posicion"])
        & ~x["grupo"].isin(config.GRUPOS_SIN_DISCIPLINA)
    ]


def ausencias(votos: pd.DataFrame) -> pd.DataFrame:
    g = votos.groupby(["diputado", "grupo"])["voto"]
    a = pd.DataFrame({"no_vota": g.apply(lambda s: (s == config.NO_VOTA).sum()), "total": g.size()})
    a["proporcion"] = a["no_vota"] / a["total"]
    return a.reset_index().sort_values(["no_vota", "diputado"], ascending=[False, True])


# --- Todo junto --------------------------------------------------------------------------
@dataclass
class AnalisisMes:
    mes: str
    votaciones: pd.DataFrame  # con aprobada, margen, mayoria_absoluta, nominal
    grupos: pd.DataFrame  # tabla_grupos
    orden: list[str]
    resumen: pd.DataFrame
    afinidad: pd.DataFrame
    disidencias: pd.DataFrame
    ausencias: pd.DataFrame
    pendientes: list[str] = field(default_factory=list)


def analizar(mes: str, v: pd.DataFrame, votos: pd.DataFrame, pendientes=None) -> AnalisisMes:
    v = resultados(v) if not v.empty else v.assign(aprobada=[], margen=[], mayoria_absoluta=[])
    nominales = set(votos["votacion_id"])
    v["nominal"] = v["votacion_id"].isin(nominales)
    tg = tabla_grupos(v, votos) if not votos.empty else pd.DataFrame()
    orden = orden_grupos(votos)
    return AnalisisMes(
        mes=mes,
        votaciones=v,
        grupos=tg,
        orden=orden,
        resumen=resumen_grupos(tg, orden) if not tg.empty else pd.DataFrame(),
        afinidad=afinidad(tg, orden) if not tg.empty else pd.DataFrame(),
        disidencias=disidencias(votos, tg) if not tg.empty else pd.DataFrame(),
        ausencias=ausencias(votos) if not votos.empty else pd.DataFrame(),
        pendientes=list(pendientes or []),
    )
