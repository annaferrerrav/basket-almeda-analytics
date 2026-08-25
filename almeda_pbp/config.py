# -*- coding: utf-8 -*-
"""
Configuració global: rutes, noms de columnes i paleta de colors.

Els noms de columna es mantenen EXACTAMENT com surten dels Excel de l'analista
(`Tàctica`, `Desenllac`, `jug 1`...). No es tradueixen ni es passen a snake_case
a propòsit: així els fitxers font i el codi parlen el mateix idioma.
"""

from __future__ import annotations

from pathlib import Path

# Arrel del projecte (la carpeta que conté aquest paquet).
ARREL = Path(__file__).resolve().parent.parent

# Les dades viuen a <arrel>/<temporada>/data/pbp/*.xlsx, p. ex. "25-26/data/pbp".
# Afegir una temporada nova és crear la carpeta: no cal tocar codi.
PATRO_TEMPORADES = "*/data/pbp"

# Temporades que l'app coneix, en ordre. S'hi afegeix una entrada quan comença
# una temporada nova — és l'única llista que cal tocar per fer-ho.
#
# El PBP manual identifica la temporada pel nom de carpeta ("25-26"); el
# boxscore scrapejat de la FEB la identifica amb l'any complet ("2025-26",
# perquè així ho dona `python -m almeda_pbp.feb --temporada 2025`). Són dues
# fonts amb formats diferents que cal poder creuar (p. ex. a la pàgina
# General, que combina PBP propi i boxscore de lliga per a la MATEIXA
# temporada), així que aquí es defineixen totes dues formes juntes.
TEMPORADES = [
    {"pbp": "25-26", "feb": "2025-26", "etiqueta": "2025-26"},
    {"pbp": "26-27", "feb": "2026-27", "etiqueta": "2026-27 (actual)"},
]


# --- Mode desenvolupament -------------------------------------------------

# La secció «Developer» de l'app (scraper de PBP i informe a mida) només té
# sentit a l'ordinador de l'analista: el scraper obre un Chromium real amb
# Playwright, que no és a requirements.txt ni existeix a Streamlit Cloud, i
# l'informe a mida escriu al disc local. Desplegades al núvol serien dues
# pàgines que el cos tècnic veuria i que només poden fallar.
#
# El senyal és un fitxer marcador buit a l'arrel, `.mode_dev`, que està al
# .gitignore: hi és en local i mai arriba al repo, per tant mai al núvol. La
# variable d'entorn ALMEDA_DEV=1 fa el mateix per a usos puntuals. No es fa
# servir cap detecció automàtica de "sóc a Streamlit Cloud" perquè no n'hi ha
# cap de documentada, i endevinar-ho és el que voldríem evitar.
FITXER_MODE_DEV = ARREL / ".mode_dev"


def mode_dev() -> bool:
    """Cert si l'app corre a la màquina de l'analista, amb les eines locals."""
    import os

    if os.environ.get("ALMEDA_DEV", "").strip() in {"1", "true", "True"}:
        return True
    return FITXER_MODE_DEV.exists()


def feb_a_pbp(temporada_feb: str) -> str | None:
    """"2025-26" -> "25-26". None si la temporada no és a TEMPORADES."""
    for t in TEMPORADES:
        if t["feb"] == temporada_feb:
            return t["pbp"]
    return None


def pbp_a_feb(temporada_pbp: str) -> str | None:
    """"25-26" -> "2025-26". None si la temporada no és a TEMPORADES."""
    for t in TEMPORADES:
        if t["pbp"] == temporada_pbp:
            return t["feb"]
    return None


# --- Columnes -------------------------------------------------------------

COL_JORNADA = "Jornada"
COL_RIVAL = "Rival"
COL_DATA = "Data"
COL_LOC_VISIT = "Loc/Visit"
COL_PERIODE = "Periode"
COL_MINUT = "Minut"
COL_TACTICA = "Tàctica"
COL_DESENLLAC = "Desenllac"
COL_ASSIST = "Assist"
COL_FINALITZADORA = "Finalitzadora"
COL_PF = "PF"
COL_PC = "PC"

# Les cinc posicions en pista. L'ORDRE ÉS SIGNIFICATIU: "jug 1" és la base i
# "jug 5" el pivot, així que mai s'ordenen alfabèticament.
COLS_QUINTET = ["jug 1", "jug 2", "jug 3", "jug 4", "jug 5"]
POSICIONS = {
    "jug 1": "1 - Base",
    "jug 2": "2 - Escorta",
    "jug 3": "3 - Aler",
    "jug 4": "4 - Ala-pivot",
    "jug 5": "5 - Pivot",
}

