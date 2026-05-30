"""Statistical edge engine + AI analyzer using Emergent LLM key.

Combines four pillars from the user requirements:
  - tempo gry (game tempo)
  - mikrotrendy kursów (odds micro-trends)
  - reakcja zespołów (team reaction)
  - dane historyczne (historical data)

For each pillar we compute a score in [0,1]; their weighted blend gives the
"model probability". Edge = model_probability - implied_probability_from_odds.
"""
from __future__ import annotations

import json
import math
import os
import re
import uuid
from typing import Any

from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_helpers import (
    parse_json_from_llm_response,
    build_llm_system_prompt,
    build_match_payload,
    validate_and_enrich_ai_response,
)


# --------------------------- Statistical engine -----------------------------

def implied_probabilities(odds_home: float, odds_draw: float, odds_away: float) -> dict:
    """Convert decimal odds to implied probabilities, normalized to remove margin."""
    raw = {"home": 1.0 / odds_home, "draw": 1.0 / odds_draw, "away": 1.0 / odds_away}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def tempo_score(tempo: dict) -> float:
    """tempo: {possession_home, shots_home, shots_away, ppda_home, ppda_away}.
    Returns home tempo dominance in [0,1]. 0.5 = balanced.
    """
    poss = tempo.get("possession_home", 50) / 100.0
    shots_home = tempo.get("shots_home", 12)
    shots_away = tempo.get("shots_away", 12)
    shot_ratio = shots_home / max(1, shots_home + shots_away)
    ppda_home = tempo.get("ppda_home", 10)
    ppda_away = tempo.get("ppda_away", 10)
    # lower PPDA = more pressing = higher tempo control
    press = ppda_away / max(1.0, ppda_home + ppda_away)
    return max(0.0, min(1.0, 0.4 * poss + 0.4 * shot_ratio + 0.2 * press))


def odds_microtrend_score(history: list) -> dict:
    """history: list of {ts, home, draw, away}.
    Returns dict with signed drift per outcome in [-1,1] indicating market shift.
    Positive home_drift = home odds drifting DOWN (market moves to home).
    """
    if not history or len(history) < 2:
        return {"home_drift": 0.0, "draw_drift": 0.0, "away_drift": 0.0, "volatility": 0.0}
    first, last = history[0], history[-1]
    def drift(key: str) -> float:
        a = first.get(key, 2.0)
        b = last.get(key, 2.0)
        # negative delta => odds going down => money on this outcome
        d = (a - b) / max(0.01, a)
        return max(-1.0, min(1.0, d * 5))  # amplify small movements
    vols = []
    for k in ("home", "draw", "away"):
        vals = [h.get(k, 2.0) for h in history]
        if len(vals) >= 2:
            mu = sum(vals) / len(vals)
            v = sum((x - mu) ** 2 for x in vals) / len(vals)
            vols.append(math.sqrt(v))
    return {
        "home_drift": drift("home"),
        "draw_drift": drift("draw"),
        "away_drift": drift("away"),
        "volatility": sum(vols) / len(vols) if vols else 0.0,
    }


def reaction_score(form: list) -> float:
    """form: list of last 5 results 'W'/'D'/'L' (most recent first).
    Recency-weighted in [0,1]."""
    if not form:
        return 0.5
    weights = [0.35, 0.25, 0.18, 0.13, 0.09]
    pts = {"W": 1.0, "D": 0.5, "L": 0.0}
    s = sum(weights[i] * pts.get(r, 0.5) for i, r in enumerate(form[:5]))
    return max(0.0, min(1.0, s / sum(weights[: len(form[:5])])))


def historical_h2h_score(h2h: list) -> float:
    """h2h: list of {result: 'H'/'D'/'A'}. Returns home advantage in [0,1]."""
    if not h2h:
        return 0.5
    h = sum(1 for x in h2h if x.get("result") == "H")
    d = sum(1 for x in h2h if x.get("result") == "D")
    a = sum(1 for x in h2h if x.get("result") == "A")
    total = h + d + a
    if total == 0:
        return 0.5
    return (h + 0.5 * d) / total


