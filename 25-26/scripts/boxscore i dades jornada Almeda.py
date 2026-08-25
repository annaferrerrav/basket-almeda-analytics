# -*- coding: utf-8 -*-
"""
Created on Tue Sep  9 16:53:04 2025

@author: AFERRERR
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Jul  9 19:46:01 2025

@author: AFERRERR
"""
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd
import requests

# Diccionari amb jornades i URLs

partits = {
    1: "https://baloncestoenvivo.feb.es/partido/2414816",
    2: "https://baloncestoenvivo.feb.es/partido/2414822",
    3: "https://baloncestoenvivo.feb.es/partido/2414829",
    4: "https://baloncestoenvivo.feb.es/partido/2414837",
    5: "https://baloncestoenvivo.feb.es/partido/2414842",
    6: "https://baloncestoenvivo.feb.es/partido/2414852",
    7: "https://baloncestoenvivo.feb.es/partido/2414855",
    8: "https://baloncestoenvivo.feb.es/partido/2414867",
    9: "https://baloncestoenvivo.feb.es/partido/2414868",
    10: "https://baloncestoenvivo.feb.es/partido/2414881",
    11: "https://baloncestoenvivo.feb.es/partido/2414883",
    12: "https://baloncestoenvivo.feb.es/partido/2414894",
    13: "https://baloncestoenvivo.feb.es/partido/2414898",
    14: "https://baloncestoenvivo.feb.es/partido/2414907",
    15: "https://baloncestoenvivo.feb.es/partido/2414913",
    16: "https://baloncestoenvivo.feb.es/partido/2414920",
    17: "https://baloncestoenvivo.feb.es/partido/2414928",
    18: "https://baloncestoenvivo.feb.es/partido/2414933",
    19: "https://baloncestoenvivo.feb.es/partido/2414943",
    20: "https://baloncestoenvivo.feb.es/partido/2414946",
    21: "https://baloncestoenvivo.feb.es/partido/2414958",
    22: "https://baloncestoenvivo.feb.es/partido/2414959",
    23: "https://baloncestoenvivo.feb.es/partido/2414972",
    24: "https://baloncestoenvivo.feb.es/partido/2414974",
    25: "https://baloncestoenvivo.feb.es/partido/2414985",
    26: "https://baloncestoenvivo.feb.es/partido/2414989"
}


partits = {
    1: "https://baloncestoenvivo.feb.es/partido/2414816",
    2: "https://baloncestoenvivo.feb.es/partido/2414822",
    3: "https://baloncestoenvivo.feb.es/partido/2414829",
    4: "https://baloncestoenvivo.feb.es/partido/2414837",
    5: "https://baloncestoenvivo.feb.es/partido/2414842",
    6: "https://baloncestoenvivo.feb.es/partido/2414852",
    }
    
    
    
'''
partits = {
    1: "https://baloncestoenvivo.feb.es/partido/2414816",
    2: "https://baloncestoenvivo.feb.es/partido/2414822",
  3: "https://baloncestoenvivo.feb.es/partido/2414829"
}

'''

partits={
    1: "https://baloncestoenvivo.feb.es/partido/2479685",
    2: "https://baloncestoenvivo.feb.es/partido/2479694", 
    3:"https://baloncestoenvivo.feb.es/partido/2479700",
    4: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479707",
    5: "https://baloncestoenvivo.feb.es/partido/2479715",
    6: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479720",
    7: "https://baloncestoenvivo.feb.es/partido/2479730",
    8: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479733",
    9: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479745",
    10: "https://baloncestoenvivo.feb.es/partido/2479746",
    11: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479759",
    12: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479761",
    13: "https://baloncestoenvivo.feb.es/partido/2479772" ,
    14: "https://baloncestoenvivo.feb.es/partido/2479776",
    15: "https://baloncestoenvivo.feb.es/partido/2479785",
    16: "https://baloncestoenvivo.feb.es/partido/2479791", 
    17: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479798",
    18: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479806",
    19: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479811",
    20: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479821",
    21: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479824",
    22: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479836",
    23: "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479837",
    24: "https://baloncestoenvivo.feb.es/partido/2479850", 
    25: "https://baloncestoenvivo.feb.es/partido/2479852"}

df_totals = []

