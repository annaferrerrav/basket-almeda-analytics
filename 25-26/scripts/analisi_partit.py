# -*- coding: utf-8 -*-
"""
Created on Sat Oct  4 14:07:16 2025

@author: AFERRERR
"""

import matplotlib.pyplot as plt
from pathlib import Path
import math
from itertools import combinations
import pandas as pd
import os

path="C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\Escritorio\\LF2 - 2025-56\\LF2\\"

# Variables
jornada = 1

path="C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\Escritorio\\LF2 - 2025-56\\LF2\\"

SHEET_NAME = "Playbyplay"

# Busca l'arxiu que contingui "J{jornada}" al nom
fitxer = None
for f in os.listdir(path):
    if f"j{jornada}-pbp" in f and f.endswith(".xlsx"):
        fitxer = os.path.join(path, f)
        break

if fitxer:
    df = pd.read_excel(fitxer)
    print(f"S'ha carregat correctament el fitxer: {fitxer}")
else:
    print(f"No s'ha trobat cap fitxer per a la jornada {jornada}")
    
# Ordenar cronològicament (ajusta si tens columna de temps o número de jugada)
df = df.sort_index()

"""
Anàlisi Jornada 1:
- Gràfic per combinacions (Tàctica, Desenllac) -> barres
- Gràfics per (jug 1, Tàctica) -> barres
- Tàctica més demanada per cada jug 1 -> taula + barres
- Nou: Pie chart per a cada tàctica (desenllaços)
"""

COLOR_MAP = {
    "T2F": "#fbb47f",        # naranja pastel suave
    "T2C": "#b5e7a0",        # verde pastel claro
    "T3F": "#fdd49e",        # naranja pastel más claro
    "T3C": "#77dd77",        # verde pastel medio
    "Falta (TLL)": "#ffdab9", # melocotón pastel
    "Falta": "#fff7a5",      # amarillo pastel
    "Pèrdua": "#fba0a0",     # rojo pastel
    "Banda": "#e6e6e6",      # gris pastel claro
    "Fons": "#cccccc"        # gris pastel medio
}

# Llegir dades

# Filtrar dades vàlides
df_clean = df[df["Tàctica"].notna() & (df["Tàctica"] != "-")]

# Ordre personalitzat
tactics_order = [
    "Go", "Play", "Siena","2 arriba",'Tac 35',
    "Contraatac", "Lliure", "Final",
    "Lado", "Boston","Pisa",
    #"Banda 35",
    "RO", "CD"
]

# Només deixar les tàctiques que existeixin al dataset
tactics = [t for t in tactics_order if t in df_clean["Tàctica"].unique()]

n = len(tactics)
cols = 3
rows = math.ceil(n / cols)

fig, axes = plt.subplots(rows, cols, figsize=(cols*5, rows*5))
axes = axes.flatten()

for i, t in enumerate(tactics):
    subset = df_clean[df_clean["Tàctica"] == t]
    counts = subset["Desenllac"].value_counts()

    # Colors segons COLOR_MAP
    colors = [COLOR_MAP.get(val, "#cccccc") for val in counts.index]

    axes[i].pie(
        counts,
        labels=counts.index,
        autopct=lambda p: int(round(p*sum(counts)/100)) if p > 0 else "",
        startangle=90,
        colors=colors
    )

    num_vegades = len(subset)
    punts_total = subset["PF"].sum()

    axes[i].set_title(
        f"{t} ({num_vegades})\nPunts a favor: {punts_total}",
        fontsize=14,
        weight="bold"
    )

# Eliminar subplots buits
for j in range(i+1, len(axes)):
    fig.delaxes(axes[j])

plt.tight_layout()
plt.show()



# Comprovem columnes mínimes necessàries
needed = {"jug 1", "Tàctica", "PF"}
missing = needed - set(df.columns)
if missing:
    raise ValueError(f"Falten columnes al full '{SHEET_NAME}': {missing}")

# ======= PREP: frequencies per (jug 1, Tactica) =======
counts = (
    df.groupby(["jug 1", "Tàctica"])
      .size()
      .reset_index(name="freq")
      .sort_values(["jug 1", "freq"], ascending=[True, False])
)

# Suma de punts per (jug 1, Tactica)
points = (
    df.groupby(["jug 1", "Tàctica"])["PF"]
      .sum()
      .reset_index(name="punts")
)

