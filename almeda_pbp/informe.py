# -*- coding: utf-8 -*-
"""
Generació de l'informe PDF.

Per què matplotlib i no els mateixos gràfics de Plotly: exportar Plotly a imatge
necessita Kaleido, que es descarrega un Chrome sencer i falla en entorns sense
navegador (com Streamlit Cloud). matplotlib i reportlab són wheels pures i no
depenen de res del sistema. Els gràfics es redibuixen aquí amb la MATEIXA paleta
que l'app, perquè el PDF i la pantalla es vegin igual.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import matplotlib

matplotlib.use("Agg")  # sense finestra: només renderitzat a fitxer

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import config as cfg, metriques as m
from .grafics import _ordena_desenllacos, _tinta_sobre

AMPLADA_UTIL = A4[0] - 3 * cm


# --- Estils ---------------------------------------------------------------

def _estils():
    base = getSampleStyleSheet()
    return {
        "titol": ParagraphStyle("titol", parent=base["Title"], fontSize=20, spaceAfter=4, textColor=colors.HexColor("#0b0b0b")),
        "subtitol": ParagraphStyle("subtitol", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#52514e"), spaceAfter=14),
        "seccio": ParagraphStyle("seccio", parent=base["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#0b0b0b")),
        "cos": ParagraphStyle("cos", parent=base["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#52514e")),
        "nota": ParagraphStyle("nota", parent=base["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#898781")),
    }


def _estil_taula(files: int) -> TableStyle:
    ordres = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0b0b0b")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#52514e")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#c3c2b7")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Files alternes amb un fons molt suau per seguir la línia amb la vista.
    for i in range(1, files):
        if i % 2 == 0:
            ordres.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f5f2")))
    return TableStyle(ordres)


def _taula(df: pd.DataFrame, amplada: float = AMPLADA_UTIL) -> Table:
    """Converteix un DataFrame en una taula de reportlab."""
    dades = [list(df.columns)] + df.astype(object).where(df.notna(), "").values.tolist()
    dades = [[f"{c:.2f}" if isinstance(c, float) else str(c) for c in fila] for fila in dades]
    taula = Table(dades, colWidths=[amplada / len(df.columns)] * len(df.columns), repeatRows=1)
    taula.setStyle(_estil_taula(len(dades)))
    return taula


# --- Gràfics (matplotlib) -------------------------------------------------

def _figura_a_imatge(figura, amplada_cm: float, alcada_max_cm: float = 21.0) -> Image:
    """
    Passa una figura de matplotlib a un objecte Image de reportlab.

    `genera_informe` només fa servir aquesta funció amb taules acotades (com a
    molt ~20 jugadores), però `genera_informe_a_mida` hi pot passar taules amb
    moltes files (parelles de posició, jugadora×posició) l'alçada natural de
    les quals, a `amplada_cm`, supera la pàgina — reportlab ho peta amb
    `LayoutError` en comptes d'escalar-ho. Per això aquí es limita SEMPRE
    l'alçada màxima i, si cal, es redueix l'amplada per mantenir la proporció.
    """
    memoria = io.BytesIO()
    figura.savefig(memoria, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(figura)
    memoria.seek(0)

    imatge = Image(memoria)
    proporcio = imatge.imageHeight / imatge.imageWidth
    amplada, alcada = amplada_cm, amplada_cm * proporcio
    if alcada > alcada_max_cm:
        alcada = alcada_max_cm
        amplada = alcada / proporcio
    imatge.drawWidth = amplada * cm
    imatge.drawHeight = alcada * cm
    return imatge


def donut_desenllacos(desenllacos: pd.DataFrame, sistema: str):
    """Donut dels desenllaços d'un sistema, amb els mateixos colors que l'app."""
    subconjunt = desenllacos[desenllacos[cfg.COL_TACTICA] == sistema]
    ordre = _ordena_desenllacos(subconjunt[cfg.COL_DESENLLAC].unique())
    subconjunt = subconjunt.set_index(cfg.COL_DESENLLAC).reindex(ordre).reset_index()

    valors = subconjunt["Jugades"].tolist()
    etiquetes = subconjunt[cfg.COL_DESENLLAC].tolist()
    colors_porcio = [cfg.COLORS_DESENLLAC.get(d, cfg.NEUTRE) for d in etiquetes]

    figura, eix = plt.subplots(figsize=(4.2, 4.0))
    # Les etiquetes van a la llegenda i no al voltant del donut: amb porcions
    # petites (una "Banda" i un "Fons" d'una jugada cadascun) els textos de fora
    # se superposen i queden il·legibles.
    trossos, textos = eix.pie(
        valors,
        colors=colors_porcio,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
    )[:2]

    # El recompte va dins de la porció, al mig de l'anell, i només si hi cap.
    radi = 1 - 0.55 / 2
    for tros, valor, color in zip(trossos, valors, colors_porcio):
        if (tros.theta2 - tros.theta1) < 18:  # menys de 5% de la volta: no hi cap
            continue
        angle_mig = math.radians((tros.theta1 + tros.theta2) / 2)
        eix.text(
            radi * math.cos(angle_mig),
            radi * math.sin(angle_mig),
            str(int(valor)),
            ha="center", va="center", fontsize=8, color=_tinta_sobre(color),
        )

    eix.legend(
        trossos,
        [f"{e} ({v})" for e, v in zip(etiquetes, valors)],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=3,
        fontsize=7,
        frameon=False,
    )
    eix.set_title(sistema, fontsize=11, fontweight="bold", color="#0b0b0b")
    return figura


def barres_punts_assist(taula: pd.DataFrame, sistema: str):
    """Punts anotats vs punts generats, per jugadora, dins d'un sistema."""
    subconjunt = taula[taula[cfg.COL_TACTICA] == sistema]
    subconjunt = subconjunt[(subconjunt["Punts anotats"] > 0) | (subconjunt["Punts assistits"] > 0)]
    subconjunt = subconjunt.sort_values("Punts anotats", ascending=False)

    figura, eix = plt.subplots(figsize=(4.6, 3.6))
    if subconjunt.empty:
        eix.text(0.5, 0.5, "Sense punts", ha="center", va="center", fontsize=10, color="#898781")
        eix.set_axis_off()
        return figura

    posicions = range(len(subconjunt))
    ample = 0.38
    eix.bar(
        [p - ample / 2 for p in posicions], subconjunt["Punts anotats"],
        width=ample, color=cfg.COLORS_SERIE[0], edgecolor="white", linewidth=1, label="Punts anotats",
    )
    eix.bar(
        [p + ample / 2 for p in posicions], subconjunt["Punts assistits"],
        width=ample, color=cfg.COLORS_SERIE[1], edgecolor="white", linewidth=1, label="Punts generats",
    )

    for p, (anotats, assistits) in enumerate(zip(subconjunt["Punts anotats"], subconjunt["Punts assistits"])):
        if anotats:
            eix.text(p - ample / 2, anotats, str(int(anotats)), ha="center", va="bottom", fontsize=7, color="#52514e")
        if assistits:
            eix.text(p + ample / 2, assistits, str(int(assistits)), ha="center", va="bottom", fontsize=7, color="#52514e")

    eix.set_xticks(list(posicions))
    eix.set_xticklabels(subconjunt["Jugadora"], rotation=35, ha="right", fontsize=8)
    eix.set_ylabel("Punts", fontsize=8)
    eix.tick_params(axis="y", labelsize=8)
    eix.legend(fontsize=7, frameon=False, loc="upper right")
    eix.spines[["top", "right"]].set_visible(False)
    eix.grid(axis="y", color="#e1e0d9", linewidth=0.6)
    eix.set_axisbelow(True)
    return figura