for jornada, url in partits.items():
    print(f"📥 Descarregant jornada {jornada}...")

    # Obtenir el HTML
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Equip local i visitant
    box = soup.find("div", class_="box-marcador")
    local_div = box.find("div", class_="columna equipo local")
    visit_div = box.find("div", class_="columna equipo visitante")
    local_team = soup.find('span', id='_ctl0_MainContentPlaceHolderMaster_equipoLocalNombre').get_text(strip=True)
    visit_team = visit_div.find("span", class_="nombre").get_text(strip=True)
    local_score = local_div.find("span", class_="resultado").get_text(strip=True)
    visit_score = visit_div.find("span", class_="resultado").get_text(strip=True)

    # Data i hora
    box_datos = soup.find("div", class_="box-datos-partido")
    fecha_class = box_datos.find("div", class_="fecha")
    data_txt = fecha_class.find("span", class_="txt").get_text(strip=True)
    fecha, hora = data_txt.split(" - ")

    # Taules de jugadors
    tables = [div.find("table") for div in soup.find_all("div", class_="responsive-scroll") if div.find("table")]
    
    df_jugadores = []
    for i, table in enumerate(tables):
        rows = table.find_all('tr')

        headers = [
            'Inicial', 'Dorsal', 'Jugador', 'MIN', 'PT', 'T2', 'T3', 'TC', 'TL',
            'RO', 'RD', 'RT', 'AS', 'BR', 'BP', 'TapF', 'TapC', 'MT',
            'FC', 'FR', 'VA', '+/-'
        ]
        
        data = []
        for tr in rows[2:]:
            row = []
            for td in tr.find_all('td'):
                a = td.find('a')
                if a:
                    row.append(a.get_text(strip=True))
                else:
                    span = td.find('span', class_='porcentaje')
                    if span:
                        span.extract()
                    row.append(td.get_text(strip=True))
            if any(row):
                data.append(row)

        df = pd.DataFrame(data, columns=headers)

        # Tractament tirs
        cols_tirs = ['T2', 'T3', 'TC', 'TL']
        for col in cols_tirs:
            if col in df.columns:
                df[col] = df[col].astype(str)
                df[[f"{col}C", f"{col}I"]] = df[col].str.extract(r'(\d+)/(\d+)').astype('Int64')
                #percent = (df[f"{col}C"] / df[f"{col}I"]*100).round(1)
                percent = np.where(df[f"{col}I"] == 0, 0, (df[f"{col}C"] / df[f"{col}I"] * 100).round(1))

                cols = list(df.columns)
                idx = cols.index(col)
                #df = df.drop(columns=[col, f"{col}C", f"{col}I"])
                df.insert(loc=idx, column=f"{col} (%)", value=percent)

        total = df[df['Jugador'] == '']
        equip = local_team if i == 0 else visit_team
        rival = visit_team if i == 0 else local_team
        pista = "Casa" if i == 0 else "Fora"

        total['Equip'] = equip
        total['Rival'] = rival
        total['Pista'] = pista
        total['Jornada'] = jornada
        total['Data'] = fecha
        total['Hora'] = hora

        jugadores = df[df['Jugador'] != ''].copy()

        # Afegim la informació del partit per a cada jugadora
        jugadores['Equip'] = equip
        jugadores['Rival'] = rival
        jugadores['Pista'] = pista
        jugadores['Jornada'] = jornada
        jugadores['Data'] = fecha
        jugadores['Hora'] = hora
        # Victòria real de l'equip (es calcula comparant el marcador)
        pt_equip = pd.to_numeric(local_score if i == 0 else visit_score, errors='coerce')
        pt_rival = pd.to_numeric(visit_score if i == 0 else local_score, errors='coerce')
        jugadores['Victòria'] = 1 if pt_equip > pt_rival else 0   
        
        
        cols_numeric = ['TCI', 'TLI', 'BP', 'RO']
        for col in cols_numeric:
            total[col] = pd.to_numeric(total[col], errors='coerce')
        
        # Càlcul de possessions
        #total['Pos'] = total['TCI'] + 0.44 * total['TLI'] + total['BP'] - total['RO']
        #total['Pos T']=

        col_inici = ['Equip', 'Jornada', 'Rival', 'Data', 'Hora', 'Pista']
        altres = [c for c in total.columns if c not in col_inici]
        total = total[col_inici + altres]
        
        df_jugadores.append(jugadores)
    # Unir local + visitant en un df per la jornada
    df_jornada = pd.concat(df_jugadores, ignore_index=True)
    
    # Afegir punts en contra (intercanviant valors de 'PT')
    df_jornada['PT'] = pd.to_numeric(df_jornada['PT'], errors='coerce')
    df_jornada['PT rival'] = df_jornada['PT'].iloc[::-1].values
    
    df_jornada['RD'] = pd.to_numeric(df_jornada['RD'], errors='coerce')
    df_jornada['RD rival'] = df_jornada['RD'].iloc[::-1].values
    # Calcular la mitjana de possessions del partit
    #df_jornada['Pos T'] = df_jornada['Pos'].mean()
    #df_jornada['Victòria'] = np.where(df_jornada['PT'] > total['PT rival'], 1, 0)

    # Afegir a la llista general
    df_totals.append(df_jornada)


