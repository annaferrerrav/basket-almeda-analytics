# -*- coding: utf-8 -*-
"""
Script d'actualització de boxscores.

  python -m almeda_pbp.feb --temporada 2025 --jornades 1 2 3
  python -m almeda_pbp.feb --temporada 2025 --lligues A --jornades 4 --refes

L'app Streamlit NO escriu mai: llegeix el que aquest script deixa a la BBDD.
Recorda que `--temporada 2025` vol dir la temporada 2025/26 (any d'inici).
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from .. import magatzem
from . import boxscore, calendari
from .client import ClientFEB, ErrorFEB


def analitza_arguments(arguments=None):
    analitzador = argparse.ArgumentParser(
        prog="python -m almeda_pbp.feb",
        description="Baixa els boxscores de LF2 de baloncestoenvivo.feb.es i els desa a la BBDD.",
    )
    analitzador.add_argument(
        "--temporada", type=int, default=2025,
        help="Any d'INICI de temporada: 2025 = 2025/26 (per defecte), 2026 = 2026/27.",
    )
    analitzador.add_argument(
        "--lligues", nargs="+", default=["A", "B"],
        help="Lletres dels grups a baixar (per defecte A i B).",
    )
    analitzador.add_argument(
        "--jornades", nargs="+", type=int, default=[1, 2, 3],
        help="Jornades a baixar (per defecte 1 2 3).",
    )
    analitzador.add_argument(
        "--refes", action="store_true",
        help="Torna a baixar partits que ja tenim desats (per defecte s'ometen).",
    )
    analitzador.add_argument(
        "--espera", type=float, default=1.5,
        help="Segons entre peticions a la FEB (per defecte 1.5).",
    )
    return analitzador.parse_args(arguments)


def executa(arguments=None) -> int:
    opcions = analitza_arguments(arguments)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    registre = logging.getLogger("actualitza")

    etiqueta_temporada = f"{opcions.temporada}-{str(opcions.temporada + 1)[-2:]}"
    client = ClientFEB(espera=opcions.espera)

    try:
        disponibles = calendari.grups(client, opcions.temporada)
    except ErrorFEB as err:
        registre.error("No s'ha pogut llegir el calendari: %s", err)
        return 1

    registre.info("Temporada %s · grups trobats: %s", etiqueta_temporada, ", ".join(sorted(disponibles)))

    desconegudes = [ll for ll in opcions.lligues if ll not in disponibles]
    if desconegudes:
        registre.error("Aquests grups no existeixen aquesta temporada: %s", ", ".join(desconegudes))
        return 1

    ja_tenim = set() if opcions.refes else magatzem.partits_desats()
    trossos: list[pd.DataFrame] = []
    fallats: list[tuple[int, str]] = []

    for lliga in opcions.lligues:
        partits = calendari.partits(
            client, opcions.temporada, lliga, disponibles[lliga], jornades=opcions.jornades
        )
        registre.info("Lliga %s: %d partits a les jornades %s",
                      lliga, len(partits), ", ".join(map(str, opcions.jornades)))

        for partit in partits:
            if partit.partit_id in ja_tenim:
                registre.info("  · j%-2d %s (ja desat, s'omet)", partit.jornada, partit.partit_id)
                continue
            try:
                df = boxscore.descarrega(client, partit, etiqueta_temporada)
                trossos.append(df)
                registre.info("  ✔ j%-2d %s vs %s (%s)",
                              partit.jornada, partit.equip_local, partit.equip_visitant, partit.resultat)
            except Exception as err:
                fallats.append((partit.partit_id, str(err)))
                registre.warning("  ✘ j%-2d partit %s: %s", partit.jornada, partit.partit_id, err)

    if not trossos:
        registre.info("Res de nou per desar.")
        return 0 if not fallats else 1

    dades = pd.concat(trossos, ignore_index=True)
    desades = magatzem.desa_boxscore(dades)
    registre.info("\nDesades %d files (%d partits) a %s", desades, dades["PartitID"].nunique(), magatzem.RUTA_BD)

    if fallats:
        registre.warning("%d partits han fallat: %s", len(fallats), ", ".join(str(i) for i, _ in fallats))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(executa())