def barres_plus_minus(taula: pd.DataFrame, columna_etiqueta: str, titol: str):
    """Barres horitzontals divergents (verd positiu / taronja negatiu)."""
    taula = taula.sort_values("+/-", ascending=True)
    alcada = max(2.4, 0.26 * len(taula) + 0.9)

    figura, eix = plt.subplots(figsize=(7.0, alcada))
    colors_barra = [
        cfg.DIVERGENT_POS if v > 0 else (cfg.DIVERGENT_NEG if v < 0 else cfg.NEUTRE) for v in taula["+/-"]
    ]
    barres = eix.barh(taula[columna_etiqueta], taula["+/-"], color=colors_barra, edgecolor="white", linewidth=0.8)

    maxim = max(abs(taula["+/-"].max()), abs(taula["+/-"].min()), 1)
    for barra, valor in zip(barres, taula["+/-"]):
        desplacament = maxim * 0.02
        eix.text(
            barra.get_width() + (desplacament if valor >= 0 else -desplacament),
            barra.get_y() + barra.get_height() / 2,
            f"{int(valor):+d}",
            va="center", ha="left" if valor >= 0 else "right", fontsize=7, color="#52514e",
        )

    eix.axvline(0, color="#52514e", linewidth=0.8)
    eix.set_xlim(-1.25 * maxim, 1.25 * maxim)
    eix.set_xlabel("+/-", fontsize=8)
    eix.set_title(titol, fontsize=11, fontweight="bold", color="#0b0b0b")
    eix.tick_params(labelsize=8)
    eix.spines[["top", "right", "left"]].set_visible(False)
    eix.grid(axis="x", color="#e1e0d9", linewidth=0.6)
    eix.set_axisbelow(True)
    return figura


