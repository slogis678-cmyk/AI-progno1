"""Edge AI – Football match statistical edge detector.

FastAPI backend exposing:
  /api/auth/* – JWT auth (email/password)
  /api/matches/* – CRUD + analysis
  /api/bets/* – bet tracker
  /api/stats – aggregate metrics
"""
from __future__ import annotations

from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

from auth import (
    AuthResponse,
    LoginIn,
    RegisterIn,
    UserOut,
    create_access_token,
    decode_token,
    get_bearer_token,
    hash_password,
    verify_password,
)
from ai_analyzer import MODEL_REGISTRY, compute_edge, llm_analyze_match
from demo_data import demo_matches
from external_data import (
    LEAGUES,
    ODDS_SPORTS,
    fetch_api_football_fixtures,
    fetch_odds_api_events,
    fetch_odds_api_sports,
)
from scheduler import (
    get_last_run_status,
    refresh_odds_history,
    start_scheduler,
    stop_scheduler,
)

logger = logging.getLogger("edge-ai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

# --------------------------------------------------------------------------
# Mongo

mongo_url = os.environ["MONGO_URL"]
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ["DB_NAME"]]

# --------------------------------------------------------------------------
# Helpers

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_id(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


async def current_user(request: Request) -> dict:
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Brak tokenu autoryzacyjnego")
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje")
    return user


# --------------------------------------------------------------------------
# Models

class Odds(BaseModel):
    home: float
    draw: float
    away: float


class TempoData(BaseModel):
    model_config = ConfigDict(extra="allow")
    possession_home: float = 50
    shots_home: float = 12
    shots_away: float = 12
    ppda_home: float = 10
    ppda_away: float = 10


class MatchIn(BaseModel):
    home_team: str
    away_team: str
    league: str
    kickoff: str
    odds: Odds
    tempo: Optional[TempoData] = None
    form_home: list[str] = Field(default_factory=list)
    form_away: list[str] = Field(default_factory=list)
    h2h: list[dict] = Field(default_factory=list)
    odds_history: list[dict] = Field(default_factory=list)


class MatchOut(MatchIn):
    id: str
    status: str = "upcoming"
    edge_summary: Optional[dict] = None


class AnalyzeIn(BaseModel):
    model: str = "claude-sonnet-4-5-20250929"


class BetIn(BaseModel):
    match_id: str
    outcome: str  # home | draw | away
    stake: float
    odds: float
    note: Optional[str] = None


class BetResultIn(BaseModel):
    result: str  # won | lost | void


# --------------------------------------------------------------------------
# App + routers

app = FastAPI(title="Edge AI – Football Edge Detector")
api = APIRouter(prefix="/api")


# ---------------- Auth ----------------------------------------------------

@api.post("/auth/register", response_model=AuthResponse)
async def register(body: RegisterIn):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail już zarejestrowany")
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "full_name": body.full_name.strip(),
        "password_hash": hash_password(body.password),
        "preferred_model": "claude-sonnet-4-5-20250929",
        "created_at": _now_iso(),
    }
    await db.users.insert_one(user_doc)
    # auto-seed demo matches for the new user
    seed = demo_matches(owner_id=user_doc["id"])
    if seed:
        await db.matches.insert_many(seed)
    token = create_access_token(user_doc["id"], email)
    return AuthResponse(
        token=token,
        user=UserOut(
            id=user_doc["id"],
            email=email,
            full_name=user_doc["full_name"],
            preferred_model=user_doc["preferred_model"],
        ),
    )


@api.post("/auth/login", response_model=AuthResponse)
async def login(body: LoginIn):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Nieprawidłowy e-mail lub hasło")
    token = create_access_token(user["id"], email)
    return AuthResponse(
        token=token,
        user=UserOut(
            id=user["id"],
            email=email,
            full_name=user["full_name"],
            preferred_model=user.get("preferred_model", "claude-sonnet-4-5-20250929"),
        ),
    )


@api.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(current_user)):
    return UserOut(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        preferred_model=user.get("preferred_model", "claude-sonnet-4-5-20250929"),
    )


