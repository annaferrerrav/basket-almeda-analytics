# -*- coding: utf-8 -*-
"""
Mètriques derivades del PBP manual.

Totes les funcions reben el DataFrame ja filtrat i el tornen agregat. No hi ha
estat compartit ni cache: recalcular sempre des de la taula base evita que un
filtre i un total deixin de quadrar.

Nota sobre el +/-: com que cada fila JA és l'increment de la possessió (`PF`,
`PC`) i no un marcador acumulat, el diferencial d'una fila és directament
PF - PC. No s'hi aplica cap `.diff()`.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from . import config as cfg
from .normalitza import DESENLLAC_CONVERTIT, DESENLLAC_PERDUA, DESENLLAC_TIR


def _divideix(numerador, denominador, per_cent: bool = False):
    """Divisió protegida: si el denominador és 0 retorna 0, no NaN ni infinit."""
    num = np.asarray(numerador, dtype="float64")
    den = np.asarray(denominador, dtype="float64")
    resultat = np.divide(num, den, out=np.zeros_like(num), where=den != 0)
    return np.round(resultat * 100, 1) if per_cent else np.round(resultat, 3)


def resum_sistemes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Una fila per sistema: quantes vegades s'ha jugat i què n'hem tret.

    "Punts/jugada" és PF / vegades jugat. Ull: una fila etiquetada "RO" és la
    continuació de la mateixa possessió després d'un rebot ofensiu, així que
    aquesta mètrica és per JUGADA, no per possessió tancada.
    """
    if df.empty:
        return pd.DataFrame(columns=["Tàctica", "Jugades", "Punts", "Punts/jugada", "% conversió", "Pèrdues", "% pèrdues"])

    treball = df[df[cfg.COL_TACTICA].notna()].copy()
    if treball.empty:
        return pd.DataFrame(columns=["Tàctica", "Jugades", "Punts", "Punts/jugada", "% conversió", "Pèrdues", "% pèrdues"])

    treball["_tir"] = treball[cfg.COL_DESENLLAC].isin(DESENLLAC_TIR)
    treball["_convertit"] = treball[cfg.COL_DESENLLAC].isin(DESENLLAC_CONVERTIT)
    treball["_perdua"] = treball[cfg.COL_DESENLLAC].isin(DESENLLAC_PERDUA)

    agrupat = treball.groupby(cfg.COL_TACTICA, dropna=True).agg(
        Jugades=(cfg.COL_PF, "size"),
        Punts=(cfg.COL_PF, "sum"),
        Tirs=("_tir", "sum"),
        Convertits=("_convertit", "sum"),
        Pèrdues=("_perdua", "sum"),
    ).reset_index()

    agrupat["Punts/jugada"] = _divideix(agrupat["Punts"], agrupat["Jugades"])
    agrupat["% conversió"] = _divideix(agrupat["Convertits"], agrupat["Tirs"], per_cent=True)
    agrupat["% pèrdues"] = _divideix(agrupat["Pèrdues"], agrupat["Jugades"], per_cent=True)

    columnes = ["Tàctica", "Jugades", "Punts", "Punts/jugada", "Tirs", "Convertits", "% conversió", "Pèrdues", "% pèrdues"]
    return agrupat[columnes].sort_values("Jugades", ascending=False, ignore_index=True)


def desenllacos_per_sistema(df: pd.DataFrame) -> pd.DataFrame:
    """Recompte de desenllaços per sistema (la base dels pie charts)."""
    if df.empty:
        return pd.DataFrame(columns=[cfg.COL_TACTICA, cfg.COL_DESENLLAC, "Jugades", "Punts"])

    treball = df[df[cfg.COL_TACTICA].notna() & df[cfg.COL_DESENLLAC].notna()]
    if treball.empty:
        return pd.DataFrame(columns=[cfg.COL_TACTICA, cfg.COL_DESENLLAC, "Jugades", "Punts"])

    return (
        treball.groupby([cfg.COL_TACTICA, cfg.COL_DESENLLAC], dropna=True)
        .agg(Jugades=(cfg.COL_PF, "size"), Punts=(cfg.COL_PF, "sum"))
        .reset_index()
    )


