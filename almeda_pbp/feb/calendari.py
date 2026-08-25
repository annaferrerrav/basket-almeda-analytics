# -*- coding: utf-8 -*-
"""
Calendari: descobreix els partits d'un grup i una jornada.

L'objectiu és no haver d'enganxar cap URL a mà. Es demana el calendari del grup i
se'n treuen els identificadors de partit, els equips i el resultat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .client import BASE, ClientFEB, ErrorFEB

# Identificadors de la competició a la web de la FEB.
COMPETICIO_LF2 = 9
# Ull: `t` és l'any d'INICI de temporada. t=2025 -> 2025/26, t=2026 -> 2026/27.
URL_CALENDARI = f"{BASE}/calendario.aspx"

DESPLEGABLE_TEMPORADA = "_ctl0:MainContentPlaceHolderMaster:temporadasDropDownList"
DESPLEGABLE_GRUP = "_ctl0:MainContentPlaceHolderMaster:gruposDropDownList"

_PATRO_JORNADA = re.compile(r"Jornada\s+(\d+)\s*(\d{2}/\d{2}/\d{4})?", re.IGNORECASE)
_PATRO_PARTIT = re.compile(r"Partido\.aspx\?p=(\d+)", re.IGNORECASE)


@dataclass
class Partit:
    lliga: str
    jornada: int
    partit_id: int
    equip_local: str
    equip_visitant: str
    resultat: str | None
    data_jornada: str | None

    @property
    def url(self) -> str:
        return f"{BASE}/Partido.aspx?p={self.partit_id}"


def _lletra_del_grup(etiqueta: str) -> str:
    """De 'Liga Regular "A"' en treu 'A'. Si no hi ha cometes, agafa l'etiqueta."""
    trobat = re.search(r'"([^"]+)"', etiqueta)
    return (trobat.group(1) if trobat else etiqueta).strip()


def grups(client: ClientFEB, temporada: int, competicio: int = COMPETICIO_LF2) -> dict[str, str]:
    """
    Retorna {lletra_del_grup: id_intern}, p. ex. {'A': '88868', 'B': '88869'}.

    Els identificadors canvien cada temporada, així que mai s'han de fixar al codi:
    es llegeixen del desplegable.
    """
    sopa = client.sopa(URL_CALENDARI, {"g": competicio, "t": temporada, "nm": "lf2"})
    desplegable = sopa.find("select", id=lambda v: v and "gruposDropDownList" in v)
    if desplegable is None:
        raise ErrorFEB("No s'ha trobat el desplegable de grups al calendari.")

    trobats = {}
    for opcio in desplegable.find_all("option"):
        valor = opcio.get("value")
        if valor:
            trobats[_lletra_del_grup(opcio.get_text(strip=True))] = valor
    if not trobats:
        raise ErrorFEB("El desplegable de grups és buit.")
    return trobats


def _sopa_del_grup(client: ClientFEB, temporada: int, grup_id: str, competicio: int) -> BeautifulSoup:
    """
    Carrega el calendari d'un grup concret.

    El primer grup del desplegable ja ve servit pel GET; per a la resta cal el
    postback, perquè afegir `&c=<grup>` a la URL no fa res (provat: retorna
    sempre el grup per defecte).
    """
    parametres = {"g": competicio, "t": temporada, "nm": "lf2"}
    sopa = client.sopa(URL_CALENDARI, parametres)

    desplegable = sopa.find("select", id=lambda v: v and "gruposDropDownList" in v)
    seleccionat = desplegable.find("option", selected=True) if desplegable else None
    if seleccionat is not None and seleccionat.get("value") == grup_id:
        return sopa

    url = f"{URL_CALENDARI}?g={competicio}&t={temporada}&nm=lf2"
    return client.postback(
        url,
        sopa,
        objectiu=DESPLEGABLE_GRUP,
        valors={DESPLEGABLE_TEMPORADA: str(temporada), DESPLEGABLE_GRUP: grup_id},
    )


def partits(
    client: ClientFEB,
    temporada: int,
    lliga: str,
    grup_id: str,
    jornades: list[int] | None = None,
    competicio: int = COMPETICIO_LF2,
) -> list[Partit]:
    """Llista els partits d'un grup, opcionalment només de certes jornades."""
    sopa = _sopa_del_grup(client, temporada, grup_id, competicio)
    volgudes = set(jornades) if jornades else None
    resultat: list[Partit] = []

    for titol in sopa.find_all("h1", class_="titulo-modulo"):
        capcalera = _PATRO_JORNADA.search(titol.get_text(" ", strip=True))
        if not capcalera:
            continue
        numero = int(capcalera.group(1))
        if volgudes is not None and numero not in volgudes:
            continue

        taula = titol.find_next("table")
        if taula is None:
            continue

        for fila in taula.find_all("tr"):
            cel_resultat = fila.find("td", class_="resultado")
            if cel_resultat is None:
                continue
            enllac = cel_resultat.find("a", href=_PATRO_PARTIT)
            if enllac is None:
                # Partit encara no jugat: no té enllaç, i per tant no té boxscore.
                continue

            local = fila.find("td", class_="equipo local")
            visitant = fila.find("td", class_="equipo visitante")
            resultat.append(
                Partit(
                    lliga=lliga,
                    jornada=numero,
                    partit_id=int(_PATRO_PARTIT.search(enllac["href"]).group(1)),
                    equip_local=local.get_text(" ", strip=True) if local else "",
                    equip_visitant=visitant.get_text(" ", strip=True) if visitant else "",
                    resultat=enllac.get_text(strip=True) or None,
                    data_jornada=capcalera.group(2),
                )
            )

    return resultat