# Parelles de posicions que interessen per al +/- (les d'`oficial_partit_analisi.py`):
# exterior × interior i interior × interior. Les parelles exterior-exterior
# (1-2, 1-3, 2-3) queden fora perquè el que es vol llegir és com casa cada
# exterior amb cada interior.
PARELLES_POSICIO = [
    ("jug 1", "jug 4"),
    ("jug 1", "jug 5"),
    ("jug 2", "jug 4"),
    ("jug 2", "jug 5"),
    ("jug 3", "jug 4"),
    ("jug 3", "jug 5"),
    ("jug 4", "jug 5"),
]

# Columnes del rebot ofensiu (no existeixen a les jornades 1-3).
COLS_REBOT = ["RO a favor", "RD a favor", "RO en contra", "RD en contra", "Punts RO a favor", "Punts RO rival"]

# Columnes afegides per la càrrega (no existeixen als Excel).
COL_FITXER = "Fitxer"
COL_TEMPORADA = "Temporada"
COL_ORDRE = "Ordre"

# Columnes mínimes perquè un fitxer sigui utilitzable.
COLS_OBLIGATORIES = [COL_PERIODE, COL_MINUT, COL_TACTICA, COL_DESENLLAC, COL_PF, COL_PC, *COLS_QUINTET]

# Columnes del bloc defensiu que només existeixen a j18/j19 (prova puntual de
# l'analista). Es llegeixen però ara mateix no s'analitzen.
COLS_DEFENSIVES = ["Tàctica defensiva", "Desenllaç", "punts"]


# --- Paleta ---------------------------------------------------------------
# Els desenllaços NO són categories intercanviables: són una escala ordenada de
# qualitat (cistella > falta > tir fallat > pèrdua).
#
# Verd / blau / taronja / gris. El to sol NO separa el verd del taronja per a
# una persona amb deuteranopia o protanopia, així que la separació la porta la
# LLUMINOSITAT: verd fosc contra taronja clar. Amb aquesta combinació concreta,
# els 6 parells passen el llindar de discriminació simulant deuteranopia,
# protanopia i tritanòpia (mesurat en OKLab, no a ull). Si es toca cap dels
# quatre hexes, cal tornar-ho a mesurar: amb un verd i un taronja de
# lluminositat semblant, el gràfic deixa de ser llegible per a molta gent.
#
# El color porta la FAMÍLIA de qualitat; el desenllaç exacte (T2C vs T3C,
# Falta vs Falta (TLL)) va escrit a l'etiqueta de cada porció, així que cap
# informació depèn només del color.

FAMILIA_CONVERTIT = "#00661f"   # verd    — cistella
FAMILIA_FALTA = "#2a78d6"       # blau    — falta rebuda
FAMILIA_FALLAT = "#f5924b"      # taronja — tir fallat
FAMILIA_PERDUA = "#8a8884"      # gris    — possessió perduda

COLORS_DESENLLAC = {
    "T3C": FAMILIA_CONVERTIT,
    "T2C": FAMILIA_CONVERTIT,
    "Falta (TLL)": FAMILIA_FALTA,
    "Falta": FAMILIA_FALTA,
    "T2F": FAMILIA_FALLAT,
    "T3F": FAMILIA_FALLAT,
    # Banda i fons són pèrdues de possessió: mateixa família que "Pèrdua".
    "Pèrdua": FAMILIA_PERDUA,
    "Banda": FAMILIA_PERDUA,
    "Fons": FAMILIA_PERDUA,
}

# Ordre de llegenda: de millor a pitjor desenllaç.
ORDRE_DESENLLAC = ["T3C", "T2C", "Falta (TLL)", "Falta", "T2F", "T3F", "Pèrdua", "Banda", "Fons"]

# Paleta categòrica (ordre fix, mai ciclat) per a sèries que sí són identitats:
# p. ex. "punts com a finalitzadora" vs "punts generats com a assistent".
# Els quatre primers són els colors de la casa: blau, taronja, verd i gris.
# Blau i taronja van primer perquè és el parell més segur que hi ha per a
# qualsevol tipus de daltonisme, i és el que faran servir els gràfics de 2 sèries.
COLORS_SERIE = [
    "#2a78d6",  # blau
    "#f5924b",  # taronja
    "#00661f",  # verd
    "#8a8884",  # gris
    "#7b4ea8",  # violeta
    "#c2410c",  # terracota
    "#0e7490",  # turquesa fosc
    "#a16207",  # ocre
]

# Parell divergent per al +/- (pol positiu / pol negatiu, neutre al mig).
# Verd i taronja, amb el mateix contrast de lluminositat que a les famílies
# de desenllaç, perquè el signe es llegeixi encara que el to no es distingeixi.
DIVERGENT_POS = "#00661f"
DIVERGENT_NEG = "#f5924b"
NEUTRE = "#c3c2b7"

TINTA_SECUNDARIA = "#52514e"
TINTA_APAGADA = "#898781"
GRAELLA = "#e1e0d9"