# Unim freq i punts
# %%
stats = counts.merge(points, on=["jug 1", "Tàctica"], how="left").fillna({"punts": 0})


jugadores = sorted(df["jug 1"].dropna().unique().tolist())
n = len(jugadores)

# Disseny dels subplots (graella)
COLS = 3
ROWS = math.ceil(n / COLS)

fig, axes = plt.subplots(ROWS, COLS, figsize=(COLS * 5, ROWS * 4))
if n == 1:
    axes = [axes]
else:
    axes = axes.flatten()

# ======= Dibuixem un bar chart per jug 1 =======
for i, j in enumerate(jugadores):
    ax = axes[i]
    sub = stats[stats["jug 1"] == j]

    if sub.empty:
        ax.axis("off")
        continue

    # Barres
    bars = ax.bar(sub["Tàctica"], sub["freq"])  # no especifiquem colors

    ax.set_title(str(j))
    ax.set_ylabel("Freqüència")
    ax.set_xlabel("Tàctica")
    ax.tick_params(axis="x", labelrotation=45)

    # Etiquetes DINS la barra: punts totals per tàctica d'aquesta jugadora
    ymax = 0
    for bar, punts in zip(bars, sub["punts"]):
        h = bar.get_height()
        ymax = max(ymax, h)
        if h > 0.6:  # suficient alçada per posar el text dins
            ax.text(bar.get_x() + bar.get_width()/2, h/2, str(int(punts)),
                    ha="center", va="center", fontsize=9)
        else:
            # si la barra és molt baixa, dibuixa el text just a sobre
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, str(int(punts)),
                    ha="center", va="bottom", fontsize=9)

    # Marges verticals perquè no es tallin etiquetes sobre-barra
    ax.set_ylim(0, max(ymax, 1) * 1.15)

# Elimina subplots buits si n'hi ha
for j in range(i + 1, len(axes)):
    fig.delaxes(axes[j])

fig.suptitle(f"{SHEET_NAME} — Freqüència de sistemes jugats i PF", fontsize=14)
plt.tight_layout()
plt.show()

# (Opcional) Desa la figura
# fig.savefig(f"{SHEET_NAME}_freq_tactiques_per_jug1_punts_dins.png", d_




#+/-






# ==== VALIDACIONS MÍNIMES ====
needed_cols = {"PF", "PC", "Periode", "Minut", "jug 1", "jug 2", "jug 3", "jug 4", "jug 5"}
missing = needed_cols - set(df.columns)
if missing:
    raise ValueError(f"Falten columnes al full '{SHEET_NAME}': {missing}")

# ==== ORDRE CRONOLÒGIC I DIFERENCIALS ====
df = df.sort_values(["Periode", "Minut"]).reset_index(drop=True)

# dPF/dPC = increments respecte fila anterior (primera fila agafa el seu valor absolut)
df["dPF"] = df["PF"].diff().fillna(df["PF"]).astype(float)
df["dPC"] = df["PC"].diff().fillna(df["PC"]).astype(float)

# ==== CÀLCUL PLUS/MINUS ====
plus_minus = {}

for _, row in df.iterrows():
    players_on_court = [row["jug 1"], row["jug 2"], row["jug 3"], row["jug 4"], row["jug 5"]]
    players_on_court = [p for p in players_on_court if pd.notna(p)]
    delta = float(row["dPF"]) - float(row["dPC"])  # suma si PF puja, resta si PC puja
    if delta != 0:
        for p in players_on_court:
            plus_minus[p] = plus_minus.get(p, 0.0) + delta

# ==== RESULTAT EN DATAFRAME ====
pm_df = (
    pd.DataFrame(list(plus_minus.items()), columns=["Jugadora", "+/-"])
      .sort_values("+/-", ascending=False, ignore_index=True)
)

print(pm_df)

# (Opcional) Desa el resultat
# OUT_CSV = EXCEL_PATH.with_name(f"{SHEET_NAME}_plus_minus.csv")
# pm_df.to_csv(OUT_CSV, index=False)
# print(f"Desat a: {OUT_CSV}")

import pandas as pd
from pathlib import Path
from itertools import combinations
import matplotlib.pyplot as plt
import matplotlib as mpl


MIN_CO_APARICIONS = 1

# ==== LECTURA ====
df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