def barres_rebot_periode(taula: pd.DataFrame):
    """Rebot ofensiu i punts de segona oportunitat, per període (versió estàtica)."""
    figura, eix = plt.subplots(figsize=(7.0, 3.6))

    dades = taula[taula[cfg.COL_PERIODE] != "Total"]
    series = [
        ("RO a favor", cfg.DIVERGENT_POS),
        ("Punts RO a favor", "#86b6ef"),
        ("RO en contra", cfg.DIVERGENT_NEG),
        ("Punts RO rival", "#f3ad91"),
    ]
    series = [(nom, color) for nom, color in series if nom in dades.columns]
    if dades.empty or not series:
        eix.text(0.5, 0.5, "Sense dades de rebot", ha="center", va="center", fontsize=10, color="#898781")
        eix.set_axis_off()
        return figura

    x = range(len(dades))
    ample = 0.8 / len(series)
    for i, (nom, color) in enumerate(series):
        posicions = [p + (i - (len(series) - 1) / 2) * ample for p in x]
        eix.bar(posicions, dades[nom], width=ample, color=color, edgecolor="white", linewidth=1, label=nom)

    eix.set_xticks(list(x))
    eix.set_xticklabels(dades[cfg.COL_PERIODE], fontsize=8)
    eix.set_ylabel("Rebots / punts", fontsize=8)
    eix.set_xlabel("Període", fontsize=8)
    eix.tick_params(axis="y", labelsize=8)
    eix.legend(fontsize=7, frameon=False, loc="upper right", ncol=2)
    eix.spines[["top", "right"]].set_visible(False)
    eix.grid(axis="y", color="#e1e0d9", linewidth=0.6)
    eix.set_axisbelow(True)
    eix.set_title("Rebot ofensiu i segona oportunitat per període", fontsize=11, fontweight="bold", color="#0b0b0b")
    return figura


