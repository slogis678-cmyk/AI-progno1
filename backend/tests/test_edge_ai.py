"""Edge AI backend regression tests - covers auth, matches, bets, stats, AI analysis."""
import os
import uuid
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load backend .env for credentials
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# Load frontend .env for public URL
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@edgeai.pl")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    return data["token"]


@pytest.fixture(scope="session")
def admin_client(api, admin_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"})
    return s


# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
class TestAuth:
    def test_login_admin(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == ADMIN_EMAIL
        assert isinstance(data["token"], str) and len(data["token"]) > 20

    def test_login_wrong_password(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_register_and_seed(self, api):
        email = f"test_{uuid.uuid4().hex[:8]}@edgeai.pl"
        r = api.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "abc123", "full_name": "Test User"})
        assert r.status_code == 200, r.text
        data = r.json()
        token = data["token"]
        assert data["user"]["email"] == email
        # auto-seed should give 6 matches
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {token}"})
        m = s.get(f"{BASE_URL}/api/matches")
        assert m.status_code == 200
        assert len(m.json()) == 6

    def test_register_duplicate(self, api):
        email = f"dup_{uuid.uuid4().hex[:6]}@edgeai.pl"
        api.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "abc123", "full_name": "Dup"})
        r = api.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "abc123", "full_name": "Dup"})
        assert r.status_code == 400

    def test_me(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_me_unauth(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_invalid_token(self, api):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
        assert r.status_code == 401

    def test_update_preferences(self, admin_client):
        r = admin_client.patch(f"{BASE_URL}/api/auth/preferences", json={"preferred_model": "gpt-5.2"})
        assert r.status_code == 200
        assert r.json()["preferred_model"] == "gpt-5.2"
        # restore
        admin_client.patch(f"{BASE_URL}/api/auth/preferences", json={"preferred_model": "claude-sonnet-4-5-20250929"})

    def test_update_preferences_invalid(self, admin_client):
        r = admin_client.patch(f"{BASE_URL}/api/auth/preferences", json={"preferred_model": "bogus-model"})
        assert r.status_code == 400


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class TestModels:
    def test_list_models(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/models")
        assert r.status_code == 200
        keys = {m["key"] for m in r.json()["models"]}
        assert {"claude-sonnet-4-5-20250929", "gpt-5.2", "gemini-3.1-pro-preview"} == keys


# -----------------------------------------------------------------------------
# Matches
# -----------------------------------------------------------------------------
class TestMatches:
    def test_list_matches_has_edge_summary(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/matches")
        assert r.status_code == 200
        matches = r.json()
        assert len(matches) >= 6
        for m in matches:
            assert m["edge_summary"] is not None
            es = m["edge_summary"]
            for k in ("best_outcome", "best_edge", "confidence", "model_prob", "implied"):
                assert k in es

    def test_bayern_match_home_edge(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/matches")
        bayern = next((m for m in r.json() if "Bayern" in m["home_team"]), None)
        assert bayern is not None
        # Strong home advantage expected
        assert bayern["edge_summary"]["best_outcome"] == "home"

    def test_get_match_detail_pillars(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/matches")
        match_id = r.json()[0]["id"]
        r = admin_client.get(f"{BASE_URL}/api/matches/{match_id}")
        assert r.status_code == 200
        es = r.json()["edge_summary"]
        assert "pillars" in es
        pillars = es["pillars"]
        for p in ("tempo", "odds_micro", "reaction_home", "reaction_away", "h2h"):
            assert p in pillars

    def test_create_match(self, admin_client):
        payload = {
            "home_team": "TEST_Home",
            "away_team": "TEST_Away",
            "league": "TEST_League",
            "kickoff": "2026-02-01T18:00:00+00:00",
            "odds": {"home": 2.0, "draw": 3.3, "away": 3.5},
            "form_home": ["W", "W"],
            "form_away": ["L", "D"],
            "h2h": [{"result": "H"}],
            "odds_history": [],
        }
        r = admin_client.post(f"{BASE_URL}/api/matches", json=payload)
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        assert r.json()["tempo"]["possession_home"] == 50  # default
        # Get back
        g = admin_client.get(f"{BASE_URL}/api/matches/{mid}")
        assert g.status_code == 200
        assert g.json()["home_team"] == "TEST_Home"
        # cleanup
        d = admin_client.delete(f"{BASE_URL}/api/matches/{mid}")
        assert d.status_code == 200
        gone = admin_client.get(f"{BASE_URL}/api/matches/{mid}")
        assert gone.status_code == 404

    def test_unauthorized_matches(self, api):
        r = api.get(f"{BASE_URL}/api/matches")
        assert r.status_code == 401


# -----------------------------------------------------------------------------
# AI Analysis (real LLM calls - slow)
# -----------------------------------------------------------------------------
class TestAIAnalysis:
    @pytest.fixture(scope="class")
    def match_id(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/matches")
        return r.json()[0]["id"]

    @pytest.mark.parametrize("model", [
        "claude-sonnet-4-5-20250929",
        "gpt-5.2",
        "gemini-3.1-pro-preview",
    ])
    def test_analyze_match(self, admin_client, match_id, model):
        r = admin_client.post(
            f"{BASE_URL}/api/matches/{match_id}/analyze",
            json={"model": model},
            timeout=90,
        )
        assert r.status_code == 200, f"{model} -> {r.status_code} {r.text[:300]}"
        data = r.json()
        assert data["model"] == model
        ai = data["ai"]
        assert ai["verdict"] in ("home", "draw", "away")
        assert "thesis" in ai and "confidence_pct" in ai
        for k in ("tempo_insight", "odds_trend_insight", "reaction_insight", "historical_insight", "risk"):
            assert k in ai

    def test_list_analyses(self, admin_client, match_id):
        r = admin_client.get(f"{BASE_URL}/api/matches/{match_id}/analyses")
        assert r.status_code == 200
        analyses = r.json()
        assert len(analyses) >= 1


# -----------------------------------------------------------------------------
# Bets + Stats
# -----------------------------------------------------------------------------
class TestBetsAndStats:
    def test_full_bet_lifecycle(self, admin_client):
        # Get a match
        matches = admin_client.get(f"{BASE_URL}/api/matches").json()
        mid = matches[0]["id"]
        # Create bet
        bet = admin_client.post(f"{BASE_URL}/api/bets", json={
            "match_id": mid, "outcome": "home", "stake": 100, "odds": 2.0, "note": "TEST_bet"
        })
        assert bet.status_code == 200, bet.text
        bid = bet.json()["id"]
        assert bet.json()["status"] == "pending"
        # Settle won
        s = admin_client.patch(f"{BASE_URL}/api/bets/{bid}", json={"result": "won"})
        assert s.status_code == 200
        assert s.json()["status"] == "won"
        assert abs(s.json()["profit"] - 100.0) < 0.01

        # Another bet -> lost
        bet2 = admin_client.post(f"{BASE_URL}/api/bets", json={
            "match_id": mid, "outcome": "away", "stake": 50, "odds": 3.5
        }).json()
        s2 = admin_client.patch(f"{BASE_URL}/api/bets/{bet2['id']}", json={"result": "lost"})
        assert s2.json()["profit"] == -50.0

        # Void
        bet3 = admin_client.post(f"{BASE_URL}/api/bets", json={
            "match_id": mid, "outcome": "draw", "stake": 20, "odds": 3.0
        }).json()
        s3 = admin_client.patch(f"{BASE_URL}/api/bets/{bet3['id']}", json={"result": "void"})
        assert s3.json()["profit"] == 0.0

        # Stats
        st = admin_client.get(f"{BASE_URL}/api/stats")
        assert st.status_code == 200
        data = st.json()
        for k in ("roi", "hit_rate", "total_profit", "by_league", "timeline", "ai_accuracy"):
            assert k in data

        # Cleanup
        for b in (bid, bet2["id"], bet3["id"]):
            admin_client.delete(f"{BASE_URL}/api/bets/{b}")

    def test_bet_invalid_match(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/bets", json={
            "match_id": "nonexistent", "outcome": "home", "stake": 10, "odds": 2.0
        })
        assert r.status_code == 404


# -----------------------------------------------------------------------------
# Seed demo idempotency
# -----------------------------------------------------------------------------
class TestSeed:
    def test_seed_demo_idempotent(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/seed-demo")
        assert r.status_code == 200
        assert r.json()["seeded"] is False  # admin already has matches
