"""Annabet.com client for fetching match statistics.

⚠️ IMPORTANT: annabet.com is a Single Page Application (SPA) that renders content
via JavaScript. Direct HTML fetching via requests/BeautifulSoup returns only the
empty shell - no match data.

To actually scrape data from annabet, you would need:
1. Playwright/Selenium (browser automation with JS rendering)
2. Or reverse-engineer their internal JSON API endpoints
3. Or use their official partner API (if available)

This module is provided for completeness and as an extension point. The structured
data you'd normally extract from annabet (H2H, BTTS rates, over/under stats) is
ALREADY computed by our `feature_engineering.py` module from existing data sources
(API-Football H2H, The Odds API odds, ClubElo ratings).

If you want to enable JS rendering, install playwright:
    pip install playwright
    playwright install chromium

And use `fetch_match_page_rendered()` below.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("edge-ai.annabet")

BASE_URL = "https://annabet.com"


class AnnabetClient:
    """Client for scraping annabet.com match statistics.
    
    NOTE: Static HTML scraping returns SPA shell only. Use Playwright for full data.
    """
    
    def __init__(self, language: str = "en"):
        self.language = language
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": f"{language},en;q=0.9",
            },
            timeout=15,
            follow_redirects=True,
        )
    
    def build_match_url(self, home_team: str, away_team: str) -> str:
        """Build annabet.com URL from team names (slug format)."""
        def slugify(name: str) -> str:
            slug = name.lower()
            slug = re.sub(r"[^a-z0-9]+", "-", slug)
            return slug.strip("-")
        
        home_slug = slugify(home_team)
        away_slug = slugify(away_team)
        return f"{BASE_URL}/{self.language}/football/stats/{home_slug}-{away_slug}"
    
    def fetch_match_page(self, url: str) -> str:
        """Fetch raw HTML page. Note: returns SPA shell, not rendered data."""
        r = self.client.get(url)
        r.raise_for_status()
        return r.text
    
    def is_spa_shell(self, html: str) -> bool:
        """Detect if HTML is just SPA shell (no rendered match data)."""
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if not body:
            return True
        body_text = body.get_text(" ", strip=True)
        # Heuristic: less than 500 chars of body text = likely SPA shell
        return len(body_text) < 500
    
    def parse_match(self, html: str) -> dict:
        """Parse match data from HTML. Returns empty structure if SPA shell."""
        soup = BeautifulSoup(html, "html.parser")
        
        data = {
            "teams": self._parse_teams(soup),
            "odds": self._parse_odds(soup),
            "h2h": self._parse_h2h(soup),
            "stats": self._parse_stats(soup),
            "is_spa_shell": self.is_spa_shell(html),
        }
        return data
    
    def _parse_teams(self, soup: BeautifulSoup) -> list:
        for tag in soup.find_all(["h1", "h2"]):
            text = tag.get_text(" ", strip=True)
            if " - " in text or " vs " in text.lower():
                separator = " - " if " - " in text else " vs "
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    return [parts[0].strip(), parts[1].strip()]
        return []
    
    def _parse_odds(self, soup: BeautifulSoup) -> list:
        odds = []
        for row in soup.find_all("tr"):
            cols = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) >= 4:
                # Skip if header row
                if any(h in cols[0].lower() for h in ("bookmaker", "match", "team")):
                    continue
                odds.append({
                    "bookmaker": cols[0],
                    "home": cols[1],
                    "draw": cols[2],
                    "away": cols[3],
                })
        return odds
    
    def _parse_h2h(self, soup: BeautifulSoup) -> list:
        matches = []
        for row in soup.find_all("tr"):
            cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                # Check if first column looks like a date
                first_col = cols[0]
                if re.match(r"^\d{4}-\d{2}-\d{2}", first_col) or re.match(r"^\d{2}\.\d{2}\.\d{4}", first_col):
                    matches.append({
                        "date": cols[0],
                        "score": cols[1],
                        "competition": cols[2],
                    })
        return matches[:20]
    
    def _parse_stats(self, soup: BeautifulSoup) -> dict:
        text = soup.get_text(" ", strip=True).lower()
        return {
            "btts_keywords_found": "both teams to score" in text or "btts" in text,
            "over_under_found": "over 2.5" in text or "under 2.5" in text,
            "handicap_found": "handicap" in text or "asian" in text,
            "page_text_length": len(text),
        }
    
    @staticmethod
    def save_json(data: dict, filepath: str | Path) -> None:
        """Save parsed data to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def close(self) -> None:
        self.client.close()


def try_fetch_annabet_data(home_team: str, away_team: str) -> Optional[dict]:
    """Try to fetch annabet data with fallback. Returns None if SPA shell.
    
    Use this from server endpoints to safely attempt fetching.
    """
    try:
        client = AnnabetClient()
        url = client.build_match_url(home_team, away_team)
        html = client.fetch_match_page(url)
        data = client.parse_match(html)
        
        if data["is_spa_shell"]:
            logger.warning("Annabet returned SPA shell for %s vs %s - needs JS rendering", 
                          home_team, away_team)
            return None
        
        return data
    except Exception as e:
        logger.warning("Annabet fetch failed for %s vs %s: %s", home_team, away_team, e)
        return None
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    # Demo usage
    client = AnnabetClient()
    url = client.build_match_url("Hertha Berlin", "Holstein Kiel")
    print(f"URL: {url}")
    
    html = client.fetch_match_page(url)
    parsed = client.parse_match(html)
    
    print(f"Is SPA shell: {parsed['is_spa_shell']}")
    print(f"Teams parsed: {parsed['teams']}")
    print(f"H2H rows: {len(parsed['h2h'])}")
    print(f"Odds rows: {len(parsed['odds'])}")
    
    client.save_json(parsed, "/tmp/annabet_test.json")
    print("Saved to /tmp/annabet_test.json")