# ==== VALIDACIONS ====
needed_cols = {"PF", "PC", "Periode", "Minut", "jug 1", "jug 2", "jug 3", "jug 4", "jug 5"}
missing = needed_cols - set(df.columns)
if missing:
    raise ValueError(f"Falten columnes al full '{SHEET_NAME}': {missing}")

# ==== ORDRE CRONOLÒGIC I DIFERENCIALS ====
df = df.sort_values(["Periode", "Minut"]).reset_index(drop=True)
df["dPF"] = df["PF"].diff().fillna(df["PF"]).astype(float)
df["dPC"] = df["PC"].diff().fillna(df["PC"]).astype(float)
df["delta"] = df["dPF"] - df["dPC"]

# ==== +/− PER PARELLES ====
pair_pm, pair_counts = {}, {}

for _, row in df.iterrows():
    players = [row["jug 1"], row["jug 4"], row["jug 5"]]
    players = [p for p in players if pd.notna(p)]
    if len(players) < 2:
        continue
    delta = float(row["delta"])
    for a, b in combinations(sorted(players), 2):
        key = (a, b)
        pair_pm[key] = pair_pm.get(key, 0.0) + delta
        pair_counts[key] = pair_counts.get(key, 0) + 1

pairs = []
for key in pair_pm:
    a, b = key
    pairs.append({
        "Parella": f"{a} & {b}",
        "+/-": pair_pm[key],
        "co_aparicions": pair_counts.get(key, 0)
    })

pair_df = pd.DataFrame(pairs).sort_values("+/-", ascending=True, ignore_index=True)
if MIN_CO_APARICIONS > 1:
    pair_df = pair_df[pair_df["co_aparicions"] >= MIN_CO_APARICIONS].reset_index(drop=True)

# ==== GRÀFIC BARRES HORITZONTALS ====
vals = pair_df["+/-"].values
norm = mpl.colors.Normalize(vmin=vals.min(), vmax=vals.max())
cmap = plt.cm.RdYlGn  # verd (+) a vermell (−), escala contínua
colors = cmap(norm(vals))

fig, ax = plt.subplots(figsize=(10, max(6, 0.3 * len(pair_df))))
bars = ax.barh(pair_df["Parella"], vals, color=colors)
ax.axvline(0, color="black", linewidth=1)
ax.set_xlabel("+/−")
ax.set_title(f"{SHEET_NAME} — +/− per parelles", weight="bold")

# Etiquetes dins o fora
for bar, val in zip(bars, vals):
    x = bar.get_width()
    y = bar.get_y() + bar.get_height() / 2
    if abs(x) > 1:  # suficient espai per posar-ho dins
        ax.text(x - (0.5 if x > 0 else -0.5), y, f"{val:.0f}",
                va="center", ha="right" if x > 0 else "left",
                color="black", fontsize=8, weight="bold")
    else:  # molt petit -> el posem a fora
        ax.text(x + (0.5 if x >= 0 else -0.5), y, f"{val:.0f}",
                va="center", ha="left" if x >= 0 else "right",
                color="black", fontsize=8, weight="bold")

plt.tight_layout()
plt.show()


import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np

# ==== Paràmetres segons el teu fitxer ====
PLAYER_COL = "Finalitzadora"
ASSIST_COL = "Assist"  # es considera "amb assistència" si no és NaN/buit
POINTS_COL = "PF"
TACTICS_COL = "Tàctica"
SHEET = SHEET_NAME
PATH = EXCEL_PATH
# ========================================

# Ordre de tàctiques demanat
tactics_order = [
    "Go", "Play", "Siena",
    "Contraatac", "Lliure", "Final",
    "Lado", "Boston", "Banda 35",
    "RO", "RD"
]

# Llegim i netegem
df = pd.read_excel(PATH, sheet_name=SHEET)
df_clean = df[df[TACTICS_COL].notna() & (df[TACTICS_COL] != "-")].copy()

# Normalitzem buits a NaN per a Assistència i Finalitzadora
df_clean[ASSIST_COL] = df_clean[ASSIST_COL].replace("", pd.NA)
df_clean[PLAYER_COL] = df_clean[PLAYER_COL].replace("", pd.NA)

# Ens quedem només amb tàctiques existents al dataset
tactics = [t for t in tactics_order if t in df_clean[TACTICS_COL].unique()]
n = len(tactics)