df_final = pd.concat(df_totals, ignore_index=True)  
'''  
df_final.replace("nan", 0, inplace=True)

porcentaje_cols = ['T2 (%)', 'T3 (%)', 'TC (%)', 'TL (%)']
df_final[porcentaje_cols] = df_final[porcentaje_cols].fillna(0)

for col in df_final.columns:
    df_final[col] = pd.to_numeric(df_final[col], errors='ignore')

    #df_totals.append(df_totals_jornada)

df_final[['PT', 'TCI', 'TLI']] = df_final[['PT', 'TCI', 'TLI']].apply(pd.to_numeric, errors='coerce')

df_final['Plays']=df_final['TCI']+0.44*df_final['TLI']+df_final['BP']
df_final['%TS'] = round(100 * df_final['PT'] / (2 * (df_final['TCI'] + df_final['TLI'] * 0.44)), 2)
df_final['%TO']=round((df_final["BP"]/(df_final['TCI']+0.44*df_final['TLI']+df_final['BP']))*100,2) #% pèrdues
df_final['RTL']=df_final['TLC']/df_final['TCI']



#ús dels tirs
denominator = df_final['TCI'] + 0.44 * df_final['TLI']

df_final['%US2'] = np.where(denominator == 0, 0, round(df_final['T2I'] * 100 / denominator, 2))
df_final['%US3'] = np.where(denominator == 0, 0, round(df_final['T3I'] * 100 / denominator, 2))
df_final['%US1'] = np.where(denominator == 0, 0, round(df_final['TLI'] * 0.44 * 100 / denominator, 2))

# Assegurem que MIN és una cadena (str)

# Convertim MIN a minuts decimals
df_final['MIN'] = df_final['MIN'].str.split(':').apply(lambda x: int(x[0]) + int(x[1]) / 60 if len(x) == 2 else int(x[0]))

# Calculem Plays per minut
df_final['Plays/min'] = (df_final['TCI'] + 0.44 * df_final['TLI'] + df_final['BP']) / df_final['MIN']

#df_final['MIN'] = df_final['MIN'].astype(str)
#df_final['MIN'] = df_final['MIN'].str.split(':').str[0].astype(int)
#df_final['Plays/min']=df_final['TCI']+0.44*df_final['TLI']+df_final['BP']

df_final['Plays/min'] = (df_final['TCI'] + 0.44 * df_final['TLI'] + df_final['BP']) / df_final['MIN']


#df_final['Victòria'] = np.where(df_final['PT'] > df_final['PT rival'], 1, 0)

#df_final = df_final.drop(columns=[ "RD rival", "T2","T3","TC","TL"])
df_final=df_final.drop(columns=['PT rival'])
ordre_columnes = [
    'Equip', 'Jornada', 'Rival', 'Data', 'Hora', 'Pista', 'Victòria','Inicial','Dorsal','Jugador','MIN',
    'PT', 
    'T2C', 'T2I', 'T2 (%)',
    'T3C', 'T3I', 'T3 (%)',
    'TCC', 'TCI', 'TC (%)',
    'TLC', 'TLI', 'TL (%)',
    'RO', 'RD', 'RT', 'AS', 'BR', 'BP', 'TapF', 'TapC', 'MT', 'FC', 'FR', 'VA', '+/-',
   # 'Pos', 'Pos T', 
    #'%eff', '%TO', '%RO', 'RTL',#4 factors
    "Plays","Plays/min",'%TS', '%TO', 'RTL',
    '%US2', '%US3','%US1' #ús dels tirs
]

# Aplicar ordre
df_final = df_final[ordre_columnes]

# Mostrar
print(df_final)
'''
df_final['Inicial'] = df_final['Inicial'].apply(lambda x: 1 if x == "*" else 0)
# Assegurem que MIN és una cadena (str)

