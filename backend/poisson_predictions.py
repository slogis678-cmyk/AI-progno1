"""Advanced match predictions using Poisson distribution model.

Generates predictions for:
  - Most likely correct score (1:0, 2:1, etc.)
  - BTS (Both Teams to Score) probability
  - Corners over/under
  - 1st half / 2nd half goals split
"""
from __future__ import annotations

import math
from typing import Optional


def poisson_pmf(k: int, lam: float) -> float:
    """Poisson probability mass function: P(X=k | λ)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * lam ** k) / math.factorial(k)


def estimate_expected_goals(match: dict, elo_data: dict | None = None, 
                           xg_data: dict | None = None) -> tuple[float, float]:
    """Estimate expected goals (λ_home, λ_away) for the match.
    
    Combines:
    - Odds-implied goals (from market)
    - Elo rating differential
    - xG data when available
    """
    odds = match.get("odds", {})
    o_home = odds.get("home", 2.5)
    o_draw = odds.get("draw", 3.3)
    o_away = odds.get("away", 2.8)
    
    # Base expected goals from odds (lower odds = more goals expected for that side)
    # Implied probabilities suggest scoring rates
    total_inv = 1/o_home + 1/o_draw + 1/o_away
    p_home = (1/o_home) / total_inv
    p_away = (1/o_away) / total_inv
    
    # Map probabilities to expected goals (typical match ~2.6 total goals)
    league_avg_total = 2.6
    home_share = p_home / max(0.1, (p_home + p_away))
    
    lam_home = league_avg_total * home_share + 0.3  # home advantage bonus
    lam_away = league_avg_total * (1 - home_share)
    
    # Adjust with xG data if available
    if xg_data:
        xg_home = xg_data.get("home_xg_estimated", lam_home)
        xg_away = xg_data.get("away_xg_estimated", lam_away)
        # Blend 50/50 with odds-based estimate
        lam_home = (lam_home + xg_home) / 2
        lam_away = (lam_away + xg_away) / 2
    
    # Adjust with Elo differential
    if elo_data:
        elo_diff = elo_data.get("elo_diff", 0)
        # Each 100 Elo diff ≈ 0.15 goals shift
        adjustment = elo_diff / 100 * 0.15
        lam_home += adjustment / 2
        lam_away -= adjustment / 2
    
    # Clamp to realistic range
    lam_home = max(0.3, min(4.5, lam_home))
    lam_away = max(0.3, min(4.5, lam_away))
    
    return round(lam_home, 2), round(lam_away, 2)


def predict_score_matrix(lam_home: float, lam_away: float, max_goals: int = 6) -> list:
    """Compute probability matrix P(home=i, away=j) for all (i,j) up to max_goals."""
    matrix = []
    for h in range(max_goals + 1):
        row = []
        for a in range(max_goals + 1):
            p = poisson_pmf(h, lam_home) * poisson_pmf(a, lam_away)
            row.append(p)
        matrix.append(row)
    return matrix


def predict_top_scores(matrix: list, top_n: int = 5) -> list:
    """Return top N most likely scores with probabilities."""
    scores = []
    for h in range(len(matrix)):
        for a in range(len(matrix[h])):
            scores.append({
                "score": f"{h}:{a}",
                "home": h,
                "away": a,
                "probability": matrix[h][a],
            })
    
    scores.sort(key=lambda x: x["probability"], reverse=True)
    
    # Round probabilities to percentages
    for s in scores[:top_n]:
        s["probability_pct"] = round(s["probability"] * 100, 2)
        del s["probability"]
    
    return scores[:top_n]


def predict_bts(matrix: list) -> dict:
    """Both Teams to Score probability."""
    p_bts_yes = 0.0
    p_bts_no = 0.0
    
    for h in range(len(matrix)):
        for a in range(len(matrix[h])):
            if h >= 1 and a >= 1:
                p_bts_yes += matrix[h][a]
            else:
                p_bts_no += matrix[h][a]
    
    return {
        "bts_yes_pct": round(p_bts_yes * 100, 2),
        "bts_no_pct": round(p_bts_no * 100, 2),
        "recommendation": "TAK" if p_bts_yes >= 0.55 else "NIE" if p_bts_no >= 0.55 else "NIEPEWNE",
    }


def predict_over_under(matrix: list, thresholds: list = [1.5, 2.5, 3.5]) -> dict:
    """Over/Under goal totals."""
    result = {}
    for threshold in thresholds:
        p_over = 0.0
        for h in range(len(matrix)):
            for a in range(len(matrix[h])):
                if (h + a) > threshold:
                    p_over += matrix[h][a]
        
        result[f"over_{threshold}"] = round(p_over * 100, 2)
        result[f"under_{threshold}"] = round((1 - p_over) * 100, 2)
    
    return result


def predict_halves(lam_home: float, lam_away: float) -> dict:
    """Predict goals in 1st half vs 2nd half.
    
    Statistical fact: ~45% of goals happen in 1st half, ~55% in 2nd half.
    """
    first_half_factor = 0.45
    second_half_factor = 0.55
    
    lam_1h = (lam_home + lam_away) * first_half_factor
    lam_2h = (lam_home + lam_away) * second_half_factor
    
    # P(at least 1 goal in half)
    p_goal_1h = 1 - poisson_pmf(0, lam_1h)
    p_goal_2h = 1 - poisson_pmf(0, lam_2h)
    
    # P(over 1.5 goals in half)
    p_over_1_5_1h = sum(poisson_pmf(k, lam_1h) for k in range(2, 10))
    p_over_1_5_2h = sum(poisson_pmf(k, lam_2h) for k in range(2, 10))
    
    return {
        "expected_goals_1h": round(lam_1h, 2),
        "expected_goals_2h": round(lam_2h, 2),
        "goal_in_1h_pct": round(p_goal_1h * 100, 2),
        "goal_in_2h_pct": round(p_goal_2h * 100, 2),
        "over_1_5_1h_pct": round(p_over_1_5_1h * 100, 2),
        "over_1_5_2h_pct": round(p_over_1_5_2h * 100, 2),
    }


def predict_corners(match: dict, lam_home: float, lam_away: float) -> dict:
    """Estimate corner kicks. Higher tempo + more shots → more corners.
    
    Heuristic: avg ~10 corners/match (5 home, 5 away).
    Adjust based on expected goals (proxy for shots).
    """
    # Baseline corners ~ 10 per match, scales with total expected goals
    total_xg = lam_home + lam_away
    avg_total_corners = 10.0
    
    # Adjust ±20% based on xG vs league avg (2.6)
    corner_multiplier = 0.8 + (total_xg / 2.6) * 0.2
    expected_total = avg_total_corners * corner_multiplier
    
    # Split by xG share
    home_share = lam_home / max(0.5, total_xg)
    expected_home_corners = expected_total * (0.5 + (home_share - 0.5) * 0.6)
    expected_away_corners = expected_total - expected_home_corners
    
    # Predict over/under common lines
    # Approximation: corners follow Poisson with λ = expected
    p_over_8_5 = sum(poisson_pmf(k, expected_total) for k in range(9, 20))
    p_over_9_5 = sum(poisson_pmf(k, expected_total) for k in range(10, 20))
    p_over_10_5 = sum(poisson_pmf(k, expected_total) for k in range(11, 20))
    
    return {
        "expected_total_corners": round(expected_total, 1),
        "expected_home_corners": round(expected_home_corners, 1),
        "expected_away_corners": round(expected_away_corners, 1),
        "over_8_5_pct": round(p_over_8_5 * 100, 2),
        "over_9_5_pct": round(p_over_9_5 * 100, 2),
        "over_10_5_pct": round(p_over_10_5 * 100, 2),
    }


def predict_full_match(match: dict, elo_data: dict | None = None, 
                       xg_data: dict | None = None) -> dict:
    """Generate ALL match predictions in one call.
    
    Returns dict with:
    - expected_goals: {home, away}
    - top_scores: [{score, probability_pct}, ...]
    - bts: {yes_pct, no_pct, recommendation}
    - over_under: {over_1_5, over_2_5, over_3_5}
    - halves: {goal_in_1h_pct, ...}
    - corners: {expected_total, over_8_5_pct, ...}
    """
    lam_home, lam_away = estimate_expected_goals(match, elo_data, xg_data)
    matrix = predict_score_matrix(lam_home, lam_away)
    
    return {
        "expected_goals": {
            "home": lam_home,
            "away": lam_away,
            "total": round(lam_home + lam_away, 2),
        },
        "top_scores": predict_top_scores(matrix, top_n=5),
        "bts": predict_bts(matrix),
        "over_under": predict_over_under(matrix),
        "halves": predict_halves(lam_home, lam_away),
        "corners": predict_corners(match, lam_home, lam_away),
    }
