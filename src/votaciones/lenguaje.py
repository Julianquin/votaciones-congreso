"""Lenguaje llano para el informe principal: títulos más cortos y explicaciones sin jerga.

Reglas conservadoras (D-18): solo se acorta lo que es fórmula administrativa («Moción
consecuencia de interpelación urgente del Grupo Parlamentario…») y los nombres de los grupos.
Nunca se resume ni se interpreta el contenido; el texto oficial sigue enlazado.
"""

from __future__ import annotations

import re

# Nombres oficiales -> nombre corto (sin artículo; `de()` lo pone).
GRUPOS_LARGOS = (
    ("Grupo Parlamentario Popular en el Congreso", "PP"),
    ("Grupo Parlamentario Socialista", "PSOE"),
    ("Grupo Parlamentario VOX", "Vox"),
    ("Grupo Parlamentario Plurinacional SUMAR", "Sumar"),
    ("Grupo Parlamentario Republicano", "ERC"),
    ("Grupo Parlamentario Junts per Catalunya", "Junts"),
    ("Grupo Parlamentario Euskal Herria Bildu", "EH Bildu"),
    ("Grupo Parlamentario Vasco (EAJ-PNV)", "PNV"),
    ("Grupo Parlamentario Mixto", "Grupo Mixto"),
)
# Dentro de «los Grupos Parlamentarios Popular en el Congreso, Socialista y Plurinacional SUMAR».
GRUPOS_EN_LISTA = (
    ("Popular en el Congreso", "PP"),
    ("Plurinacional SUMAR", "Sumar"),
    ("Socialista", "PSOE"),
    ("Republicano", "ERC"),
    ("Junts per Catalunya", "Junts"),
    ("Euskal Herria Bildu", "EH Bildu"),
    ("Vasco (EAJ-PNV)", "PNV"),
    ("Mixto", "Grupo Mixto"),
    ("VOX", "Vox"),
)
CON_ARTICULO = ("PP", "PSOE", "PNV", "Grupo Mixto", "Gobierno")

RE_DIPUTADA = re.compile(r"\s*\((?:Sra?|Sres?)\.[^)]*\)")
COLETILLAS = (
    re.compile(r"\s*\(corresponde al número de expediente[^)]*\)"),
    re.compile(r"\. Se vota en .*$"),
    re.compile(r"\s*\(pública por llamamiento\)", re.I),
)

# (patrón sobre el texto ya con nombres cortos, plantilla). Gana la primera que encaje.
# {de_g} = «del PP», «de Vox»…; {r} = el resto del texto, sin tocar.
_G = r"(?:PP|PSOE|Vox|Sumar|ERC|Junts|EH Bildu|PNV|Grupo Mixto)"
G = rf"{_G}(?:(?:, | y ){_G})*"  # uno o varios grupos, ya con nombre corto
FORMULAS = (
    (rf"^Moción consecuencia de interpelación urgente del? (?P<g>{G}), (?P<r>.+)$",
     "Moción {de_g} {r}"),
    (rf"^Proposición no de Ley del? (?P<g>{G}), (?P<r>.+)$", "Propuesta {de_g} {r}"),
    (rf"^Del? (?P<g>{G}), (?P<r>.+)$", "Propuesta {de_g} {r}"),
    (rf"^Proposición de Ley (?:Orgánica )?del? (?P<g>{G}), (?:Orgánica )?(?P<r>.+)$",
     "Proposición de ley {de_g} {r}"),
    (r"^Propuesta (?:de )?(?:don|doña) (?P<n>.+?) como candidat(?P<o>[oa]) a la Presidencia del "
     r"Gobierno$", "Investidura de {n} como president{e_a} del Gobierno"),
    (r"^Tramitación como Proyecto de Ley por el procedimiento de urgencia del Real Decreto-ley "
     r"(?P<n>\d+/\d{4}), de [^,]+, (?P<r>.+)$",
     "Tramitar como proyecto de ley, lo que permite cambiarlo, el decreto-ley {n}, {r}"),
    (r"^Real Decreto-ley (?P<n>\d+/\d{4}), de [^,]+, (?P<r>.+)$",
     "Decreto-ley {n} del Gobierno, {r}"),
    (r"^Votación de la enmienda a la totalidad de devolución al (?P<obj>.+), presentada por "
     r"(?:el |los )?(?P<g>.+)$", "Enmienda {de_g} para devolver el {obj}"),
    (r"^Votación de la enmienda a la totalidad de texto alternativo (?:a la|al) (?P<obj>.+), "
     r"presentada por (?:el |los )?(?P<g>.+)$", "Texto alternativo {de_g} a: {obj}"),
    (r"^Votación de las? solicitud(?:es)? de avocación por el Pleno de la Cámara de la "
     r"deliberación y votación final (?:del|de la) (?P<obj>.+)$",
     "Que la votación final se haga en el Pleno y no solo en comisión: {obj}"),
    (r"^Votación conjunta de las enmiendas a la totalidad de devolución al (?P<obj>.+)$",
     "Enmiendas para devolver el {obj}"),
    (r"^Votación de conjunto (?P<art>del texto del|de la|del) (?P<obj>.+?)"
     r"(?:, por (?:tener|tramitarse|tratarse) .*)?$", "Votación final {art} {obj}"),
    (r"^Proyecto de Ley (?P<r>.+)$", "Proyecto de ley del Gobierno {r}"),
)  # fmt: skip
FORMULAS_RE = tuple((re.compile(p), t) for p, t in FORMULAS)


