# -*- coding: utf-8 -*-
"""
Magatzem de dades scrapejades (SQLite).

Es fa servir SQLite en un fitxer dins del repositori: l'analista executa
l'script al seu ordinador, el fitxer es versiona amb git i Streamlit Cloud el
llegeix. Sense credencials ni serveis externs.

Tot passa per aquestes funcions (patró repository): si algun dia es migra a
Postgres, només s'ha de tocar aquest fitxer.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from . import config as cfg

RUTA_BD = cfg.ARREL / "dades" / "lf2.sqlite"
TAULA_BOXSCORE = "boxscore_jugadora"


def _connexio(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = ruta or RUTA_BD
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(ruta)


def desa_boxscore(df: pd.DataFrame, ruta: Path | None = None) -> int:
    """
    Desa (o reemplaça) els boxscores.

    És idempotent: abans d'inserir esborra el que ja hi hagi d'aquests partits,
    així tornar a executar l'scraper no duplica files ni deixa dades velles si
    la FEB ha corregit una acta.
    """
    if df.empty:
        return 0

    with _connexio(ruta) as connexio:
        existeix = connexio.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TAULA_BOXSCORE,)
        ).fetchone()

        if existeix:
            identificadors = sorted({int(i) for i in df["PartitID"].unique()})
            marques = ",".join("?" * len(identificadors))
            connexio.execute(f'DELETE FROM "{TAULA_BOXSCORE}" WHERE "PartitID" IN ({marques})', identificadors)

        df.to_sql(TAULA_BOXSCORE, connexio, if_exists="append", index=False)
        connexio.execute(
            f'CREATE INDEX IF NOT EXISTS idx_boxscore ON "{TAULA_BOXSCORE}" '
            '("Temporada", "Lliga", "Jornada", "Equip")'
        )
    return len(df)


def carrega_boxscore(ruta: Path | None = None) -> pd.DataFrame:
    """Llegeix tot el boxscore desat. Retorna buit si encara no s'ha scrapejat res."""
    ruta = ruta or RUTA_BD
    if not ruta.exists():
        return pd.DataFrame()

    with _connexio(ruta) as connexio:
        existeix = connexio.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TAULA_BOXSCORE,)
        ).fetchone()
        if not existeix:
            return pd.DataFrame()
        return pd.read_sql_query(f'SELECT * FROM "{TAULA_BOXSCORE}"', connexio)


def partits_desats(ruta: Path | None = None) -> set[int]:
    """Identificadors de partit que ja tenim, per no tornar-los a baixar."""
    dades = carrega_boxscore(ruta)
    return set() if dades.empty else {int(i) for i in dades["PartitID"].unique()}


def resum_desat(ruta: Path | None = None) -> pd.DataFrame:
    """Què hi ha al magatzem, per temporada / lliga / jornada."""
    dades = carrega_boxscore(ruta)
    if dades.empty:
        return pd.DataFrame(columns=["Temporada", "Lliga", "Jornada", "Partits", "Equips", "Files"])

    return (
        dades.groupby(["Temporada", "Lliga", "Jornada"])
        .agg(Partits=("PartitID", "nunique"), Equips=("Equip", "nunique"), Files=("Jugador", "size"))
        .reset_index()
        .sort_values(["Temporada", "Lliga", "Jornada"], ignore_index=True)
    )
