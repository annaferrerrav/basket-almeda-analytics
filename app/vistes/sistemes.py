# -*- coding: utf-8 -*-
"""
Tot el que va per sistema, en tres pestanyes.

- Eficiència: què treu l'equip de cada sistema.
- Desenllaços: com acaba cada sistema (donuts).
- Per jugadora: quins sistemes funcionen amb qui (el que abans era la pàgina
  de Jugadores; ara aquella pàgina és la plantilla i la fitxa individual).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _comuns import avis_mostra, barra_filtres, capcalera, carrega_dades, carrega_etiquetes

from almeda_pbp import config as cfg, etiquetes as etq, grafics, metriques as m


def pagina(temporada: str) -> None:
    dades, incidencies = carrega_dades()

    capcalera(f"🥧 Sistemes · {temporada}")

    if dades.empty:
        st.error(
            "No s'ha trobat cap fitxer PBP. Han d'estar a `<temporada>/data/pbp/` amb el número "
            "de jornada al nom (p. ex. `25-26/data/pbp/j22-pbp.xlsx`)."
        )
        st.stop()

    filtrat = barra_filtres(dades, temporada_fixada=temporada)
    if filtrat.empty:
        st.info(f"Encara no hi ha PBP carregat de {temporada}, o els filtres actuals no deixen cap jugada.")
        st.stop()

    # El filtre d'etiquetes i el mínim de jugades comparteixen fila: tots dos
    # decideixen QUÈ apareix, i el mínim en un slider d'ample sencer ocupava
    # una franja de pantalla per a un sol número.
    fila = st.columns([3, 1])
    filtrat = _cercador_etiquetes(filtrat, temporada, fila[0])
    min_eficiencia = fila[1].slider("Mínim de jugades", 1, 50, 10, key="sis_ef_min")

    if filtrat.empty:
        st.info("Cap jugada amb aquesta etiqueta o aquest text.")
        st.stop()

    avis_mostra(len(filtrat))

    resum = m.resum_sistemes(filtrat)

    tab_eficiencia, tab_desenllacos, tab_jugadores = st.tabs(
        ["📈 Eficiència", "🥧 Desenllaços", "🎯 Per jugadora"]
    )

    with tab_eficiencia:
        _eficiencia(filtrat, resum, incidencies, min_eficiencia)

    with tab_desenllacos:
        _desenllacos(filtrat, resum, temporada)

    with tab_jugadores:
        _per_jugadora(filtrat, resum, temporada)


def _eficiencia(
    filtrat: pd.DataFrame, resum: pd.DataFrame, incidencies: pd.DataFrame, min_jugades: int
) -> None:
    """Xifres de temporada i punts per jugada de cada sistema."""
    general = m.resum_general(filtrat)

    capcalera_esq, capcalera_dre = st.columns([3, 1])

    with capcalera_esq:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Jornades", general["jornades"])
        col2.metric("Jugades", f"{general['jugades']:,}".replace(",", "."))
        col3.metric("Punts a favor", general["punts"], delta=f"{general['ppp']:.2f} per jugada", delta_color="off")
        col4.metric("Punts en contra", general["punts_rival"], delta=f"{general['ppp_rival']:.2f} per jugada", delta_color="off")

    with capcalera_dre:
        # Plegat: és context per consultar de tant en tant, no la primera cosa
        # que s'ha de mirar en obrir la pàgina.
        with st.expander("📅 Jornades carregades"):
            per_jornada = (
                filtrat.groupby(cfg.COL_JORNADA)
                .agg(Rival=(cfg.COL_RIVAL, "first"), Jugades=(cfg.COL_PF, "size"), PF=(cfg.COL_PF, "sum"), PC=(cfg.COL_PC, "sum"))
                .reset_index()
            )
            per_jornada["Dif."] = per_jornada["PF"] - per_jornada["PC"]
            st.dataframe(per_jornada, width="stretch", hide_index=True)

            if not incidencies.empty:
                st.info(
                    f"Hi ha {len(incidencies)} avisos de qualitat de dades. "
                    "Mira la pàgina **Qualitat de dades** abans de treure'n conclusions."
                )

    if resum.empty:
        st.info("Cap jugada amb sistema anotat amb els filtres actuals.")
        return

    st.plotly_chart(grafics.barres_punts_jugada(resum, min_jugades), width="stretch")

    st.subheader("Detall numèric")
    st.dataframe(resum, width="stretch", hide_index=True)


def _desenllacos(filtrat: pd.DataFrame, resum: pd.DataFrame, temporada: str) -> None:
    """Els donuts: repartiment de desenllaços dins de cada sistema."""
    if resum.empty:
        st.info("Cap jugada amb sistema anotat amb els filtres actuals.")
        return

    esquerra, mig, dreta = st.columns([2, 1, 1])
    min_jugades = esquerra.slider("Mínim de jugades per mostrar el sistema", 1, 50, 8, key="sis_des_min")
    columnes = mig.select_slider("Donuts per fila", options=[2, 3, 4], value=4, key="sis_cols")
    alcada = dreta.select_slider(
        "Mida",
        options=[360, 460, 560, 680],
        value=360,
        format_func=lambda v: {360: "Petit", 460: "Mitjà", 560: "Gran", 680: "Molt gran"}[v],
        key="sis_des_mida",
    )

    resum_filtrat = resum[resum["Jugades"] >= min_jugades]
    if resum_filtrat.empty:
        st.info(f"Cap sistema arriba a {min_jugades} jugades. Abaixa el mínim o afegeix jornades.")
        return

    desenllacos = m.desenllacos_per_sistema(filtrat)
    st.plotly_chart(
        grafics.pies_desenllac_per_sistema(
            desenllacos, resum_filtrat, columnes=columnes, alcada_fila=alcada
        ),
        width="stretch",
        key=f"pies_{temporada}",
    )

    with st.expander("Repartiment exacte de desenllaços"):
        taula = desenllacos[desenllacos[cfg.COL_TACTICA].isin(resum_filtrat[cfg.COL_TACTICA])]
        pivot = (
            taula.pivot_table(index=cfg.COL_TACTICA, columns="Desenllac", values="Jugades", fill_value=0, aggfunc="sum")
            .astype(int)
        )
        st.dataframe(pivot, width="stretch")


def _per_jugadora(filtrat: pd.DataFrame, resum: pd.DataFrame, temporada: str) -> None:
    """Quins sistemes funcionen amb cada jugadora (abans, la pàgina Jugadores)."""
    taula = m.punts_i_assistencies_per_sistema(filtrat)

    if resum.empty or taula.empty:
        st.info("Cap jugada amb sistema anotat amb els filtres actuals.")
        return

    min_jugades = st.slider("Mínim de jugades per mostrar el sistema", 1, 50, 8, key="sis_jug_min")
    sistemes = resum[resum["Jugades"] >= min_jugades][cfg.COL_TACTICA].tolist()

    if not sistemes:
        st.info(f"Cap sistema arriba a {min_jugades} jugades amb els filtres actuals.")
        return

    # Tres gràfics per fila: caben bé i es poden comparar sense fer scroll.
    per_fila = 3
    for i in range(0, len(sistemes), per_fila):
        columnes = st.columns(per_fila)
        for columna, sistema in zip(columnes, sistemes[i : i + per_fila]):
            with columna:
                st.plotly_chart(
                    grafics.barres_punts_assistencies(taula, sistema),
                    width="stretch",
                    key=f"barres_{temporada}_{sistema}",
                )

    st.divider()
    st.subheader("Quins sistemes es juguen amb cada jugadora")
    st.caption(
        "L'alçada de la barra és **quantes vegades** s'ha jugat el sistema amb aquella jugadora "
        "a la posició escollida; el número de sobre són els **punts** que ha donat. Amb `jug 1` "
        "veus què demana cada base."
    )

    posicio = st.selectbox(
        "Posició",
        cfg.COLS_QUINTET,
        format_func=lambda c: cfg.POSICIONS.get(c, c),
        key="sis_jug_posicio",
    )
    per_posicio = m.sistemes_per_posicio(filtrat, posicio=posicio)
    st.plotly_chart(
        grafics.barres_sistemes_per_jugadora(per_posicio),
        width="stretch",
        key=f"sis_per_jug_{temporada}",
    )

    with st.expander("Detall per sistema i jugadora"):
        st.dataframe(taula[taula[cfg.COL_TACTICA].isin(sistemes)], width="stretch", hide_index=True)


def _cercador_etiquetes(filtrat: pd.DataFrame, temporada: str, contenidor) -> pd.DataFrame:
    """
    Filtre per les etiquetes de `dades/etiquetes_sistemes.toml`.

    Filtra JUGADES però decideix per SISTEMA: triar `banda` es queda amb totes
    les jugades dels sistemes etiquetats `banda`.

    Va a la pàgina i no a la barra lateral perquè és un filtre de treball
    puntual ("ensenya'm només els sistemes de banda"), no un dels filtres
    permanents que es mantenen en canviar de pàgina.
    """
    mapa = carrega_etiquetes()
    disponibles = etq.etiquetes_disponibles(mapa)

    if not disponibles:
        with contenidor.expander("🏷️ Etiquetes de sistema"):
            st.markdown(
                "Encara no hi ha cap etiqueta escrita. Obre "
                "`dades/etiquetes_sistemes.toml` i posa-n'hi:\n\n"
                '```toml\n[sistemes]\n"Pisa" = ["banda"]\n'
                '"Fons 21" = ["fons"]\n"Triple" = ["zona"]\n```\n\n'
                "Si hi apareix un sistema nou, refresca la llista amb "
                "`python -m almeda_pbp.etiquetes` (no s'hi perd res del que ja hi hagi escrit)."
            )
        return filtrat

    sufix = f"__{temporada}"
    sense_etiquetar = sorted(s for s, e in mapa.items() if not e)

    with contenidor.expander(f"🏷️ Etiquetes de sistema · {len(disponibles)} disponibles", expanded=False):
        columnes = st.columns([3, 1])
        seleccio = columnes[0].multiselect(
            "Etiqueta", disponibles, default=[], key="etq_sel" + sufix, help="Buit = tots els sistemes."
        )
        mode = columnes[1].radio(
            "Combinació", ["qualsevol", "totes"], key="etq_mode" + sufix,
            help="«qualsevol»: el sistema té almenys una de les etiquetes. «totes»: les té totes.",
            disabled=len(seleccio) < 2,
        )

        if seleccio:
            sistemes = etq.sistemes_amb_etiqueta(mapa, seleccio, mode=mode)
            st.caption("Sistemes que hi entren: " + (" · ".join(sistemes) if sistemes else "cap"))

        if sense_etiquetar:
            st.caption(f"Sense etiquetar ({len(sense_etiquetar)}): " + " · ".join(sense_etiquetar))

    if not seleccio:
        return filtrat

    resultat = etq.filtra_per_etiqueta(filtrat, mapa, etiquetes=seleccio, mode=mode)
    st.info("🏷️ Filtrant per " + " · ".join(f"**{e}**" for e in seleccio))
    return resultat