# Layout: 3 columnes, barres primes
cols = 3
rows = math.ceil(n / cols)
bar_width = 0.28  # <<<< barres primes

fig, axes = plt.subplots(rows, cols, figsize=(cols*6.2, rows*5.2), squeeze=False)

for i, t in enumerate(tactics):
    r, c = divmod(i, cols)
    ax = axes[r][c]

    subset = df_clean[df_clean[TACTICS_COL] == t].copy()

    # Agreguem punts totals per finalitzadora
    total_pts = (
        subset.groupby(PLAYER_COL, dropna=False)[POINTS_COL]
        .sum()
        .sort_values(ascending=False)
    )

    # Punts amb assistència per finalitzadora (files on Assistència no és NaN)
    assisted_pts = (
        subset[subset[ASSIST_COL].notna()]
        .groupby(PLAYER_COL, dropna=False)[POINTS_COL]
        .sum()
        .reindex(total_pts.index, fill_value=0)
    )

    # Punts sense assistència
    unassisted_pts = (total_pts - assisted_pts).clip(lower=0)

    # Etiquetes: substituir NaN per "Sense finalitzadora"
    player_labels = total_pts.index.to_series().fillna("Sense finalitzadora").astype(str)
    x = np.arange(len(total_pts))

    if len(x) == 0:
        ax.text(0.5, 0.5, "Sense punts", ha="center", va="center", fontsize=12)
        ax.set_title(f"{t} • Anotadores: 0 • Total PF: 0", fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        continue

    # Barres apilades (mateixa barra, segments de diferent color)
    b1 = ax.bar(x, unassisted_pts.values, width=bar_width, label="Sense assistència")
    b2 = ax.bar(x, assisted_pts.values,  width=bar_width, bottom=unassisted_pts.values, label="Amb assistència")

    # Etiqueta amb el total al capdamunt (p.e. 7)
    totals = (unassisted_pts + assisted_pts).astype(int)
    for xi, tot in zip(x, totals):
        if tot > 0:
            ax.annotate(
                f"{tot}",
                xy=(xi, tot),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center", va="bottom", fontsize=9
            )

    # Títol i eixos
    num_scorers = (totals > 0).sum()
    total_points = int(totals.sum())
    ax.set_title(f"{t} • Anotadores: {num_scorers} • Total PF: {total_points}", fontweight="bold")
    ax.set_ylabel("Punts (PF)")
    ax.set_xlabel("Finalitzadora")
    ax.set_xticks(x)
    ax.set_xticklabels(player_labels, rotation=45, ha="right")

# Elimina subplots buits si sobren
total_axes = rows * cols
for j in range(n, total_axes):
    rr, cc = divmod(j, cols)
    fig.delaxes(axes[rr][cc])

# Llegenda comuna un cop (fora dels subplots) perquè no molesti
handles, labels = axes[0][0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.995), borderaxespad=0.8)

plt.tight_layout(rect=[0, 0, 1, 0.96])  # deixem espai a dalt per la llegenda comuna
plt.show()

import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np

# ==== Paràmetres segons el teu fitxer ====
PLAYER_FIN_COL = "Finalitzadora"
PLAYER_AST_COL = "Assist"
POINTS_COL = "PF"
TACTICS_COL = "Tàctica"
SHEET = SHEET_NAME
PATH = EXCEL_PATH
# ========================================

# Ordre de tàctiques demanat
tactics_order = [
    "Go", "Play", "Siena",
    "Contraatac", "Lliure", "Final",
    "Lado", "Boston", "Banda 35",
    "RO", "RD"
]

# Llegim i netegem
df = pd.read_excel(PATH, sheet_name=SHEET)
df_clean = df[df[TACTICS_COL].notna() & (df[TACTICS_COL] != "-")].copy()

# Normalitzem buits a NaN
df_clean[PLAYER_FIN_COL] = df_clean[PLAYER_FIN_COL].replace("", pd.NA)
df_clean[PLAYER_AST_COL] = df_clean[PLAYER_AST_COL].replace("", pd.NA)

# Ens quedem només amb tàctiques existents al dataset
tactics = [t for t in tactics_order if t in df_clean[TACTICS_COL].unique()]
n = len(tactics)

