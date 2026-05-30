"""Feature engineering for match predictions.

Computes advanced features from existing data sources:
- H2H statistics (wins, draws, avg goals, BTTS rate, over 2.5 rate)
- Odds movement (open vs current)
- Form-based features (last 5 results)

These features feed into the LLM prompt and compute_edge() pillars.
Alternative to annabet.com scraping (which requires JS rendering).
"""
from __future__ import annotations

from typing import Any


# ============================== H2H Features ==============================

def parse_score_string(score: str) -> tuple[int, int] | None:
    """Parse '2-1' or '2:1' format. Returns (home, away) or None."""
    if not score:
        return None
    score = score.strip()
    for sep in ("-", ":", "–"):
        if sep in score:
            try:
                parts = score.split(sep)
                return int(parts[0].strip()), int(parts[1].strip())
            except (ValueError, IndexError):
                continue
    return None


def _count_h2h_results(h2h: list) -> dict:
    """Count W/D/L from H2H results list."""
    home_wins = sum(1 for m in h2h if m.get("result") == "H")
    draws = sum(1 for m in h2h if m.get("result") == "D")
    away_wins = sum(1 for m in h2h if m.get("result") == "A")
    return {"home_wins": home_wins, "draws": draws, "away_wins": away_wins}


def _aggregate_h2h_scores(h2h: list) -> dict:
    """Aggregate score-based stats: avg goals, BTTS rate, over 2.5 rate."""
    btts_count = 0
    over_2_5_count = 0
    total_goals = 0
    score_count = 0
    
    for m in h2h:
        parsed = parse_score_string(m.get("score", ""))
        if not parsed:
            continue
        h, a = parsed
        total_goals += h + a
        score_count += 1
        if h >= 1 and a >= 1:
            btts_count += 1
        if (h + a) > 2.5:
            over_2_5_count += 1
    
    if score_count == 0:
        return {
            "avg_goals": None,
            "btts_rate": None,
            "over_2_5_rate": None,
            "score_count": 0,
        }
    
    return {
        "avg_goals": total_goals / score_count,
        "btts_rate": btts_count / score_count,
        "over_2_5_rate": over_2_5_count / score_count,
        "score_count": score_count,
    }


def compute_h2h_features(h2h: list) -> dict:
    """Compute aggregate H2H features.
    
    Input: list of {result: 'H'/'D'/'A', score?: '2-1', ...}
    Output: h2h_home_wins, h2h_draws, h2h_away_wins, avg_goals, btts_rate, over_2_5_rate
    """
    if not h2h:
        return _empty_h2h_features()
    
    total = len(h2h)
    counts = _count_h2h_results(h2h)
    scores = _aggregate_h2h_scores(h2h)
    
    return {
        "h2h_matches": total,
        "h2h_home_wins": counts["home_wins"],
        "h2h_draws": counts["draws"],
        "h2h_away_wins": counts["away_wins"],
        "h2h_home_win_rate": round(counts["home_wins"] / total, 3),
        "h2h_draw_rate": round(counts["draws"] / total, 3),
        "h2h_away_win_rate": round(counts["away_wins"] / total, 3),
        "h2h_avg_goals": round(scores["avg_goals"], 2) if scores["avg_goals"] is not None else None,
        "h2h_btts_rate": round(scores["btts_rate"], 3) if scores["btts_rate"] is not None else None,
        "h2h_over_2_5_rate": round(scores["over_2_5_rate"], 3) if scores["over_2_5_rate"] is not None else None,
        "h2h_scored_samples": scores["score_count"],
    }


def _empty_h2h_features() -> dict:
    return {
        "h2h_matches": 0,
        "h2h_home_wins": 0,
        "h2h_draws": 0,
        "h2h_away_wins": 0,
        "h2h_home_win_rate": 0,
        "h2h_draw_rate": 0,
        "h2h_away_win_rate": 0,
        "h2h_avg_goals": None,
        "h2h_btts_rate": None,
        "h2h_over_2_5_rate": None,
        "h2h_scored_samples": 0,
    }


# ============================== Odds Movement ==============================

