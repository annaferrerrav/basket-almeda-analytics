# PROMPT PER A CLAUDE CODE — Plataforma d'Analytics Basket Almeda (LF2)

## ROL
Actua com a enginyer de software sènior especialitzat en aplicacions de dades
amb Python (pandas, numpy, bs4/requests, openpyxl, streamlit, plotly/matplotlib).
Construeix una aplicació modular, ben estructurada i documentada, pensada per
créixer setmana a setmana durant tota una temporada esportiva.

## CONTEXT
- Equip: Basket Almeda (Liga Femenina 2, grup C, temporada 2026-27 en curs).
- Usuari: analista de dades de l'equip, amb coneixements de Python.
- Objectiu final: una app Streamlit accessible a la resta del cos tècnic (en
  una fase futura, amb autenticació per correu via Streamlit Cloud — NO cal
  implementar autenticació ara, deixa-ho preparat però fora d'abast).
- Fonts de dades:
  · Web pública de resultats/calendari/boxscores: baloncestoenvivo.feb.es
    (competició LF2, grups A i B com a referència de format i, si escau,
    grup C que és on juga Basket Almeda — verificar IDs de competició amb
    l'usuari abans de fer scraping massiu).
  · PBP oficial (play-by-play) de cada partit, disponible a la mateixa web.
  · Gráfico de tiro (shot chart) per partit.
  · PBP manual en Excel de l'usuari, amb els SISTEMES de joc etiquetats
    jugada a jugada (estructura exacta pendent de confirmar amb l'usuari).
  · Plantilla Excel de scouting rival ja existent (format openpyxl a
    respectar, NO recrear des de zero).

## ARQUITECTURA PROPOSADA (amb supòsits marcats — confirmar amb l'usuari)

- **Emmagatzematge**: [SUPÒSIT] SQLite per a desenvolupament i proves locals.
  ⚠️ Streamlit Community Cloud NO té filesystem persistent entre redeploys,
  així que per a producció (actualització setmanal real) cal migrar a una
  DB externa gratuïta: Postgres (Supabase/Neon) o alternativa lleugera
  (Google Sheets com a backend). Implementa la capa de dades amb un
  repository pattern (funcions `get_*`/`save_*` desacoblades de SQL concret)
  perquè migrar de SQLite a Postgres sigui trivial. Pregunta a l'usuari
  abans de fixar la solució definitiva de producció.
- **Frontend**: Streamlit, app multipàgina (`pages/`).
- **Scraping**: `requests` + `BeautifulSoup4`, amb rate limiting (sleep entre
  peticions), user-agent identificable, i gestió d'errors/reintents. Cap
  petició en paral·lel agressiva a la web de la FEB.
- **Visualització**: `plotly` (interactiu, millor per Streamlit) per a
  piecharts de sistemes, +/- per parelles, comparatives de 4 Factors.
- **Autenticació**: cap en aquesta fase. [SUPÒSIT — es farà via Streamlit
  Cloud + llista de correus en una fase futura].
- **Flux d'actualització de dades**: NO es fa des de la UI. L'analista (que
  programa) executa scripts CLI (`python -m scraping.actualitza_jornada ...`)
  de manera manual/periòdica, que escriuen a la BBDD compartida. La app
  Streamlit és NOMÉS de lectura/consulta per a la resta del cos tècnic —
  no exposis cap acció d'escriptura a la UI.

## MODEL DE DADES (esquema orientatiu — ajustar segons dades reals)

Taules mínimes:
- `equips` (id, nom, grup, temporada)
- `partits` (id, temporada, jornada, equip_local, equip_visitant,
  resultat_local, resultat_visitant, data, url_font)
- `boxscore_jugadora` (partit_id, equip_id, jugadora, minuts, TCC, TCI,
  T3C, T3I, TLC, TLI, RO, RD, AS, BP, ROB, TAP_F, TAP_C, FP, FR, VAL,
  inicial, plus_minus)
- `pbp_events` (partit_id, quarter, temps, equip_id, jugadora, tipus_event,
  resultat) — PBP OFICIAL (scraped de la web, sense sistema)

- `pbp_manual` — PBP MANUAL EN EXCEL (font real del sistema de joc, jugada a
  jugada). **Esquema confirmat a partir del fitxer real aportat per l'usuari**
  (`j22-pbp.xlsx`, 1 fila = 1 jugada, no 1 fila = 1 possessió completa):
  - `jornada`, `rival`, `data`, `hora`, `loc_visit` (Local/Visitant)
  - `periode` (1-4), `minut` (minut restant del període)
  - `jug_1..jug_5` (quintet en pista en aquesta jugada)
  - `tactica` (sistema executat; valors reals vistos: play, cuatro, siena,
    lliure, contratac, RO, CD, cinco, lado, go, final, banda 35, fons 21,
    tac30/33/35, "2 mano", o "-" quan no aplica)
  - `desenllac` (resultat de la jugada; valors reals: t2c, t2f, t3c, t3f,
    falta, falta (tll), pèrdua, banda, "-")
  - `assist` (jugadora, sovint buida — només s'omple quan hi ha assistència)
  - `finalitzadora` (jugadora que acaba la jugada)
  - `pf`, `pc` (punts equip propi / punts rival generats en aquesta jugada)
  - `marcador_equip`, `marcador_rival`, `marcador` (acumulat, format "X-Y")
  - `ro_a_favor`, `rd_a_favor`, `ro_en_contra`, `rd_en_contra` (rebots
    ofensius/defensius propis i del rival — **aquí ja tenim el desglossat
    RO/RD per als partits propis**, cosa que permet calcular ORB%/DRB%
    reals per als NOSTRES partits sense haver-los d'estimar)
  - `punts_ro_a_favor`, `punts_ro_rival` (segona oportunitat)

  ⚠️ Com que 1 fila ≠ 1 possessió (una RO genera una fila nova dins la
  mateixa possessió lògica), cal una funció `agrupa_possessions()` que
  reconstrueixi possessions a partir de talls lògics (canvi de "Marcador",
  pèrdua, tir convertit sense RO posterior, falta personal amb tirs lliures
  finals, fi de període). Implementa-ho com a pas explícit i testeja'l amb
  aquest fitxer real abans de generalitzar-ho a tota la temporada.

Mètriques derivades (calculades, no emmagatzemades en brut, per evitar
inconsistències — recalcular sempre a partir de la taula base):
- Plays = TCI + 0.44·TLI + BP
- %TS, %TO, RTL, %US2/%US3/%US1
- Possessions = TCI + 0.44·TLI + BP − RO
- eFG% = (TCC + 0.5·T3C) / TCI
- TOV% = BP / Plays
- ORB% = RO / (RO + RD_rival) ; DRB% = RD / (RD + RO_rival)
  ⚠️ Requereix RO/RD del RIVAL en el mateix partit — verificar que el
  boxscore de baloncestoenvivo dona aquesta dada desglossada per equip
  (normalment sí, al boxscore complet del partit). Si no, cal calcular-ho
  restant el rebot ofensiu propi del total de rebots del rival.
- FT rate = TLI / TCI (indicar sempre quina variant s'usa als informes)
- OER = 100·PT/Pos ; DER = 100·PT_rival/Pos ; NET = OER − DER

## FASES DE DESENVOLUPAMENT

### FASE 0 — Setup
- Estructura de repo (`/scraping`, `/data`, `/analytics`, `/app` (Streamlit),
  `/tests`, `requirements.txt`, `README.md`, `.env.example`).
- Configuració de secrets (credencials DB) via `st.secrets` / `.env`.

### FASE 1 — Ingesta històrica (temporada 2025-26)
1. Scraper de calendari/resultats per jornada i grup.
2. Scraper de boxscore complet per partit (local + visitant).
3. Scraper de PBP oficial (si l'estructura HTML ho permet raonablement).
4. Càrrega del PBP manual en Excel (sistemes) — necessito l'estructura de
   columnes real; si no la tinc, defineix un parser flexible amb columnes
   configurables per YAML/dict de mapeig.
5. Persistència a la BBDD segons l'esquema anterior.
6. Tests bàsics: recompte de partits per jornada, valors nuls, duplicats.

### FASE 2 — Anàlisi de lliga (temporada sencera)
7. Càlcul de 4 Factors ofensius/defensius per equip + mitjana de lliga.
8. Taula de "palanques": per cada equip, diferència vs mitjana de lliga en
   cada factor (ofensiu i defensiu), amb interpretació automàtica en
   llenguatge natural (ex: "eFG% ofensiu +6pts vs mitjana → punt fort de tir;
   TOV% defensiu −3pts vs mitjana → feblesa forçant pèrdues").
9. Perfil Victòria/Derrota per equip: mitjanes de mètriques clau (punts,
   assistències, T3, RO, %TO, ritme/possessions) separades per partits
   guanyats vs perduts, amb diferència (effect size simple, tipus
   diferència de mitjanes) i avís explícit quan la mostra és petita
   (< 5-6 partits en un dels dos grups) per no sobreinterpretar.

### FASE 3 — UI Streamlit
Pàgines mínimes:
- **Lliga**: taula de 4 Factors + rànquings, filtre per equip → comparativa
  amb mitjana de lliga, badge visual de punts forts/febles.
- **Fitxa de rival**: selector d'equip → 4F, perfil G/P, jugadores clau
  (per punts/assistències/ús), enllaç per generar plantilla de scouting.
- **Equip propi (post-jornada)**: pujada/selecció de partit → anàlisi de
  sistemes (eficiència, piechart d'ús, jugadores que més punts/assistències
  generen per sistema), RO, boxscore, +/- per parelles.
- (Sense pàgina d'actualització a la UI — l'actualització la fa l'analista
  per script/CLI, com s'indica a l'arquitectura.)

### FASE 4 — Scouting rival (Excel)
10. Reutilitzar/adaptar el codi openpyxl existent (l'usuari l'aportarà) per
    omplir la plantilla a partir de les dades ja carregades a la BBDD,
    sense trencar el format.

## RESTRICCIONS
- Codi Python modular, funcions reutilitzables, comentaris en català.
- Gestió explícita de divisions per zero i valors buits (np.where o
  equivalent) a totes les mètriques derivades.
- No trencar el format de la plantilla de scouting existent (openpyxl).
- Si falta una dada crítica per a un càlcul (p. ex. estructura del PBP
  manual, RO/RD del rival), atura't i pregunta — no inventis valors.
- Distingir sempre correlació de causalitat a les conclusions generades
  automàticament (perfil G/P, palanques de 4F).
- Respecta robots.txt i afegeix rate limiting raonable al scraping.

## LLIURABLE ESPERAT EN AQUESTA PRIMERA INTERACCIÓ
1. Un pla d'arquitectura final (confirmant o proposant alternativa als
   supòsits marcats [SUPÒSIT]), amb les preguntes obertes que necessitis
   respondre abans de programar.
2. L'esquema de BBDD definitiu (DDL SQL).
3. Comença a implementar la Fase 0 i la Fase 1 (scraping + model de dades),
   deixant Fase 2-4 per a iteracions següents.

## FITXER D'EXEMPLE ADJUNT
S'aporta `j22-pbp.xlsx` (jornada 22, temporada 2025-26) com a referència real
de l'esquema del PBP manual. Fes-lo servir per validar el parser i la funció
`agrupa_possessions()` abans de generalitzar a la resta de jornades — els
noms de columnes hi són en català/castellà mixt tal com surt del fitxer real
(`Tàctica`, `Desenllac`, `jug 1`...`jug 5`, etc.), NO els tradueixis sense
avisar-me primer si canvies noms de columna internament.

## PREGUNTES OBERTES QUE HAURIES DE FER-ME (Claude Code) SI NO TENS RESPOSTA
- Codi de scraping ja existent que hagi de reutilitzar en lloc de refer.
- IDs/URLs exactes de competició per a LF2 grup C (Basket Almeda) i grups
  A/B de referència, per temporades 2025-26 i 2026-27.
- Confirmació de la solució de BBDD de producció (SQLite local vs
  Postgres extern vs Google Sheets), tenint en compte que l'actualització
  es fa per script des del meu ordinador i la BBDD ha de quedar accessible
  després per la Streamlit Cloud que usaran els altres entrenadors.
- Si el boxscore de baloncestoenvivo.feb.es dona RO/RD desglossat per equip
  també pel RIVAL (no només al PBP manual, que és només dels partits propis)
  — necessari per calcular ORB%/DRB% de qualsevol equip de la lliga, no
  només del Basket Almeda.
