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
    1: "https://baloncestoenvivo.feb.es/partido/2479690", #distrito - almeda
    1: "https://baloncestoenvivo.feb.es/partido/2479684", #mostoles - andratx
    1: "https://baloncestoenvivo.feb.es/partido/2479686", #alcorcon - segle
    1: "https://baloncestoenvivo.feb.es/partido/2479687", #geieg - gmasb
    1: "https://baloncestoenvivo.feb.es/partido/2479688", #picken - viladecans
    1: "https://baloncestoenvivo.feb.es/partido/2479689", #lanzarote - granca
    1: "https://baloncestoenvivo.feb.es/partido/2479683" #isla bonita- miralvalle
    
    }

jornada=8
    
partits = [
"https://baloncestoenvivo.feb.es/Partido.aspx?p=2479750",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479751", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479752", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479747", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479749", 
   "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479746", 
    "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479748"
    
    
    ]

jornada=11

partits = [
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479759",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479758", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479756", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479757",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479753", 
   "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479754", 
    "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479755"
    
    
    ]


jornada=23
    
partits = [
"https://baloncestoenvivo.feb.es/Partido.aspx?p=2479840",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479841", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479838", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479843",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479839", 
   "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479842", 
    "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479837"
    
    ]

jornada=25
    
partits = [
"https://baloncestoenvivo.feb.es/Partido.aspx?p=2479853",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479855", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479852", 
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479854",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479857", 
"https://baloncestoenvivo.feb.es/Partido.aspx?p=2479851",
 "https://baloncestoenvivo.feb.es/Partido.aspx?p=2479856"
    
    
    ]

df_totals = []


for url in partits:
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

        #jugadores = df[df['Jugador'] != ''].copy()
        
        # Si la columna 'Jugador' està buida, posa-hi 'TOTAL'
        df['Jugador'] = df['Jugador'].replace('', np.nan)
        df['Jugador'] = df['Jugador'].fillna('TOTAL')
        


        
        jugadores=df

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
df_final.replace("nan", 0, inplace=True)

porcentaje_cols = ['T2 (%)', 'T3 (%)', 'TC (%)', 'TL (%)']
df_final[porcentaje_cols] = df_final[porcentaje_cols].fillna(0)

for col in df_final.columns:
    df_final[col] = pd.to_numeric(df_final[col], errors='ignore')

    #df_totals.append(df_totals_jornada)
'''
df_final['OER']=(df_final['PT']/df_final['Pos T'])*100
df_final['DER']=(df_final['PT rival']/df_final['Pos T'])*100
df_final['NET']=df_final['OER']-df_final['DER']

#els 4 factors
df_final['%eff']=round(((df_final['TCC']+0.5*df_final['T3C'])/df_final['TCI'])*100,2) #tir de camp efectiu
df_final['%TO']=round((df_final["BP"]/(df_final['TCI']+0.44*df_final['TLI']+df_final['BP']))*100,2) #% pèrdues
#df_final['%RO']= round((df_final['RO']/(df_final['RO']+df_final['RD rival']))*100,2) #%RO
df_final['RTL']=df_final['TLC']/df_final['TCI']
'''
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
'''
df_final['%US2']=round(df_final['T2I']*100/(df_final['TCI']+0.44*df_final['TLI']), 2)
df_final['%US3']=round(df_final['T3I']*100/(df_final['TCI']+0.44*df_final['TLI']),2)
df_final['%US1']=round(df_final['TLI']*0.44*100/(df_final['TCI']+0.44*df_final['TLI']),2)
'''
# Assegurem que MIN és una cadena (str)

# Convertim MIN a minuts decimals
df_final['MIN'] = df_final['MIN'].str.split(':').apply(lambda x: int(x[0]) + int(x[1]) / 60 if len(x) == 2 else int(x[0]))

# Calculem Plays per minut
df_final['Plays/min'] = (df_final['TCI'] + 0.44 * df_final['TLI'] + df_final['BP']) / df_final['MIN']

#df_final['MIN'] = df_final['MIN'].astype(str)
#df_final['MIN'] = df_final['MIN'].str.split(':').str[0].astype(int)
#df_final['Plays/min']=df_final['TCI']+0.44*df_final['TLI']+df_final['BP']

df_final['Plays/min'] = (df_final['TCI'] + 0.44 * df_final['TLI'] + df_final['BP']) / df_final['MIN']

df_final['Inicial'] = df_final['Inicial'].apply(lambda x: 1 if x == "*" else 0)

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

df_final.to_excel("C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\\Escritorio\\LF2 - 2025-56\\LF2\\boxscore_jornada\\j25-boxscore.xlsx")


df_final_almeda=df_final[df_final['Equip']=="BASKET ALMEDA"]
df_final_almeda = df_final_almeda.drop(columns=["Equip"])



#df_final_almeda.to_excel("C:\\Users\\aferrerr\\OneDrive - Hospital Clínic de Barcelona\\Escritorio\\Micro UB\\df_jugadores_26jornades_2.xlsx")
