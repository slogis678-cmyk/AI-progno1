"""Seed demo football matches for first-time users."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta


def _now_iso(offset_hours: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


def _odds_history(start: dict, end: dict, steps: int = 6) -> list:
    """Linear interpolation between two odds snapshots."""
    out = []
    for i in range(steps):
        t = i / (steps - 1)
        out.append({
            "ts": _now_iso(-48 + i * 8),
            "home": round(start["home"] + (end["home"] - start["home"]) * t, 2),
            "draw": round(start["draw"] + (end["draw"] - start["draw"]) * t, 2),
            "away": round(start["away"] + (end["away"] - start["away"]) * t, 2),
        })
    return out


def demo_matches(owner_id: str) -> list[dict]:
    matches = [
        {
            "home_team": "Real Madryt",
            "away_team": "FC Barcelona",
            "league": "La Liga",
            "kickoff": _now_iso(28),
            "odds": {"home": 2.05, "draw": 3.60, "away": 3.40},
            "odds_history": _odds_history(
                {"home": 2.30, "draw": 3.50, "away": 3.10},
                {"home": 2.05, "draw": 3.60, "away": 3.40},
            ),
            "tempo": {"possession_home": 56, "shots_home": 17, "shots_away": 12, "ppda_home": 8.5, "ppda_away": 11.2},
            "form_home": ["W", "W", "D", "W", "W"],
            "form_away": ["W", "L", "W", "D", "W"],
            "h2h": [{"result": "H"}, {"result": "D"}, {"result": "A"}, {"result": "H"}, {"result": "D"}],
        },
        {
            "home_team": "Manchester City",
            "away_team": "Liverpool",
            "league": "Premier League",
            "kickoff": _now_iso(50),
            "odds": {"home": 1.95, "draw": 3.80, "away": 3.70},
            "odds_history": _odds_history(
                {"home": 1.85, "draw": 3.90, "away": 4.20},
                {"home": 1.95, "draw": 3.80, "away": 3.70},
            ),
            "tempo": {"possession_home": 62, "shots_home": 19, "shots_away": 10, "ppda_home": 7.8, "ppda_away": 12.5},
            "form_home": ["W", "W", "W", "D", "W"],
            "form_away": ["D", "W", "L", "W", "W"],
            "h2h": [{"result": "H"}, {"result": "H"}, {"result": "D"}, {"result": "A"}, {"result": "H"}],
        },
        {
            "home_team": "Bayern Monachium",
            "away_team": "Borussia Dortmund",
            "league": "Bundesliga",
            "kickoff": _now_iso(72),
            "odds": {"home": 1.55, "draw": 4.50, "away": 5.20},
            "odds_history": _odds_history(
                {"home": 1.65, "draw": 4.20, "away": 5.00},
                {"home": 1.55, "draw": 4.50, "away": 5.20},
            ),
            "tempo": {"possession_home": 60, "shots_home": 18, "shots_away": 9, "ppda_home": 8.0, "ppda_away": 13.5},
            "form_home": ["W", "W", "W", "W", "D"],
            "form_away": ["L", "W", "D", "W", "L"],
            "h2h": [{"result": "H"}, {"result": "H"}, {"result": "H"}, {"result": "D"}, {"result": "H"}],
        },
        {
            "home_team": "Lech Poznań",
            "away_team": "Legia Warszawa",
            "league": "Ekstraklasa",
            "kickoff": _now_iso(36),
            "odds": {"home": 2.40, "draw": 3.20, "away": 2.95},
            "odds_history": _odds_history(
                {"home": 2.20, "draw": 3.30, "away": 3.20},
                {"home": 2.40, "draw": 3.20, "away": 2.95},
            ),
            "tempo": {"possession_home": 52, "shots_home": 13, "shots_away": 14, "ppda_home": 9.5, "ppda_away": 10.0},
            "form_home": ["W", "D", "W", "L", "W"],
            "form_away": ["W", "W", "W", "D", "W"],
            "h2h": [{"result": "A"}, {"result": "H"}, {"result": "D"}, {"result": "A"}, {"result": "H"}],
        },
        {
            "home_team": "Inter Mediolan",
            "away_team": "AC Milan",
            "league": "Serie A",
            "kickoff": _now_iso(60),
            "odds": {"home": 2.10, "draw": 3.40, "away": 3.50},
            "odds_history": _odds_history(
                {"home": 2.30, "draw": 3.30, "away": 3.20},
                {"home": 2.10, "draw": 3.40, "away": 3.50},
            ),
            "tempo": {"possession_home": 54, "shots_home": 15, "shots_away": 11, "ppda_home": 9.0, "ppda_away": 10.5},
            "form_home": ["W", "W", "D", "W", "W"],
            "form_away": ["D", "W", "L", "D", "W"],
            "h2h": [{"result": "H"}, {"result": "D"}, {"result": "H"}, {"result": "D"}, {"result": "A"}],
        },
        {
            "home_team": "PSG",
            "away_team": "Olympique Marsylia",
            "league": "Ligue 1",
            "kickoff": _now_iso(44),
            "odds": {"home": 1.45, "draw": 4.80, "away": 6.50},
            "odds_history": _odds_history(
                {"home": 1.50, "draw": 4.60, "away": 6.20},
                {"home": 1.45, "draw": 4.80, "away": 6.50},
            ),
            "tempo": {"possession_home": 64, "shots_home": 20, "shots_away": 8, "ppda_home": 7.5, "ppda_away": 14.0},
            "form_home": ["W", "W", "W", "W", "W"],
            "form_away": ["L", "D", "W", "L", "D"],
            "h2h": [{"result": "H"}, {"result": "H"}, {"result": "D"}, {"result": "H"}, {"result": "H"}],
        },
    ]
    out = []
    for m in matches:
        m["id"] = str(uuid.uuid4())
        m["owner_id"] = owner_id
        m["status"] = "upcoming"
        m["created_at"] = _now_iso()
        out.append(m)
    return out
