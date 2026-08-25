# -*- coding: utf-8 -*-
"""
Parsing del boxscore d'un partit.

La lògica de lectura de les taules ve de `scraping_boxscore_jornada.py`, que ja
funcionava. Aquí s'hi han corregit dues coses:

1. Els punts del rival es prenen del MARCADOR del partit, no invertint el
   DataFrame concatenat (`df['PT'].iloc[::-1]`). Aquell truc només dona el
   resultat correcte si els dos equips tenen exactament el mateix nombre de
   jugadores a l'acta, cosa que sovint no passa.
2. No es modifiquen talls del DataFrame (`total['Equip'] = ...` sobre un slice),
   que és el que provocava els SettingWithCopyWarning.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

from .client import ClientFEB
from .calendari import Partit

# Ordre real de les columnes de la taula de l'acta.
COLUMNES = [
    "Inicial", "Dorsal", "Jugador", "MIN", "PT", "T2", "T3", "TC", "TL",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT",
    "FC", "FR", "VA", "+/-",
]
COLUMNES_TIR = ["T2", "T3", "TC", "TL"]


def _minuts_a_decimal(valor) -> float:
    """'24:57' -> 24.95. Un valor buit o rar val 0 minuts, no NaN."""
    text = str(valor).strip()
    if not text or text in {"nan", "-"}:
        return 0.0
    parts = text.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60
        return float(parts[0])
    except ValueError:
        return 0.0


def _text_de_cella(cella) -> str:
    """Text d'una cel·la, descartant el percentatge que la FEB hi encasta."""
    enllac = cella.find("a")
    if enllac:
        return enllac.get_text(strip=True)
    percentatge = cella.find("span", class_="porcentaje")
    if percentatge:
        percentatge.extract()
    return cella.get_text(strip=True)


def _taula_a_dataframe(taula) -> pd.DataFrame:
    files = []
    for fila in taula.find_all("tr")[2:]:  # dues files de capçalera
        celles = [_text_de_cella(td) for td in fila.find_all("td")]
        if any(celles):
            files.append(celles)

    if not files:
        return pd.DataFrame(columns=COLUMNES)

    # Si l'acta porta menys columnes de les esperades, s'omple per la dreta
    # en comptes de petar: així un partit rar no tomba tota la jornada.
    amplada = len(COLUMNES)
    files = [(f + [""] * amplada)[:amplada] for f in files]
    return pd.DataFrame(files, columns=COLUMNES)


def _desglossa_tirs(df: pd.DataFrame) -> pd.DataFrame:
    """De '4/12' en treu convertits (4) i intentats (12), i el percentatge."""
    for columna in COLUMNES_TIR:
        parell = df[columna].astype(str).str.extract(r"(\d+)/(\d+)")
        df[f"{columna}C"] = pd.to_numeric(parell[0], errors="coerce").fillna(0).astype(int)
        df[f"{columna}I"] = pd.to_numeric(parell[1], errors="coerce").fillna(0).astype(int)
        intentats = df[f"{columna}I"]
        df[f"{columna} (%)"] = np.where(
            intentats == 0, 0.0, (df[f"{columna}C"] / intentats.replace(0, np.nan) * 100).round(1)
        )
    return df.drop(columns=COLUMNES_TIR)


def parseja(html: str, partit: Partit, temporada: str) -> pd.DataFrame:
    """
    Converteix la pàgina d'un partit en una fila per jugadora (dels dos equips).

    La fila de totals de cada equip es conserva amb Jugador = 'TOTAL': és la que
    fa servir tot el càlcul d'equip, i recalcular-la sumant jugadores donaria
    diferències quan l'acta té alguna incoherència.
    """
    sopa = BeautifulSoup(html, "html.parser")

    marcador = sopa.find("div", class_="box-marcador")
    div_local = marcador.find("div", class_="columna equipo local")
    div_visitant = marcador.find("div", class_="columna equipo visitante")

    equip_local = sopa.find("span", id="_ctl0_MainContentPlaceHolderMaster_equipoLocalNombre").get_text(strip=True)
    equip_visitant = div_visitant.find("span", class_="nombre").get_text(strip=True)
    punts_local = int(div_local.find("span", class_="resultado").get_text(strip=True))
    punts_visitant = int(div_visitant.find("span", class_="resultado").get_text(strip=True))

    caixa_dades = sopa.find("div", class_="box-datos-partido")
    text_data = caixa_dades.find("div", class_="fecha").find("span", class_="txt").get_text(strip=True)
    data, _, hora = text_data.partition(" - ")

    taules = [d.find("table") for d in sopa.find_all("div", class_="responsive-scroll") if d.find("table")]
    if len(taules) < 2:
        raise ValueError(f"El partit {partit.partit_id} no té les dues taules de l'acta.")

    trossos = []
    for i, taula in enumerate(taules[:2]):
        es_local = i == 0
        df = _taula_a_dataframe(taula)
        if df.empty:
            continue

        df = _desglossa_tirs(df)

        # Jugador buit = fila de totals de l'equip.
        df["Jugador"] = df["Jugador"].replace("", np.nan).fillna("TOTAL")
        df["Inicial"] = (df["Inicial"].astype(str).str.strip() == "*").astype(int)
        df["MIN"] = df["MIN"].map(_minuts_a_decimal)

        for columna in ["PT", "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR", "VA", "+/-", "Dorsal"]:
            df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0).astype(int)

        df["Temporada"] = temporada
        df["Lliga"] = partit.lliga
        df["Jornada"] = partit.jornada
        df["PartitID"] = partit.partit_id
        df["URL"] = partit.url
        df["Data"] = data
        df["Hora"] = hora
        df["Equip"] = equip_local if es_local else equip_visitant
        df["Rival"] = equip_visitant if es_local else equip_local
        df["Pista"] = "Casa" if es_local else "Fora"
        df["PT equip"] = punts_local if es_local else punts_visitant
        df["PT rival"] = punts_visitant if es_local else punts_local
        df["Victòria"] = int(df["PT equip"].iloc[0] > df["PT rival"].iloc[0])

        trossos.append(df)

    return pd.concat(trossos, ignore_index=True)


ORDRE_COLUMNES = [
    "Temporada", "Lliga", "Jornada", "PartitID", "Data", "Hora",
    "Equip", "Rival", "Pista", "PT equip", "PT rival", "Victòria",
    "Inicial", "Dorsal", "Jugador", "MIN", "PT",
    "T2C", "T2I", "T2 (%)", "T3C", "T3I", "T3 (%)",
    "TCC", "TCI", "TC (%)", "TLC", "TLI", "TL (%)",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR", "VA", "+/-",
    "URL",
]


def descarrega(client: ClientFEB, partit: Partit, temporada: str) -> pd.DataFrame:
    """Baixa i parseja el boxscore d'un partit."""
    html = client.html(partit.url)
    df = parseja(html, partit, temporada)
    return df[[c for c in ORDRE_COLUMNES if c in df.columns]]