def barres_punts_jugada(resum: pd.DataFrame, min_jugades: int = 5):
    """Punts per jugada per sistema, ordenat (versió estàtica de `grafics.barres_punts_jugada`)."""
    taula = resum[resum["Jugades"] >= min_jugades].sort_values("Punts/jugada", ascending=True)
    alcada = max(2.4, 0.3 * len(taula) + 0.9)

    figura, eix = plt.subplots(figsize=(7.0, alcada))
    if taula.empty:
        eix.text(0.5, 0.5, f"Cap sistema arriba a {min_jugades} jugades", ha="center", va="center", fontsize=10, color="#898781")
        eix.set_axis_off()
        return figura

    eix.barh(taula[cfg.COL_TACTICA], taula["Punts/jugada"], color=cfg.COLORS_SERIE[0], edgecolor="white", linewidth=0.8)
    for i, valor in enumerate(taula["Punts/jugada"]):
        eix.text(valor + 0.01, i, f"{valor:.2f}", va="center", ha="left", fontsize=7, color="#52514e")

    eix.set_xlabel("Punts per jugada", fontsize=8)
    eix.set_title(f"Punts per jugada · sistemes amb ≥ {min_jugades} jugades", fontsize=11, fontweight="bold", color="#0b0b0b")
    eix.tick_params(labelsize=8)
    eix.spines[["top", "right", "left"]].set_visible(False)
    eix.grid(axis="x", color="#e1e0d9", linewidth=0.6)
    eix.set_axisbelow(True)
    return figura


# --- Document -------------------------------------------------------------

def _linia_context(context: dict) -> str:
    """Resumeix els filtres aplicats perquè el PDF sigui interpretable tot sol."""
    parts = []
    for etiqueta, clau in (
        ("Temporada", "temporada"),
        ("Jornades", "jornades"),
        ("Períodes", "periodes"),
        ("Jugadores", "jugadores"),
    ):
        valor = context.get(clau)
        if not valor:
            continue
        if isinstance(valor, (list, tuple)):
            valor = ", ".join(str(v) for v in valor) if len(valor) <= 12 else f"{len(valor)} seleccionades"
        parts.append(f"<b>{etiqueta}:</b> {valor}")
    if context.get("jugadores") and context.get("mode"):
        parts.append(f"<b>Filtre de jugadora:</b> {context['mode']}")
    return " &nbsp;·&nbsp; ".join(parts)


def _capcalera_document(titol: str, context: dict) -> list:
    """Paràgraf de títol + línia de generació/context, comuna a tots els informes."""
    estils = _estils()
    return [
        Paragraph(titol, estils["titol"]),
        Paragraph(
            f"Generat el {datetime.now():%d/%m/%Y a les %H:%M}"
            + (f"<br/>{_linia_context(context)}" if context else ""),
            estils["subtitol"],
        ),
    ]


def _construeix_document(historia: list, titol_document: str = "Informe PBP Basket Almeda") -> bytes:
    """Munta un `SimpleDocTemplate` a partir d'una llista de flowables i el serialitza a bytes."""
    memoria = io.BytesIO()
    document = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=titol_document,
        author="Basket Almeda",
    )
    document.build(historia)
    return memoria.getvalue()


