# -*- coding: utf-8 -*-
"""
Tot un partit en una pàgina.

La resta de vistes miren la temporada sencera i deixen filtrar per jornada;
aquesta fa el contrari: es tria un partit i s'hi posa a sobre tot el que se'n
sap, de les dues fonts, sense haver d'anar saltant de pàgina.

No fa servir `_comuns.barra_filtres` a propòsit: aquí el filtre és el partit i
prou. Barrejar-hi els filtres de jugadora i sistema de la barra lateral faria
que la pàgina digués «el partit» ensenyant-ne un tros.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _comuns import capcalera, carrega_boxscore, carrega_dades, graella_caixes, injecta_estil_caixes

from almeda_pbp import config as cfg, grafics, jugadores as jug, lliga, metriques as m

EQUIP_PROPI = "BASKET ALMEDA"

COLS_ACTA = [
    "Jugadora", "MIN", "PT", "T2C", "T2I", "T3C", "T3I", "TLC", "TLI",
    "RO", "RD", "RT", "AS", "BR", "BP", "FC", "FR", "VA", "+/-",
]


def pagina(temporada: str) -> None:
    dades, _ = carrega_dades()
    boxscore = carrega_boxscore()
    temporada_feb = cfg.pbp_a_feb(temporada)

    pbp_temporada = dades[dades[cfg.COL_TEMPORADA] == temporada] if not dades.empty else dades
    acta_temporada = jug.boxscore_equip(boxscore, temporada_feb)

    jornades = _jornades_disponibles(pbp_temporada, acta_temporada)
    if not jornades:
        capcalera(f"📋 Per jornada · {temporada}")
        st.info(f"Encara no hi ha cap partit de {temporada}, ni al PBP ni a l'acta oficial.")
        st.stop()

    titol, selector = st.columns([2, 1])
    with titol:
        capcalera(f"📋 Per jornada · {temporada}")
    jornada = selector.selectbox(
        "Jornada",
        jornades,
        index=len(jornades) - 1,
        key=f"jornada_sel__{temporada}",
        format_func=lambda j: _etiqueta_jornada(j, pbp_temporada, acta_temporada),
    )

    pbp = pbp_temporada[pbp_temporada[cfg.COL_JORNADA] == jornada] if not pbp_temporada.empty else pbp_temporada
    acta = acta_temporada[acta_temporada["Jornada"] == jornada] if not acta_temporada.empty else acta_temporada

    injecta_estil_caixes()
    _marcador(pbp, acta, boxscore, temporada_feb, jornada)

    st.divider()
    esquerra, dreta = st.columns([3, 2])

    with esquerra:
        st.subheader("Acta oficial")
        _taula_acta(boxscore, temporada_feb, jornada)

    with dreta:
        st.subheader("Sistemes")
        _sistemes(pbp, temporada, jornada)

    st.divider()
    esquerra, dreta = st.columns([1, 1])

    with esquerra:
        st.subheader("+/- del partit")
        _plus_minus(pbp, temporada, jornada)

    with dreta:
        st.subheader("Com acaben les jugades")
        _desenllacos(pbp, temporada, jornada)


def _jornades_disponibles(pbp: pd.DataFrame, acta: pd.DataFrame) -> list[int]:
    """Totes les jornades que tenen alguna cosa: PBP, acta, o les dues."""
    trobades: set[int] = set()
    if not pbp.empty:
        trobades.update(pbp[cfg.COL_JORNADA].dropna().astype(int).tolist())
    if not acta.empty:
        trobades.update(acta["Jornada"].dropna().astype(int).tolist())
    return sorted(trobades)


def _etiqueta_jornada(jornada: int, pbp: pd.DataFrame, acta: pd.DataFrame) -> str:
    """«J14 · GEIEG PACISA», amb el rival de la font que el tingui."""
    rival = ""
    if not acta.empty:
        seves = acta[acta["Jornada"] == jornada]
        if not seves.empty:
            rival = str(seves.iloc[0]["Rival"])
    if not rival and not pbp.empty:
        seves = pbp[pbp[cfg.COL_JORNADA] == jornada]
        if not seves.empty and pd.notna(seves.iloc[0].get(cfg.COL_RIVAL)):
            rival = str(seves.iloc[0][cfg.COL_RIVAL])
    return f"J{jornada} · {rival}" if rival else f"J{jornada}"


def _marcador(
    pbp: pd.DataFrame,
    acta: pd.DataFrame,
    boxscore: pd.DataFrame,
    temporada_feb: str,
    jornada: int,
) -> None:
    """Resultat i xifres de capçalera, de l'acta si hi és i del PBP si no."""
    items: list[dict] = []

    if not acta.empty:
        fila = acta.iloc[0]
        propis, contraris = int(fila["PT equip"]), int(fila["PT rival"])
        items += [
            {
                "etiqueta": str(fila["Rival"]),
                "valor": f"{propis}-{contraris}",
                "delta": ("Victòria" if propis > contraris else "Derrota") + f" · {fila['Pista']}",
            },
            {"etiqueta": "Data", "valor": str(fila["Data"]), "delta": f"jornada {jornada}"},
        ]
        rebot = lliga.resum_rebot(boxscore, temporada_feb, EQUIP_PROPI, jornades=[jornada])
        items += [
            {"etiqueta": "Rebots", "valor": rebot["rt"], "delta": f"{rebot['ro']} of. · {rebot['rd']} def."},
            {"etiqueta": "ORB %", "valor": f"{rebot['orb']:.1f}%", "delta": f"DRB {rebot['drb']:.1f}%"},
        ]

    if not pbp.empty:
        resum = m.resum_general(pbp)
        items += [
            {"etiqueta": "Jugades (PBP)", "valor": resum["jugades"], "delta": f"{resum['ppp']:.2f} punts/jugada"},
            {
                "etiqueta": "Diferencial PBP",
                "valor": f"{resum['punts'] - resum['punts_rival']:+d}",
                "delta": f"{resum['punts']}-{resum['punts_rival']}",
            },
        ]
    else:
        items.append({"etiqueta": "PBP", "valor": "—", "delta": "sense fitxer"})

    graella_caixes(items, columnes=min(len(items), 6), gran=True)


