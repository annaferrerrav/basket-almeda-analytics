# -*- coding: utf-8 -*-
"""
Peces compartides per totes les pàgines: càrrega amb cache i barra de filtres.

Els filtres viuen aquí i no a cada pàgina perquè es comportin igual arreu: si
canvies de pàgina, la selecció es manté (Streamlit la guarda al session_state
per la clau del widget).
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# El paquet almeda_pbp viu al directori pare de app/.
ARREL = Path(__file__).resolve().parent.parent
if str(ARREL) not in sys.path:
    sys.path.insert(0, str(ARREL))

from almeda_pbp import carrega, config as cfg, etiquetes as etq, magatzem  # noqa: E402


@st.cache_data(show_spinner="Llegint els PBP...")
def carrega_dades() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Llegeix tots els Excel un sol cop per sessió. Retorna (dades, incidències)."""
    resultat = carrega.carrega_pbp(ARREL)
    return resultat.dades, resultat.taula_incidencies


@st.cache_data(show_spinner="Llegint les etiquetes...")
def carrega_etiquetes() -> dict[str, list[str]]:
    """{sistema: [etiquetes]} del TOML. Buit si encara no s'ha generat."""
    return etq.carrega_etiquetes(ARREL)


@st.cache_data(show_spinner="Llegint els boxscores...")
def carrega_boxscore() -> pd.DataFrame:
    """Boxscores oficials descarregats de la FEB. Buit si encara no s'ha scrapejat."""
    return magatzem.carrega_boxscore()


def capcalera(titol: str, subtitol: str = "") -> None:
    """
    Títol de pàgina.

    Es dibuixa a mà i no amb `st.title`/`st.header`: els dos són massa grans
    per a pàgines que ja porten mètriques i filtres a sobre de tot: el títol es
    menjava mitja pantalla abans d'ensenyar cap dada.
    """
    st.markdown(
        f'<div style="font-size:1.45rem;font-weight:700;line-height:1.25;'
        f'margin:0 0 .15rem 0;">{html.escape(titol)}</div>',
        unsafe_allow_html=True,
    )
    if subtitol:
        st.caption(subtitol)


def barra_filtres(df: pd.DataFrame, temporada_fixada: str | None = None) -> pd.DataFrame:
    """
    Dibuixa els filtres a la barra lateral i retorna el DataFrame filtrat.

    Un filtre que deixa el conjunt buit no és un error: es retorna buit i cada
    gràfic ja ensenya un missatge explicant-ho.

    `temporada_fixada`: quan es dona (les pàgines de secció "Temporada 25-26"
    / "Temporada 26-27" sempre el donen), no es mostra el selector de
    temporada — la pàgina només treballa amb aquesta. Si aquesta temporada
    encara no té cap fitxer carregat (típic de 26-27 a l'inici de curs), es
    retorna un DataFrame buit en comptes d'un error.
    """
    st.sidebar.header("Filtres")

    if df.empty:
        st.sidebar.info("Cap dada carregada.")
        return df

    temporades = sorted(df[cfg.COL_TEMPORADA].unique())

    if temporada_fixada is not None:
        temporada = temporada_fixada
        st.sidebar.caption(f"📅 Temporada **{temporada}**")
        if temporada not in temporades:
            st.sidebar.info(f"Encara no hi ha PBP carregat de la temporada {temporada}.")
            return df.iloc[0:0]
    else:
        temporada = st.sidebar.selectbox("Temporada", temporades, index=len(temporades) - 1, key="f_temporada")

    # Sufix per aïllar l'estat dels widgets entre temporades: sense això,
    # canviar de "Temporada 25-26" a "Temporada 26-27" a la navegació
    # arrossegaria la jornada/jugadora seleccionades d'una temporada a
    # l'altra, on ni tan sols existeixen. Dins d'una mateixa temporada els
    # filtres SÍ es mantenen en canviar de pàgina (és la intenció original).
    sufix = f"__{temporada}"

    st.session_state["f_temporada"] = temporada
    treball = df[df[cfg.COL_TEMPORADA] == temporada]

    jornades = sorted(treball[cfg.COL_JORNADA].dropna().unique().tolist())
    seleccio_jornades = st.sidebar.multiselect(
        "Jornades",
        jornades,
        default=jornades,
        key="f_jornades" + sufix,
        help="Buit = totes. Les jornades sense fitxer PBP no hi surten.",
    )

    periodes = sorted(treball[cfg.COL_PERIODE].dropna().unique().tolist())
    seleccio_periodes = st.sidebar.multiselect(
        "Períodes", periodes, default=[], key="f_periodes" + sufix, help="Buit = tots."
    )

    jugadores = carrega.jugadores_disponibles(treball)
    seleccio_jugadores = st.sidebar.multiselect(
        "Jugadores", jugadores, default=[], key="f_jugadores" + sufix, help="Buit = totes."
    )
    mode = st.sidebar.radio(
        "Com filtrar per jugadora",
        ["a pista", "protagonista"],
        key="f_mode" + sufix,
        horizontal=True,
        help=(
            "«a pista»: jugades on la jugadora era una de les cinc en pista "
            "(mesura com va l'equip amb ella). «protagonista»: jugades on va "
            "finalitzar o assistir (mesura què fa ella)."
        ),
        disabled=not seleccio_jugadores,
    )

    tactiques = sorted(treball[cfg.COL_TACTICA].dropna().unique().tolist())
    seleccio_tactiques = st.sidebar.multiselect(
        "Sistemes", tactiques, default=[], key="f_tactiques" + sufix, help="Buit = tots."
    )

    filtrat = carrega.filtra(
        treball,
        jornades=seleccio_jornades or None,
        jugadores=seleccio_jugadores or None,
        tactiques=seleccio_tactiques or None,
        periodes=seleccio_periodes or None,
        mode_jugadora=mode,
    )

    st.sidebar.divider()
    st.sidebar.metric("Jugades seleccionades", f"{len(filtrat):,}".replace(",", "."))
    if st.sidebar.button("Rellegir els Excel", help="Buida la cache i torna a llegir els fitxers del disc.", key="reeleg" + sufix):
        st.cache_data.clear()
        st.rerun()

    return filtrat