def punts_i_assistencies_per_sistema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per cada (sistema, jugadora): punts anotats i punts generats amb assistència.

    Són dues columnes diferents i NO se sumen: els mateixos punts poden comptar
    com a anotats per A i com a generats per B. Sumar-los els duplicaria.
    """
    buit = pd.DataFrame(columns=[cfg.COL_TACTICA, "Jugadora", "Punts anotats", "Punts assistits", "Assistències"])
    if df.empty:
        return buit

    treball = df[df[cfg.COL_TACTICA].notna()]
    if treball.empty:
        return buit

    anotats = (
        treball[treball[cfg.COL_FINALITZADORA].notna()]
        .groupby([cfg.COL_TACTICA, cfg.COL_FINALITZADORA])[cfg.COL_PF]
        .sum()
        .rename("Punts anotats")
    )
    anotats.index.names = [cfg.COL_TACTICA, "Jugadora"]

    amb_assist = treball[treball[cfg.COL_ASSIST].notna()]
    assistits = (
        amb_assist.groupby([cfg.COL_TACTICA, cfg.COL_ASSIST])[cfg.COL_PF]
        .sum()
        .rename("Punts assistits")
    )
    nombre_assist = (
        amb_assist.groupby([cfg.COL_TACTICA, cfg.COL_ASSIST])[cfg.COL_PF]
        .size()
        .rename("Assistències")
    )
    for serie in (assistits, nombre_assist):
        serie.index.names = [cfg.COL_TACTICA, "Jugadora"]

    resultat = (
        pd.concat([anotats, assistits, nombre_assist], axis=1)
        .fillna(0)
        .reset_index()
    )
    for col in ("Punts anotats", "Punts assistits", "Assistències"):
        resultat[col] = resultat[col].astype(int)

    return resultat.sort_values([cfg.COL_TACTICA, "Punts anotats"], ascending=[True, False], ignore_index=True)


def plus_minus_individual(df: pd.DataFrame) -> pd.DataFrame:
    """+/- per jugadora, comptant cada jugada on era en pista."""
    buit = pd.DataFrame(columns=["Jugadora", "+/-", "Jugades", "+/- per 100 jugades", "PF", "PC"])
    if df.empty:
        return buit

    treball = df.copy()
    treball["_delta"] = treball[cfg.COL_PF] - treball[cfg.COL_PC]

    # Format llarg: una fila per (jugada, jugadora en pista).
    llarg = treball.melt(
        id_vars=["_delta", cfg.COL_PF, cfg.COL_PC],
        value_vars=cfg.COLS_QUINTET,
        var_name="Posició",
        value_name="Jugadora",
    ).dropna(subset=["Jugadora"])

    if llarg.empty:
        return buit

    resultat = llarg.groupby("Jugadora").agg(
        **{
            "+/-": ("_delta", "sum"),
            "Jugades": ("_delta", "size"),
            "PF": (cfg.COL_PF, "sum"),
            "PC": (cfg.COL_PC, "sum"),
        }
    ).reset_index()

    resultat["+/- per 100 jugades"] = np.round(_divideix(resultat["+/-"], resultat["Jugades"]) * 100, 1)
    return resultat.sort_values("+/-", ascending=False, ignore_index=True)


def plus_minus_per_posicio(df: pd.DataFrame, min_jugades: int = 10) -> pd.DataFrame:
    """
    +/- desglossat per jugadora I posició ocupada (jug 1..jug 5).

    Una mateixa jugadora pot jugar de 2 i de 3 segons el quintet; això separa
    els dos casos. Ull amb la interpretació: un +/- dolent "de 4" no vol dir que
    hi jugui pitjor, pot voler dir que quan hi juga és perquè falta la pivot
    titular. És descriptiu, no causal.
    """
    buit = pd.DataFrame(columns=["Jugadora", "Posició", "Etiqueta", "+/-", "Jugades", "+/- per 100 jugades"])
    if df.empty:
        return buit

    treball = df.copy()
    treball["_delta"] = treball[cfg.COL_PF] - treball[cfg.COL_PC]

    llarg = treball.melt(
        id_vars=["_delta", cfg.COL_PF, cfg.COL_PC],
        value_vars=cfg.COLS_QUINTET,
        var_name="Posició",
        value_name="Jugadora",
    ).dropna(subset=["Jugadora"])

    if llarg.empty:
        return buit

    resultat = llarg.groupby(["Jugadora", "Posició"]).agg(
        **{"+/-": ("_delta", "sum"), "Jugades": ("_delta", "size")}
    ).reset_index()

    resultat = resultat[resultat["Jugades"] >= min_jugades]
    if resultat.empty:
        return buit

    resultat["Etiqueta"] = resultat["Jugadora"] + " · " + resultat["Posició"].map(cfg.POSICIONS).fillna(resultat["Posició"])
    resultat["+/- per 100 jugades"] = np.round(_divideix(resultat["+/-"], resultat["Jugades"]) * 100, 1)
    resultat["+/-"] = resultat["+/-"].astype(int)

    return resultat.sort_values("+/-", ascending=False, ignore_index=True)[
        ["Jugadora", "Posició", "Etiqueta", "+/-", "Jugades", "+/- per 100 jugades"]
    ]


def plus_minus_parelles(df: pd.DataFrame, min_jugades: int = 10) -> pd.DataFrame:
    """
    +/- per parella de jugadores.

    Es generen les 10 parelles possibles del quintet de cada jugada (C(5,2)).
    `min_jugades` filtra les parelles amb massa poca mostra: amb 3 o 4 jugades
    juntes, un +/- de +8 no vol dir res.
    """
    buit = pd.DataFrame(columns=["Parella", "Jugadora A", "Jugadora B", "+/-", "Jugades", "+/- per 100 jugades"])
    if df.empty:
        return buit

    acumulat: dict[tuple[str, str], list[float]] = {}
    quintets = df[cfg.COLS_QUINTET].to_numpy()
    deltes = (df[cfg.COL_PF] - df[cfg.COL_PC]).to_numpy(dtype="float64")

    for quintet, delta in zip(quintets, deltes):
        jugadores = sorted({j for j in quintet if isinstance(j, str) and j})
        for parella in combinations(jugadores, 2):
            registre = acumulat.setdefault(parella, [0.0, 0])
            registre[0] += delta
            registre[1] += 1

    if not acumulat:
        return buit

    resultat = pd.DataFrame(
        [
            {"Jugadora A": a, "Jugadora B": b, "Parella": f"{a} · {b}", "+/-": suma, "Jugades": n}
            for (a, b), (suma, n) in acumulat.items()
        ]
    )
    resultat = resultat[resultat["Jugades"] >= min_jugades]
    if resultat.empty:
        return buit

    resultat["+/-"] = resultat["+/-"].astype(int)
    resultat["+/- per 100 jugades"] = np.round(_divideix(resultat["+/-"], resultat["Jugades"]) * 100, 1)
    return resultat.sort_values("+/-", ascending=False, ignore_index=True)[
        ["Parella", "Jugadora A", "Jugadora B", "+/-", "Jugades", "+/- per 100 jugades"]
    ]


def plus_minus_parelles_posicio(df: pd.DataFrame, min_jugades: int = 10) -> pd.DataFrame:
    """
    +/- per parella de POSICIONS (jug 1 amb jug 4, jug 2 amb jug 5...).

    És diferent de `plus_minus_parelles`: allà la parella són dos noms, juguin
    on juguin. Aquí interessa com casa cada exterior amb cada interior, així que
    la mateixa parella de noms pot sortir dues vegades si han jugat en
    combinacions de posicions diferents.
    """
    buit = pd.DataFrame(
        columns=["Parella posicions", "Jugadores", "Jugadora A", "Jugadora B", "+/-", "Jugades", "+/- per 100 jugades"]
    )
    if df.empty:
        return buit

    delta = (df[cfg.COL_PF] - df[cfg.COL_PC]).to_numpy(dtype="float64")
    registres = []

    for col_a, col_b in cfg.PARELLES_POSICIO:
        if col_a not in df.columns or col_b not in df.columns:
            continue
        valida = df[col_a].notna() & df[col_b].notna()
        parcial = pd.DataFrame(
            {
                "Parella posicions": f"{col_a} · {col_b}",
                "Jugadora A": df.loc[valida, col_a].to_numpy(),
                "Jugadora B": df.loc[valida, col_b].to_numpy(),
                "_delta": delta[valida.to_numpy()],
            }
        )
        registres.append(parcial)

    if not registres:
        return buit

    llarg = pd.concat(registres, ignore_index=True)
    resultat = llarg.groupby(["Parella posicions", "Jugadora A", "Jugadora B"]).agg(
        **{"+/-": ("_delta", "sum"), "Jugades": ("_delta", "size")}
    ).reset_index()

    resultat = resultat[resultat["Jugades"] >= min_jugades]
    if resultat.empty:
        return buit

    resultat["Jugadores"] = resultat["Jugadora A"] + " · " + resultat["Jugadora B"]
    resultat["+/- per 100 jugades"] = np.round(_divideix(resultat["+/-"], resultat["Jugades"]) * 100, 1)
    resultat["+/-"] = resultat["+/-"].astype(int)

    return resultat.sort_values(["Parella posicions", "+/-"], ascending=[True, False], ignore_index=True)[
        ["Parella posicions", "Jugadores", "Jugadora A", "Jugadora B", "+/-", "Jugades", "+/- per 100 jugades"]
    ]


def resum_rebot_ofensiu(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rebot ofensiu i punts de segona oportunitat, per període.

    Les columnes de rebot no existeixen a les jornades 1-3 del 25-26; si no hi
    són, es retorna buit i la pàgina ho diu, en comptes d'inventar zeros.
    """
    # Només les columnes que algú ha omplert de debò: a 25-26 "RD a favor" i
    # "RD en contra" tenen 1 i 2 valors en tota la temporada, i pintar-les com a
    # zeros donaria la impressió falsa que no hi ha hagut rebots defensius.
    disponibles = [c for c in cfg.COLS_REBOT if c in df.columns and df[c].notna().any()]
    if df.empty or not disponibles:
        return pd.DataFrame()

    agrupat = df.groupby(cfg.COL_PERIODE)[disponibles].sum().reset_index()
    agrupat[cfg.COL_PERIODE] = agrupat[cfg.COL_PERIODE].astype(str)

    total = agrupat[disponibles].sum().to_frame().T
    total[cfg.COL_PERIODE] = "Total"
    return pd.concat([agrupat, total], ignore_index=True)[[cfg.COL_PERIODE, *disponibles]]


