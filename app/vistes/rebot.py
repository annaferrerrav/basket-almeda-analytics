# -*- coding: utf-8 -*-
"""
Rebot: capçalera general i dues pestanyes, ofensiu (RO) i defensiu (RD).

Les dues fonts es reparteixen la feina segons què sap cadascuna:

- L'**acta oficial** té els totals de rebot bons (ofensius i defensius, propis
  i del rival) i és l'única que permet calcular ORB%/DRB%, que necessiten els
  rebots defensius de l'altre equip al mateix partit. També sap quina jugadora
  agafa cada rebot.
- El **PBP** anota el rebot a la POSSESSIÓ, no a la jugadora: no sap qui
  l'agafa, però sí quins punts en surten, en quin període passa i com acaba la
  jugada que continua després (`Tàctica == "RO"`). I sap qui era al quintet.

Per això els totals surten de l'acta i tot el que és per jugadora en pista surt
del PBP: són preguntes diferents i no es barregen a la mateixa taula.
"""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from _comuns import (
    barra_filtres,
    capcalera,
    carrega_boxscore,
    carrega_dades,
    graella_caixes,
    injecta_estil_caixes,
)

from almeda_pbp import config as cfg, grafics, jugadores as jug, lliga, metriques as m

PERIODE_PRORROGA = 5
EQUIP_PROPI = "BASKET ALMEDA"


def pagina(temporada: str) -> None:
    dades, _ = carrega_dades()
    boxscore = carrega_boxscore()
    temporada_feb = cfg.pbp_a_feb(temporada)

    titol, nota = st.columns([3, 2])
    with titol:
        capcalera(f"🔁 Rebot · {temporada}")

    if dades.empty:
        st.error("Cap dada carregada.")
        st.stop()

    filtrat = barra_filtres(dades, temporada_fixada=temporada)
    if filtrat.empty:
        st.info("Cap jugada amb els filtres actuals.")
        st.stop()

    acta = lliga.resum_rebot(boxscore, temporada_feb, EQUIP_PROPI)

    # Columna estreta amb les xifres de capçalera i els commutadors, i el
    # gràfic ocupant la resta: apilades en vertical, les cinc mètriques caben
    # al costat del gràfic en comptes de robar-li una franja sencera a sobre.
    # La nota va al costat del títol: explica d'on surt TOTA la pàgina, no
    # només el bloc que tingui a sobre.
    _nota_de_fonts(acta, nota)

    esquerra, dreta = st.columns([2, 5])
    _capcalera_acta(acta, temporada, esquerra, _cobertura(filtrat))
    _grafic_per_periode(filtrat, temporada, dreta)

    tab_ro, tab_rd = st.tabs(["⬆️ Rebot ofensiu (RO)", "⬇️ Rebot defensiu (RD)"])

    with tab_ro:
        _ofensiu(filtrat, boxscore, temporada, temporada_feb, acta)

    with tab_rd:
        _defensiu(filtrat, boxscore, temporada, temporada_feb, acta)


def _capcalera_acta(acta: dict, temporada: str, contenidor, cobertura: str) -> None:
    """
    Els totals i els percentatges de captura, de l'acta oficial.

    En graella de 2×3 i amb les caixes de `_comuns` en comptes de `st.metric`:
    apilades en una columna fan prop de 500px d'alt, i el que es vol és que
    aquest bloc i el gràfic del costat facin la mateixa alçada (uns 7 cm).
    """
    if not acta["partits"]:
        contenidor.warning(
            f"Encara no hi ha actes descarregades de {temporada}: sense elles no es pot calcular "
            "ORB%/DRB%, que necessiten els rebots del rival al mateix partit.",
            icon="⚠️",
        )
        return

    balanc = acta["ro"] + acta["rd"] - acta["ro_rival"] - acta["rd_rival"]
    items = [
        {"etiqueta": "RO a favor", "valor": acta["ro"], "delta": f"{acta['ro_per_partit']}/partit"},
        {"etiqueta": "RD a favor", "valor": acta["rd"], "delta": f"{acta['rd_per_partit']}/partit"},
        {"etiqueta": "ORB %", "valor": f"{acta['orb']:.1f}%", "delta": f"rival {acta['orb_rival']:.1f}%"},
        {"etiqueta": "DRB %", "valor": f"{acta['drb']:.1f}%", "delta": f"rival {acta['drb_rival']:.1f}%"},
        {"etiqueta": "Balanç", "valor": f"{balanc:+d}", "delta": "rebots"},
        {"etiqueta": "Partits", "valor": acta["partits"], "delta": "a l'acta"},
    ]
    with contenidor:
        injecta_estil_caixes()
        graella_caixes(items, columnes=2, gran=True)
        # A peu de les xifres i en cos petit: és una nota al peu sobre l'abast
        # de les dades, no una conclusió. Amb st.caption encara feia massa cos.
        st.markdown(
            f'<div style="font-size:10px;line-height:1.35;opacity:.6;margin:-2px 0 0 2px;">'
            f'* {html.escape(cobertura)}</div>',
            unsafe_allow_html=True,
        )


