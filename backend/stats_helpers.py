"""Statistics calculation helpers - extracted from server.py for better maintainability."""


def calculate_basic_stats(bets: list) -> dict:
    """Calculate basic betting statistics: wins, ROI, hit rate."""
    settled = [b for b in bets if b["status"] in ("won", "lost")]
    wins = sum(1 for b in settled if b["status"] == "won")
    total_stake = sum(b["stake"] for b in settled)
    total_profit = sum(b["profit"] for b in settled)
    
    roi = (total_profit / total_stake * 100) if total_stake > 0 else 0.0
    hit_rate = (wins / len(settled) * 100) if settled else 0.0
    
    return {
        "total_bets": len(bets),
        "settled_bets": len(settled),
        "wins": wins,
        "hit_rate": round(hit_rate, 2),
        "total_stake": round(total_stake, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
    }


def calculate_league_stats(bets: list) -> dict:
    """Calculate per-league statistics."""
    settled = [b for b in bets if b["status"] in ("won", "lost")]
    by_league: dict[str, dict] = {}
    
    for b in settled:
        lg = by_league.setdefault(b["league"], {
            "bets": 0,
            "wins": 0,
            "stake": 0.0,
            "profit": 0.0
        })
        lg["bets"] += 1
        lg["wins"] += 1 if b["status"] == "won" else 0
        lg["stake"] += b["stake"]
        lg["profit"] += b["profit"]
    
    # Calculate derived metrics
    for lg in by_league.values():
        lg["roi"] = (lg["profit"] / lg["stake"] * 100) if lg["stake"] > 0 else 0.0
        lg["hit_rate"] = (lg["wins"] / lg["bets"] * 100) if lg["bets"] else 0.0
    
    return by_league


def calculate_profit_timeline(bets: list) -> list:
    """Calculate cumulative profit timeline."""
    settled = [b for b in bets if b["status"] in ("won", "lost")]
    sorted_bets = sorted(settled, key=lambda x: x["created_at"])
    
    timeline = []
    cum = 0.0
    for b in sorted_bets:
        cum += b["profit"]
        timeline.append({
            "ts": b["created_at"],
            "cum_profit": round(cum, 2)
        })
    
    return timeline


def calculate_ai_accuracy(analyses: list, bets: list) -> dict:
    """Calculate AI prediction accuracy based on winning bets."""
    settled = [b for b in bets if b["status"] in ("won", "lost")]
    matched_bets = {b["match_id"]: b for b in settled}
    
    ai_correct = 0
    ai_total = 0
    
    for analysis in analyses:
        bet = matched_bets.get(analysis["match_id"])
        if not bet:
            continue
        
        ai_total += 1
        predicted = analysis.get("ai", {}).get("verdict")
        if predicted == bet["outcome"] and bet["status"] == "won":
            ai_correct += 1
    
    ai_acc = (ai_correct / ai_total * 100) if ai_total else 0.0
    
    return {
        "ai_accuracy": round(ai_acc, 2),
        "ai_total": ai_total,
    }