class UpdatePrefIn(BaseModel):
    preferred_model: str


@api.patch("/auth/preferences", response_model=UserOut)
async def update_pref(body: UpdatePrefIn, user: dict = Depends(current_user)):
    if body.preferred_model not in MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail="Nieobsługiwany model")
    await db.users.update_one({"id": user["id"]}, {"$set": {"preferred_model": body.preferred_model}})
    return UserOut(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        preferred_model=body.preferred_model,
    )


@api.get("/models")
async def list_models():
    return {
        "models": [
            {"key": "claude-sonnet-4-5-20250929", "label": "Claude Sonnet 4.5", "provider": "Anthropic"},
            {"key": "gpt-5.2", "label": "GPT-5.2", "provider": "OpenAI"},
            {"key": "gemini-3.1-pro-preview", "label": "Gemini 3 Pro", "provider": "Google"},
        ]
    }


# ---------------- Matches -------------------------------------------------

@api.get("/matches")
async def list_matches(user: dict = Depends(current_user)):
    docs = await db.matches.find({"owner_id": user["id"]}, {"_id": 0}).sort("kickoff", 1).to_list(500)
    # enrich with edge summary
    out = []
    for d in docs:
        try:
            stats = compute_edge(d)
            d["edge_summary"] = {
                "best_outcome": stats["best_outcome"],
                "best_edge": stats["best_edge"],
                "confidence": stats["confidence"],
                "model_prob": stats["model_prob"],
                "implied": stats["implied"],
            }
        except Exception as e:
            logger.warning("edge compute failed for %s: %s", d.get("id"), e)
            d["edge_summary"] = None
        out.append(d)
    return out


@api.post("/matches")
async def create_match(body: MatchIn, user: dict = Depends(current_user)):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["owner_id"] = user["id"]
    doc["status"] = "upcoming"
    doc["created_at"] = _now_iso()
    if not doc.get("tempo"):
        doc["tempo"] = {"possession_home": 50, "shots_home": 12, "shots_away": 12, "ppda_home": 10, "ppda_away": 10}
    await db.matches.insert_one(doc)
    _strip_id(doc)
    return doc