def _nota_de_fonts(acta: dict, contenidor) -> None:
    """D'on surt cada xifra, i què volen dir exactament ORB% i DRB%."""
    with contenidor.expander("ℹ️ D'on surt cada xifra i què vol dir ORB%"):
        if acta["partits"]:
            st.markdown(
                f"**ORB %** és quants dels rebots ofensius *disponibles* agafem: els nostres "
                f"{acta['ro']} sobre els {acta['ro'] + acta['rd_rival']} que hi va haver al nostre "
                "atac (els nostres més els defensius del rival). **DRB %**, el mateix a l'altra "
                "cistella. Per construcció l'ORB% del rival és 100 − el nostre DRB%: tot rebot "
                "disponible se l'endú algú."
            )
        st.markdown(
            "- **Totals i percentatges de rebot** (RO, RD, ORB%, DRB%): de l'**acta oficial** "
            "de la FEB. És l'única font que té els rebots del rival al mateix partit, que calen "
            "per saber quants dels rebots *disponibles* s'agafen.\n"
            "- **Quina jugadora agafa cada rebot**: també de l'acta — el PBP anota el rebot a la "
            "possessió, no a la jugadora.\n"
            "- **Punts de segona oportunitat, repartiment per període i què passa després d'un "
            "rebot**: del **play-by-play** propi, que és qui ho sap.\n"
            "- **Rebots amb cada jugadora a la pista**: del **play-by-play**, que és qui sap el "
            "quintet. No és qui l'agafa: és quants se'n fan (o se'n concedeixen) mentre ella hi és."
        )


def _grafic_per_periode(filtrat: pd.DataFrame, temporada: str, grafic) -> None:
    """
    Els commutadors i el gràfic, tots dos a la columna ampla.

    Els commutadors van amb el gràfic i no amb les xifres de l'esquerra perquè
    només afecten el gràfic: les mètriques de l'acta no canvien tocant-los.
    """
    with grafic:
        controls = st.columns(3)
        per_periode = controls[0].toggle(
            "Per període",
            value=True,
            key=f"reb_per_periode__{temporada}",
            help="Desactiva-ho per veure un sol grup de barres amb la suma de tots els períodes.",
        )
        amb_prorroga = controls[1].toggle(
            "Pròrroga",
            key=f"reb_prorroga__{temporada}",
            help="Inclou el període 5. Té molt poca mostra i descompensa l'escala del gràfic.",
        )
        potencial = controls[2].toggle(
            "Sostre",
            value=True,
            key=f"reb_potencial__{temporada}",
            help=(
                "Línia discontínua sobre cada barra de punts, fins als punts que sortirien "
                f"si cada RO acabés en cistella de {m.PUNTS_PER_RO}."
            ),
        )

        dades = filtrat if amb_prorroga else filtrat[filtrat[cfg.COL_PERIODE] != PERIODE_PRORROGA]
        taula = m.potencial_ro(m.resum_rebot_ofensiu(dades))

        if taula.empty:
            st.warning("Les jornades seleccionades no tenen columnes de rebot anotades al PBP.", icon="⚠️")
            return

        st.plotly_chart(
            grafics.barres_rebot_per_periode(
                taula, potencial=potencial, agregat=not per_periode, alcada=265
            ),
            width="stretch",
            key=f"reb_periode_{temporada}",
        )


