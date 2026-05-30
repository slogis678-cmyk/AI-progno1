# Edge AI — Product Requirements Document

## Original problem statement
"Stwórz Model AI który wykryła przewagę statystyczną opartą na stabilnych i powtarzalnych wzorcach meczowych. Uwzględnij: tempo gry, mikrotrendy kursów, reakcję zespołów, dane historyczne."

(EN: Build an AI model that detects a statistical edge based on stable, repeatable match patterns. Include: game tempo, odds micro-trends, team reactions, historical data.)

## User choices (May 2026 - UPDATED)
- Sport: Football
- Data: External API + manual entry (API keys configured and working)
- AI: Multi-LLM via Emergent Universal Key — Claude Sonnet 4.5 + GPT-5.2 + Gemini 3 Pro (user picks per analysis)
- Features: dashboard + AI predictions + deep analysis + history + bet tracking + stats + import — all delivered in MVP
- Auth: JWT email/password
- UI language: Polish
- Aesthetic: Bloomberg-terminal / dark fintech (Chivo + IBM Plex Sans/Mono)

## Architecture
- **Backend** FastAPI + Motor (MongoDB), JWT auth (bcrypt + PyJWT), Emergent LLM library
  - `compute_edge()` — 4-pillar statistical engine: tempo (28%), odds micro-trend (18%), reaction home (22%) / away (12%), H2H (20%)
  - `llm_analyze_match()` — sends signals + match data to selected LLM, returns structured Polish JSON
  - Collections: `users`, `matches`, `analyses`, `bets`
- **Frontend** React 19 + react-router-dom 7 + Tailwind + shadcn/ui + recharts + Phosphor icons
  - `/login`, `/register`, `/`, `/match/:id`, `/add`, `/bets`, `/stats`, `/settings`

## Personas
- **Analityk-typer (primary)** — chce szybko zidentyfikować mecze z wartościową przewagą i mieć po jednym kliknięciu tezę LLM-a.
- **Tracker zakładów** — loguje swoje typy i obserwuje ROI / hit-rate.

## Core requirements (static)
1. Wykrywanie przewagi w oparciu o 4 filary: tempo, mikrotrendy, reakcja, historia.
2. Wybieralny silnik LLM (Claude / GPT / Gemini) do interpretacji sygnałów.
3. Manualne wprowadzanie meczów (kursy 1X2 + tempo + forma + H2H).
4. JWT-owe konta z auto-seedem demo dla każdego nowego użytkownika.
5. Tracker zakładów + statystyki ROI, hit-rate, ROI per liga, AI accuracy.
6. Import meczów z zewnętrznych API (The Odds API, API-Football).

## ✅ Implemented (May 2026 - CURRENT STATUS)
- ✅ JWT auth + bcrypt + admin seed
- ✅ 6 demo meczów auto-seedowanych dla każdego nowego użytkownika
- ✅ Silnik statystyczny `compute_edge` (Python, w ai_analyzer.py)
- ✅ Integracja 3 modeli LLM przez Emergent Universal Key (WSZYSTKIE DZIAŁAJĄ)
  - ✅ Claude Sonnet 4.5 - tested and working
  - ✅ GPT-5.2 - tested and working
  - ✅ Gemini 3 Pro - tested and working
- ✅ REST: matches CRUD + analyze + bets + stats + models + preferences
- ✅ UI w PL: Login, Register, Dashboard, Match Detail, Add Match, Bet Tracker, Stats, Settings
- ✅ data-testid registry centralised
- ✅ **Real-time import** z The Odds API (`/api/external/import/odds-api`) - WORKING
- ✅ **API-Football integration** (`/api/external/import/api-football`) - WORKING
- ✅ **Dashboard filtry**: search + league dropdown + min-edge slider
- ✅ **Alerts banner** dla value-bet ≥ 5% z dismissem do localStorage
- ✅ **Historia analiz** w widoku MatchDetail
- ✅ All API connections fixed and tested:
  - API-Football (RapidAPI): fc38af146amsh345885558a4706ap1f235ejsn1d2252bb0361
  - The Odds API: ea902ad456619ef68a7d5ad30c061b31
  - Emergent LLM Key: sk-emergent-932598b2d4a962a448

## 🎯 Test Results (May 30, 2026)

### Backend Tests
- ✅ Server running on http://0.0.0.0:8001
- ✅ MongoDB connection successful
- ✅ Admin user seeded: admin@edgeai.pl / admin123
- ✅ JWT authentication working
- ✅ 6 demo matches loaded
- ✅ All 3 AI models tested and working:
  - Claude Sonnet 4.5: verdict="home", confidence=78%
  - GPT-5.2: verdict="away", confidence=73%
  - Gemini 3 Pro: verdict="home", confidence=85%
- ✅ The Odds API: 14 leagues fetched
- ✅ API-Football: Integration ready

### Frontend Tests
- ✅ Login page: Working perfectly
- ✅ Dashboard: All features working (filters, alerts, match list, edge calculations)
- ✅ Match Detail: Complete with AI analysis, charts, 4 pillars breakdown
- ✅ Add Match: Full form with all fields
- ✅ Bet Tracker: Working (empty state shown correctly)
- ✅ Stats: Working (empty state shown correctly)
- ✅ Settings: User preferences and model selection working
- ✅ Import Dialog: Both API sources available

## Next action items
1. ✅ COMPLETED: All API connections fixed
2. ✅ COMPLETED: All AI models tested and working
3. User can start using the application to:
   - Import matches from external APIs
   - Analyze matches with AI
   - Track bets and view statistics
   - Add custom matches manually

## API Keys Configuration
All keys are stored in `/app/backend/.env`:
- MONGO_URL="mongodb://localhost:27017"
- DB_NAME="edge_ai_database"
- JWT_SECRET="edge-ai-super-secret-jwt-key-2026-prod-v1"
- API_FOOTBALL_KEY="fc38af146amsh345885558a4706ap1f235ejsn1d2252bb0361"
- ODDS_API_KEY="ea902ad456619ef68a7d5ad30c061b31"
- EMERGENT_LLM_KEY="sk-emergent-932598b2d4a962a448"
- ADMIN_EMAIL="admin@edgeai.pl"
- ADMIN_PASSWORD="admin123"