def compute_edge(match: dict, elo_data: dict | None = None, 
                xg_data: dict | None = None, injuries_data: dict | None = None) -> dict:
    """Run the full statistical pipeline on a single match document.
    
    Combines up to 7 pillars (more = higher confidence):
    Core (always): tempo, odds_micro, reaction_home, reaction_away, h2h
    Advanced (when available): elo_rating, xg_dominance, squad_advantage
    """
    odds = match["odds"]
    implied = implied_probabilities(odds["home"], odds["draw"], odds["away"])

    # === CORE PILLARS (always computed) ===
    tempo = tempo_score(match.get("tempo", {}))
    micro = odds_microtrend_score(match.get("odds_history", []))
    rs_home = reaction_score(match.get("form_home", []))
    rs_away = reaction_score(match.get("form_away", []))
    h2h = historical_h2h_score(match.get("h2h", []))

    # === ADVANCED PILLARS (when data available) ===
    elo_signal = elo_data["elo_home_win_prob"] if elo_data else None
    xg_signal = xg_data["home_xg_dominance"] if xg_data else None
    squad_signal = injuries_data["home_squad_advantage"] if injuries_data else None

    # === DYNAMIC WEIGHTING based on available pillars ===
    # Base weights (5 core pillars sum to 1.0)
    weights = {
        "tempo": 0.22,
        "odds_micro": 0.15,
        "rs_home": 0.18,
        "rs_away": 0.10,
        "h2h": 0.15,
        "elo": 0.10 if elo_signal is not None else 0,
        "xg": 0.07 if xg_signal is not None else 0,
        "squad": 0.03 if squad_signal is not None else 0,
    }
    # Renormalize to sum=1
    weight_sum = sum(weights.values())
    weights = {k: v / weight_sum for k, v in weights.items()}

    # Build home raw probability with all available signals
    p_home_raw = (
        weights["tempo"] * tempo
        + weights["odds_micro"] * (0.5 + 0.5 * micro["home_drift"])
        + weights["rs_home"] * rs_home
        + weights["rs_away"] * (1 - rs_away)
        + weights["h2h"] * h2h
    )
    p_away_raw = (
        weights["tempo"] * (1 - tempo)
        + weights["odds_micro"] * (0.5 + 0.5 * micro["away_drift"])
        + weights["rs_home"] * (1 - rs_home)
        + weights["rs_away"] * rs_away
        + weights["h2h"] * (1 - h2h)
    )
    # Advanced pillars contribution
    if elo_signal is not None:
        p_home_raw += weights["elo"] * elo_signal
        p_away_raw += weights["elo"] * (1 - elo_signal)
    if xg_signal is not None:
        p_home_raw += weights["xg"] * xg_signal
        p_away_raw += weights["xg"] * (1 - xg_signal)
    if squad_signal is not None:
        p_home_raw += weights["squad"] * squad_signal
        p_away_raw += weights["squad"] * (1 - squad_signal)

    # Draw probability anchored on implied, adjusted by closeness of strengths
    closeness = 1 - abs(p_home_raw - p_away_raw)
    p_draw_raw = max(0.05, implied["draw"] * (0.6 + 0.4 * closeness))

    total = p_home_raw + p_draw_raw + p_away_raw
    model_prob = {
        "home": p_home_raw / total,
        "draw": p_draw_raw / total,
        "away": p_away_raw / total,
    }

    edges = {k: model_prob[k] - implied[k] for k in ("home", "draw", "away")}
    best_outcome = max(edges, key=edges.get)

    # Confidence based on signal alignment (low variance + more signals = higher conf)
    signal_list = [tempo, 0.5 + 0.5 * micro["home_drift"], rs_home, h2h]
    if elo_signal is not None:
        signal_list.append(elo_signal)
    if xg_signal is not None:
        signal_list.append(xg_signal)
    if squad_signal is not None:
        signal_list.append(squad_signal)
    
    mu = sum(signal_list) / len(signal_list)
    spread = sum((x - mu) ** 2 for x in signal_list) / len(signal_list)
    # More pillars + low spread = higher confidence
    pillar_count_bonus = min(0.15, (len(signal_list) - 4) * 0.05)
    base_confidence = max(0.0, min(1.0, 1 - math.sqrt(spread) * 1.6))
    confidence = max(0.0, min(0.95, base_confidence + pillar_count_bonus))

    result = {
        "implied": implied,
        "model_prob": model_prob,
        "edges": edges,
        "best_outcome": best_outcome,
        "best_edge": edges[best_outcome],
        "confidence": confidence,
        "pillars_count": len(signal_list),
        "pillars": {
            "tempo": tempo,
            "odds_micro": micro,
            "reaction_home": rs_home,
            "reaction_away": rs_away,
            "h2h": h2h,
        },
    }
    
    # Add advanced pillar data if used
    if elo_data:
        result["pillars"]["elo"] = elo_data
    if xg_data:
        result["pillars"]["xg"] = xg_data
    if injuries_data:
        result["pillars"]["squad"] = injuries_data
    
    return result


# ----------------------------- LLM analyzer --------------------------------

MODEL_REGISTRY = {
    "claude-sonnet-4-5-20250929": ("anthropic", "claude-sonnet-4-5-20250929"),
    "gpt-5.2": ("openai", "gpt-5.2"),
    "gemini-3.1-pro-preview": ("gemini", "gemini-3.1-pro-preview"),
}


def _parse_json_response(text: str) -> dict:
    """Wrapper for backward compatibility - uses ai_helpers."""
    return parse_json_from_llm_response(text)


async def llm_analyze_match(match: dict, stats: dict, model_key: str, 
                            features_summary: dict | None = None) -> dict:
    """Ask the selected LLM to interpret statistical signals and produce
    a structured Polish analysis.
    
    Args:
        match: match document
        stats: compute_edge() result
        model_key: which LLM to use
        features_summary: optional engineered features (H2H stats, odds movement, form)
    """
    api_key = os.environ["EMERGENT_LLM_KEY"]
    provider, model = MODEL_REGISTRY.get(
        model_key, 
        MODEL_REGISTRY["claude-sonnet-4-5-20250929"]
    )

    # Build prompts and payload using helpers
    system_msg = build_llm_system_prompt()
    payload = build_match_payload(match, stats)
    
    # Add engineered features to payload if available
    if features_summary:
        payload["engineered_features"] = features_summary

    # Initialize LLM chat
    chat = LlmChat(
        api_key=api_key,
        session_id=f"edge-{uuid.uuid4()}",
        system_message=system_msg,
    ).with_model(provider, model)

    # Send user message
    user_msg = UserMessage(
        text=(
            "Przeanalizuj poniższe dane meczu i wyniki silnika. "
            "Wykorzystaj engineered_features (H2H stats, odds movement, form trends) "
            "do wzbogacenia analizy. Zwróć WYŁĄCZNIE JSON zgodny ze schematem.\n\n"
            f"DANE:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
    )
    
    raw = await chat.send_message(user_msg)
    
    # Parse and validate response
    parsed = parse_json_from_llm_response(raw if isinstance(raw, str) else str(raw))
    return validate_and_enrich_ai_response(parsed, stats, model_key)
