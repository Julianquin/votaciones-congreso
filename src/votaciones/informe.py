"""Informe mensual en Markdown (reports/AAAA-MM.md) y el índice reports/README.md."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import almacen, analisis, config, graficos, lenguaje
from .analisis import AnalisisMes

ABREV = {"Sí": "Sí", "No": "No", "Abstención": "Abst.", "Dividido": "Div.", "Sin voto": "—"}
MAX_ASUNTO = 160
MARGEN_AJUSTADA = config.MARGEN_AJUSTADA
HEMICICLOS = 4  # votaciones ajustadas que se dibujan cada mes
ANTIGUEDAD_SIN_DATOS = 90  # días: un pendiente más viejo se da por no publicado


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
    partes = [x for x in (fila["titulo_subgrupo"], fila["texto_subgrupo"]) if x]
    if len(partes) == 2 and partes[0].rstrip(".") == partes[1].rstrip("."):
        partes = partes[:1]
    extra = " ".join(partes)
    return f"{base} *({recortar(extra, 60)})*" if extra else base


def resultado(fila) -> str:
    if fila["asentimiento"]:
        return "Aprobada por asentimiento"
    if fila.get("empate"):
        return "Empate (se repite)"
    r = "Aprobada" if fila["aprobada"] else "Rechazada"
    if fila["umbral"]:
        r += f" (necesita {fila['umbral']})"
    if fila.get("llamamiento"):
        r += " (por llamamiento)"  # voto individual solo en el Diario de Sesiones
    elif not fila["nominal"]:
        r += " (secreta)"  # p. ej. suplicatorios: el portal no publica el voto individual
    return r


# --- Secciones ---------------------------------------------------------------------------
def _resumen(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    nom = v[v["nominal"]]
    dias = sorted(v["fecha"].unique())
    sesiones = sorted(v["sesion"].unique())
    aprob = int(v["aprobada"].sum())
    empates = int(v["empate"].sum()) if "empate" in v else 0
    llam = int(v["llamamiento"].sum()) if "llamamiento" in v else 0
    secretas = int((~v["nominal"] & ~v["asentimiento"]).sum()) - llam
    asent = int(v["asentimiento"].sum())
    notas = [plural(asent, "por asentimiento", "por asentimiento")] if asent else []
    notas += [plural(llam, "pública por llamamiento", "públicas por llamamiento")] if llam else []
    notas += [plural(secretas, "secreta")] if secretas else []
    balance = (
        f"**{plural(aprob, 'aprobada')}** y **{plural(len(v) - aprob - empates, 'rechazada')}**"
    )
    if empates:
        balance += f", más {plural(empates, 'empate')} que obligaron a repetir"
    lineas = [
        f"- **{plural(len(v), 'votación', 'votaciones')}** en "
        f"{plural(len(dias), 'día de pleno', 'días de pleno')} "
        f"({'sesión' if len(sesiones) == 1 else 'sesiones'} {lista([str(x) for x in sesiones])}).",
        f"- {balance}" + (f"; de ellas, {', '.join(notas)}." if notas else "."),
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
    gob = a.gobierno
    unidos = gob[gob["posicion"].isin(["Sí", "No"])] if not gob.empty else gob
    if len(unidos):
        perdidas = int(unidos["pierde"].sum())
        cuantas = {0: "no perdieron ninguna", 1: "perdieron una"}.get(
            perdidas, f"perdieron {perdidas}"
        )
        lineas.append(
            f"- Los grupos del Gobierno ({nombres_gobierno(a)}) votaron lo mismo en "
            f"{len(unidos)} de {len(gob)} votaciones nominales y {cuantas} de ellas."
        )
    if not a.disidencias.empty:
        n = len(a.disidencias)
        quien = plural(a.disidencias["diputado"].nunique(), "diputado")
        verbo = "voto individual se apartó" if n == 1 else "votos individuales se apartaron"
        lineas.append(f"- {n} {verbo} de la posición de su grupo ({quien}).")
    return lineas


def nombres_gobierno(a: AnalisisMes) -> str:
    legs = a.votaciones["legislatura"]
    grupos = config.GOBIERNO.get(int(legs.mode().iloc[0]), ()) if len(legs) else ()
    return lista([config.etiqueta(g) for g in grupos]) if grupos else ""


def imagen(par: tuple[str, str] | None, alt: str, ancho: int = 720) -> list[str]:
    """<picture> con la versión oscura para quien lea GitHub en tema oscuro."""
    if not par:
        return []
    claro, oscuro = par
    alt = alt.replace('"', "'")
    return [
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" srcset="{oscuro}">',
        f'  <img src="{claro}" alt="{alt}" width="{ancho}">',
        "</picture>",
        "",
    ]


def _pendientes(a: AnalisisMes, hoy: date | None = None) -> list[str]:
    if not a.pendientes:
        return []
    hoy = hoy or date.today()
    fechas = [date.fromisoformat(d) for d in a.pendientes]
    recientes = [d for d in fechas if (hoy - d).days <= ANTIGUEDAD_SIN_DATOS]
    viejas = [d for d in fechas if (hoy - d).days > ANTIGUEDAD_SIN_DATOS]
    salida = []
    if recientes:
        dias = lista([fecha_larga(d) for d in recientes])
        salida += [
            "> [!WARNING]",
            f"> El calendario del Congreso marca votaciones el {dias}, pero sus datos aún no "
            "están publicados (o lo están solo en parte). Este informe se regenerará cuando "
            "aparezcan.",
            "",
        ]
    if viejas:
        dias = lista([fecha_larga(d) for d in viejas])
        salida += [
            "> [!NOTE]",
            f"> Del {dias} falta alguna votación en los datos abiertos del Congreso (solo hay "
            "una imagen). No se incluye en este informe.",
            "",
        ]
    return salida


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


def _tabla_afinidad(a: AnalisisMes, imagenes: dict) -> list[str]:
    m = a.afinidad
    cab = [""] + [config.etiqueta(g) for g in m.columns]
    filas = [[config.etiqueta(g)] + [pct(m.loc[g, h]) for h in m.columns] for g in m.index]
    texto = "Porcentaje de votaciones nominales en que los dos grupos tomaron la misma posición."
    if not imagenes.get("afinidad"):
        return [tabla(cab, filas, "l" + "c" * len(m.columns)), "", texto]
    return [
        *imagen(imagenes["afinidad"], "Mapa de calor de la afinidad entre grupos", 560),
        texto + " Los grupos están ordenados según el mapa de diputados.",
        "",
        "<details><summary>Ver la tabla</summary>",
        "",
        tabla(cab, filas, "l" + "c" * len(m.columns)),
        "",
        "</details>",
    ]


def _mapa(a: AnalisisMes, imagenes: dict) -> list[str]:
    if not imagenes.get("mapa") or a.mapa is None:
        return []
    v1, v2 = a.mapa.varianza
    fuera = a.votos["diputado"].nunique() - len(a.mapa.puntos)
    return [
        *imagen(imagenes["mapa"], "Mapa de diputados según su voto, un panel por grupo"),
        "Cada punto es un diputado; dos diputados están cerca si votaron parecido. Un punto "
        "más grande reúne a varios que votaron exactamente igual. En cada panel, el grupo en "
        "azul y el resto del Congreso en gris.",
        "",
        f"*Cómo se calcula*: componentes principales de los votos (Sí, No, abstención) en "
        f"{a.mapa.votaciones} votaciones con algún desacuerdo. El eje horizontal recoge el "
        f"{100 * v1:.0f} % de la variación y el vertical el {100 * v2:.0f} %. Los ejes no "
        "tienen nombre ni sentido político propio; por convención, el PP queda a la derecha."
        + (f" No se sitúa a {plural(fuera, 'diputado')} que votó en menos de la mitad."
           if fuera > 0 else ""),
    ]  # fmt: skip


def _mayorias(a: AnalisisMes, n: int = 8) -> list[str]:
    m = a.mayorias
    if m.empty:
        return ["Ninguna votación nominal salió aprobada este mes."]
    escanos = a.resumen["diputados"] if not a.resumen.empty else pd.Series(dtype=int)
    todos = set(a.orden)
    filas = []
    for _, x in m.head(n).iterrows():
        grupos = list(x["grupos"])
        nombre = (
            "Todos los grupos"
            if set(grupos) == todos
            else " + ".join(config.etiqueta(g) for g in grupos)
        )
        filas.append([nombre, x["votaciones"], int(sum(escanos.get(g, 0) for g in grupos))])
    resto = int(m["votaciones"].iloc[n:].sum())
    total = int(m["votaciones"].sum())
    pie = f"De {plural(total, 'votación nominal aprobada', 'votaciones nominales aprobadas')}."
    if resto:
        pie += f" Otras {resto} salieron con combinaciones que se dieron menos veces."
    return [
        tabla(["Grupos que votaron Sí", "Votaciones", "Escaños"], filas, "lrr"),
        "",
        pie + " La posición de cada grupo es la de la mayoría de sus diputados.",
    ]


def _gobierno(a: AnalisisMes, n: int = 15) -> list[str]:
    gob = a.gobierno
    if gob.empty:
        return []
    nombres = nombres_gobierno(a)
    perdidas = gob[gob["pierde"]]
    distintos = int((gob["posicion"] == "Dividido").sum())
    lineas = []
    if perdidas.empty:
        lineas.append(f"{nombres} no perdieron ninguna votación en la que votaran lo mismo.")
    else:
        v = a.votaciones.set_index("votacion_id")
        filas = []
        for _, g in perdidas.head(n).iterrows():
            x = v.loc[g["votacion_id"]]
            filas.append([fecha_larga(x["fecha"]), asunto(x), x["categoria"], g["posicion"],
                          resultado(x), x["a_favor"], x["en_contra"]])  # fmt: skip
        lineas += [
            tabla(
                ["Fecha", "Asunto", "Tipo", f"{nombres} votaron", "Resultado", "Sí", "No"],
                filas,
                "lllclrr",
            ),  # fmt: skip
            "",
        ]
        if len(perdidas) > n:
            lineas += [f"Y {len(perdidas) - n} más (ver «Todas las votaciones»).", ""]
    if distintos:
        lineas.append(
            f"Además, {nombres} votaron distinto entre sí en "
            f"{plural(distintos, 'votación', 'votaciones')}."
        )
    return lineas


def _ajustadas(a: AnalisisMes, imagenes: dict, n: int = 10) -> list[str]:
    nom = graficos.ajustadas(a, n, MARGEN_AJUSTADA, solo_nominales=False)
    if nom.empty:
        return [f"Ninguna votación se decidió por {MARGEN_AJUSTADA} votos o menos."]
    salida = []
    for vid, par in imagenes.get("hemiciclos", {}).items():
        x = a.votaciones.set_index("votacion_id").loc[vid]
        salida += [
            f"**{fecha_larga(x['fecha'])}** · {asunto(x)}",
            "",
            *imagen(par, f"Hemiciclo: {x['a_favor']} a favor y {x['en_contra']} en contra", 640),
        ]
    filas = [
        [fecha_larga(x["fecha"]), asunto(x), resultado(x), x["a_favor"], x["en_contra"],
         x["abstenciones"]]
        for _, x in nom.iterrows()
    ]  # fmt: skip
    if salida:
        salida += [
            "Cada punto es un escaño, agrupado por grupo parlamentario; el color es su voto.",
            "",
        ]
    return [
        *salida,
        tabla(["Fecha", "Asunto", "Resultado", "Sí", "No", "Abst."], filas, "llcrrr"),
        "",
        f"Votaciones decididas por {MARGEN_AJUSTADA} votos o menos (o a esa distancia de la "
        "mayoría que exigían). Las públicas por llamamiento no tienen hemiciclo: el voto de cada "
        "diputado solo consta en el Diario de Sesiones.",
    ]


def _por_tipo(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    t = v.groupby("categoria").agg(n=("votacion_id", "size"), aprobadas=("aprobada", "sum"))
    t = t.sort_values(["n", "aprobadas"], ascending=False)
    filas = [[tipo, int(x["n"]), int(x["aprobadas"]), int(x["n"] - x["aprobadas"])]
             for tipo, x in t.iterrows()]  # fmt: skip
    return [
        tabla(["Tipo de asunto", "Votaciones", "Aprobadas", "No aprobadas"], filas),
        "",
        "Las proposiciones no de ley y las mociones expresan la posición del Congreso pero no "
        "obligan al Gobierno. Las leyes pasan por varias votaciones (toma en consideración, "
        "totalidad, dictamen, Senado), así que una misma ley puede aparecer varias veces.",
    ]


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
def componer_detalle(
    a: AnalisisMes, generado: datetime | None = None, imagenes: dict | None = None
) -> str:
    generado = generado or datetime.now()
    imagenes = imagenes or {}
    hoy = generado.date()
    titulo = f"# Análisis detallado: {almacen.nombre_mes(a.mes)}"
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
        return "\n".join([titulo, "", *_pendientes(a, hoy), vacio, "", pie, ""])
    volver = f"[← Volver al resumen del mes]({a.mes}.md)"
    partes = [
        titulo,
        "",
        volver,
        "",
        pie,
        "",
        *_pendientes(a, hoy),
        "## Resumen",
        "",
        *_resumen(a),
        "",
    ]
    if not a.resumen.empty:
        partes += ["## Cómo votó cada grupo", "", *_tabla_grupos(a), ""]
        mapa = _mapa(a, imagenes)
        if mapa:
            partes += ["## Mapa de diputados", "", *mapa, ""]
        partes += ["## Afinidad entre grupos", "", *_tabla_afinidad(a, imagenes), ""]
        partes += ["## Quién sacó adelante las votaciones", "", *_mayorias(a), ""]
        gobierno = _gobierno(a)
        if gobierno:
            partes += ["## Votaciones que perdieron los grupos del Gobierno", "", *gobierno, ""]
        partes += ["## Votaciones más ajustadas", "", *_ajustadas(a, imagenes), ""]
    partes += ["## Qué se votó, por tipo de asunto", "", *_por_tipo(a), ""]
    if not a.resumen.empty:
        partes += ["## Votos distintos de su grupo", "", *_disidencias(a), ""]
        partes += ["## Diputados que más veces no votaron", "", *_ausencias(a), ""]
    partes += [
        "## Todas las votaciones",
        "",
        "Posición de cada grupo: la opción que votó la mayoría de sus diputados "
        "(*Div.*: empate dentro del grupo). El número enlaza al JSON oficial o, en las "
        "votaciones por llamamiento, al Diario de Sesiones.",
        "",
        *_todas(a),
    ]
    return "\n".join(partes).rstrip() + "\n"


# --- Informe principal: para cualquier ciudadano (D-19) -----------------------------------
VINCULANTES = (
    "Investidura", "Decretos-ley (convalidación)", "Leyes: toma en consideración",
    "Enmiendas a la totalidad", "Leyes: dictamen y votación final", "Leyes: enmiendas del Senado",
    "Leyes: veto del Senado",
    "Presupuestos y estabilidad",
)  # fmt: skip


def distancia(fila) -> str:
    """«por 2 votos», «le faltaron 5 votos para los 176», «superó los 176 por 3»."""
    umbral = int(fila.get("umbral") or 0)
    si, no = int(fila["a_favor"]), int(fila["en_contra"])
    if umbral:
        d = si - umbral
        votos = plural(abs(d), "voto")
        if d > 0:
            return f"superó los {umbral} síes por {votos}"
        if d == 0:
            return f"llegó justo a los {umbral} síes"
        return f"le faltaron {votos} para los {umbral}"
    return f"por {plural(abs(si - no), 'voto')}"


def _pocas_palabras(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    aprob = int(v["aprobada"].sum())
    empates = int(v["empate"].sum()) if "empate" in v else 0
    rech = len(v) - aprob - empates
    dias = v["fecha"].nunique()
    salieron = plural(aprob, "propuesta salió", "propuestas salieron")
    cierre = f"; hubo además {plural(empates, 'empate')}, que se repiten." if empates else "."
    lineas = [
        f"- El Congreso votó **{plural(len(v), 'vez', 'veces')}** en "
        f"{plural(dias, 'día de pleno', 'días de pleno')}. **{salieron} adelante** y {rech} no"
        + cierre
    ]
    leyes = int(v["categoria"].isin(VINCULANTES).sum())
    peticiones = int(v["categoria"].isin(lenguaje.NO_OBLIGA).sum())
    if leyes or peticiones:
        frase = f"- {plural(leyes, 'votación fue', 'votaciones fueron')} sobre leyes, decretos o "
        frase += "presupuestos."
        if peticiones:
            frase += (
                f" Otras {peticiones} fueron peticiones al Gobierno que no le obligan "
                "(proposiciones no de ley y mociones)."
            )
        lineas.append(frase)
    gob = a.gobierno
    unidos = gob[gob["posicion"].isin(["Sí", "No"])] if not gob.empty else gob
    if len(unidos):
        p = int(unidos["pierde"].sum())
        cuantas = "no perdió ninguna" if p == 0 else f"perdió **{p}**"
        lineas.append(
            f"- El Gobierno ({nombres_gobierno(a)}) {cuantas} de las {len(unidos)} votaciones en "
            "las que sus grupos votaron lo mismo."
        )
    con_votos = v[(v["nominal"] | v.get("llamamiento", False)) & ~v["empate"]]
    if len(con_votos):
        x = con_votos.assign(d=con_votos["margen"].abs()).sort_values(["d", "fecha"]).iloc[0]
        lineas.append(
            f"- La votación más reñida se decidió {distancia(x)}: "
            f"{lenguaje.titulo_llano(x['texto_expediente'] or x['titulo'], 120)}."
        )
    if not a.disidencias.empty:
        n = len(a.disidencias)
        lineas.append(
            f"- Los diputados casi siempre votan lo mismo que su grupo: en todo el mes solo hubo "
            f"{plural(n, 'voto distinto', 'votos distintos')} (sin contar el Grupo Mixto)."
        )
    return lineas


def _destacadas(a: AnalisisMes, dest: pd.DataFrame, imagenes: dict) -> list[str]:
    salida = []
    pares = imagenes.get("destacadas", {})
    for i, (_, x) in enumerate(dest.iterrows(), start=1):
        titulo = lenguaje.titulo_llano(x["texto_expediente"] or x["titulo"])
        salida += [f"### {i}. {titulo}", ""]
        salida += [f"**{fecha_larga(x['fecha'])} · {x['categoria']}.** "
                   f"{lenguaje.explicacion(x['categoria'])}", ""]  # fmt: skip
        salida += imagen(pares.get(x["votacion_id"]), f"Resultado: {x['a_favor']} a favor y "
                         f"{x['en_contra']} en contra", 640)  # fmt: skip
        if x.get("empate"):
            salida.append(f"**= Empate** a {x['a_favor']}: la votación se repitió.")
        else:
            res = "✔ Salió adelante" if x["aprobada"] else "✘ No salió adelante"
            salida.append(
                f"**{res}** {distancia(x)}: {x['a_favor']} a favor, {x['en_contra']} en contra y "
                + (
                    f"{plural(int(x['abstenciones']), 'abstención', 'abstenciones')}."
                    if int(x["abstenciones"])
                    else "ninguna abstención."
                )
            )
        salida.append("")
        if x["nominal"]:
            q = analisis.quien_voto(a, x["votacion_id"])
            rotulos = (("Sí", "A favor"), ("No", "En contra"), ("Abstención", "Se abstuvieron"),
                       ("mezcla", "Repartidos"))  # fmt: skip
            for clave, nombre in rotulos:
                if q[clave]:
                    salida.append(f"- **{nombre}:** {lista(q[clave])}")
            salida.append("")
        elif x.get("llamamiento"):
            salida += [
                "Fue una votación por llamamiento: cada diputado dijo su voto en voz alta. El voto "
                f"de cada uno está en el [Diario de Sesiones]({x['url']}).",
                "",
            ]
        extra = []
        if int(x.get("votaciones_asunto", 1)) > 1:
            extra.append(f"Este asunto tuvo {x['votaciones_asunto']} votaciones este mes; aquí "
                         "se muestra la más disputada.")  # fmt: skip
        if x["url"] and not x.get("llamamiento"):
            extra.append(f"[Datos oficiales]({x['url']})")
        if extra:
            salida += [" ".join(extra), ""]
    return salida


def _que_se_voto(a: AnalisisMes) -> list[str]:
    v = a.votaciones
    t = v.groupby("categoria").agg(n=("votacion_id", "size"), si=("aprobada", "sum"))
    t = t.sort_values(["n", "si"], ascending=False)
    filas = [[c, int(x["n"]), int(x["si"]), lenguaje.explicacion(c)] for c, x in t.iterrows()]
    return [tabla(["Tipo", "Votaciones", "Salieron adelante", "Qué es"], filas, "lrrl")]


def componer(a: AnalisisMes, generado: datetime | None = None, imagenes: dict | None = None,
             destacadas: pd.DataFrame | None = None) -> str:  # fmt: skip
    """Informe principal: qué se decidió y cómo votó cada grupo, sin tecnicismos."""
    generado = generado or datetime.now()
    imagenes = imagenes or {}
    hoy = generado.date()
    titulo = f"# Qué votó el Congreso en {almacen.nombre_mes(a.mes)}"
    intro = (
        "Las votaciones del Pleno del Congreso de los Diputados, explicadas sin tecnicismos. "
        f"Datos oficiales del [Congreso]({config.URL_VOTACIONES}); este resumen se actualiza "
        f"solo cada mes (última vez: {generado:%d/%m/%Y})."
    )
    if a.votaciones.empty:
        vacio = (
            "Todavía no hay datos publicados de este mes."
            if a.pendientes
            else "Este mes no hubo votaciones en el Pleno."
        )
        return "\n".join([titulo, "", intro, "", *_pendientes(a, hoy), vacio, ""])
    dest = analisis.destacadas(a) if destacadas is None else destacadas
    partes = [titulo, "", intro, "", *_pendientes(a, hoy)]
    partes += ["## En pocas palabras", "", *_pocas_palabras(a), ""]
    if not dest.empty:
        partes += [
            "## Las votaciones más importantes del mes",
            "",
            "Elegidas por su importancia: pesan más las leyes y los decretos que las peticiones "
            "al Gobierno, y suben las que se decidieron por pocos votos o las que perdió el "
            "Gobierno. Cada punto del dibujo es un diputado, colocado con su grupo, y el color "
            "es lo que votó.",
            "",
            *_destacadas(a, dest, imagenes),
        ]
    if imagenes.get("ganadora"):
        partes += [
            "## ¿Qué grupos votaron más veces lo que finalmente salió?",
            "",
            *imagen(imagenes["ganadora"], "Votaciones en que cada grupo votó lo que salió", 560),
            "Porcentaje de votaciones en que el grupo votó Sí y salió adelante, o votó No y no "
            "salió. Abstenerse no cuenta como acertar.",
            "",
        ]  # fmt: skip
    if imagenes.get("afinidad"):
        partes += [
            "## ¿Quién vota con quién?",
            "",
            *imagen(imagenes["afinidad"], "Votaciones en que cada par de grupos votó igual", 560),
            "Cada casilla dice en qué porcentaje de las votaciones dos grupos votaron lo mismo: "
            "100 es que siempre coincidieron y 0 que nunca.",
            "",
        ]  # fmt: skip
    partes += ["## ¿Qué tipo de cosas se votaron?", "", *_que_se_voto(a), ""]
    partes += ["## Palabras que conviene saber", ""]
    partes += [f"- **{p}**: {d}" for p, d in lenguaje.GLOSARIO]
    partes += [
        "",
        "---",
        "",
        f"**¿Quieres más detalle?** El [análisis detallado]({a.mes}-detalle.md) tiene la "
        "cohesión de cada grupo, un mapa de los diputados según cómo votan, qué diputados "
        "votaron distinto de su grupo, las ausencias y la lista completa de votaciones.",
        "",
        "_Los resultados están calculados a partir de los votos: el Congreso no publica si cada "
        "votación salió adelante. Este proyecto no tiene relación con el Congreso. Método en "
        "[docs/DOCUMENTO_FUNCIONAL.md](../docs/DOCUMENTO_FUNCIONAL.md)._",
    ]
    return "\n".join(partes).rstrip() + "\n"


def escribir(a: AnalisisMes, informes: Path | None = None) -> Path:
    """Escribe reports/AAAA-MM.md (principal), reports/AAAA-MM-detalle.md y sus gráficos."""
    carpeta = informes or config.INFORMES
    carpeta.mkdir(parents=True, exist_ok=True)
    dest = analisis.destacadas(a) if not a.votaciones.empty else pd.DataFrame()
    imagenes = graficos.generar_mes(a, carpeta, dest if not dest.empty else None)
    (carpeta / f"{a.mes}-detalle.md").write_text(
        componer_detalle(a, imagenes=imagenes), encoding="utf-8"
    )
    p = carpeta / f"{a.mes}.md"
    p.write_text(componer(a, imagenes=imagenes, destacadas=dest), encoding="utf-8")
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
        filas.append(
            [
                f"[{almacen.nombre_mes(mes)}]({mes}.md)",
                len(v),
                estado,
                f"[detalle]({mes}-detalle.md)",
            ]
        )
    texto = "\n".join(
        [
            "# Qué votó el Congreso, mes a mes",
            "",
            "Un resumen por mes de las votaciones del Pleno del Congreso, explicado sin "
            "tecnicismos, y un análisis detallado para quien quiera más. Se generan solos cada "
            "mes.",
            "",
            tabla(["Mes", "Votaciones", "Datos", "Análisis detallado"], filas, "lrll"),
            "",
        ]
    )
    p = carpeta / "README.md"
    p.write_text(texto, encoding="utf-8")
    return p
