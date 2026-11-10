"""Línea de órdenes: python -m src.votaciones <orden> ...

sondear                      una petición: ¿responde el portal y qué legislatura sirve?
actualizar --mes AAAA-MM     descarga los días de ese mes que falten o estén pendientes
actualizar --dia AAAA-MM-DD  descarga solo ese día (útil para probar)
informe --mes AAAA-MM        regenera reports/AAAA-MM.md con lo que haya en data/
mensual [--mes AAAA-MM]      lo que corre GitHub Actions: mes anterior + pendientes + informes
historico --desde AAAA-MM    carga inicial de varios meses (largo: lo lanza el usuario)
instagram --mes AAAA-MM      carrusel de Instagram en social/AAAA-MM/ (sin red)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from . import almacen, analisis, config, fuente, informe
from .normalizar import normalizar, normalizar_html

log = logging.getLogger("votaciones")


def hoy() -> date:
    try:
        return datetime.now(ZoneInfo(config.ZONA)).date()
    except Exception:  # sin base de zonas horarias: basta con UTC para saber el mes
        return datetime.now(UTC).date()


def mes_anterior(d: date) -> str:
    return almacen.sumar_meses(almacen.mes_de(d), -1)


# --- Descarga ----------------------------------------------------------------------------
def actualizar_dia(cliente: fuente.Cliente, leg: int, dia: date, manifiesto: dict) -> dict:
    enlaces = fuente.votaciones_del_dia(cliente, leg, dia)
    filas, votos, sin_json = [], [], 0
    for e in enlaces:
        if e.url_json is None:
            if e.llamamiento and e.totales:  # nunca tendrá JSON: se toma de la página (D-12)
                filas.append(normalizar_html(e, config.DIPUTADOS))
            else:
                sin_json += 1
            continue
        fila, vs = normalizar(fuente.descargar_json(cliente, e.url_json), e.legislatura,
                              e.url_json, e.fecha)  # fmt: skip
        filas.append(fila)
        votos.extend(vs)
    almacen.guardar_dia(dia, filas, votos)
    estado = {
        "legislatura": leg,
        "votaciones": len(filas),
        "sin_json": sin_json,
        "completo": bool(enlaces) and sin_json == 0,
        "comprobado": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifiesto[dia.isoformat()] = estado
    almacen.guardar_manifiesto(manifiesto)
    nivel = logging.INFO if estado["completo"] else logging.WARNING
    log.log(nivel, "%s: %d votaciones, %d sin JSON%s", dia, len(filas), sin_json,
            "" if enlaces else " (el día no tiene ficheros publicados)")  # fmt: skip
    return estado


def actualizar_mes(
    cliente: fuente.Cliente, leg: int, dias: list[date], mes: str, manifiesto: dict,
    forzar: bool = False,
) -> int:  # fmt: skip
    """Descarga los días del mes que falten o estén pendientes. Devuelve cuántos ha pedido."""
    pedidos = 0
    for dia in (d for d in dias if almacen.mes_de(d) == mes):
        estado = manifiesto.get(dia.isoformat())
        if estado and estado.get("completo") and not forzar:
            continue
        actualizar_dia(cliente, leg, dia, manifiesto)
        pedidos += 1
    return pedidos


def generar_informe(mes: str, manifiesto: dict) -> str:
    v, votos = almacen.cargar_mes(mes)
    a = analisis.analizar(mes, v, votos, almacen.dias_pendientes(manifiesto, mes))
    p = informe.escribir(a)
    log.info("Informe %s: %d votaciones -> %s", mes, len(v), p)
    return str(p)


def resumen_actions(lineas: list[str]) -> None:
    """Escribe en el resumen del job de GitHub Actions, si se está dentro de uno."""
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")


# --- Órdenes -----------------------------------------------------------------------------
def cmd_sondear(args) -> int:
    cliente = fuente.Cliente()
    leg, dias = fuente.dias_con_votacion(cliente, args.legislatura)
    print(f"Legislatura {fuente.romano(leg)}: {len(dias)} días con votación, "
          f"del {dias[0]} al {dias[-1]}.")  # fmt: skip
    return 0


def cmd_actualizar(args) -> int:
    cliente = fuente.Cliente()
    manifiesto = almacen.cargar_manifiesto()
    if args.dia:
        dia = date.fromisoformat(args.dia)
        leg = args.legislatura or fuente.dias_con_votacion(cliente)[0]
        actualizar_dia(cliente, leg, dia, manifiesto)
    else:
        mes = almacen.validar_mes(args.mes)
        leg, dias = fuente.dias_con_votacion(cliente, args.legislatura)
        actualizar_mes(cliente, leg, dias, mes, manifiesto, args.forzar)
    log.info("Peticiones al portal: %d", cliente.peticiones)
    return 0


def cmd_informe(args) -> int:
    manifiesto = almacen.cargar_manifiesto()
    meses = [almacen.validar_mes(args.mes)] if args.mes else almacen.meses_guardados()
    for mes in meses:
        generar_informe(mes, manifiesto)
    informe.escribir_indice(manifiesto)
    return 0


def cmd_mensual(args) -> int:
    objetivo = almacen.validar_mes(args.mes) if args.mes else mes_anterior(hoy())
    cliente = fuente.Cliente()
    leg, dias = fuente.dias_con_votacion(cliente, args.legislatura)
    manifiesto = almacen.cargar_manifiesto()
    limite = almacen.sumar_meses(objetivo, -args.revisar)
    meses = {objetivo} | {m for m in almacen.meses_con_pendientes(manifiesto) if m >= limite}
    for mes in sorted(meses):
        actualizar_mes(cliente, leg, dias, mes, manifiesto)
    for mes in sorted(meses):
        generar_informe(mes, manifiesto)
    informe.escribir_indice(manifiesto)

    pendientes = almacen.dias_pendientes(manifiesto)
    log.info("Peticiones al portal: %d. Días pendientes: %s", cliente.peticiones,
             ", ".join(pendientes) or "ninguno")  # fmt: skip
    resumen_actions([
        f"## Informe mensual: {almacen.nombre_mes(objetivo)}",
        f"- Meses revisados: {', '.join(sorted(meses))}",
        f"- Peticiones al portal: {cliente.peticiones}",
        f"- Días con votación aún sin datos: {', '.join(pendientes) or 'ninguno'}",
    ])  # fmt: skip
    return 0


def cmd_historico(args) -> int:
    desde = almacen.validar_mes(args.desde)
    hasta = almacen.validar_mes(args.hasta) if args.hasta else mes_anterior(hoy())
    cliente = fuente.Cliente()
    leg, dias = fuente.dias_con_votacion(cliente, args.legislatura)
    manifiesto = almacen.cargar_manifiesto()
    meses = sorted({almacen.mes_de(d) for d in dias if desde <= almacen.mes_de(d) <= hasta})
    log.info("Legislatura %s: %d meses con votaciones entre %s y %s", fuente.romano(leg),
             len(meses), desde, hasta)  # fmt: skip
    for mes in meses:
        actualizar_mes(cliente, leg, dias, mes, manifiesto, args.forzar)
        generar_informe(mes, manifiesto)
    informe.escribir_indice(manifiesto)
    log.info("Peticiones al portal: %d", cliente.peticiones)
    return 0


def cmd_instagram(args) -> int:
    from pathlib import Path

    from . import instagram

    fondo = Path(args.fondo) if args.fondo else None
    if fondo and not fondo.exists():
        raise ValueError(f"No existe la imagen de fondo {fondo}")
    carpeta = instagram.generar(args.mes, fondo=fondo)
    log.info("Carrusel en %s", carpeta)
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.votaciones", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="orden", required=True)

    def con_legislatura(s):
        s.add_argument("--legislatura", type=int, help="número (15 = XV); por defecto, la actual")
        return s

    con_legislatura(sub.add_parser("sondear")).set_defaults(func=cmd_sondear)

    s = con_legislatura(sub.add_parser("actualizar"))
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--mes")
    g.add_argument("--dia")
    s.add_argument("--forzar", action="store_true", help="vuelve a descargar días ya completos")
    s.set_defaults(func=cmd_actualizar)

    s = sub.add_parser("informe")
    s.add_argument("--mes", help="por defecto, todos los meses guardados")
    s.set_defaults(func=cmd_informe)

    s = con_legislatura(sub.add_parser("mensual"))
    s.add_argument("--mes", help="por defecto, el mes anterior (hora de Madrid)")
    s.add_argument("--revisar", type=int, default=3,
                   help="meses hacia atrás en que se reintentan los días pendientes")  # fmt: skip
    s.set_defaults(func=cmd_mensual)

    s = con_legislatura(sub.add_parser("historico"))
    s.add_argument("--desde", required=True)
    s.add_argument("--hasta", help="por defecto, el mes anterior")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(func=cmd_historico)

    s = sub.add_parser("instagram")
    s.add_argument("--mes", required=True)
    s.add_argument("--fondo", help="ilustración para la portada (notebooks/portada_ia.ipynb)")
    s.set_defaults(func=cmd_instagram)
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        return args.func(args)
    except fuente.ErrorAcceso as e:
        log.error("No se pudo leer el portal del Congreso: %s", e)
        return 2
    except ValueError as e:
        log.error("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
