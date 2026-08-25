# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 16:33:52 2025
@author: AFERRERR
"""

import pandas as pd
import glob
import os

# Ruta a la carpeta
path = r"C:\Users\aferrerr\OneDrive - Hospital Clínic de Barcelona\Escritorio\LF2 - 2025-56\LF2\boxscore_jornada"

# Variable del equipo
equip = "SPAR GRAN CANARIA"

# Buscar todos los archivos Excel (xls, xlsx, xlsm, etc.)
excel_files = glob.glob(os.path.join(path, "*.xls*"))

# Lista para guardar los DataFrames
dfs = []

for file in excel_files:
    try:
        df = pd.read_excel(file)
        if "Equip" in df.columns:
            df_filtrado = df[df["Equip"] == equip]
            if not df_filtrado.empty:
                df_filtrado["Archivo"] = os.path.basename(file)
                dfs.append(df_filtrado)
    except Exception as e:
        print(f"⚠️ Error leyendo {file}: {e}")

if dfs:
    resultado = pd.concat(dfs, ignore_index=True)
    print("✅ Datos concatenados del equipo.\n")

    if "Jugador" in resultado.columns:
        # --- Columnas a promediar ---
        columnas_media = [
            "MIN", "PT", "T2C", "T2I", "T3C", "T3I", "TCC", "TCI", "TLC", "TLI",
            "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC",
            "FR", "VA", "+/-", "Plays", "Plays/min"
        ]
        columnas_media = [c for c in columnas_media if c in resultado.columns]

        # Contamos partidos jugados
        partidos_jugados = resultado.groupby("Jugador").size().reset_index(name="Partidos jugados")

        # Si existe la columna "Dorsal", la mantenemos en el resumen
        if "Dorsal" in resultado.columns:
            dorsales = resultado[["Jugador", "Dorsal"]].drop_duplicates(subset="Jugador")
        else:
            dorsales = pd.DataFrame(columns=["Jugador", "Dorsal"])

        # Calculamos las medias
        medias = resultado.groupby("Jugador")[columnas_media].mean().reset_index()

        # Unimos datos
        resumen = pd.merge(partidos_jugados, medias, on="Jugador")
        resumen = pd.merge(dorsales, resumen, on="Jugador", how="left")

        # Reordenamos columnas
        cols = ["Jugador", "Dorsal", "Partidos jugados"] + [c for c in columnas_media if c in resumen.columns]
        resumen = resumen[cols]

        # Mostramos resultado
        print("📊 Promedios por jugadora (con Dorsal y partidos jugados):\n")
        print(resumen.round(2))

        # (Opcional) Guardar en Excel
        # resumen.to_excel("promedios_jugadoras.xlsx", index=False)
    else:
        print("⚠️ No se encontró la columna 'Jugador' en los archivos.")
else:
    print("No se encontraron datos para el equipo especificado.")

import numpy as np

# --- Afegim percentatges (si les columnes existeixen) ---
def pct(nume, deno):
    return np.where(deno > 0, (nume / deno) * 100, 0.0)

if {"T2C","T2I"}.issubset(resumen.columns):
    resumen["T2 (%)"] = pct(resumen["T2C"], resumen["T2I"])

if {"T3C","T3I"}.issubset(resumen.columns):
    resumen["T3 (%)"] = pct(resumen["T3C"], resumen["T3I"])

if {"TLC","TLI"}.issubset(resumen.columns):
    resumen["TL (%)"] = pct(resumen["TLC"], resumen["TLI"])

if {"TCC","TCI"}.issubset(resumen.columns):
    resumen["TC (%)"] = pct(resumen["TCC"], resumen["TCI"])

# Arrodonim una mica
for col in ["T2 (%)","T3 (%)","TL (%)","TC (%)"]:
    if col in resumen.columns:
        resumen[col] = resumen[col].round(2)

# --- Reordenem columnes: % just després del que li toca ---
ordre_desitjat = [
    "Jugador", "Dorsal", "Partidos jugados",
    "MIN", "PT",
    "T2C", "T2I", "T2 (%)",
    "T3C", "T3I", "T3 (%)",
    "TCC", "TCI", "TC (%)",
    "TLC", "TLI", "TL (%)",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR",
    "VA", "+/-", "Plays", "Plays/min"
]

# Ens quedem només amb les que existeixen i després afegim la resta (si n'hi ha)
ordre_final = [c for c in ordre_desitjat if c in resumen.columns] + \
              [c for c in resumen.columns if c not in ordre_desitjat]

resumen = resumen[ordre_final]

import numpy as np

# --- Helper per obtenir el denominador "Total" d'una columna d'intents ---
def total_denominator(df, col_intents, jugador_total="Total"):
    if col_intents not in df.columns:
        return None
    # Busca la fila "Total"
    mask_total = df["Jugador"].astype(str).str.strip().str.casefold() == jugador_total.casefold()
    if mask_total.any():
        val = df.loc[mask_total, col_intents].iloc[0]
        return float(val) if pd.notna(val) else None
    # Si no hi ha fila "Total", fem servir la suma de la resta de jugadores
    return float(df.loc[~mask_total, col_intents].sum())

# --- Calcula %US per a cada tipus de tir ---
pairs = [
    ("T2I",  "% US T2"),
    ("T3I",  "% US T3"),
    ("TCI",  "% US TC"),
    ("TLI",  "% US TLL"),
]

for col_intents, col_pctus in pairs:
    den = total_denominator(resumen, col_intents)
    if den is not None and den > 0 and col_intents in resumen.columns:
        resumen[col_pctus] = (resumen[col_intents] / den) * 100.0
    elif col_intents in resumen.columns:
        # Si no hi ha denominador vàlid, deixem 0.0 (pots canviar a np.nan si prefereixes)
        resumen[col_pctus] = 0.0

# Opcional: per a la fila "Total", posa 100% si el denominador és >0
if "Jugador" in resumen.columns:
    mask_total = resumen["Jugador"].astype(str).str.strip().str.casefold() == "total"
    for _, col_pctus in pairs:
        if col_pctus in resumen.columns:
            # 100% només si hi havia denominador > 0
            origen = [p[0] for p in pairs if p[1] == col_pctus][0]
            den = total_denominator(resumen, origen)
            if den is not None and den > 0:
                resumen.loc[mask_total, col_pctus] = 100.0

# Arrodoneix %US
for _, col_pctus in pairs:
    if col_pctus in resumen.columns:
        resumen[col_pctus] = resumen[col_pctus].round(2)

# --- Reordena: %US just després de cada bloc ---
ordre_desitjat = [
    "Jugador", "Dorsal", "Partidos jugados",
    "MIN", "PT",
    "T2C", "T2I", "T2 (%)", "% US T2",
    "T3C", "T3I", "T3 (%)", "% US T3",
    "TCC", "TCI", "TC (%)", "% US TC",
    "TLC", "TLI", "TL (%)", "% US TLL",
    "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR",
    "VA", "+/-", "Plays", "Plays/min"
]

ordre_final = [c for c in ordre_desitjat if c in resumen.columns] + \
              [c for c in resumen.columns if c not in ordre_desitjat]
resumen = resumen[ordre_final]

