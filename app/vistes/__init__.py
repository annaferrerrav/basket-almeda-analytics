# -*- coding: utf-8 -*-
"""
Vistes de l'app: una funció `pagina(temporada)` per mòdul.

Cada mòdul és el cos d'una pàgina antiga (`app/pages/*.py`), convertit de
script a funció perquè `app/Inici.py` en pugui muntar DUES instàncies a la
navegació — una per «Temporada 25-26» i una per «Temporada 26-27» — sense
duplicar el fitxer. Res aquí crida `st.set_page_config`: això només es pot
fer un cop, i viu a `Inici.py`.
"""