def sistemes_per_posicio(df: pd.DataFrame, posicio: str = "jug 1") -> pd.DataFrame:
    """Quins sistemes es juguen amb cada jugadora ocupant una posició concreta."""
    if df.empty or posicio not in df.columns:
        return pd.DataFrame(columns=["Jugadora", cfg.COL_TACTICA, "Jugades", "Punts", "Punts/jugada"])

    treball = df[df[posicio].notna() & df[cfg.COL_TACTICA].notna()]
    if treball.empty:
        return pd.DataFrame(columns=["Jugadora", cfg.COL_TACTICA, "Jugades", "Punts", "Punts/jugada"])

    agrupat = (
        treball.groupby([posicio, cfg.COL_TACTICA])
        .agg(Jugades=(cfg.COL_PF, "size"), Punts=(cfg.COL_PF, "sum"))
        .reset_index()
        .rename(columns={posicio: "Jugadora"})
    )
    agrupat["Punts/jugada"] = _divideix(agrupat["Punts"], agrupat["Jugades"])
    return agrupat.sort_values(["Jugadora", "Jugades"], ascending=[True, False], ignore_index=True)


def resum_general(df: pd.DataFrame) -> dict:
    """Xifres de capçalera per a la pàgina d'inici."""
    if df.empty:
        return {"jugades": 0, "jornades": 0, "punts": 0, "punts_rival": 0, "ppp": 0.0, "ppp_rival": 0.0}

    jugades = len(df)
    punts = int(df[cfg.COL_PF].sum())
    punts_rival = int(df[cfg.COL_PC].sum())
    return {
        "jugades": jugades,
        "jornades": int(df[cfg.COL_JORNADA].nunique()),
        "punts": punts,
        "punts_rival": punts_rival,
        "ppp": float(_divideix(punts, jugades)),
        "ppp_rival": float(_divideix(punts_rival, jugades)),
    }


