# -*- coding: utf-8 -*-
"""
Descàrrega del repo privat de dades (`basket-almeda-analytics-dades`) via
l'API de GitHub, per reconstruir a l'arrel del projecte l'estructura que
`config.py` espera trobar (`<temporada>/data/pbp/*.xlsx`, `dades/lf2.sqlite`...).

Sense imports de Streamlit a propòsit (vegeu la nota d'arquitectura a
CLAUDE.md): aquest mòdul és pur Python, reutilitzable des d'un script o test.
Qui llegeix `st.secrets` és `app/_dades_remot.py`, que crida `descarrega()`.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import requests


class ErrorDescarregaDades(Exception):
    """El repo privat de dades no s'ha pogut descarregar."""


def descarrega(token: str, repo: str, desti: Path, ref: str = "main") -> None:
    """Descarrega `repo` (p. ex. "annaferrerrav/basket-almeda-analytics-dades")
    i n'extreu el contingut a `desti`, sobreescrivint el que hi trobi.

    Fa servir l'endpoint de tarball de l'API de GitHub amb el `token` a la
    capçalera d'autorització — mai en una URL, perquè no quedi en cap log.
    """
    url = f"https://api.github.com/repos/{repo}/tarball/{ref}"
    resposta = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    if resposta.status_code != 200:
        raise ErrorDescarregaDades(
            f"GitHub ha respost {resposta.status_code} descarregant {repo}. "
            "Comprova que el token és vàlid i té accés de lectura a aquest repo."
        )

    desti.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(resposta.content), mode="r:gz") as tar:
        for membre in tar.getmembers():
            if not membre.isfile():
                continue
            # El tarball de GitHub arrela tot sota "<owner>-<repo>-<sha>/";
            # cal treure aquest primer component per recuperar les rutes
            # relatives reals ("dades/lf2.sqlite", "25-26/data/pbp/...").
            parts = Path(membre.name).parts[1:]
            if not parts:
                continue
            ruta_relativa = Path(*parts)
            ruta_final = desti / ruta_relativa
            ruta_final.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(membre) as origen, open(ruta_final, "wb") as sortida:
                sortida.write(origen.read())
