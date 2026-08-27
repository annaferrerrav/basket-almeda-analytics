# PBP Basket Almeda

App Streamlit per analitzar el **play-by-play manual** (el que s'anota a mà durant
el partit, amb els sistemes de joc etiquetats jugada a jugada) i comparar-se amb
la resta de la lliga (boxscore oficial de la FEB).

## Posar-ho en marxa

```bash
pip install -r requirements.txt
streamlit run app/Inici.py
```

## Navegació

La barra lateral té tres seccions:

- **Temporada 2025-26** i **Temporada 2026-27 (actual)** — el mateix joc de 7
  pàgines a cadascuna (General, Sistemes, Jugadores, +/-, Rebot ofensiu,
  Informe PDF, Qualitat de dades), cada una bloquejada a la seva temporada.
  No és un fitxer duplicat per temporada: `app/vistes/*.py` té una única
  funció `pagina(temporada)` per pàgina, i `app/Inici.py` en munta dues
  instàncies (vegeu «Estructura»). 26-27 mostrarà missatges de "encara no hi
  ha dades" fins que hi hagi PBP o boxscore d'aquesta temporada.
- **Developer** — eines de l'analista, **només per ús local** (vegeu més
  avall): generar el PBP d'un partit puntual i un constructor lliure
  d'informes PDF.

## D'on surten les dades

L'app busca sola tots els fitxers que encaixin amb:

```
<temporada>/data/pbp/j<NÚMERO>-*.xlsx
```

Per exemple `25-26/data/pbp/j22-pbp.xlsx`. Per afegir la temporada nova només cal
crear `26-27/data/pbp/` i anar-hi deixant els Excel setmana a setmana: **no s'ha
de tocar codi ni cap llista de fitxers**. El selector de temporada i el de
jornades s'omplen sols amb el que hi hagi.

El número de jornada surt del nom del fitxer, no de la columna `Jornada`. Si no
coincideixen, mana el nom del fitxer i surt un avís a la pàgina *Qualitat de
dades* (a 25-26 passa a `j8` i a `j10-pbp_bo`).

## Què vol dir cada fila

Una fila = una jugada d'atac nostra:

- `jug 1`..`jug 5` — el quintet en pista. **L'ordre és la posició** (1 base,
  5 pivot), així que mai s'ordenen alfabèticament.
- `Tàctica` — el sistema que s'ha jugat.
- `Desenllac` — com acaba (`t2c`, `t3f`, `pèrdua`...).
- `PF` / `PC` — punts que fem en aquella jugada / punts que ens fa el rival tot
  seguit. **Ja són l'increment de la jugada**, no un marcador acumulat: el
  diferencial és directament `PF - PC`, sense cap `.diff()`.

⚠️ Les files amb `Tàctica = RO` són la continuació de la mateixa possessió després
d'un rebot ofensiu. Per això a l'app tot es compta **per jugada**, no per
possessió tancada. Si algun dia interessa la possessió com a unitat, cal escriure
una funció que agrupi les files (`RO` amb la jugada anterior).

## Pàgines

| Pàgina | Què hi ha |
|---|---|
| **General** | Comparativa amb la mitjana de la lliga (boxscore FEB) + resum del PBP propi |
| **Sistemes** | Els pie charts sistema → desenllaç, interactius |
| **Jugadores** | Per sistema: qui anota i qui genera els punts amb assistència; i quins sistemes es juguen amb cada jugadora segons la posició |
| **+/-** | Parelles per posició (1·4, 1·5, 2·4...), parelles per nom, individual i jugadora × posició |
| **Qualitat de dades** | Tot el que la càrrega ha trobat estrany |
| **Rebot ofensiu** | RO propi i del rival, i punts de segona oportunitat, per període |
| **Informe PDF** | Tria de jugades i descàrrega del PDF amb números i gràfics |

