# -*- coding: utf-8 -*-
"""
La plantilla, a partir dels boxscores oficials de la FEB.

El PBP manual sap coses que l'acta no sap (quin sistema es jugava, qui hi havia
a pista a cada possessió), però per a les xifres bàsiques d'una jugadora
—minuts, punts, tirs, rebots, assistències, valoració— la font bona és l'acta
oficial: està arbitrada, no depèn de qui anotava aquell dia i inclou coses que
el PBP no recull (minuts, taps, faltes, tirs lliures).

Per unir les dues fonts cal una taula de noms: el PBP fa servir noms curts
("Tierno", "Puyi") i l'acta el nom complet ("TIERNO MARTÍ, LAURA"). Viu a
`dades/noms_jugadores.toml` i es genera amb `python -m almeda_pbp.jugadores`,
que hi deixa fetes les correspondències inequívoques i buides les altres.
No s'endevina cap parella dubtosa: una correspondència mal feta barrejaria les
estadístiques de dues jugadores diferents, que és pitjor que no tenir-les.
"""

from __future__ import annotations

import argparse
import tomllib
import unicodedata
from pathlib import Path

import pandas as pd

from . import config as cfg

EQUIP_PROPI = "BASKET ALMEDA"
NOM_FITXER = "dades/noms_jugadores.toml"

# Columnes de l'acta que se sumen tal qual al llarg de la temporada.
COLS_SUMA = [
    "MIN", "PT", "T2C", "T2I", "T3C", "T3I", "TCC", "TCI", "TLC", "TLI",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR", "VA", "+/-",
]

# Les que tenen sentit com a mitjana per partit. La resta (percentatges) es
# calculen sobre els totals acumulats, mai com a mitjana de percentatges.
COLS_PER_PARTIT = [
    "MIN", "PT", "T2C", "T2I", "T3C", "T3I", "TCC", "TCI", "TLC", "TLI",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR", "VA", "+/-",
]

_CAPCALERA = """# Correspondència entre els noms curts del PBP i els de l'acta oficial.
#
#     "Tierno" = "TIERNO MARTÍ, LAURA"
#
# Deixa-ho buit ("") si una jugadora del PBP no surt a cap acta descarregada,
# o si el nom curt no correspon a ningú. Les que ja estan plenes s'han trobat
# soles perquè el nom curt hi apareix sencer i sense ambigüitat.
#
# Per refrescar la llista quan es descarreguin actes noves:
#     python -m almeda_pbp.jugadores
# El que ja hi hagi escrit no es perd mai.

[noms]
"""


def ruta_fitxer(arrel: Path | None = None) -> Path:
    return (Path(arrel) if arrel is not None else cfg.ARREL) / NOM_FITXER


def _clau(text) -> str:
    """Minúscules i sense accents, per comparar noms escrits de maneres diferents."""
    net = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(c for c in net if not unicodedata.combining(c))


def carrega_noms(arrel: Path | None = None) -> dict[str, str]:
    """{nom curt del PBP: nom oficial}. Les entrades buides no hi surten."""
    ruta = ruta_fitxer(arrel)
    if not ruta.exists():
        return {}
    try:
        with ruta.open("rb") as fitxer:
            document = tomllib.load(fitxer)
    except (tomllib.TOMLDecodeError, OSError):
        return {}

    noms = document.get("noms", {})
    if not isinstance(noms, dict):
        return {}
    return {str(k): str(v) for k, v in noms.items() if isinstance(v, str) and v.strip()}


def noms_curts(arrel: Path | None = None) -> dict[str, str]:
    """L'invers: {nom oficial: nom curt del PBP}."""
    return {oficial: curt for curt, oficial in carrega_noms(arrel).items()}


def boxscore_equip(
    boxscore: pd.DataFrame,
    temporada_feb: str,
    equip: str = EQUIP_PROPI,
    jornades: list[int] | None = None,
) -> pd.DataFrame:
    """Files d'acta de les jugadores d'un equip (sense la fila TOTAL)."""
    if boxscore.empty:
        return boxscore

    resultat = boxscore[
        (boxscore["Temporada"] == temporada_feb)
        & (boxscore["Equip"] == equip)
        & (boxscore["Jugador"] != "TOTAL")
    ]
    if jornades:
        resultat = resultat[resultat["Jornada"].isin(jornades)]
    return resultat.copy()


def _percentatge(fets: pd.Series, intents: pd.Series) -> pd.Series:
    """Percentatge sobre els totals acumulats, no mitjana de percentatges."""
    return (fets.divide(intents.where(intents != 0)) * 100).round(1)