# Layout: 3 columnes, barres primes
cols = 3
rows = math.ceil(n / cols)
bar_width = 0.28      # barres primes
gap = 0.08            # petit espai entre grups (ajuda visual)
min_slots = 5         # mínim d'espais X perquè 1-2 barres no omplin tot el subplot

fig, axes = plt.subplots(rows, cols, figsize=(cols*6.6, rows*5.4), squeeze=False)

for i, t in enumerate(tactics):
    r, c = divmod(i, cols)
    ax = axes[r][c]

    subset = df_clean[df_clean[TACTICS_COL] == t].copy()

    # Punts com a finalitzadora per jugadora
    pts_fin = subset.groupby(PLAYER_FIN_COL, dropna=False)[POINTS_COL].sum()

    # Punts com a assistent per jugadora (sumem els PF de la jugada on figura com a assistent)
    pts_ast = subset.groupby(PLAYER_AST_COL, dropna=False)[POINTS_COL].sum()

    # Construïm l'univers de noms (finalitzadores ∪ assistents)
    all_names = pd.Index(set(pts_fin.index.dropna()).union(set(pts_ast.index.dropna())))
    all_names = all_names.sort_values()

    # Sèries reindexades i netes
    fin_vals = pts_fin.reindex(all_names, fill_value=0).astype(int)
    ast_vals = pts_ast.reindex(all_names, fill_value=0).astype(int)

    # Si no hi ha dades, subplot buit informatiu
    if (fin_vals.sum() + ast_vals.sum()) == 0:
        ax.text(0.5, 0.5, "Sense punts", ha="center", va="center", fontsize=12)
        ax.set_title(f"{t} • Finalitzadores/Assistents: 0 • Total PF: 0", fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        continue

    # Posicions X i amplada visual constant encara que hi hagi pocs noms
    k = len(all_names)
    x = np.arange(k)
    # dues barres per nom (en grup): finalitzadora a l'esquerra, assistència a la dreta
    x_fin = x - (bar_width/2 + gap/2)
    x_ast = x + (bar_width/2 + gap/2)

    # Dibuix
    bars_fin = ax.bar(x_fin, fin_vals.values, width=bar_width, label="Punts (Finalitzadora)", color="#77aadd")
    bars_ast = ax.bar(x_ast, ast_vals.values, width=bar_width, label="Punts (Assistència)", color="#f6a04d")

    # Etiquetes al capdamunt (només si > 0)
    for xi, val in zip(x_fin, fin_vals.values):
        if val > 0:
            ax.annotate(f"{int(val)}", xy=(xi, val), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9)
    for xi, val in zip(x_ast, ast_vals.values):
        if val > 0:
            ax.annotate(f"{int(val)}", xy=(xi, val), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9)

    # Títol i eixos
    num_people = ((fin_vals > 0) | (ast_vals > 0)).sum()
    total_points = int(fin_vals.sum())  # total PF compta punts anotats (no doble-comptem assistències)
    ax.set_title(f"{t} • Persones implicades: {num_people} • Total PF: {total_points}", fontweight="bold")

    ax.set_ylabel("Punts (PF)")
    ax.set_xlabel("Jugadora")

    # Etiquetes X (substituïm NaN per text si calgués)
    labels = pd.Series(all_names).fillna("Sense nom").astype(str).tolist()
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")

    # LÍMITS X: garantim espai mínim perquè 1-2 barres no omplin tot
    right_slots = max(min_slots, k)
    ax.set_xlim(-0.5, right_slots - 0.5)

# Elimina subplots buits
total_axes = rows * cols
for j in range(n, total_axes):
    rr, cc = divmod(j, cols)
    fig.delaxes(axes[rr][cc])

# Llegenda comuna
handles, labels = axes[0][0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
           bbox_to_anchor=(0.5, 0.995), borderaxespad=0.8)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()


import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np

# ==== Parámetros según tu fichero ====
PLAYER_FIN_COL = "Finalitzadora"
ASSIST_COL     = "Assist"
POINTS_COL     = "PF"
TACTICS_COL    = "Tàctica"
SHEET          = SHEET_NAME
PATH           = EXCEL_PATH
# =====================================

# Orden de tácticas deseado
tactics_order = [
    "Go", "Play", "Siena",
    "Contraatac", "Lliure", "Final",
    "Lado", "Boston", "Banda 35",
    "RO", "RD"
]

# Leemos y limpiamos
df = pd.read_excel(PATH, sheet_name=SHEET)
df_clean = df[df[TACTICS_COL].notna() & (df[TACTICS_COL] != "-")].copy()
df_clean[PLAYER_FIN_COL] = df_clean[PLAYER_FIN_COL].replace("", pd.NA)
df_clean[ASSIST_COL]     = df_clean[ASSIST_COL].replace("", pd.NA)

# Tácticas que existen en el dataset
tactics = [t for t in tactics_order if t in df_clean[TACTICS_COL].unique()]
n = len(tactics)

# Layout: 3 columnas, barras primas
cols = 3
rows = math.ceil(n / cols)
bar_width = 0.28
min_slots = 5  # asegura espacio lateral cuando hay 1-2 nombres

fig, axes = plt.subplots(rows, cols, figsize=(cols*6.6, rows*5.4), squeeze=False)

for i, t in enumerate(tactics):
    r, c = divmod(i, cols)
    ax = axes[r][c]

    subset = df_clean[df_clean[TACTICS_COL] == t].copy()

    # Puntos como finalizadora por jugadora (TOTAL)
    pts_total_fin = (
        subset.groupby(PLAYER_FIN_COL, dropna=False)[POINTS_COL]
        .sum()
    )

    # Puntos ASISTIDOS (solo jugadas con Assistència no nulo), imputados a la finalizadora
    pts_assisted = (
        subset[subset[ASSIST_COL].notna()]
        .groupby(PLAYER_FIN_COL, dropna=False)[POINTS_COL]
        .sum()
    )

    # Unimos índices y ordenamos por total descendente
    all_players = pd.Index(set(pts_total_fin.index.dropna()) | set(pts_assisted.index.dropna()))
    if len(all_players) == 0:
        ax.text(0.5, 0.5, "Sense punts", ha="center", va="center", fontsize=12)
        ax.set_title(f"{t} • Finalitzadores: 0 • Total PF: 0", fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        continue

    total_vals = pts_total_fin.reindex(all_players, fill_value=0).astype(int)
    asst_vals  = pts_assisted.reindex(all_players,  fill_value=0).astype(int)
    unass_vals = (total_vals - asst_vals).clip(lower=0)

    # Orden por total descendente
    order = total_vals.sort_values(ascending=False).index
    total_vals = total_vals.reindex(order)
    asst_vals  = asst_vals.reindex(order)
    unass_vals = unass_vals.reindex(order)

    # Eje X y barras apiladas
    x = np.arange(len(order))
    bars_unass = ax.bar(x, unass_vals.values, width=bar_width, label="Punts sense assistència", color="#77aadd")
    bars_asst  = ax.bar(x, asst_vals.values,  width=bar_width, bottom=unass_vals.values, label="Punts assistits", color="#f6a04d")

    # Etiquetas: valor del segmento sin asistencia y del asistido (cada uno sobre su segmento)
    for xi, u, a in zip(x, unass_vals.values, asst_vals.values):
        if u > 0:
            ax.annotate(f"{int(u)}",
                        xy=(xi, u/2), ha="center", va="center",
                        fontsize=9)
        if a > 0:
            ax.annotate(f"{int(a)}",
                        xy=(xi, u + a/2), ha="center", va="center",
                        fontsize=9)

    # Título y ejes
    num_players   = ((total_vals > 0)).sum()
    total_points  = int(total_vals.sum())
    total_assists = int(asst_vals.sum())  # puntos anotados que fueron asistidos
    ax.set_title(f"{t} • Finalitzadores: {num_players} • PF totals: {total_points} (assistits: {total_assists})",
                 fontweight="bold")

    labels = pd.Series(order).fillna("Sense finalitzadora").astype(str).tolist()
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Punts (PF)")
    ax.set_xlabel("Finalitzadora")

    # Mantener barras finas aunque haya 1 jugadora
    right_slots = max(min_slots, len(order))
    ax.set_xlim(-0.5, right_slots - 0.5)

# Eliminar subplots vacíos
total_axes = rows * cols
for j in range(n, total_axes):
    rr, cc = divmod(j, cols)
    fig.delaxes(axes[rr][cc])

# Leyenda común
handles, labels = axes[0][0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
           bbox_to_anchor=(0.5, 0.995), borderaxespad=0.8)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()