def avis_mostra(n: int, llindar: int = 30) -> None:
    """Avisa quan la mostra és massa petita per treure'n conclusions."""
    if 0 < n < llindar:
        st.warning(
            f"Només {n} jugades amb aquests filtres. Els percentatges i el +/- són "
            "molt inestables amb tan poca mostra: mira-t'ho com a descriptiu, no com a tendència."
        )


# --- Caixes de mètriques compactes -----------------------------------------
# Fetes en HTML/CSS en comptes de st.metric perquè st.metric és massa gran per
# encabir-ne moltes en una sola línia.
#
# Streamlit NO exposa el tema actiu com a variables CSS ni com a atribut
# `data-theme` (s'ha comprovat als paquets JS del propi Streamlit: no n'hi ha
# cap) — ho pinta tot amb CSS-in-JS intern. Per tant aquí es fan servir els
# colors per DEFECTE de Streamlit (clar i fosc), fixats a mà, amb
# `@media (prefers-color-scheme: dark)` per triar-los: és exactament el que fa
# el propi Streamlit quan no se li ha fixat un tema per configuració. Si
# l'analista defineix un tema personalitzat a `.streamlit/config.toml`, les
# caixes deixaran de coincidir exactament amb el fons de l'app.

_ESTIL_CAIXES = """
<style>
.pbp-fila { display:flex; flex-wrap:nowrap; gap:5px; overflow-x:auto; padding:1px 1px 6px 1px; }
.pbp-caixa {
  flex:0 0 auto; min-width:56px; padding:4px 8px; border-radius:7px;
  background:#f0f2f6; border:1px solid rgba(49,51,63,.18);
  text-align:center; line-height:1.15;
  /* Alçada fixa: totes les files han de fer el mateix alt encara que la de
     dalt no porti delta, o la columna d'etiquetes de l'esquerra deixaria de
     quadrar amb les files a les quals posa nom. */
  min-height:46px; display:flex; flex-direction:column; justify-content:center;
}
.pbp-caixa .lbl {
  font-size:9px; font-weight:600; letter-spacing:.03em; text-transform:uppercase;
  color:#31333F; opacity:.6; white-space:nowrap;
}
.pbp-caixa .val { font-size:14px; font-weight:700; color:#31333F; white-space:nowrap; margin-top:1px; }
.pbp-caixa .dlt { font-size:9.5px; font-weight:700; white-space:nowrap; margin-top:1px; min-height:11px; }
.pbp-caixa.factor { background:rgba(42,120,214,.12); border-color:rgba(42,120,214,.45); }
.pbp-caixa.factor .lbl { color:#2a78d6; opacity:1; }
.pbp-titol-bloc {
  font-size:11.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em;
  color:#31333F; opacity:.65; margin:8px 0 2px 0;
}
.pbp-titol-bloc.factor { color:#2a78d6; opacity:.95; }
.pbp-titol-bloc .nota { font-weight:400; text-transform:none; letter-spacing:0; opacity:.7; font-size:10px; margin-left:4px; }

/* Tots els blocs en una sola tira horitzontal: cada bloc és una columna amb
   el títol a dalt, la fila de la lliga al mig i la de l'equip propi a baix.
   La tira fa scroll horizontal en comptes d'ajustar-se, perquè trencar un
   bloc a mitges deixaria les dues files desalineades i la comparació
   dalt/baix és tot el sentit d'aquesta vista. */
.pbp-tira { display:flex; flex-wrap:nowrap; gap:12px; overflow-x:auto; padding:2px 1px 8px 1px; align-items:flex-start; }
.pbp-bloc { flex:0 0 auto; display:flex; flex-direction:column; }
.pbp-bloc + .pbp-bloc { border-left:1px solid rgba(49,51,63,.15); padding-left:12px; }
.pbp-bloc .pbp-fila { overflow:visible; padding:0; margin-bottom:4px; }
.pbp-bloc .pbp-fila:last-child { margin-bottom:0; }
.pbp-bloc .pbp-titol-bloc { margin:0 0 3px 0; }

/* Fila de l'equip propi, en groc, perquè es distingeixi de la mitjana de la
   lliga sense haver de llegir l'etiqueta. El groc canvia de to entre clar i
   fosc pel mateix motiu que el verd/taronja dels deltes: el que contrasta
   sobre #fff no contrasta sobre #262730. */
.pbp-caixa.propi { background:rgba(214,158,0,.16); border-color:rgba(160,116,0,.55); }
.pbp-caixa.propi .lbl { color:#7a5600; opacity:.95; }

/* Fila del rival (opcional). Violeta i no un altre gris: sota simulació de
   deuteranopia/protanopia el groc i el violeta queden a extrems oposats de
   to I de lluminositat, mentre que dos grisos només es distingirien per
   posició. */
.pbp-caixa.rival { background:rgba(140,80,200,.14); border-color:rgba(110,50,175,.5); }
.pbp-caixa.rival .lbl { color:#6b2d99; opacity:.95; }

/* Columna d'etiquetes: diu quina fila és quina sense haver de posar-ho en un
   peu de text. Queda enganxada a l'esquerra en fer scroll horitzontal. */
/* Graella de caixes: les mateixes caixes que la tira, però en N columnes
   d'ample igual. Serveix per posar unes quantes xifres en una columna
   estreta al costat d'un gràfic, on st.metric ocuparia el triple d'alçada. */
.pbp-graella { display:grid; gap:5px; padding:1px 1px 6px 1px; }
.pbp-graella .pbp-caixa { min-width:0; }

/* Variant gran: la mateixa caixa amb la xifra prou llegible per ser la
   capçalera d'una pàgina, no una fila més d'una tira de comparació. */
.pbp-caixa.gran { min-height:62px; padding:6px 10px; }
.pbp-caixa.gran .lbl { font-size:10px; }
.pbp-caixa.gran .val { font-size:24px; line-height:1.1; margin-top:2px; }
.pbp-caixa.gran .dlt { font-size:10.5px; }

.pbp-bloc.etiquetes { position:sticky; left:0; z-index:2; background:inherit; }
.pbp-bloc.etiquetes + .pbp-bloc { border-left:none; padding-left:0; }
.pbp-etiqueta-fila {
  min-height:46px; display:flex; align-items:center; justify-content:flex-end;
  font-size:9.5px; font-weight:700; letter-spacing:.03em; text-transform:uppercase;
  white-space:nowrap; padding-right:6px; color:#31333F; opacity:.75;
}
.pbp-etiqueta-fila.propi { color:#7a5600; opacity:1; }
.pbp-etiqueta-fila.rival { color:#6b2d99; opacity:1; }

/* Verd/taronja de config.DIVERGENT_POS/NEG, però en un to diferent per
   clar i fosc: el verd fosc de la resta de l'app (#00661f) no arriba a 3:1
   de contrast sobre el gris fosc de Streamlit (#262730), i el mateix passa
   a l'inrevés amb un verd clar sobre fons clar. Es mesura, no s'endevina. */
.pbp-caixa .dlt.millor { color:#0a7d22; }
.pbp-caixa .dlt.pitjor { color:#c2410c; }
.pbp-caixa .dlt.neutre { color:#31333F; opacity:.5; }

@media (prefers-color-scheme: dark) {
  .pbp-caixa { background:#262730; border-color:rgba(250,250,250,.18); }
  .pbp-caixa .lbl, .pbp-caixa .val, .pbp-titol-bloc { color:#fafafa; }
  .pbp-caixa.factor { background:rgba(57,135,229,.16); border-color:rgba(57,135,229,.55); }
  .pbp-caixa.factor .lbl, .pbp-titol-bloc.factor { color:#3987e5; }
  .pbp-caixa.propi { background:rgba(255,199,44,.15); border-color:rgba(255,199,44,.5); }
  .pbp-caixa.propi .lbl { color:#ffc72c; opacity:.95; }
  .pbp-caixa.rival { background:rgba(190,140,255,.15); border-color:rgba(190,140,255,.5); }
  .pbp-caixa.rival .lbl { color:#be8cff; opacity:.95; }
  .pbp-etiqueta-fila { color:#fafafa; }
  .pbp-etiqueta-fila.propi { color:#ffc72c; }
  .pbp-etiqueta-fila.rival { color:#be8cff; }
  .pbp-bloc + .pbp-bloc { border-left-color:rgba(250,250,250,.15); }
  .pbp-caixa .dlt.millor { color:#3ddc61; }
  .pbp-caixa .dlt.pitjor { color:#ffb066; }
  .pbp-caixa .dlt.neutre { color:#fafafa; opacity:.5; }
}
</style>
"""