@api.get("/matches/{match_id}")
async def get_match(match_id: str, user: dict = Depends(current_user)):
    doc = await db.matches.find_one({"id": match_id, "owner_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Mecz nie znaleziony")
    try:
        stats = compute_edge(doc)
        doc["edge_summary"] = {
            "best_outcome": stats["best_outcome"],
            "best_edge": stats["best_edge"],
            "confidence": stats["confidence"],
            "model_prob": stats["model_prob"],
            "implied": stats["implied"],
            "edges": stats["edges"],
            "pillars": stats["pillars"],
        }
    except Exception as e:
        logger.warning("edge compute failed: %s", e)
    # latest AI analysis (if any)
    latest = await db.analyses.find_one({"match_id": match_id}, {"_id": 0}, sort=[("created_at", -1)])
    doc["latest_analysis"] = latest
    return doc


@api.delete("/matches/{match_id}")
async def delete_match(match_id: str, user: dict = Depends(current_user)):
    r = await db.matches.delete_one({"id": match_id, "owner_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Mecz nie znaleziony")
    await db.analyses.delete_many({"match_id": match_id})
    return {"ok": True}


@api.post("/matches/{match_id}/analyze")
async def analyze_match(match_id: str, body: AnalyzeIn, user: dict = Depends(current_user)):
    doc = await db.matches.find_one({"id": match_id, "owner_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Mecz nie znaleziony")
    stats = compute_edge(doc)
    model_key = body.model if body.model in MODEL_REGISTRY else user.get("preferred_model", "claude-sonnet-4-5-20250929")
    try:
        ai = await llm_analyze_match(doc, stats, model_key)
    except Exception as e:
        logger.exception("LLM analysis failed")
        raise HTTPException(status_code=502, detail=f"Błąd modelu AI: {e}")
    record = {
        "id": str(uuid.uuid4()),
        "match_id": match_id,
        "owner_id": user["id"],
        "model": model_key,
        "stats": stats,
        "ai": ai,
        "created_at": _now_iso(),
    }
    await db.analyses.insert_one(record)
    record.pop("_id", None)
    return record


@api.get("/matches/{match_id}/analyses")
async def list_analyses(match_id: str, user: dict = Depends(current_user)):
    docs = await db.analyses.find({"match_id": match_id, "owner_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return docs


# ---------------- Bets ----------------------------------------------------

@api.get("/bets")
async def list_bets(user: dict = Depends(current_user)):
    docs = await db.bets.find({"owner_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api.post("/bets")
async def place_bet(body: BetIn, user: dict = Depends(current_user)):
    match = await db.matches.find_one({"id": body.match_id, "owner_id": user["id"]}, {"_id": 0})
    if not match:
        raise HTTPException(status_code=404, detail="Mecz nie istnieje")
    doc = {
        "id": str(uuid.uuid4()),
        "owner_id": user["id"],
        "match_id": body.match_id,
        "match_label": f"{match['home_team']} vs {match['away_team']}",
        "league": match["league"],
        "outcome": body.outcome,
        "stake": body.stake,
        "odds": body.odds,
        "note": body.note or "",
        "status": "pending",
        "profit": 0.0,
        "created_at": _now_iso(),
    }
    await db.bets.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.patch("/bets/{bet_id}")
async def settle_bet(bet_id: str, body: BetResultIn, user: dict = Depends(current_user)):
    bet = await db.bets.find_one({"id": bet_id, "owner_id": user["id"]})
    if not bet:
        raise HTTPException(status_code=404, detail="Zakład nie istnieje")
    status = body.result
    if status not in ("won", "lost", "void"):
        raise HTTPException(status_code=400, detail="Nieprawidłowy status")
    if status == "won":
        profit = (bet["odds"] - 1) * bet["stake"]
    elif status == "lost":
        profit = -bet["stake"]
    else:
        profit = 0.0
    await db.bets.update_one({"id": bet_id}, {"$set": {"status": status, "profit": profit}})
    bet["status"] = status
    bet["profit"] = profit
    bet.pop("_id", None)
    return bet


@api.delete("/bets/{bet_id}")
async def delete_bet(bet_id: str, user: dict = Depends(current_user)):
    r = await db.bets.delete_one({"id": bet_id, "owner_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Zakład nie istnieje")
    return {"ok": True}


# ---------------- Stats ---------------------------------------------------

@api.get("/stats")
async def stats(user: dict = Depends(current_user)):
    bets = await db.bets.find({"owner_id": user["id"]}, {"_id": 0}).to_list(2000)
    total = len(bets)
    settled = [b for b in bets if b["status"] in ("won", "lost")]
    wins = sum(1 for b in settled if b["status"] == "won")
    total_stake = sum(b["stake"] for b in settled)
    total_profit = sum(b["profit"] for b in settled)
    roi = (total_profit / total_stake * 100) if total_stake > 0 else 0.0
    hit_rate = (wins / len(settled) * 100) if settled else 0.0

    by_league: dict[str, dict] = {}
    for b in settled:
        lg = by_league.setdefault(b["league"], {"bets": 0, "wins": 0, "stake": 0.0, "profit": 0.0})
        lg["bets"] += 1
        lg["wins"] += 1 if b["status"] == "won" else 0
        lg["stake"] += b["stake"]
        lg["profit"] += b["profit"]
    for lg in by_league.values():
        lg["roi"] = (lg["profit"] / lg["stake"] * 100) if lg["stake"] > 0 else 0.0
        lg["hit_rate"] = (lg["wins"] / lg["bets"] * 100) if lg["bets"] else 0.0

    # cumulative profit timeline
    sorted_bets = sorted(settled, key=lambda x: x["created_at"])
    timeline = []
    cum = 0.0
    for b in sorted_bets:
        cum += b["profit"]
        timeline.append({"ts": b["created_at"], "cum_profit": round(cum, 2)})

    # AI accuracy: analyses whose predicted verdict matches winning bet outcome
    analyses = await db.analyses.find({"owner_id": user["id"]}, {"_id": 0}).to_list(1000)
    matched_bets = {b["match_id"]: b for b in settled if b["status"] in ("won", "lost")}
    ai_correct = 0
    ai_total = 0
    for a in analyses:
        b = matched_bets.get(a["match_id"])
        if not b:
            continue
        ai_total += 1
        if a.get("ai", {}).get("verdict") == b["outcome"] and b["status"] == "won":
            ai_correct += 1
    ai_acc = (ai_correct / ai_total * 100) if ai_total else 0.0

    return {
        "total_bets": total,
        "settled_bets": len(settled),
        "wins": wins,
        "hit_rate": round(hit_rate, 2),
        "total_stake": round(total_stake, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
        "by_league": by_league,
        "timeline": timeline,
        "ai_accuracy": round(ai_acc, 2),
        "ai_total": ai_total,
    }


# ---------------- Misc ----------------------------------------------------

@api.get("/")
async def root():
    return {"name": "Edge AI", "status": "ok"}


@api.post("/seed-demo")
async def seed_demo(user: dict = Depends(current_user)):
    existing = await db.matches.count_documents({"owner_id": user["id"]})
    if existing > 0:
        return {"seeded": False, "existing": existing}
    seed = demo_matches(owner_id=user["id"])
    await db.matches.insert_many(seed)
    return {"seeded": True, "count": len(seed)}


# ---------------- External imports ---------------------------------------

class ImportApiFootballIn(BaseModel):
    league_id: int
    days_ahead: int = 7
    season: Optional[int] = None


class ImportOddsApiIn(BaseModel):
    sport_key: str


@api.get("/external/leagues")
async def external_leagues():
    odds = await fetch_odds_api_sports()
    return {"api_football": LEAGUES, "odds_api": odds}


async def _persist_imported(user_id: str, items: list[dict]) -> dict:
    inserted = 0
    skipped = 0
    for it in items:
        ext = it.get("external_id")
        if ext:
            exists = await db.matches.find_one({"owner_id": user_id, "external_id": ext})
            if exists:
                skipped += 1
                continue
        doc = {
            **it,
            "id": str(uuid.uuid4()),
            "owner_id": user_id,
            "status": "upcoming",
            "created_at": _now_iso(),
        }
        await db.matches.insert_one(doc)
        inserted += 1
    return {"inserted": inserted, "skipped": skipped, "total_fetched": len(items)}


@api.post("/external/import/api-football")
async def import_api_football(body: ImportApiFootballIn, user: dict = Depends(current_user)):
    try:
        items = await fetch_api_football_fixtures(body.league_id, body.days_ahead, body.season)
    except Exception as e:
        logger.exception("API-Football fetch failed")
        raise HTTPException(status_code=502, detail=f"Błąd API-Football: {e}")
    return await _persist_imported(user["id"], items)


@api.post("/external/import/odds-api")
async def import_odds_api(body: ImportOddsApiIn, user: dict = Depends(current_user)):
    try:
        items = await fetch_odds_api_events(body.sport_key)
    except Exception as e:
        logger.exception("Odds API fetch failed")
        raise HTTPException(status_code=502, detail=f"Błąd The Odds API: {e}")
    return await _persist_imported(user["id"], items)


# --------------------------------------------------------------------------
# Wire up

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.matches.create_index([("owner_id", 1), ("kickoff", 1)])
    await db.bets.create_index([("owner_id", 1), ("created_at", -1)])
    await db.analyses.create_index([("match_id", 1), ("created_at", -1)])
    # seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@edgeai.pl")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        admin_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": admin_id,
            "email": admin_email,
            "full_name": "Admin",
            "password_hash": hash_password(admin_password),
            "preferred_model": "claude-sonnet-4-5-20250929",
            "created_at": _now_iso(),
            "role": "admin",
        })
        await db.matches.insert_many(demo_matches(owner_id=admin_id))
        logger.info("Seeded admin user %s", admin_email)


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
