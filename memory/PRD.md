# Edge AI — Product Requirements Document

## Original problem statement
"Stwórz Model AI który wykryła przewagę statystyczną opartą na stabilnych i powtarzalnych wzorcach meczowych. Uwzględnij: tempo gry, mikrotrendy kursów, reakcję zespołów, dane historyczne."

## User choices (May 2026 - Phase 1 ADVANCED)
- Sport: Football
- Data: External API (multiple sources) + manual entry
- AI: Multi-LLM via Emergent Universal Key — Claude Sonnet 4.5 + GPT-5.2 + Gemini 3 Pro
- **NEW**: ClubElo (Elo ratings), Poisson predictions, API-Football Direct
- Features: dashboard, AI predictions, deep analysis, history, bet tracking, stats, import, **advanced predictions panel**
- Auth: JWT email/password
- UI language: Polish
- Aesthetic: Bloomberg-terminal / dark fintech

## Architecture
- **Backend** FastAPI + Motor (MongoDB), JWT auth, Emergent LLM library
  - Modules: `server.py`, `ai_analyzer.py`, `external_data.py`, `advanced_data.py` (NEW), `poisson_predictions.py` (NEW)
  - Helpers: `stats_helpers.py`, `ai_helpers.py`, `external_helpers.py`
  - `compute_edge()` — extended **7-pillar engine**: tempo + odds_micro + reaction (home/away) + h2h + **Elo** + xG + squad
  - `predict_full_match()` — Poisson model for: correct score, BTS, over/under, corners, halves
  - Collections: `users`, `matches`, `analyses` (now with predictions), `bets`
- **Frontend** React 19 + react-router-dom 7 + Tailwind + shadcn/ui + recharts + Phosphor icons
  - Pages: `/login`, `/register`, `/`, `/match/:id`, `/add`, `/bets`, `/stats`, `/settings`
  - New component: `AdvancedPredictions.jsx` (score/BTS/corners/halves panel)
  - Custom hooks: `useMatchData`, `useMatchesList`

## External APIs Integrated

### ✅ API-Football (Direct api-sports.io)
- **Key**: `55e0cb8c1b4a4621899d8148ca4cafac` (Free plan, 100 req/day)
- **Endpoint**: `https://v3.football.api-sports.io`
- **Features**: fixtures, statistics, injuries, standings, team form, H2H
- **Note**: Free plan has limited season coverage (2022-2024 + selected current leagues)

### ✅ The Odds API
- **Key**: `ea902ad456619ef68a7d5ad30c061b31`
- **Features**: Real-time bookmaker odds (h2h, 14 active soccer leagues)

### ✅ ClubElo (free, no key required)
- **Endpoint**: `http://api.clubelo.com/{ClubName}`
- **Features**: Historical Elo ratings (1939-present) for European clubs
- **Used for**: home_elo, away_elo, elo_diff, elo_home_win_probability pillar

### ✅ Emergent LLM
- **Key**: `sk-emergent-932598b2d4a962a448`
- **Models**: Claude Sonnet 4.5, GPT-5.2, Gemini 3 Pro

## Advanced Predictions (NEW)

The `/api/matches/{id}/analyze` endpoint now returns `predictions` object with:

1. **Expected Goals (xG)** - estimated home/away/total
2. **Top 5 Correct Scores** - Poisson probability distribution
3. **BTS (Both Teams to Score)** - YES/NO probability + recommendation
4. **Over/Under Goals** - 1.5, 2.5, 3.5 lines
5. **Corner Kicks** - home/away/total + over 8.5/9.5/10.5
6. **Halves** - 1H xG, 2H xG, goal probability per half

## Personas
- **Analityk-typer (primary)** — szybko identyfikuje value bets z wieloma typami (1X2, BTS, corners, halves)
- **Tracker zakładów** — loguje typy z różnych rynków, śledzi ROI per typ

## ✅ Implemented (May 2026 - Latest)

### Core (Phase 0)
- ✅ JWT auth + bcrypt + admin seed
- ✅ 6 demo meczów auto-seedowanych
- ✅ Silnik statystyczny `compute_edge` (4-pillar oryginalny)
- ✅ Integracja 3 modeli LLM
- ✅ REST: matches CRUD + analyze + bets + stats + models + preferences
- ✅ UI w PL: Login, Register, Dashboard, Match Detail, Add Match, Bet Tracker, Stats, Settings
- ✅ data-testid registry
- ✅ The Odds API real-time import
- ✅ API-Football integration
- ✅ Dashboard filtry + value-bet alerts
- ✅ Code review fixes (security, hooks, refactoring)

### Phase 1 Advanced (NEW)
- ✅ **API-Football switched to Direct api-sports.io** (supports both direct and RapidAPI)
- ✅ **ClubElo integration** - real Elo ratings as new pillar
- ✅ **7-pillar compute_edge** - dynamic weighting, higher confidence
- ✅ **Confidence boost to 85%** when all pillars align
- ✅ **Poisson predictions module**:
  - Correct score (TOP 5)
  - BTS (Both Teams Score)
  - Over/Under 1.5/2.5/3.5
  - Rzuty rożne (home/away/total + over lines)
  - Gole 1H vs 2H
- ✅ **Frontend AdvancedPredictions component** - displays all new predictions
- ✅ **Elo section** in MatchDetail - shows ratings + win probability

## Test Results (May 30, 2026)
- ✅ Pytest: 26/27 passed (96.3%)
- ✅ Bayern vs Dortmund analysis with Elo: 84% confidence, edge +2.9% home
- ✅ Predicted score: 2:0 (16.3% prob)
- ✅ BTS: NIE 65.03%
- ✅ Corners: 10.2 total expected
- ✅ Goals halves: 1H xG=1.31, 2H xG=1.6
- ✅ All 3 LLMs working
- ✅ ClubElo returns real ratings for TOP European clubs

## API Keys Configuration (`/app/backend/.env`)
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="edge_ai_database"
JWT_SECRET="edge-ai-super-secret-jwt-key-2026-prod-v1"
API_FOOTBALL_KEY="55e0cb8c1b4a4621899d8148ca4cafac"
API_FOOTBALL_PROVIDER="direct"  # or "rapidapi"
ODDS_API_KEY="ea902ad456619ef68a7d5ad30c061b31"
EMERGENT_LLM_KEY="sk-emergent-932598b2d4a962a448"
ADMIN_EMAIL="admin@edgeai.pl"
ADMIN_PASSWORD="admin123"
```

## Backlog
### P0
- Phase 2: Understat xG scraping (better xG data than estimated)
- Phase 2: soccerdata library integration (FBref + Understat + 538)

### P1
- Live mode: in-play odds tracking
- CSV export of bet tracker
- Email/push notifications for value bets >= 5%
- Bet tracker filters by market type (1X2 / BTS / Corners / etc.)

### P2
- Mobile app
- Affiliate links to bookmakers (revenue)
- Multi-sport support (basketball, tennis)
