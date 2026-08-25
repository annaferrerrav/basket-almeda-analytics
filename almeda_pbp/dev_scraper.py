# -*- coding: utf-8 -*-
"""
Embolcall de subprocess per a `scraping_pbp/feb_pbp_to_excel.py`.

Aquest mòdul NO importa res d'aquell script — viu en una carpeta a part
(`almeda_pbp/scraping_pbp/`) amb les seves pròpies dependències (Playwright
amb un Chromium real, no una petició HTTP senzilla). Es limita a cridar-lo per
subprocess, exactament com ja el crides tu per terminal, i a interpretar-ne
la sortida.

NOMÉS té sentit executar-ho LOCALMENT, on ja tens Playwright i Chromium
instal·lats (`python -m playwright install chromium`). No funcionarà a
Streamlit Cloud ni a cap entorn sense navegador — per això la pàgina que fa
servir aquest mòdul viu darrere la secció «Developer» de l'app i no s'ha de
desplegar per a la resta del cos tècnic.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ARREL_SCRAPING_PBP = Path(__file__).resolve().parent / "scraping_pbp"
SCRIPT = ARREL_SCRAPING_PBP / "feb_pbp_to_excel.py"

# Carpeta d'esborranys: els PBP generats aquí NO són vistos per l'app (que
# només llegeix `*/data/pbp/*.xlsx`). Cal moure'ls a mà a la carpeta de la
# temporada un cop revisats — així un partit mal extret mai contamina
# l'anàlisi en silenci.
CARPETA_ESBORRANYS = Path(__file__).resolve().parent.parent / "dades" / "pbp_desenvolupament"


@dataclass
class ResultatScraping:
    ok: bool
    sortida_consola: str
    error_consola: str
    fitxer: Path | None
    ordre: str


def assegura_aliases(ruta: Path) -> bool:
    """
    Crea `ruta` amb `{}` si no existeix. Retorna True si l'ha creat.

    Un JSON buit és un valor vàlid per a `--aliases`: el script ja porta uns
    àlies genèrics per defecte (`DEFAULT_ALIASES`); el fitxer només hi afegeix
    els que l'analista vulgui personalitzar.
    """
    if ruta.exists():
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("{}\n", encoding="utf-8")
    return True


def genera_pbp(
    url: str,
    jornada: int,
    aliases: Path,
    sortida: Path,
    equip: str = "BASKET ALMEDA",
    timeout: int = 180,
) -> ResultatScraping:
    """
    Executa `feb_pbp_to_excel.py` per subprocess i retorna el resultat.

    Triga: obre un navegador real i espera que la pàgina del partit carregui,
    compta amb 30-90 segons, no és instantani. El script ja compara el
    marcador generat amb l'oficial i NO crea l'Excel si no coincideixen —
    aquí només es reporta el que digui ell, no es reinterpreta.
    """
    sortida.parent.mkdir(parents=True, exist_ok=True)
    ordre = [
        sys.executable, str(SCRIPT), url,
        "--team", equip,
        "--jornada", str(jornada),
        "--aliases", str(aliases),
        "--output", str(sortida),
    ]

    try:
        procés = subprocess.run(
            ordre,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # la consola de Windows pot no ser UTF-8; no petar per això
            timeout=timeout,
            cwd=ARREL_SCRAPING_PBP,
        )
    except subprocess.TimeoutExpired as err:
        return ResultatScraping(
            ok=False,
            sortida_consola=(err.stdout or ""),
            error_consola=f"S'ha superat el temps màxim ({timeout}s) sense resposta. {err}",
            fitxer=None,
            ordre=" ".join(ordre),
        )
    except FileNotFoundError as err:
        return ResultatScraping(
            ok=False,
            sortida_consola="",
            error_consola=f"No s'ha trobat l'script o Python: {err}",
            fitxer=None,
            ordre=" ".join(ordre),
        )

    ok = procés.returncode == 0 and sortida.exists()
    return ResultatScraping(
        ok=ok,
        sortida_consola=procés.stdout,
        error_consola=procés.stderr,
        fitxer=sortida if ok else None,
        ordre=" ".join(ordre),
    )


def llegeix_aliases(ruta: Path) -> dict[str, str]:
    """Contingut actual del fitxer d'àlies, buit si no existeix o és invàlid."""
    if not ruta.exists():
        return {}
    try:
        dades = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return dades if isinstance(dades, dict) else {}
