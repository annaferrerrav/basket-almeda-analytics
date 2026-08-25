# -*- coding: utf-8 -*-
"""
Gràfics interactius (Plotly).

Criteris aplicats a tots:
- El color dels desenllaços és una escala ORDENADA de qualitat (cistella →
  pèrdua), no una paleta d'identitats, i sempre va acompanyat d'etiqueta o
  llegenda: el color no porta mai el significat tot sol.
- El +/- fa servir un parell divergent (blau positiu / vermell negatiu) amb
  neutre al mig, perquè el que importa és el signe.
- Marques primes, graella discreta, etiquetes directes només on aporten.
- Un sol eix per gràfic. Punts i assistències van en dues barres agrupades,
  mai en dos eixos Y.
"""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import config as cfg

_LAYOUT_BASE = dict(
    template="simple_white",
    font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13),
    margin=dict(l=10, r=10, t=60, b=10),
    hoverlabel=dict(font_size=13),
)


# Separació entre grups de barres del gràfic de rebot. Viu fora de la funció
# perquè el càlcul de la posició de les línies del sostre l'ha de fer servir
# exactament igual que el layout.
_REBOT_BARGAP = 0.3


def _tinta_sobre(fons: str) -> str:
    """
    Tinta llegible sobre un color de fons.

    No es fa amb un llindar de lluminositat sinó comparant el contrast (WCAG)
    de blanc i de negre contra el fons i quedant-se amb el millor. Amb un llindar
    fix, els grisos mitjans (com el `#8a8884` de les pèrdues) es queden amb text
    blanc quan el negre s'hi llegeix millor.
    """
    r, g, b = (int(fons.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    canals = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    lluminancia = 0.2126 * canals[0] + 0.7152 * canals[1] + 0.0722 * canals[2]

    contrast_blanc = 1.05 / (lluminancia + 0.05)
    contrast_negre = (lluminancia + 0.05) / 0.05
    return "#ffffff" if contrast_blanc >= contrast_negre else "#0b0b0b"


def _ordena_desenllacos(etiquetes) -> list[str]:
    """Ordena els desenllaços de millor a pitjor; els desconeguts, al final."""
    coneguts = [d for d in cfg.ORDRE_DESENLLAC if d in etiquetes]
    altres = sorted(e for e in etiquetes if e not in cfg.ORDRE_DESENLLAC)
    return coneguts + altres


def pies_desenllac_per_sistema(
    desenllacos: pd.DataFrame,
    resum: pd.DataFrame,
    columnes: int = 3,
    alcada_fila: int = 460,
) -> go.Figure:
    """
    Graella de donuts: un per sistema, repartint les jugades per desenllaç.

    El títol de cada donut porta les jugades i els punts/jugada, que és el que
    permet comparar sistemes: un sistema amb molts T2C però jugat 4 vegades no
    és millor que un de jugat 40 amb més punts per jugada.

    `alcada_fila` és l'alçada en píxels de cada fila de la graella. Un donut
    creix fins al MENOR de l'ample i l'alt de la seva cel·la, així que amb
    poques files i tot l'ample de la pàgina és l'alçada la que mana: sense
    donar-n'hi prou, els donuts surten minúsculs encara que hi hagi ample de
    sobra.
    """
    if desenllacos.empty:
        return _figura_buida("Cap jugada amb sistema i desenllaç anotats.")

    sistemes = resum[cfg.COL_TACTICA].tolist()
    sistemes = [s for s in sistemes if s in set(desenllacos[cfg.COL_TACTICA])]
    if not sistemes:
        return _figura_buida("Cap sistema per mostrar amb els filtres actuals.")

    files = math.ceil(len(sistemes) / columnes)
    ppp = resum.set_index(cfg.COL_TACTICA)["Punts/jugada"].to_dict()
    poss = resum.set_index(cfg.COL_TACTICA)["Jugades"].to_dict()

    figura = make_subplots(
        rows=files,
        cols=columnes,
        specs=[[{"type": "domain"} for _ in range(columnes)] for _ in range(files)],
        subplot_titles=[f"{s}<br><sub>{poss.get(s, 0)} jug. · {ppp.get(s, 0):.2f} punts/jug.</sub>" for s in sistemes],
        # L'espai entre files es dona en fracció de l'alçada total: amb un valor
        # fix, moltes files el fan il·legal (ha de ser < 1/(files-1)) i poques
        # el fan enorme en píxels. Es lliga a l'alçada de fila.
        vertical_spacing=min(0.10, 60 / max(alcada_fila * files, 1)) if files > 1 else 0.0,
    )

    for i, sistema in enumerate(sistemes):
        subconjunt = desenllacos[desenllacos[cfg.COL_TACTICA] == sistema]
        ordre = _ordena_desenllacos(subconjunt[cfg.COL_DESENLLAC].unique())
        subconjunt = subconjunt.set_index(cfg.COL_DESENLLAC).reindex(ordre).reset_index()

        colors = [cfg.COLORS_DESENLLAC.get(d, cfg.NEUTRE) for d in subconjunt[cfg.COL_DESENLLAC]]

        figura.add_trace(
            go.Pie(
                labels=subconjunt[cfg.COL_DESENLLAC],
                values=subconjunt["Jugades"],
                name=sistema,
                hole=0.45,
                # Sense això, Plotly encongeix el donut per reservar marge
                # dins de la cel·la encara que no hi hagi cap etiqueta a fora.
                automargin=False,
                sort=False,
                direction="clockwise",
                marker=dict(
                    colors=colors,
                    # 2px de separació entre segments perquè es llegeixin com a peces
                    # separades encara que dos desenllaços comparteixin família de color.
                    line=dict(color="#ffffff", width=2),
                ),
                # El desenllaç exacte va escrit a la porció: el color només porta
                # la família de qualitat, mai la categoria concreta.
                texttemplate="%{label}<br>%{value}",
                textposition="inside",
                insidetextfont=dict(color=[_tinta_sobre(c) for c in colors], size=11),
                hovertemplate=(
                    f"<b>{sistema}</b><br>%{{label}}: %{{value}} jugades "
                    "(%{percent})<extra></extra>"
                ),
            ),
            row=i // columnes + 1,
            col=i % columnes + 1,
        )

    layout = dict(_LAYOUT_BASE)
    # Marge inferior propi per a la llegenda horitzontal: amb els 10px de
    # _LAYOUT_BASE es menjaria la fila de baix de donuts.
    layout["margin"] = dict(l=10, r=10, t=70, b=60)

    figura.update_layout(
        **layout,
        height=alcada_fila * files + 90,
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5),
        uniformtext=dict(minsize=10, mode="hide"),
    )
    figura.update_annotations(font_size=14)
    return figura


def barres_punts_assistencies(taula: pd.DataFrame, sistema: str) -> go.Figure:
    """
    Per un sistema: qui anota i qui genera els punts amb assistència.

    Dues barres agrupades per jugadora sobre un únic eix Y (punts). No s'apilen
    perquè no són parts d'un total: els mateixos punts poden aparèixer a les
    dues sèries si A assisteix i B anota.
    """
    subconjunt = taula[taula[cfg.COL_TACTICA] == sistema]
    subconjunt = subconjunt[(subconjunt["Punts anotats"] > 0) | (subconjunt["Punts assistits"] > 0)]
    if subconjunt.empty:
        return _figura_buida(f"Cap punt anotat amb «{sistema}» amb els filtres actuals.")

    subconjunt = subconjunt.sort_values("Punts anotats", ascending=False)

    figura = go.Figure()
    figura.add_trace(
        go.Bar(
            x=subconjunt["Jugadora"],
            y=subconjunt["Punts anotats"],
            name="Punts anotats",
            marker_color=cfg.COLORS_SERIE[0],
            marker_line=dict(color="#ffffff", width=2),
            text=subconjunt["Punts anotats"].replace(0, ""),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Punts anotats: %{y}<extra></extra>",
        )
    )
    figura.add_trace(
        go.Bar(
            x=subconjunt["Jugadora"],
            y=subconjunt["Punts assistits"],
            name="Punts generats (assistència)",
            marker_color=cfg.COLORS_SERIE[1],
            marker_line=dict(color="#ffffff", width=2),
            text=subconjunt["Punts assistits"].replace(0, ""),
            textposition="outside",
            customdata=subconjunt[["Assistències"]],
            hovertemplate="<b>%{x}</b><br>Punts generats: %{y}<br>Assistències: %{customdata[0]}<extra></extra>",
        )
    )

    figura.update_layout(
        **_LAYOUT_BASE,
        barmode="group",
        bargap=0.35,
        bargroupgap=0.12,
        title=dict(text=f"{sistema} — punts anotats i generats", font=dict(size=15)),
        yaxis=dict(title="Punts", gridcolor=cfg.GRAELLA, zeroline=False),
        xaxis=dict(title=None, tickangle=-30),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        height=380,
    )
    return figura


def barres_plus_minus(
    taula: pd.DataFrame,
    columna_etiqueta: str,
    columna_valor: str = "+/-",
    titol: str = "+/-",
    alcada_per_barra: int = 19,
) -> go.Figure:
    """
    Barres horitzontals divergents per a +/-.

    El color codifica només el signe (blau per damunt de 0, vermell per sota);
    la magnitud la porta la llargada de la barra, que és el canal que l'ull
    llegeix bé. L'etiqueta numèrica va sempre visible.

    El gruix de la barra és `alcada_per_barra * (1 - bargap)` i la separació,
    la resta. Els dos valors es toquen junts: abaixar només l'alçada aprima les
    barres, i abaixar només el bargap les engreixa sense acostar-les.
    """
    if taula.empty:
        return _figura_buida("Sense parelles/jugadores que superin el mínim de jugades.")

    taula = taula.sort_values(columna_valor, ascending=True)
    colors = [cfg.DIVERGENT_POS if v > 0 else (cfg.DIVERGENT_NEG if v < 0 else cfg.NEUTRE) for v in taula[columna_valor]]

    figura = go.Figure(
        go.Bar(
            x=taula[columna_valor],
            y=taula[columna_etiqueta],
            orientation="h",
            marker=dict(color=colors, line=dict(color="#ffffff", width=1)),
            text=taula[columna_valor],
            textposition="outside",
            customdata=taula[["Jugades", "+/- per 100 jugades"]],
            hovertemplate=(
                "<b>%{y}</b><br>+/-: %{x}<br>Jugades juntes: %{customdata[0]}"
                "<br>+/- per 100 poss.: %{customdata[1]}<extra></extra>"
            ),
        )
    )
    figura.add_vline(x=0, line_width=1, line_color=cfg.TINTA_SECUNDARIA)
    figura.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=titol, font=dict(size=15)),
        xaxis=dict(title="+/-", gridcolor=cfg.GRAELLA, zeroline=False),
        yaxis=dict(title=None, automargin=True),
        height=max(280, alcada_per_barra * len(taula) + 100),
        showlegend=False,
        bargap=0.18,
    )
    return figura


