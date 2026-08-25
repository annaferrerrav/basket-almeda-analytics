# -*- coding: utf-8 -*-
"""
Mètriques d'equip a partir dels boxscores scrapejats.

Dues decisions que canvien els números i convé tenir clares:

1. **Els percentatges es calculen sobre els totals, no com a mitjana de
   percentatges.** Un equip que un dia tira 1/1 (100%) i un altre 3/20 (15%) no
   té un 57,5% de mitjana: té 4/21, un 19%. Fer la mitjana dels percentatges
   dona pes igual a partits amb mostres molt diferents.

2. **Les mitjanes de comptatge són per partit**, no per possessió, perquè és
   com es llegeixen a l'acta. El ritme el porten a part «Possessions» i els
   índexs d'eficiència (OER/DER), que sí estan normalitzats per possessió.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Columnes de comptatge de l'acta que es promitgen per partit.
COMPTATGE = [
    "PT", "T2C", "T2I", "T3C", "T3I", "TCC", "TCI", "TLC", "TLI",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR", "VA",
]

# Direcció de cada mètrica: +1 = com més alt millor, -1 = com més alt pitjor,
# 0 = ni bo ni dolent (és volum o estil, no rendiment).
DIRECCIO = {
    "PT": 1, "PT rival": -1,
    "T2C": 1, "T2I": 0, "T2 %": 1,
    "T3C": 1, "T3I": 0, "T3 %": 1,
    "TCC": 1, "TCI": 0, "TC %": 1,
    "TLC": 1, "TLI": 0, "TL %": 1,
    "RO": 1, "RD": 1, "RT": 1,
    "AS": 1, "BR": 1, "BP": -1,
    "TapF": 1, "TapC": -1, "MT": 1,
    "FC": -1, "FR": 1, "VA": 1,
    "Possessions": 0, "OER": 1, "DER": -1, "NET": 1,
    "eFG %": 1, "%TO": -1, "ORB %": 1, "DRB %": 1, "RTL": 1,
}

# Els 4 Factors clàssics (eFG%, TOV%, ORB%/DRB%, FT rate) van en un bloc a
# part, visualment diferenciat: no són un comptatge de l'acta sinó una mètrica
# calculada, i barrejar-los amb "quants tirs de 3 ha fet" confon el que és cru
# amb el que és una ràtio d'eficiència.
FACTORS = ["eFG %", "%TO", "ORB %", "DRB %", "RTL"]

# Blocs que surten sempre, a la vista compacta. TapF/TapC/MT/TLC/TLI queden
# fora perquè no aporten res que TL% i FC/FR ja no diguin per a una ullada
# ràpida; només es veuen amb "Mostrar tot".
BLOCS = {
    "Marcador": ["PT", "PT rival", "VA"],
    "Tir de 2": ["T2C", "T2I", "T2 %"],
    "Tir de 3": ["T3C", "T3I", "T3 %"],
    "Tir de camp": ["TCC", "TCI", "TC %"],
    "Tirs lliures": ["TL %"],
    "Rebot": ["RO", "RD", "RT"],
    "Passada i pilota": ["AS", "BR", "BP"],
    "Defensa i faltes": ["FC", "FR"],
    "Ritme i eficiència": ["Possessions", "OER", "DER", "NET"],
}

# Només visibles amb "Mostrar tot".
BLOCS_OCULTS = {
    "Tirs lliures (detall)": ["TLC", "TLI"],
    "Taps": ["TapF", "TapC", "MT"],
}

# Quants decimals té sentit ensenyar de cada cosa.
DECIMALS = {"OER": 1, "DER": 1, "NET": 1, "Possessions": 1, "RTL": 3}
DECIMALS_PER_DEFECTE = 1
DECIMALS_PERCENTATGE = 1


def _percentatge(numerador, denominador):
    """Divisió protegida en percentatge: denominador 0 dona 0, mai NaN."""
    num = np.asarray(numerador, dtype="float64")
    den = np.asarray(denominador, dtype="float64")
    return np.round(np.divide(num, den, out=np.zeros_like(num), where=den != 0) * 100, 1)


def totals_per_partit(boxscore: pd.DataFrame) -> pd.DataFrame:
    """
    Una fila per equip i partit, amb les dades del rival al costat.

    Les dades del rival calen per a ORB% i DRB%: el rebot ofensiu propi només
    es pot valorar contra els rebots defensius que va agafar l'altre equip.
    """
    if boxscore.empty:
        return pd.DataFrame()

    totals = boxscore[boxscore["Jugador"] == "TOTAL"].copy()
    if totals.empty:
        return pd.DataFrame()

    rival = totals[["PartitID", "Equip", "RO", "RD", "TCI", "TLI", "BP", "PT"]].rename(
        columns={
            "Equip": "_equip_rival", "RO": "RO rival", "RD": "RD rival",
            "TCI": "TCI rival", "TLI": "TLI rival", "BP": "BP rival", "PT": "PT rival calc",
        }
    )
    creuat = totals.merge(rival, on="PartitID")
    # Cada partit té dues files; l'auto-unió en genera quatre. Ens quedem amb
    # les dues on l'equip i el rival són diferents.
    return creuat[creuat["Equip"] != creuat["_equip_rival"]].drop(columns=["_equip_rival"])


def taula_equips(
    boxscore: pd.DataFrame,
    lligues: list[str] | None = None,
    jornades: list[int] | None = None,
) -> pd.DataFrame:
    """Una fila per equip amb totes les mètriques promitjades."""
    per_partit = totals_per_partit(boxscore)
    if per_partit.empty:
        return pd.DataFrame()

    if lligues:
        per_partit = per_partit[per_partit["Lliga"].isin(lligues)]
    if jornades:
        per_partit = per_partit[per_partit["Jornada"].isin(jornades)]
    if per_partit.empty:
        return pd.DataFrame()

    a_sumar = COMPTATGE + ["PT rival", "RO rival", "RD rival"]
    sumes = per_partit.groupby(["Lliga", "Equip"])[a_sumar].sum()
    partits = per_partit.groupby(["Lliga", "Equip"]).size().rename("Partits")

    taula = pd.concat([partits, sumes], axis=1).reset_index()

    # Mitjanes per partit dels comptatges.
    resultat = taula[["Lliga", "Equip", "Partits"]].copy()
    for columna in COMPTATGE + ["PT rival"]:
        resultat[columna] = np.round(taula[columna] / taula["Partits"], 1)

    # Percentatges sobre els totals acumulats.
    resultat["T2 %"] = _percentatge(taula["T2C"], taula["T2I"])
    resultat["T3 %"] = _percentatge(taula["T3C"], taula["T3I"])
    resultat["TC %"] = _percentatge(taula["TCC"], taula["TCI"])
    resultat["TL %"] = _percentatge(taula["TLC"], taula["TLI"])
    resultat["eFG %"] = _percentatge(taula["TCC"] + 0.5 * taula["T3C"], taula["TCI"])
    resultat["RTL"] = np.round(
        np.divide(taula["TLI"], taula["TCI"], out=np.zeros(len(taula)), where=taula["TCI"] != 0), 3
    )

    # Possessions i eficiència.
    possessions = taula["TCI"] + 0.44 * taula["TLI"] + taula["BP"] - taula["RO"]
    resultat["Possessions"] = np.round(possessions / taula["Partits"], 1)
    resultat["OER"] = _percentatge(taula["PT"], possessions)
    resultat["DER"] = _percentatge(taula["PT rival"], possessions)
    resultat["NET"] = np.round(resultat["OER"] - resultat["DER"], 1)

    jugades = taula["TCI"] + 0.44 * taula["TLI"] + taula["BP"]
    resultat["%TO"] = _percentatge(taula["BP"], jugades)
    resultat["ORB %"] = _percentatge(taula["RO"], taula["RO"] + taula["RD rival"])
    resultat["DRB %"] = _percentatge(taula["RD"], taula["RD"] + taula["RO rival"])

    return resultat.sort_values(["Lliga", "Equip"], ignore_index=True)


def metriques_disponibles(taula: pd.DataFrame) -> list[str]:
    """
    Totes les mètriques presents a la taula, en l'ordre dels blocs.

    Inclou els 4 Factors i els blocs ocults: aquesta llista alimenta la taula
    completa i els rànquings, que han de tenir-ho tot encara que la vista
    compacta n'amagui una part.
    """
    ordenades = (
        [m for bloc in BLOCS.values() for m in bloc]
        + FACTORS
        + [m for bloc in BLOCS_OCULTS.values() for m in bloc]
    )
    return [m for m in ordenades if m in taula.columns]


def mitjana_lliga(taula: pd.DataFrame) -> pd.Series:
    """
    Mitjana de la lliga: la mitjana dels equips, no la de tots els partits.

    Com que tots els equips juguen les mateixes jornades, les dues coses
    coincideixen; es fa per equip perquè segueixi sent correcte si algun dia hi
    ha partits ajornats i un equip n'ha jugat un menys.
    """
    if taula.empty:
        return pd.Series(dtype="float64")
    return taula[metriques_disponibles(taula)].mean().round(2)


def comparativa(taula: pd.DataFrame, equip: str) -> pd.DataFrame:
    """
    Per cada mètrica: valor de l'equip, mitjana de la lliga, diferència i
    posició al rànquing (1 = el millor segons la direcció de la mètrica).
    """
    if taula.empty or equip not in set(taula["Equip"]):
        return pd.DataFrame()

    metriques = metriques_disponibles(taula)
    mitjana = mitjana_lliga(taula)
    fila = taula[taula["Equip"] == equip].iloc[0]

    registres = []
    for metrica in metriques:
        direccio = DIRECCIO.get(metrica, 0)
        # El rànquing només té sentit si la mètrica té direcció; per a les
        # neutrals (volum de tirs, possessions) es deixa buit a propòsit.
        if direccio:
            ordre = taula[metrica].rank(ascending=(direccio < 0), method="min")
            posicio = int(ordre[taula["Equip"] == equip].iloc[0])
        else:
            posicio = None

        registres.append({
            "Mètrica": metrica,
            "Equip": fila[metrica],
            "Mitjana lliga": mitjana[metrica],
            "Diferència": round(float(fila[metrica]) - float(mitjana[metrica]), 2),
            "Posició": posicio,
            "Direcció": direccio,
        })

    resultat = pd.DataFrame(registres)
    # Int64 nullable: les mètriques neutrals no tenen rànquing i han de quedar
    # buides, no convertir-se en NaN de coma flotant (que es mostraria "12.0").
    resultat["Posició"] = resultat["Posició"].astype("Int64")
    return resultat


def formata(metrica: str, valor: float) -> str:
    """Text del valor amb els decimals que toquen i el símbol de percentatge."""
    if pd.isna(valor):
        return "—"
    decimals = DECIMALS.get(metrica, DECIMALS_PERCENTATGE if "%" in metrica else DECIMALS_PER_DEFECTE)
    text = f"{valor:.{decimals}f}"
    return f"{text}%" if "%" in metrica else text


def resum_rebot(
    boxscore: pd.DataFrame,
    temporada: str,
    equip: str,
    jornades: list[int] | None = None,
) -> dict:
    """
    Rebot d'un equip segons l'acta, amb els percentatges de captura.

    **ORB%** és quants dels rebots ofensius DISPONIBLES s'agafen: els propis
    sobre els propis més els defensius que va agafar el rival, que són tots els
    rebots que hi va haver a l'atac propi. Un 30% vol dir que de cada deu tirs
    fallats se'n recupera tres.

    **DRB%** és el mateix a l'altra cistella. Per construcció, l'ORB% del rival
    és 100 − DRB% propi: tot rebot disponible se l'endú algú.

    Els percentatges surten dels totals acumulats de tots els partits, no de la
    mitjana dels percentatges de cada partit.
    """
    buit = {
        "partits": 0, "ro": 0, "rd": 0, "rt": 0,
        "ro_rival": 0, "rd_rival": 0,
        "orb": 0.0, "drb": 0.0, "orb_rival": 0.0, "drb_rival": 0.0,
        "ro_per_partit": 0.0, "rd_per_partit": 0.0,
    }
    if boxscore.empty:
        return buit

    per_partit = totals_per_partit(boxscore[boxscore["Temporada"] == temporada])
    if per_partit.empty:
        return buit

    files = per_partit[per_partit["Equip"] == equip]
    if jornades:
        files = files[files["Jornada"].isin(jornades)]
    if files.empty:
        return buit

    ro, rd = int(files["RO"].sum()), int(files["RD"].sum())
    ro_rival, rd_rival = int(files["RO rival"].sum()), int(files["RD rival"].sum())

    return {
        "partits": int(files["PartitID"].nunique()),
        "ro": ro,
        "rd": rd,
        "rt": ro + rd,
        "ro_rival": ro_rival,
        "rd_rival": rd_rival,
        "orb": float(_percentatge(ro, ro + rd_rival)),
        "drb": float(_percentatge(rd, rd + ro_rival)),
        "orb_rival": float(_percentatge(ro_rival, ro_rival + rd)),
        "drb_rival": float(_percentatge(rd_rival, rd_rival + ro)),
        "ro_per_partit": round(ro / files["PartitID"].nunique(), 1),
        "rd_per_partit": round(rd / files["PartitID"].nunique(), 1),
    }