def _cobertura(dades: pd.DataFrame) -> str:
    """
    Sobre quantes jornades es calcula el gràfic.

    No són les mateixes que les de l'acta: el bloc de rebot no existia als
    primers fitxers de PBP i hi ha jornades sense fitxer. Sense dir-ho, un
    total baix es confon amb «poc rebot» quan en realitat és «menys partits».
    """
    columna = cfg.COLS_REBOT[0]
    total = dades[cfg.COL_JORNADA].nunique()
    if columna not in dades.columns:
        return f"{total} jornades seleccionades, cap amb el bloc de rebot anotat."

    per_jornada = dades.groupby(cfg.COL_JORNADA)[columna].apply(lambda s: s.notna().sum())
    amb_rebot = int((per_jornada > 0).sum())
    if amb_rebot == total:
        return f"Els gràfics del PBP surten de les {total} jornades seleccionades."
    sense = sorted(per_jornada[per_jornada == 0].index.tolist())
    return (
        f"Els gràfics del PBP surten de {amb_rebot} de les {total} jornades seleccionades: "
        f"les {', '.join(map(str, sense))} no tenen el bloc de rebot anotat."
    )


def _ofensiu(
    filtrat: pd.DataFrame, boxscore: pd.DataFrame, temporada: str, temporada_feb: str, acta: dict
) -> None:
    eficiencia = m.eficiencia_ro(filtrat)

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Punts de segona oportunitat",
        eficiencia["punts"],
        delta=f"sostre {eficiencia['potencial']}",
        delta_color="off",
    )
    col2.metric("Aprofitament", f"{eficiencia['aprofitament']:.1f}%")
    col3.metric("Punts per RO", f"{eficiencia['punts_per_ro']:.2f}")
    st.caption(
        f"Del PBP. El sostre són {m.PUNTS_PER_RO} punts per rebot ofensiu: el que valdria si tots "
        f"acabessin en cistella de dos. Compta sobre els {eficiencia['ro']} rebots anotats al PBP, "
        f"no sobre els {acta['ro']} de l'acta."
    )

    esquerra, dreta = st.columns([1, 1])

    with esquerra:
        st.subheader("Què passa després d'un RO?")
        _despres_de_ro(filtrat, temporada)

    with dreta:
        st.subheader("Quines jugadores agafen RO?")
        _rebots_de_lacta(boxscore, temporada, temporada_feb, columna="RO", etiqueta="rebots ofensius")

    st.divider()
    st.subheader("RO a favor amb cada jugadora a la pista")
    st.caption(
        "Del PBP: no és qui l'agafa (això és la taula de l'acta), és quants se'n fan mentre "
        "ella és al quintet. Mesura l'equip amb ella, no ella."
    )
    st.dataframe(
        m.rebots_per_jugadora_en_pista(filtrat, columna="RO a favor"),
        width="stretch",
        hide_index=True,
    )


def _despres_de_ro(filtrat: pd.DataFrame, temporada: str) -> None:
    despres = m.despres_de_rebot(filtrat)
    if despres.empty:
        st.info("Cap jugada amb sistema **RO** anotat amb els filtres actuals.")
        return

    jugades = int(despres["Jugades"].sum())
    punts = int(despres["Punts"].sum())
    # La comparació que dona sentit al número: la resta de jugades de l'equip
    # amb els mateixos filtres.
    altres = filtrat[filtrat[cfg.COL_TACTICA] != "RO"]
    ppp_altres = float(altres[cfg.COL_PF].mean()) if not altres.empty else 0.0
    ppp_ro = punts / jugades if jugades else 0.0

    caixes = st.columns(2)
    caixes[0].metric("Punts per jugada després de RO", f"{ppp_ro:.2f}")
    caixes[1].metric(
        "La resta de jugades",
        f"{ppp_altres:.2f}",
        delta=f"{ppp_ro - ppp_altres:+.2f} de diferència",
        delta_color="off",
    )
    # Aquí la columna es diu "Times": no es compta el mateix que a la resta de
    # l'app (allà "Jugades" són possessions), sinó quantes vegades s'ha donat
    # cada desenllaç després d'un rebot.
    despres = despres.rename(columns={"Jugades": "Times", "% de les jugades": "% dels times"})
    st.plotly_chart(
        grafics.barres_desenllac_jugadora(
            despres.rename(columns={"Times": "Jugades"}),
            titol=f"Desenllaç dels {jugades} times després de rebot",
            etiqueta_valor="Times",
        ),
        width="stretch",
        key=f"ro_despres_{temporada}",
    )
    st.dataframe(despres, width="stretch", hide_index=True)


