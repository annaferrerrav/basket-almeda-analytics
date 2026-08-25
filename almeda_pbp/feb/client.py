# -*- coding: utf-8 -*-
"""
Client HTTP per a baloncestoenvivo.feb.es.

Fa tres coses que un `requests.get` pelat no fa:
- espera entre peticions (la web és pública i gratuïta: no se l'ha de martellejar),
- reintenta amb espera creixent quan la resposta falla,
- sap fer els *postbacks* d'ASP.NET, que és l'única manera de canviar de grup:
  el paràmetre `c=<grup>` de la URL s'ignora, cal enviar `__VIEWSTATE` i companyia
  per POST.
"""

from __future__ import annotations

import logging
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://baloncestoenvivo.feb.es"

registre = logging.getLogger(__name__)


class ErrorFEB(RuntimeError):
    """La web no ha respost com esperàvem després de tots els reintents."""


class ClientFEB:
    def __init__(self, espera: float = 1.5, reintents: int = 3, timeout: int = 30):
        self.espera = espera
        self.reintents = reintents
        self.timeout = timeout
        self.sessio = requests.Session()
        # User-agent identificable: si algú de la FEB mira els logs, ha de poder
        # veure qui som i que no som un bot anònim.
        self.sessio.headers.update(
            {"User-Agent": "BasketAlmedaAnalytics/1.0 (analista del club; ús intern, no comercial)"}
        )
        self._darrera_peticio = 0.0

    def _frena(self) -> None:
        """Garanteix `espera` segons entre peticions consecutives."""
        transcorregut = time.monotonic() - self._darrera_peticio
        if transcorregut < self.espera:
            time.sleep(self.espera - transcorregut)
        self._darrera_peticio = time.monotonic()

    def _demana(self, metode: str, url: str, **kwargs) -> requests.Response:
        ultim_error: Exception | None = None
        for intent in range(1, self.reintents + 1):
            self._frena()
            try:
                resposta = self.sessio.request(metode, url, timeout=self.timeout, **kwargs)
                resposta.raise_for_status()
                return resposta
            except Exception as err:
                ultim_error = err
                espera = self.espera * 2**intent
                registre.warning("Intent %d/%d ha fallat a %s (%s). Reintento en %.1fs.",
                                 intent, self.reintents, url, err, espera)
                time.sleep(espera)
        raise ErrorFEB(f"No s'ha pogut baixar {url}: {ultim_error}")

    def html(self, url: str, params: dict | None = None) -> str:
        return self._demana("GET", url, params=params).text

    def sopa(self, url: str, params: dict | None = None) -> BeautifulSoup:
        return BeautifulSoup(self.html(url, params), "html.parser")

    def postback(self, url: str, sopa: BeautifulSoup, objectiu: str, valors: dict[str, str]) -> BeautifulSoup:
        """
        Reprodueix un postback d'ASP.NET.

        `sopa` ha de ser la pàgina tal com l'ha servit el GET previ: d'allà surten
        `__VIEWSTATE` i `__EVENTVALIDATION`, que caduquen i no es poden inventar.
        """
        formulari = {
            camp.get("name"): camp.get("value", "")
            for camp in sopa.select("input[type=hidden]")
            if camp.get("name")
        }
        formulari.update(valors)
        formulari["__EVENTTARGET"] = objectiu
        formulari["__EVENTARGUMENT"] = ""

        resposta = self._demana("POST", url, data=formulari)
        return BeautifulSoup(resposta.text, "html.parser")
