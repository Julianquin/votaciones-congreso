"""Informe mensual en Markdown (reports/AAAA-MM.md) y el índice reports/README.md."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import almacen, config
from .analisis import AnalisisMes

ABREV = {"Sí": "Sí", "No": "No", "Abstención": "Abst.", "Dividido": "Div.", "Sin voto": "—"}
MAX_ASUNTO = 160
MARGEN_AJUSTADA = 10  # votos de diferencia (o de distancia a 176 en mayoría absoluta)


# --- Utilidades de formato ---------------------------------------------------------------
def celda(x) -> str:
    return str(x).replace("|", "\\|").replace("\n", " ").strip()


def tabla(cabecera: list[str], filas: list[list], alinear: str | None = None) -> str:
    alinear = alinear or "l" + "r" * (len(cabecera) - 1)
    sep = ["---:" if a == "r" else ":---:" if a == "c" else "---" for a in alinear]
    lineas = ["| " + " | ".join(cabecera) + " |", "| " + " | ".join(sep) + " |"]
    lineas += ["| " + " | ".join(celda(c) for c in f) + " |" for f in filas]
    return "\n".join(lineas)


def pct(x) -> str:
    return "—" if pd.isna(x) else f"{100 * x:.0f} %"


def plural(n: int, singular: str, plural_: str | None = None) -> str:
    return f"{n} {singular if n == 1 else plural_ or singular + 's'}"


def lista(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def fecha_larga(d: date) -> str:
    return f"{d.day} de {config.MESES[d.month - 1]}"


def recortar(s: str, n: int = MAX_ASUNTO) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def asunto(fila) -> str:
    base = recortar(fila["texto_expediente"] or fila["titulo"])
    extra = " ".join(x for x in (fila["titulo_subgrupo"], fila["texto_subgrupo"]) if x)
    return f"{base} *({recortar(extra, 60)})*" if extra else base


def resultado(fila) -> str:
    if fila["asentimiento"]:
        return "Aprobada por asentimiento"
    r = "Aprobada" if fila["aprobada"] else "Rechazada"
    if fila["mayoria_absoluta"]:
        r += " (may. abs.)"
    if not fila["nominal"]:
        r += " (secreta)"  # p. ej. suplicatorios: el portal no publica el voto individual
    return r


# --- Secciones ---------------------------------------------------------------------------
def _resumen(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    nom = v[v["nominal"]]
    dias = sorted(v["fecha"].unique())
    sesiones = sorted(v["sesion"].unique())
    aprob = int(v["aprobada"].sum())
    secretas = int((~v["nominal"] & ~v["asentimiento"]).sum())
    asent = int(v["asentimiento"].sum())
    notas = [plural(asent, "por asentimiento", "por asentimiento")] if asent else []
    notas += [plural(secretas, "secreta")] if secretas else []
    lineas = [
        f"- **{plural(len(v), 'votación', 'votaciones')}** en "
        f"{plural(len(dias), 'día de pleno', 'días de pleno')} "
        f"({'sesión' if len(sesiones) == 1 else 'sesiones'} {lista([str(x) for x in sesiones])}).",
        f"- **{plural(aprob, 'aprobada')}** y **{plural(len(v) - aprob, 'rechazada')}**"
        + (f"; de ellas, {' y '.join(notas)}." if notas else "."),
    ]
    if len(nom):
        ajustadas = int((nom["margen"].abs() <= 5).sum())
        lineas.append(
            f"- {plural(ajustadas, 'votación se decidió', 'votaciones se decidieron')} "
            "por 5 votos o menos."
        )
    if not a.resumen.empty:
        r = a.resumen["ganadora"]
        mejores = [config.etiqueta(g) for g in r.index[r == r.max()]]
        lineas.append(
            f"- {'El grupo' if len(mejores) == 1 else 'Los grupos'} que más veces "
            f"{'votó' if len(mejores) == 1 else 'votaron'} con el resultado final: "
            f"**{lista(mejores)}** ({pct(r.max())} de las votaciones nominales)."
        )
    if not a.disidencias.empty:
        n = len(a.disidencias)
        quien = plural(a.disidencias["diputado"].nunique(), "diputado")
        verbo = "voto individual se apartó" if n == 1 else "votos individuales se apartaron"
        lineas.append(f"- {n} {verbo} de la posición de su grupo ({quien}).")
    return lineas


def _pendientes(a: AnalisisMes) -> list[str]:
    if not a.pendientes:
        return []
    dias = ", ".join(fecha_larga(date.fromisoformat(d)) for d in a.pendientes)
    return [
        "> [!WARNING]",
        f"> El calendario del Congreso marca votaciones el {dias}, pero sus datos aún no están "
        "publicados (o lo están solo en parte). Este informe se regenerará cuando aparezcan.",
        "",
    ]


def _tabla_grupos(a: AnalisisMes) -> list[str]:
    r = a.resumen
    filas = [
        [
            config.etiqueta(g), int(x["diputados"]), pct(x["cohesion"]), pct(x["ganadora"]),
            int(x["decisivo"]), int(x["si"]), int(x["no"]), int(x["abstencion"]),
        ]
        for g, x in r.iterrows()
    ]  # fmt: skip
    cab = ["Grupo", "Diputados", "Cohesión", "Votó con el resultado", "Decisivo",
           "Posición Sí", "Posición No", "Posición Abst."]  # fmt: skip
    return [
        tabla(cab, filas),
        "",
        "*Cohesión*: índice de acuerdo interno (100 % = todo el grupo votó igual). "
        "*Votó con el resultado*: el grupo votó Sí y salió aprobada, o No y salió rechazada. "
        "*Decisivo*: votaciones cuyo resultado habría cambiado si el grupo se hubiera abstenido "
        "en bloque. El Grupo Mixto reúne partidos distintos: su posición es la de su mayoría.",
    ]


def _tabla_afinidad(a: AnalisisMes) -> list[str]:
    m = a.afinidad
    cab = [""] + [config.etiqueta(g) for g in m.columns]
    filas = [[config.etiqueta(g)] + [pct(m.loc[g, h]) for h in m.columns] for g in m.index]
    return [
        tabla(cab, filas, "l" + "c" * len(m.columns)),
        "",
        "Porcentaje de votaciones nominales en que los dos grupos tomaron la misma posición.",
    ]


def _ajustadas(a: AnalisisMes, n: int = 10) -> list[str]:
    nom = a.votaciones[a.votaciones["nominal"]].copy()
    nom["dist"] = nom["margen"].abs()
    nom = nom[nom["dist"] <= MARGEN_AJUSTADA]
    if nom.empty:
        return [f"Ninguna votación nominal se decidió por {MARGEN_AJUSTADA} votos o menos."]
    filas = [
        [fecha_larga(x["fecha"]), asunto(x), resultado(x), x["a_favor"], x["en_contra"],
         x["abstenciones"]]
        for _, x in nom.sort_values(["dist", "fecha", "numero"]).head(n).iterrows()
    ]  # fmt: skip
    return [
        tabla(["Fecha", "Asunto", "Resultado", "Sí", "No", "Abst."], filas, "llcrrr"),
        "",
        f"Votaciones nominales decididas por {MARGEN_AJUSTADA} votos o menos.",
    ]


def _por_tipo(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    t = v.groupby("titulo").agg(n=("votacion_id", "size"), aprobadas=("aprobada", "sum"))
    t = t.sort_values(["n", "aprobadas"], ascending=False)
    filas = [[tipo, int(x["n"]), int(x["aprobadas"]), int(x["n"] - x["aprobadas"])]
             for tipo, x in t.iterrows()]  # fmt: skip
    return [tabla(["Tipo de asunto", "Votaciones", "Aprobadas", "Rechazadas"], filas)]


def _disidencias(a: AnalisisMes, n: int = 15) -> list[str]:
    d = a.disidencias
    if d.empty:
        return ["Ningún diputado votó distinto de su grupo este mes (sin contar el Mixto)."]
    por = (
        d.groupby(["diputado", "grupo"])
        .agg(votos=("votacion_id", "size"))
        .reset_index()
        .sort_values(["votos", "diputado"], ascending=[False, True])
        .head(n)
    )
    filas = [[x["diputado"], config.etiqueta(x["grupo"]), x["votos"]] for _, x in por.iterrows()]
    return [
        tabla(["Diputado", "Grupo", "Votos distintos de su grupo"], filas, "llr"),
        "",
        "Un voto aislado puede ser un error al pulsar, no una decisión política: el Congreso "
        "no publica las correcciones. Se excluye el Grupo Mixto.",
    ]


def _ausencias(a: AnalisisMes, n: int = 15) -> list[str]:
    x = a.ausencias
    x = x[x["no_vota"] > 0].head(n)
    if x.empty:
        return ["Todos los diputados votaron en todas las votaciones nominales."]
    filas = [[f["diputado"], config.etiqueta(f["grupo"]), f["no_vota"], pct(f["proporcion"])]
             for _, f in x.iterrows()]  # fmt: skip
    return [
        tabla(["Diputado", "Grupo", "No votó", "% de votaciones"], filas, "llrr"),
        "",
        "«No vota» incluye ausencias justificadas (baja, maternidad o paternidad) y escaños "
        "vacantes; el portal no las distingue.",
    ]


def _todas(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    pos = (
        a.grupos.pivot(index="votacion_id", columns="grupo", values="posicion")
        if not a.grupos.empty
        else pd.DataFrame()
    )
    dec = (
        a.grupos[a.grupos["decisivo"]].groupby("votacion_id")["grupo"].apply(list)
        if not a.grupos.empty
        else pd.Series(dtype=object)
    )
    grupos = [g for g in a.orden if g in pos.columns]
    salida: list[str] = []
    for (dia, sesion), bloque in v.groupby(["fecha", "sesion"], sort=True):
        salida += [f"### {fecha_larga(dia)} (sesión {sesion})", ""]
        cab = ["Nº", "Asunto", "Resultado", "Sí", "No", "Abst."]
        cab += [config.etiqueta(g) for g in grupos] + ["Decisivos"]
        filas = []
        for _, x in bloque.sort_values("numero").iterrows():
            p = pos.loc[x["votacion_id"]] if x["votacion_id"] in pos.index else None
            celdas = [ABREV.get(p[g], p[g]) if p is not None else "" for g in grupos]
            decisivos = ", ".join(config.etiqueta(g) for g in dec.get(x["votacion_id"], []))
            numero = f"[{x['numero']}]({x['url']})" if x["url"] else x["numero"]
            filas.append(
                [numero, asunto(x), resultado(x), x["a_favor"], x["en_contra"], x["abstenciones"],
                 *celdas, decisivos]
            )  # fmt: skip
        salida += [tabla(cab, filas, "rllrrr" + "c" * len(grupos) + "l"), ""]
    return salida


# --- Documento ---------------------------------------------------------------------------
def componer(a: AnalisisMes, generado: datetime | None = None) -> str:
    generado = generado or datetime.now()
    titulo = f"# Votaciones del Congreso: {almacen.nombre_mes(a.mes)}"
    pie = (
        f"_Generado automáticamente el {generado:%Y-%m-%d} con datos abiertos del "
        f"[Congreso de los Diputados]({config.URL_VOTACIONES}). Solo plenos y Diputación "
        "Permanente. Método y límites en [docs/DOCUMENTO_FUNCIONAL.md]"
        "(../docs/DOCUMENTO_FUNCIONAL.md)._"
    )
    if a.votaciones.empty:
        vacio = (
            "Todavía no hay datos publicados de este mes."
            if a.pendientes
            else "No hubo votaciones en el Pleno este mes."
        )
        return "\n".join([titulo, "", *_pendientes(a), vacio, "", pie, ""])
    partes = [titulo, "", pie, "", *_pendientes(a), "## Resumen", "", *_resumen(a), ""]
    if not a.resumen.empty:
        partes += ["## Cómo votó cada grupo", "", *_tabla_grupos(a), ""]
        partes += ["## Afinidad entre grupos", "", *_tabla_afinidad(a), ""]
        partes += ["## Votaciones más ajustadas", "", *_ajustadas(a), ""]
    partes += ["## Qué se votó, por tipo de asunto", "", *_por_tipo(a), ""]
    if not a.resumen.empty:
        partes += ["## Votos distintos de su grupo", "", *_disidencias(a), ""]
        partes += ["## Diputados que más veces no votaron", "", *_ausencias(a), ""]
    partes += [
        "## Todas las votaciones",
        "",
        "Posición de cada grupo: la opción que votó la mayoría de sus diputados "
        "(*Div.*: empate dentro del grupo). El número enlaza al JSON oficial.",
        "",
        *_todas(a),
    ]
    return "\n".join(partes).rstrip() + "\n"


def escribir(a: AnalisisMes, informes: Path | None = None) -> Path:
    carpeta = informes or config.INFORMES
    carpeta.mkdir(parents=True, exist_ok=True)
    p = carpeta / f"{a.mes}.md"
    p.write_text(componer(a), encoding="utf-8")
    return p


def escribir_indice(
    manifiesto: dict, informes: Path | None = None, datos: Path | None = None
) -> Path:
    carpeta = informes or config.INFORMES
    carpeta.mkdir(parents=True, exist_ok=True)
    filas = []
    for mes in sorted((p.stem for p in carpeta.glob("????-??.md")), reverse=True):
        v, _ = almacen.cargar_mes(mes, datos)
        pend = len(almacen.dias_pendientes(manifiesto, mes))
        estado = f"{plural(pend, 'día pendiente', 'días pendientes')}" if pend else "Completo"
        filas.append([f"[{almacen.nombre_mes(mes)}]({mes}.md)", len(v), estado])
    texto = "\n".join(
        [
            "# Informes mensuales",
            "",
            "Un informe por mes con las votaciones del Pleno del Congreso. Se generan solos "
            "cada mes (ver `.github/workflows/mensual.yml`).",
            "",
            tabla(["Mes", "Votaciones", "Datos"], filas, "lrl"),
            "",
        ]
    )
    p = carpeta / "README.md"
    p.write_text(texto, encoding="utf-8")
    return p
