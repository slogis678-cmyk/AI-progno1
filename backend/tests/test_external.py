"""Iteration 2 - external imports (API-Football + The Odds API) + match history regression."""
import os
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN_EMAIL = "admin@edgeai.pl"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


class TestExternalLeagues:
    def test_leagues_returns_both_sources(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/external/leagues", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "api_football" in data and "odds_api" in data
        # api_football is static list of 8 leagues
        assert isinstance(data["api_football"], list)
        assert len(data["api_football"]) == 8
        for lg in data["api_football"]:
            assert "id" in lg and "name" in lg
        # odds_api dynamically fetched; must be non-empty list (fallback to ODDS_SPORTS if API down)
        assert isinstance(data["odds_api"], list)
        assert len(data["odds_api"]) >= 1
        for s in data["odds_api"]:
            assert "key" in s and "label" in s


class TestOddsApiImport:
    @pytest.fixture(scope="class")
    def sport_key(self):
        # spec asks for brazil; fallback to first active soccer league if not in list
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        token = r.json()["token"]
        s.headers["Authorization"] = f"Bearer {token}"
        leagues = s.get(f"{BASE_URL}/api/external/leagues").json()["odds_api"]
        keys = [lg["key"] for lg in leagues]
        if "soccer_brazil_campeonato" in keys:
            return "soccer_brazil_campeonato"
        return keys[0]

    def test_import_inserts_and_skips_duplicates(self, admin_client, sport_key):
        r1 = admin_client.post(
            f"{BASE_URL}/api/external/import/odds-api",
            json={"sport_key": sport_key},
            timeout=60,
        )
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert {"inserted", "skipped", "total_fetched"} <= set(d1.keys())
        assert d1["total_fetched"] >= 0
        # if total_fetched is 0, league has no fixtures; treat as soft-pass
        if d1["total_fetched"] == 0:
            pytest.skip(f"League {sport_key} returned 0 events - cannot test dedup")
        assert d1["inserted"] + d1["skipped"] == d1["total_fetched"]

        # second call should skip everything
        r2 = admin_client.post(
            f"{BASE_URL}/api/external/import/odds-api",
            json={"sport_key": sport_key},
            timeout=60,
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["skipped"] >= d1["inserted"], f"Expected skipped>={d1['inserted']}, got {d2}"
        assert d2["inserted"] == 0

    def test_imported_match_has_edge_summary(self, admin_client, sport_key):
        admin_client.post(
            f"{BASE_URL}/api/external/import/odds-api",
            json={"sport_key": sport_key},
            timeout=60,
        )
        matches = admin_client.get(f"{BASE_URL}/api/matches").json()
        # find one with external_id starting with oddsapi:
        imported = [m for m in matches if str(m.get("external_id", "")).startswith("oddsapi:")]
        if not imported:
            pytest.skip("No odds-api imported matches found")
        m = imported[0]
        assert m["edge_summary"] is not None
        for k in ("best_outcome", "best_edge", "confidence"):
            assert k in m["edge_summary"]


class TestApiFootballImportGracefulFailure:
    def test_api_football_returns_502_on_subscription_block(self, admin_client):
        # premier league id=39; test account expected to be unsubscribed -> 502 with Polish msg
        r = admin_client.post(
            f"{BASE_URL}/api/external/import/api-football",
            json={"league_id": 39, "days_ahead": 7},
            timeout=60,
        )
        # Either succeeds (if subscribed) OR returns 502 gracefully
        if r.status_code == 200:
            data = r.json()
            assert "inserted" in data
        else:
            assert r.status_code == 502, f"expected 502, got {r.status_code}: {r.text[:200]}"
            body = r.json()
            assert "detail" in body
            assert "API-Football" in body["detail"] or "Błąd" in body["detail"]


class TestAnalysesRegression:
    def test_list_analyses_endpoint_still_works(self, admin_client):
        matches = admin_client.get(f"{BASE_URL}/api/matches").json()
        assert len(matches) >= 1
        mid = matches[0]["id"]
        r = admin_client.get(f"{BASE_URL}/api/matches/{mid}/analyses")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
