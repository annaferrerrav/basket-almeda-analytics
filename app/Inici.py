# -*- coding: utf-8 -*-
"""
Punt d'entrada de l'app: navegació per seccions.

- «Temporada 2025-26» i «Temporada 2026-27 (actual)»: el mateix joc de
  pàgines, cadascuna bloquejada a la seva temporada (vegeu `vistes/*.py`,
  cada mòdul exposa `pagina(temporada)` i aquí només se n'instancia una
  còpia per temporada amb `functools.partial`, sense duplicar cap fitxer).
- «Developer»: eines locals de l'analista (scraping puntual d'un partit i
  constructor lliure de PDF). NOMÉS funcionen en aquest ordinador — no es
  desplegaran a Streamlit Cloud.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import streamlit as st

# app/ ha d'estar a sys.path perquè "from _comuns import ..." funcioni dins
# de vistes/*.py. Streamlit ja ho fa sol per a l'script principal, però aquí
# ho garantim explícitament perquè els mòduls de vistes/ no depenguin d'un
# detall no documentat de Streamlit.
ARREL_APP = Path(__file__).resolve().parent
if str(ARREL_APP) not in sys.path:
    sys.path.insert(0, str(ARREL_APP))

# I l'arrel del repo perquè "import almeda_pbp" funcioni. En local colava
# sense això només perquè el directori de treball (l'arrel, des d'on es fa
# `streamlit run app/Inici.py`) acaba a sys.path; a Streamlit Cloud això no
# es pot donar per fet, i sense aquesta línia l'app peta a l'arrencada.
ARREL_REPO = ARREL_APP.parent
if str(ARREL_REPO) not in sys.path:
    sys.path.insert(0, str(ARREL_REPO))

st.set_page_config(page_title="Basket Almeda", page_icon="🏀", layout="wide")

from vistes import (  # noqa: E402
    dev_informe,
    dev_scraper,
    general,
    informe_pdf,
    jornada,
    jugadores,
    parelles,
    qualitat_dades,
    rebot,
    sistemes,
)
from almeda_pbp import config as cfg  # noqa: E402


def _pagines_temporada(temporada: str) -> list[st.Page]:
    """Un joc complet de pàgines, totes bloquejades a `temporada`."""
    return [
        st.Page(functools.partial(general.pagina, temporada), title="General", icon="🏀", url_path=f"general-{temporada}"),
        st.Page(functools.partial(sistemes.pagina, temporada), title="Sistemes", icon="🥧", url_path=f"sistemes-{temporada}"),
        st.Page(functools.partial(jugadores.pagina, temporada), title="Jugadores", icon="👥", url_path=f"jugadores-{temporada}"),
        st.Page(functools.partial(jornada.pagina, temporada), title="Per jornada", icon="📋", url_path=f"jornada-{temporada}"),
        st.Page(functools.partial(parelles.pagina, temporada), title="+/-", icon="➕", url_path=f"mesmenys-{temporada}"),
        st.Page(functools.partial(rebot.pagina, temporada), title="Rebot", icon="🔁", url_path=f"rebot-{temporada}"),
        st.Page(functools.partial(informe_pdf.pagina, temporada), title="Informe PDF", icon="📄", url_path=f"informe-{temporada}"),
        st.Page(functools.partial(qualitat_dades.pagina, temporada), title="Qualitat de dades", icon="🔎", url_path=f"qualitat-{temporada}"),
    ]


# Les seccions de temporada surten de config.TEMPORADES: afegir una
# temporada nova és afegir-hi una entrada, no tocar aquest fitxer.
seccions = {f"Temporada {t['etiqueta']}": _pagines_temporada(t["pbp"]) for t in cfg.TEMPORADES}
# La secció Developer només s'afegeix a la màquina de l'analista (vegeu
# `cfg.mode_dev()`): al núvol serien dues pàgines trencades a la vista del
# cos tècnic, perquè depenen de Playwright i d'escriure al disc local.
if cfg.mode_dev():
    seccions["Developer"] = [
        st.Page(dev_scraper.pagina, title="Scraper PBP", icon="🛠️", url_path="dev-scraper"),
        st.Page(dev_informe.pagina, title="Informe a mida", icon="🧩", url_path="dev-informe"),
    ]

navegacio = st.navigation(seccions)
navegacio.run()
