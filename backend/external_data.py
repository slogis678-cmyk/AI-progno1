"""External football data sources.

Integrates two free-tier APIs:
  - API-Football (RapidAPI) — fixtures, statistics, team form
  - The Odds API — bookmaker 1X2 odds

Both return our normalized internal match shape:
{
  home_team, away_team, league, kickoff (ISO),
  odds: {home, draw, away},
  tempo: {...}, form_home: [...], form_away: [...],
  h2h: [{result}], odds_history: [...]
}
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from external_helpers import (
    calculate_result_letter,
    calculate_h2h_letter,
    build_tempo_data,
    aggregate_bookmaker_odds,
    build_match_document,
)

API_FOOTBALL_HOST = "api-football-v1.p.rapidapi.com"
API_FOOTBALL_BASE = f"https://{API_FOOTBALL_HOST}/v3"
ODDS_API_BASE = "https://api.the-odds-api.com/v4"


def _af_headers() -> dict:
    key = os.environ.get("API_FOOTBALL_KEY", "")
    return {"x-rapidapi-key": key, "x-rapidapi-host": API_FOOTBALL_HOST}


# Major leagues that we expose by default
LEAGUES = [
    {"id": 39, "name": "Premier League", "country": "Anglia"},
    {"id": 140, "name": "La Liga", "country": "Hiszpania"},
    {"id": 78, "name": "Bundesliga", "country": "Niemcy"},
    {"id": 135, "name": "Serie A", "country": "Włochy"},
    {"id": 61, "name": "Ligue 1", "country": "Francja"},
    {"id": 106, "name": "Ekstraklasa", "country": "Polska"},
    {"id": 2, "name": "UEFA Champions League", "country": "Europa"},
    {"id": 3, "name": "UEFA Europa League", "country": "Europa"},
]


def _result_letter_from(team_id: int, home_id: int, away_id: int, hg: int | None, ag: int | None) -> str | None:
    """Wrapper for backward compatibility."""
    return calculate_result_letter(team_id, home_id, away_id, hg, ag)


def _h2h_letter(home_id: int, hg: int | None, ag: int | None) -> str | None:
    """Wrapper for backward compatibility."""
    return calculate_h2h_letter(home_id, hg, ag)


async def _af_get(client: httpx.AsyncClient, path: str, params: dict) -> dict:
    r = await client.get(f"{API_FOOTBALL_BASE}{path}", params=params, headers=_af_headers(), timeout=20)
    r.raise_for_status()
    return r.json()


async def _team_last_form(client: httpx.AsyncClient, team_id: int, season: int, limit: int = 5) -> list[str]:
    js = await _af_get(client, "/fixtures", {"team": team_id, "season": season, "last": limit})
    out: list[str] = []
    for fx in js.get("response", []):
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        hid = teams.get("home", {}).get("id")
        aid = teams.get("away", {}).get("id")
        letter = _result_letter_from(team_id, hid, aid, goals.get("home"), goals.get("away"))
        if letter:
            out.append(letter)
    return out


async def _h2h(client: httpx.AsyncClient, home_id: int, away_id: int, limit: int = 5) -> list[dict]:
    js = await _af_get(client, "/fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": limit})
    out: list[dict] = []
    for fx in js.get("response", []):
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        # for H2H we compute from perspective of "home_id" being home in current match
        hg, ag = goals.get("home"), goals.get("away")
        if hg is None or ag is None:
            continue
        hh_id = teams.get("home", {}).get("id")
        if hh_id == home_id:
            letter = _h2h_letter(home_id, hg, ag)
        else:
            # swapped — translate
            if hg == ag:
                letter = "D"
            else:
                letter = "A" if hg > ag else "H"
        if letter:
            out.append({"result": letter})
    return out


async def _team_stats_tempo(client: httpx.AsyncClient, team_id: int, league_id: int, season: int) -> dict:
    """Approximate tempo metrics from season averages."""
    try:
        js = await _af_get(client, "/teams/statistics", {"team": team_id, "league": league_id, "season": season})
        resp = js.get("response", {}) or {}
        fixt = resp.get("fixtures", {}).get("played", {}).get("total") or 1
        shots_total = (resp.get("goals", {}).get("for", {}).get("total", {}).get("total") or 0) * 5  # rough proxy
        return {
            "possession": 50,  # API-Football v3 free tier does not expose possession reliably
            "shots_per_match": max(8, shots_total / max(1, fixt)),
        }
    except Exception:
        return {"possession": 50, "shots_per_match": 12}


async def fetch_api_football_fixtures(league_id: int, days_ahead: int = 7, season: int | None = None) -> list[dict]:
    """Fetch upcoming fixtures + enrichment for a single league."""
    key = os.environ.get("API_FOOTBALL_KEY", "")
    if not key:
        raise RuntimeError("Brak API_FOOTBALL_KEY w .env")

    season = season or datetime.now(timezone.utc).year
    today = datetime.now(timezone.utc).date()
    end = today.fromordinal(today.toordinal() + days_ahead)

    async with httpx.AsyncClient() as client:
        js = await _af_get(client, "/fixtures", {
            "league": league_id,
            "season": season,
            "from": str(today),
            "to": str(end),
            "status": "NS-TBD-PST",
        })
        fixtures = js.get("response", [])

        results: list[dict] = []
        # limit to first 10 to stay within free quota
        for fx in fixtures[:10]:
            teams = fx.get("teams", {})
            home = teams.get("home", {}) or {}
            away = teams.get("away", {}) or {}
            league = fx.get("league", {}) or {}
            kickoff = fx.get("fixture", {}).get("date")

            # odds (single bookmaker, market 1X2 = bet id 1)
            odds = {"home": 2.5, "draw": 3.3, "away": 2.8}
            try:
                odds_js = await _af_get(client, "/odds", {"fixture": fx["fixture"]["id"], "bet": 1})
                bookmakers = (odds_js.get("response", [{}])[0] or {}).get("bookmakers", [])
                if bookmakers:
                    values = (bookmakers[0].get("bets", [{}])[0] or {}).get("values", [])
                    by_name = {v.get("value"): float(v.get("odd", 0)) for v in values}
                    if by_name.get("Home") and by_name.get("Draw") and by_name.get("Away"):
                        odds = {
                            "home": by_name["Home"],
                            "draw": by_name["Draw"],
                            "away": by_name["Away"],
                        }
            except Exception:
                pass

            # form & h2h (parallel-ish, sequential is fine for free tier rate limits)
            try:
                fh = await _team_last_form(client, home.get("id"), season)
                fa = await _team_last_form(client, away.get("id"), season)
                h2h = await _h2h(client, home.get("id"), away.get("id"))
            except Exception:
                fh, fa, h2h = [], [], []

            try:
                stats_h = await _team_stats_tempo(client, home.get("id"), league_id, season)
                stats_a = await _team_stats_tempo(client, away.get("id"), league_id, season)
            except Exception:
                stats_h = stats_a = {"possession": 50, "shots_per_match": 12}

            results.append({
                "home_team": home.get("name", "?"),
                "away_team": away.get("name", "?"),
                "league": f'{league.get("name", "")} ({league.get("country", "")})'.strip(" ()"),
                "kickoff": kickoff,
                "odds": odds,
                "tempo": {
                    "possession_home": stats_h.get("possession", 50),
                    "shots_home": round(stats_h.get("shots_per_match", 12), 1),
                    "shots_away": round(stats_a.get("shots_per_match", 12), 1),
                    "ppda_home": 10,
                    "ppda_away": 10,
                },
                "form_home": fh,
                "form_away": fa,
                "h2h": h2h,
                "odds_history": [{
                    "ts": datetime.now(timezone.utc).isoformat(),
                    **odds,
                }],
                "external_id": f'apifootball:{fx.get("fixture", {}).get("id")}',
            })
        return results


# --------------------------- The Odds API ---------------------------------

ODDS_SPORTS = [
    {"key": "soccer_epl", "label": "Premier League"},
    {"key": "soccer_spain_la_liga", "label": "La Liga"},
    {"key": "soccer_germany_bundesliga", "label": "Bundesliga"},
    {"key": "soccer_italy_serie_a", "label": "Serie A"},
    {"key": "soccer_france_ligue_one", "label": "Ligue 1"},
    {"key": "soccer_poland_ekstraklasa", "label": "Ekstraklasa"},
    {"key": "soccer_uefa_champs_league", "label": "Champions League"},
    {"key": "soccer_uefa_europa_league", "label": "Europa League"},
]


async def fetch_odds_api_sports() -> list[dict]:
    """Return only currently-active soccer leagues from The Odds API."""
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        return ODDS_SPORTS
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{ODDS_API_BASE}/sports", params={"apiKey": key}, timeout=15)
            r.raise_for_status()
            data = r.json()
            soccer = [
                {"key": s["key"], "label": s["title"]}
                for s in data
                if s.get("group") == "Soccer" and s.get("active") and not s.get("has_outrights")
            ]
            return soccer or ODDS_SPORTS
    except Exception:
        return ODDS_SPORTS


async def _fetch_odds_api_raw(sport_key: str) -> list[dict]:
    """Single API call - returns raw event list from The Odds API."""
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        raise RuntimeError("Brak ODDS_API_KEY w .env")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/odds",
            params={"apiKey": key, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()


def _aggregate_h2h(ev: dict) -> dict | None:
    """Average h2h odds across bookmakers into {home, draw, away}, or None."""
    home = ev.get("home_team")
    away = ev.get("away_team")
    sums = {"home": [], "draw": [], "away": []}
    for bk in ev.get("bookmakers", []):
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            for o in mkt.get("outcomes", []):
                name = o.get("name")
                try:
                    price = float(o.get("price", 0))
                except (TypeError, ValueError):
                    continue
                if name == home:
                    sums["home"].append(price)
                elif name == away:
                    sums["away"].append(price)
                elif name and name.lower() in ("draw", "tie"):
                    sums["draw"].append(price)
    if not (sums["home"] and sums["draw"] and sums["away"]):
        return None

    def _avg(arr):
        return round(sum(arr) / len(arr), 2)
    return {"home": _avg(sums["home"]), "draw": _avg(sums["draw"]), "away": _avg(sums["away"])}


async def fetch_odds_api_events(sport_key: str) -> list[dict]:
    """Return normalized match dicts ready to be persisted."""
    sports = await fetch_odds_api_sports()
    label = next((s["label"] for s in sports if s["key"] == sport_key), sport_key)
    data = await _fetch_odds_api_raw(sport_key)
    out: list[dict] = []
    for ev in data[:15]:
        odds = _aggregate_h2h(ev) or {"home": 2.5, "draw": 3.3, "away": 2.8}
        out.append({
            "home_team": ev.get("home_team"),
            "away_team": ev.get("away_team"),
            "league": label,
            "kickoff": ev.get("commence_time"),
            "odds": odds,
            "tempo": {"possession_home": 50, "shots_home": 12, "shots_away": 12, "ppda_home": 10, "ppda_away": 10},
            "form_home": [],
            "form_away": [],
            "h2h": [],
            "odds_history": [
                {"ts": datetime.now(timezone.utc).isoformat(), **odds},
            ],
            "external_id": f"oddsapi:{ev.get('id')}",
            "sport_key": sport_key,
        })
    return out


async def fetch_odds_api_event_odds(sport_key: str) -> dict[str, dict]:
    """Single API call. Returns {event_id: {home, draw, away}} for the sport."""
    data = await _fetch_odds_api_raw(sport_key)
    out: dict[str, dict] = {}
    for ev in data:
        odds = _aggregate_h2h(ev)
        if odds and ev.get("id"):
            out[ev["id"]] = odds
    return out
