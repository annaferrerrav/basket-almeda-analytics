# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit analytics app for Basket Almeda (Liga Femenina 2, group A). Covers
two seasons side by side — **2025-26** (complete) and **2026-27** (current,
mostly empty until games are played) — plus a **Developer** section of local-
only tools. Two independent data sources feed the season pages:

1. **Manual play-by-play** — Excel files the analyst fills in by hand during
   games, one row per own-team possession, with the offensive system tagged.
2. **Official FEB boxscores** — scraped from `baloncestoenvivo.feb.es` for
   both league groups (A and B), stored in SQLite, used to compare Almeda
   against the league average.
3. **Per-system tags** (`almeda_pbp/etiquetes.py`) — a hand-written TOML at
   `dades/etiquetes_sistemes.toml` mapping each `Tàctica` value to a free-form
   tag list (`"Pisa" = ["banda"]`). TOML and not Excel because this describes
   the *playbook*, not the plays: tens of rows, stable across a season, read
   like a config file. `python -m almeda_pbp.etiquetes` regenerates the list of
   systems from the loaded PBP, ordered by usage with the play count as a
   comment, and never destroys existing tags — a system that disappears from
   the PBP is kept if it has tags, since it may belong to a season that isn't
   loaded right now. Filtering by a tag selects *plays* but decides by
   *system*. Only the *Sistemes* page reads them (`_cercador_etiquetes`).

The two pipelines don't share code. `almeda_pbp/` contains no Streamlit
imports (except `dev_scraper.py`, which only shells out to a subprocess) — it
can be used from a script or notebook without launching the app.

Everything is written in Catalan: code comments, docstrings, column names,
UI text. Column names from the source Excel files (`Tàctica`, `Desenllac`,
`jug 1`..`jug 5`, `PF`, `PC`) are used verbatim throughout the codebase —
they are never translated or snake_cased, so the source files and the code
speak the same language.

## Commands

```bash
pip install -r requirements.txt

# Run the app
streamlit run app/Inici.py

# Run tests
python -m pytest tests/ -q
python -m pytest tests/test_pbp.py::test_plus_minus_quadra_amb_el_diferencial -q  # single test

# Update FEB boxscores (writes to dades/lf2.sqlite)
python -m almeda_pbp.feb --temporada 2025 --lligues A B --jornades 1 2 3
python -m almeda_pbp.feb --temporada 2025 --lligues A --jornades 4   # one jornada, one group
python -m almeda_pbp.feb --temporada 2025 --jornades 1 --refes       # force re-download
```

`--temporada` is the season's **start year**: `2025` = 2025/26.

There is no `.git` repository here yet, no lint config, and no pytest config
file — `pytest tests/ -q` is the whole test command.

## Architecture

### Two pipelines, one app

- **PBP pipeline** (`carrega.py` → `metriques.py` / `grafics.py` / `informe.py`):
  reads the manual Excel files directly at app startup, no database involved.
- **FEB pipeline** (`feb/` → `magatzem.py` → `lliga.py`): a separate CLI
  script scrapes the FEB site and writes to SQLite; the Streamlit app only
  ever *reads* that database. The app never scrapes and never writes to the
  DB — `python -m almeda_pbp.feb` is a manual, out-of-band step the analyst
  runs periodically.

The **General** vista is the only one that touches both pipelines (league
comparison up top from the FEB data, PBP summary below). Every other vista is
PBP-only.

### Navigation: one function per page, two instances per season

