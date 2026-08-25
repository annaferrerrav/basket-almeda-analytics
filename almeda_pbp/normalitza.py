# -*- coding: utf-8 -*-
"""
Normalització de valors del PBP manual.

Els Excel s'omplen a mà durant el partit, així que el mateix concepte hi apareix
escrit de maneres diferents ("contratac" / "Contraatac", "t2f" / "T2F",
"Jové" / "jové" / "jove"). Aquí es consolida tot a una forma canònica.

Regla de disseny: NO s'endevina mai. Un valor que no estigui als diccionaris
d'àlies i que no encaixi amb la normalització genèrica es marca com a
desconegut i surt a la pàgina "Qualitat de dades" perquè l'analista decideixi.
Així cap error d'anotació desapareix silenciosament dins d'una mitjana.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Valors que volen dir "aquí no hi ha res".
BUITS = {"", "-", "--", "nan", "none", "n/a"}


def _clau(valor) -> str:
    """Passa un valor a minúscules, sense accents i amb espais col·lapsats."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    text = re.sub(r"\s+", " ", str(valor)).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


# --- Tàctiques ------------------------------------------------------------
# Clau = forma normalitzada per _clau(); valor = forma canònica.
# Només hi ha entrades per als sinònims REALS trobats als fitxers 25-26.

ALIES_TACTICA = {
    "play": "Play",
    "go": "Go",
    "siena": "Siena",
    "contratac": "Contratac",
    "contraatac": "Contratac",
    "lliure": "Lliure",
    "libre": "Lliure",
    "zona libre": "Zona lliure",   # ES diferent de "lliure": atac lliure contra zona
    "zona 2": "Zona 2",
    "zona 4": "Zona 4",
    "zona4": "Zona 4",           # sense l'espai
    "final": "Final",
    "final/ro": "Final",           # jugada final que acaba en rebot ofensiu
    "lado": "Lado",
    "2 lado": "2 Lado",
    "bloc lado": "Bloc lado",
    "boston": "Boston",
    "pisa": "Pisa",
    "portland": "Portland",
    "miami": "Miami",
    "zeta": "Zeta",
    "triple": "Triple",
    "cuatro": "Cuatro",
    "cinco": "Cinco",
    "2 arriba": "2 Arriba",
    "2 mano": "2 Mano",
    "2mano": "2 Mano",
    "pissarra": "Pissarra",
    "pisarra": "Pissarra",
    "pissara": "Pissarra",
    "banda 34": "Banda 34",
    "banda 35": "Banda 35",
    "fons": "Fons",              # fons genèric, sense especificar la jugada
    "fons?": "Fons",             # anotat amb dubte durant el partit
    "fons 21": "Fons 21",
    "fons zona": "Fons zona",
    "fons zeta": "Fons zeta",
    "tac30": "Tac30",
    "tac33": "Tac33",
    "tac34": "Tac34",
    "tac35": "Tac35",
    "tac 35": "Tac35",
    "recuperacio": "Recuperació",
    # Situacions, no sistemes: es conserven perquè expliquen d'on ve la possessió.
    "ro": "RO",
    "cd": "CD",
}

# --- Desenllaços ----------------------------------------------------------

ALIES_DESENLLAC = {
    "t2c": "T2C",
    "t2f": "T2F",
    "t3c": "T3C",
    "t3f": "T3F",
    "falta": "Falta",
    "falta (tll)": "Falta (TLL)",
    "perdua": "Pèrdua",
    "banda": "Banda",
    "fons": "Fons",
}

# Desenllaços que compten com a possessió acabada en tir de camp.
DESENLLAC_TIR = {"T2C", "T2F", "T3C", "T3F"}
DESENLLAC_CONVERTIT = {"T2C", "T3C"}
DESENLLAC_PERDUA = {"Pèrdua", "Banda", "Fons"}

# --- Noms de jugadores ----------------------------------------------------
# Només calen entrades per a variants que la normalització genèrica (Title Case
# + accents del primer cop vist) no resol tota sola.

ALIES_JUGADORA = {
    "jove": "Jové",
    "bet": "Bet",
    # "Bali" surt només a j10 (5 cops): mateixa jugadora que "Balibrea"
    # (Claudia Balibrea), que juga la resta de jornades del voltant.
    "bali": "Balibrea",
    # L'antic "Maria" (j1,3,4,5) es diu de cognom Llodra.
    "maria": "Llodra",
    # "Ibáñez" (j17, font automàtica) és una Maria diferent: Maria Ibáñez.
    # Per això l'altra Maria s'ha renombrat a "Llodra" i no es diu "Maria" a
    # seques enlloc: si hi hagués dues "Maria" curtes no es podrien distingir.
    "ibanez": "Maria Ibáñez",
    # "Garcia" (j17, font automàtica) és Marina Garcia: la mateixa jugadora
    # que ja surt com a "Marina" a la resta de la temporada.
    "garcia": "Marina",
    # "Robles" (j22) també es diu Marina de nom (Marina Robles), però és una
    # jugadora DIFERENT de "Marina" (Marina Garcia, ja consolidada amb 1000+
    # aparicions). Es deixa amb el cognom a propòsit perquè no es confonguin.
}


def _aplica(valor, alies: dict[str, str]) -> tuple[str | None, bool]:
    """
    Retorna (valor_canonic, es_desconegut).

    - buit  -> (None, False): absència legítima, no és un error.
    - àlies -> (canonic, False)
    - altre -> (Title Case, True): es conserva tal com està però es marca.
    """
    clau = _clau(valor)
    if clau in BUITS:
        return None, False
    if clau in alies:
        return alies[clau], False
    return str(valor).strip(), True


def normalitza_serie(serie: pd.Series, alies: dict[str, str]) -> tuple[pd.Series, pd.Series]:
    """Normalitza una columna sencera. Retorna (valors, màscara de desconeguts)."""
    resultat = serie.map(lambda v: _aplica(v, alies))
    valors = resultat.map(lambda t: t[0])
    desconeguts = resultat.map(lambda t: t[1])
    return valors, desconeguts


def normalitza_jugadora(serie: pd.Series) -> pd.Series:
    """
    Normalitza noms de jugadores: capitalitza i unifica variants sense accent.

    A diferència de tàctiques i desenllaços, aquí la normalització genèrica
    (Title Case) SÍ és segura, perquè les variants observades només difereixen
    en majúscules i accents.
    """
    def _una(valor):
        clau = _clau(valor)
        if clau in BUITS:
            return None
        if clau in ALIES_JUGADORA:
            return ALIES_JUGADORA[clau]
        # Es conserva l'accentuació original, només s'arregla la caixa.
        net = re.sub(r"\s+", " ", str(valor)).strip()
        return net[:1].upper() + net[1:].lower()

    return serie.map(_una)