def de(grupos: str) -> str:
    """«PP» -> «del PP»; «Vox» -> «de Vox»; «PSOE y Sumar» -> «del PSOE y Sumar»."""
    g = grupos.strip()
    return f"del {g}" if g.startswith(CON_ARTICULO) else f"de {g}"


def nombres_cortos(texto: str) -> str:
    if "Grupos Parlamentarios " in texto:
        for largo, corto in GRUPOS_EN_LISTA:
            texto = texto.replace(largo, corto)
        texto = texto.replace("los Grupos Parlamentarios ", "").replace(
            "Grupos Parlamentarios ", ""
        )
    for largo, corto in GRUPOS_LARGOS:
        texto = texto.replace(largo, corto)
    return texto


def titulo_llano(texto_expediente: str, maximo: int = 150) -> str:
    """«Moción consecuencia de interpelación urgente del Grupo Parlamentario VOX, sobre…» ->
    «Moción de Vox sobre…». Lo que no encaja en ninguna fórmula se deja tal cual."""
    t = " ".join(str(texto_expediente).split())
    t = RE_DIPUTADA.sub("", t)
    for coletilla in COLETILLAS:
        t = coletilla.sub("", t)
    t = t.rstrip(". ")
    t = nombres_cortos(t)
    for patron, plantilla in FORMULAS_RE:
        m = patron.match(t)
        if m:
            partes = {k: v.strip() for k, v in m.groupdict().items()}
            if "g" in partes:
                partes["de_g"] = de(partes["g"])
            if "o" in partes:
                partes["e_a"] = "a" if partes["o"] == "a" else "e"
            t = plantilla.format(**partes)
            break
    # «del el PP», «de el PP» y similares tras sustituir nombres en mitad de una frase.
    t = re.sub(
        r"\b(de|por) el (PP|PSOE|PNV|Grupo Mixto)\b",
        lambda m: f"{'del' if m[1] == 'de' else 'por el'} {m[2]}",
        t,
    )
    t = t[0].upper() + t[1:] if t else t
    return t if len(t) <= maximo else t[: maximo - 1].rstrip(" ,;:") + "…"


# Explicación de una línea para cada categoría (config.CATEGORIAS).
EXPLICACIONES = {
    "Investidura": "Votación para elegir presidente del Gobierno. En la primera votación hacen "
    "falta 176 votos a favor; en la segunda, más síes que noes.",
    "Decretos-ley (convalidación)": "El Gobierno aprobó esta norma por urgencia. Ya está en "
    "vigor, pero el Congreso tiene 30 días para confirmarla o tumbarla.",
    "Leyes: toma en consideración": "Primer paso de una ley propuesta por un grupo o una "
    "comunidad autónoma: el Congreso decide si empieza a tramitarla.",
    "Enmiendas a la totalidad": "Un grupo intenta devolver la ley a quien la propuso o "
    "sustituirla por otra. Si no sale adelante, la ley sigue su camino.",
    "Leyes: dictamen y votación final": "Votación del texto de una ley después de trabajarla "
    "en comisión.",
    "Leyes: enmiendas del Senado": "El Senado propuso cambios a esta ley y el Congreso decide "
    "si los acepta. Es uno de los últimos pasos antes de que la ley se publique.",
    "Leyes: veto del Senado": "El Senado rechazó la ley entera. El Congreso puede levantar el "
    "veto: enseguida con 176 votos o, pasados dos meses, con más síes que noes.",
    "Proposiciones no de ley": "Petición al Gobierno para que haga algo. Expresa la opinión "
    "del Congreso, pero no obliga.",
    "Mociones": "Petición al Gobierno después de pedirle explicaciones en el Pleno. Expresa la "
    "opinión del Congreso, pero no obliga.",
    "Tratados internacionales": "El Congreso autoriza a España a comprometerse con un "
    "acuerdo con otro país u organismo.",
    "Presupuestos y estabilidad": "Cuentas públicas: límites de déficit y deuda o cuentas "
    "del Estado.",
    "Organización de la Cámara": "Asunto interno del Congreso: comisiones, plazos o el "
    "estatuto de los diputados.",
}
NO_OBLIGA = ("Proposiciones no de ley", "Mociones")


def explicacion(categoria: str) -> str:
    return EXPLICACIONES.get(categoria, "")


GLOSARIO = (
    ("Pleno", "La reunión de los 350 diputados, donde se vota."),
    ("Grupo parlamentario", "Los diputados de un partido o coalición. Los partidos pequeños "
     "van juntos en el Grupo Mixto, aunque no piensen igual."),
    ("Abstención", "El diputado vota, pero ni a favor ni en contra."),
    ("No votó", "El diputado no votó: no estaba, estaba de baja o el escaño estaba vacío."),
    ("Mayoría simple", "Salen adelante las votaciones con más síes que noes. Es lo normal."),
    ("Mayoría absoluta", "176 votos a favor, la mitad más uno de 350. La piden las leyes "
     "orgánicas (derechos fundamentales, sistema electoral…) y la primera votación de "
     "investidura."),
    ("Votación por llamamiento", "Cada diputado dice su voto en voz alta. Se usa en las "
     "investiduras y otras votaciones importantes."),
)  # fmt: skip