# Convertim MIN a minuts decimals
df_final['MIN'] = df_final['MIN'].str.split(':').apply(lambda x: int(x[0]) + int(x[1]) / 60 if len(x) == 2 else int(x[0]))


#f_final.to_excel("C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\\Escritorio\\Micro UB\\df_totals_26jornades.xlsx")

df_final_almeda=df_final[df_final['Equip']=="BASKET ALMEDA"]
df_final_almeda = df_final_almeda.drop(columns=["Equip"])

#df_final_almeda.to_excel("C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\\Escritorio\\Micro UB\\df_jugadores_26jornades_2.xlsx")


# 2) PARÁMETROS
# ----------------------------------------------------------------------------------
EQUIPO_OBJETIVO = "BASKET ALMEDA"
from pathlib import Path

RUTA_SALIDA = Path(r"C:\Users\aferrerr\OneDrive - Hospital Clínic de Barcelona\Escritorio\LF2 - 2025-56\LF2") / "boxscores_almeda_por_jornada_25.xlsx"

# ----------------------------------------------------------------------------------
# 3) COLUMNAS DEL BOXSCORE (orden y selección)
# ----------------------------------------------------------------------------------
cols_boxscore = [
    'Inicial','Dorsal','Jugador','MIN','PT',
    'T2C','T2I','T2 (%)',
    'T3C','T3I','T3 (%)',
    'TCC','TCI','TC (%)',
    'TLC','TLI','TL (%)',
    'RO','RD','RT','AS','BR','BP','TapF','TapC','MT','FC','FR','VA','+/-'
]

# Asegurar tipos y formatos usados más abajo
df_final = df_final.copy()
# Inicial en binario -> símbolo
df_final['Inicial'] = df_final['Inicial'].apply(lambda x: "*" if str(x) in ("1", "*") else "")
# MIN puede venir ya en decimal: mostramos con mm:ss si es string tipo "12:34", si es float mantenemos tal cual
# Si MIN era decimal y quieres mm:ss, descomenta:
# df_final['MIN'] = (df_final['MIN'].astype(float) * 60).round().astype(int).apply(lambda s: f"{s//60}:{s%60:02d}")

