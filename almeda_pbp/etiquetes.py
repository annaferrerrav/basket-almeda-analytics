# -*- coding: utf-8 -*-
"""
Etiquetes per sistema.

Un TOML a `dades/etiquetes_sistemes.toml` on cada sistema del PBP (`Tàctica`)
porta la llista d'etiquetes que l'analista li vulgui posar:

    [sistemes]
    "Pisa" = ["banda"]
    "Fons 21" = ["fons"]
    "Triple" = ["zona"]

D'aquí surt un vocabulari d'etiquetes que es pot filtrar a la pàgina de
Sistemes. Filtrar per `banda` vol dir quedar-se amb totes les jugades dels
sistemes etiquetats `banda`.

TOML i no Excel perquè això és una taula petita i estable — desenes de files,
no milers — que descriu el REPERTORI, no les jugades: es toca un cop cada
temporada i es llegeix com un fitxer de configuració. Un sistema sense
etiquetes hi és igualment, amb la llista buida, perquè es vegi què queda per
etiquetar.

Les etiquetes no es reparteixen per temporada: el repertori és el mateix i un
sistema que es diu igual a 25-26 i a 26-27 és el mateix sistema.
"""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import pandas as pd

from . import config as cfg

NOM_FITXER = "dades/etiquetes_sistemes.toml"

_CAPCALERA = """# Etiquetes per sistema.
#
# Escriu, a cada sistema, les etiquetes que li vulguis posar. Són text lliure:
# no hi ha cap llista tancada, el vocabulari s'inventa escrivint.
#
#     "Pisa" = ["banda"]
#     "Fons 21" = ["fons", "fora de banda"]
#     "Triple" = ["zona"]
#
# Un sistema pot tenir-ne diverses, o cap (llista buida). Els sistemes surten
# d'aquí ordenats per quantes vegades s'han jugat, amb el comptatge al costat.
#
# Per refrescar la llista quan aparegui un sistema nou:
#     python -m almeda_pbp.etiquetes
# Les etiquetes ja escrites no es perden mai en regenerar.

[sistemes]
"""


def ruta_fitxer(arrel: Path | None = None) -> Path:
    """On viu (o ha de viure) el fitxer d'etiquetes."""
    return (Path(arrel) if arrel is not None else cfg.ARREL) / NOM_FITXER


def carrega_etiquetes(arrel: Path | None = None) -> dict[str, list[str]]:
    """
    {sistema: [etiquetes]} tal com està escrit al TOML.

    Retorna un diccionari buit si el fitxer no hi és o està mal format: sense
    etiquetes es veu tot, que és el comportament per defecte i no un error.
    """
    ruta = ruta_fitxer(arrel)
    if not ruta.exists():
        return {}

    try:
        with ruta.open("rb") as fitxer:
            document = tomllib.load(fitxer)
    except (tomllib.TOMLDecodeError, OSError):
        return {}

    sistemes = document.get("sistemes", {})
    if not isinstance(sistemes, dict):
        return {}

    resultat: dict[str, list[str]] = {}
    for sistema, valor in sistemes.items():
        # Una sola etiqueta es pot haver escrit sense claudàtors.
        if isinstance(valor, str):
            valor = [valor]
        if not isinstance(valor, list):
            continue
        resultat[str(sistema)] = sorted({str(e).strip().lower() for e in valor if str(e).strip()})
    return resultat


def etiquetes_disponibles(mapa: dict[str, list[str]]) -> list[str]:
    """Totes les etiquetes escrites, ordenades i sense repetir."""
    trobades: set[str] = set()
    for llista in mapa.values():
        trobades.update(llista)
    return sorted(trobades)


