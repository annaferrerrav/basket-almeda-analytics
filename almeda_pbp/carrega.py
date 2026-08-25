# -*- coding: utf-8 -*-
"""
Descoberta i càrrega dels fitxers PBP manuals.

Cada fila d'aquests Excel és UNA POSSESSIÓ NOSTRA: quin quintet hi havia (amb la
posició, per això `jug 1`..`jug 5` no s'ordenen mai), quin sistema es va jugar,
com va acabar la possessió i quants punts va donar (`PF`). `PC` són els punts que
el rival va fer immediatament després d'aquella possessió.

L'ORDRE DE LES FILES DEL FITXER ÉS L'ORDRE CRONOLÒGIC. No s'ordena per
(Periode, Minut) perquè `Minut` és el minut RESTANT del període i, per tant,
decreix: ordenar-lo ascendentment invertiria cada període.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import config as cfg
from .normalitza import (
    ALIES_DESENLLAC,
    ALIES_TACTICA,
    normalitza_jugadora,
    normalitza_serie,
)


@dataclass
class Incidencia:
    """Un problema detectat en carregar les dades, per mostrar a l'app."""

    temporada: str
    jornada: int | None
    tipus: str
    detall: str


@dataclass
class ResultatCarrega:
    dades: pd.DataFrame
    incidencies: list[Incidencia] = field(default_factory=list)

    @property
    def taula_incidencies(self) -> pd.DataFrame:
        if not self.incidencies:
            return pd.DataFrame(columns=["Temporada", "Jornada", "Tipus", "Detall"])
        taula = pd.DataFrame(
            [
                {"Temporada": i.temporada, "Jornada": i.jornada, "Tipus": i.tipus, "Detall": i.detall}
                for i in self.incidencies
            ]
        )
        # Int64 (nullable) perquè les incidències de temporada sencera no tenen
        # jornada i no surtin com a "1.0" a la taula.
        taula["Jornada"] = taula["Jornada"].astype("Int64")
        return taula.sort_values(["Temporada", "Jornada", "Tipus"], na_position="last", ignore_index=True)


def descobreix_fitxers(arrel: Path | None = None) -> list[tuple[str, int, Path]]:
    """
    Busca tots els PBP disponibles.

    Retorna una llista de (temporada, jornada, ruta) ordenada. La temporada surt
    del nom de la carpeta ("25-26") i la jornada del nom del fitxer ("j22-...").
    Els fitxers sense número de jornada al nom s'ignoren.
    """
    arrel = arrel or cfg.ARREL
    trobats: list[tuple[str, int, Path]] = []
    for carpeta in sorted(arrel.glob(cfg.PATRO_TEMPORADES)):
        temporada = carpeta.parents[1].name
        for fitxer in carpeta.glob("*.xlsx"):
            if fitxer.name.startswith("~$"):  # fitxers temporals d'Excel oberts
                continue
            match = re.search(r"j(\d+)", fitxer.name, flags=re.IGNORECASE)
            if match:
                trobats.append((temporada, int(match.group(1)), fitxer))
    return sorted(trobats, key=lambda t: (t[0], t[1]))