`app/Inici.py` is the entrypoint — it's the only place `st.set_page_config`
is called, and the only place that builds the nav via `st.navigation({...})`.
There is no `app/pages/` directory (Streamlit's old filename-convention
auto-discovery); pages are explicit `st.Page(...)` objects instead, which is
what makes grouped sections ("Temporada 2025-26" / "Temporada 2026-27
(actual)" / "Developer") possible at all.

Each season page lives in `app/vistes/<nom>.py` as **one function**
`pagina(temporada: str) -> None` — not a script, not two files. `Inici.py`
builds two `st.Page`s per vista via `functools.partial(vista.pagina, "25-26")`
/ `functools.partial(vista.pagina, "26-27")`, reading the season list from
`config.TEMPORADES` (the single place to add a season). This means a season
section is *not* a data filter dropdown — it's a distinct navigation entry
that pre-binds which season's data the page ever sees.

Because both instances of, say, `vistes/sistemes.py` are literally the same
Python function, Streamlit widget `key`s inside it would collide across
seasons unless namespaced — `app/_comuns.py`'s `barra_filtres(df,
temporada_fixada=...)` suffixes every filter widget key with `f"__{temporada}"`,
and `vistes/informe_pdf.py` does the same by hand for its own `pdf_*` keys
(session-state values like `pdf_bytes` aren't tied to a widget's lifecycle,
so without the suffix, generating a PDF on the 25-26 page and then navigating
to the 26-27 page would show a stale download button offering last season's
file). Purely cosmetic per-page widgets (chart size sliders, etc.) are left
unsuffixed on purpose — sharing those across season instances is harmless.

`vistes/qualitat_dades.py` is season-scoped like the rest (defaults to
showing that season's incidents) but has a "veure totes les temporades"
toggle, since data-quality issues are sometimes worth seeing across seasons
at once.

### Developer section — local-only tools

Two pages under "Developer" in the nav, both gated on running locally (never
intended for Streamlit Cloud):

- **Scraper PBP** (`vistes/dev_scraper.py` + `almeda_pbp/dev_scraper.py`):
  generates one match's PBP from its FEB URL. Calls
  `almeda_pbp/scraping_pbp/feb_pbp_to_excel.py` via `subprocess`, never via
  `import` — that script drives **Playwright with a real Chromium**, not an
  HTTP request, and a headless browser with no browser installed is exactly
  what already failed on this machine once (see the Kaleido note below).
  Output goes to `dades/pbp_desenvolupament/`, deliberately *outside* any
  `*/data/pbp/` folder so `carrega.py`'s glob never picks it up automatically
  — the analyst reviews the preview in-app, then moves the file into
  `26-27/data/pbp/` by hand once satisfied.
- **Informe a mida** (`vistes/dev_informe.py` + `informe.genera_informe_a_mida`):
  a free-form report builder — any season/jornada/jugadora combination, any
  subset of chart types, in contrast to `vistes/informe_pdf.py`'s fixed
  one-season / one-block-per-system structure. See "PDF report registry"
  below.

### PBP data model — the non-obvious part

Each row in a manual PBP Excel file is **one own-team possession**, not one
event. `PF`/`PC` are already the point *increment* of that possession (own
points scored / opponent's immediate response), not a running scoreboard —
so any +/- calculation is `PF - PC` directly, never `.diff()`. Rows tagged
`Tàctica == "RO"` are the continuation of the previous possession after an
offensive rebound, which is why everything in the app is counted "per play"
rather than "per possession" — a possession that includes an offensive
rebound spans two rows. `jug 1`..`jug 5` are court positions (1=base,
5=pivot), not arbitrary slots, so they are never sorted alphabetically.

`carrega.py` discovers season folders itself via the glob
`*/data/pbp/*.xlsx` under the repo root — adding a new season is just
creating `26-27/data/pbp/` and dropping files in; nothing in the code
references season or jornada numbers directly. The jornada number comes from
the filename (`jNN-*.xlsx`), not the `Jornada` column inside the file; when
they disagree the filename wins and it's logged as an incident.

**Nothing is silently guessed.** `normalitza.py` holds alias dictionaries
(`ALIES_TACTICA`, `ALIES_DESENLLAC`) that fold hand-typed variants
(`contratac`/`Contraatac`, `t2f`/`T2F`) into canonical forms. A value that
matches no alias is kept as-is and surfaces as an incident on the *Qualitat
de dades* page rather than being coerced or dropped — same for schema
problems (missing columns, empty jornada files, scoreboard/PF-sum
mismatches, duplicate jornada files). `carrega_pbp()` returns both the
dataframe and this incident list; check it before trusting aggregates on
new data.

A jornada file is only fully **discarded** if it has neither `Tàctica` nor
`Desenllac` filled anywhere (a genuinely blank template). A file with plays
but no system tags — the case for jornades backfilled from
`feb_pbp_to_excel.py` (see below) — is kept and flagged "Sense sistemes"
instead: it contributes to everything except the system-grouped pages.
Separately, `_comprova_quintet()` nulls out all five `jug 1`..`jug 5`
columns for a whole file (not just the offending position) if any single
position never changes across ≥20 rows — a real game always has
substitutions, so a static position means the automatic extraction lost
them; leaving it in would silently attribute a real player's +/- to plays
she may not have been on court for. Flagged "Quintet no fiable"; the rest of
that file's data (points, outcomes, scorer/assist) stays valid. Because of
this, +/- identity checks in tests only hold over rows with a complete
quintet (`df.dropna(subset=cfg.COLS_QUINTET)`), not the raw loaded frame.

### FEB scraping — non-obvious FEB-site behavior

- `feb/client.py` wraps `requests` with rate limiting, retries, and
  ASP.NET postback support. **Switching league group cannot be done via URL
  parameter** — `&c=<groupId>` is silently ignored by the site. It requires
  a POST with `__VIEWSTATE`/`__EVENTVALIDATION` scraped from the prior GET,
  targeting the group dropdown. `feb/calendari.py` handles this.
- Group IDs (`88868`/`88869` for A/B in 2025/26) **change every season** and
  are never hardcoded — they're read from the calendar page's dropdown at
  runtime via `feb.calendari.grups()`.
- `feb/boxscore.py` parses a match page into one row per player plus a
  `Jugador == "TOTAL"` row per team. Opponent points come from the match
  scoreboard, not from reversing the concatenated dataframe — the earlier
  version of this scraper (`25-26/scripts/scraping_boxscore_jornada.py`,
  kept for reference only, not imported anywhere) got this wrong when the
  two teams had different roster sizes.
- `magatzem.py` is the single place that knows SQL; `desa_boxscore()` is
  idempotent (deletes then re-inserts by `PartitID`), so re-running the
  scraper never duplicates rows. Swapping SQLite for Postgres later means
  touching only this file (repository pattern).

### Roster page — official boxscore, not PBP (`jugadores.py`)

`vistes/jugadores.py` reads the **FEB boxscore**, not the manual PBP: minutes,
shooting splits, fouls and blocks only exist on the official sheet, and what
both sources have (points, assists) is refereed there. The PBP still supplies
the bottom half of a player's card — which systems she was on court for, +/-
by position, play-by-play detail — because the boxscore knows none of that.

Joining the two needs a name table: the PBP uses short names (`Tierno`,
`Puyi`), the sheet uses `TIERNO MARTÍ, LAURA`. It lives in
`dades/noms_jugadores.toml`, generated by `python -m almeda_pbp.jugadores`,
which fills in only **unambiguous** matches (the short name appears whole
inside exactly one official name) and leaves the rest blank. It never guesses a
doubtful pair: a wrong match silently merges two different players' stats,
which is worse than having none. Regenerating preserves what is already
written.

`plantilla_oficial()` follows the same rule as `lliga.py`: percentages come
from summed totals, never from averaging per-game percentages — and
`per_partit=True` divides the counting stats only, leaving percentages alone.

### Rebounding page — the two sources split the question (`vistes/rebot.py`)

Two tabs, RO and RD, and the split between sources is deliberate: the **PBP**
records a rebound against the *possession*, not the player, so it can say how
many offensive rebounds happened and what came of them (`Tàctica == "RO"` rows
are the continuation after one) but never who grabbed it. The **boxscore** knows
who grabbed each one but not what happened next. So "which players get
rebounds" reads the official sheet and "how many are conceded with her on
court" reads the PBP — they never share a table.

`metriques.PUNTS_PER_RO = 2` is the ceiling used by the dashed reference lines:
what second-chance points would be if every offensive rebound ended in a made
two. Two and not three because a putback is the typical continuation; taking 3
would inflate the line with threes that are barely shot after a rebound. The
PBP's `RD a favor` / `RD en contra` columns are effectively unfilled (1 and 2
values across all of 25-26), which is why the RD tab's own-rebound numbers come
from the boxscore instead.

### League comparison metrics (`lliga.py`)

- **Percentages are computed from summed totals, not averaged per game** —
  a team going 1/1 one game and 3/20 the next is 19% (4/21), not the mean of
  100% and 15%.
- **Counting stats are per-game averages**; pace and efficiency are handled
  separately (`Possessions`, `OER`/`DER`/`NET`), which *are* normalized per
  possession.
- `DIRECCIO` maps each metric to whether higher is better (+1), worse (-1),
  or neutral (0, e.g. shot volume) — this drives which comparisons get
  colored and ranked in the UI; neutral metrics are never color-coded.
- `BLOCS` groups metrics for the compact "General" page display; `FACTORS`
  (eFG%, %TO, ORB%/DRB%, RTL) is the classic Four Factors set and is
  rendered as a visually distinct block (accent color) from raw box-score
  counts, since it's derived efficiency, not a countable stat. `BLOCS_OCULTS`
  (TapF/TapC/MT, TLC/TLI) is hidden by default behind a "Mostrar tot" toggle.
  `metriques_disponibles()` — used for rankings and the full data table —
  always includes everything regardless of what the compact view shows.
- ORB%/DRB% need the *opponent's* rebounds from the same game
  (`totals_per_partit()` self-joins the boxscore on `PartitID`).

### Color palette (`config.py`)

Colors are chosen by measurement, not by eye — green/orange/blue/gray with
specific hex values, deliberately dark-green vs light-orange (not
light-green) because luminance, not hue, is what separates them under
deuteranopia/protanopia simulation. **If any of the four hexes change, the
separation has to be re-measured** (see the long comment block in
`config.py` for the method) or the charts stop being readable for a
meaningful fraction of colorblind viewers. Color always carries a *family*
(made/foul/miss/turnover), never the exact outcome alone — the specific
outcome label is always also present as text.

`grafics.py` (Plotly, interactive app charts) and `informe.py` (matplotlib,
static PDF charts) both read from the same `config.py` palette so the PDF
and the on-screen charts render identically. `informe.py` deliberately does
*not* export Plotly figures via Kaleido — Kaleido downloads a full Chrome
and fails in browserless environments (confirmed broken on this machine and
expected to fail on Streamlit Cloud too) — it redraws everything natively in
matplotlib instead.

### PDF report registry (`informe.py`)

`genera_informe()` (fixed structure, used by `vistes/informe_pdf.py`) and
`genera_informe_a_mida()` (free-form, used by `vistes/dev_informe.py`) share
their document plumbing (`_capcalera_document`, `_construeix_document`,
`_figura_a_imatge`) but not their content logic. The free-form generator
drives off `TIPUS_BLOCS: dict[str, TipusBloc]`, where each entry has an
`abast` of `"sistema"` (repeated once per selected system — donut, points
anotats/assistits) or `"general"` (emitted once regardless — +/- variants,
rebot, tables). Adding a new block type to the a-mida builder is adding one
`TIPUS_BLOCS` entry; the page already iterates the whole registry to draw its
checkboxes.

`_figura_a_imatge(figura, amplada_cm)` always caps the rendered height
(`alcada_max_cm`, default 21cm) and shrinks the width to compensate if a
figure would be taller than that at the requested width — without this, a
matplotlib horizontal-bar chart with many rows (e.g. `plus_minus_parelles_posicio`,
which can have 30+ position-pair rows) produces an image taller than an A4
page, and reportlab raises `LayoutError` instead of scaling it. This was a
real crash caught while building the a-mida report (see
`test_informe_a_mida_amb_taula_gran_no_peta`) — `genera_informe()`'s own
charts never hit it because its inputs are bounded (≤~20 players), but
anything reusing `_figura_a_imatge` with a caller-supplied table needs this
safety net.

Streamlit exposes no theme CSS variables or `data-theme` attribute to custom
HTML (verified against Streamlit's own JS bundle — there is none), so the
compact metric tiles in `app/_comuns.py` (`fila_caixes`, `injecta_estil_caixes`)
hardcode Streamlit's actual default light/dark hex values with a
`prefers-color-scheme` media query, rather than referencing nonexistent
`var(--...)` tokens.

### Testing approach

`tests/test_pbp.py` runs against the real PBP Excel files under `25-26/`
where possible (skipped if absent) — so a change to the Excel schema fails a
test before it fails the app. Includes a control identity for +/-: the sum
of all individual +/- values must equal exactly `5 × team point
differential` (every possession has 5 players on court). Synthetic
DataFrames are used for edge cases (division by zero, empty selections,
position-pair combinatorics) that aren't guaranteed to occur in the current
data. Also covers `dev_scraper.genera_pbp()` with `subprocess.run` monkeypatched
(no real Playwright/browser call in tests) and `informe.genera_informe_a_mida()`.

`tests/test_app.py` smoke-tests every vista by executing its `pagina(...)`
function through `AppTest.from_string(...)` — **not** `AppTest.from_file` +
`.switch_page()`, because `switch_page()` only knows how to navigate to a
page by file path, and every page here is a plain function bound via
`functools.partial` inside `st.navigation`, not a separate script file.
`from_string` sidesteps that by building a tiny inline script that imports
the vista module and calls `pagina(temporada)` directly (`sys.path` gets
`app/` inserted first, matching what `Inici.py` does at runtime) — this is
the pattern to follow for any new vista's smoke test, not `from_file`.

## Known repo quirks

- `almeda_pbp/scraping_pbp/` (`feb_pbp_to_excel.py`) is a separate experiment
  with its own dependencies (Playwright) — its *code* is never `import`ed,
  only invoked via `subprocess` from `almeda_pbp/dev_scraper.py` (Developer ›
  Scraper PBP). Its *output* — system-less PBP `.xlsx` files — gets dropped
  into `25-26/data/pbp/` (or `26-27/...` going forward) alongside the manual
  ones, where `carrega.py` picks it up like any other jornada (see "Sense
  sistemes" / "Quintet no fiable" above). Don't modify this script's
  internals unless asked to.
- `25-26/scripts/*.py` are the analyst's original one-off matplotlib/pandas
  scripts that predate this app; several were the starting point for
  `almeda_pbp/` modules but are not imported by them.
- Known data issues for the 2025-26 PBP files (missing jornadas, an empty
  jornada 21, a malformed value, scoreboard mismatches) are documented in
  README.md's "Coses conegudes de 25-26" section and surfaced live via the
  *Qualitat de dades* page — check there rather than assuming a given
  jornada's data is clean.
