"""Gráficos del informe: hemiciclo de una votación, afinidad entre grupos y mapa de diputados.

Cada gráfico se dibuja dos veces, con tema claro y oscuro, y el informe los sirve con
<picture> para que GitHub elija según el tema del lector. Paleta validada (docs/DESIGN.md):
el par Sí/No es verde azulado/naranja y NO azul/rojo, porque en España esos colores se leen
como PP/PSOE.

Los SVG son deterministas (sin fecha, sal de identificadores fija) para que regenerar un
informe sin cambios no produzca diffs en git.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from . import config  # noqa: E402

plt.rcParams.update(
    {
        "svg.hashsalt": "votaciones-congreso",
        # Texto como texto, no como trazos: SVG 3-4 veces más ligeros. Si el lector no tiene
        # DejaVu Sans, el navegador usa su sans-serif.
        "svg.fonttype": "none",
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
        "font.size": 9,
        "axes.titlesize": 10,
    }
)

TEMAS = {
    "claro": {
        "fondo": "#fcfcfb", "tinta": "#0b0b0b", "tinta2": "#52514e", "tenue": "#898781",
        "rejilla": "#e1e0d9", "Sí": "#127a8a", "No": "#eb6834", "Abstención": "#c3c2b7",
        "No vota": "#898781", "resaltado": "#2a78d6", "resto": "#dcdad3",
        "rampa": ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95",
                  "#0d366b"],
    },
    "oscuro": {
        "fondo": "#1a1a19", "tinta": "#f0efec", "tinta2": "#c3c2b7", "tenue": "#898781",
        "rejilla": "#2c2c2a", "Sí": "#2aa3b3", "No": "#e8683a", "Abstención": "#4d4b46",
        "No vota": "#898781", "resaltado": "#3987e5", "resto": "#383835",
        "rampa": ["#262624", "#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4",
                  "#cde2fb"],
    },
}  # fmt: skip
OPCIONES = ("Sí", "No", "Abstención", "No vota")


# --- Utilidades --------------------------------------------------------------------------
def _figura(tema: dict, ancho: float, alto: float):
    fig = plt.figure(figsize=(ancho, alto), facecolor=tema["fondo"])
    return fig


def guardar(fig, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        ruta, format=ruta.suffix[1:], facecolor=fig.get_facecolor(), bbox_inches="tight",
        pad_inches=0.15, metadata={"Date": None} if ruta.suffix == ".svg" else None,
    )  # fmt: skip
    plt.close(fig)


# --- Hemiciclo ---------------------------------------------------------------------------
def posiciones_hemiciclo(n: int, filas: int = 12, r0: float = 0.38) -> np.ndarray:
    """n asientos en semicírculo, ordenados de izquierda a derecha (el reparto clásico)."""
    filas = min(filas, max(1, n // 8))
    radios = np.linspace(r0, 1.0, filas)
    por_fila = np.floor(n * radios / radios.sum()).astype(int)
    por_fila[-1] += n - por_fila.sum()
    puntos = []
    for r, k in zip(radios, por_fila, strict=True):
        angulos = np.linspace(np.pi, 0, k) if k > 1 else np.array([np.pi / 2])
        puntos += [(a, r) for a in angulos]
    puntos.sort(key=lambda t: (-round(t[0], 9), t[1]))
    a = np.array(puntos)
    return np.c_[a[:, 1] * np.cos(a[:, 0]), a[:, 1] * np.sin(a[:, 0])]


def orden_asientos(votos_v: pd.DataFrame, grupos: list[str], mapa_x: pd.Series | None):
    """Diputados de una votación, por grupo (orden espacial) y dentro del grupo por su eje 1.

    Devuelve una lista con None como hueco entre grupos.
    """
    asientos: list = []
    for g in grupos:
        d = votos_v[votos_v["grupo"] == g].copy()
        if d.empty:
            continue
        d["x"] = d["diputado"].map(mapa_x) if mapa_x is not None else np.nan
        d = d.sort_values(["x", "diputado"], na_position="last")
        if asientos:
            asientos.append(None)
        asientos += list(d.itertuples(index=False))
    return asientos


def hemiciclo(
    votos_v: pd.DataFrame, fila_v, grupos: list[str], mapa_x: pd.Series | None, tema: dict
):
    asientos = orden_asientos(votos_v, grupos, mapa_x)
    xy = posiciones_hemiciclo(len(asientos))
    fig = _figura(tema, 7.0, 4.3)
    ax = fig.add_axes([0, 0.1, 1, 0.9])
    ax.set_facecolor(tema["fondo"])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.32, 1.32)
    ax.set_ylim(-0.08, 1.3)

    por_opcion: dict[str, list[int]] = {o: [] for o in OPCIONES}
    for i, a in enumerate(asientos):
        if a is not None:
            por_opcion.setdefault(a.voto, []).append(i)
    for opcion in OPCIONES:
        idx = por_opcion.get(opcion, [])
        if not idx:
            continue
        if opcion == "No vota":
            ax.scatter(xy[idx, 0], xy[idx, 1], s=70, facecolor=tema["fondo"],
                       edgecolor=tema["No vota"], linewidth=1.2, zorder=3)  # fmt: skip
        else:
            ax.scatter(xy[idx, 0], xy[idx, 1], s=95, color=tema[opcion], linewidth=0, zorder=3)

    # Etiqueta de cada grupo en el ángulo medio de sus asientos; los pequeños se escalonan.
    alterno = False
    for g in grupos:
        idx = [i for i, a in enumerate(asientos) if a is not None and a.grupo == g]
        if not idx:
            continue
        ang = np.arctan2(xy[idx, 1], xy[idx, 0]).mean()
        pequeno = len(idx) < 20
        r = 1.09 + (0.11 if pequeno and alterno else 0)
        alterno = (not alterno) if pequeno else False
        x, y = r * np.cos(ang), r * np.sin(ang)
        ha = "center" if abs(x) < 0.25 else ("right" if x < 0 else "left")
        ax.text(x, y, config.etiqueta(g), ha=ha, va="bottom" if y > 0.3 else "center",
                color=tema["tinta2"], fontsize=8.5)  # fmt: skip

    # Resultado en el centro.
    si, no = int(fila_v["a_favor"]), int(fila_v["en_contra"])
    ax.text(0, 0.17, f"{si} – {no}", ha="center", va="center", fontsize=20,
            color=tema["tinta"], fontweight="bold")  # fmt: skip
    resultado = "Aprobada" if fila_v["aprobada"] else "Rechazada"
    if fila_v.get("umbral"):
        resultado += f" (necesita {int(fila_v['umbral'])})"
    ax.text(0, 0.03, resultado, ha="center", va="center", fontsize=9.5, color=tema["tinta2"])

    cuentas = votos_v["voto"].value_counts()
    manejadores = [
        Line2D([], [], linestyle="", marker="o", markersize=8,
               markerfacecolor=tema["fondo"] if o == "No vota" else tema[o],
               markeredgecolor=tema[o], markeredgewidth=1.2 if o == "No vota" else 0,
               label=f"{o} {int(cuentas.get(o, 0))}")
        for o in OPCIONES
    ]  # fmt: skip
    fig.legend(handles=manejadores, loc="lower center", ncol=4, frameon=False,
               labelcolor=tema["tinta2"], bbox_to_anchor=(0.5, 0.0), handletextpad=0.3,
               columnspacing=1.6)  # fmt: skip
    return fig


# --- Afinidad ----------------------------------------------------------------------------
def afinidad(m: pd.DataFrame, grupos: list[str], tema: dict):
    """Triángulo inferior de la matriz de afinidad, con el porcentaje en cada celda."""
    grupos = [g for g in grupos if g in m.index]
    filas, columnas = grupos[1:], grupos[:-1]
    datos = np.full((len(filas), len(columnas)), np.nan)
    for i, a in enumerate(filas):
        for j, b in enumerate(columnas):
            if j <= i:
                datos[i, j] = m.loc[a, b]
    cmap = LinearSegmentedColormap.from_list("rampa", tema["rampa"]).with_extremes(
        bad=tema["fondo"]
    )
    lado = 0.55 * len(columnas) + 1.4
    fig = _figura(tema, lado, 0.5 * len(filas) + 0.9)
    ax = fig.add_subplot()
    ax.set_facecolor(tema["fondo"])
    ax.imshow(np.ma.masked_invalid(datos), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(len(filas)):
        for j in range(len(columnas)):
            if np.isnan(datos[i, j]):
                continue
            fondo = cmap(datos[i, j])
            claro = 0.2126 * fondo[0] + 0.7152 * fondo[1] + 0.0722 * fondo[2] > 0.5
            ax.text(j, i, f"{100 * datos[i, j]:.0f}", ha="center", va="center", fontsize=8.5,
                    color="#0b0b0b" if claro else "#ffffff")  # fmt: skip
    # Hueco de 2 px entre celdas: rejilla menor del color del fondo.
    ax.set_xticks(np.arange(len(columnas) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(filas) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color=tema["fondo"], linewidth=2)
    ax.tick_params(which="both", length=0)
    ax.set_xticks(range(len(columnas)), [config.etiqueta(g) for g in columnas], rotation=0)
    ax.set_yticks(range(len(filas)), [config.etiqueta(g) for g in filas])
    for t in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        t.set_color(tema["tinta2"])
    ax.xaxis.tick_top()
    for lado_eje in ax.spines.values():
        lado_eje.set_visible(False)
    return fig


# --- Mapa de diputados -------------------------------------------------------------------
def mapa(puntos: pd.DataFrame, grupos: list[str], tema: dict, columnas: int = 3):
    """Un panel por grupo: sus diputados resaltados sobre el resto del Congreso en gris."""
    grupos = [g for g in grupos if (puntos["grupo"] == g).any()]
    filas = int(np.ceil(len(grupos) / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(7.2, 2.3 * filas), squeeze=False,
                             sharex=True, sharey=True, facecolor=tema["fondo"])  # fmt: skip
    margen = 0.12
    for k, ax in enumerate(ejes.flat):
        ax.set_facecolor(tema["fondo"])
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(tema["rejilla"])
        if k >= len(grupos):
            ax.set_visible(False)
            continue
        g = grupos[k]
        propio = puntos["grupo"] == g
        resto, suyos = _agrupar(puntos[~propio]), _agrupar(puntos[propio])
        ax.scatter(resto["x"], resto["y"], s=6 + 6 * np.sqrt(resto["n"]),
                   color=tema["resto"], linewidth=0)  # fmt: skip
        ax.scatter(suyos["x"], suyos["y"], s=14 + 10 * np.sqrt(suyos["n"]),
                   color=tema["resaltado"], edgecolor=tema["fondo"], linewidth=0.8)  # fmt: skip
        ax.set_title(f"{config.etiqueta(g)} · {int(propio.sum())}", loc="left",
                     color=tema["tinta"], pad=4)  # fmt: skip
        ax.set_xlim(-1 - margen, 1 + margen)
        ax.set_ylim(-1 - margen, 1 + margen)
    fig.subplots_adjust(wspace=0.06, hspace=0.28)
    return fig


def _agrupar(p: pd.DataFrame) -> pd.DataFrame:
    """Diputados en (casi) el mismo punto -> un punto con n; el área crece con n."""
    r = p.assign(x=p["x"].round(2), y=p["y"].round(2))
    return r.groupby(["x", "y"]).size().rename("n").reset_index()


# --- Todo el mes -------------------------------------------------------------------------
def generar_mes(a, informes: Path, max_hemiciclos: int = 4) -> dict:
    """Dibuja los gráficos del mes en reports/img/AAAA-MM/ y devuelve sus rutas relativas.

    {"mapa": (claro, oscuro), "afinidad": (...), "hemiciclos": {votacion_id: (...)}}
    """
    carpeta = informes / "img" / a.mes
    if carpeta.exists():
        shutil.rmtree(carpeta)  # sin restos de una versión anterior del informe
    rutas: dict = {"hemiciclos": {}}
    if a.grupos.empty:
        return rutas

    def dibujar(nombre: str, hacer) -> tuple[str, str]:
        par = []
        for clave, sufijo in (("claro", ""), ("oscuro", "-oscuro")):
            ruta = carpeta / f"{nombre}{sufijo}.svg"
            guardar(hacer(TEMAS[clave]), ruta)
            par.append(ruta.relative_to(informes).as_posix())
        return par[0], par[1]

    grupos = a.orden_espacial or a.orden
    if a.mapa is not None:
        rutas["mapa"] = dibujar("mapa", lambda t: mapa(a.mapa.puntos, grupos, t))
    if not a.afinidad.empty and len(a.afinidad) > 1:
        rutas["afinidad"] = dibujar("afinidad", lambda t: afinidad(a.afinidad, grupos, t))

    mapa_x = a.mapa.puntos.set_index("diputado")["x"] if a.mapa is not None else None
    for vid in ajustadas(a, max_hemiciclos)["votacion_id"]:
        fila = a.votaciones.set_index("votacion_id").loc[vid]
        votos_v = a.votos[a.votos["votacion_id"] == vid]
        rutas["hemiciclos"][vid] = dibujar(
            f"hemiciclo-{vid}", lambda t, f=fila, vv=votos_v: hemiciclo(vv, f, grupos, mapa_x, t)
        )
    return rutas


def ajustadas(
    a, n: int, margen_max: int | None = None, solo_nominales: bool = True
) -> pd.DataFrame:
    """Las n votaciones más ajustadas. Para dibujar hace falta el voto individual (nominales);
    la tabla del informe incluye también las públicas por llamamiento."""
    margen_max = config.MARGEN_AJUSTADA if margen_max is None else margen_max
    v = a.votaciones
    con_votos = v["nominal"] | (v["llamamiento"] if "llamamiento" in v else False)
    nom = v[v["nominal"] if solo_nominales else con_votos].copy()
    nom["dist"] = nom["margen"].abs()
    nom = nom[nom["dist"] <= margen_max]
    return nom.sort_values(["dist", "fecha", "numero"]).head(n)
