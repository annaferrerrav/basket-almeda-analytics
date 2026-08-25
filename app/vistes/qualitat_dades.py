# -*- coding: utf-8 -*-
"""
Qualitat de dades.

Aquesta pàgina existeix perquè el PBP s'omple a mà (o es genera automàticament
a partir del feed de la FEB) i sempre hi ha errades. Cap valor estrany
s'arregla sol: es llista aquí perquè l'analista decideixi. Si un valor apareix
com a "no reconegut", el que toca és o corregir l'Excel o afegir-lo al
diccionari d'àlies de `almeda_pbp/normalitza.py`.
"""

from __future__ import annotations

import streamlit as st

from _comuns import capcalera, carrega_dades

from almeda_pbp import carrega, config as cfg


def pagina(temporada: str) -> None:
    dades, incidencies = carrega_dades()

    capcalera(
        f"🔎 Qualitat de dades · {temporada}",
        "Tot el que la càrrega ha trobat estrany. Res s'ha corregit automàticament.",
    )

    incidencies_temporada = incidencies[incidencies["Temporada"] == temporada]
    veure_totes = st.toggle(
        "Veure totes les temporades",
        key=f"qual_totes__{temporada}",
        help="Per defecte només es mostren les incidències d'aquesta temporada.",
    )
    taula_incidencies = incidencies if veure_totes else incidencies_temporada

    if taula_incidencies.empty:
        st.success("Cap incidència detectada.")
    else:
        tipus = sorted(taula_incidencies["Tipus"].unique())
        seleccio = st.multiselect("Filtra per tipus", tipus, default=tipus, key=f"qual_tipus__{temporada}")
        st.dataframe(
            taula_incidencies[taula_incidencies["Tipus"].isin(seleccio)],
            width="stretch",
            hide_index=True,
        )

        st.caption(
            "**Com llegir-ho** · *Tàctica/Desenllaç no reconegut*: el valor s'ha conservat tal qual i "
            "surt als gràfics amb color neutre; afegeix-lo als àlies o corregeix l'Excel. "
            "*Sense sistemes*: font automàtica (feed de la FEB) sense el sistema de joc anotat; compta "
            "per a tot excepte les pàgines de sistemes. *Quintet no fiable*: cap substitució detectada "
            "en un fitxer llarg, es descarta el quintet d'aquell fitxer (+/-, parelles, jugadora×posició) "
            "però es manté la resta. *Marcador descuadrat*: la suma de PF/PC no coincideix amb el "
            "marcador acumulat del propi fitxer. *Jornada incoherent*: el número de jornada del nom del "
            "fitxer i el de la columna no coincideixen; mana el del nom del fitxer. *Jornada descartada*: "
            "el fitxer no té res anotat i no s'ha carregat."
        )

    st.divider()
    st.subheader("Fitxers trobats")

    fitxers = carrega.descobreix_fitxers(cfg.ARREL)
    if not veure_totes:
        fitxers = [f for f in fitxers if f[0] == temporada]
    carregades = set(zip(dades[cfg.COL_TEMPORADA], dades[cfg.COL_JORNADA])) if not dades.empty else set()
    st.dataframe(
        [
            {
                "Temporada": temp,
                "Jornada": jornada,
                "Fitxer": ruta.name,
                "Carregat": "sí" if (temp, jornada) in carregades else "no",
            }
            for temp, jornada, ruta in fitxers
        ],
        width="stretch",
        hide_index=True,
    )

    st.divider()
    st.subheader("Columnes extres detectades")
    st.caption(
        "Algunes jornades porten un bloc defensiu (`Tàctica defensiva`, `Desenllaç`, `punts`) que "
        "només està omplert a mitges i que ara mateix l'app **no analitza**. Si el vols recuperar, "
        "cal decidir abans si aquelles files són possessions defensives independents o van aparellades "
        "a les ofensives de la mateixa fila."
    )
    extres = [c for c in cfg.COLS_DEFENSIVES if c in dades.columns]
    st.write(", ".join(f"`{c}`" for c in extres) if extres else "Cap.")
