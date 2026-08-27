# -*- coding: utf-8 -*-
"""
Garanteix que les dades privades (PBP, boxscores, SQLite) siguin al disc
abans que cap vista les llegeixi.

En local ja hi són (l'analista treballa amb els fitxers directament, com
sempre), així que `assegura_dades()` no fa res. A Streamlit Cloud el repo
públic no les conté (vegeu README.md > "Desplegament a Streamlit Cloud"):
la primera vegada que arrenca el contenidor, aquesta funció les descarrega
del repo privat `basket-almeda-analytics-dades` fent servir un token de
només lectura guardat als secrets de l'app, mai al codi.

`st.cache_resource` fa que la descàrrega passi un sol cop per contenidor,
no a cada rerun de l'script (que Streamlit fa constantment).
"""

from __future__ import annotations

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from almeda_pbp import config as cfg
from almeda_pbp import sync_dades

REPO_DADES_PER_DEFECTE = "annaferrerrav/basket-almeda-analytics-dades"

# Sentinella: si aquest fitxer ja hi és, les dades ja estan al disc
# (desenvolupament local, o contenidor que ja ha descarregat abans).
_FITXER_SENTINELLA = cfg.ARREL / "dades" / "lf2.sqlite"


@st.cache_resource(show_spinner=False)
def assegura_dades() -> None:
    if _FITXER_SENTINELLA.exists():
        return

    # st.secrets es comporta com un dict, però si no hi ha CAP secrets.toml
    # configurat ("app/Inici.py" sense .streamlit/secrets.toml enlloc), fins
    # i tot el simple "in" llança StreamlitSecretNotFoundError en lloc de
    # donar False — cal capturar-ho a part de l'absència de la clau.
    try:
        token = st.secrets["dades_github_token"]
    except (KeyError, StreamlitSecretNotFoundError):
        st.error(
            "Falten les dades i no hi ha cap token configurat per descarregar-les "
            "(`dades_github_token` als secrets de l'app). Vegeu la secció "
            "\"Desplegament a Streamlit Cloud\" del README."
        )
        st.stop()
        return

    repo = st.secrets.get("dades_repo", REPO_DADES_PER_DEFECTE)

    with st.spinner("Descarregant dades..."):
        try:
            sync_dades.descarrega(token=token, repo=repo, desti=cfg.ARREL)
        except sync_dades.ErrorDescarregaDades as exc:
            st.error(f"No s'han pogut descarregar les dades: {exc}")
            st.stop()