Els filtres (jornades, períodes, jugadores, sistemes) són a la barra lateral i
valen per a totes les pàgines **d'una mateixa temporada**: canviar de pàgina
dins de «Temporada 2025-26» manté la selecció; canviar a «Temporada 2026-27»
en té una d'independent (l'estat de cada filtre es guarda per temporada, no
es barreja).

Filtrar per jugadora té dos modes:
- **a pista** — jugades on era una de les cinc (com va l'equip amb ella).
- **protagonista** — jugades on va finalitzar o assistir (què fa ella).

## Normalització

Els Excel s'omplen a mà, i el mateix concepte hi apareix escrit de maneres
diferents (`contratac` / `Contraatac`, `t2f` / `T2F`, `Jové` / `jove`). Tot això
es consolida a `almeda_pbp/normalitza.py`.

**Res s'endevina.** Un valor que no sigui a cap diccionari d'àlies es conserva
tal com està i surt llistat a *Qualitat de dades*. Quan n'aparegui un de nou:
o es corregeix l'Excel, o s'afegeix a `ALIES_TACTICA` / `ALIES_DESENLLAC`.

Els noms de columna **no es tradueixen**: `Tàctica`, `Desenllac`, `jug 1` i
companyia es fan servir tal com surten del fitxer.

## Colors

Verd, blau, taronja i gris, per famílies de qualitat del desenllaç:

| Família | Color | Desenllaços |
|---|---|---|
| Cistella | verd `#00661f` | T2C, T3C |
| Falta rebuda | blau `#2a78d6` | Falta, Falta (TLL) |
| Tir fallat | taronja `#f5924b` | T2F, T3F |
| Possessió perduda | gris `#8a8884` | Pèrdua, Banda, Fons |

El **verd és fosc i el taronja clar a propòsit**. El to per si sol no separa el
verd del taronja per a una persona amb deuteranopia o protanopia; qui fa la feina
és la diferència de lluminositat. Amb aquests quatre hexes concrets, els 6
parells passen el llindar de discriminació simulant els tres tipus de daltonisme
(mesurat en OKLab). **Si es canvia cap dels quatre colors, cal tornar-ho a
mesurar**: amb un verd i un taronja de lluminositat semblant el gràfic deixa de
ser llegible per a molta gent.

El color porta la **família**; el desenllaç exacte va escrit a cada porció o a la
llegenda. Cap informació depèn només del color.

El +/- fa servir verd (positiu) i taronja (negatiu), amb el mateix contrast de
lluminositat, i a més el signe ja el porta el costat de la barra.

## Informe PDF

A la pàgina **Informe PDF** tries quines jugades hi entren i et baixes un
document amb, per cada jugada, el donut de desenllaços i les anotadores, més el
resum i (opcionalment) el +/- de la selecció.

El PDF surt del **mateix filtre que hi ha a la barra lateral**, així que no pot
dir res diferent del que veus a pantalla. Els filtres aplicats surten impresos a
la capçalera perquè el document s'entengui tot sol.

Els gràfics del PDF es redibuixen amb **matplotlib**, no s'exporten de Plotly:
fer-ho amb Plotly necessita Kaleido, que es descarrega un Chrome sencer i falla
en entorns sense navegador (Streamlit Cloud, i de fet també en aquesta màquina).
matplotlib i reportlab són wheels pures i no demanen res del sistema. La paleta
és compartida, així que el PDF i la pantalla es veuen igual.

## Boxscores de la FEB (scraping)

Font: `baloncestoenvivo.feb.es`. **No cal passar cap URL**: l'script va al
calendari del grup, en treu els partits de les jornades que li demanis i baixa
cada acta.

```bash
# LF2 2025/26, grups A i B, jornades 1 a 3 (aquests són els valors per defecte)
python -m almeda_pbp.feb --temporada 2025 --lligues A B --jornades 1 2 3

# Una jornada nova d'un sol grup
python -m almeda_pbp.feb --temporada 2025 --lligues A --jornades 4

# Tornar a baixar partits ja desats (p. ex. si la FEB ha corregit una acta)
python -m almeda_pbp.feb --temporada 2025 --jornades 1 --refes
```

⚠️ `--temporada` és l'any d'**inici**: `2025` = 2025/26, `2026` = 2026/27.

Coses a saber de la web de la FEB:

- LF2 és `g=9`. Els identificadors dels grups **canvien cada temporada**, així
  que no estan fixats al codi: es llegeixen del desplegable del calendari.
- Canviar de grup **no** es pot fer per URL (`&c=<grup>` s'ignora): és un
  postback d'ASP.NET amb `__VIEWSTATE`. El client ja ho fa.
- No hi ha `robots.txt`. Igualment hi ha 1,5 s d'espera entre peticions,
  reintents amb espera creixent i un user-agent identificable.

### On es guarda

SQLite a `dades/lf2.sqlite`, taula `boxscore_jugadora`, una fila per jugadora i
partit més una fila `TOTAL` per equip. Hi ha una columna **`Lliga`** amb `A` o
`B`. Tornar a executar l'script no duplica res: esborra els partits afectats
abans d'inserir.

L'accés passa tot per `almeda_pbp/magatzem.py` (`carrega_boxscore()`,
`desa_boxscore()`), així que migrar a Postgres seria tocar només aquell fitxer.

```python
from almeda_pbp import magatzem
dades = magatzem.carrega_boxscore()
print(magatzem.resum_desat())
```

L'app Streamlit **no escriu mai**: només llegeix el que deixa aquest script.

### Comparativa amb la lliga

`almeda_pbp/lliga.py` converteix els boxscores en mètriques d'equip, i la pàgina
**General** les ensenya en caixes: una fila amb la mitjana de la lliga i, just a
sota, la mateixa fila de l'equip amb la diferència.

Dues decisions que canvien els números:

- **Els percentatges surten dels totals acumulats, no de la mitjana de
  percentatges.** Un equip que tira 1/1 un dia i 3/20 un altre té un 19%
  (4/21), no un 57,5% (la mitjana de 100% i 15%).
- **Els comptatges són per partit.** El ritme va a part, a «Possessions», i
  l'eficiència a OER/DER, que sí estan normalitzades per possessió.

Cada mètrica té una direcció (`DIRECCIO` a `lliga.py`): a les pèrdues, les faltes
comeses i els punts encaixats **menys és millor**, i la fletxa de la caixa ho té
en compte. Les mètriques de volum (tirs intentats, possessions) són neutrals i
no es pinten de color, perquè tirar més no és ni bo ni dolent.

Per defecte la comparació és **contra el grup on juga l'equip**, no contra A+B
barrejats, que serien dues competicions diferents.

## Developer

Dues eines a la secció **Developer** de la navegació, pensades per a l'analista,
**només en local**:

### Scraper PBP

Genera el PBP d'un partit puntual a partir de la seva URL de
`baloncestoenvivo.feb.es`, sabent que l'equip analitzat sempre és el BASKET
ALMEDA. Per sota crida `almeda_pbp/scraping_pbp/feb_pbp_to_excel.py` — un
script a part que **NO és de l'app**: fa servir Playwright amb un Chromium
real (no una petició HTTP), triga 30-90 segons i **no funcionarà mai a
Streamlit Cloud** (ja s'ha comprovat en aquesta mateixa màquina: un navegador
headless sense instal·lar peta amb "Could not create session" — el mateix
problema pel qual el PDF no exporta Plotly via Kaleido). Per això aquesta
pàgina crida l'script per `subprocess` (`almeda_pbp/dev_scraper.py`) en
comptes d'importar-lo, i per això viu darrere «Developer» i no a cap
temporada: si mai es desplega l'app a Cloud, cal amagar aquesta pàgina.

El fitxer d'àlies per defecte és `almeda_pbp/scraping_pbp/aliases_almeda_2627.json`
(un JSON `{nom complet FEB: nom curt}` — el mateix format que
`aliases_almeda.json` de 25-26). Si no existeix, l'app el crea buit (`{}`) en
generar el primer PBP; un JSON buit és vàlid perquè l'script ja porta uns
àlies genèrics per defecte.

L'Excel generat es desa a `dades/pbp_desenvolupament/`, **fora** de qualsevol
carpeta `*/data/pbp/`, així que l'app no el recull automàticament. La pàgina
en mostra una previsualització (jugades, punts, taula sencera) perquè es
pugui revisar — sobretot que el quintet rota (si una posició és sempre la
mateixa jugadora, l'extracció ha fallat, vegeu «Quintets no fiables» més
avall) — abans de moure'l a mà a `26-27/data/pbp/` perquè entri a l'anàlisi
de debò.

### Informe a mida

A diferència de la pàgina **Informe PDF** (una temporada fixada, estructura
fixa: un bloc per sistema + un +/- final), aquí es pot combinar **qualsevol**
temporada/jornada/jugadora i triar **lliurement** quins tipus de gràfic
entren al PDF, en qualsevol ordre.

El catàleg de tipus de bloc viu a `almeda_pbp.informe.TIPUS_BLOCS` — un
`dict` de `{id: TipusBloc(etiqueta, abast, construeix)}`. Un bloc d'abast
`"sistema"` (donut de desenllaços, punts anotats/generats) es repeteix un cop
per cada sistema seleccionat; un d'abast `"general"` (+/- individual, per
parelles, per parelles de posició, per jugadora×posició, rebot ofensiu, taula
de sistemes, eficiència per sistema) surt un sol cop. Ampliar el catàleg és
afegir-hi una entrada — la pàgina ja el recorre sencer per pintar els
checkboxes, no cal tocar la UI.