def plantilla(df: pd.DataFrame) -> pd.DataFrame:
    """
    Una fila per jugadora amb les xifres de capçalera: la llista de la pàgina
    de Jugadores.

    El +/- i les jugades venen d'estar en pista; els punts anotats/assistits,
    de ser-ne la protagonista. Són preguntes diferents i per això conviuen a la
    mateixa fila sense sumar-se mai (vegeu `punts_i_assistencies_per_sistema`).

    Es fa un merge extern a propòsit: una jugadora pot tenir punts anotats i cap
    jugada en pista si el fitxer d'aquella jornada té el quintet marcat com a no
    fiable (`carrega._comprova_quintet` l'anul·la sencer), i deixar-la fora de
    la plantilla per això seria amagar-la.
    """
    columnes = [
        "Jugadora", "Jugades", "Punts anotats", "Assistències",
        "Punts assistits", "PF", "PC", "+/-", "+/- per 100 jugades",
    ]
    if df.empty:
        return pd.DataFrame(columns=columnes)

    pista = plus_minus_individual(df)
    protagonisme = (
        punts_i_assistencies_per_sistema(df)
        .groupby("Jugadora")[["Punts anotats", "Punts assistits", "Assistències"]]
        .sum()
        .reset_index()
    )

    if pista.empty and protagonisme.empty:
        return pd.DataFrame(columns=columnes)

    resultat = pista.merge(protagonisme, on="Jugadora", how="outer")
    for col in columnes[1:]:
        if col not in resultat.columns:
            resultat[col] = 0
    resultat[columnes[1:]] = resultat[columnes[1:]].fillna(0)
    for col in ("Jugades", "Punts anotats", "Assistències", "Punts assistits", "PF", "PC", "+/-"):
        resultat[col] = resultat[col].astype(int)

    return resultat[columnes].sort_values(
        ["Punts anotats", "Jugades"], ascending=False, ignore_index=True
    )