def plantilla_oficial(
    boxscore: pd.DataFrame,
    temporada_feb: str,
    equip: str = EQUIP_PROPI,
    jornades: list[int] | None = None,
    per_partit: bool = False,
    arrel: Path | None = None,
) -> pd.DataFrame:
    """
    Una fila per jugadora amb les xifres acumulades de l'acta.

    `per_partit=True` divideix els comptatges pels partits jugats. Els
    percentatges NO es toquen: sempre surten dels totals acumulats (una
    jugadora que fa 1/1 un partit i 3/20 el següent tira un 19%, no la mitjana
    de 100% i 15%).
    """
    columnes = ["Jugadora", "Nom oficial", "Dorsal", "Partits", "Titular"] + COLS_SUMA + ["T2 (%)", "T3 (%)", "TC (%)", "TL (%)"]

    files = boxscore_equip(boxscore, temporada_feb, equip=equip, jornades=jornades)
    if files.empty:
        return pd.DataFrame(columns=columnes)

    presents = [c for c in COLS_SUMA if c in files.columns]
    agregat = (
        files.groupby("Jugador")
        .agg(
            Dorsal=("Dorsal", "first"),
            Partits=("Jornada", "nunique"),
            Titular=("Inicial", "sum"),
            **{col: (col, "sum") for col in presents},
        )
        .reset_index()
        .rename(columns={"Jugador": "Nom oficial"})
    )

    # Els percentatges es calculen ABANS de dividir per partits: si es fes
    # després, sortirien igual però per accident, i qualsevol canvi d'ordre
    # aquí els trencaria en silenci.
    for etiqueta, fets, intents in (
        ("T2 (%)", "T2C", "T2I"), ("T3 (%)", "T3C", "T3I"),
        ("TC (%)", "TCC", "TCI"), ("TL (%)", "TLC", "TLI"),
    ):
        if fets in agregat.columns and intents in agregat.columns:
            agregat[etiqueta] = _percentatge(agregat[fets], agregat[intents])

    if per_partit:
        for col in (c for c in COLS_PER_PARTIT if c in agregat.columns):
            agregat[col] = (agregat[col] / agregat["Partits"]).round(1)

    curts = noms_curts(arrel)
    agregat["Jugadora"] = agregat["Nom oficial"].map(curts).fillna(agregat["Nom oficial"])
    agregat["Titular"] = agregat["Titular"].astype(int)

    ordre = "PT" if "PT" in agregat.columns else "Partits"
    return agregat[[c for c in columnes if c in agregat.columns]].sort_values(
        ordre, ascending=False, ignore_index=True
    )


def partits_jugadora(
    boxscore: pd.DataFrame,
    temporada_feb: str,
    nom_oficial: str,
    equip: str = EQUIP_PROPI,
    jornades: list[int] | None = None,
) -> pd.DataFrame:
    """L'acta d'una jugadora, partit a partit."""
    files = boxscore_equip(boxscore, temporada_feb, equip=equip, jornades=jornades)
    if files.empty:
        return files

    seves = files[files["Jugador"] == nom_oficial]
    columnes = ["Jornada", "Rival", "Pista", "MIN", "PT", "T2C", "T2I", "T3C", "T3I",
                "TLC", "TLI", "RO", "RD", "RT", "AS", "BR", "BP", "FC", "FR", "VA", "+/-"]
    presents = [c for c in columnes if c in seves.columns]
    return seves[presents].sort_values("Jornada", ignore_index=True)


def genera_noms(
    noms_pbp: list[str],
    boxscore: pd.DataFrame,
    equip: str = EQUIP_PROPI,
    arrel: Path | None = None,
) -> tuple[Path, int, int]:
    """
    Crea o actualitza el TOML de correspondència de noms.

    Deixa fetes només les parelles INEQUÍVOQUES: el nom curt ha d'aparèixer
    sencer dins d'un únic nom oficial. Un nom curt que encaixi amb dos noms
    oficials (p. ex. "Mar" dins de "MARINA" i de "COLL-VINENT, MAR") es deixa
    buit: barrejar dues jugadores és pitjor que no tenir-ne les dades.

    Retorna (ruta, noms totals, noms amb correspondència).
    """
    existents = carrega_noms(arrel)

    oficials = []
    if not boxscore.empty:
        del_equip = boxscore[(boxscore["Equip"] == equip) & (boxscore["Jugador"] != "TOTAL")]
        oficials = sorted(del_equip["Jugador"].dropna().unique().tolist())

    linies = [_CAPCALERA]
    resolts = 0
    for curt in sorted(noms_pbp):
        oficial = existents.get(curt, "")
        if not oficial:
            candidats = [o for o in oficials if _clau(curt) in _clau(o)]
            oficial = candidats[0] if len(candidats) == 1 else ""
        if oficial:
            resolts += 1
        linies.append(f'"{curt}" = "{oficial}"\n')

    sense_curt = [o for o in oficials if o not in set(existents.values())]
    sense_curt = [o for o in sense_curt if not any(_clau(c) in _clau(o) for c in noms_pbp)]
    if sense_curt:
        linies.append("\n# A l'acta però sense cap nom curt del PBP que hi encaixi:\n")
        linies.extend(f"#   {o}\n" for o in sense_curt)

    ruta = ruta_fitxer(arrel)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("".join(linies), encoding="utf-8")
    return ruta, len(noms_pbp), resolts


def _cli() -> None:
    from . import carrega, magatzem

    argparse.ArgumentParser(
        description="Crea o actualitza dades/noms_jugadores.toml amb els noms del PBP i de l'acta."
    ).parse_args()

    dades = carrega.carrega_pbp(cfg.ARREL).dades
    noms_pbp = carrega.jugadores_disponibles(dades)
    if not noms_pbp:
        print("No hi ha cap jugadora al PBP carregat.")
        return

    ruta, total, resolts = genera_noms(noms_pbp, magatzem.carrega_boxscore(), arrel=cfg.ARREL)
    print(f"{total} noms del PBP a {ruta} ({resolts} amb correspondència a l'acta).")


if __name__ == "__main__":
    _cli()