def genera_informe(
    dades: pd.DataFrame,
    sistemes: list[str],
    context: dict | None = None,
    incloure_plus_minus: bool = True,
) -> bytes:
    """
    Construeix l'informe PDF de les jugades seleccionades i el retorna en bytes.

    `dades` ha d'arribar JA filtrat (el mateix que es veu a pantalla) perquè el
    PDF i l'app no puguin dir coses diferents.
    """
    context = context or {}
    estils = _estils()

    seleccio = dades[dades[cfg.COL_TACTICA].isin(sistemes)] if sistemes else dades
    resum = m.resum_sistemes(seleccio)
    desenllacos = m.desenllacos_per_sistema(seleccio)
    punts_assist = m.punts_i_assistencies_per_sistema(seleccio)
    general = m.resum_general(seleccio)

    historia = _capcalera_document("Informe play-by-play · Basket Almeda", context)

    # --- Resum general ---
    capcalera = pd.DataFrame(
        [{
            "Jornades": general["jornades"],
            "Jugades": general["jugades"],
            "Punts a favor": general["punts"],
            "Punts en contra": general["punts_rival"],
            "Punts/jugada": general["ppp"],
            "Punts/jugada rival": general["ppp_rival"],
        }]
    )
    historia += [Paragraph("Resum de la selecció", estils["seccio"]), _taula(capcalera), Spacer(1, 0.5 * cm)]

    if resum.empty:
        historia.append(Paragraph("No hi ha cap jugada amb sistema anotat en aquesta selecció.", estils["cos"]))
        return _construeix_document(historia)

    historia += [
        Paragraph("Sistemes seleccionats", estils["seccio"]),
        _taula(resum),
        Paragraph(
            "«Jugades» compta files del PBP. Les files amb sistema RO són la continuació de la mateixa "
            "possessió després d'un rebot ofensiu, així que aquestes xifres són per jugada, no per "
            "possessió tancada.",
            estils["nota"],
        ),
    ]

    # --- Un bloc per sistema ---
    for sistema in resum[cfg.COL_TACTICA]:
        fila = resum[resum[cfg.COL_TACTICA] == sistema].iloc[0]
        bloc = [
            Paragraph(
                f"{sistema} &nbsp;·&nbsp; {int(fila['Jugades'])} jugades &nbsp;·&nbsp; "
                f"{int(fila['Punts'])} punts &nbsp;·&nbsp; {fila['Punts/jugada']:.2f} punts/jugada",
                estils["seccio"],
            )
        ]

        imatges = []
        if not desenllacos[desenllacos[cfg.COL_TACTICA] == sistema].empty:
            imatges.append(_figura_a_imatge(donut_desenllacos(desenllacos, sistema), 7.6))
        imatges.append(_figura_a_imatge(barres_punts_assist(punts_assist, sistema), 8.6))

        graella = Table([imatges], colWidths=[i.drawWidth + 0.3 * cm for i in imatges])
        graella.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        bloc.append(graella)

        historia.append(KeepTogether(bloc))

    # --- +/- de la selecció ---
    if incloure_plus_minus:
        individual = m.plus_minus_individual(seleccio)
        if not individual.empty:
            historia.append(PageBreak())
            historia.append(Paragraph("Plus/minus de la selecció", estils["seccio"]))
            historia.append(
                Paragraph(
                    "Aquest +/- només compta les jugades seleccionades, així que no és el +/- del partit. "
                    "És descriptiu: no vol dir que la jugadora sigui la causa del diferencial.",
                    estils["nota"],
                )
            )
            historia.append(Spacer(1, 0.3 * cm))
            historia.append(_figura_a_imatge(barres_plus_minus(individual, "Jugadora", "+/- per jugadora"), 16.0))
            historia.append(Spacer(1, 0.4 * cm))
            historia.append(_taula(individual))

    return _construeix_document(historia)


# --- Informe a mida ---------------------------------------------------------
# Constructor genèric: en comptes de l'estructura fixa de `genera_informe`
# (un bloc per sistema + un +/- final), aquí l'analista tria LLIUREMENT quins
# tipus de bloc vol, de qualsevol pàgina, i en quin ordre. Cada entrada de
# TIPUS_BLOCS sap construir-se sola a partir del DataFrame ja filtrat.

def _bloc_donut(dades: pd.DataFrame, sistema: str) -> list:
    desenllacos = m.desenllacos_per_sistema(dades)
    desenllacos = desenllacos[desenllacos[cfg.COL_TACTICA] == sistema]
    if desenllacos.empty:
        return []
    return [KeepTogether([
        Paragraph(f"{sistema} — desenllaços", _estils()["seccio"]),
        _figura_a_imatge(donut_desenllacos(desenllacos, sistema), 8.0),
    ])]