def jugades_en_pista(df: pd.DataFrame, jugadora: str) -> pd.DataFrame:
    """Files on la jugadora era una de les cinc en pista."""
    if df.empty:
        return df
    return df[df[cfg.COLS_QUINTET].eq(jugadora).any(axis=1)].copy()


def desenllacos_jugadora(df: pd.DataFrame, jugadora: str) -> pd.DataFrame:
    """Com acaben les jugades que finalitza ella: comptatge i punts per desenllaç."""
    columnes = ["Desenllac", "Jugades", "Punts"]
    if df.empty:
        return pd.DataFrame(columns=columnes)

    seves = df[df[cfg.COL_FINALITZADORA] == jugadora]
    seves = seves[seves[cfg.COL_DESENLLAC].notna()]
    if seves.empty:
        return pd.DataFrame(columns=columnes)

    return (
        seves.groupby(cfg.COL_DESENLLAC)
        .agg(Jugades=(cfg.COL_PF, "size"), Punts=(cfg.COL_PF, "sum"))
        .reset_index()
        .rename(columns={cfg.COL_DESENLLAC: "Desenllac"})
        .sort_values("Jugades", ascending=False, ignore_index=True)
    )


def fitxa_jugadora(df: pd.DataFrame, jugadora: str) -> dict:
    """
    Tot el que se sap d'una jugadora a partir del PBP, en un sol diccionari.

    `en_pista` és el subconjunt de jugades amb ella a la pista: tot el que en
    penja (sistemes, evolució per jornada) mesura com va l'EQUIP amb ella, no
    què fa ella. El que sí que és seu — desenllaços i punts anotats/assistits —
    es calcula sobre les jugades on és finalitzadora o assistent.
    """
    en_pista = jugades_en_pista(df, jugadora)

    plantilla_completa = plantilla(df)
    fila = plantilla_completa[plantilla_completa["Jugadora"] == jugadora]
    totals = fila.iloc[0].to_dict() if not fila.empty else dict.fromkeys(plantilla_completa.columns, 0)

    posicions = plus_minus_per_posicio(df, min_jugades=1)
    posicions = posicions[posicions["Jugadora"] == jugadora].drop(columns=["Jugadora", "Etiqueta"])
    if not posicions.empty:
        posicions = posicions.assign(Posició=posicions["Posició"].map(cfg.POSICIONS).fillna(posicions["Posició"]))

    per_sistema = punts_i_assistencies_per_sistema(df)
    per_sistema = per_sistema[per_sistema["Jugadora"] == jugadora].drop(columns=["Jugadora"])

    if en_pista.empty:
        per_jornada = pd.DataFrame(columns=[cfg.COL_JORNADA, "Rival", "Jugades", "PF", "PC", "+/-"])
    else:
        per_jornada = (
            en_pista.groupby(cfg.COL_JORNADA)
            .agg(
                Rival=(cfg.COL_RIVAL, "first"),
                Jugades=(cfg.COL_PF, "size"),
                PF=(cfg.COL_PF, "sum"),
                PC=(cfg.COL_PC, "sum"),
            )
            .reset_index()
        )
        per_jornada["+/-"] = per_jornada["PF"] - per_jornada["PC"]

    return {
        "totals": totals,
        "en_pista": en_pista,
        "sistemes_en_pista": resum_sistemes(en_pista),
        "protagonisme_per_sistema": per_sistema,
        "desenllacos": desenllacos_jugadora(df, jugadora),
        "posicions": posicions,
        "per_jornada": per_jornada,
    }