def barres_punts_jugada(resum: pd.DataFrame, min_jugades: int = 5) -> go.Figure:
    """
    Punts per jugada per sistema, ordenat. La barra amaga la mostra, així que
    les jugades van al hover i els sistemes amb poca mostra queden fora.
    """
    taula = resum[resum["Jugades"] >= min_jugades]
    if taula.empty:
        return _figura_buida(f"Cap sistema arriba a {min_jugades} jugades amb els filtres actuals.")

    taula = taula.sort_values("Punts/jugada", ascending=True)
    figura = go.Figure(
        go.Bar(
            x=taula["Punts/jugada"],
            y=taula[cfg.COL_TACTICA],
            orientation="h",
            marker=dict(color=cfg.COLORS_SERIE[0], line=dict(color="#ffffff", width=1)),
            text=[f"{v:.2f}" for v in taula["Punts/jugada"]],
            textposition="outside",
            customdata=taula[["Jugades", "Punts", "% pèrdues"]],
            hovertemplate=(
                "<b>%{y}</b><br>Punts/jugada: %{x:.2f}<br>Jugades: %{customdata[0]}"
                "<br>Punts: %{customdata[1]}<br>%% pèrdues: %{customdata[2]}<extra></extra>"
            ),
        )
    )
    figura.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=f"Punts per jugada · sistemes amb ≥ {min_jugades} jugades", font=dict(size=15)),
        xaxis=dict(title="Punts/jugada", gridcolor=cfg.GRAELLA, zeroline=False),
        yaxis=dict(title=None, automargin=True),
        height=max(320, 26 * len(taula) + 110),
        showlegend=False,
        bargap=0.35,
    )
    return figura


