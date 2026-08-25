import pandas as pd
import matplotlib.pyplot as plt

path = r"C:\Users\aferrerr\OneDrive - Hospital Clínic de Barcelona\Escritorio\LF2 - 2025-56\LF2\\"
EXCEL_PATH = path + "boxscores_MOSTOLES_por_jornada_25.xlsx"

# --- Funció auxiliar per convertir "34,3%" o "80,16" a float ---
def to_float(x):
    if isinstance(x, str):
        x = x.replace('%', '').replace(',', '.')
        return float(x)
    return float(x)

# Obrim l'Excel per veure les pestanyes
xls = pd.ExcelFile(EXCEL_PATH)

# Només pestanyes tipus J01, J02...
fulls_jornada = sorted([s for s in xls.sheet_names if s.upper().startswith("J")])

resultats = []

for full in fulls_jornada:
    df = pd.read_excel(EXCEL_PATH, sheet_name=full, header=None)

    # ------------------------------
    # BUSCAR SEMPRE LA FILA DEL TEU EQUIP
    # ------------------------------
    col0 = df.iloc[:, 0].astype(str).str.strip().str.lower()
    idx_equip = df.index[col0 == "basket almeda"]

    if len(idx_equip) == 0:
        print(f"⚠️ No s'ha trobat 'BASKET ALMEDA' al full {full}")
        continue

    fila_equip = idx_equip[0]

    # ------------------------------
    # Les capçaleres estan UNA FILA A SOBRE
    # ------------------------------
    fila_caps = fila_equip - 1
    caps = df.iloc[fila_caps]
    idx_col = {str(v).strip(): i for i, v in caps.items()}

    # ------------------------------
    # Llegir valors necessaris
    # ------------------------------
    oer  = to_float(df.iat[fila_equip, idx_col["OER"]])
    der  = to_float(df.iat[fila_equip, idx_col["DER"]])
    tef  = to_float(df.iat[fila_equip, idx_col["% Tir eficient"]])
    perd = to_float(df.iat[fila_equip, idx_col["% Pèrdues"]])
    rop  = to_float(df.iat[fila_equip, idx_col["% RO"]])

    resultats.append({
        "Jornada": int(full[1:]),   # "J01" → 1
        "OER": oer,
        "DER": der,
        "%Tir eficient": tef,
        "%Pèrdues": perd,
        "%RO": rop
    })

# Resultat final
res = pd.DataFrame(resultats).sort_values("Jornada")
print(res)

# ------------------------------------------------------------------
# GRÀFIC OER i DER
# ------------------------------------------------------------------
plt.figure(figsize=(10, 5))
plt.plot(res["Jornada"], res["OER"], marker="o", label="OER")
plt.plot(res["Jornada"], res["DER"], marker="o", label="DER")

plt.title("Evolució OER i DER")
plt.xlabel("Jornada")
plt.ylabel("Valor")
plt.xticks(res["Jornada"])
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# ------------------------------------------------------------------
# GRÀFIC % Tir eficient, % Pèrdues i % RO
# ------------------------------------------------------------------
plt.figure(figsize=(10, 5))
plt.plot(res["Jornada"], res["%Tir eficient"], marker="o", label="% Tir eficient")
plt.plot(res["Jornada"], res["%Pèrdues"], marker="o", label="% Pèrdues")
plt.plot(res["Jornada"], res["%RO"], marker="o", label="% RO")

plt.title("Evolució % Tir eficient, % Pèrdues i % RO")
plt.xlabel("Jornada")
plt.ylabel("Percentatge")
plt.xticks(res["Jornada"])
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
