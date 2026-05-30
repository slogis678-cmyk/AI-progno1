"""AI analysis helpers - extracted from ai_analyzer.py for better maintainability."""
import json
import re
from typing import Any


def parse_json_from_llm_response(text: str) -> dict:
    """Tolerantly extract JSON object from LLM reply, handling code fences."""
    if not text:
        return {}
    
    text = text.strip()
    
    # Remove markdown code fences if present
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    
    # Try direct JSON parse
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try to find JSON object in text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    
    # Fallback: return text as summary
    return {"summary": text}


def build_llm_system_prompt() -> str:
    """Build system prompt for LLM analysis."""
    return (
        "Jesteś analitykiem typującym mecze piłki nożnej. "
        "Otrzymujesz dane statystyczne i wyniki silnika wykrywania przewagi. "
        "Twoim zadaniem jest stworzyć krótką, profesjonalną analizę w języku polskim. "
        "ZAWSZE odpowiadaj wyłącznie poprawnym JSON-em w schemacie: "
        '{"verdict":"home|draw|away","confidence_pct":0-100,'
        '"thesis":"krótka teza 1-2 zdania","tempo_insight":"...",'
        '"odds_trend_insight":"...","reaction_insight":"...",'
        '"historical_insight":"...","risk":"główne ryzyko zakładu"}'
    )


def build_match_payload(match: dict, stats: dict) -> dict:
    """Build structured payload for LLM from match data and computed stats."""
    return {
        "match": {
            "home": match["home_team"],
            "away": match["away_team"],
            "league": match["league"],
            "odds": match["odds"],
            "tempo": match.get("tempo", {}),
            "form_home": match.get("form_home", []),
            "form_away": match.get("form_away", []),
            "h2h_recent": match.get("h2h", []),
            "odds_history": match.get("odds_history", []),
        },
        "statistical_engine": {
            "implied_probabilities": stats["implied"],
            "model_probabilities": stats["model_prob"],
            "edges": stats["edges"],
            "best_outcome": stats["best_outcome"],
            "best_edge": stats["best_edge"],
            "confidence": stats["confidence"],
            "pillars": stats["pillars"],
        },
    }


def validate_and_enrich_ai_response(parsed: dict, stats: dict, model_key: str) -> dict:
    """Ensure AI response has all required fields with fallbacks."""
    # Set required fields with fallbacks
    parsed.setdefault("verdict", stats["best_outcome"])
    parsed.setdefault("confidence_pct", round(stats["confidence"] * 100))
    parsed.setdefault("thesis", "Analiza wygenerowana przez model.")
    
    # Ensure all insight fields exist
    for field in ("tempo_insight", "odds_trend_insight", "reaction_insight", 
                  "historical_insight", "risk"):
        parsed.setdefault(field, "")
    
    # Add metadata
    parsed["model_used"] = model_key
    
    return parsed


def calculate_pillar_confidence(pillars: dict) -> float:
    """Calculate confidence based on alignment of pillar signals."""
    values = [
        pillars["tempo"],
        0.5 + 0.5 * pillars["odds_micro"]["home_drift"],
        pillars["reaction_home"],
        pillars["h2h"],
    ]
    
    # Lower variance = higher confidence (signals agree)
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    
    # Convert variance to confidence score [0, 1]
    import math
    confidence = max(0.0, min(1.0, 1 - math.sqrt(variance) * 1.6))
    
    return confidence