def _llegeix_un(temporada: str, jornada: int, ruta: Path, incidencies: list[Incidencia]) -> pd.DataFrame | None:
    """Llegeix i normalitza un únic fitxer. Retorna None si no és utilitzable."""
    try:
        df = pd.read_excel(ruta)
    except Exception as err:  # fitxer corrupte, format inesperat...
        incidencies.append(Incidencia(temporada, jornada, "No s'ha pogut llegir", f"{ruta.name}: {err}"))
        return None

    # Fora columnes fantasma d'Excel ("Unnamed: 27" i companyia).
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]

    falten = [c for c in cfg.COLS_OBLIGATORIES if c not in df.columns]
    if falten:
        incidencies.append(
            Incidencia(temporada, jornada, "Falten columnes obligatòries", f"{ruta.name}: {', '.join(falten)}")
        )
        return None

    # Un fitxer sense NI tàctica NI desenllaç és una plantilla buida (només
    # quintets i minuts): no hi ha cap jugada real anotada i esbiaixaria el
    # +/- amb zeros. Es descarta.
    #
    # En canvi, un fitxer amb desenllaç però sense tàctica (el cas dels PBP
    # generats automàticament a partir del feed de la FEB: tenen quintet,
    # desenllaç i punts, però el sistema de joc no surt del feed i encara no
    # s'ha etiquetat a mà) SÍ es carrega. Les funcions que agreguen per
    # sistema (`resum_sistemes`, `punts_i_assistencies_per_sistema`...) ja
    # filtren `Tàctica.notna()`, així que aquestes jornades simplement no hi
    # aporten res — però sí compten per a tota la resta (+/-, RO, boxscore
    # de jugades, resum general).
    if df[cfg.COL_TACTICA].isna().all() and df[cfg.COL_DESENLLAC].isna().all():
        incidencies.append(
            Incidencia(
                temporada,
                jornada,
                "Jornada descartada",
                f"{ruta.name}: {len(df)} files però cap tàctica ni desenllaç anotat (plantilla buida).",
            )
        )
        return None

    if df[cfg.COL_TACTICA].isna().all():
        incidencies.append(
            Incidencia(
                temporada,
                jornada,
                "Sense sistemes",
                f"{ruta.name}: {len(df)} jugades carregades però sense cap tàctica anotada "
                "(font automàtica). No apareix a les pàgines de sistemes; sí a la resta.",
            )
        )

    _comprova_quintet(df, temporada, jornada, ruta, incidencies)

    df[cfg.COL_ORDRE] = range(len(df))
    df[cfg.COL_TEMPORADA] = temporada
    df[cfg.COL_FITXER] = ruta.name

    # La jornada del nom del fitxer mana; si la columna no hi coincideix, s'avisa.
    if cfg.COL_JORNADA in df.columns:
        de_columna = pd.to_numeric(df[cfg.COL_JORNADA], errors="coerce").dropna().unique()
        if len(de_columna) and set(de_columna.astype(int)) != {jornada}:
            incidencies.append(
                Incidencia(
                    temporada,
                    jornada,
                    "Jornada incoherent",
                    f"{ruta.name}: la columna Jornada diu {sorted(de_columna.astype(int))}, "
                    f"el nom del fitxer diu {jornada}. Es fa servir la del nom.",
                )
            )
    df[cfg.COL_JORNADA] = jornada

    # Normalització de valors categòrics.
    df[cfg.COL_TACTICA], desc_tac = normalitza_serie(df[cfg.COL_TACTICA], ALIES_TACTICA)
    df[cfg.COL_DESENLLAC], desc_des = normalitza_serie(df[cfg.COL_DESENLLAC], ALIES_DESENLLAC)

    for valor in sorted(set(df.loc[desc_tac, cfg.COL_TACTICA].dropna())):
        incidencies.append(Incidencia(temporada, jornada, "Tàctica no reconeguda", f"«{valor}»"))
    for valor in sorted(set(df.loc[desc_des, cfg.COL_DESENLLAC].dropna())):
        incidencies.append(Incidencia(temporada, jornada, "Desenllaç no reconegut", f"«{valor}»"))

    for col in [*cfg.COLS_QUINTET, cfg.COL_FINALITZADORA, cfg.COL_ASSIST]:
        if col in df.columns:
            df[col] = normalitza_jugadora(df[col])

    # Numèrics: el que no es pugui convertir passa a 0 punts, no a NaN, perquè
    # una possessió sense anotació de punts és una possessió de 0 punts.
    for col in (cfg.COL_PF, cfg.COL_PC):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in (cfg.COL_PERIODE, cfg.COL_MINUT):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Columnes de rebot: es passen a numèric, però un valor com "3?" (dubte de
    # l'anotador) no es converteix en silenci a res — es reporta.
    for col in cfg.COLS_REBOT:
        if col not in df.columns:
            continue
        convertit = pd.to_numeric(df[col], errors="coerce")
        perduts = df[col].notna() & convertit.isna()
        for valor in sorted(set(df.loc[perduts, col].astype(str))):
            incidencies.append(
                Incidencia(temporada, jornada, "Valor no numèric", f"{ruta.name}: «{valor}» a la columna «{col}»")
            )
        df[col] = convertit

    # Control de coherència: la suma de PF ha de quadrar amb el marcador final.
    _comprova_marcador(df, temporada, jornada, ruta, incidencies)

    if cfg.COL_DATA in df.columns:
        df[cfg.COL_DATA] = pd.to_datetime(df[cfg.COL_DATA], errors="coerce")

    return df


def _comprova_quintet(df, temporada, jornada, ruta, incidencies) -> None:
    """
    Detecta quintets que no s'han extret bé (típic dels PBP automàtics).

    Un partit real de 4 períodes sempre té substitucions: si una posició és
    sempre la mateixa jugadora a totes les jugades (o sempre buida), la
    substitució no s'ha capturat i el quintet d'aquell fitxer no és fiable.
    Deixar-ho passar contaminaria el +/- real de la jugadora que hi surt
    fixa amb jugades on potser no era ni en pista. Es descarten NOMÉS les
    columnes de quintet d'aquest fitxer (Desenllaç/PF/PC/Finalitzadora es
    mantenen: la puntuació i qui anota segueixen sent vàlides).
    """
    if len(df) < 20:  # mostra massa petita per distingir "sort" de "error"
        return

    trencat = any(
        df[col].isna().all() or df[col].dropna().nunique() <= 1 for col in cfg.COLS_QUINTET if col in df.columns
    )
    if not trencat:
        return

    detall = ", ".join(
        f"{col}: {df[col].dropna().nunique()} jugadora(es) diferent(s)" for col in cfg.COLS_QUINTET if col in df.columns
    )
    incidencies.append(
        Incidencia(
            temporada,
            jornada,
            "Quintet no fiable",
            f"{ruta.name}: cap substitució detectada en {len(df)} jugades ({detall}). "
            "Es descarta el quintet d'aquest fitxer (+/-, parelles, jugadora×posició no "
            "l'inclouen); es manté la resta (punts, desenllaços, finalitzadora/assist).",
        )
    )
    for col in cfg.COLS_QUINTET:
        if col in df.columns:
            # None, no pd.NA: normalitza_jugadora() només reconeix com a buit
            # None o NaN de coma flotant (`_clau` a normalitza.py); pd.NA es
            # convertiria en el text literal "<NA>" i no es filtraria enlloc.
            df[col] = None


def _comprova_marcador(df, temporada, jornada, ruta, incidencies) -> None:
    """Compara sum(PF)/sum(PC) amb el marcador acumulat anotat al fitxer."""
    for col_punts, col_marcador, etiqueta in (
        (cfg.COL_PF, "Marcador equip", "propi"),
        (cfg.COL_PC, "Marcador rival", "rival"),
    ):
        if col_marcador not in df.columns:
            continue
        final = pd.to_numeric(df[col_marcador], errors="coerce").max()
        suma = df[col_punts].sum()
        if pd.notna(final) and int(final) != int(suma):
            incidencies.append(
                Incidencia(
                    temporada,
                    jornada,
                    "Marcador descuadrat",
                    f"{ruta.name}: sum({col_punts})={int(suma)} però {col_marcador} final={int(final)} "
                    f"(marcador {etiqueta}). Diferència de {int(suma) - int(final)} punts.",
                )
            )


def carrega_pbp(arrel: Path | None = None) -> ResultatCarrega:
    """Carrega tots els PBP disponibles en un únic DataFrame normalitzat."""
    incidencies: list[Incidencia] = []
    trossos = []

    fitxers = descobreix_fitxers(arrel)
    if not fitxers:
        return ResultatCarrega(pd.DataFrame(), incidencies)

    # Si hi ha dos fitxers per a la mateixa jornada (p. ex. "j10-pbp.xlsx" i
    # "j10-pbp_bo.xlsx") es carregarien duplicats: es queda el més recent.
    per_jornada: dict[tuple[str, int], Path] = {}
    for temporada, jornada, ruta in fitxers:
        clau = (temporada, jornada)
        if clau in per_jornada:
            anterior = per_jornada[clau]
            escollit, descartat = (
                (ruta, anterior) if ruta.stat().st_mtime > anterior.stat().st_mtime else (anterior, ruta)
            )
            per_jornada[clau] = escollit
            incidencies.append(
                Incidencia(
                    temporada, jornada, "Fitxer duplicat",
                    f"S'ha trobat més d'un fitxer per a la jornada {jornada}. "
                    f"S'usa «{escollit.name}» (més recent) i s'ignora «{descartat.name}».",
                )
            )
        else:
            per_jornada[clau] = ruta

    for (temporada, jornada), ruta in sorted(per_jornada.items()):
        df = _llegeix_un(temporada, jornada, ruta, incidencies)
        if df is not None:
            trossos.append(df)

    if not trossos:
        return ResultatCarrega(pd.DataFrame(), incidencies)

    dades = pd.concat(trossos, ignore_index=True)

    # Jornades que falten dins del rang carregat, per temporada.
    for temporada, grup in dades.groupby(cfg.COL_TEMPORADA):
        presents = set(grup[cfg.COL_JORNADA].unique())
        buides = sorted(set(range(1, max(presents) + 1)) - presents)
        if buides:
            incidencies.append(
                Incidencia(
                    temporada, None, "Jornades sense PBP",
                    f"No hi ha dades de les jornades {', '.join(map(str, buides))}.",
                )
            )

    return ResultatCarrega(dades, incidencies)


def jugadores_disponibles(df: pd.DataFrame) -> list[str]:
    """Totes les jugadores que apareixen en pista, ordenades alfabèticament."""
    if df.empty:
        return []
    noms = pd.unique(df[cfg.COLS_QUINTET].values.ravel())
    return sorted(n for n in noms if isinstance(n, str) and n)


def filtra(
    df: pd.DataFrame,
    jornades: list[int] | None = None,
    jugadores: list[str] | None = None,
    tactiques: list[str] | None = None,
    periodes: list[int] | None = None,
    mode_jugadora: str = "a pista",
) -> pd.DataFrame:
    """
    Filtra possessions.

    `mode_jugadora` decideix què vol dir filtrar per jugadora:
      - "a pista": possessions on la jugadora era una de les cinc en pista.
      - "protagonista": possessions on va finalitzar o donar l'assistència.
    Són preguntes diferents ("com va l'equip amb ella a pista" vs "què fa ella"),
    per això no es barregen.
    """
    resultat = df
    if jornades:
        resultat = resultat[resultat[cfg.COL_JORNADA].isin(jornades)]
    if periodes:
        resultat = resultat[resultat[cfg.COL_PERIODE].isin(periodes)]
    if tactiques:
        resultat = resultat[resultat[cfg.COL_TACTICA].isin(tactiques)]
    if jugadores:
        if mode_jugadora == "protagonista":
            cols = [cfg.COL_FINALITZADORA, cfg.COL_ASSIST]
        else:
            cols = cfg.COLS_QUINTET
        mascara = resultat[cols].isin(jugadores).any(axis=1)
        resultat = resultat[mascara]
    return resultat.copy()
