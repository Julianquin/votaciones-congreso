"""Carrusel de Instagram (1080 × 1350) a partir del informe de un mes (D-20).

Todo lo que es dato (hemiciclos, cifras, quién votó qué) sale del análisis, igual que el
informe. Un modelo de imagen solo puede poner el **fondo de la portada** (``fondo=``): una
ilustración abstracta, sin texto, sin personas reales y sin logos, etiquetada como generada con
IA. Ver notebooks/portada_ia.ipynb.

Salida en social/AAAA-MM/: 01-portada.png … NN-cierre.png y pie.txt (el texto de la publicación).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, findfont
from PIL import Image, ImageDraw, ImageFont

from . import almacen, analisis, config, graficos, informe, lenguaje

W, H = 1080, 1350
MARGEN = 72
TEMA = graficos.TEMAS["claro"]
OSCURO = graficos.TEMAS["oscuro"]
REPO = "github.com/Julianquin/votaciones-congreso"
SALIDA = config.RAIZ / "social"
DESTACADAS_CARRUSEL = 3  # Instagram admite 20, pero un carrusel corto se lee entero

_RUTA = findfont(FontProperties(family="DejaVu Sans"))
_RUTA_NEGRITA = findfont(FontProperties(family="DejaVu Sans", weight="bold"))


def fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_RUTA_NEGRITA if negrita else _RUTA, tam)


# --- Utilidades de composición -----------------------------------------------------------
def envolver(texto: str, f: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if f.getlength(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def escribir(d: ImageDraw.ImageDraw, xy, texto: str, f, color, ancho: int, max_lineas: int = 99,
             interlineado: float = 1.25) -> int:  # fmt: skip
    """Escribe un párrafo envuelto; devuelve la y donde acaba."""
    x, y = xy
    lineas = envolver(texto, f, ancho)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        while f.getlength(lineas[-1] + "…") > ancho and " " in lineas[-1]:
            lineas[-1] = lineas[-1].rsplit(" ", 1)[0]
        lineas[-1] = lineas[-1].rstrip(" ,;:") + "…"
    alto = int(f.size * interlineado)
    for linea in lineas:
        d.text((x, y), linea, font=f, fill=color)
        y += alto
    return y


def escribir_rico(d, xy, partes: list[tuple[str, bool]], tam: int, color, ancho: int) -> int:
    """Texto envuelto que mezcla negrita y normal: [("A favor: ", True), ("PP y Vox", False)]."""
    x0, y = xy
    x = x0
    alto = int(tam * 1.3)
    for texto, negrita in partes:
        f = fuente(tam, negrita)
        for i, palabra in enumerate(texto.split(" ")):
            trozo = palabra + (" " if i < len(texto.split(" ")) - 1 or texto.endswith(" ") else "")
            largo = f.getlength(trozo)
            if x + largo > x0 + ancho and x > x0:
                x, y = x0, y + alto
            d.text((x, y), trozo, font=f, fill=color)
            x += largo
    return y + alto


def figura_a_imagen(fig, ancho: int) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220, facecolor=fig.get_facecolor(), bbox_inches="tight",
                pad_inches=0.04)  # fmt: skip
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    return img.resize((ancho, round(img.height * ancho / img.width)), Image.LANCZOS)


def pie_pagina(d: ImageDraw.ImageDraw, n: int, total: int, tema: dict) -> None:
    f = fuente(22)
    y = H - 56
    d.text((MARGEN, y), "Datos oficiales del Congreso · cálculo propio", font=f, fill=tema["tenue"])
    marca = f"{n}/{total}"
    d.text((W - MARGEN - f.getlength(marca), y), marca, font=f, fill=tema["tenue"])


def etiqueta(d, xy, texto: str, tema: dict) -> int:
    """Pastilla con el tipo y la fecha; devuelve la y de debajo."""
    f = fuente(24, True)
    x, y = xy
    largo = f.getlength(texto)
    d.rounded_rectangle((x, y, x + largo + 32, y + 44), radius=22, fill=tema["rejilla"])
    d.text((x + 16, y + 8), texto, font=f, fill=tema["tinta2"])
    return y + 44


def cubrir(img: Image.Image, w: int, h: int) -> Image.Image:
    """Recorta y escala para llenar w × h sin deformar."""
    escala = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


# --- Diapositivas ------------------------------------------------------------------------
def portada(a, total: int, fondo: Path | None, principal=None, pagina: int = 2) -> Image.Image:
    v = a.votaciones
    aprob = int(v["aprobada"].sum())
    if fondo:
        with Image.open(fondo) as original:
            img = cubrir(original.convert("RGB"), W, H)
        # Velo oscuro de abajo arriba para que el texto se lea sobre cualquier ilustración.
        velo = Image.new("L", (W, H))
        dv = ImageDraw.Draw(velo)
        for y in range(H):
            t = min(1.0, max(0.0, (y - 0.18 * H) / (0.28 * H)))  # opaco desde el 46 % de alto
            dv.line([(0, y), (W, y)], fill=int(242 * t**0.85))
        img = Image.composite(Image.new("RGB", (W, H), OSCURO["fondo"]), img, velo)
    else:
        img = Image.new("RGB", (W, H), OSCURO["fondo"])
    d = ImageDraw.Draw(img)
    y = 640 if fondo else 120
    y = escribir(
        d, (MARGEN, y), "Qué votó el Congreso", fuente(76, True), OSCURO["tinta"], W - 2 * MARGEN
    )
    y = escribir(d, (MARGEN, y + 4), almacen.nombre_mes(a.mes).capitalize(), fuente(52),
                 OSCURO["tinta2"], W - 2 * MARGEN)  # fmt: skip
    y += 50
    gob = a.gobierno
    unidos = gob[gob["posicion"].isin(["Sí", "No"])] if not gob.empty else gob
    cifras = [
        (f"{len(v)}", "votaciones en el Pleno"),
        (f"{aprob}", "salieron adelante"),
    ]
    if len(unidos):
        cifras.append((f"{int(unidos['pierde'].sum())}", "perdió el Gobierno"))
    for numero, texto in cifras:
        d.text((MARGEN, y), numero, font=fuente(84, True), fill=OSCURO["Sí"])
        d.text((MARGEN + fuente(84, True).getlength(numero) + 24, y + 34), texto, font=fuente(36),
               fill=OSCURO["tinta"])  # fmt: skip
        y += 108
    if not fondo and principal is not None and principal["nominal"]:
        # Sin ilustración: el hemiciclo de la votación principal, que también es dato.
        votos_v = a.votos[a.votos["votacion_id"] == principal["votacion_id"]]
        mapa_x = a.mapa.puntos.set_index("diputado")["x"] if a.mapa is not None else None
        fig = graficos.hemiciclo(votos_v, principal, a.orden_espacial or a.orden, mapa_x, OSCURO,
                                 compacto=True)  # fmt: skip
        hemi = figura_a_imagen(fig, W - 2 * 90)
        y_hemi = min(y + 10, H - 230 - hemi.height)
        img.paste(hemi, (90, y_hemi))
        d = ImageDraw.Draw(img)
        titulo = lenguaje.titulo_llano(principal["texto_expediente"] or principal["titulo"], 90)
        escribir(d, (MARGEN, y_hemi + hemi.height + 12), f"En el dibujo: {titulo} (página "
                 f"{pagina})", fuente(24), OSCURO["tinta2"], W - 2 * MARGEN, 2)  # fmt: skip
    f = fuente(24)
    d.text((MARGEN, H - 96), "Desliza →", font=fuente(28, True), fill=OSCURO["tinta"])
    marca = f"1/{total}"
    d.text((W - MARGEN - f.getlength(marca), H - 56), marca, font=f, fill=OSCURO["tenue"])
    if fondo:
        d.text((MARGEN, H - 56), "Ilustración de portada generada con IA", font=f,
               fill=OSCURO["tenue"])  # fmt: skip
    return img


def diapositiva_votacion(a, x, n: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), TEMA["fondo"])
    d = ImageDraw.Draw(img)
    ancho = W - 2 * MARGEN
    y = etiqueta(d, (MARGEN, 64), f"{x['categoria']} · {x['fecha']:%d/%m/%Y}", TEMA) + 28
    titulo = lenguaje.titulo_llano(x["texto_expediente"] or x["titulo"], 400)
    y = escribir(d, (MARGEN, y), titulo, fuente(44, True), TEMA["tinta"], ancho, max_lineas=4) + 8

    grupos = a.orden_espacial or a.orden
    if x["nominal"]:
        mapa_x = a.mapa.puntos.set_index("diputado")["x"] if a.mapa is not None else None
        votos_v = a.votos[a.votos["votacion_id"] == x["votacion_id"]]
        fig = graficos.hemiciclo(votos_v, x, grupos, mapa_x, TEMA)
    else:
        fig = graficos.barra_resultado(x, TEMA)
    grafico = figura_a_imagen(fig, W - 2 * 40)
    img.paste(grafico, (40, y))
    y += grafico.height + 18

    if x.get("empate"):
        res = f"= Empate a {x['a_favor']}: se repitió"
    else:
        res = (
            "✔ Salió adelante " if x["aprobada"] else "✘ No salió adelante "
        ) + informe.distancia(x)
    y = escribir(d, (MARGEN, y), res, fuente(38, True), TEMA["tinta"], ancho, 2) + 10
    if x["nominal"]:
        q = analisis.quien_voto(a, x["votacion_id"])
        rotulos = (("Sí", "A favor: "), ("No", "En contra: "), ("Abstención", "Se abstuvieron: "),
                   ("mezcla", "Repartidos: "))  # fmt: skip
        for clave, nombre in rotulos:
            if q[clave] and y < H - 190:
                partes = [(nombre, True), (informe.lista(q[clave]), False)]
                y = escribir_rico(d, (MARGEN, y), partes, 29, TEMA["tinta"], ancho) + 4
    elif x.get("llamamiento"):
        y = escribir(d, (MARGEN, y), "Votación por llamamiento: el voto de cada diputado está en "
                     "el Diario de Sesiones.", fuente(28), TEMA["tinta2"], ancho, 2)  # fmt: skip
    explicacion = lenguaje.explicacion(x["categoria"])
    if explicacion and y < H - 150:
        escribir(d, (MARGEN, max(y + 16, H - 170)), explicacion, fuente(25), TEMA["tinta2"],
                 ancho, max_lineas=3)  # fmt: skip
    pie_pagina(d, n, total, TEMA)
    return img


def diapositiva_barras(a, n: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), TEMA["fondo"])
    d = ImageDraw.Draw(img)
    ancho = W - 2 * MARGEN
    y = escribir(d, (MARGEN, 80), "¿Qué grupos votaron más veces lo que salió?", fuente(50, True),
                 TEMA["tinta"], ancho)  # fmt: skip
    nota = (
        "Porcentaje de votaciones en que el grupo votó Sí y salió adelante, o votó No y no salió."
    )
    y = escribir(d, (MARGEN, y + 10), nota, fuente(28), TEMA["tinta2"], ancho) + 30
    grafico = figura_a_imagen(graficos.barras(a.resumen["ganadora"], TEMA, alto_barra=0.62), ancho)
    img.paste(grafico, (MARGEN, y))
    pie_pagina(d, n, total, TEMA)
    return img


def cierre(n: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), TEMA["fondo"])
    d = ImageDraw.Draw(img)
    ancho = W - 2 * MARGEN
    y = escribir(d, (MARGEN, 110), "Cómo leer estos datos", fuente(56, True), TEMA["tinta"], ancho)
    y += 30
    puntos = [
        "Cada punto del hemiciclo es un diputado, colocado con su grupo. El color es lo que votó.",
        "Una propuesta sale adelante con más síes que noes. Algunas leyes piden 176 síes, la "
        "mitad más uno de 350.",
        "Las proposiciones no de ley y las mociones son peticiones al Gobierno: no le obligan.",
        "El Grupo Mixto junta partidos distintos; por eso a menudo vota repartido.",
    ]
    for p in puntos:
        d.ellipse((MARGEN, y + 14, MARGEN + 14, y + 28), fill=TEMA["Sí"])
        y = escribir(d, (MARGEN + 34, y), p, fuente(32), TEMA["tinta"], ancho - 34) + 22
    y += 30
    y = escribir(d, (MARGEN, y), "Informe completo, método y datos:", fuente(32, True),
                 TEMA["tinta"], ancho)  # fmt: skip
    y = escribir(d, (MARGEN, y + 4), REPO, fuente(32), TEMA["resaltado"], ancho) + 40
    escribir(d, (MARGEN, y), "Cálculo propio con los datos abiertos del Congreso de los "
             "Diputados. Este proyecto no tiene relación con el Congreso.", fuente(26),
             TEMA["tinta2"], ancho)  # fmt: skip
    pie_pagina(d, n, total, TEMA)
    return img


def texto_publicacion(a, dest, con_ia: bool) -> str:
    v = a.votaciones
    aprob = int(v["aprobada"].sum())
    lineas = [
        f"Qué votó el Congreso en {almacen.nombre_mes(a.mes)} 🏛️",
        "",
        f"{len(v)} votaciones en {v['fecha'].nunique()} días de pleno: {aprob} salieron adelante y "
        f"{len(v) - aprob} no.",
        "",
        "Las más importantes:",
    ]
    for i, (_, x) in enumerate(dest.iterrows(), start=1):
        res = "salió adelante" if x["aprobada"] else "no salió adelante"
        titulo = lenguaje.titulo_llano(x["texto_expediente"] or x["titulo"], 110)
        lineas.append(f"{i}. {titulo}: {res} ({x['a_favor']} a favor, {x['en_contra']} en contra).")
    lineas += [
        "",
        "Desliza para ver cómo votó cada grupo. Informe completo: enlace en la bio.",
        "",
        "Datos oficiales del Congreso de los Diputados; cálculo propio. Este proyecto no tiene "
        "relación con el Congreso.",
    ]
    if con_ia:
        lineas.append("La ilustración de la portada está generada con IA; los gráficos, no.")
    lineas += ["", "#CongresoDeLosDiputados #DatosAbiertos #Parlamento #Política #España"]
    return "\n".join(lineas) + "\n"


# --- Todo junto --------------------------------------------------------------------------
def generar(mes: str, fondo: Path | None = None, salida: Path | None = None) -> Path:
    mes = almacen.validar_mes(mes)
    v, votos = almacen.cargar_mes(mes)
    if v.empty:
        raise ValueError(f"No hay votaciones guardadas de {mes}.")
    manifiesto = almacen.cargar_manifiesto()
    a = analisis.analizar(mes, v, votos, almacen.dias_pendientes(manifiesto, mes))
    dest = analisis.destacadas(a, DESTACADAS_CARRUSEL)
    carpeta = (salida or SALIDA) / mes
    carpeta.mkdir(parents=True, exist_ok=True)
    for viejo in carpeta.glob("*.png"):
        viejo.unlink()

    total = 1 + len(dest) + (0 if a.resumen.empty else 1) + 1
    principal, pagina = None, 2
    if not dest.empty:
        principal = dest.sort_values("puntos", ascending=False).iloc[0]
        pagina = 2 + list(dest["votacion_id"]).index(principal["votacion_id"])
    diapositivas = [("portada", portada(a, total, fondo, principal, pagina))]
    for i, (_, x) in enumerate(dest.iterrows(), start=2):
        diapositivas.append((f"votacion-{i - 1}", diapositiva_votacion(a, x, i, total)))
    if not a.resumen.empty:
        diapositivas.append(("grupos", diapositiva_barras(a, len(diapositivas) + 1, total)))
    diapositivas.append(("cierre", cierre(total, total)))
    for k, (nombre, img) in enumerate(diapositivas, start=1):
        img.save(carpeta / f"{k:02d}-{nombre}.png", optimize=True)
    (carpeta / "pie.txt").write_text(texto_publicacion(a, dest, fondo is not None), "utf-8")
    meta = {"mes": mes, "fondo": str(fondo) if fondo else None,
            "votaciones": list(dest["votacion_id"])}  # fmt: skip
    (carpeta / "carrusel.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    return carpeta