`genera_informe_a_mida()` reutilitza els mateixos ajudants que
`genera_informe()` (`_capcalera_document`, `_construeix_document`,
`_figura_a_imatge`): les dues funcions comparteixen exactament el mateix
peu de pàgina i estil.

## Tests

```bash
python -m pytest tests/ -q
```

`test_pbp.py` corre contra els fitxers reals: si un Excel canvia d'estructura,
ho ha de petar aquí abans que a l'app. Inclou una identitat de control del +/-
(la suma de tots els +/- individuals ha de ser exactament 5 × diferencial de
l'equip, restringida a les jugades amb quintet complet).

`test_app.py` és fum de les pàgines: executa cada `pagina(...)` de
`app/vistes/` amb `AppTest.from_string` (no `from_file`: `app/Inici.py` fa
servir `st.navigation` amb pàgines basades en funcions, i
`AppTest.switch_page()` només sap navegar per camí de fitxer). Corre les 7
pàgines a les dues temporades (incloent-hi 26-27 buida) i les dues de
Developer, i fa clic real als botons de generar PDF.

## Estructura

```
almeda_pbp/          lògica reutilitzable (no depèn de Streamlit)
  config.py          rutes, noms de columna, paleta, temporades (PBP <-> FEB)
  normalitza.py      diccionaris d'àlies i neteja de valors
  carrega.py         descoberta de fitxers, lectura, incidències, filtres
  metriques.py       agregats: sistemes, jugadores, +/-
  grafics.py         figures Plotly (app interactiva)
  informe.py         figures matplotlib + documents PDF (fix i a mida)
  lliga.py           mètriques d'equip i comparativa amb la mitjana
  magatzem.py        accés a SQLite (l'únic lloc que sap de SQL)
  dev_scraper.py     subprocess wrapper de scraping_pbp/ (Developer, local)
  feb/               scraping de baloncestoenvivo.feb.es (boxscores)
    client.py        sessió HTTP amb espera, reintents i postbacks ASP.NET
    calendari.py     descoberta de grups i partits per jornada
    boxscore.py      parsing de l'acta d'un partit
    __main__.py      CLI d'actualització
  scraping_pbp/       eina a part (Playwright): PBP puntual d'un partit
app/
  Inici.py            punt d'entrada: st.navigation per seccions
  _comuns.py          càrrega amb cache, barra de filtres, caixes compactes
  vistes/             una funció pagina(temporada) o pagina() per pàgina
dades/
  lf2.sqlite           boxscores scrapejats
  pbp_desenvolupament/ esborranys del Scraper PBP (Developer), fora del pipeline
tests/
  test_pbp.py          capa de dades i mètriques
  test_app.py           fum de les pàgines Streamlit
```

`almeda_pbp` no importa Streamlit enlloc (excepte `dev_scraper.py`, que tampoc
ho fa — només llança un subprocess): es pot fer servir des d'un notebook o
d'un script sense arrencar l'app.

## PBP automàtics (sense sistemes)

Algunes jornades (9, 12, 17, 20, 23, 26 a 25-26) no tenen PBP manual: en
comptes es carrega un PBP generat automàticament a partir del feed en directe
de la FEB (`almeda_pbp/scraping_pbp/feb_pbp_to_excel.py` — el mateix script
que hi ha darrere la pàgina Developer › Scraper PBP, vegeu «Developer» més
avall). Aquests fitxers tenen quintet, desenllaç i punts, però **no tenen el
sistema de joc** — això no surt del feed, només de l'anotació manual de
l'entrenador.

`carrega.py` els carrega igualment (abans es descartava qualsevol fitxer
sense `Tàctica`; ara només es descarta si **tampoc** té `Desenllac`, senyal
d'una plantilla buida de debò). Una jornada sense sistemes:

- **no surt** a les pàgines *Sistemes* i *Jugadores* (que agrupen per
  `Tàctica`),
- **sí surt** a tota la resta: resum general, +/-, rebot ofensiu, informe PDF.

Es marca com a incidència "Sense sistemes" a *Qualitat de dades*.

### Quintets no fiables

Un partit real sempre té substitucions. Si en carregar un fitxer alguna de
les cinc posicions (`jug 1`..`jug 5`) és sempre la mateixa jugadora (o sempre
buida) a totes les jugades, `_comprova_quintet()` ho detecta com un senyal
que l'extracció no ha capturat els canvis de quintet — típic dels PBP
automàtics quan el feed no dona bé les substitucions — i **buida les cinc
columnes de quintet d'aquest fitxer** (es manté tota la resta: punts,
desenllaços, finalitzadora, assistència). Si no, un quintet fals contaminaria
en silenci el +/- real de la jugadora que hi surt fixa. Es marca com a
incidència "Quintet no fiable"; la comprovació només s'aplica a fitxers amb
20 files o més (amb menys mostra no es pot distingir "no hi ha hagut cap
substitució" d'un error d'extracció).

## Coses conegudes de 25-26

- La **j21** té el fitxer però només amb quintets i minuts: cap tàctica ni
  desenllaç. No es carrega.
- Les **j18 i j19** porten un bloc defensiu (`Tàctica defensiva`, `Desenllaç`,
  `punts`) omplert a mitges que l'app **no analitza**.
- Hi ha tres jornades amb el marcador descuadrat respecte a la suma de PF/PC
  (j6, j16, j25). Surten llistades a *Qualitat de dades*.
- La **j23** és una font automàtica amb el quintet invalidat (vegeu més amunt):
  compta per a punts i desenllaços, però no per al +/-, les parelles ni
  jugadora×posició.
- El **rebot defensiu** (`RD a favor`, `RD en contra`) pràcticament no es va
  anotar: 1 i 2 valors en tota la temporada. Per això la pàgina de rebot és
  només ofensiva.
- Les jornades **1, 2 i 3** no tenen cap columna de rebot.
- Hi ha un `3?` a `Punts RO a favor` de la j4 (dubte de l'anotador). Es reporta
  com a incidència i compta com a buit.

## Desplegament a Streamlit Cloud

### Dos repos: codi públic, dades privades

Streamlit Community Cloud només permet **una app privada per compte** — i el
que compta com a "privada" és que el repo de GitHub sigui privat, no cap
opció de l'app. Per poder desplegar aquesta app sense fer-la dependre de
l'única plaça privada (ocupada per una altra), el projecte es reparteix en
dos repos:

- **`basket-almeda-analytics`** (aquest repo, públic): tot el codi. No conté
  cap fitxer de dades — `25-26/data/pbp/`, `25-26/data/boxscore_jornada/`,
  `dades/lf2.sqlite`, `dades/etiquetes_sistemes.toml` i
  `dades/noms_jugadores.toml` són al `.gitignore`.
- **`basket-almeda-analytics-dades`** (privat): exactament aquests fitxers,
  amb la mateixa estructura de carpetes. Conté noms complets de jugadores,
  per això és privat.

En local, els fitxers de dades ja són al disc (com sempre) i l'app els
llegeix directament — cap canvi en el dia a dia de l'analista. A Streamlit
Cloud, el clonat inicial del repo públic no els porta; `app/_dades_remot.py`
ho detecta a l'arrencada (mira si `dades/lf2.sqlite` existeix) i, si falten,
descarrega el repo privat de dades via l'API de GitHub amb un token de
només lectura (`almeda_pbp/sync_dades.py`, sense cap dependència de
Streamlit: és pur Python, reutilitzable fora de l'app). Passa un sol cop per
contenidor, no a cada rerun.

### Configuració al diàleg de desplegament

- **Main file path**: `app/Inici.py`
- **Python version**: 3.11 o superior (`almeda_pbp/etiquetes.py` i
  `jugadores.py` fan servir `tomllib`, que és stdlib només a partir de 3.11).
  Es tria a *Advanced settings*; no hi ha cap fitxer al repo que ho fixi.
- **Secrets** (*Advanced settings → Secrets*, format TOML):

  ```toml
  dades_github_token = "ghp_..."
  # dades_repo = "annaferrerrav/basket-almeda-analytics-dades"  # per defecte
  ```

  El token ha de ser un **fine-grained personal access token** de GitHub
  (Settings → Developer settings → Personal access tokens → Fine-grained
  tokens) amb accés limitat **només** al repo `basket-almeda-analytics-dades`
  i permís **Contents: Read-only** — cap més permís, cap altre repo. Sense
  aquest secret configurat, l'app mostra un error clar a l'arrencada en lloc
  de petar.
- **Secció Developer**: no hi surt, i és volgut. Apareix només si
  `almeda_pbp.config.mode_dev()` és cert, és a dir si hi ha un fitxer buit
  `.mode_dev` a l'arrel (ignorat per git, per tant mai al núvol) o si
  `ALMEDA_DEV=1`. En una màquina nova cal crear el marcador per recuperar-la:
  `touch .mode_dev` (o `New-Item .mode_dev` a PowerShell).

### Actualitzar les dades

Els fitxers de dades **ja no es publiquen fent push al repo de codi**. Cal
fer-ho al repo de dades: després d'executar l'scraper o d'afegir un jornada
nou en local, copiar els fitxers canviats (`25-26/data/pbp/`,
`25-26/data/boxscore_jornada/`, `dades/lf2.sqlite`, etc.) a un clon local de
`basket-almeda-analytics-dades`, fer commit i push allà. Streamlit Cloud no
detecta aquest canvi automàticament: un cop `dades/lf2.sqlite` existeix al
contenidor, `assegura_dades()` ja no torna a baixar res. Cal forçar un
contenidor nou — un *reboot* des del panell de Streamlit Cloud, o qualsevol
push al repo de codi que ja toqués redesplegar — perquè agafi les dades
noves. (No verificat si un simple reboot sempre crea contenidor nou o de
vegades reutilitza disc; si les dades no s'actualitzen amb un reboot, cal
mirar-ho.)

Els informes `.docx` de `25-26/data/report/` no són a cap dels dos repos
(vegeu `.gitignore`), així que tampoc al núvol.