def compute_odds_movement(odds_history: list) -> dict:
    """Compute odds movement features from history.
    
    Input: list of {ts, home, draw, away}
    Output: open/current odds, movement %, market shift signal
    """
    if not odds_history or len(odds_history) < 1:
        return _empty_odds_movement()
    
    first = odds_history[0]
    last = odds_history[-1]
    
    def safe_float(v, default=2.5):
        try:
            return float(v) if v else default
        except (ValueError, TypeError):
            return default
    
    open_home = safe_float(first.get("home"))
    open_draw = safe_float(first.get("draw"))
    open_away = safe_float(first.get("away"))
    
    curr_home = safe_float(last.get("home"))
    curr_draw = safe_float(last.get("draw"))
    curr_away = safe_float(last.get("away"))
    
    def pct_change(old: float, new: float) -> float:
        if old == 0:
            return 0
        return round((new - old) / old * 100, 2)
    
    home_move = pct_change(open_home, curr_home)
    draw_move = pct_change(open_draw, curr_draw)
    away_move = pct_change(open_away, curr_away)
    
    # Identify market favorite based on movement (default if no clear signal)
    signal = "stable"
    if home_move < -3 and away_move > 0:
        signal = "money_to_home"
    elif away_move < -3 and home_move > 0:
        signal = "money_to_away"
    elif draw_move < -3:
        signal = "money_to_draw"
    
    return {
        "odds_open": {"home": open_home, "draw": open_draw, "away": open_away},
        "odds_current": {"home": curr_home, "draw": curr_draw, "away": curr_away},
        "odds_movement_pct": {
            "home": home_move,
            "draw": draw_move,
            "away": away_move,
        },
        "market_signal": signal,
        "samples_count": len(odds_history),
    }


def _empty_odds_movement() -> dict:
    return {
        "odds_open": None,
        "odds_current": None,
        "odds_movement_pct": None,
        "market_signal": "no_data",
        "samples_count": 0,
    }


# ============================== Form Features ==============================

def compute_form_features(form: list, label: str = "home") -> dict:
    """Compute form features from last 5 results.
    
    Input: ['W', 'L', 'D', 'W', 'W']
    Output: points, wins, losses, draws, form_trend
    """
    if not form:
        return {
            f"{label}_form_5": "",
            f"{label}_form_wins": 0,
            f"{label}_form_draws": 0,
            f"{label}_form_losses": 0,
            f"{label}_form_points": 0,
            f"{label}_form_trend": "no_data",
        }
    
    last5 = form[:5]
    wins = sum(1 for r in last5 if r == "W")
    draws = sum(1 for r in last5 if r == "D")
    losses = sum(1 for r in last5 if r == "L")
    points = wins * 3 + draws
    
    # Trend: compare first half vs second half of last 5
    if len(last5) >= 4:
        recent_points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in last5[:2])
        older_points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in last5[2:])
        if recent_points > older_points:
            trend = "improving"
        elif recent_points < older_points:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    return {
        f"{label}_form_5": "".join(last5),
        f"{label}_form_wins": wins,
        f"{label}_form_draws": draws,
        f"{label}_form_losses": losses,
        f"{label}_form_points": points,
        f"{label}_form_trend": trend,
    }


# ============================ Aggregate ==================================

def compute_all_features(match: dict) -> dict:
    """Compute all engineered features for a match.
    
    Combines H2H, odds movement, and form features into single feature vector.
    """
    h2h_features = compute_h2h_features(match.get("h2h", []))
    odds_features = compute_odds_movement(match.get("odds_history", []))
    home_form = compute_form_features(match.get("form_home", []), "home")
    away_form = compute_form_features(match.get("form_away", []), "away")
    
    return {
        "h2h": h2h_features,
        "odds_movement": odds_features,
        "home_form": home_form,
        "away_form": away_form,
    }


def features_summary_for_llm(features: dict) -> dict:
    """Compact summary of features for LLM prompt (smaller token usage)."""
    h2h = features["h2h"]
    odds = features["odds_movement"]
    hf = features["home_form"]
    af = features["away_form"]
    
    return {
        "h2h_record": f"H{h2h['h2h_home_wins']}-D{h2h['h2h_draws']}-A{h2h['h2h_away_wins']}",
        "h2h_avg_goals": h2h.get("h2h_avg_goals"),
        "h2h_btts_rate": h2h.get("h2h_btts_rate"),
        "h2h_over_2_5_rate": h2h.get("h2h_over_2_5_rate"),
        "odds_movement": odds.get("odds_movement_pct"),
        "market_signal": odds.get("market_signal"),
        "home_form": hf.get("home_form_5"),
        "home_form_points": hf.get("home_form_points"),
        "home_form_trend": hf.get("home_form_trend"),
        "away_form": af.get("away_form_5"),
        "away_form_points": af.get("away_form_points"),
        "away_form_trend": af.get("away_form_trend"),
    }
