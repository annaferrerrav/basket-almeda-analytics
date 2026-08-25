# -*- coding: utf-8 -*-
"""
Created on Mon Oct 20 16:16:24 2025

@author: AFERRERR
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import math
from itertools import combinations
import numpy as np


path="C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\Escritorio\\LF2 - 2025-56\\LF2\\pbp\\"
# %%
EXCEL_PATH = path + "j25-pbp.xlsx"   # posa la ruta al teu fitxer


df = pd.read_excel(EXCEL_PATH)


##gràfic piechart jugades!

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

'''
COLOR_MAP = {
    "t2f": "#fbb47f",        # naranja pastel suave
    "t2c": "#b5e7a0",        # verde pastel claro
    "t3f": "#fdd49e",        # naranja pastel más claro
    "t3c": "#77dd77",        # verde pastel medio
    "Falta (TLL)": "#ffdab9", # melocotón pastel
    "falta": "#fff7a5",      # amarillo pastel
    "pèrdua": "#fba0a0",     # rojo pastel
    "banda": "#e6e6e6",      # gris pastel claro
    "fons": "#cccccc"        # gris pastel medio
}


# Llegir dades

# Filtrar dades vàlides
df_clean = df[df["Tàctica"].notna() & (df["Tàctica"] != "-")]

# Ordre personalitzat
tactics_order = [
    "Go", "Play", "Siena","2 arriba","2 mano", "2 lado",
    "Contratac", "Lliure", "Final", "tac35",
    "Zona 2", "Zona 4",
    "Lado", "Boston","Pisa",
    "Banda 35",
    "RO", "CD"
]

# Només deixar les tàctiques que existeixin al dataset
tactics = [t for t in tactics_order if t in df_clean["Tàctica"].unique()]

n = len(tactics)
cols = 4
rows = math.ceil(n / cols)
fig, axes = plt.subplots(rows, cols, figsize=(cols*5, rows*5))
axes = axes.flatten()
for i, t in enumerate(tactics):
    subset = df_clean[df_clean["Tàctica"] == t]
    counts = subset["Desenllac"].value_counts()
    colors = [COLOR_MAP.get(val, "#cccccc") for val in counts.index]
    axes[i].pie(counts, labels=counts.index,   autopct=lambda p: int(round(p*sum(counts)/100)) if p > 0 else "",  startangle=90, colors=colors )
    num_vegades = len(subset)
    punts_total = subset["PF"].sum()
    axes[i].set_title( f"{t} ({num_vegades})\nPunts a favor: {punts_total}", fontsize=14, weight="bold")

# Eliminar subplots buits
for j in range(i+1, len(axes)): fig.delaxes(axes[j])
plt.tight_layout()
plt.show()
'''
# --- Config (sense canvis visuals) ---
COLOR_MAP = {
    "t2f": "#fbb47f",        # naranja pastel suave
    "t2c": "#b5e7a0",        # verde pastel claro
    "t3f": "#fdd49e",        # naranja pastel más claro
    "t3c": "#77dd77",        # verde pastel medio
    "falta (TLL)": "#ffdab9",# melocotón pastel
    "falta": "#fff7a5",      # amarillo pastel
    "pèrdua": "#fba0a0",     # rojo pastel
    "banda": "#e6e6e6",      # gris pastel claro
    "fons": "#cccccc"        # gris pastel medio
}

# Versió insensible a majúscules del mapa de colors
COLOR_MAP_NORM = {str(k).strip().lower(): v for k, v in COLOR_MAP.items()}

# --- Dades ---
# Filtrar dades vàlides i crear columnes normalitzades (lowercase + trim)
df_clean = df[df["Tàctica"].notna() & (df["Tàctica"].astype(str).str.strip() != "-")].copy()
df_clean["tactic_norm"] = df_clean["Tàctica"].astype(str).str.strip().str.lower()
df_clean["desenllac_norm"] = df_clean["Desenllac"].astype(str).str.strip().str.lower()

# --- Ordre personalitzat ---
tactics_order = [
    "go", "play", "siena","tac30", "tac33","tac34", "tac35","cuatro", "cinco", 
    "2 mano","2 arriba", "2 lado","bloc lado","pintura",
    "contratac", "lliure", "Final", "recuperació",
    "Zona 2", "Zona 4","zona libre", "triple","pissarra","miami",
    "Lado", "Boston","Pisa","Fons zona","portland", "fons 21"
    "banda 35","banda 34","zeta", 
    "RO", "CD"
]

# Mapes per conservar el format original però comparar en minúscules
order_norm = [t.lower() for t in tactics_order]
norm_to_original = {t.lower(): t for t in tactics_order}

# Només deixar les tàctiques que existeixin al dataset (comparant en minúscules)
present_norm = set(df_clean["tactic_norm"].unique())
tactics_norm = [t for t in order_norm if t in present_norm]         # per comparar/filtrar
tactics_show = [norm_to_original[t] for t in tactics_norm]          # per mostrar títol original

# --- Gràfics ---
n = len(tactics_norm)
cols = 4
rows = math.ceil(n / cols)
fig, axes = plt.subplots(rows, cols, figsize=(cols*5, rows*5))
axes = axes.flatten()

for i, t_norm in enumerate(tactics_norm):
    # Subset insensible a majúscules
    subset = df_clean[df_clean["tactic_norm"] == t_norm]

    # Comptes conservant etiquetes originals de "Desenllac" per mostrar bonic a la llegenda
    counts = subset["Desenllac"].value_counts()

    # Colors insensibles a majúscules (fent servir les etiquetes originals però normalitzades per buscar color)
    colors = [COLOR_MAP_NORM.get(str(lbl).strip().lower(), "#cccccc") for lbl in counts.index]

    axes[i].pie(
        counts,
        labels=counts.index,
        autopct=lambda p: int(round(p*sum(counts)/100)) if p > 0 else "",
        startangle=90,
        colors=colors
    )

    num_vegades = len(subset)
    punts_total = subset["PF"].sum()
    axes[i].set_title(f"{norm_to_original[t_norm]} ({num_vegades})\nPunts a favor: {punts_total}",
                      fontsize=14, weight="bold")

# Eliminar subplots buits
for j in range(n, len(axes)):
    fig.delaxes(axes[j])

plt.tight_layout()
plt.show()



PLAYER_FIN_COL = "Finalitzadora"
PLAYER_AST_COL = "Assist"
POINTS_COL = "PF"
TACTICS_COL = "Tàctica"
PATH = EXCEL_PATH

# Normalitzem buits a NaN
df_clean[PLAYER_FIN_COL] = df_clean[PLAYER_FIN_COL].replace("", pd.NA)
df_clean[PLAYER_AST_COL] = df_clean[PLAYER_AST_COL].replace("", pd.NA)

# Ens quedem només amb tàctiques existents al dataset
tactics = [t for t in tactics_order if t in df_clean[TACTICS_COL].unique()]
n = len(tactics)

# Layout: 3 columnes, barres primes
cols = 4
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




# Comprovem columnes mínimes necessàries
needed = {"jug 1", "Tàctica", "PF"}
missing = needed - set(df.columns)

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

fig.suptitle(f" — Freqüència de sistemes jugats i PF", fontsize=14)
plt.tight_layout()
plt.show()



# Definir columnas de jugadores y pares
target_pairs = [ ("jug 1", "jug 4"),  ("jug 1", "jug 5"), ("jug 2", "jug 4"), ("jug 3", "jug 4"),   ("jug 2", "jug 5"),   ("jug 3", "jug 5"),  ("jug 4", "jug 5"),
]

records = []
for idx, row in df.iterrows():
    pf = row["PF"]
    pc = row["PC"]
    for col_a, col_b in target_pairs:
        a, b = row[col_a], row[col_b]
        if pd.notna(a) and pd.notna(b) and a != "-" and b != "-":
            key = tuple(sorted([a, b]))
            records.append({
                "parella": f"{col_a}-{col_b}",
                "jug_a": key[0],
                "jug_b": key[1],
                "punts_favor": pf,
                "punts_contra": pc,
            })

# Crear DataFrame resumen
pairs_df = pd.DataFrame(records)
summary = (pairs_df
           .groupby(["parella", "jug_a", "jug_b"])
           .agg(
               aparicions=("punts_favor", "count"),
               punts_favor=("punts_favor", "sum"),
               punts_contra=("punts_contra", "sum")
           )
           .reset_index())
summary["+/-"] = summary["punts_favor"] - summary["punts_contra"]

# ========= Subplots =========
order_pairs = [ "jug 1-jug 4", "jug 1-jug 5",  "jug 2-jug 4", "jug 2-jug 5", "jug 3-jug 4", "jug 3-jug 5", "jug 4-jug 5"]

available = [p for p in order_pairs if p in summary["parella"].unique()]
n = len(available)
ncols = 2
nrows = math.ceil(n / ncols)

min_v = summary["+/-"].min() if not summary.empty else 0
max_v = summary["+/-"].max() if not summary.empty else 0
M = max(abs(min_v), abs(max_v))
xlim = (-1.1 * M, 1.1 * M) if M > 0 else (-1, 1)

fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(25, 4*nrows), squeeze=False)

for i, parella in enumerate(available):
    r, c = divmod(i, ncols)
    ax = axes[r][c]
    sub = (summary[summary["parella"] == parella]
           .sort_values(by="+/-", ascending=True)
           .copy())
    if sub.empty:
        ax.set_title(parella.replace("jug", "JUG"))
        ax.axis("off")
        continue

    labels = sub["jug_a"] + " - " + sub["jug_b"]
    bars = ax.barh(labels, sub["+/-"], color="#8ecae6")

    # Añadir valores dentro/derecha de cada barra
    for bar, value in zip(bars, sub["+/-"]):
        ax.text(
            bar.get_width() + (M * 0.02),
            bar.get_y() + bar.get_height()/2,
            f"{int(value):+d}",   # con signo +/-
            va="center", ha="left", fontsize=9, color="black"
        )

    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(xlim)
    ax.set_xlabel("+/-")
    ax.set_title(parella.replace("jug", "JUG"))
    ax.grid(axis="x", linestyle="--", alpha=0.3)

# Ocultar ejes vacíos
for j in range(i+1, nrows*ncols):
    r, c = divmod(j, ncols)
    axes[r][c].axis("off")

plt.tight_layout()
plt.show()



# ========= +/- individual per JUGADORA i POSICIÓ =========
position_cols = ["jug 1", "jug 2", "jug 3", "jug 4", "jug 5"]

indiv_records = []
for _, row in df.iterrows():
    pf = row["PF"]
    pc = row["PC"]
    for pos in position_cols:
        player = row[pos]
        if pd.notna(player) and player != "-":
            indiv_records.append({
                "jugadora": str(player).strip(),
                "posicio": pos,              # "jug 1"..."jug 5"
                "pf": pf,
                "pc": pc
            })

indiv_df = pd.DataFrame(indiv_records)

# Agrupar per jugadora i posició i calcular +/- individual
indiv_summary = (indiv_df
                 .groupby(["jugadora", "posicio"], as_index=False)
                 .agg(pf=("pf", "sum"),
                      pc=("pc", "sum"),
                      aparicions=("pf", "count"))
                )
indiv_summary["+/-"] = indiv_summary["pf"] - indiv_summary["pc"]

# Etiqueta "Nom - jugX"
indiv_summary["label"] = indiv_summary.apply(
    lambda r: f'{r["jugadora"]} - {r["posicio"].replace(" ", "")}', axis=1
)

# Ordenar per +/- (creixent)
indiv_plot = indiv_summary.sort_values(by="+/-", ascending=True).reset_index(drop=True)

# ========= Gràfic =========
plt.figure(figsize=(12, max(4, 0.4 * len(indiv_plot))))
bars = plt.barh(indiv_plot["label"], indiv_plot["+/-"])

# línia a zero i graella suau
plt.axvline(0, color="black", linewidth=0.8)
plt.grid(axis="x", linestyle="--", alpha=0.3)

# Valors al final de cada barra
M = indiv_plot["+/-"].abs().max() if not indiv_plot.empty else 0
for bar, value in zip(bars, indiv_plot["+/-"]):
    plt.text(
        bar.get_width() + (0.02 * (M if M > 0 else 1)),
        bar.get_y() + bar.get_height()/2,
        f"{int(value):+d}",
        va="center", ha="left", fontsize=9
    )

plt.xlabel("+/- individual (per posició jugada)")
plt.title("± per jugadora i posició (Nom - jugX)")
plt.tight_layout()
plt.show()

# (Opcional) si vols veure també les aparicions:
# display(indiv_summary.sort_values(["jugadora","posicio"]))


import pandas as pd
import matplotlib.pyplot as plt

# 1. LLEGIR L'EXCEL
# Canvia 'dades.xlsx' i 'Full1' pel nom del teu fitxer i full

# 2. TAULA RESUM PER PERÍODE
# Si les columnes "RO a favor" i "RO en contra" són 0/1,
# el 'sum' ja et dona el nombre de vegades.
taula = (
    df.groupby("Periode")
      .agg({
          "RO a favor": "sum",          # nombre de RO a favor
          "Punts RO a favor": "sum",    # punts després de RO a favor
          "RO en contra": "sum",        # nombre de RO en contra
          "Punts RO rival": "sum"       # punts del rival després de RO en contra
      })
      .reset_index()
)

# 3. RE-NOMENAR COLUMNES COM A LA TEVA TAULA
taula = taula.rename(columns={
    "Punts RO a favor": "PF de RO a favor",
    "Punts RO rival": "PF de RO en contra"
})

# 4. AFEGIR FILA TOTAL
totals = taula[["RO a favor", "PF de RO a favor",
                "RO en contra", "PF de RO en contra"]].sum()
totals["Periode"] = "total"

taula_final = pd.concat(
    [taula, totals.to_frame().T],
    ignore_index=True
)

print(taula_final)

# 5. GRÀFICA DE BARRES (sense la fila 'total')
taula_graf = taula.copy()   # només períodes 1,2,3,4

x = range(len(taula_graf))  # posicions base
amplada = 0.2

plt.figure(figsize=(10, 6))

plt.bar([i - 1.5*amplada for i in x],
        taula_graf["RO a favor"],
        width=amplada,
        label="RO a favor")

plt.bar([i - 0.5*amplada for i in x],
        taula_graf["RO en contra"],
        width=amplada,
        label="RO en contra")

plt.bar([i + 0.5*amplada for i in x],
        taula_graf["PF de RO a favor"],
        width=amplada,
        label="PF de RO a favor")

plt.bar([i + 1.5*amplada for i in x],
        taula_graf["PF de RO en contra"],
        width=amplada,
        label="PF de RO en contra")

plt.xticks(x, taula_graf["Periode"])
plt.xlabel("Periode")
plt.ylabel("Nombre / Punts")
plt.title("Resum RO per període")
plt.legend()
plt.tight_layout()
plt.show()


# ========= PF/PC "en pista" por jugadora (en cualquier jugX) + subplots por columna =========
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

# --- columnas jugadoras existentes (jug 1..jug 5) ---
jug_cols = [c for c in ["jug 1", "jug 2", "jug 3", "jug 4", "jug 5"] if c in df.columns]
if not jug_cols:
    raise ValueError("No se han encontrado columnas 'jug 1'...'jug 5' en el dataframe.")

# --- asegurar PF/PC existen ---
for c in ["PF", "PC"]:
    if c not in df.columns:
        raise ValueError(f"Falta la columna '{c}' en el dataframe.")

# --- normalizar nombres (quitar espacios, tratar '-' como vacío) ---
df_j = df.copy()
for c in jug_cols:
    df_j[c] = df_j[c].astype(str).str.strip()
    df_j.loc[df_j[c].isin(["", "-", "nan", "NaN", "None"]), c] = np.nan

# --- universo de jugadoras (todos los nombres que salen en jug_cols) ---
all_players = (
    pd.unique(df_j[jug_cols].values.ravel("K"))
)
all_players = [p for p in all_players if pd.notna(p)]
all_players = sorted(set(all_players), key=lambda x: str(x))

# --- tabla global: PF/PC cuando la jugadora está en pista (en cualquiera de las columnas) ---
records_global = []
for player in all_players:
    on_court = df_j[jug_cols].eq(player).any(axis=1)
    pf_sum = df_j.loc[on_court, "PF"].sum()
    pc_sum = df_j.loc[on_court, "PC"].sum()
    apps   = int(on_court.sum())
    records_global.append({
        "jugadora": player,
        "apariciones": apps,
        "PF_en_pista": pf_sum,
        "PC_en_pista": pc_sum,
        "+/-": pf_sum - pc_sum
    })

tabla_global = pd.DataFrame(records_global).sort_values(by="+/-", ascending=False).reset_index(drop=True)
print("\n=== TAULA GLOBAL (en pista a qualsevol posició) ===")
print(tabla_global)

# --- tabla por posición (jug 1..jug 5): PF/PC cuando está en pista EN ESA COLUMNA ---
pos_records = []
for pos in jug_cols:
    for player in all_players:
        in_pos = df_j[pos].eq(player)
        pf_sum = df_j.loc[in_pos, "PF"].sum()
        pc_sum = df_j.loc[in_pos, "PC"].sum()
        apps   = int(in_pos.sum())
        if apps > 0:  # solo guardamos si aparece al menos una vez en esa columna
            pos_records.append({
                "posicio": pos,
                "jugadora": player,
                "apariciones": apps,
                "PF": pf_sum,
                "PC": pc_sum,
                "+/-": pf_sum - pc_sum
            })

tabla_pos = pd.DataFrame(pos_records)

# --- PLOT: tantos subplots como columnas jugX ---
ncols = len(jug_cols)
fig, axes = plt.subplots(1, ncols, figsize=(7*ncols, max(6, 0.35*len(all_players))), squeeze=False)
axes = axes[0]

# límites comunes para que los +/- sean comparables entre subplots
if not tabla_pos.empty:
    M = float(tabla_pos["+/-"].abs().max())
else:
    M = 0.0
xlim = (-1.1*M, 1.1*M) if M > 0 else (-1, 1)

for i, pos in enumerate(jug_cols):
    ax = axes[i]
    sub = tabla_pos[tabla_pos["posicio"] == pos].copy()

    if sub.empty:
        ax.set_title(f"{pos} (sin datos)")
        ax.axis("off")
        continue

    sub = sub.sort_values(by="+/-", ascending=True)
    labels = sub["jugadora"].astype(str)
    bars = ax.barh(labels, sub["+/-"])  # sin colores forzados

    # línea 0
    ax.axvline(0, linewidth=0.8)

    # textos: PF y PC al lado de cada barra
    pad = 0.02*(M if M > 0 else 1)
    for bar, pf, pc, pm in zip(bars, sub["PF"], sub["PC"], sub["+/-"]):
        ax.text(
            bar.get_width() + (pad if bar.get_width() >= 0 else -pad),
            bar.get_y() + bar.get_height()/2,
            f"PF {int(pf)} | PC {int(pc)} | {int(pm):+d}",
            va="center",
            ha="left" if bar.get_width() >= 0 else "right",
            fontsize=9
        )

    ax.set_xlim(xlim)
    ax.set_xlabel("+/- (PF - PC)")
    ax.set_title(f"{pos} — PF/PC cuando está en esa posición")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

plt.tight_layout()
plt.show()




#gràfic defensaç
import math
import pandas as pd
import matplotlib.pyplot as plt

# --- Colors (els teus) ---
COLOR_MAP = {
    "t2f": "#fbb47f",
    "t2c": "#b5e7a0",
    "t3f": "#fdd49e",
    "t3c": "#77dd77",
    "Falta (TLL)": "#ffdab9",
    "falta": "#fff7a5",
    "pèrdua": "#fba0a0",
    "banda": "#e6e6e6",
    "fons": "#cccccc"
}
COLOR_MAP_NORM = {str(k).strip().lower(): v for k, v in COLOR_MAP.items()}
'''
# --- Noms de columna (tal com m'has dit) ---
COL_TACT_DEF = "Tàctica defensiva"
COL_DESENLLAC = "Desenllaç"
COL_PUNTS = "punts"

# --- Neteja + normalització ---
df_clean = df[df[COL_TACT_DEF].notna() & (df[COL_TACT_DEF].astype(str).str.strip() != "-")].copy()
df_clean = df_clean[df_clean[COL_DESENLLAC].notna() & (df_clean[COL_DESENLLAC].astype(str).str.strip() != "-")].copy()

df_clean["tdef_norm"] = df_clean[COL_TACT_DEF].astype(str).str.strip().str.lower()

# Ordre per freqüència (si vols un ordre fix, digues-me'l i t'ho poso)
tactics_norm = df_clean["tdef_norm"].value_counts().index.tolist()

# Per mostrar el nom "bonic" (primer que apareix al df per aquella tàctica)
norm_to_show = (
    df_clean.drop_duplicates("tdef_norm")
            .set_index("tdef_norm")[COL_TACT_DEF]
            .to_dict()
)

# --- Subplots ---
n = len(tactics_norm)
cols = 4
rows = math.ceil(n / cols)
fig, axes = plt.subplots(rows, cols, figsize=(cols*5, rows*5))
axes = axes.flatten()

for i, t_norm in enumerate(tactics_norm):
    subset = df_clean[df_clean["tdef_norm"] == t_norm]

    counts = subset[COL_DESENLLAC].value_counts()
    colors = [COLOR_MAP_NORM.get(str(lbl).strip().lower(), "#cccccc") for lbl in counts.index]

    axes[i].pie(
        counts,
        labels=counts.index,
        autopct=lambda p: int(round(p * sum(counts) / 100)) if p > 0 else "",
        startangle=90,
        colors=colors
    )

    num_vegades = len(subset)
    punts_total = pd.to_numeric(subset[COL_PUNTS], errors="coerce").sum()

    axes[i].set_title(
        f"{norm_to_show.get(t_norm, t_norm)} ({num_vegades})\n(Punts: {int(punts_total)})",
        fontsize=14,
        weight="bold"
    )

# Eliminar subplots buits
for j in range(n, len(axes)):
    fig.delaxes(axes[j])

plt.tight_layout()
plt.show()

'''