# -*- coding: utf-8 -*-
"""
Developer · Scraper PBP.

Genera el PBP d'un partit a partir de la seva URL de baloncestoenvivo.feb.es,
sabent que l'equip que s'analitza sempre és el BASKET ALMEDA.

NOMÉS funciona en local: crida per subprocess `feb_pbp_to_excel.py`, que obre
un Chromium real amb Playwright. No té sentit desplegar aquesta pàgina a
Streamlit Cloud (no hi ha navegador) — és per això que viu a la secció
«Developer», no a cap de les temporades.

El fitxer generat es desa a `dades/pbp_desenvolupament/`, FORA de qualsevol
carpeta `*/data/pbp/`, així que l'app no el recull automàticament. Cal
revisar-lo i moure'l a mà a `26-27/data/pbp/` quan es doni per bo.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from _comuns import capcalera

from almeda_pbp import config as cfg, dev_scraper, metriques as m

EQUIP = "BASKET ALMEDA"
ALIASES_PER_DEFECTE = dev_scraper.ARREL_SCRAPING_PBP / "aliases_almeda_2627.json"


def pagina() -> None:
    capcalera(
        "🛠️ Developer · Scraper PBP",
        f"Genera el PBP d'un partit a partir de la URL. Equip analitzat: **{EQUIP}**.",
    )

    st.info(
        "Fa servir Playwright amb un Chromium real (com quan l'executes per terminal): "
        "triga 30-90 segons i **només funciona en aquest ordinador**, no a Streamlit Cloud.",
        icon="🖥️",
    )

    with st.form("form_scraper"):
        url = st.text_input(
            "URL del partit",
            placeholder="https://baloncestoenvivo.feb.es/partido/XXXXXXX",
            help="La pàgina del partit a baloncestoenvivo.feb.es, no la del boxscore ni la del calendari.",
        )
        columnes = st.columns(2)
        jornada = columnes[0].number_input("Jornada", min_value=1, max_value=40, value=1, step=1)
        ruta_aliases = columnes[1].text_input(
            "Fitxer d'àlies",
            value=str(ALIASES_PER_DEFECTE),
            help="Es crea buit (`{}`) si encara no existeix. Els noms que no hi surtin es queden amb "
            "l'àlies genèric del script (normalment cognom).",
        )
        nom_sortida = st.text_input(
            "Nom del fitxer de sortida",
            value=f"j{int(jornada)}-pbp-dev.xlsx",
            help=f"Es desa a `{dev_scraper.CARPETA_ESBORRANYS}/`, no a la carpeta oficial de la temporada.",
        )
        enviat = st.form_submit_button("Generar PBP", type="primary")

    aliases_path = Path(ruta_aliases) if ruta_aliases else ALIASES_PER_DEFECTE
    if aliases_path.exists():
        contingut = dev_scraper.llegeix_aliases(aliases_path)
        st.caption(f"📇 `{aliases_path.name}` ja té {len(contingut)} àlies definits.")
    else:
        st.caption(f"📇 `{aliases_path.name}` encara no existeix — es crearà buit en generar el primer PBP.")

    if enviat:
        if not url.strip():
            st.error("Falta la URL del partit.")
            st.stop()

        creat = dev_scraper.assegura_aliases(aliases_path)
        if creat:
            st.info(f"S'ha creat `{aliases_path}` buit (`{{}}`).", icon="📄")

        sortida = dev_scraper.CARPETA_ESBORRANYS / (nom_sortida or f"j{int(jornada)}-pbp-dev.xlsx")

        with st.spinner("Obrint el partit i extraient el PBP... (30-90 s)"):
            resultat = dev_scraper.genera_pbp(
                url=url.strip(),
                jornada=int(jornada),
                aliases=aliases_path,
                sortida=sortida,
                equip=EQUIP,
            )

        st.session_state["dev_resultat"] = resultat
        st.session_state["dev_generat_el"] = datetime.now()

    resultat = st.session_state.get("dev_resultat")
    if resultat is None:
        return

    st.divider()

    if resultat.ok:
        st.success(f"PBP generat: `{resultat.fitxer}`")
    else:
        st.error(
            "L'script no ha generat cap Excel. Sovint és perquè el marcador reconstruït no coincideix "
            "amb l'oficial (el propi script s'atura per no crear un fitxer incorrecte)."
        )

    with st.expander("Sortida de la consola", expanded=not resultat.ok):
        st.caption("Ordre executada:")
        st.code(resultat.ordre, language="bash")
        if resultat.sortida_consola:
            st.text(resultat.sortida_consola)
        if resultat.error_consola:
            st.caption("Sortida d'error:")
            st.text(resultat.error_consola)

    if not resultat.ok or resultat.fitxer is None:
        return

    # --- Previsualització: llegim el fitxer que acabem de generar tal com ho
    # faria l'app, per veure de seguida si l'extracció sembla correcta. Com
    # que és un sol partit sense sistema anotat, no té sentit passar-lo per
    # carrega.carrega_pbp() sencer (que llegeix TOTS els fitxers de la
    # temporada) — es llegeix i es normalitza aquest sol fitxer.
    st.subheader("Previsualització")
    try:
        df = pd.read_excel(resultat.fitxer)
    except Exception as err:
        st.warning(f"El fitxer s'ha creat però no s'ha pogut rellegir per previsualitzar-lo: {err}")
        return

    resum = m.resum_general(df.assign(**{cfg.COL_JORNADA: int(jornada)}))
    columnes = st.columns(4)
    columnes[0].metric("Jugades", resum["jugades"])
    columnes[1].metric("Punts a favor", resum["punts"])
    columnes[2].metric("Punts en contra", resum["punts_rival"])
    columnes[3].metric("Diferencial", resum["punts"] - resum["punts_rival"])

    st.caption(
        "Cap sistema anotat (font automàtica): normal, encara no s'ha etiquetat a mà. "
        "Revisa sobretot que els noms de `jug 1`..`jug 5` tinguin sentit i que hi hagi "
        "substitucions al llarg del partit — si una posició és sempre la mateixa jugadora, "
        "l'extracció probablement ha fallat en aquest partit."
    )
    st.dataframe(df, width="stretch", hide_index=True)

    with open(resultat.fitxer, "rb") as f:
        st.download_button(
            "Descarregar l'Excel",
            data=f.read(),
            file_name=resultat.fitxer.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    st.caption(
        f"Fitxer a `{resultat.fitxer}`. Quan el donis per bo, mou'l (o copia'l) a "
        "`26-27/data/pbp/` perquè l'app el reculli — aquesta carpeta de desenvolupament "
        "no es llegeix mai automàticament."
    )
