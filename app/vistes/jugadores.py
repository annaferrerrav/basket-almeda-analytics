# -*- coding: utf-8 -*-
"""
Plantilla i fitxa individual.

Dues pantalles a la mateixa pàgina: la llista de jugadores i, en clicar-ne
una, la seva fitxa. La selecció viu al session_state (no a la URL) perquè
`st.navigation` aquí lliga cada pàgina a una funció, no a un fitxer amb
paràmetres propis.

Les xifres bàsiques surten de l'**acta oficial** (`almeda_pbp/jugadores.py`),
no del PBP manual: minuts, tirs, rebots i faltes només hi són a l'acta, i el
que sí que hi ha a totes dues fonts (punts, assistències) a l'acta està
arbitrat. El PBP aporta a la fitxa el que l'acta no sap: amb quins sistemes
era a pista, el +/- per posició i el detall jugada a jugada.

Els sistemes per jugadora són a la pestanya «Per jugadora» de Sistemes, que és
on s'analitzen sistemes.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _comuns import avis_mostra, barra_filtres, capcalera, carrega_boxscore, carrega_dades

from almeda_pbp import config as cfg, grafics, jugadores as jug, metriques as m


def pagina(temporada: str) -> None:
    dades, _ = carrega_dades()
    boxscore = carrega_boxscore()
    temporada_feb = cfg.pbp_a_feb(temporada)

    filtrat = dades.iloc[0:0] if dades.empty else barra_filtres(dades, temporada_fixada=temporada)
    jornades = _jornades_seleccionades(dades, filtrat, temporada)

    plantilla = jug.plantilla_oficial(boxscore, temporada_feb, jornades=jornades)

    if plantilla.empty:
        capcalera(f"👥 Plantilla · {temporada}")
        st.warning(
            f"Encara no hi ha actes descarregades de {temporada}. Executa:\n\n"
            f"```\npython -m almeda_pbp.feb --temporada {temporada_feb[:4]} --lligues A --jornades 1 2 3\n```",
            icon="⚠️",
        )
        st.stop()

    # Clau amb sufix de temporada: sense això, obrir una fitxa a 25-26 i
    # canviar de secció deixaria seleccionada una jugadora que potser ni hi és.
    clau = f"jug_seleccionada__{temporada}"
    seleccionada = st.session_state.get(clau)
    if seleccionada is not None and seleccionada not in set(plantilla["Nom oficial"]):
        seleccionada = None
        st.session_state[clau] = None

    if seleccionada is None:
        _llista(plantilla, temporada, clau)
    else:
        _fitxa(boxscore, filtrat, plantilla, seleccionada, temporada, temporada_feb, jornades, clau)


def _jornades_seleccionades(dades: pd.DataFrame, filtrat: pd.DataFrame, temporada: str) -> list[int] | None:
    """
    Quines jornades ha de mirar l'acta, segons els filtres de la barra lateral.

    `None` vol dir «totes les descarregades». Si el filtre de la barra lateral
    està tal com ve (totes les jornades amb PBP), es retorna None a propòsit:
    hi ha jornades amb acta però sense fitxer PBP (la 21 i la 23 de 25-26), i
    amagar-les perquè no s'han anotat a mà seria perdre dades oficials.
    """
    if dades.empty or filtrat.empty:
        return None

    de_la_temporada = dades[dades[cfg.COL_TEMPORADA] == temporada]
    totes = sorted(de_la_temporada[cfg.COL_JORNADA].dropna().astype(int).unique().tolist())
    triades = sorted(filtrat[cfg.COL_JORNADA].dropna().astype(int).unique().tolist())
    return None if triades == totes else triades


def _llista(plantilla: pd.DataFrame, temporada: str, clau: str) -> None:
    capcalera(f"👥 Plantilla · {temporada}", "Dades de l'acta oficial. Clica una jugadora per veure'n la fitxa.")

    per_partit = st.toggle(
        "Per partit",
        key=f"plantilla_per_partit__{temporada}",
        help="Divideix els comptatges pels partits jugats. Els percentatges no canvien: "
        "sempre surten dels totals acumulats.",
    )

    mostrar = _escala(plantilla, per_partit)
    # Els totals són nombres rodons (599 minuts); les mitjanes necessiten el
    # decimal per distingir 4.1 de 4.4 punts per partit.
    formata = (lambda v: f"{v:.1f}") if per_partit else (lambda v: f"{v:.0f}")

    columnes = st.columns(4)
    for i, fila in mostrar.iterrows():
        with columnes[i % 4]:
            with st.container(border=True):
                dorsal = f"#{int(fila['Dorsal'])} " if pd.notna(fila.get("Dorsal")) else ""
                st.markdown(f"### {dorsal}{fila['Jugadora']}")
                caixa1, caixa2, caixa3 = st.columns(3)
                caixa1.metric("Minuts", formata(fila["MIN"]))
                caixa2.metric("Punts", formata(fila["PT"]))
                caixa3.metric("Val.", formata(fila["VA"]))
                st.caption(f"{int(fila['Partits'])} partits · {int(fila['Titular'])} de titular")
                if st.button(
                    "Veure fitxa",
                    key=f"btn_fitxa_{temporada}_{fila['Nom oficial']}",
                    width="stretch",
                ):
                    st.session_state[clau] = fila["Nom oficial"]
                    st.rerun()

    st.divider()
    st.subheader("Tota la plantilla")
    st.dataframe(mostrar.drop(columns=["Nom oficial"]), width="stretch", hide_index=True)


def _escala(plantilla: pd.DataFrame, per_partit: bool) -> pd.DataFrame:
    """
    Els comptatges dividits pels partits jugats, si es demana.

    Els percentatges es deixen tal com venen a propòsit: ja estan calculats
    sobre els totals acumulats i dividir-los pels partits no voldria dir res.
    """
    taula = plantilla.copy()
    if not per_partit:
        return taula
    for col in (c for c in jug.COLS_PER_PARTIT if c in taula.columns):
        taula[col] = (taula[col] / taula["Partits"]).round(1)
    return taula


def _fitxa(
    boxscore: pd.DataFrame,
    filtrat: pd.DataFrame,
    plantilla: pd.DataFrame,
    nom_oficial: str,
    temporada: str,
    temporada_feb: str,
    jornades: list[int] | None,
    clau: str,
) -> None:
    if st.button("← Tornar a la plantilla", key=f"btn_torna_{temporada}"):
        st.session_state[clau] = None
        st.rerun()

    fila = plantilla[plantilla["Nom oficial"] == nom_oficial].iloc[0]
    nom = fila["Jugadora"]
    capcalera(f"👤 {nom} · {temporada}", nom_oficial if nom != nom_oficial else "")

    partits = max(int(fila["Partits"]), 1)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Partits", int(fila["Partits"]), delta=f"{int(fila['Titular'])} de titular", delta_color="off")
    col2.metric("Minuts", f"{fila['MIN'] / partits:.1f}")
    col3.metric("Punts", f"{fila['PT'] / partits:.1f}")
    col4.metric("Rebots", f"{fila['RT'] / partits:.1f}", delta=f"{fila['RO'] / partits:.1f} ofensius", delta_color="off")
    col5.metric("Assistències", f"{fila['AS'] / partits:.1f}")
    col6.metric("Valoració", f"{fila['VA'] / partits:.1f}")
    st.caption("Mitjanes per partit, de l'acta oficial.")

    esquerra, dreta = st.columns([1, 1])

    with esquerra:
        st.subheader("Tir")
        tirs = [
            {"Tir": "2 punts", "Fets": int(fila["T2C"]), "Intents": int(fila["T2I"]), "%": fila["T2 (%)"]},
            {"Tir": "3 punts", "Fets": int(fila["T3C"]), "Intents": int(fila["T3I"]), "%": fila["T3 (%)"]},
            {"Tir": "Camp", "Fets": int(fila["TCC"]), "Intents": int(fila["TCI"]), "%": fila["TC (%)"]},
            {"Tir": "Lliures", "Fets": int(fila["TLC"]), "Intents": int(fila["TLI"]), "%": fila["TL (%)"]},
        ]
        st.dataframe(pd.DataFrame(tirs), width="stretch", hide_index=True)
        st.caption("Totals de la temporada. Els percentatges surten dels totals acumulats.")

    with dreta:
        st.subheader("La resta de l'acta")
        altres = [
            {"Concepte": "Rebots ofensius / defensius", "Total": f"{int(fila['RO'])} / {int(fila['RD'])}"},
            {"Concepte": "Assistències", "Total": int(fila["AS"])},
            {"Concepte": "Recuperacions / pèrdues", "Total": f"{int(fila['BR'])} / {int(fila['BP'])}"},
            {"Concepte": "Taps a favor / en contra", "Total": f"{int(fila['TapF'])} / {int(fila['TapC'])}"},
            {"Concepte": "Faltes comeses / rebudes", "Total": f"{int(fila['FC'])} / {int(fila['FR'])}"},
            {"Concepte": "+/- oficial", "Total": f"{int(fila['+/-']):+d}"},
        ]
        st.dataframe(pd.DataFrame(altres), width="stretch", hide_index=True)

    st.subheader("Partit a partit")
    st.dataframe(
        jug.partits_jugadora(boxscore, temporada_feb, nom_oficial, jornades=jornades),
        width="stretch",
        hide_index=True,
    )

    _seccio_pbp(filtrat, nom, temporada)


def _seccio_pbp(filtrat: pd.DataFrame, nom: str, temporada: str) -> None:
    """El que només sap el PBP: sistemes a pista, posicions i jugada a jugada."""
    st.divider()
    st.subheader("Del play-by-play propi")

    if filtrat.empty:
        st.info("No hi ha PBP carregat d'aquesta temporada.")
        return

    if nom not in set(filtrat[cfg.COLS_QUINTET].values.ravel()):
        st.info(
            f"«{nom}» no surt a cap quintet del PBP amb els filtres actuals. "
            "Si el nom curt del PBP no coincideix amb el de l'acta, repassa "
            "`dades/noms_jugadores.toml`."
        )
        return

    fitxa = m.fitxa_jugadora(filtrat, nom)
    totals = fitxa["totals"]
    avis_mostra(int(totals["Jugades"]))

    col1, col2, col3 = st.columns(3)
    col1.metric("Jugades en pista", int(totals["Jugades"]))
    col2.metric("+/- del PBP", f"{int(totals['+/-']):+d}", delta=f"{totals['+/- per 100 jugades']:+.1f} per 100", delta_color="off")
    col3.metric("Punts generats", int(totals["Punts assistits"]), delta=f"{int(totals['Assistències'])} assistències", delta_color="off")

    esquerra, dreta = st.columns([1, 1])

    with esquerra:
        st.plotly_chart(
            grafics.barres_desenllac_jugadora(fitxa["desenllacos"]),
            width="stretch",
            key=f"fitxa_des_{temporada}_{nom}",
        )

    with dreta:
        st.markdown("**Sistemes amb ella en pista**")
        st.caption(
            "Mesura com va l'**equip** amb ella a la pista, no què fa ella: totes les jugades "
            "amb ella al quintet compten, les acabi qui les acabi."
        )
        min_jugades = st.slider("Mínim de jugades", 1, 50, 8, key=f"fitxa_min_{temporada}")
        st.plotly_chart(
            grafics.barres_punts_jugada(fitxa["sistemes_en_pista"], min_jugades),
            width="stretch",
            key=f"fitxa_sis_{temporada}_{nom}",
        )

    esquerra, dreta = st.columns([1, 1])

    with esquerra:
        st.markdown("**Per posició**")
        st.caption(
            "Un +/- dolent en una posició no vol dir que hi jugui pitjor: sovint vol dir que "
            "quan hi juga és perquè falta la titular d'aquella posició. És descriptiu, no causal."
        )
        if fitxa["posicions"].empty:
            st.info("Aquesta jugadora no consta a cap quintet fiable.")
        else:
            st.dataframe(fitxa["posicions"], width="stretch", hide_index=True)

    with dreta:
        st.markdown("**Punts anotats i generats per sistema**")
        if fitxa["protagonisme_per_sistema"].empty:
            st.info("No consta com a finalitzadora ni assistent en cap sistema.")
        else:
            st.dataframe(fitxa["protagonisme_per_sistema"], width="stretch", hide_index=True)

    with st.expander("Les seves jugades, una a una"):
        columnes_detall = [
            cfg.COL_JORNADA, cfg.COL_PERIODE, cfg.COL_MINUT, cfg.COL_TACTICA,
            cfg.COL_DESENLLAC, cfg.COL_FINALITZADORA, cfg.COL_ASSIST, cfg.COL_PF, cfg.COL_PC,
        ]
        presents = [c for c in columnes_detall if c in fitxa["en_pista"].columns]
        st.dataframe(fitxa["en_pista"][presents], width="stretch", hide_index=True)