def _defensiu(
    filtrat: pd.DataFrame, boxscore: pd.DataFrame, temporada: str, temporada_feb: str, acta: dict
) -> None:
    eficiencia = m.eficiencia_ro(filtrat)

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Punts que ens fan de segona",
        eficiencia["punts_rival"],
        delta=f"sostre {eficiencia['potencial_rival']}",
        delta_color="off",
    )
    col2.metric("Aprofitament del rival", f"{eficiencia['aprofitament_rival']:.1f}%")
    col3.metric("Punts per RO del rival", f"{eficiencia['punts_per_ro_rival']:.2f}")
    st.caption(
        f"Del PBP. Segons l'acta, el rival agafa {acta['ro_rival']} rebots ofensius contra "
        f"nosaltres i en captura el {acta['orb_rival']:.1f}% dels disponibles."
    )

    st.divider()
    esquerra, dreta = st.columns([1, 1])

    with esquerra:
        st.subheader("Quantes RD agafa cada jugadora")
        _rebots_de_lacta(boxscore, temporada, temporada_feb, columna="RD", etiqueta="rebots defensius")

    with dreta:
        st.subheader("Quants RO ens agafen amb cada jugadora a la pista")
        st.caption(
            "Del PBP. La columna per 100 jugades és la que val: una jugadora amb el doble de "
            "minuts sortiria automàticament com la pitjor en el total."
        )
        taula = m.rebots_per_jugadora_en_pista(filtrat, columna="RO en contra")
        if taula.empty:
            st.info("Cap jornada amb `RO en contra` anotat als filtres actuals.")
        else:
            st.dataframe(
                taula.sort_values("RO en contra per 100 jugades", ascending=True, ignore_index=True),
                width="stretch",
                hide_index=True,
            )


def _rebots_de_lacta(
    boxscore: pd.DataFrame,
    temporada: str,
    temporada_feb: str,
    columna: str,
    etiqueta: str,
) -> None:
    """Rebots per jugadora segons l'acta oficial (que sí sap qui els agafa)."""
    plantilla = jug.plantilla_oficial(boxscore, temporada_feb)
    if plantilla.empty or columna not in plantilla.columns:
        st.warning(
            f"Encara no hi ha actes descarregades de {temporada}. Sense elles no se sap "
            "quina jugadora agafa cada rebot.",
            icon="⚠️",
        )
        return

    taula = plantilla[["Jugadora", columna, "MIN"]].copy()
    taula = taula[taula[columna] > 0]
    if taula.empty:
        st.info(f"Cap {etiqueta} anotat a l'acta.")
        return

    # Tres decimals i no dos: els valors reals van de 0.02 a 0.14 per minut, i
    # amb dos decimals mitja plantilla quedaria empatada.
    taula[f"{columna} per minut"] = (taula[columna] / taula["MIN"]).round(3)
    taula["MIN"] = taula["MIN"].round(0).astype(int)
    taula = taula.sort_values(columna, ascending=False, ignore_index=True)

    st.plotly_chart(
        grafics.barres_recompte(
            taula,
            columna_etiqueta="Jugadora",
            columna_valor=columna,
            titol=f"{etiqueta.capitalize()} per jugadora (acta oficial)",
        ),
        width="stretch",
        key=f"reb_acta_{columna}_{temporada}",
    )
    st.dataframe(taula, width="stretch", hide_index=True)
