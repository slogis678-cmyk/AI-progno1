"""Helper functions for external API data processing - extracted for better maintainability."""
from typing import Optional


def calculate_result_letter(team_id: int, home_id: int, away_id: int, 
                           home_goals: Optional[int], away_goals: Optional[int]) -> Optional[str]:
    """Return W/D/L result letter from perspective of team_id."""
    if home_goals is None or away_goals is None:
        return None
    
    if home_goals == away_goals:
        return "D"
    
    if (team_id == home_id and home_goals > away_goals) or \
       (team_id == away_id and away_goals > home_goals):
        return "W"
    
    return "L"


def calculate_h2h_letter(home_id: int, home_goals: Optional[int], 
                        away_goals: Optional[int]) -> Optional[str]:
    """Return H/D/A letter from perspective of home team in H2H."""
    if home_goals is None or away_goals is None:
        return None
    
    if home_goals == away_goals:
        return "D"
    
    return "H" if home_goals > away_goals else "A"


def build_tempo_data(possession: float = 50, shots_per_match: float = 12) -> dict:
    """Build tempo data structure with defaults."""
    return {
        "possession": possession,
        "shots_per_match": shots_per_match,
    }


def aggregate_bookmaker_odds(bookmakers: list) -> dict:
    """Aggregate odds from multiple bookmakers into average h2h odds."""
    sums = {"home": [], "draw": [], "away": []}
    
    for bk in bookmakers:
        for market in bk.get("markets", []):
            if market.get("key") != "h2h":
                continue
            
            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                try:
                    price = float(outcome.get("price", 0))
                except (TypeError, ValueError):
                    continue
                
                # Map outcome names to our keys
                if "home" in name.lower() or name == bookmakers[0].get("home_team"):
                    sums["home"].append(price)
                elif "away" in name.lower() or name == bookmakers[0].get("away_team"):
                    sums["away"].append(price)
                elif name and name.lower() in ("draw", "tie"):
                    sums["draw"].append(price)
    
    # Return None if we don't have complete odds
    if not (sums["home"] and sums["draw"] and sums["away"]):
        return None
    
    def average(arr):
        return round(sum(arr) / len(arr), 2)
    
    return {
        "home": average(sums["home"]),
        "draw": average(sums["draw"]),
        "away": average(sums["away"]),
    }


def build_match_document(home_team: str, away_team: str, league: str, 
                        kickoff: str, odds: dict, **kwargs) -> dict:
    """Build normalized match document structure."""
    return {
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "kickoff": kickoff,
        "odds": odds,
        "tempo": kwargs.get("tempo", {
            "possession_home": 50,
            "shots_home": 12,
            "shots_away": 12,
            "ppda_home": 10,
            "ppda_away": 10,
        }),
        "form_home": kwargs.get("form_home", []),
        "form_away": kwargs.get("form_away", []),
        "h2h": kwargs.get("h2h", []),
        "odds_history": kwargs.get("odds_history", []),
        "external_id": kwargs.get("external_id"),
        "sport_key": kwargs.get("sport_key"),
    }