def facetes_plus_minus_posicio(
    taula: pd.DataFrame,
    columnes: int = 2,
    alcada_barra: int = 13,
) -> go.Figure:
    """
    Un panell per parella de posicions (jug 1·jug 4, jug 1·jug 5...).

    Tots els panells comparteixen l'escala de l'eix X a propòsit: si cadascun
    s'escalés al seu màxim, una parella amb +4 semblaria tan bona com una amb
    +30. Amb escala comuna les alçades es poden comparar d'un panell a l'altre.

    `alcada_barra` són els píxels que es reserven per barra. L'alçada del panell
    la marca el panell amb MÉS parelles, no la mitjana: com que l'escala és
    comuna, tots els panells han de fer el mateix alt o les barres del mateix
    valor es veurien de gruixos diferents segons on caiguessin.
    """
    if taula.empty:
        return _figura_buida("Cap parella de posicions arriba al mínim de jugades.")

    parelles = [p for p in (f"{a} · {b}" for a, b in cfg.PARELLES_POSICIO) if p in set(taula["Parella posicions"])]
    if not parelles:
        return _figura_buida("Cap parella de posicions amb dades.")

    files = math.ceil(len(parelles) / columnes)
    maxim = float(taula["+/-"].abs().max()) or 1.0
    limit = [-1.25 * maxim, 1.25 * maxim]

    figura = make_subplots(
        rows=files,
        cols=columnes,
        subplot_titles=parelles,
        horizontal_spacing=0.16,
        vertical_spacing=max(0.05, 0.5 / files),
    )

    for i, parella in enumerate(parelles):
        subconjunt = taula[taula["Parella posicions"] == parella].sort_values("+/-", ascending=True)
        colors = [
            cfg.DIVERGENT_POS if v > 0 else (cfg.DIVERGENT_NEG if v < 0 else cfg.NEUTRE)
            for v in subconjunt["+/-"]
        ]
        fila, columna = i // columnes + 1, i % columnes + 1

        figura.add_trace(
            go.Bar(
                x=subconjunt["+/-"],
                y=subconjunt["Jugadores"],
                orientation="h",
                marker=dict(color=colors, line=dict(color="#ffffff", width=1)),
                text=subconjunt["+/-"],
                textposition="outside",
                customdata=subconjunt[["Jugades", "+/- per 100 jugades"]],
                hovertemplate=(
                    f"<b>{parella}</b><br>%{{y}}<br>+/-: %{{x}}<br>Jugades juntes: %{{customdata[0]}}"
                    "<br>+/- per 100 jugades: %{customdata[1]}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=fila,
            col=columna,
        )
        figura.add_vline(x=0, line_width=1, line_color=cfg.TINTA_SECUNDARIA, row=fila, col=columna)
        figura.update_xaxes(range=limit, gridcolor=cfg.GRAELLA, zeroline=False, row=fila, col=columna)
        figura.update_yaxes(automargin=True, row=fila, col=columna)

    alcada_panell = max(150, alcada_barra * int(taula.groupby("Parella posicions").size().max()) + 80)
    figura.update_layout(
        **_LAYOUT_BASE,
        height=alcada_panell * files,
        # Barres primes però juntes: el que es llegeix és la LLARGADA (el +/-),
        # no el gruix ni l'aire que hi ha entremig. El gruix real és
        # alcada_barra * (1 - bargap), així que les dues xifres van lligades.
        bargap=0.25,
        showlegend=False,
    )
    figura.update_annotations(font_size=13)
    return figura


def barres_sistemes_per_jugadora(taula: pd.DataFrame, columnes: int = 3) -> go.Figure:
    """
    Un panell per jugadora: quants cops es juga cada sistema amb ella a la posició
    escollida, amb els punts que ha donat el sistema escrits sobre la barra.

    L'alçada de la barra és la freqüència i el número és els punts: són dues
    coses diferents i per això el número va etiquetat, no encastat a l'escala.
    """
    if taula.empty:
        return _figura_buida("Cap dada per a aquesta posició amb els filtres actuals.")

    jugadores = taula.groupby("Jugadora")["Jugades"].sum().sort_values(ascending=False).index.tolist()
    files = math.ceil(len(jugadores) / columnes)

    figura = make_subplots(
        rows=files,
        cols=columnes,
        subplot_titles=[f"{j} <sub>({int(taula.loc[taula['Jugadora'] == j, 'Jugades'].sum())} jug.)</sub>" for j in jugadores],
        vertical_spacing=max(0.06, 0.42 / files),
        horizontal_spacing=0.08,
    )

    for i, jugadora in enumerate(jugadores):
        subconjunt = taula[taula["Jugadora"] == jugadora].sort_values("Jugades", ascending=False)
        fila, columna = i // columnes + 1, i % columnes + 1
        figura.add_trace(
            go.Bar(
                x=subconjunt[cfg.COL_TACTICA],
                y=subconjunt["Jugades"],
                marker=dict(color=cfg.COLORS_SERIE[0], line=dict(color="#ffffff", width=2)),
                text=subconjunt["Punts"],
                textposition="outside",
                customdata=subconjunt[["Punts", "Punts/jugada"]],
                hovertemplate=(
                    f"<b>{jugadora}</b><br>%{{x}}<br>Jugades: %{{y}}<br>Punts: %{{customdata[0]}}"
                    "<br>Punts/jugada: %{customdata[1]:.2f}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=fila,
            col=columna,
        )
        figura.update_xaxes(tickangle=-45, tickfont=dict(size=10), row=fila, col=columna)
        figura.update_yaxes(gridcolor=cfg.GRAELLA, zeroline=False, row=fila, col=columna)

    figura.update_layout(**_LAYOUT_BASE, height=max(340, 300 * files), bargap=0.35, showlegend=False)
    figura.update_annotations(font_size=13)
    return figura


def barres_rebot_per_periode(
    taula: pd.DataFrame,
    potencial: bool = True,
    alcada: int = 320,
    agregat: bool = False,
) -> go.Figure:
    """
    Rebot ofensiu i punts de segona oportunitat, per període.

    Amb `agregat`, es dibuixa un sol grup de barres amb la suma de tots els
    períodes en comptes d'un grup per període.

    Amb `potencial`, sobre cada barra de punts s'hi dibuixa el tram que falta
    fins al sostre teòric (`metriques.PUNTS_PER_RO` punts per rebot ofensiu):
    una línia vertical DISCONTÍNUA del mateix color que la barra, del valor
    real fins al sostre. Discontínua i a sobre de la seva barra, en comptes
    d'una línia horitzontal creuant el gràfic: així el sostre queda lligat
    visualment a la barra que qualifica i no es confon amb una sèrie més.

    L'eix X es fa numèric a propòsit: amb `barmode="group"` cada sèrie es
    dibuixa desplaçada del centre de la categoria, i per posar la línia damunt
    de la seva barra cal calcular aquest desplaçament, cosa que amb un eix de
    categories no es pot fer.
    """
    if taula.empty:
        return _figura_buida("Les jornades seleccionades no tenen columnes de rebot anotades.")

    dades = taula[taula[cfg.COL_PERIODE] == "Total"] if agregat else taula[taula[cfg.COL_PERIODE] != "Total"]
    if dades.empty:
        return _figura_buida("Sense períodes amb dades de rebot.")

    series = [
        ("RO a favor", cfg.DIVERGENT_POS, None),
        ("Punts RO a favor", "#86b6ef", "Potencial RO a favor"),
        ("RO en contra", cfg.DIVERGENT_NEG, None),
        ("Punts RO rival", "#f3ad91", "Potencial RO rival"),
    ]
    presents = [(nom, color, sostre) for nom, color, sostre in series if nom in dades.columns]
    if not presents:
        return _figura_buida("Sense columnes de rebot per dibuixar.")

    posicions = list(range(len(dades)))
    etiquetes = ["Tots els períodes"] if agregat else [f"Període {p}" for p in dades[cfg.COL_PERIODE]]
    marques = ["Total"] if agregat else dades[cfg.COL_PERIODE].tolist()

    figura = go.Figure()
    for nom, color, _ in presents:
        figura.add_trace(
            go.Bar(
                x=posicions,
                y=dades[nom],
                name=nom,
                marker=dict(color=color, line=dict(color="#ffffff", width=2)),
                text=[f"{v:.0f}" for v in dades[nom]],
                textposition="outside",
                textfont=dict(size=10, color=color),
                # Sense això, l'etiqueta de la barra més alta queda tallada per
                # la vora superior en comptes de desplaçar l'escala.
                cliponaxis=False,
                customdata=etiquetes,
                hovertemplate=f"<b>{nom}</b><br>%{{customdata}}: %{{y}}<extra></extra>",
            )
        )

    if potencial:
        # Geometria de barmode="group": el grup ocupa (1 - bargap) de l'ample
        # de la categoria i es reparteix en parts iguals entre les sèries.
        # bargroupgap només aprima cada barra, no en mou el centre.
        ample_grup = 1 - _REBOT_BARGAP
        pas = ample_grup / len(presents)
        primera = True

        for index, (nom, color, sostre) in enumerate(presents):
            if not sostre or sostre not in dades.columns:
                continue
            desplacament = -ample_grup / 2 + (index + 0.5) * pas

            for posicio, (real, cim) in enumerate(zip(dades[nom], dades[sostre])):
                if cim <= real:
                    continue
                figura.add_trace(
                    go.Scatter(
                        x=[posicio + desplacament] * 2,
                        y=[real, cim],
                        mode="lines",
                        line=dict(color=color, width=2, dash="dot"),
                        name="Sostre teòric",
                        legendgroup="sostre",
                        showlegend=primera,
                        hovertemplate=(
                            f"<b>{sostre}</b><br>Sostre: {cim:.0f}<br>Real: {real:.0f}<extra></extra>"
                        ),
                    )
                )
                # Barreta al capdamunt amb el valor: sense ella la línia sembla
                # que segueixi amunt i no es veu on és exactament el sostre.
                figura.add_trace(
                    go.Scatter(
                        x=[posicio + desplacament],
                        y=[cim],
                        mode="markers+text",
                        marker=dict(color=color, size=10, symbol="line-ew", line=dict(color=color, width=2)),
                        text=[f"{cim:.0f}"],
                        textposition="top center",
                        # Cursiva per distingir-lo d'un valor real: el sostre no
                        # ha passat, és el que hauria pogut passar.
                        textfont=dict(size=10, color=color, style="italic"),
                        cliponaxis=False,
                        legendgroup="sostre",
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
                primera = False

    figura.update_layout(
        **_LAYOUT_BASE,
        barmode="group",
        bargap=_REBOT_BARGAP,
        bargroupgap=0.08,
        title=dict(
            text="Rebot ofensiu i segona oportunitat" + ("" if agregat else " per període"),
            font=dict(size=15),
        ),
        xaxis=dict(
            title=None if agregat else "Període",
            tickmode="array",
            tickvals=posicions,
            ticktext=marques,
            range=[-0.6, len(posicions) - 0.4],
        ),
        yaxis=dict(title="Rebots / punts", gridcolor=cfg.GRAELLA, zeroline=False, rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uniformtext=dict(minsize=8, mode="hide"),
        height=alcada,
    )
    return figura


def barres_desenllac_jugadora(
    taula: pd.DataFrame,
    titol: str = "Com acaben les seves jugades",
    etiqueta_valor: str = "Jugades",
) -> go.Figure:
    """
    Desenllaços d'una jugadora com a finalitzadora, de millor a pitjor.

    Barres i no un pie: aquí interessa comparar volums entre desenllaços, i
    l'escala de qualitat ja va donada per l'ordre de l'eix, no cal la lectura
    de "parts d'un tot" que sí té sentit a `pies_desenllac_per_sistema`.
    """
    if taula.empty:
        return _figura_buida("Aquesta jugadora no consta com a finalitzadora de cap jugada.")

    # De pitjor a millor de baix a dalt: a un eix Y invertit, el primer de
    # l'ordre canònic acaba a dalt de tot.
    ordre = _ordena_desenllacos(taula["Desenllac"].tolist())
    taula = taula.set_index("Desenllac").loc[reversed(ordre)].reset_index()

    colors = [cfg.COLORS_DESENLLAC.get(d, cfg.NEUTRE) for d in taula["Desenllac"]]
    figura = go.Figure(
        go.Bar(
            x=taula["Jugades"],
            y=taula["Desenllac"],
            orientation="h",
            marker=dict(color=colors, line=dict(color="#ffffff", width=1)),
            text=[f"{int(j)}" for j in taula["Jugades"]],
            textposition="outside",
            customdata=taula[["Punts"]],
            hovertemplate=f"<b>%{{y}}</b><br>{etiqueta_valor}: %{{x}}<br>Punts: %{{customdata[0]}}<extra></extra>",
        )
    )
    figura.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=titol, font=dict(size=15)),
        xaxis=dict(title=etiqueta_valor, gridcolor=cfg.GRAELLA, zeroline=False),
        yaxis=dict(title=None, automargin=True),
        height=max(280, 28 * len(taula) + 110),
        showlegend=False,
        bargap=0.3,
    )
    return figura


def barres_recompte(
    taula: pd.DataFrame,
    columna_etiqueta: str,
    columna_valor: str,
    titol: str,
    alcada_per_barra: int = 26,
) -> go.Figure:
    """
    Barres horitzontals d'un comptatge simple, de més a menys.

    Un sol color i no l'escala divergent: aquí no hi ha signe (no es poden
    agafar rebots negatius), i pintar-ho de verd/taronja suggeriria una
    valoració de bo/dolent que el comptatge tot sol no dona.
    """
    if taula.empty:
        return _figura_buida("Cap dada amb els filtres actuals.")

    dades = taula.sort_values(columna_valor, ascending=True)
    figura = go.Figure(
        go.Bar(
            x=dades[columna_valor],
            y=dades[columna_etiqueta],
            orientation="h",
            marker=dict(color=cfg.COLORS_SERIE[0], line=dict(color="#ffffff", width=1)),
            text=dades[columna_valor],
            textposition="outside",
            hovertemplate=f"<b>%{{y}}</b><br>{columna_valor}: %{{x}}<extra></extra>",
        )
    )
    figura.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=titol, font=dict(size=15)),
        xaxis=dict(title=columna_valor, gridcolor=cfg.GRAELLA, zeroline=False),
        yaxis=dict(title=None, automargin=True),
        height=max(300, alcada_per_barra * len(dades) + 110),
        showlegend=False,
        bargap=0.3,
    )
    return figura


def _figura_buida(missatge: str) -> go.Figure:
    """Placeholder honest quan un filtre deixa el gràfic sense dades."""
    figura = go.Figure()
    figura.add_annotation(
        text=missatge, showarrow=False, font=dict(size=14, color=cfg.TINTA_APAGADA), xref="paper", yref="paper", x=0.5, y=0.5
    )
    figura.update_layout(**_LAYOUT_BASE, height=220, xaxis=dict(visible=False), yaxis=dict(visible=False))
    return figura
