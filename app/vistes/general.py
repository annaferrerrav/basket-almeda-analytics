# -*- coding: utf-8 -*-
"""Comparativa amb la mitjana de la lliga (i, si es vol, amb un rival concret)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _comuns import (
    capcalera,
    carrega_boxscore,
    injecta_estil_caixes,
    tira_blocs,
)

from almeda_pbp import config as cfg, lliga

EQUIP_PROPI = "BASKET ALMEDA"


def pagina(temporada: str) -> None:
    capcalera(f"🏀 General · {temporada}")
    _seccio_lliga(carrega_boxscore(), temporada)


def _seccio_lliga(boxscore: pd.DataFrame, temporada: str) -> None:
    #st.header("Comparativa amb la mitjana de la lliga")

    # Cada temporada té el seu propi boxscore: barrejar-les donaria una
    # mitjana de dues competicions diferents.
    temporada_feb = cfg.pbp_a_feb(temporada)
    boxscore_temporada = boxscore[boxscore["Temporada"] == temporada_feb] if not boxscore.empty else boxscore

    if boxscore_temporada.empty:
        st.warning(
            f"Encara no hi ha boxscores descarregats de {temporada}. Executa:\n\n"
            f"```\npython -m almeda_pbp.feb --temporada {temporada_feb[:4]} --lligues A B --jornades 1 2 3\n```",
            icon="⚠️",
        )
        return

    sufix = f"__{temporada}"
    filtres = st.columns([1, 2, 2])

    lligues_disponibles = sorted(boxscore_temporada["Lliga"].dropna().unique().tolist())
    # Per defecte, la lliga on juga l'equip propi: comparar-se amb l'altre grup
    # barreja dos contextos de competició diferents.
    lliga_propia = sorted(boxscore_temporada.loc[boxscore_temporada["Equip"] == EQUIP_PROPI, "Lliga"].unique().tolist())
    lligues = filtres[0].multiselect(
        "Lliga",
        lligues_disponibles,
        default=lliga_propia or lligues_disponibles,
        key="bx_lligues" + sufix,
        help="Per defecte només el grup on juga el Basket Almeda.",
    )

    jornades_disponibles = sorted(boxscore_temporada["Jornada"].dropna().astype(int).unique().tolist())
    triades = st.session_state.get("bx_jornades" + sufix, jornades_disponibles)
    resum = (
        f"totes ({len(jornades_disponibles)})"
        if len(triades) == len(jornades_disponibles)
        else f"{len(triades)} de {len(jornades_disponibles)}"
    )
    with st.expander(f"📅 Jornades · {resum}"):
        botons = st.columns([1, 1, 6])
        if botons[0].button("Totes", key="bx_j_totes" + sufix):
            st.session_state["bx_jornades" + sufix] = jornades_disponibles
            st.rerun()
        if botons[1].button("Cap", key="bx_j_cap" + sufix):
            st.session_state["bx_jornades" + sufix] = []
            st.rerun()
        jornades = st.multiselect(
            "Jornades",
            jornades_disponibles,
            default=jornades_disponibles,
            key="bx_jornades" + sufix,
            label_visibility="collapsed",
        )

    taula = lliga.taula_equips(boxscore_temporada, lligues=lligues or None, jornades=jornades or None)

    if taula.empty:
        st.info("Cap partit amb aquests filtres.")
        return

    equips = sorted(taula["Equip"].unique().tolist())
    index_propi = equips.index(EQUIP_PROPI) if EQUIP_PROPI in equips else 0
    equip = filtres[1].selectbox("Equip a comparar", equips, index=index_propi, key="bx_equip" + sufix)

    opcions_rival = ["— cap —"] + [x for x in equips if x != equip]
    rival = filtres[2].selectbox(
        "Rival a intercalar",
        opcions_rival,
        key="bx_rival" + sufix,
        help=(
            "Afegeix una fila entre la mitjana de la lliga i l'equip propi. "
            "El seu delta també és respecte a la mitjana, així les dues files "
            "es poden comparar directament."
        ),
    )
    rival = None if rival == opcions_rival[0] else rival

    comparativa = lliga.comparativa(taula, equip)
    valors = comparativa.set_index("Mètrica")

    valors_rival = lliga.comparativa(taula, rival).set_index("Mètrica") if rival else None

    mostrar_tot = st.toggle(
        "Mostrar tot",
        key="bx_mostrar_tot" + sufix,
        help="Afegeix taps, mates i el detall de tirs lliures fets/intentats.",
    )

    injecta_estil_caixes()

    def _items_mitjana(metriques: list[str]) -> list[dict]:
        return [{"etiqueta": metrica, "valor": lliga.formata(metrica, valors.loc[metrica, "Mitjana lliga"])} for metrica in metriques]

    def _items_equip(metriques: list[str], font: pd.DataFrame) -> list[dict]:
        items = []
        for metrica in metriques:
            fila = font.loc[metrica]
            direccio = int(fila["Direcció"])
            diferencia = fila["Diferència"]

            # Favorable = el signe de la diferència coincideix amb el que és
            # "millor" per a aquesta mètrica (a les pèrdues, negatiu és bo).
            favorable = diferencia * direccio
            if direccio == 0 or diferencia == 0:
                color = "neutre"
            elif favorable > 0:
                color = "millor"
            else:
                color = "pitjor"

            # La fletxa marca el sentit real del canvi; el color, si és bo o
            # dolent. Mai un sol canal per si algú no distingeix els colors.
            fletxa = "▲" if diferencia > 0 else ("▼" if diferencia < 0 else "•")
            delta = f"{fletxa}{diferencia:+.1f}" if diferencia else "• 0"

            posicio = fila["Posició"]
            ajuda = f"{int(posicio)}è de {len(taula)} equips" if pd.notna(posicio) else None

            items.append({
                "etiqueta": metrica,
                "valor": lliga.formata(metrica, fila["Equip"]),
                "delta": delta,
                "color": color,
                "ajuda": ajuda,
            })
        return items

    # --- Tots els blocs en una sola tira horitzontal: dalt la mitjana de la
    # lliga, al mig el rival si se n'ha triat cap, i a baix l'equip propi. Els
    # 4 Factors van primers i amb accent, perquè es vegi que són ràtios
    # calculades i no un comptatge cru de l'acta.
    def _files(metriques: list[str]) -> list[dict]:
        files = [{"items": _items_mitjana(metriques), "estil": ""}]
        if valors_rival is not None:
            files.append({"items": _items_equip(metriques, valors_rival), "estil": "rival"})
        files.append({"items": _items_equip(metriques, valors), "estil": "propi"})
        return files

    blocs_tira: list[dict] = []

    factors_presents = [x for x in lliga.FACTORS if x in valors.index]
    if factors_presents:
        blocs_tira.append({
            "titol": "4 Factors",
            "nota": "ràtios d'eficiència, no comptatges",
            "factor": True,
            "files": _files(factors_presents),
        })

    blocs = dict(lliga.BLOCS)
    if mostrar_tot:
        blocs.update(lliga.BLOCS_OCULTS)

    for nom_bloc, metriques in blocs.items():
        presents = [x for x in metriques if x in valors.index]
        if not presents:
            continue
        blocs_tira.append({"titol": nom_bloc, "files": _files(presents)})

    etiquetes = ["Lliga"] + ([rival] if rival else []) + [equip]
    tira_blocs(blocs_tira, etiquetes=etiquetes)

    with st.expander("Taula completa i rànquings"):
        st.caption("«Posició» és el rànquing dins dels filtres actuals (1 = el millor). Les mètriques de volum no en tenen.")
        st.dataframe(comparativa.drop(columns=["Direcció"]), width="stretch", hide_index=True)
        st.caption("Tots els equips:")
        st.dataframe(taula, width="stretch", hide_index=True)

