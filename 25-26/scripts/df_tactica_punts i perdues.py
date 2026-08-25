# -*- coding: utf-8 -*-
"""
Anàlisi per tàctica (multi-partit) + Pèrdues (global)
"""

import pandas as pd
import re
import unicodedata
from collections import Counter
'''
Resum, vull un datframe amb les seguents columnes
- Tàctica
- Vegades jugat
- Punts ficats
- Posició que fica més punts en aquella jugada?
- Nom de la Jugadora que fica més punts a la jugada
- Nom de la jugadora que, a pista, aconsegueix que l'equip fiqui més punts en aquella jugada

- Pèrdues
- Posició que perd mes boles en aquella jugada
- Nom de la jugadora que perd mes boles
- Nom de la jugadora que, a pista, fa que l'equip perdi més boles en aquella jugada 

'''
# -*- coding: utf-8 -*-
"""
Resum per tàctica (multi-partit) amb:
- Tàctica
- Vegades jugat
- Punts ficats
- Posició que fica més punts en aquella jugada
- Nom de la Jugadora que fica més punts a la jugada
- Nom de la jugadora que, a pista, aconsegueix que l'equip fiqui més punts en aquella jugada
- Pèrdues
- Posició que perd mes boles en aquella jugada
- Nom de la jugadora que perd mes boles
- Nom de la jugadora que, a pista, fa que l'equip perdi més boles en aquella jugada
"""

import pandas as pd
import re
import unicodedata
from collections import Counter

# ============== CONFIG ==============
path = r"C:\Users\aferrerr\OneDrive - Hospital Clínic de Barcelona\Escritorio\LF2 - 2025-56\testing\\"
EXCEL_PATH = path + "Lliga Catalana.xlsx"

# Pots afegir més (fitxer, full)
SOURCES = [
  #  (EXCEL_PATH, "J1 - Playbyplay"),
    (EXCEL_PATH, "J2 - Playbyplay"),
]

# Noms de columnes del teu Excel
COL_TACTIC    = "Tàctica"       # nom de la tàctica
COL_POINTS    = "PF"            # punts a favor
COL_OUTCOME   = "Desenllac"     # resultat de la jugada
COL_FINISHER  = "Finalitzadora" # nom de qui finalitza la jugada (per punts i, si cal, per pèrdua)
LOSS_VALUE    = "Pèrdua"        # literal que marca pèrdua a COL_OUTCOME

# Si tens una columna que indiqui explícitament qui perd la pilota, afegeix-la als candidats (en ordre de preferència):
LOSS_ACTOR_CANDIDATES = ["Pèrdua per", "Perdua per", "Perduda per", "Turnover by", "Lost by", COL_FINISHER]
# ===================================

def normalize_cols(df: pd.DataFrame):
    mapping = {c: re.sub(r"\s+", " ", str(c)).strip() for c in df.columns}
    return df.rename(columns=mapping), mapping

