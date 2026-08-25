#!/usr/bin/env python3
"""Converteix el play-by-play d'un partit de baloncestoenvivo.feb.es a Excel.

Dissenyat per al format de j22-pbp.xlsx:
- una fila per finalització ofensiva de l'equip analitzat;
- els punts/RO del rival ocorreguts entre dues finalitzacions s'imputen a la
  següent fila de l'equip analitzat;
- la columna "Tàctica" queda buida;
- RD a favor / RD en contra queden buides;
- el minut es conserva com M:SS.

La web FEB carrega les dades amb JavaScript. El programa usa Playwright,
intercepta les respostes JSON i, si cal, fa fallback al DOM renderitzat.
També desa un fitxer debug JSON per facilitar ajustos si la FEB canvia el web.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional
from urllib.parse import urlparse

try:
    import xlsxwriter
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Falta xlsxwriter. Instal·la dependències amb: pip install -r requirements.txt"
    ) from exc


COLUMNS = [
    "Jornada",
    "Rival",
    "Data",
    "Hora",
    "Loc/Visit",
    "Periode",
    "Minut",
    "jug 1",
    "jug 2",
    "jug 3",
    "jug 4",
    "jug 5",
    "Tàctica",
    "Desenllac",
    "Assist",
    "Finalitzadora",
    "PF",
    "PC",
    "Marcador equip",
    "Marcador rival",
    "Marcador",
    "RO a favor",
    "RD a favor",
    "RO en contra",
    "RD en contra",
    "Punts RO a favor",
    "Punts RO rival",
]

# Aliasos específics observats a l'Excel de mostra. Es poden sobreescriure
# o ampliar amb --aliases un_fitxer.json.
DEFAULT_ALIASES = {
    "BERNAL IBARRIA, NURIA": "Bernal",
    "GARCIA MENENDEZ, MARINA": "Marina",
    "HOMS FATJO, IVET": "Ivet",
    "TIERNO MARTI, LAURA": "Tierno",
    "TAPIA PALACIO, CLARA": "Tapia",
    "JOVE FUSTE, LAIA": "Jové",
    "ROBLES SANABRIA, MARINA": "Robles",
    "CARRETERO SOLER, MARIONA": "Mariona",
    "COJOCARIU, ANDREEA MARIA": "Cojo",
    "PERIS FONS, DANA": "Dana",
    "COLL-VINENT OLLE, MAR": "Mar",
}


@dataclass
class Player:
    player_id: str = ""
    number: str = ""
    full_name: str = ""
    alias: str = ""
    starter: bool = False
    team_key: str = ""


@dataclass
class Team:
    key: str
    name: str
    is_home: Optional[bool] = None
    players: list[Player] = field(default_factory=list)


@dataclass
class Event:
    index: int
    period: int
    clock: str
    seconds_remaining: int
    sequence: Optional[float]
    team_key: str
    team_name: str
    player: str
    assist: str
    kind: str
    made: Optional[bool]
    shot_value: int
    points: int
    description: str
    player_in: str = ""
    player_out: str = ""
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputRow:
    jornada: Any
    rival: str
    date: Optional[datetime]
    time_text: str
    home_away: str
    period: int
    clock: str
    lineup: list[str]
    outcome: str
    assist: str
    finisher: str
    pf: int
    pc: int
    ro_for: Optional[int]
    ro_against: Optional[int]
    points_ro_for: Optional[int]
    points_ro_against: Optional[int]
    note: str = ""


def norm(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def norm_key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", norm(value))


def as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else None


def first_value(obj: Any, aliases: Iterable[str], default: Any = None) -> Any:
    """Cerca una clau sense distingir majúscules, accents ni separadors."""
    if not isinstance(obj, dict):
        return default
    index = {norm_key(k): v for k, v in obj.items()}
    for alias in aliases:
        key = norm_key(alias)
        if key in index and index[key] not in (None, ""):
            return index[key]
    return default


def iter_nodes(obj: Any, path: str = "root") -> Iterator[tuple[str, Any]]:
    yield path, obj
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from iter_nodes(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from iter_nodes(value, f"{path}[{idx}]")


def iter_lists(obj: Any, path: str = "root") -> Iterator[tuple[str, list[Any]]]:
    if isinstance(obj, list):
        yield path, obj
        for idx, value in enumerate(obj):
            yield from iter_lists(value, f"{path}[{idx}]")
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from iter_lists(value, f"{path}.{key}")


def flatten_text(obj: Any, max_depth: int = 3) -> str:
    parts: list[str] = []

    def walk(value: Any, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if norm_key(k) in {
                    "DESCRIPTION", "DESCRIPCION", "TEXT", "ACTION", "ACTIONTYPE",
                    "TYPE", "EVENT", "PLAY", "NAME", "PLAYERNAME", "JUGADOR",
                    "TEAMNAME", "EQUIPO", "RESULT", "SUBTYPE",
                }:
                    walk(v, depth + 1)
        elif isinstance(value, list):
            for item in value[:10]:
                walk(item, depth + 1)
        elif value not in (None, ""):
            parts.append(str(value))

    walk(obj, 0)
    return " | ".join(dict.fromkeys(parts))


def parse_clock(value: Any) -> tuple[str, int]:
    if value is None:
        return "", -1
    text = str(value).strip()
    # ISO duration, p. ex. PT9M34S
    iso = re.search(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", text, re.I)
    if iso:
        minutes = int(iso.group(1) or 0)
        seconds = int(float(iso.group(2) or 0))
        return f"{minutes}:{seconds:02d}", minutes * 60 + seconds
    match = re.search(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", text)
    if match:
        minutes, seconds = int(match.group(1)), int(match.group(2))
        return f"{minutes}:{seconds:02d}", minutes * 60 + seconds
    # Alguns feeds guarden segons restants.
    if isinstance(value, (int, float)) and 0 <= float(value) <= 900:
        total = int(float(value))
        return f"{total // 60}:{total % 60:02d}", total
    return "", -1


def parse_period(value: Any, description: str = "") -> int:
    parsed = as_int(value)
    if parsed is not None and 1 <= parsed <= 20:
        return parsed
    text = norm(description)
    match = re.search(r"(?:PERIODO|PERIODE|QUARTER|CUARTO|Q)\s*(\d+)", text)
    return int(match.group(1)) if match else 0


def value_to_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(first_value(value, ["name", "nombre", "fullName", "displayName", "text"], ""))
    if isinstance(value, list):
        return " ".join(value_to_text(v) for v in value if value_to_text(v))
    return "" if value is None else str(value)


def load_aliases(path: Optional[Path]) -> dict[str, str]:
    aliases = {norm(k): v for k, v in DEFAULT_ALIASES.items()}
    if path:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("El fitxer d'aliasos ha de ser un objecte JSON {nom_complet: alias}.")
        aliases.update({norm(k): str(v) for k, v in data.items()})
    return aliases


def generic_alias(full_name: str) -> str:
    clean = re.sub(r"\s+", " ", full_name).strip()
    if not clean:
        return ""
    if "," in clean:
        surname, given = [part.strip() for part in clean.split(",", 1)]
        # Per defecte usem el primer cognom. Els casos especials s'han de posar
        # al JSON d'aliasos.
        candidate = surname.split()[0]
    else:
        candidate = clean.split()[0]
    return candidate.title()


def player_alias(full_name: str, aliases: dict[str, str]) -> str:
    normalized = norm(full_name)
    if normalized in aliases:
        return aliases[normalized]
    # També permet claus parcials prou llargues.
    matches = [(len(k), v) for k, v in aliases.items() if len(k) >= 5 and k in normalized]
    if matches:
        return max(matches)[1]
    return generic_alias(full_name)


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return norm(value) in {"1", "TRUE", "SI", "YES", "Y", "S", "STARTER", "TITULAR", "*"}


def score_team_list(candidate: list[Any]) -> int:
    if len(candidate) != 2 or not all(isinstance(x, dict) for x in candidate):
        return -1
    score = 0
    for team in candidate:
        keys = {norm_key(k) for k in team}
        if keys & {"PLAYER", "PLAYERS", "JUGADORES", "ROSTER"}:
            score += 8
        if keys & {"NAME", "TEAMNAME", "NOMBRE", "EQUIPO"}:
            score += 3
        if keys & {"ID", "TEAMID", "IDEQUIPO"}:
            score += 1
    return score


def extract_teams(json_payloads: list[dict[str, Any]], body_text: str, aliases: dict[str, str]) -> list[Team]:
    best: Optional[list[Any]] = None
    best_score = -1
    for payload in json_payloads:
        data = payload.get("data")
        for path, candidate in iter_lists(data):
            score = score_team_list(candidate)
            if "BOXSCORE" in norm(path):
                score += 4
            if score > best_score:
                best, best_score = candidate, score

    if not best:
        raise RuntimeError(
            "No he pogut trobar els dos equips al JSON. Consulta el fitxer debug; "
            "pot ser que la FEB hagi canviat l'estructura."
        )

    teams: list[Team] = []
    for idx, raw_team in enumerate(best):
        name = value_to_text(first_value(raw_team, ["name", "teamName", "nombre", "equipo", "club"], ""))
        key = str(first_value(raw_team, ["id", "teamId", "idEquipo", "code", "teamCode"], name or idx))
        side = first_value(raw_team, ["isHome", "home", "local", "side", "homeAway"], None)
        is_home: Optional[bool]
        if side is None:
            is_home = idx == 0
        elif isinstance(side, str) and norm(side) in {"AWAY", "VISITOR", "VISITANTE"}:
            is_home = False
        else:
            is_home = boolish(side) or idx == 0

        raw_players = first_value(raw_team, ["PLAYER", "players", "jugadores", "roster"], [])
        if isinstance(raw_players, dict):
            raw_players = list(raw_players.values())
        players: list[Player] = []
        if isinstance(raw_players, list):
            for raw_player in raw_players:
                if not isinstance(raw_player, dict):
                    continue
                full_name = value_to_text(first_value(
                    raw_player,
                    ["name", "playerName", "fullName", "nombre", "jugador", "displayName"],
                    "",
                ))
                if not full_name:
                    continue
                pid = str(first_value(raw_player, ["id", "playerId", "idJugador"], ""))
                number = str(first_value(raw_player, ["no", "number", "shirtNumber", "dorsal"], ""))
                starter = boolish(first_value(
                    raw_player,
                    ["inn", "starter", "isStarter", "initial", "titular", "startingFive"],
                    False,
                ))
                players.append(Player(
                    player_id=pid,
                    number=number,
                    full_name=full_name,
                    alias=player_alias(full_name, aliases),
                    starter=starter,
                    team_key=key,
                ))
        teams.append(Team(key=key, name=name or f"Equip {idx + 1}", is_home=is_home, players=players))
    return teams


def choose_target_team(teams: list[Team], selector: str) -> tuple[Team, Team]:
    wanted = norm(selector)
    ranked = []
    for team in teams:
        name = norm(team.name)
        score = 100 if wanted == name else 80 if wanted in name or name in wanted else 0
        ranked.append((score, team))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] == 0:
        options = ", ".join(team.name for team in teams)
        raise ValueError(f"No trobo l'equip '{selector}'. Equips detectats: {options}")
    target = ranked[0][1]
    opponent = next(team for team in teams if team is not target)
    return target, opponent


def candidate_event_score(path: str, rows: list[Any]) -> float:
    dict_rows = [row for row in rows if isinstance(row, dict)]
    if len(dict_rows) < 5:
        return -1
    sample = dict_rows[: min(30, len(dict_rows))]
    keys = {norm_key(k) for row in sample for k in row.keys()}
    score = min(len(dict_rows), 300) / 10
    path_n = norm(path)
    if any(word in path_n for word in ["PLAYBYPLAY", "PBP", "ACTION", "EVENT", "DIRECTO", "KEYFACT"]):
        score += 30
    for group in [
        {"CLOCK", "TIME", "MINUTE", "TIMEFORMATTED", "GAMECLOCK"},
        {"PERIOD", "QUARTER", "CUARTO", "PERIODE"},
        {"ACTION", "DESCRIPTION", "TEXT", "EVENTTYPE", "TYPE", "PLAY"},
        {"TEAM", "TEAMID", "TEAMNAME", "EQUIPO"},
        {"PLAYER", "PLAYERID", "PLAYERNAME", "JUGADOR"},
    ]:
        if keys & group:
            score += 8
    text = " ".join(flatten_text(row) for row in sample)
    clock_hits = len(re.findall(r"\b\d{1,2}:\d{2}\b", text))
    score += min(clock_hits, 20)
    action_hits = sum(word in norm(text) for word in [
        "REBOTE", "REBOT", "TIRO", "TIR", "SHOT", "FALTA", "FOUL",
        "PERDIDA", "TURNOVER", "ASISTENCIA", "SUBSTITUTION", "ENTRA", "SALE",
    ])
    score += action_hits * 3
    return score


def extract_event_dicts(json_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[float, str, list[Any]]] = []
    for payload in json_payloads:
        url = payload.get("url", "")
        for path, rows in iter_lists(payload.get("data")):
            score = candidate_event_score(f"{url} {path}", rows)
            if score >= 0:
                candidates.append((score, f"{url} {path}", rows))
    if not candidates:
        return []

    candidates.sort(key=lambda item: item[0], reverse=True)
    top_score = candidates[0][0]
    # De vegades hi ha una llista per període. Combina candidats similars del
    # mateix endpoint, però evita sumar boxscores o còpies clarament pitjors.
    selected = [c for c in candidates if c[0] >= max(20, top_score * 0.72)]
    raw_events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _score, _path, rows in selected:
        for row in rows:
            if not isinstance(row, dict):
                continue
            signature = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
            if signature in seen:
                continue
            seen.add(signature)
            raw_events.append(row)
    return raw_events


def dom_rows_as_events(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in bundle.get("dom_rows", []):
        if not isinstance(row, dict):
            continue
        text = str(row.get("text", "")).strip()
        if not re.search(r"\b\d{1,2}:\d{2}\b", text):
            continue
        cells = row.get("cells", [])
        description = max((str(c.get("text", "")) for c in cells if isinstance(c, dict)), key=len, default=text)
        side = row.get("side", "")
        events.append({
            "clock": text,
            "description": description or text,
            "text": text,
            "side": side,
            "period": row.get("period", 0),
            "__dom": True,
        })
    return events


def player_lookup(teams: list[Team]) -> tuple[dict[str, Player], dict[str, Player]]:
    by_id: dict[str, Player] = {}
    by_name: dict[str, Player] = {}
    for team in teams:
        for player in team.players:
            if player.player_id:
                by_id[str(player.player_id)] = player
            by_name[norm(player.full_name)] = player
            by_name[norm(player.alias)] = player
            surname = norm(player.full_name.split(",", 1)[0])
            if len(surname) >= 4:
                by_name.setdefault(surname, player)
    return by_id, by_name


def find_player_in_text(text: str, players: Iterable[Player]) -> Optional[Player]:
    text_n = norm(text)
    best: tuple[int, Optional[Player]] = (0, None)
    for player in players:
        candidates = [norm(player.full_name), norm(player.alias)]
        if "," in player.full_name:
            candidates.append(norm(player.full_name.split(",", 1)[0]))
        for candidate in candidates:
            if len(candidate) >= 3 and candidate in text_n and len(candidate) > best[0]:
                best = (len(candidate), player)
    return best[1]


def resolve_player(value: Any, description: str, by_id: dict[str, Player], players: list[Player]) -> str:
    if isinstance(value, dict):
        pid = str(first_value(value, ["id", "playerId", "idJugador"], ""))
        if pid and pid in by_id:
            return by_id[pid].alias
        name = value_to_text(value)
        if name:
            found = find_player_in_text(name, players)
            return found.alias if found else generic_alias(name)
    elif value not in (None, ""):
        raw = str(value)
        if raw in by_id:
            return by_id[raw].alias
        found = find_player_in_text(raw, players)
        if found:
            return found.alias
        if not raw.isdigit():
            return generic_alias(raw)
    found = find_player_in_text(description, players)
    return found.alias if found else ""


def resolve_team(
    raw: dict[str, Any],
    description: str,
    teams: list[Team],
    player: str,
) -> tuple[str, str]:
    value = first_value(raw, ["team", "teamId", "idTeam", "idEquipo", "teamName", "equipo", "club"], "")
    value_text = value_to_text(value)
    value_n = norm(value_text)
    for team in teams:
        if value_text and str(team.key) == value_text:
            return team.key, team.name
    # La comparació parcial per nom només és segura amb cadenes prou llargues;
    # IDs curts com "S" no poden usar-se com a substring del nom de l'equip.
    if len(value_n) >= 4:
        for team in teams:
            team_name_n = norm(team.name)
            if team_name_n == value_n or value_n in team_name_n or team_name_n in value_n:
                return team.key, team.name
    side = norm(first_value(raw, ["side", "homeAway"], ""))
    if side in {"HOME", "LOCAL"}:
        team = next((t for t in teams if t.is_home), teams[0])
        return team.key, team.name
    if side in {"AWAY", "VISITOR", "VISITANTE"}:
        team = next((t for t in teams if t.is_home is False), teams[-1])
        return team.key, team.name
    if player:
        for team in teams:
            if any(norm(p.alias) == norm(player) for p in team.players):
                return team.key, team.name
    found = find_player_in_text(description, [p for t in teams for p in t.players])
    if found:
        team = next(t for t in teams if t.key == found.team_key)
        return team.key, team.name
    return "", ""


def classify_action(description: str, raw_type: str, explicit_points: int) -> tuple[str, Optional[bool], int, int]:
    text = norm(f"{raw_type} {description}")
    code = norm_key(raw_type)

    if any(word in text for word in ["SUSTITUC", "SUBSTITUTION", "CAMBIO", "ENTRA", "SALE", "IN FOR", "OUT FOR"]):
        return "substitution", None, 0, 0
    if any(word in text for word in ["REBOTE OFENSIVO", "REBOT OFENSIU", "OFFENSIVE REBOUND"] ) or code in {"RO", "OREB"}:
        return "oreb", None, 0, 0
    if any(word in text for word in ["REBOTE DEFENSIVO", "REBOT DEFENSIU", "DEFENSIVE REBOUND"] ) or code in {"RD", "DREB"}:
        return "dreb", None, 0, 0
    if any(word in text for word in ["PERDIDA", "PERDUDA", "PERD BALON", "PERDIDA DE BALON", "TURNOVER", "PÈRDUA", "PERDUA"] ) or code in {"TO", "BP"}:
        return "turnover", False, 0, 0

    is_made = any(word in text for word in [
        "ANOTADO", "ANOTADA", "CONVERTIDO", "CONVERTIDA", "ENCESTADO", "ENCESTADA",
        "CANASTA", "MADE", "GOOD", "ACIERTO",
    ])
    is_missed = any(word in text for word in [
        "FALLADO", "FALLADA", "ERRADO", "ERRADA", "MISSED", "NO ANOTADO", "NO ANOTADA",
    ])
    if code in {"P1M", "FTM", "FREETHROWMADE"}:
        is_made = True
    elif code in {"P1A", "P1F", "FTMISS", "FREETHROWMISS"}:
        is_missed = True
    elif code in {"P2M", "2PM", "T2C"}:
        is_made = True
    elif code in {"P2A", "P2F", "2PMISS", "T2F"}:
        is_missed = True
    elif code in {"P3M", "3PM", "T3C"}:
        is_made = True
    elif code in {"P3A", "P3F", "3PMISS", "T3F"}:
        is_missed = True

    free_throw = any(word in text for word in ["TIRO LIBRE", "TIR LLIURE", "FREE THROW", "1 POINT"] ) or code.startswith("P1") or "FREETHROW" in code
    three = any(word in text for word in ["TIRO DE 3", "TIR DE 3", "TRIPLE", "3 POINT", "3PT"] ) or code.startswith("P3") or code.startswith("3P")
    two = any(word in text for word in ["TIRO DE 2", "TIR DE 2", "2 PUNT", "2 POINT", "2PT", "BANDEJA", "MATE"] ) or code.startswith("P2") or code.startswith("2P")

    if free_throw:
        made = True if is_made else False if is_missed else explicit_points > 0
        return "free_throw", made, 1, 1 if made else 0
    if three:
        made = True if is_made else False if is_missed else explicit_points == 3
        return "shot", made, 3, 3 if made else 0
    if two:
        made = True if is_made else False if is_missed else explicit_points == 2
        return "shot", made, 2, 2 if made else 0
    if explicit_points in {2, 3}:
        return "shot", True, explicit_points, explicit_points
    if any(word in text for word in ["FALTA", "FOUL"]):
        return "foul", None, 0, 0
    if any(word in text for word in ["ASISTENCIA", "ASSIST"]):
        return "assist", None, 0, 0
    return "other", None, 0, max(0, explicit_points)


def extract_substitution_players(
    raw: dict[str, Any], description: str, by_id: dict[str, Player], all_players: list[Player]
) -> tuple[str, str]:
    pin = resolve_player(first_value(raw, ["playerIn", "inPlayer", "entra", "subIn"], ""), "", by_id, all_players)
    pout = resolve_player(first_value(raw, ["playerOut", "outPlayer", "sale", "subOut"], ""), "", by_id, all_players)
    if pin and pout:
        return pin, pout

    # Patrons típics: "Entra X - Sale Y", "X in for Y".
    desc_n = description
    patterns = [
        r"(?:ENTRA|IN)\s*[:\-]?\s*(.+?)\s*(?:SALE|OUT|POR|FOR)\s*[:\-]?\s*(.+)$",
        r"(.+?)\s+(?:ENTRA POR|IN FOR)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, desc_n, re.I)
        if not match:
            continue
        a = find_player_in_text(match.group(1), all_players)
        b = find_player_in_text(match.group(2), all_players)
        if a and b:
            return a.alias, b.alias

    mentioned: list[Player] = []
    for p in all_players:
        if find_player_in_text(description, [p]) and p not in mentioned:
            mentioned.append(p)
    if len(mentioned) >= 2:
        text_n = norm(description)
        # Intenta assignar segons proximitat a ENTRA/SALE.
        for p in mentioned:
            pos = text_n.find(norm(p.alias))
            if pos < 0:
                pos = text_n.find(norm(p.full_name.split(",", 1)[0]))
            prefix = text_n[max(0, pos - 20):pos]
            if "ENTRA" in prefix or " IN " in f" {prefix} ":
                pin = p.alias
            if "SALE" in prefix or " OUT " in f" {prefix} ":
                pout = p.alias
        if not pin:
            pin = mentioned[0].alias
        if not pout:
            pout = mentioned[1].alias
    return pin, pout


def normalize_events(raw_events: list[dict[str, Any]], teams: list[Team]) -> list[Event]:
    by_id, _by_name = player_lookup(teams)
    all_players = [player for team in teams for player in team.players]
    events: list[Event] = []

    for idx, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            continue
        description = flatten_text(raw) or value_to_text(first_value(raw, ["description", "text", "action", "play"], ""))
        raw_type = value_to_text(first_value(raw, ["actionType", "eventType", "type", "action", "code", "subType"], ""))
        clock_value = first_value(raw, [
            "clock", "gameClock", "time", "timeFormatted", "minute", "min", "reloj", "temps",
        ], description)
        clock, seconds = parse_clock(clock_value)
        period = parse_period(first_value(raw, ["period", "quarter", "cuarto", "periode", "q"], 0), description)
        sequence_raw = first_value(raw, ["sequence", "eventId", "actionNumber", "number", "order", "id"], None)
        try:
            sequence = float(sequence_raw) if sequence_raw not in (None, "") else None
        except (TypeError, ValueError):
            sequence = None

        player_value = first_value(raw, ["player", "playerName", "jugador", "athlete", "person"], "")
        player = resolve_player(player_value, description, by_id, all_players)
        team_key, team_name = resolve_team(raw, description, teams, player)

        assist_value = first_value(raw, ["assist", "assistPlayer", "assistedBy", "asistencia"], "")
        assist = resolve_player(assist_value, "", by_id, all_players)
        if not assist and any(word in norm(description) for word in ["ASISTENCIA", "ASSIST"]):
            # Sovint l'assistent és el segon nom de jugador que apareix.
            matches = []
            for p in all_players:
                if find_player_in_text(description, [p]):
                    matches.append(p.alias)
            assist = next((name for name in matches if norm(name) != norm(player)), "")

        explicit_points = as_int(first_value(raw, ["points", "pts", "scoreValue", "point", "value"], 0)) or 0
        kind, made, shot_value, points = classify_action(description, raw_type, explicit_points)
        home_score = as_int(first_value(raw, ["homeScore", "scoreHome", "localScore", "score1"], None))
        away_score = as_int(first_value(raw, ["awayScore", "scoreAway", "visitorScore", "score2"], None))

        pin = pout = ""
        if kind == "substitution":
            pin, pout = extract_substitution_players(raw, description, by_id, all_players)

        # Filtra files estructurals sense rellotge ni acció útil.
        if not clock and kind in {"other", "assist", "foul"}:
            continue
        events.append(Event(
            index=idx,
            period=period,
            clock=clock,
            seconds_remaining=seconds,
            sequence=sequence,
            team_key=team_key,
            team_name=team_name,
            player=player,
            assist=assist,
            kind=kind,
            made=made,
            shot_value=shot_value,
            points=points,
            description=description,
            player_in=pin,
            player_out=pout,
            home_score=home_score,
            away_score=away_score,
            raw=raw,
        ))

    # Omple períodes absents detectant reinicis del rellotge.
    current_period = 1
    previous_seconds: Optional[int] = None
    for event in events:
        if event.period:
            current_period = event.period
        elif previous_seconds is not None and event.seconds_remaining > previous_seconds + 120:
            current_period += 1
        event.period = current_period
        if event.seconds_remaining >= 0:
            previous_seconds = event.seconds_remaining

    # Ordena cronològicament: període ascendent, rellotge descendent.
    # La seqüència sol ser ascendent; l'índex conserva l'ordre dins del mateix segon.
    events.sort(key=lambda e: (
        e.period if e.period else 99,
        -(e.seconds_remaining if e.seconds_remaining >= 0 else -1),
        e.sequence if e.sequence is not None else e.index,
        e.index,
    ))

    # Deduplicació després de normalitzar.
    unique: list[Event] = []
    seen: set[tuple[Any, ...]] = set()
    for event in events:
        sig = (
            event.period, event.clock, event.team_key, norm(event.player), event.kind,
            event.made, event.shot_value, norm(event.description), event.player_in, event.player_out,
        )
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(event)

    infer_scoring_from_scoreboard(unique, teams)
    return unique


def infer_scoring_from_scoreboard(events: list[Event], teams: list[Team]) -> None:
    home = next((team for team in teams if team.is_home), teams[0])
    away = next((team for team in teams if team.is_home is False), teams[-1])
    prev_home = prev_away = 0
    for event in events:
        if event.home_score is None or event.away_score is None:
            continue
        delta_home = max(0, event.home_score - prev_home)
        delta_away = max(0, event.away_score - prev_away)
        prev_home, prev_away = event.home_score, event.away_score
        delta = delta_home or delta_away
        if delta and not event.team_key:
            team = home if delta_home else away
            event.team_key, event.team_name = team.key, team.name
        if delta and event.points == 0 and event.kind in {"shot", "free_throw", "other"}:
            event.points = delta
            if event.kind == "other" and delta in {1, 2, 3}:
                event.kind = "free_throw" if delta == 1 else "shot"
                event.shot_value = delta
                event.made = True


def initial_lineup(team: Team, events: list[Event]) -> list[str]:
    starters = [p.alias for p in team.players if p.starter]
    if len(starters) >= 5:
        return starters[:5]
    # Fallback: primers cinc jugadors diferents de l'equip que apareixen en accions.
    inferred = starters[:]
    for event in events:
        if event.team_key == team.key and event.player and event.player not in inferred:
            inferred.append(event.player)
        if len(inferred) == 5:
            break
    return inferred


def lineup_sorted(lineup: list[str], roster_order: dict[str, int]) -> list[str]:
    # Manté una ordre estable semblant a la llista de la plantilla.
    return sorted(dict.fromkeys(lineup), key=lambda name: roster_order.get(norm(name), 999))[:5]


def outcome_for_event(event: Event) -> str:
    if event.kind == "turnover":
        return "pèrdua"
    if event.kind == "shot":
        suffix = "c" if event.made else "f"
        return f"t{event.shot_value}{suffix}"
    if event.kind == "free_throw":
        return "falta (tll)"
    return ""


def same_free_throw_group(a: Event, b: Event) -> bool:
    return (
        a.kind == b.kind == "free_throw"
        and a.period == b.period
        and a.clock == b.clock
        and a.team_key == b.team_key
        and (not a.player or not b.player or norm(a.player) == norm(b.player))
    )


def build_rows(
    events: list[Event],
    target: Team,
    opponent: Team,
    jornada: Any,
    game_date: Optional[datetime],
    time_text: str,
) -> tuple[list[OutputRow], list[str]]:
    warnings: list[str] = []
    lineup = initial_lineup(target, events)
    if len(lineup) < 5:
        warnings.append(
            f"Només s'han pogut inferir {len(lineup)} jugadores inicials. "
            "Revisa titulars/substitucions al debug."
        )
    roster_order = {norm(p.alias): idx for idx, p in enumerate(target.players)}
    lineup = lineup_sorted(lineup, roster_order)

    target_oreb = 0
    opponent_oreb = 0
    opponent_points = 0
    opponent_points_after_oreb = 0
    rows: list[OutputRow] = []

    i = 0
    while i < len(events):
        event = events[i]

        if event.kind == "substitution" and event.team_key == target.key:
            if event.player_out and event.player_out in lineup:
                lineup.remove(event.player_out)
            if event.player_in and event.player_in not in lineup:
                lineup.append(event.player_in)
            lineup = lineup_sorted(lineup, roster_order)
            i += 1
            continue

        if event.kind == "oreb":
            if event.team_key == target.key:
                target_oreb += 1
            elif event.team_key == opponent.key:
                opponent_oreb += 1
            i += 1
            continue

        if event.team_key == opponent.key and event.points > 0:
            opponent_points += event.points
            if opponent_oreb > 0:
                opponent_points_after_oreb += event.points
            i += 1
            continue

        # Agrupa tirs lliures consecutius com una única finalització.
        if event.team_key == target.key and event.kind == "free_throw":
            group = [event]
            j = i + 1
            while j < len(events) and same_free_throw_group(event, events[j]):
                group.append(events[j])
                j += 1
            made = sum(1 for ft in group if ft.made or ft.points > 0)
            player = next((ft.player for ft in group if ft.player), event.player)
            assist = next((ft.assist for ft in group if ft.assist), "")
            row = OutputRow(
                jornada=jornada,
                rival=opponent.name,
                date=game_date,
                time_text=time_text,
                home_away="Local" if target.is_home else "Visitant",
                period=event.period,
                clock=event.clock,
                lineup=lineup_sorted(lineup, roster_order),
                outcome="falta (tll)",
                assist=assist.lower() if assist else "",
                finisher=player.lower() if player else "-",
                pf=made,
                pc=opponent_points,
                ro_for=target_oreb or None,
                ro_against=opponent_oreb or None,
                points_ro_for=made if target_oreb and made else None,
                points_ro_against=opponent_points_after_oreb or None,
            )
            rows.append(row)
            target_oreb = opponent_oreb = opponent_points = opponent_points_after_oreb = 0
            i = j
            continue

        if event.team_key == target.key and event.kind in {"shot", "turnover"}:
            pf = event.points if event.kind == "shot" and event.made else 0
            row = OutputRow(
                jornada=jornada,
                rival=opponent.name,
                date=game_date,
                time_text=time_text,
                home_away="Local" if target.is_home else "Visitant",
                period=event.period,
                clock=event.clock,
                lineup=lineup_sorted(lineup, roster_order),
                outcome=outcome_for_event(event),
                assist=event.assist.lower() if event.assist else "",
                finisher=event.player.lower() if event.player else "-",
                pf=pf,
                pc=opponent_points,
                ro_for=target_oreb or None,
                ro_against=opponent_oreb or None,
                points_ro_for=pf if target_oreb and pf else None,
                points_ro_against=opponent_points_after_oreb or None,
            )
            rows.append(row)
            target_oreb = opponent_oreb = opponent_points = opponent_points_after_oreb = 0
        i += 1

    if rows and (opponent_points or opponent_oreb or opponent_points_after_oreb):
        # Per no perdre el tram final del rival, l'imputem a l'última fila i ho
        # indiquem al log. Això garanteix que PC quadri amb el marcador final.
        rows[-1].pc += opponent_points
        rows[-1].ro_against = (rows[-1].ro_against or 0) + opponent_oreb or None
        rows[-1].points_ro_against = (rows[-1].points_ro_against or 0) + opponent_points_after_oreb or None
        rows[-1].note = "Tram final del rival imputat a l'última fila"
        warnings.append("S'ha imputat el tram final del rival a l'última fila.")

    if not rows:
        raise RuntimeError(
            "No s'ha generat cap finalització de l'equip. Revisa feb_debug_*.json; "
            "probablement cal adaptar els noms de camps o les descripcions d'acció."
        )
    return rows, warnings


def parse_game_metadata(body_text: str) -> tuple[Optional[datetime], str]:
    match = re.search(
        r"(?:Fecha|Data)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s*[-–]\s*(\d{1,2}:\d{2})",
        body_text,
        re.I,
    )
    if not match:
        return None, ""
    date_text = match.group(1).replace("-", "/")
    date_value = datetime.strptime(date_text, "%d/%m/%Y")
    return date_value, match.group(2)


def validate_totals(rows: list[OutputRow], target: Team, opponent: Team, body_text: str) -> list[str]:
    warnings: list[str] = []
    pf = sum(row.pf for row in rows)
    pc = sum(row.pc for row in rows)
    # Busca el marcador final a prop dels noms dels equips; si falla, no bloqueja.
    scores = [int(x) for x in re.findall(r"(?<!\d)(\d{1,3})(?!\d)", body_text[:4000])]
    if pf == 0:
        warnings.append("La suma de PF és 0; revisa la classificació de tirs.")
    if pc == 0:
        warnings.append("La suma de PC és 0; revisa la identificació de l'equip rival.")
    warnings.append(f"Totals generats: {target.name} {pf} - {pc} {opponent.name}.")
    return warnings


def write_excel(rows: list[OutputRow], output_path: Path, source_url: str, warnings: list[str]) -> None:
    workbook = xlsxwriter.Workbook(output_path)
    sheet = workbook.add_worksheet("Hoja1")
    log_sheet = workbook.add_worksheet("Log")

    header_fmt = workbook.add_format({
        "bold": True,
        "font_color": "#FFFFFF",
        "bg_color": "#1F4E78",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })
    text_fmt = workbook.add_format({"border": 1, "valign": "vcenter"})
    center_fmt = workbook.add_format({"border": 1, "align": "center", "valign": "vcenter"})
    int_fmt = workbook.add_format({"border": 1, "align": "center", "num_format": "0"})
    date_fmt = workbook.add_format({"border": 1, "align": "center", "num_format": "dd/mm/yyyy"})
    time_fmt = workbook.add_format({"border": 1, "align": "center", "num_format": "hh:mm"})
    blank_tactic_fmt = workbook.add_format({"border": 1, "bg_color": "#FFF2CC"})
    score_fmt = workbook.add_format({"border": 1, "align": "center", "bold": True})
    warning_fmt = workbook.add_format({"font_color": "#9C0006", "bg_color": "#FFC7CE", "text_wrap": True})
    url_fmt = workbook.add_format({"font_color": "blue", "underline": True})

    sheet.write_row(0, 0, COLUMNS, header_fmt)
    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, max(1, len(rows)), len(COLUMNS) - 1)
    sheet.set_row(0, 34)

    widths = [9, 20, 11, 8, 10, 8, 8, 12, 12, 12, 12, 12, 15, 15, 14, 16, 6, 6, 14, 14, 11, 11, 11, 12, 12, 16, 15]
    for col, width in enumerate(widths):
        sheet.set_column(col, col, width)

    running_pf = 0
    running_pc = 0
    for row_idx, row in enumerate(rows, start=1):
        lineup = (row.lineup + [""] * 5)[:5]
        running_pf += row.pf
        running_pc += row.pc
        values = [
            row.jornada,
            row.rival,
            row.date,
            row.time_text,
            row.home_away,
            row.period,
            row.clock,
            *lineup,
            "",  # Tàctica
            row.outcome,
            row.assist,
            row.finisher,
            row.pf,
            row.pc,
            None,  # fórmula
            None,  # fórmula
            None,  # fórmula
            row.ro_for,
            None,  # RD favor buit
            row.ro_against,
            None,  # RD contra buit
            row.points_ro_for,
            row.points_ro_against,
        ]
        for col_idx, value in enumerate(values):
            fmt = center_fmt
            if col_idx in {1, 7, 8, 9, 10, 11, 13, 14, 15}:
                fmt = text_fmt
            if col_idx == 2:
                if isinstance(value, datetime):
                    sheet.write_datetime(row_idx, col_idx, value, date_fmt)
                else:
                    sheet.write_blank(row_idx, col_idx, None, date_fmt)
                continue
            if col_idx == 3:
                if value and re.fullmatch(r"\d{1,2}:\d{2}", str(value)):
                    hour, minute = map(int, str(value).split(":"))
                    excel_time = (hour * 3600 + minute * 60) / 86400
                    sheet.write_number(row_idx, col_idx, excel_time, time_fmt)
                else:
                    sheet.write(row_idx, col_idx, value, center_fmt)
                continue
            if col_idx == 12:
                sheet.write_blank(row_idx, col_idx, None, blank_tactic_fmt)
                continue
            if col_idx in {16, 17, 21, 22, 23, 24, 25, 26}:
                if value is None:
                    sheet.write_blank(row_idx, col_idx, None, int_fmt)
                else:
                    sheet.write_number(row_idx, col_idx, value, int_fmt)
                continue
            if value is None:
                sheet.write_blank(row_idx, col_idx, None, fmt)
            else:
                sheet.write(row_idx, col_idx, value, fmt)

        excel_row = row_idx + 1
        if row_idx == 1:
            sheet.write_formula(row_idx, 18, f"=Q{excel_row}", int_fmt, running_pf)
            sheet.write_formula(row_idx, 19, f"=R{excel_row}", int_fmt, running_pc)
        else:
            sheet.write_formula(row_idx, 18, f"=S{excel_row-1}+Q{excel_row}", int_fmt, running_pf)
            sheet.write_formula(row_idx, 19, f"=T{excel_row-1}+R{excel_row}", int_fmt, running_pc)
        sheet.write_formula(
            row_idx, 20, f'=S{excel_row}&"-"&T{excel_row}', score_fmt,
            f"{running_pf}-{running_pc}",
        )

    # Full de control, útil quan el web canviï o hi hagi dades dubtoses.
    log_sheet.set_column("A:A", 22)
    log_sheet.set_column("B:B", 95)
    log_sheet.write("A1", "Font", header_fmt)
    log_sheet.write_url("B1", source_url, url_fmt, source_url)
    log_sheet.write("A3", "Avisos", header_fmt)
    for idx, warning in enumerate(warnings, start=3):
        log_sheet.write(idx, 1, warning, warning_fmt if "revisa" in norm(warning).lower() else text_fmt)
    log_sheet.write(len(warnings) + 5, 0, "Files", header_fmt)
    log_sheet.write_number(len(warnings) + 5, 1, len(rows), int_fmt)
    log_sheet.write(len(warnings) + 6, 0, "PF", header_fmt)
    log_sheet.write_formula(len(warnings) + 6, 1, f"=SUM(Hoja1!Q2:Q{len(rows)+1})", int_fmt)
    log_sheet.write(len(warnings) + 7, 0, "PC", header_fmt)
    log_sheet.write_formula(len(warnings) + 7, 1, f"=SUM(Hoja1!R2:R{len(rows)+1})", int_fmt)

    workbook.close()


def extract_dom_rows(page: Any) -> list[dict[str, Any]]:
    script = r"""
    () => {
      const selectors = [
        '#keyfacts-playbyplay-content-scroll tr',
        '[id*="playbyplay" i] tr',
        '[class*="playbyplay" i] tr',
        '[id*="directo" i] tr',
        '[class*="directo" i] tr',
        'table tr'
      ];
      const rows = [];
      const seen = new Set();
      for (const selector of selectors) {
        for (const tr of document.querySelectorAll(selector)) {
          const text = (tr.innerText || '').replace(/\s+/g, ' ').trim();
          if (!text || seen.has(text + '|' + selector)) continue;
          seen.add(text + '|' + selector);
          const cells = [...tr.querySelectorAll('th,td')].map((cell, i) => ({
            index: i,
            text: (cell.innerText || '').replace(/\s+/g, ' ').trim(),
            className: cell.className || ''
          }));
          let side = '';
          if (cells.length >= 3) {
            const mid = Math.floor(cells.length / 2);
            const left = cells.slice(0, mid).map(c => c.text).join(' ').trim();
            const right = cells.slice(mid + 1).map(c => c.text).join(' ').trim();
            if (left && !right) side = 'home';
            else if (right && !left) side = 'away';
          }
          rows.push({selector, text, cells, side, html: tr.outerHTML.slice(0, 5000)});
        }
      }
      return rows;
    }
    """
    return page.evaluate(script)


def fetch_bundle(url: str, headful: bool, browser_executable: Optional[str]) -> dict[str, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Falta Playwright. Instal·la dependències i el navegador:\n"
            "  pip install -r requirements.txt\n"
            "  playwright install chromium"
        ) from exc

    payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    with sync_playwright() as p:
        launch_kwargs: dict[str, Any] = {"headless": not headful}
        if browser_executable:
            launch_kwargs["executable_path"] = browser_executable
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(locale="ca-ES")
        page = context.new_page()

        def on_response(response: Any) -> None:
            try:
                content_type = (response.headers.get("content-type") or "").lower()
                url_l = response.url.lower()
                interesting = (
                    "json" in content_type
                    or response.request.resource_type in {"xhr", "fetch"}
                    or any(token in url_l for token in ["livestats", "boxscore", "playbyplay", "keyfacts", "/api/"])
                )
                if not interesting:
                    return
                text = response.text()
                stripped = text.lstrip()
                if not stripped.startswith(("{", "[")):
                    return
                data = json.loads(text)
                payloads.append({"url": response.url, "status": response.status, "data": data})
            except Exception as exc:  # la navegació no ha de fallar per una resposta concreta
                errors.append(f"{getattr(response, 'url', '?')}: {type(exc).__name__}: {exc}")

        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # Cookies: prova botons habituals sense dependre d'un text concret.
        for label in ["Aceptar", "Acceptar", "Accept", "Continuar"]:
            try:
                locator = page.get_by_role("button", name=re.compile(label, re.I))
                if locator.count():
                    locator.first.click(timeout=1500)
                    break
            except Exception:
                pass

        # Activa la pestanya Directo si és clicable.
        clicked = False
        for locator in [
            page.get_by_text("Directo", exact=True),
            page.get_by_text("Play by play", exact=False),
            page.locator("a,button,[role=tab]").filter(has_text=re.compile(r"Directo|Play.?by.?play", re.I)),
        ]:
            try:
                if locator.count() and locator.first.is_visible():
                    locator.first.click(timeout=3000)
                    clicked = True
                    break
            except Exception:
                pass

        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(3500 if clicked else 2500)
        body_text = page.locator("body").inner_text(timeout=10_000)
        dom_rows = extract_dom_rows(page)
        final_url = page.url
        browser.close()

    return {
        "requested_url": url,
        "final_url": final_url,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "body_text": body_text,
        "json_responses": payloads,
        "dom_rows": dom_rows,
        "capture_errors": errors,
    }


def game_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    match = re.search(r"(\d+)$", path)
    return match.group(1) if match else "partit"


def save_normalized_debug(
    debug_path: Path,
    bundle: dict[str, Any],
    teams: list[Team],
    events: list[Event],
    rows: list[OutputRow],
    warnings: list[str],
) -> None:
    debug = {
        "capture": bundle,
        "parsed": {
            "teams": [asdict(team) for team in teams],
            "events": [asdict(event) for event in events],
            "rows": [asdict(row) for row in rows],
            "warnings": warnings,
        },
    }
    debug_path.write_text(json.dumps(debug, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    aliases = load_aliases(args.aliases)
    if args.from_debug:
        loaded = json.loads(args.from_debug.read_text(encoding="utf-8"))
        bundle = loaded.get("capture", loaded)
        source_url = bundle.get("requested_url", args.url or "")
    else:
        if not args.url:
            raise ValueError("Cal indicar URL o bé --from-debug.")
        source_url = args.url
        bundle = fetch_bundle(args.url, args.headful, args.browser_executable)

    payloads = bundle.get("json_responses", [])
    body_text = bundle.get("body_text", "")
    teams = extract_teams(payloads, body_text, aliases)
    target, opponent = choose_target_team(teams, args.team)

    raw_events = extract_event_dicts(payloads)
    if not raw_events:
        raw_events = dom_rows_as_events(bundle)
    events = normalize_events(raw_events, teams)

    game_date, game_time = parse_game_metadata(body_text)
    if args.date:
        game_date = datetime.strptime(args.date, "%d/%m/%Y")
    if args.time:
        game_time = args.time

    rows, warnings = build_rows(
        events=events,
        target=target,
        opponent=opponent,
        jornada=args.jornada if args.jornada is not None else "",
        game_date=game_date,
        time_text=game_time,
    )
    warnings.extend(validate_totals(rows, target, opponent, body_text))
    warnings.extend(bundle.get("capture_errors", []))

    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    write_excel(rows, output, source_url, warnings)

    debug_path = args.debug or output.with_name(f"feb_debug_{game_id_from_url(source_url)}.json")
    save_normalized_debug(debug_path, bundle, teams, events, rows, warnings)

    print(f"Excel creat: {output}")
    print(f"Debug creat: {debug_path}")
    print(f"Equip: {target.name} | Rival: {opponent.name}")
    print(f"Files: {len(rows)} | PF: {sum(r.pf for r in rows)} | PC: {sum(r.pc for r in rows)}")
    for warning in warnings:
        print(f"AVÍS: {warning}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extreu el play-by-play FEB i crea un Excel amb el format d'Almeda.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", nargs="?", help="URL del partit FEB")
    parser.add_argument("--team", default="BASKET ALMEDA", help="Equip que s'analitza")
    parser.add_argument("--jornada", type=int, help="Número de jornada")
    parser.add_argument("--output", type=Path, default=Path("pbp_almeda.xlsx"), help="Excel de sortida")
    parser.add_argument("--aliases", type=Path, help="JSON opcional {nom complet: alias}")
    parser.add_argument("--debug", type=Path, help="Ruta del JSON de diagnòstic")
    parser.add_argument("--from-debug", type=Path, help="Reprocessa un JSON debug sense obrir el web")
    parser.add_argument("--date", help="Força la data, format DD/MM/AAAA")
    parser.add_argument("--time", help="Força l'hora, format HH:MM")
    parser.add_argument("--headful", action="store_true", help="Mostra el navegador durant la captura")
    parser.add_argument("--browser-executable", help="Ruta opcional a Chrome/Chromium")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except KeyboardInterrupt:
        print("Interromput.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("Executa amb --headful i revisa feb_debug_*.json si el web ha canviat.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
