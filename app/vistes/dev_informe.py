# -*- coding: utf-8 -*-
"""
Developer · Informe a mida.

A diferència de la pàgina «Informe PDF» (una temporada fixada, estructura fixa
de blocs), aquí es pot combinar QUALSEVOL temporada/jornada/jugadora/sistema i
triar LLIUREMENT quins tipus de gràfic hi entren, en qualsevol ordre. Pensat
per muntar un informe puntual (p. ex. comparar dues jornades de temporades
diferents) que no encaixa a cap de les pàgines fixes.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from _comuns import capcalera, carrega_dades

from almeda_pbp import carrega, config as cfg, informe


def pagina() -> None:
    dades, _ = carrega_dades()

    capcalera(
        "🧩 Developer · Informe a mida",
        "Tria qualsevol combinació de temporada/jornada/jugadora i qualsevol gràfic: es munten en un sol PDF.",
    )

    if dades.empty:
        st.error("Cap dada carregada.")
        st.stop()

    st.subheader("1. Dades a incloure")
    fila1 = st.columns(3)

    temporades_disponibles = sorted(dades[cfg.COL_TEMPORADA].unique())
    temporades = fila1[0].multiselect(
        "Temporades", temporades_disponibles, default=temporades_disponibles, key="dinf_temporades"
    )
    treball = dades[dades[cfg.COL_TEMPORADA].isin(temporades)] if temporades else dades.iloc[0:0]

    jornades_disponibles = sorted(treball[cfg.COL_JORNADA].dropna().unique().tolist())
    jornades = fila1[1].multiselect(
        "Jornades", jornades_disponibles, default=jornades_disponibles, key="dinf_jornades", help="Buit = totes."
    )

    jugadores_disponibles = carrega.jugadores_disponibles(treball)
    jugadores = fila1[2].multiselect(
        "Jugadores (a pista)", jugadores_disponibles, default=[], key="dinf_jugadores", help="Buit = totes."
    )

    filtrat = carrega.filtra(
        treball,
        jornades=jornades or None,
        jugadores=jugadores or None,
        mode_jugadora="a pista",
    )

    if filtrat.empty:
        st.info("Cap jugada amb aquesta combinació de filtres.")
        st.stop()

    st.caption(f"{len(filtrat):,}".replace(",", ".") + " jugades seleccionades.")

    st.divider()
    st.subheader("2. Sistemes")

    sistemes_presents = sorted(filtrat[filtrat[cfg.COL_TACTICA].notna()][cfg.COL_TACTICA].unique())
    if sistemes_presents:
        sistemes = st.multiselect(
            "Sistemes a incloure als blocs «per sistema» (buit = tots els presents)",
            sistemes_presents,
            default=[],
            key="dinf_sistemes",
        )
    else:
        sistemes = []
        st.caption("Cap sistema anotat en aquesta selecció (font automàtica o sense etiquetar) — els blocs «per sistema» no generaran res.")

    st.divider()
    st.subheader("3. Gràfics")

    tipus_per_sistema = {k: v for k, v in informe.TIPUS_BLOCS.items() if v.abast == "sistema"}
    tipus_generals = {k: v for k, v in informe.TIPUS_BLOCS.items() if v.abast == "general"}

    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("Un bloc per cada sistema seleccionat:")
        seleccio_sistema = [k for k, v in tipus_per_sistema.items() if st.checkbox(v.etiqueta, key=f"dinf_tipus_{k}")]
    with col_b:
        st.caption("Un sol bloc, per a tota la selecció:")
        seleccio_general = [k for k, v in tipus_generals.items() if st.checkbox(v.etiqueta, key=f"dinf_tipus_{k}")]

    tipus_seleccionats = seleccio_sistema + seleccio_general

    if not tipus_seleccionats:
        st.warning("Tria almenys un tipus de gràfic.")
        st.stop()

    n_sistemes_bloc = len(sistemes or sistemes_presents) if seleccio_sistema else 0
    st.caption(
        f"Blocs previstos: {len(seleccio_sistema) * n_sistemes_bloc} «per sistema» + "
        f"{len(seleccio_general)} generals."
    )

    st.divider()
    st.subheader("4. Generar")

    nom_fitxer = st.text_input(
        "Nom del fitxer", value=f"informe_a_mida_{datetime.now():%Y%m%d_%H%M}", key="dinf_nom"
    )

    if st.button("Generar l'informe a mida", type="primary", key="dinf_generar"):
        with st.spinner("Dibuixant gràfics i muntant el PDF..."):
            context = {
                "temporada": ", ".join(temporades) if len(temporades) > 1 else (temporades[0] if temporades else None),
                "jornades": jornades,
            }
            st.session_state["dinf_bytes"] = informe.genera_informe_a_mida(
                filtrat, tipus_seleccionats, sistemes=sistemes or None, context=context
            )
            st.session_state["dinf_nom_final"] = f"{nom_fitxer or 'informe_a_mida'}.pdf"

    if st.session_state.get("dinf_bytes"):
        st.success(f"Informe llest ({len(st.session_state['dinf_bytes']) / 1024:.0f} KB).")
        st.download_button(
            "Descarregar el PDF",
            data=st.session_state["dinf_bytes"],
            file_name=st.session_state.get("dinf_nom_final", "informe_a_mida.pdf"),
            mime="application/pdf",
            key="dinf_descarrega",
        )
