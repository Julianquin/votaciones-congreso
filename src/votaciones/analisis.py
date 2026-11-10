"""Métricas de un mes de votaciones. Todas las definiciones están en docs/DECISIONS.md.

Entradas: el DataFrame de votaciones y el de votos de almacen.cargar_mes. Nada de red.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

EMITIDOS = list(config.VOTOS_EMITIDOS)


# --- Resultado de cada votación ----------------------------------------------------------
RE_CONSTITUCIONAL = re.compile(r"reforma (?:constitucional|del artículo \d+ de la constitución)")
RE_ORGANICA = re.compile(
    r"(?:proyecto|proposición) de ley orgánica|, orgánica |carácter orgánico"
    r"|estatuto de autonomía|reglamento del congreso"
)


def umbral_mayoria(v: pd.DataFrame) -> pd.Series:
    """Votos a favor necesarios: 0 = mayoría simple (Sí > No). Reglas en D-06."""
    t = (
        v["titulo"] + " " + v["titulo_subgrupo"] + " " + v["texto_subgrupo"] + " "
        + v["texto_expediente"]
    ).str.lower()  # fmt: skip
    conjunto = t.str.contains("conjunto", regex=False)
    umbral = pd.Series(0, index=v.index)
    umbral = umbral.mask(t.str.contains("investidura", regex=False), config.MAYORIA_ABSOLUTA)
    umbral = umbral.mask(conjunto & t.str.contains(RE_ORGANICA), config.MAYORIA_ABSOLUTA)
    umbral = umbral.mask(conjunto & t.str.contains(RE_CONSTITUCIONAL), config.TRES_QUINTOS)
    return umbral.where(~v["asentimiento"], 0).astype(int)


def resultados(v: pd.DataFrame) -> pd.DataFrame:
    """Añade umbral, aprobada y margen. El portal no publica el resultado: se calcula."""
    v = v.copy()
    v["umbral"] = umbral_mayoria(v)
    cualificada = v["umbral"] > 0
    simple = v["a_favor"] > v["en_contra"]
    v["aprobada"] = v["asentimiento"] | simple.where(~cualificada, v["a_favor"] >= v["umbral"])
    v["margen"] = (v["a_favor"] - v["en_contra"]).where(~cualificada, v["a_favor"] - v["umbral"])
    # Un empate con mayoría simple obliga a repetir la votación (art. 88 del Reglamento): no es
    # un rechazo. Cuenta como no aprobada en las métricas, pero el informe lo dice.
    v["empate"] = ~cualificada & ~v["asentimiento"] & (v["a_favor"] == v["en_contra"])
    v["empate"] &= v["a_favor"] > 0
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
    r = resultados(v).set_index("votacion_id")[["a_favor", "en_contra", "aprobada", "umbral"]]
    c = c.join(r, on="votacion_id")
    c["ganadora"] = ((c["posicion"] == "Sí") & c["aprobada"]) | (
        (c["posicion"] == "No") & ~c["aprobada"]
    )
    # Decisivo (D-04): si el grupo se hubiera abstenido en bloque, el resultado cambiaría.
    cualificada = c["umbral"] > 0
    sin_si = c["a_favor"] - c["Sí"]
    decide_si = (c["posicion"] == "Sí") & c["aprobada"] & (
        (sin_si <= c["en_contra"]).where(~cualificada, sin_si < c["umbral"])
    )  # fmt: skip
    decide_no = (
        (c["posicion"] == "No") & ~c["aprobada"] & ~cualificada
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


# --- Mapa de diputados (D-13) -----------------------------------------------------------
CODIGO_VOTO = {"Sí": 1.0, "No": -1.0, "Abstención": 0.0}


@dataclass
class Mapa:
    puntos: pd.DataFrame  # diputado, grupo, x, y, participacion
    varianza: tuple[float, float]  # proporción explicada por cada eje
    votaciones: int  # votaciones con desacuerdo usadas


def mapa_diputados(votos: pd.DataFrame, min_participacion: float | None = None) -> Mapa | None:
    """Componentes principales de la matriz diputado × votación (Sí 1, No −1, Abst. 0).

    Las votaciones unánimes no aportan y se quitan; quien votó en menos de
    ``min_participacion`` de las restantes no se sitúa. El signo de cada eje es arbitrario: se
    orienta para que el grupo de referencia quede en positivo (convención, no ideología).
    """
    minimo = config.MAPA_MIN_PARTICIPACION if min_participacion is None else min_participacion
    x = votos[votos["voto"].isin(list(CODIGO_VOTO))]
    if x.empty:
        return None
    m = x.assign(v=x["voto"].map(CODIGO_VOTO)).pivot_table(
        index="diputado", columns="votacion_id", values="v", aggfunc="first"
    )
    m = m.loc[:, m.std(skipna=True).fillna(0) > 0]
    if m.shape[1] < config.MAPA_MIN_VOTACIONES:
        return None
    participacion = m.notna().sum(axis=1) / m.shape[1]
    m = m[participacion >= minimo]
    if len(m) < 3:
        return None
    z = (m - m.mean()).fillna(0.0).to_numpy()
    u, s, _ = np.linalg.svd(z, full_matrices=False)
    coords = u[:, :2] * s[:2]
    grupo = votos.sort_values("votacion_id").groupby("diputado")["grupo"].last()
    p = pd.DataFrame(
        {
            "diputado": m.index,
            "grupo": grupo.reindex(m.index).to_numpy(),
            "x": coords[:, 0],
            "y": coords[:, 1],
            "participacion": participacion.reindex(m.index).to_numpy(),
        }
    )
    for eje in ("x", "y"):
        ref = p.loc[p["grupo"].isin(config.GRUPOS_REFERENCIA_EJES), eje].mean()
        if pd.notna(ref) and ref < 0:
            p[eje] = -p[eje]
        escala = p[eje].abs().max()
        if escala > 0:
            p[eje] = p[eje] / escala
    var = s**2 / (s**2).sum()
    return Mapa(p, (float(var[0]), float(var[1]) if len(var) > 1 else 0.0), m.shape[1])


def orden_espacial(mapa: Mapa | None, orden: list[str]) -> list[str]:
    """Grupos según la media de sus diputados en el eje 1; los que no salen en el mapa, al final."""
    if mapa is None:
        return list(orden)
    medias = mapa.puntos.groupby("grupo")["x"].mean()
    con = sorted((g for g in orden if g in medias.index), key=lambda g: medias[g])
    return con + [g for g in orden if g not in medias.index]


# --- Mayorías y Gobierno -----------------------------------------------------------------
def mayorias(v: pd.DataFrame, tg: pd.DataFrame, orden: list[str]) -> pd.DataFrame:
    """Combinaciones de grupos con posición Sí en las votaciones nominales aprobadas."""
    if tg.empty:
        return pd.DataFrame(columns=["grupos", "votaciones"])
    aprobadas = v.loc[v["nominal"] & v["aprobada"], "votacion_id"]
    si = tg[tg["votacion_id"].isin(aprobadas) & (tg["posicion"] == "Sí")]
    combos = si.groupby("votacion_id")["grupo"].apply(
        lambda s: tuple(g for g in orden if g in set(s))
    )
    n = combos.value_counts()
    return pd.DataFrame({"grupos": list(n.index), "votaciones": n.to_numpy()})


def gobierno(v: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    """Posición común de los grupos del Gobierno en cada votación nominal (D-14).

    Columnas: votacion_id, posicion («Sí», «No», «Abstención» o «Dividido» si no coinciden),
    gana y pierde. Un empate no es ni lo uno ni lo otro: se repite. Vacío si la legislatura no
    tiene grupos de Gobierno declarados en config.
    """
    filas = []
    if tg.empty:
        return pd.DataFrame(columns=["votacion_id", "posicion", "gana", "pierde"])
    pos = tg.pivot(index="votacion_id", columns="grupo", values="posicion")
    for _, x in v[v["nominal"]].iterrows():
        grupos = config.GOBIERNO.get(int(x["legislatura"]), ())
        if not grupos or not all(g in pos.columns for g in grupos):
            continue
        ps = {pos.loc[x["votacion_id"], g] for g in grupos}
        comun = ps.pop() if len(ps) == 1 else "Dividido"
        gana = (comun == "Sí" and x["aprobada"]) or (comun == "No" and not x["aprobada"])
        pierde = comun in ("Sí", "No") and not gana and not x.get("empate", False)
        filas.append(
            {"votacion_id": x["votacion_id"], "posicion": comun, "gana": bool(gana),
             "pierde": bool(pierde)}
        )  # fmt: skip
    return pd.DataFrame(filas, columns=["votacion_id", "posicion", "gana", "pierde"])


RE_LLAMAMIENTO = re.compile(r"\(\s*pública por llamamiento\s*\)", re.I)


def clave_asunto(texto: str) -> str:
    """El mismo asunto aunque una votación diga «(Pública por llamamiento)» y otra no."""
    t = RE_LLAMAMIENTO.sub("", str(texto)).lower()
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())


def destacadas(a: AnalisisMes, n: int | None = None) -> pd.DataFrame:
    """Las votaciones más relevantes del mes para el informe principal, una por asunto (D-19).

    Puntuación = peso del tipo de asunto + 3 si fue ajustada + 2 si la perdió el Gobierno + 2 si
    exigía mayoría reforzada − 3 si nadie votó en contra − 2 si fue casi unánime (más de
    config.CASI_UNANIME votos de diferencia). Un empate se sustituye por su
    repetición (otra votación del mismo asunto, ese mismo día, con número mayor).
    """
    n = config.DESTACADAS if n is None else n
    v = a.votaciones[~a.votaciones["asentimiento"]].copy()
    if v.empty:
        return v
    pierde = (
        set(a.gobierno.loc[a.gobierno["pierde"], "votacion_id"]) if not a.gobierno.empty else set()
    )
    v["puntos"] = (
        v["categoria"].map(config.PESO_CATEGORIA).fillna(1)
        + 3 * (v["margen"].abs() <= config.MARGEN_AJUSTADA)
        + 2 * v["votacion_id"].isin(pierde)
        + 2 * (v["umbral"] > 0)
        - 3 * (v["en_contra"] == 0)
        - 2 * ((v["a_favor"] - v["en_contra"]).abs() > config.CASI_UNANIME)
    )
    v["asunto"] = v["texto_expediente"].map(clave_asunto)
    # Empates con repetición: fuera.
    repetidas = v.groupby(["fecha", "asunto"])["numero"].transform("max")
    v = v[~(v["empate"] & (v["numero"] < repetidas))]
    v["dist"] = v["margen"].abs()
    v = v.sort_values(["puntos", "dist", "fecha", "numero"], ascending=[False, True, True, True])
    v["votaciones_asunto"] = v.groupby("asunto")["votacion_id"].transform("size")
    v = v.drop_duplicates("asunto")
    return v.head(n).sort_values(["fecha", "numero"])


def quien_voto(a: AnalisisMes, votacion_id: str) -> dict[str, list[str]]:
    """Grupos por su posición en una votación: {"Sí": [...], "No": [...], ...}.

    Un grupo que votó en bloque, o casi (al menos el 75 % de sus votos), va con su posición; si no
    fue unánime se añade la cuenta: «Sumar (19 de 23)». El Mixto, que reúne partidos distintos, y
    los grupos sin mayoría clara van en "mezcla" con su reparto.
    """
    g = a.grupos[a.grupos["votacion_id"] == votacion_id].set_index("grupo")
    salida: dict[str, list[str]] = {"Sí": [], "No": [], "Abstención": [], "mezcla": []}
    for grupo in a.orden:
        if grupo not in g.index:
            continue
        x = g.loc[grupo]
        emitidos = {o: int(x[o]) for o in EMITIDOS if x[o]}
        total = sum(emitidos.values())
        pos = x["posicion"]
        unanime = len(emitidos) == 1
        casi = grupo not in config.GRUPOS_SIN_DISCIPLINA and emitidos.get(pos, 0) >= 0.75 * total
        claro = pos in EMITIDOS and (unanime or casi)
        if claro:
            nombre = "Grupo Mixto" if grupo == "GMx" else config.etiqueta(grupo)
            if emitidos[pos] < total:
                nombre += f" ({emitidos[pos]} de {total})"
            salida[pos].append(nombre)
        elif emitidos:
            reparto = ", ".join(f"{k} {n}" for k, n in emitidos.items())
            nombre = "Grupo Mixto" if grupo == "GMx" else config.etiqueta(grupo)
            salida["mezcla"].append(f"{nombre} ({reparto})")
    return salida


def categoria(titulo: str) -> str:
    t = titulo.lower()
    for patron, nombre in config.CATEGORIAS:
        if re.search(patron, t):
            return nombre
    return "Otros"


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
    votaciones: pd.DataFrame  # con umbral, aprobada, margen, nominal, categoria
    grupos: pd.DataFrame  # tabla_grupos
    orden: list[str]  # por tamaño: tablas
    resumen: pd.DataFrame
    afinidad: pd.DataFrame
    disidencias: pd.DataFrame
    ausencias: pd.DataFrame
    votos: pd.DataFrame = field(default_factory=pd.DataFrame)
    mapa: Mapa | None = None
    orden_espacial: list[str] = field(default_factory=list)  # por el eje 1: gráficos
    mayorias: pd.DataFrame = field(default_factory=pd.DataFrame)
    gobierno: pd.DataFrame = field(default_factory=pd.DataFrame)
    pendientes: list[str] = field(default_factory=list)


def analizar(mes: str, v: pd.DataFrame, votos: pd.DataFrame, pendientes=None) -> AnalisisMes:
    v = resultados(v) if not v.empty else v.assign(aprobada=[], margen=[], umbral=[])
    nominales = set(votos["votacion_id"])
    v["nominal"] = v["votacion_id"].isin(nominales)
    v["categoria"] = v["titulo"].map(categoria) if not v.empty else []
    tg = tabla_grupos(v, votos) if not votos.empty else pd.DataFrame()
    orden = orden_grupos(votos)
    mapa = mapa_diputados(votos) if not votos.empty else None
    return AnalisisMes(
        mes=mes,
        votaciones=v,
        grupos=tg,
        orden=orden,
        resumen=resumen_grupos(tg, orden) if not tg.empty else pd.DataFrame(),
        afinidad=afinidad(tg, orden) if not tg.empty else pd.DataFrame(),
        disidencias=disidencias(votos, tg) if not tg.empty else pd.DataFrame(),
        ausencias=ausencias(votos) if not votos.empty else pd.DataFrame(),
        votos=votos,
        mapa=mapa,
        orden_espacial=orden_espacial(mapa, orden),
        mayorias=mayorias(v, tg, orden),
        gobierno=gobierno(v, tg),
        pendientes=list(pendientes or []),
    )
