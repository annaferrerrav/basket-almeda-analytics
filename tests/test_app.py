# -*- coding: utf-8 -*-
"""
Tests de fum de les pàgines Streamlit.

Cada vista de `app/vistes/` és una funció `pagina(...)`, no un script: es
prova executant-la de debò amb `AppTest.from_string` (no `from_file`, perquè
`app/Inici.py` fa servir `st.navigation` amb pàgines basades en funcions —
`AppTest.switch_page()` només sap navegar per camí de fitxer, no serveix
aquí). Només es comprova que no peti; el contingut ja el cobreixen els tests
de `test_pbp.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ARREL = Path(__file__).resolve().parent.parent
APP = ARREL / "app"

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

TEMPORADES = ["25-26", "26-27"]
VISTES_PER_TEMPORADA = [
    "general", "sistemes", "jugadores", "jornada", "parelles", "rebot", "informe_pdf", "qualitat_dades",
]


def _executa(cos: str, timeout: int = 400):
    script = f'import sys\nsys.path.insert(0, {str(APP)!r})\n{cos}\n'
    return AppTest.from_string(script, default_timeout=timeout).run(timeout=timeout)


@pytest.mark.parametrize("modul", VISTES_PER_TEMPORADA)
@pytest.mark.parametrize("temporada", TEMPORADES)
def test_vista_per_temporada_no_peta(modul, temporada):
    """Cada vista ha de renderitzar sense excepcions, també quan la temporada és buida (26-27)."""
    at = _executa(f"from vistes.{modul} import pagina\npagina({temporada!r})")
    assert [str(e.value) for e in at.exception] == []


def test_dev_scraper_no_peta_sense_enviar():
    at = _executa("from vistes.dev_scraper import pagina\npagina()")
    assert [str(e.value) for e in at.exception] == []


def test_dev_informe_no_peta():
    at = _executa("from vistes.dev_informe import pagina\npagina()")
    assert [str(e.value) for e in at.exception] == []


def test_informe_pdf_genera_i_permet_descarregar():
    """Clic real al botó «Generar l'informe»: exercita informe.genera_informe des de la UI."""
    at = _executa("from vistes.informe_pdf import pagina\npagina('25-26')")
    botons = [b for b in at.button if b.key and b.key.startswith("pdf_generar")]
    assert len(botons) == 1

    botons[0].click().run(timeout=400)
    assert [str(e.value) for e in at.exception] == []
    assert len(at.download_button) == 1


def test_dev_informe_genera_amb_blocs_barrejats():
    """
    Marca un tipus «per sistema» i un «general» i genera: exercita
    genera_informe_a_mida des de la UI real, no només des de Python directe.
    """
    at = _executa("from vistes.dev_informe import pagina\npagina()")

    per_marcar = {"dinf_tipus_donut", "dinf_tipus_pm_individual"}
    trobats = {c.key for c in at.checkbox if c.key in per_marcar}
    assert trobats == per_marcar
    for casella in at.checkbox:
        if casella.key in per_marcar:
            casella.set_value(True)
    at.run(timeout=400)

    botons = [b for b in at.button if b.key == "dinf_generar"]
    assert len(botons) == 1
    botons[0].click().run(timeout=400)

    assert [str(e.value) for e in at.exception] == []
    assert len(at.success) == 1


def test_jugadores_obre_la_fitxa_dune_jugadora():
    """Clic real a «Veure fitxa»: la pàgina ha de passar de la plantilla a la fitxa individual."""
    at = _executa("from vistes.jugadores import pagina\npagina('25-26')")
    if not at.button:
        pytest.skip("Sense PBP de 25-26 carregat.")

    botons = [b for b in at.button if b.key and b.key.startswith("btn_fitxa_25-26_")]
    assert botons, "La plantilla hauria de tenir un botó per jugadora."

    at = botons[0].click().run(timeout=400)
    assert [str(e.value) for e in at.exception] == []
    assert any(b.key == "btn_torna_25-26" for b in at.button), "La fitxa ha de portar el botó de tornar."

    # I s'ha de poder tornar enrere sense petar.
    at = at.button(key="btn_torna_25-26").click().run(timeout=400)
    assert [str(e.value) for e in at.exception] == []


def test_general_amb_un_rival_intercalat():
    """Triar un rival afegeix una tercera fila a la tira; no ha de petar."""
    at = _executa("from vistes.general import pagina\npagina('25-26')")
    seleccionables = [s for s in at.selectbox if s.key == "bx_rival__25-26"]
    if not seleccionables:
        pytest.skip("Sense boxscores de 25-26 descarregats.")

    opcions = seleccionables[0].options
    if len(opcions) < 2:
        pytest.skip("Cap rival disponible per intercalar.")

    at = seleccionables[0].select(opcions[1]).run(timeout=400)
    assert [str(e.value) for e in at.exception] == []


def test_jornada_ensenya_un_partit_amb_sistemes():
    """La vista per jornada ha de muntar el partit sencer en triar-ne un amb sistemes."""
    at = _executa("from vistes.jornada import pagina\npagina('25-26')")
    assert [str(e.value) for e in at.exception] == []

    seleccionables = [s for s in at.selectbox if s.key == "jornada_sel__25-26"]
    if not seleccionables:
        pytest.skip("Sense partits de 25-26.")
    if not any(o.startswith("J25 ") for o in seleccionables[0].options):
        pytest.skip("La jornada 25 no hi és.")

    # Es tria escrivint al session_state i no amb `.select()`: `AppTest` compara
    # el valor triat contra les etiquetes ja formatades pel `format_func`, i amb
    # un format_func que converteix l'enter 25 en "J25 · ..." la comparació peta.
    at.session_state["jornada_sel__25-26"] = 25
    at = at.run(timeout=400)

    assert [str(e.value) for e in at.exception] == []
    assert {"Acta oficial", "Sistemes", "+/- del partit"} <= {x.value for x in at.subheader}
    # Acta + taula de sistemes.
    assert len(at.dataframe) >= 2