# ----------------------------------------------------------------------------------
# 4) FUNCIÓN AUXILIAR: totales del partido para la mini-tabla
# ----------------------------------------------------------------------------------
def totales_partido(df_almeda_j, df_rival_j):
    def _sumas(df):
        s = {}
        safe = lambda c: pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0).sum()
        # tirs detallats
        s['T2I']   = safe('T2I')
        s['T2C']   = safe('T2C')
        s['T3I']   = safe('T3I')
        s['T3C']   = safe('T3C')
        s['TCI']   = safe('TCI')
        s['TCC']   = safe('TCC')
        s['TLLI']  = safe('TLI')
        s['TLLC']  = safe('TLC')
        # altres
        s['BP']    = safe('BP')
        s['RO']    = safe('RO')
        s['RD']    = safe('RD')
        s['PF']    = safe('PT')   # punts a favor
        return s

    a = _sumas(df_almeda_j)
    r = _sumas(df_rival_j)

    def _metrics(own, opp):
        poss = own['TCI'] + 0.44*own['TLLI'] + own['BP'] - own['RO']
        OER  = 100 * own['PF'] / poss if poss > 0 else 0
        DER  = 100 * opp['PF'] / poss if poss > 0 else 0
        NETR = OER - DER
        eff  = 100 * (own['TCC'] + 0.5*own['T3C']) / own['TCI'] if own['TCI']>0 else 0
        TO   = 100 * own['BP'] / (own['TCI'] + 0.44*own['TLLI'] + own['BP']) if (own['TCI']+0.44*own['TLLI']+own['BP'])>0 else 0
        ROpc = 100 * own['RO'] / (own['RO'] + opp['RD']) if (own['RO']+opp['RD'])>0 else 0
        RTL  = own['TLLC']/own['TCI'] if own['TCI']>0 else 0
        return poss, OER, DER, NETR, eff, TO, ROpc, RTL

    poss_a, OER_a, DER_a, NETR_a, eff_a, TO_a, RO_a, RTL_a = _metrics(a, r)
    poss_r, OER_r, DER_r, NETR_r, eff_r, TO_r, RO_r, RTL_r = _metrics(r, a)

    fila_almeda = {
        'Equipo'        : "BASKET ALMEDA",
        'T2C'           : int(a['T2C']),
        'T2I'           : int(a['T2I']),
        'T3C'           : int(a['T3C']),
        'T3I'           : int(a['T3I']),
        'TCC'           : int(a['TCC']),
        'TCI'           : int(a['TCI']),
        'TLLC'          : int(a['TLLC']),
        'TLLI'          : int(a['TLLI']),
        'Perdidas'      : int(a['BP']),
        'RO'            : int(a['RO']),
        'RD rival'      : int(r['RD']),
        'Punts Anotats' : int(a['PF']),
        'Punts rebuts'  : int(r['PF']),
        'Poss'          : round(poss_a,2),
        'OER'           : round(OER_a,1),
        'DER'           : round(DER_a,1),
        'NETR'          : round(NETR_a,1),
        '%eff'          : round(eff_a,1),
        '%TO'           : round(TO_a,1),
        '%RO'           : round(RO_a,1),
        'RTL'           : round(RTL_a,2)
    }
    fila_rival = {
        'Equipo'        : df_almeda_j['Rival'].iloc[0] if not df_almeda_j.empty else 'Rival',
        'T2C'           : int(r['T2C']),
        'T2I'           : int(r['T2I']),
        'T3C'           : int(r['T3C']),
        'T3I'           : int(r['T3I']),
        'TCC'           : int(r['TCC']),
        'TCI'           : int(r['TCI']),
        'TLLC'          : int(r['TLLC']),
        'TLLI'          : int(r['TLLI']),
        'Perdidas'      : int(r['BP']),
        'RO'            : int(r['RO']),
        'RD rival'      : int(a['RD']),
        'Punts Anotats' : int(r['PF']),
        'Punts rebuts'  : int(a['PF']),
        'Poss'          : round(poss_r,2),
        'OER'           : round(OER_r,1),
        'DER'           : round(DER_r,1),
        'NETR'          : round(NETR_r,1),
        '%eff'          : round(eff_r,1),
        '%TO'           : round(TO_r,1),
        '%RO'           : round(RO_r,1),
        'RTL'           : round(RTL_r,2)
    }
    return pd.DataFrame([fila_almeda, fila_rival])



# ----------------------------------------------------------------------------------
# 5) ESCRITURA DEL EXCEL: 1 pestaña por jornada
# ----------------------------------------------------------------------------------
# Jornadas presentes en df_final del equipo objetivo
jornadas = sorted(df_final.loc[df_final['Equip'] == EQUIPO_OBJETIVO, 'Jornada'].dropna().unique())