def strip_accents_lower(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

def detect_jug_position_columns(df: pd.DataFrame):
    """
    Detecta columnes 'jug 1'..'jug 5' (insensible a espais/majúscules).
    Retorna dict: {'jug 1': colname1, ..., 'jug 5': colname5}
    """
    mapping = {}
    for c in df.columns:
        m = re.match(r"^\s*jug\s*([1-5])\s*$", str(c), flags=re.IGNORECASE)
        if m:
            mapping[f"jug {m.group(1)}"] = c
    return mapping

def find_actor_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def finisher_position_in_row(row, finisher_col, jug_cols_map):
    """
    Retorna 'jug X' on jugava la persona de 'finisher_col' en aquella fila.
    """
    finisher = strip_accents_lower(row.get(finisher_col))
    if not finisher:
        return None
    for label, colname in jug_cols_map.items():
        candidate = strip_accents_lower(row.get(colname))
        if candidate and candidate == finisher:
            return label
    return None

def join_ties(labels):
    """
    Uneix empats en un string "A / B / C". Retorna None si buit.
    """
    labels = [str(x).strip() for x in labels if x and str(x).strip()]
    if not labels:
        return None
    # treu duplicats mantenint ordre
    seen, out = set(), []
    for x in labels:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return " / ".join(out)

def load_sources(sources):
    frames = []
    for fp, sheet in sources:
        df_raw = pd.read_excel(fp, sheet_name=sheet)
        df_norm, _ = normalize_cols(df_raw)
        df_norm["Origen"] = sheet
        frames.append(df_norm)
    if not frames:
        raise ValueError("No s'ha carregat cap font.")
    return pd.concat(frames, ignore_index=True)

# ---------- Carrega i prepara dades ----------
df = load_sources(SOURCES)

for needed in [COL_TACTIC, COL_POINTS, COL_OUTCOME, COL_FINISHER]:
    if needed not in df.columns:
        raise KeyError(
            f"No s'ha trobat la columna requerida: '{needed}'. "
            f"Columnes disponibles: {list(df.columns)}"
        )

df[COL_POINTS]   = pd.to_numeric(df[COL_POINTS], errors="coerce").fillna(0)
df[COL_OUTCOME]  = df[COL_OUTCOME].astype(str).str.strip()
df[COL_TACTIC]   = df[COL_TACTIC].astype(str).str.strip()
df[COL_FINISHER] = df[COL_FINISHER].astype(str).str.strip()
df.loc[df[COL_FINISHER].isin(["", "nan", "None"]), COL_FINISHER] = pd.NA

jug_cols_map = detect_jug_position_columns(df)
loss_actor_col = find_actor_col(df, LOSS_ACTOR_CANDIDATES)

# ---------- Agregats per tàctica ----------
rows = []

for tactic, g in df.groupby(COL_TACTIC, dropna=False):
    # Bàsics
    times_played   = int(len(g))
    points_scored  = float(g[COL_POINTS].sum())
    losses         = int((g[COL_OUTCOME].str.strip() == LOSS_VALUE).sum())

    # --- SCORING: Posició que fica més punts (per jugades amb punts) ---
    g_scoring = g[g[COL_POINTS] > 0]
    pos_counts_score = Counter()
    if not g_scoring.empty and jug_cols_map:
        for _, row in g_scoring.iterrows():
            pos = finisher_position_in_row(row, COL_FINISHER, jug_cols_map)
            if pos:
                pos_counts_score[pos] += 1
    # empats -> totes
    if pos_counts_score:
        maxc = max(pos_counts_score.values())
        top_pos_scoring = join_ties([p for p, c in pos_counts_score.items() if c == maxc])
    else:
        top_pos_scoring = None

    # --- SCORING: Jugadora que fica més punts (Finalitzadora, suma PF) ---
    # Només jugades amb punts
    top_scorer = None
    if not g_scoring.empty and g_scoring[COL_FINISHER].notna().any():
        per_finisher_pts = g_scoring.groupby(COL_FINISHER, dropna=True)[COL_POINTS].sum()
        if not per_finisher_pts.empty:
            max_pts = per_finisher_pts.max()
            top_scorer = join_ties(per_finisher_pts[per_finisher_pts == max_pts].index.tolist())

    # --- SCORING: Jugadora a pista que fa que l'equip fiqui més punts ---
    # Suma PF a TOTES les jugadores presents a la pista a cada jugada (jug 1..5)
    top_oncourt_scorer = None
    if jug_cols_map and not g_scoring.empty:
        bucket_pf = Counter()
        for _, row in g_scoring.iterrows():
            pf = float(row[COL_POINTS])
            for col in jug_cols_map.values():
                name = str(row.get(col)).strip()
                if name and name.lower() not in ("nan", "none"):
                    bucket_pf[name] += pf
        if bucket_pf:
            maxpf = max(bucket_pf.values())
            top_oncourt_scorer = join_ties([n for n, v in bucket_pf.items() if v == maxpf])

    # --- TURNOVERS: Posició que perd més boles ---
    g_losses = g[g[COL_OUTCOME].str.strip() == LOSS_VALUE]
    pos_counts_tov = Counter()
    if not g_losses.empty and jug_cols_map and loss_actor_col:
        for _, row in g_losses.iterrows():
            pos = finisher_position_in_row(row, loss_actor_col, jug_cols_map)
            if pos:
                pos_counts_tov[pos] += 1
    if pos_counts_tov:
        maxc = max(pos_counts_tov.values())
        top_pos_tov = join_ties([p for p, c in pos_counts_tov.items() if c == maxc])
    else:
        top_pos_tov = None

    # --- TURNOVERS: Jugadora que perd més boles (actora directa) ---
    top_turnover_actor = None
    if not g_losses.empty and loss_actor_col:
        actors = g_losses[loss_actor_col].astype(str).str.strip()
        actors = actors[(actors.str.len() > 0) & (~actors.str.lower().isin(["nan", "none"]))]
        if not actors.empty:
            counts = actors.value_counts()
            maxc = counts.max()
            top_turnover_actor = join_ties(counts[counts == maxc].index.tolist())

    # --- TURNOVERS: Jugadora a pista que fa que l'equip perdi més boles ---
    # Comptem presències (no actora): a cada pèrdua, +1 a cada jugadora present en jug 1..5
    top_oncourt_turnover = None
    if not g_losses.empty and jug_cols_map:
        pres_counts = Counter()
        for _, row in g_losses.iterrows():
            for col in jug_cols_map.values():
                name = str(row.get(col)).strip()
                if name and name.lower() not in ("nan", "none"):
                    pres_counts[name] += 1
        if pres_counts:
            maxc = max(pres_counts.values())
            top_oncourt_turnover = join_ties([n for n, v in pres_counts.items() if v == maxc])

    rows.append({
        "Tàctica": tactic,
        "Vegades jugat": times_played,
        "Punts ficats": points_scored,
        "Posició que fica més punts en aquella jugada?": top_pos_scoring,
        "Nom de la Jugadora que fica més punts a la jugada": top_scorer,
        "Nom de la jugadora que, a pista, aconsegueix que l'equip fiqui més punts en aquella jugada": top_oncourt_scorer,
        "Pèrdues": losses,
        "Posició que perd mes boles en aquella jugada": top_pos_tov,
        "Nom de la jugadora que perd mes boles": top_turnover_actor,
        "Nom de la jugadora que, a pista, fa que l'equip perdi més boles en aquella jugada": top_oncourt_turnover
    })

# DataFrame final
resum_df = pd.DataFrame(rows)
resum_df = resum_df.sort_values(["Vegades jugat", "Punts ficats"], ascending=[False, False]).reset_index(drop=True)

print(resum_df)

# (Opcional) Desa a Excel
# from pathlib import Path
# out_path = Path(path) / "resum_tactiques_total.xlsx"
# resum_df.to_excel(out_path, index=False)
# print("Desat a:", out_path)