def injecta_estil_caixes() -> None:
    """Insereix el <style> un cop per pàgina. Cridar abans de la primera fila_caixes()."""
    st.markdown(_ESTIL_CAIXES, unsafe_allow_html=True)


def _html_caixes(items: list[dict], classe: str) -> str:
    """HTML d'una llista de caixes. `classe` són les classes CSS de cada caixa."""
    trossos = []
    for item in items:
        cos = [
            f'<div class="lbl">{html.escape(item["etiqueta"])}</div>',
            f'<div class="val">{html.escape(str(item["valor"]))}</div>',
        ]
        classe_color = item.get("color", "neutre")
        if classe_color not in ("millor", "pitjor", "neutre"):
            classe_color = "neutre"
        # El div hi és sempre, encara que buit: si només el posessim quan hi ha
        # delta, la fila de referència quedaria més baixa que les altres.
        cos.append(f'<div class="dlt {classe_color}">{html.escape(item.get("delta") or "")}</div>')
        titol = f' title="{html.escape(item["ajuda"])}"' if item.get("ajuda") else ""
        trossos.append(f'<div class="{classe}"{titol}>{"".join(cos)}</div>')
    return f'<div class="pbp-fila">{"".join(trossos)}</div>'


def _html_titol_bloc(text: str, factor: bool = False, nota: str = "") -> str:
    classe = "pbp-titol-bloc factor" if factor else "pbp-titol-bloc"
    nota_html = f'<span class="nota">{html.escape(nota)}</span>' if nota else ""
    return f'<div class="{classe}">{html.escape(text)}{nota_html}</div>'


