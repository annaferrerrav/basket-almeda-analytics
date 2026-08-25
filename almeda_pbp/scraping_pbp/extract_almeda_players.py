#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extreu totes les jugadores de BASKET ALMEDA que apareixen en els 26 partits
indicats i genera una plantilla JSON d'àlies.

REQUISIT:
    Aquest fitxer ha d'estar a la mateixa carpeta que:
        feb_pbp_to_excel.py
        aliases_almeda.json   (opcional, però recomanat)

El programa reutilitza el scraper estable de feb_pbp_to_excel.py.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Any

PARTITS ={
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
    25: "https://baloncestoenvivo.feb.es/partido/2479852",
    26: "https://baloncestoenvivo.feb.es/partido/2479863"}

def norm(text: Any) -> str:
    value = "" if text is None else str(text)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"\s+", " ", value).strip().upper()
    return value


def surname_identity(name: str) -> str:
    """
    Converteix:
      'GARCIA MENÉNDEZ, MARINA' -> 'GARCIA MENENDEZ'
      'M. GARCIA MENÉNDEZ'     -> 'GARCIA MENENDEZ'
      'A. COJOCARIU'            -> 'COJOCARIU'
    Això permet fusionar el nom complet i el nom abreujat de la FEB.
    """
    text = re.sub(r"\s+", " ", name).strip()
    if "," in text:
        surname = text.split(",", 1)[0].strip()
    else:
        # Elimina una o més inicials inicials: "A. ", "M. A. ", etc.
        surname = re.sub(
            r"^(?:[A-ZÁÉÍÓÚÜÑÇ]\.\s*)+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    return norm(surname)


def suggested_alias(name: str) -> str:
    """Àlies inicial per a jugadores noves; després el pots editar al JSON."""
    text = re.sub(r"\s+", " ", name).strip()
    if "," in text:
        surname = text.split(",", 1)[0].strip()
    else:
        surname = re.sub(
            r"^(?:[A-ZÁÉÍÓÚÜÑÇ]\.\s*)+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    first = surname.split()[0] if surname else text
    return first.title()


def prefer_display(old: str, new: str) -> str:
    """Prefereix el nom més complet quan la mateixa jugadora surt en dos formats."""
    if not old:
        return new
    if "," in new and "," not in old:
        return new
    if "," in old and "," not in new:
        return old
    return new if len(new) > len(old) else old


def load_module(script_path: Path):
    if not script_path.exists():
        raise FileNotFoundError(
            f"No trobo {script_path}. Posa extract_almeda_players.py "
            "a la mateixa carpeta que feb_pbp_to_excel.py."
        )

    spec = importlib.util.spec_from_file_location("feb_pbp_runtime", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No puc carregar {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["feb_pbp_runtime"] = module
    spec.loader.exec_module(module)
    return module


def load_existing_aliases(path: Path | None) -> OrderedDict[str, str]:
    if not path or not path.exists():
        return OrderedDict()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("aliases_almeda.json ha de ser un objecte JSON.")
    return OrderedDict((str(k), str(v)) for k, v in data.items())


def names_from_body(body_text: str, team_name: str) -> list[str]:
    """
    Fallback: extreu noms directament del play-by-play renderitzat.
    Exclou accions d'equip com 'Equipo'.
    """
    pattern = re.compile(
        rf"\({re.escape(team_name)}\)\s+([^:\n]+):",
        flags=re.IGNORECASE,
    )
    result: list[str] = []
    seen: set[str] = set()

    for match in pattern.finditer(body_text or ""):
        name = re.sub(r"\s+", " ", match.group(1)).strip()
        if norm(name) in {
            "EQUIPO", "EQUIP", "TEAM", "TIEMPO MUERTO",
            "TEMPS MORT", "TIMEOUT"
        }:
            continue
        ident = surname_identity(name)
        if not ident or ident in seen:
            continue
        seen.add(ident)
        result.append(name)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extreu les jugadores d'Almeda dels 26 partits i crea un JSON d'àlies."
    )
    parser.add_argument("--team", default="BASKET ALMEDA")
    parser.add_argument(
        "--scraper",
        default="feb_pbp_to_excel.py",
        help="Ruta al teu scraper principal.",
    )
    parser.add_argument(
        "--aliases-existing",
        default="aliases_almeda.json",
        help="JSON actual: els àlies ja definits es conservaran.",
    )
    parser.add_argument(
        "--output",
        default="aliases_almeda_detectades.json",
        help="JSON de sortida.",
    )
    parser.add_argument(
        "--report",
        default="jugadores_almeda_detectades.txt",
        help="Informe de jugadores i jornades.",
    )
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--browser-executable", default=None)
    args = parser.parse_args()

    scraper_path = Path(args.scraper).resolve()
    feb = load_module(scraper_path)

    existing_path = Path(args.aliases_existing).resolve()
    existing = load_existing_aliases(existing_path)

    # Índex d'àlies ja existents per cognoms.
    existing_by_identity: dict[str, tuple[str, str]] = {}
    for key, alias in existing.items():
        ident = surname_identity(key)
        if ident:
            existing_by_identity.setdefault(ident, (key, alias))

    # identity -> informació
    found: OrderedDict[str, dict[str, Any]] = OrderedDict()
    errors: list[str] = []

    print(f"Equip: {args.team}")
    print(f"Partits a revisar: {len(PARTITS)}")
    print()

    for jornada, url in PARTITS.items():
        print(f"[{jornada:02d}/26] {url}")

        try:
            bundle = feb.fetch_bundle(
                url,
                headful=args.headful,
                browser_executable=args.browser_executable,
            )
            body_text = bundle.get("body_text", "")
            payloads = bundle.get("json_responses", [])

            names: list[str] = []
            roster_ok = False

            # Mètode principal: roster/boxscore de la FEB.
            try:
                teams = feb.extract_teams(payloads, body_text, {})
                target, _opponent = feb.choose_target_team(teams, args.team)
                names = [p.full_name for p in target.players if p.full_name]
                roster_ok = bool(names)
            except Exception as exc:
                print(f"   avís roster: {exc}")

            # Fallback / complement: noms que apareixen al play-by-play.
            body_names = names_from_body(body_text, args.team)
            names.extend(body_names)

            if not names:
                raise RuntimeError("No s'ha detectat cap jugadora d'Almeda.")

            jornada_seen: set[str] = set()
            added = 0

            for name in names:
                ident = surname_identity(name)
                if not ident or ident in jornada_seen:
                    continue
                jornada_seen.add(ident)

                if ident not in found:
                    found[ident] = {
                        "display": name,
                        "jornades": [],
                        "sources": set(),
                    }
                    added += 1
                else:
                    found[ident]["display"] = prefer_display(
                        found[ident]["display"], name
                    )

                if jornada not in found[ident]["jornades"]:
                    found[ident]["jornades"].append(jornada)

                found[ident]["sources"].add(
                    "roster/pbp" if roster_ok else "pbp"
                )

            print(f"   OK: {len(jornada_seen)} jugadores ({added} noves)")

        except Exception as exc:
            msg = f"Jornada {jornada}: {type(exc).__name__}: {exc}"
            errors.append(msg)
            print(f"   ERROR: {msg}")

    if not found:
        print("\nNo s'ha pogut detectar cap jugadora.")
        return 2

    # JSON final:
    # - si la jugadora ja existeix a aliases_almeda.json, conserva CLAU + ÀLIES;
    # - si és nova, usa el millor nom FEB detectat i un àlies suggerit.
    output_aliases: OrderedDict[str, str] = OrderedDict()

    report_lines = [
        f"JUGADORES DETECTADES - {args.team}",
        "=" * 70,
        "",
    ]

    for ident, info in found.items():
        if ident in existing_by_identity:
            out_key, alias = existing_by_identity[ident]
            status = "existent"
        else:
            out_key = info["display"]
            alias = suggested_alias(info["display"])
            status = "NOVA"

        output_aliases[out_key] = alias
        jornades = ", ".join(str(j) for j in info["jornades"])
        report_lines.append(
            f"{alias:<20} | {out_key:<40} | jornades: {jornades} | {status}"
        )

    if errors:
        report_lines += [
            "",
            "ERRORS / PARTITS A REVISAR",
            "-" * 70,
            *errors,
        ]

    output_path = Path(args.output).resolve()
    report_path = Path(args.report).resolve()

    output_path.write_text(
        json.dumps(output_aliases, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print()
    print("=" * 60)
    print(f"Jugadores úniques detectades: {len(output_aliases)}")
    print(f"JSON creat:   {output_path}")
    print(f"Informe creat: {report_path}")

    if errors:
        print(f"Partits amb error: {len(errors)}")
        print("Revisa l'informe; la resta de partits s'han processat igualment.")
        return 1

    print("Tots els partits s'han processat correctament.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
