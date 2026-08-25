# -*- coding: utf-8 -*-
"""Generació i descàrrega de l'informe PDF de les jugades seleccionades."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from _comuns import barra_filtres, capcalera, carrega_dades

from almeda_pbp import config as cfg, informe, metriques as m


def pagina(temporada: str) -> None:
    dades, _ = carrega_dades()

    capcalera(
        f"📄 Informe PDF · {temporada}",
        "Tria les jugades i baixa't un PDF amb els números i els gràfics d'aquesta selecció.",
    )

    if dades.empty:
        st.error("Cap dada carregada.")
        st.stop()

    filtrat = barra_filtres(dades, temporada_fixada=temporada)

    if filtrat.empty:
        st.info("Cap jugada amb els filtres actuals. Afluixa els filtres de la barra lateral.")
        st.stop()

    resum = m.resum_sistemes(filtrat)
    if resum.empty:
        st.info("Cap jugada amb sistema anotat amb els filtres actuals.")
        st.stop()

    st.caption(
        "L'informe surt del **mateix filtre que tens a la barra lateral**, així que el PDF i la "
        "pantalla no poden dir coses diferents. Aquí només tries quines jugades hi entren."
    )

    # Sufix: sense això, generar un PDF a "Informe PDF · 25-26" i després
    # navegar a "Informe PDF · 26-27" mostraria encara el botó de descàrrega
    # del PDF vell (pdf_bytes és estat pur, no lligat al cicle de vida d'un
    # widget concret).
    sufix = f"__{temporada}"

    esquerra, dreta = st.columns([2, 1])

    with esquerra:
        disponibles = resum[cfg.COL_TACTICA].tolist()
        per_defecte = resum[resum["Jugades"] >= 10][cfg.COL_TACTICA].tolist() or disponibles[:6]
        sistemes = st.multiselect(
            "Jugades a incloure",
            disponibles,
            default=per_defecte,
            key="pdf_sistemes" + sufix,
            help="Cada jugada ocupa un bloc amb el seu donut de desenllaços i les seves anotadores.",
        )

    with dreta:
        incloure_pm = st.checkbox("Incloure el +/- de la selecció", value=True, key="pdf_pm" + sufix)
        nom_fitxer = st.text_input(
            "Nom del fitxer",
            value=f"informe_pbp_{temporada}_{datetime.now():%Y%m%d}",
            key="pdf_nom" + sufix,
        )

    if not sistemes:
        st.warning("Tria almenys una jugada.")
        st.stop()

    seleccio = filtrat[filtrat[cfg.COL_TACTICA].isin(sistemes)]

    st.divider()
    st.subheader("Previsualització del contingut")

    columnes = st.columns(4)
    columnes[0].metric("Jugades", len(seleccio))
    columnes[1].metric("Sistemes", len(sistemes))
    columnes[2].metric("Punts a favor", int(seleccio[cfg.COL_PF].sum()))
    columnes[3].metric("Blocs al PDF", len(sistemes) + (1 if incloure_pm else 0))

    st.dataframe(resum[resum[cfg.COL_TACTICA].isin(sistemes)], width="stretch", hide_index=True)

    st.divider()

    # El PDF es genera només quan es demana (dibuixar les figures triga uns segons)
    # i es guarda a la sessió perquè el botó de descàrrega no el torni a fer a cada
    # interacció de la pàgina.
    if st.button("Generar l'informe", type="primary", key="pdf_generar" + sufix):
        with st.spinner("Dibuixant gràfics i muntant el PDF..."):
            context = {
                "temporada": temporada,
                "jornades": st.session_state.get("f_jornades" + sufix),
                "periodes": st.session_state.get("f_periodes" + sufix),
                "jugadores": st.session_state.get("f_jugadores" + sufix),
                "mode": st.session_state.get("f_mode" + sufix),
            }
            st.session_state["pdf_bytes" + sufix] = informe.genera_informe(
                filtrat, sistemes, context=context, incloure_plus_minus=incloure_pm
            )
            st.session_state["pdf_nom_final" + sufix] = f"{nom_fitxer or 'informe_pbp'}.pdf"

    if st.session_state.get("pdf_bytes" + sufix):
        st.success(f"Informe llest ({len(st.session_state['pdf_bytes' + sufix]) / 1024:.0f} KB).")
        st.download_button(
            "Descarregar el PDF",
            data=st.session_state["pdf_bytes" + sufix],
            file_name=st.session_state.get("pdf_nom_final" + sufix, "informe_pbp.pdf"),
            mime="application/pdf",
            key="pdf_descarrega" + sufix,
        )
        st.caption(
            "Si canvies els filtres o les jugades, torna a prémer **Generar l'informe**: "
            "el PDF guardat és el de l'última generació."
        )