def sistemes_amb_etiqueta(
    mapa: dict[str, list[str]],
    etiquetes: list[str],
    mode: str = "qualsevol",
) -> list[str]:
    """
    Quins sistemes tenen les etiquetes demanades.

    `mode`: "qualsevol" (en té almenys una) o "totes" (les té totes).
    """
    volgudes = {e.strip().lower() for e in etiquetes if e.strip()}
    if not volgudes:
        return sorted(mapa)

    coincideix = (lambda t: volgudes.issubset(t)) if mode == "totes" else (lambda t: bool(t & volgudes))
    return sorted(sistema for sistema, llista in mapa.items() if coincideix(set(llista)))


def filtra_per_etiqueta(
    dades: pd.DataFrame,
    mapa: dict[str, list[str]],
    etiquetes: list[str] | None = None,
    mode: str = "qualsevol",
) -> pd.DataFrame:
    """Es queda amb les jugades dels sistemes que porten les etiquetes demanades."""
    if dades.empty or not etiquetes:
        return dades

    sistemes = sistemes_amb_etiqueta(mapa, etiquetes, mode=mode)
    return dades[dades[cfg.COL_TACTICA].isin(sistemes)].copy()


def sistemes_del_pbp(dades: pd.DataFrame) -> list[tuple[str, int]]:
    """(sistema, vegades jugat), de més a menys jugat."""
    if dades.empty or cfg.COL_TACTICA not in dades.columns:
        return []
    comptatge = dades[cfg.COL_TACTICA].dropna().value_counts()
    return [(str(sistema), int(vegades)) for sistema, vegades in comptatge.items()]


def _escapa(text: str) -> str:
    """Cadena TOML bàsica: cal escapar la barra invertida i les cometes."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def genera_plantilla(dades: pd.DataFrame, arrel: Path | None = None) -> tuple[Path, int, int]:
    """
    Crea o actualitza el TOML amb tots els sistemes que apareixen al PBP.

    Mai destrueix feina feta: les etiquetes ja escrites es tornen a col·locar
    al seu sistema, i un sistema que ja no apareix al PBP es conserva igualment
    si tenia etiquetes (pot ser d'una temporada que ara no està carregada).

    Retorna (ruta, sistemes totals, sistemes amb almenys una etiqueta).
    """
    existents = carrega_etiquetes(arrel)
    ordenats = sistemes_del_pbp(dades)
    vistos = {sistema for sistema, _ in ordenats}

    linies = [_CAPCALERA]
    for sistema, vegades in ordenats:
        etiquetes = existents.get(sistema, [])
        valor = ", ".join(f'"{_escapa(e)}"' for e in etiquetes)
        linies.append(f'"{_escapa(sistema)}" = [{valor}]  # {vegades} jugades\n')

    orfes = sorted(s for s, e in existents.items() if s not in vistos and e)
    if orfes:
        linies.append(
            "\n# Sistemes que ja no surten al PBP carregat però tenen etiquetes:\n"
            "# es conserven per si són d'una temporada que ara no està carregada.\n"
        )
        for sistema in orfes:
            valor = ", ".join(f'"{_escapa(e)}"' for e in existents[sistema])
            linies.append(f'"{_escapa(sistema)}" = [{valor}]\n')

    ruta = ruta_fitxer(arrel)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("".join(linies), encoding="utf-8")

    total = len(ordenats) + len(orfes)
    amb_etiqueta = sum(1 for s in list(vistos) + orfes if existents.get(s))
    return ruta, total, amb_etiqueta


def _cli() -> None:
    from . import carrega

    argparse.ArgumentParser(
        description="Crea o actualitza dades/etiquetes_sistemes.toml amb els sistemes del PBP."
    ).parse_args()

    resultat = carrega.carrega_pbp(cfg.ARREL)
    if resultat.dades.empty:
        print("No hi ha cap fitxer PBP carregat: no se'n pot treure cap sistema.")
        return

    ruta, total, amb_etiqueta = genera_plantilla(resultat.dades, cfg.ARREL)
    print(f"{total} sistemes a {ruta} ({amb_etiqueta} ja etiquetats).")


if __name__ == "__main__":
    _cli()