with pd.ExcelWriter(RUTA_SALIDA, engine='xlsxwriter') as writer:
    wb = writer.book

    # Formatos útiles
    fmt_header = wb.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    fmt_center = wb.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    fmt_int    = wb.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0'})
    fmt_pct    = wb.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.0'})
    fmt_title  = wb.add_format({'bold': True})
    fmt_text   = wb.add_format({})

    for j in jornadas:
        hoja = f"J{int(j):02d}"
        ws_info = df_final.loc[(df_final['Equip'] == EQUIPO_OBJETIVO) & (df_final['Jornada'] == j)]
        if ws_info.empty:
            # Si no hay datos de esa jornada, crea hoja vacía informativa
            empty_df = pd.DataFrame({'Info': [f'Sin datos para jornada {j}']})
            empty_df.to_excel(writer, sheet_name=hoja, index=False)
            continue

        # Info rival / cabecera
        rival = ws_info['Rival'].iloc[0]
        fecha = ws_info['Data'].iloc[0]
        hora  = ws_info['Hora'].iloc[0]
        pista = ws_info['Pista'].iloc[0]

        # Boxscore ordenado
        box = ws_info.loc[:, [c for c in cols_boxscore if c in ws_info.columns]].copy()
        # Asegurar tipos numéricos donde toque (para que se aplique num_format)
        for c in ['PT','T2C','T2I','T3C','T3I','TCC','TCI','TLC','TLI',
                  'RO','RD','RT','AS','BR','BP','TapF','TapC','MT','FC','FR','VA','+/-']:
            if c in box.columns:
                box[c] = pd.to_numeric(box[c], errors='coerce')

        # Escribimos el boxscore empezando en la fila 1 (0-based)
        start_row = 1
        box.to_excel(writer, sheet_name=hoja, startrow=start_row, index=False)
        ws = writer.sheets[hoja]

        # Título arriba
        ws.write(0, 0, f"{EQUIPO_OBJETIVO} vs {rival} — J{int(j)} — {fecha} {hora} — {pista}", fmt_title)

        # Formato cabecera y celdas
        for col_idx, col_name in enumerate(box.columns):
            ws.write(start_row, col_idx, col_name, fmt_header)
            # ancho razonable
            ancho = 14 if col_name in ('Jugador',) else 8
            ws.set_column(col_idx, col_idx, ancho)

        # Formato de números
        last_row = start_row + len(box)
        # % con un decimal
        for col_name in ['T2 (%)','T3 (%)','TC (%)','TL (%)']:
            if col_name in box.columns:
                col_idx = box.columns.get_loc(col_name)
                ws.set_column(col_idx, col_idx, 8, fmt_pct)
        # enteros centrados
        for col_name in [c for c in box.columns if c not in ['Jugador','Inicial'] and '(%)' not in c]:
            col_idx = box.columns.get_loc(col_name)
            ws.set_column(col_idx, col_idx, 8, fmt_int)

        ws.freeze_panes(start_row+1, 0)

                # ------------------- Mini-tabla dos líneas abajo (estilo captura ajustado) -------------------
        blank_row_1 = last_row + 1
        blank_row_2 = last_row + 2
        start_summary = last_row + 3  # "dos líneas abajo"

        # Rival df (mismos jugadores pero del otro equipo y misma jornada)
        rival_df = df_final.loc[(df_final['Equip'] != EQUIPO_OBJETIVO) & (df_final['Jornada'] == j)]

        # Totales + métricas (usa tu función totales_partido ya ampliada)
        tabla = totales_partido(ws_info, rival_df)

        # -------- Diseño de columnas con separadores vacíos (como tu hoja) --------
        left_cols = [
            'Equipo',
            'T2C','T2I',
            'T3C','T3I',
            'TCC','TCI',
            'TLLC','TLLI',
            'Perdidas',
            'RO','RD rival',
            'Punts Anotats','Punts rebuts'
        ]

        # Solo una columna para el valor de posesiones (con cabecera "POSSESSIÓ")
        pos_value = 'Poss'

        green_cols = ['OER','DER','NETR']          # bloque verde
        blue_cols  = ['%eff','%TO','%RO','RTL']    # bloque azul

        # Orden final con separadores (None)
        layout_cols = left_cols + [None, pos_value, None] + green_cols + [None] + blue_cols

        # ------------------- Formatos -------------------
        fmt_hdr      = wb.add_format({'bold': True, 'align':'center','valign':'vcenter','border':1})
        fmt_cell     = wb.add_format({'align':'center','valign':'vcenter','border':1})
        fmt_int      = wb.add_format({'align':'center','valign':'vcenter','border':1, 'num_format':'0'})
        fmt_dec2     = wb.add_format({'align':'center','valign':'vcenter','border':1, 'num_format':'0.00'})
        fmt_pct1     = wb.add_format({'align':'center','valign':'vcenter','border':1, 'num_format':'0.0%'})
        fmt_greenhdr = wb.add_format({'bold': True,'align':'center','valign':'vcenter','border':1,'bg_color':'#C6EFCE'})
        fmt_bluehdr  = wb.add_format({'bold': True,'align':'center','valign':'vcenter','border':1,'bg_color':'#DBEEF3'})
        fmt_title2   = wb.add_format({'bold': True})
        fmt_link     = wb.add_format({'font_color':'blue','underline':1})

        # ------------------- Fila superior "CAS {j}" + hyperlink -------------------
        ws.write(start_summary - 1, 0, f"CAS {int(j)}", fmt_title2)
        url_partit = partits.get(int(j), "")
        if url_partit:
            ws.write_url(start_summary - 1, 1, url_partit, fmt_link, url_partit)

        # ------------------- Cabeceras (con colores y separadores) -------------------
        row_h = start_summary
        col0  = 0
        col   = col0
        for name in layout_cols:
            if name is None:
                ws.set_column(col, col, 2)  # separador estrecho
            else:
                if name in green_cols:
                    ws.write(row_h, col, name.replace('NETR', 'NET R'), fmt_greenhdr)
                elif name in blue_cols:
                    nice = {'%eff':'% Tir eficient','%TO':'% Pèrdues','%RO':'% RO','RTL':'RTL'}[name]
                    ws.write(row_h, col, nice, fmt_bluehdr)
                elif name == pos_value:
                    # la columna de valor de posesiones tiene cabecera "POSSESSIÓ"
                    ws.write(row_h, col, "POSSESSIÓ", fmt_hdr)
                else:
                    ws.write(row_h, col, name, fmt_hdr)

                # Anchos
                if name in ('Equipo','Punts Anotats','Punts rebuts'):
                    ws.set_column(col, col, 16)
                elif name in ('T2C','T2I','T3C','T3I','TCC','TCI','TLLC','TLLI','Perdidas','RO','RD rival'):
                    ws.set_column(col, col, 10)
                elif name == pos_value:
                    ws.set_column(col, col, 10)
                else:
                    ws.set_column(col, col, 12)
            col += 1

        # ------------------- Datos (2 filas: Almeda y rival) -------------------
        for i in range(len(tabla)):
            r = row_h + 1 + i
            col = col0
            for name in layout_cols:
                if name is None:
                    col += 1
                    continue

                # Valor por defecto
                val = '' if name not in tabla.columns else tabla.iloc[i][name]

                # Escritura con formato según tipo/columna
                if name in ('Equipo',):
                    ws.write(r, col, val, fmt_cell)

                elif name in ('T2C','T2I','T3C','T3I','TCC','TCI','TLLC','TLLI',
                              'Perdidas','RO','RD rival','Punts Anotats','Punts rebuts'):
                    ws.write_number(r, col, float(val or 0), fmt_int)

                elif name == pos_value:
                    ws.write_number(r, col, float(tabla.iloc[i]['Poss']), fmt_dec2)

                elif name in green_cols:
                    ws.write_number(r, col, float(tabla.iloc[i][name]), fmt_dec2)

                elif name in ('%eff','%TO','%RO'):
                    # vienen como 69.3 -> para estilo porcentaje dividimos por 100
                    ws.write_number(r, col, float(tabla.iloc[i][name]) / 100.0, fmt_pct1)

                elif name == 'RTL':
                    ws.write_number(r, col, float(tabla.iloc[i]['RTL']), fmt_dec2)

                else:
                    ws.write(r, col, val, fmt_cell)

                col += 1

        # ------------------- Pie: TOTAL / Minuts + bloque POSS/RITME -------------------
        foot_row_1 = row_h + 1 + len(tabla) + 1
        foot_row_2 = foot_row_1 + 1
        ws.write(foot_row_1, col0, "TOTAL", fmt_title2)
        ws.write(foot_row_2, col0, "Minuts", fmt_title2)
        ws.write_number(foot_row_2, col0+1, 40, fmt_int)

        # POSS / RITME debajo del bloque de posesiones
        avg_poss = float(tabla['Poss'].mean()) if 'Poss' in tabla.columns else 0.0
        pos_col_idx = layout_cols.index(pos_value)
        ws.write(foot_row_1, col0 + pos_col_idx - 1, "POSS", fmt_title2)
        ws.write_number(foot_row_1, col0 + pos_col_idx, avg_poss, fmt_dec2)
        ws.write(foot_row_2, col0 + pos_col_idx - 1, "RITME", fmt_title2)
        ws.write_number(foot_row_2, col0 + pos_col_idx, avg_poss, fmt_dec2)