def _bloc_punts_assist(dades: pd.DataFrame, sistema: str) -> list:
    taula = m.punts_i_assistencies_per_sistema(dades)
    if taula.empty or sistema not in set(taula[cfg.COL_TACTICA]):
        return []
    return [KeepTogether([
        Paragraph(f"{sistema} — punts anotats i generats", _estils()["seccio"]),
        _figura_a_imatge(barres_punts_assist(taula, sistema), 9.0),
    ])]


def _bloc_taula_sistemes(dades: pd.DataFrame) -> list:
    resum = m.resum_sistemes(dades)
    if resum.empty:
        return []
    return [Paragraph("Taula de sistemes", _estils()["seccio"]), _taula(resum), Spacer(1, 0.4 * cm)]


def _bloc_eficiencia(dades: pd.DataFrame) -> list:
    resum = m.resum_sistemes(dades)
    if resum.empty:
        return []
    return [KeepTogether([
        Paragraph("Eficiència per sistema", _estils()["seccio"]),
        _figura_a_imatge(barres_punts_jugada(resum), 16.0),
    ])]


def _bloc_pm_individual(dades: pd.DataFrame) -> list:
    taula = m.plus_minus_individual(dades)
    if taula.empty:
        return []
    return [
        Paragraph("+/- individual", _estils()["seccio"]),
        _figura_a_imatge(barres_plus_minus(taula, "Jugadora", "+/- per jugadora"), 16.0),
        Spacer(1, 0.3 * cm),
        _taula(taula),
        Spacer(1, 0.4 * cm),
    ]


def _bloc_pm_parelles(dades: pd.DataFrame, min_jugades: int = 25) -> list:
    taula = m.plus_minus_parelles(dades, min_jugades=min_jugades)
    if taula.empty:
        return []
    return [
        Paragraph(f"+/- per parelles (≥ {min_jugades} jugades juntes)", _estils()["seccio"]),
        _figura_a_imatge(barres_plus_minus(taula, "Parella", "+/- per parella"), 16.0),
        Spacer(1, 0.3 * cm),
        _taula(taula),
        Spacer(1, 0.4 * cm),
    ]


def _bloc_pm_parelles_posicio(dades: pd.DataFrame, min_jugades: int = 15) -> list:
    taula = m.plus_minus_parelles_posicio(dades, min_jugades=min_jugades)
    if taula.empty:
        return []
    columnes = [c for c in taula.columns if c not in ("Jugadora A", "Jugadora B")]
    return [
        Paragraph(f"+/- per parelles de posició (≥ {min_jugades} jugades juntes)", _estils()["seccio"]),
        _figura_a_imatge(barres_plus_minus(taula, "Jugadores", "+/- per parella de posicions"), 16.0),
        Spacer(1, 0.3 * cm),
        _taula(taula[columnes]),
        Spacer(1, 0.4 * cm),
    ]


def _bloc_pm_posicio(dades: pd.DataFrame, min_jugades: int = 25) -> list:
    taula = m.plus_minus_per_posicio(dades, min_jugades=min_jugades)
    if taula.empty:
        return []
    columnes = [c for c in taula.columns if c != "Etiqueta"]
    return [
        Paragraph(f"+/- per jugadora × posició (≥ {min_jugades} jugades)", _estils()["seccio"]),
        _figura_a_imatge(barres_plus_minus(taula, "Etiqueta", "+/- per jugadora i posició"), 16.0),
        Spacer(1, 0.3 * cm),
        _taula(taula[columnes]),
        Spacer(1, 0.4 * cm),
    ]


def _bloc_rebot(dades: pd.DataFrame) -> list:
    taula = m.resum_rebot_ofensiu(dades)
    if taula.empty:
        return []
    return [
        Paragraph("Rebot ofensiu per període", _estils()["seccio"]),
        _figura_a_imatge(barres_rebot_periode(taula), 16.0),
        Spacer(1, 0.3 * cm),
        _taula(taula),
        Spacer(1, 0.4 * cm),
    ]