# --- Rebot -----------------------------------------------------------------
# Punts que es podrien treure de cada rebot ofensiu si TOTS acabessin en
# cistella. Es fixa a 2 perquè és el que val la continuació típica d'un rebot
# ofensiu (safata o tir de 2); un T3C en valdria 3 i un tir lliure 1, però
# prendre 2 com a sostre de referència no infla la línia amb triples que gairebé
# no es tiren després de rebot.
PUNTS_PER_RO = 2


def potencial_ro(taula: pd.DataFrame) -> pd.DataFrame:
    """
    Afegeix els punts POTENCIALS a una taula de rebot: els que es traurien si
    cada rebot ofensiu acabés en cistella de dos.

    És un sostre de referència, no una predicció: serveix per veure la distància
    entre el que es rebota i el que se n'acaba treient.
    """
    resultat = taula.copy()
    for rebots, punts in (("RO a favor", "Potencial RO a favor"), ("RO en contra", "Potencial RO rival")):
        if rebots in resultat.columns:
            resultat[punts] = resultat[rebots] * PUNTS_PER_RO
    return resultat


def eficiencia_ro(df: pd.DataFrame) -> dict:
    """
    Què traiem dels rebots ofensius, comparat amb el sostre teòric.

    `aprofitament` és punts reals / punts potencials en tant per cent. Un 50%
    vol dir que de cada dos rebots ofensius se'n converteix un en cistella de
    dos (o l'equivalent en tirs lliures i triples).
    """
    buit = {
        "ro": 0, "punts": 0, "potencial": 0, "aprofitament": 0.0, "punts_per_ro": 0.0,
        "ro_rival": 0, "punts_rival": 0, "potencial_rival": 0, "aprofitament_rival": 0.0,
        "punts_per_ro_rival": 0.0,
    }
    if df.empty:
        return buit

    def _suma(columna):
        return int(df[columna].sum()) if columna in df.columns else 0

    ro, punts = _suma("RO a favor"), _suma("Punts RO a favor")
    ro_rival, punts_rival = _suma("RO en contra"), _suma("Punts RO rival")
    potencial, potencial_rival = ro * PUNTS_PER_RO, ro_rival * PUNTS_PER_RO

    return {
        "ro": ro,
        "punts": punts,
        "potencial": potencial,
        "aprofitament": float(_divideix(punts, potencial, per_cent=True)),
        "punts_per_ro": float(_divideix(punts, ro)),
        "ro_rival": ro_rival,
        "punts_rival": punts_rival,
        "potencial_rival": potencial_rival,
        "aprofitament_rival": float(_divideix(punts_rival, potencial_rival, per_cent=True)),
        "punts_per_ro_rival": float(_divideix(punts_rival, ro_rival)),
    }


