# -*- coding: utf-8 -*-
"""+/- individual, per parelles i per jugadora × posició."""

from __future__ import annotations

import streamlit as st

from _comuns import avis_mostra, barra_filtres, capcalera, carrega_dades

from almeda_pbp import grafics, metriques as m


def pagina(temporada: str) -> None:
    dades, _ = carrega_dades()

    capcalera(
        f"➕➖ Plus/minus · {temporada}",
        "Diferencial de punts amb cada jugadora (o cada parella) en pista.",
    )

    if dades.empty:
        st.error("Cap dada carregada.")
        st.stop()

    filtrat = barra_filtres(dades, temporada_fixada=temporada)
    avis_mostra(len(filtrat))

    if filtrat.empty:
        st.info("Cap jugada amb els filtres actuals.")
        st.stop()

    pestanya_pos_parelles, pestanya_parelles, pestanya_individual, pestanya_posicio = st.tabs(
        ["Parelles per posició", "Parelles (qualsevol posició)", "Individual", "Jugadora × posició"]
    )

    with pestanya_pos_parelles:
        controls = st.columns([2, 1, 1])
        min_pos_par = controls[0].slider(
            "Mínim de jugades juntes en aquelles posicions", 1, 150, 15, key="pospar_min"
        )
        panells_fila = controls[1].select_slider(
            "Panells per fila", options=[1, 2, 3], value=2, key="pospar_cols"
        )
        alcada_barra = controls[2].select_slider(
            "Mida",
            options=[10, 13, 18, 26],
            value=13,
            format_func=lambda v: {10: "Molt petit", 13: "Petit", 18: "Mitjà", 26: "Gran"}[v],
            key="pospar_mida",
        )
        per_posicions = m.plus_minus_parelles_posicio(filtrat, min_jugades=min_pos_par)

        if per_posicions.empty:
            st.info(f"Cap parella de posicions arriba a {min_pos_par} jugades juntes amb els filtres actuals.")
        else:
            st.plotly_chart(
                grafics.facetes_plus_minus_posicio(
                    per_posicions, columnes=panells_fila, alcada_barra=alcada_barra
                ),
                width="stretch",
                key=f"pospar_{temporada}",
            )
            st.dataframe(
                per_posicions.drop(columns=["Jugadora A", "Jugadora B"]),
                width="stretch",
                hide_index=True,
            )

    with pestanya_parelles:
        min_jugades = st.slider(
            "Mínim de jugades juntes",
            1, 200, 25,
            key="par_min",
            help="Filtra parelles amb massa poca mostra. Amb 5 jugades juntes, un +/- de +6 no significa res.",
        )
        parelles = m.plus_minus_parelles(filtrat, min_jugades=min_jugades)

        if parelles.empty:
            st.info(f"Cap parella arriba a {min_jugades} jugades juntes amb els filtres actuals.")
        else:
            normalitzar = st.checkbox(
                "Normalitzar per 100 jugades",
                value=False,
                key="par_norm",
                help="Compara parelles que han jugat molt amb parelles que han jugat poc. Amplifica el soroll de les que tenen poca mostra.",
            )
            columna = "+/- per 100 jugades" if normalitzar else "+/-"
            st.plotly_chart(
                grafics.barres_plus_minus(
                    parelles,
                    columna_etiqueta="Parella",
                    columna_valor=columna,
                    titol=f"{columna} per parella (≥ {min_jugades} jugades juntes)",
                ),
                width="stretch",
            )
            st.dataframe(parelles, width="stretch", hide_index=True)

    with pestanya_individual:
        individual = m.plus_minus_individual(filtrat)
        if individual.empty:
            st.info("Cap jugadora amb jugades als filtres actuals.")
        else:
            st.plotly_chart(
                grafics.barres_plus_minus(
                    individual,
                    columna_etiqueta="Jugadora",
                    columna_valor="+/-",
                    titol="+/- per jugadora",
                    alcada_per_barra=30,
                ),
                width="stretch",
            )
            st.dataframe(individual, width="stretch", hide_index=True)

    with pestanya_posicio:
        st.caption(
            "La mateixa jugadora desglossada per la posició que ocupava al quintet "
            "(`jug 1` = base ... `jug 5` = pivot). Serveix per veure si una jugadora rendeix "
            "diferent segons on la posis — però compte: quan juga fora de la seva posició "
            "sol ser perquè falta algú, i això també mou el resultat."
        )
        min_posicio = st.slider("Mínim de jugades en aquella posició", 1, 200, 25, key="pos_min")
        per_posicio = m.plus_minus_per_posicio(filtrat, min_jugades=min_posicio)

        if per_posicio.empty:
            st.info(f"Cap combinació jugadora-posició arriba a {min_posicio} jugades.")
        else:
            st.plotly_chart(
                grafics.barres_plus_minus(
                    per_posicio,
                    columna_etiqueta="Etiqueta",
                    columna_valor="+/-",
                    titol=f"+/- per jugadora i posició (≥ {min_posicio} jugades)",
                ),
                width="stretch",
            )
            st.dataframe(
                per_posicio.drop(columns=["Etiqueta"]),
                width="stretch",
                hide_index=True,
            )