def tira_blocs(blocs: list[dict], etiquetes: list[str] | None = None) -> None:
    """
    Tots els blocs de mètriques en una sola tira horitzontal.

    Cada bloc: {"titol": str, "files": list[fila], "nota": str opcional,
    "factor": bool opcional}, on cada fila és {"items": [...], "estil": str}.
    `estil` és "" (referència: mitjana de la lliga), "rival" o "propi", i ha de
    ser el mateix a tots els blocs perquè la tira es llegeixi per files.
    Els items tenen el format de `fila_caixes`.

    `etiquetes`: nom de cada fila, dibuixat en una columna fixa a l'esquerra.
    Ha de tenir tants elements com files tingui cada bloc.
    """
    if not blocs:
        return

    parts = []

    if etiquetes:
        cel_les = [_html_titol_bloc(" ")]
        for etiqueta, fila in zip(etiquetes, blocs[0]["files"]):
            classe = f'pbp-etiqueta-fila {fila.get("estil", "")}'.strip()
            cel_les.append(f'<div class="pbp-fila"><div class="{classe}">{html.escape(etiqueta)}</div></div>')
        parts.append(f'<div class="pbp-bloc etiquetes">{"".join(cel_les)}</div>')

    for bloc in blocs:
        cel_les = [_html_titol_bloc(bloc["titol"], factor=bool(bloc.get("factor")), nota=bloc.get("nota", ""))]
        for fila in bloc["files"]:
            estil = fila.get("estil", "")
            # L'accent de "4 Factors" només pinta la fila de referència: les
            # altres ja porten el seu propi color d'equip.
            if not estil and bloc.get("factor"):
                estil = "factor"
            cel_les.append(_html_caixes(fila["items"], f"pbp-caixa {estil}".strip()))
        parts.append(f'<div class="pbp-bloc">{"".join(cel_les)}</div>')

    st.markdown(f'<div class="pbp-tira">{"".join(parts)}</div>', unsafe_allow_html=True)


def graella_caixes(items: list[dict], columnes: int = 2, gran: bool = False) -> None:
    """
    Caixes compactes repartides en una graella de `columnes` columnes.

    Mateix format d'item que `tira_blocs`. Amb `gran`, la xifra es dibuixa prou
    gran per fer de capçalera de pàgina. Cal haver cridat
    `injecta_estil_caixes()` abans.
    """
    if not items:
        return
    classe = "pbp-caixa gran" if gran else "pbp-caixa"
    cel_les = _html_caixes(items, classe).removeprefix('<div class="pbp-fila">').removesuffix("</div>")
    st.markdown(
        f'<div class="pbp-graella" style="grid-template-columns:repeat({columnes},1fr)">{cel_les}</div>',
        unsafe_allow_html=True,
    )