def rebots_per_jugadora_en_pista(df: pd.DataFrame, columna: str = "RO en contra") -> pd.DataFrame:
    """
    Rebots comptats a cada jugadora que era en pista quan van passar.

    NO és «rebots que agafa ella»: el PBP anota el rebot a la possessió, no a la
    jugadora. Per als rebots que agafa cadascuna, la font és l'acta oficial
    (`jugadores.plantilla_oficial`). Això mesura una altra cosa: quant se'n
    concedeix (o se'n treu) amb ella a la pista.

    Es dona també per 100 jugades perquè una jugadora amb el doble de minuts no
    surti automàticament com la pitjor.
    """
    columnes = ["Jugadora", columna, "Jugades", f"{columna} per 100 jugades"]
    if df.empty or columna not in df.columns:
        return pd.DataFrame(columns=columnes)

    treball = df[df[columna].notna()].copy()
    if treball.empty:
        return pd.DataFrame(columns=columnes)

    llarg = treball.melt(
        id_vars=[columna],
        value_vars=cfg.COLS_QUINTET,
        var_name="Posició",
        value_name="Jugadora",
    ).dropna(subset=["Jugadora"])

    if llarg.empty:
        return pd.DataFrame(columns=columnes)

    resultat = llarg.groupby("Jugadora").agg(
        **{columna: (columna, "sum"), "Jugades": (columna, "size")}
    ).reset_index()
    resultat[columna] = resultat[columna].astype(int)
    resultat[f"{columna} per 100 jugades"] = np.round(
        _divideix(resultat[columna], resultat["Jugades"]) * 100, 1
    )
    return resultat[columnes].sort_values(columna, ascending=False, ignore_index=True)


def despres_de_rebot(df: pd.DataFrame, tactica: str = "RO") -> pd.DataFrame:
    """
    Com acaben les jugades que continuen una possessió després d'un rebot
    ofensiu (les files amb `Tàctica == "RO"`), i què val cadascuna.

    Es compara contra la resta de jugades a la pàgina, no aquí: aquesta funció
    només reparteix els desenllaços.
    """
    columnes = ["Desenllac", "Jugades", "Punts", "% de les jugades"]
    if df.empty:
        return pd.DataFrame(columns=columnes)

    files = df[(df[cfg.COL_TACTICA] == tactica) & df[cfg.COL_DESENLLAC].notna()]
    if files.empty:
        return pd.DataFrame(columns=columnes)

    resultat = (
        files.groupby(cfg.COL_DESENLLAC)
        .agg(Jugades=(cfg.COL_PF, "size"), Punts=(cfg.COL_PF, "sum"))
        .reset_index()
        .rename(columns={cfg.COL_DESENLLAC: "Desenllac"})
    )
    resultat["% de les jugades"] = _divideix(resultat["Jugades"], len(files), per_cent=True)
    return resultat.sort_values("Jugades", ascending=False, ignore_index=True)
