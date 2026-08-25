# FEB play-by-play → Excel Almeda (v3.1)

## Correccions principals

La v3.1 corregeix els errors detectats amb el partit 2479761:

- reconeix els tirs lliures del feed FEB (`action: fthrow`, text `TIRO DE 1`);
- llegeix el marcador acumulat dels camps `scoreA` i `scoreB`;
- ordena els esdeveniments pel camp `num`, inclosos els que comparteixen segon;
- infereix si cada rebot genèric és ofensiu o defensiu segons el tir anterior;
- reconstrueix els canvis quan la FEB envia l'entrada i la sortida en files separades;
- evita que àlies curts com `Mar` coincideixin dins de cognoms com `MARTÍ`;
- manté sempre cinc jugadores al quintet;
- associa les assistències amb el tir anotat del mateix instant;
- compara els totals generats amb el marcador oficial i no crea l'Excel si no coincideixen.

Els noms es mostren com `Tierno`, `Tapia`, `Pujol`, `Jové`, `Moreno`, `Cojo`, `Dana`, `Mar`, `Ivet`… i no com una inicial.

## Instal·lació

```powershell
python -m pip install -r .\requirements_feb_pbp.txt
python -m playwright install chromium
```

## Jornada 12 — captura normal

Executa-ho des de la carpeta on hi ha els fitxers:

```powershell
python .\feb_pbp_to_excel.py "https://baloncestoenvivo.feb.es/partido/2479761" --team "BASKET ALMEDA" --jornada 12 --aliases .\aliases_almeda.json --output .\j12-pbp-automatic-v3.xlsx
```

El marcador final, vist des d'Almeda, ha de ser:

```text
BASKET ALMEDA 41 - 57 HIERROS DÍAZ EXTREMADURA MIRALVALLE
```

## Reprocessar el debug que ja tens

Aquesta opció és més ràpida perquè no torna a obrir la web:

```powershell
python .\feb_pbp_to_excel.py --from-debug .\feb_debug_2479761.json --team "BASKET ALMEDA" --jornada 12 --aliases .\aliases_almeda.json --output .\j12-pbp-automatic-v3.xlsx
```

## Criteris aplicats

- `Minut`: `M:SS`, per exemple `9:34`.
- `Tàctica`: buida.
- `RO a favor`: rebots ofensius d'Almeda abans de la finalització següent d'Almeda.
- `RO en contra`: rebots ofensius del rival entre dues finalitzacions d'Almeda.
- `RD a favor` i `RD en contra`: buides.
- `Punts RO`: punts anotats després d'un rebot ofensiu dins del mateix tram ofensiu.
- `PF`: punts de la finalització d'Almeda.
- `PC`: punts del rival acumulats abans de la finalització següent d'Almeda.

## Àlies

Edita `aliases_almeda.json` per decidir el nom curt de cada jugadora. La clau és el nom complet i el valor és el text que sortirà a l'Excel.

## Diagnòstic

Per veure el navegador:

```powershell
python .\feb_pbp_to_excel.py "URL" --team "BASKET ALMEDA" --jornada 12 --aliases .\aliases_almeda.json --headful
```

El programa crea també `feb_debug_IDPARTIT.json` i un full `Log`. Si el marcador generat no coincideix amb el marcador oficial, s'atura abans de crear un Excel incorrecte.