def _taula_acta(boxscore: pd.DataFrame, temporada_feb: str, jornada: int) -> None:
    taula = jug.plantilla_oficial(boxscore, temporada_feb, jornades=[jornada])
    if taula.empty:
        st.info("Aquesta jornada no té acta descarregada.")
        return

    # «Partits» i «Titular» no diuen res dins d'un sol partit: o va jugar o no.
    presents = [c for c in COLS_ACTA if c in taula.columns]
    st.dataframe(
        taula[presents].assign(MIN=taula["MIN"].round(1)),
        width="stretch",
        hide_index=True,
    )


def _sistemes(pbp: pd.DataFrame, temporada: str, jornada: int) -> None:
    if pbp.empty:
        st.info("Aquesta jornada no té fitxer de PBP.")
        return

    resum = m.resum_sistemes(pbp)
    if resum.empty:
        st.info(
            "Aquesta jornada no té els sistemes anotats: és un PBP generat automàticament "
            "des del feed de la FEB, que porta desenllaç i punts però no la tàctica. "
            "La resta de la pàgina sí que hi és."
        )
        return

    # Mínim d'1 i no el de la resta de l'app: dins d'un sol partit un sistema
    # jugat tres cops ja és informació, i amb el llindar habitual (8-10) no
    # quedaria pràcticament res a la pantalla.
    st.plotly_chart(
        grafics.barres_punts_jugada(resum, min_jugades=1),
        width="stretch",
        key=f"jor_sis_{temporada}_{jornada}",
    )
    st.dataframe(
        resum[[cfg.COL_TACTICA, "Jugades", "Punts", "Punts/jugada", "% pèrdues"]],
        width="stretch",
        hide_index=True,
    )


def _plus_minus(pbp: pd.DataFrame, temporada: str, jornada: int) -> None:
    if pbp.empty:
        st.info("Aquesta jornada no té fitxer de PBP.")
        return

    taula = m.plus_minus_individual(pbp)
    if taula.empty:
        st.info("Aquesta jornada no té els quintets anotats de forma fiable.")
        return

    st.caption(
        "Del PBP: diferencial de punts amb ella a la pista. No és el +/- de l'acta, "
        "que compta per temps i no per possessions anotades."
    )
    st.plotly_chart(
        grafics.barres_plus_minus(taula, columna_etiqueta="Jugadora", titol="+/- del partit"),
        width="stretch",
        key=f"jor_pm_{temporada}_{jornada}",
    )


def _desenllacos(pbp: pd.DataFrame, temporada: str, jornada: int) -> None:
    if pbp.empty:
        st.info("Aquesta jornada no té fitxer de PBP.")
        return

    taula = (
        pbp[pbp[cfg.COL_DESENLLAC].notna()]
        .groupby(cfg.COL_DESENLLAC)
        .agg(Jugades=(cfg.COL_PF, "size"), Punts=(cfg.COL_PF, "sum"))
        .reset_index()
        .rename(columns={cfg.COL_DESENLLAC: "Desenllac"})
    )
    if taula.empty:
        st.info("Aquesta jornada no té els desenllaços anotats.")
        return

    st.plotly_chart(
        grafics.barres_desenllac_jugadora(taula, titol="Desenllaç de totes les jugades"),
        width="stretch",
        key=f"jor_des_{temporada}_{jornada}",
    )