@dataclass
class TipusBloc:
    etiqueta: str
    # "sistema": es repeteix un cop per cada sistema triat. "general": un
    # sol cop encara que hi hagi diversos sistemes seleccionats.
    abast: str
    construeix: Callable[..., list]


TIPUS_BLOCS: dict[str, TipusBloc] = {
    "donut": TipusBloc("Desenllaços per sistema (donut)", "sistema", _bloc_donut),
    "punts_assist": TipusBloc("Punts anotats i generats per sistema", "sistema", _bloc_punts_assist),
    "taula_sistemes": TipusBloc("Taula resum de sistemes", "general", lambda d, s=None: _bloc_taula_sistemes(d)),
    "eficiencia_sistemes": TipusBloc("Eficiència (punts/jugada) per sistema", "general", lambda d, s=None: _bloc_eficiencia(d)),
    "pm_individual": TipusBloc("+/- individual", "general", lambda d, s=None: _bloc_pm_individual(d)),
    "pm_parelles": TipusBloc("+/- per parelles", "general", lambda d, s=None: _bloc_pm_parelles(d)),
    "pm_parelles_posicio": TipusBloc("+/- per parelles de posició", "general", lambda d, s=None: _bloc_pm_parelles_posicio(d)),
    "pm_posicio": TipusBloc("+/- per jugadora × posició", "general", lambda d, s=None: _bloc_pm_posicio(d)),
    "rebot": TipusBloc("Rebot ofensiu per període", "general", lambda d, s=None: _bloc_rebot(d)),
}


def genera_informe_a_mida(
    dades: pd.DataFrame,
    tipus_seleccionats: list[str],
    sistemes: list[str] | None = None,
    context: dict | None = None,
    titol: str = "Informe a mida · Basket Almeda",
) -> bytes:
    """
    Informe compost lliurement a partir del catàleg `TIPUS_BLOCS`.

    A diferència de `genera_informe` (estructura fixa: un bloc per sistema +
    un +/- final), aquí es trien els tipus de bloc un a un. Els d'abast
    "sistema" es repeteixen per cada sistema de `sistemes` (o per tots els
    presents a `dades` si no se'n passa cap); els d'abast "general" surten un
    sol cop encara que se'n demanin diversos.

    `dades` ha d'arribar ja filtrada (temporada, jornades, jugadores...): el
    PDF només compon els blocs, no torna a decidir quines dades hi entren.
    """
    context = context or {}
    historia = _capcalera_document(titol, context)

    general_resum = m.resum_general(dades)
    capcalera_taula = pd.DataFrame(
        [{
            "Jornades": general_resum["jornades"],
            "Jugades": general_resum["jugades"],
            "Punts a favor": general_resum["punts"],
            "Punts en contra": general_resum["punts_rival"],
            "Punts/jugada": general_resum["ppp"],
            "Punts/jugada rival": general_resum["ppp_rival"],
        }]
    )
    historia += [Paragraph("Resum de la selecció", _estils()["seccio"]), _taula(capcalera_taula), Spacer(1, 0.5 * cm)]

    if dades.empty or not tipus_seleccionats:
        historia.append(Paragraph("Cap bloc seleccionat, o cap jugada amb aquests filtres.", _estils()["cos"]))
        return _construeix_document(historia, titol)

    sistemes_presents = sorted(dades[dades[cfg.COL_TACTICA].notna()][cfg.COL_TACTICA].unique())
    sistemes_a_recorrer = [s for s in (sistemes or sistemes_presents) if s in sistemes_presents]

    for tipus_id in tipus_seleccionats:
        bloc = TIPUS_BLOCS.get(tipus_id)
        if bloc is None:
            continue
        if bloc.abast == "sistema":
            for sistema in sistemes_a_recorrer:
                historia.extend(bloc.construeix(dades, sistema))
        else:
            historia.extend(bloc.construeix(dades))

    return _construeix_document(historia, titol)
