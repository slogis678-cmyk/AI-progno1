# Edge AI — Product Requirements Document

## Original problem statement
"Stwórz Model AI który wykryła przewagę statystyczną opartą na stabilnych i powtarzalnych wzorcach meczowych. Uwzględnij: tempo gry, mikrotrendy kursów, reakcję zespołów, dane historyczne."

(EN: Build an AI model that detects a statistical edge based on stable, repeatable match patterns. Include: game tempo, odds micro-trends, team reactions, historical data.)

## User choices (Feb 2026)
- Sport: Football
- Data: External API + manual entry (started with demo data; API keys deferred)
- AI: Multi-LLM via Emergent Universal Key — Claude Sonnet 4.5 + GPT-5.2 + Gemini 3 Pro (user picks per analysis)
- Features: dashboard + AI predictions + deep analysis + history + bet tracking + stats — all delivered in MVP
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

## Implemented (2026-02 — initial release)
- ✅ JWT auth + bcrypt + admin seed
- ✅ 6 demo meczów auto-seedowanych dla każdego nowego użytkownika
- ✅ Silnik statystyczny `compute_edge` (Python, w ai_analyzer.py)
- ✅ Integracja 3 modeli LLM przez Emergent Universal Key
- ✅ REST: matches CRUD + analyze + bets + stats + models + preferences
- ✅ UI w PL: Login (split screen, financial data art), Register, Dashboard, Match Detail, Add Match, Bet Tracker, Stats, Settings
- ✅ data-testid registry centralised
- ✅ E2E tests passed (backend 95%, frontend 92%)

## Implemented (2026-02 — iteration 2)
- ✅ **Real-time import** z The Odds API (`/api/external/import/odds-api`, klucz w .env, dynamiczna lista aktywnych lig)
- ✅ **API-Football integration** (`/api/external/import/api-football`) – działa kod, klucz wymaga subskrypcji konkretnej API na RapidAPI
- ✅ **Dashboard filtry**: search + league dropdown + min-edge slider (`-5%` … `+15%`)
- ✅ **Alerts banner** dla value-bet ≥ 5% z dismissem do localStorage
- ✅ **Historia analiz** w widoku MatchDetail – tabela wszystkich wcześniejszych przebiegów AI z timestampem, modelem, werdyktem, pewnością
- ✅ Fix recharts ResponsiveContainer (explicit inline width/height) – brak warning'ów w konsoli
- ✅ E2E iteration 2: backend 100% (5/5 new), frontend 95%, brak bugów

## Backlog
### P0 / Next iteration
- Integracja API-Football (RapidAPI) i The Odds API — pobieranie meczów + kursów na żywo (klucze od użytkownika).
- Automatyczne odświeżanie kursów (refresh trendów co X min).

### P1
- Lista historycznych analiz na ekranie meczu (`/api/matches/{id}/analyses` jest gotowe — UI do dodania).
- Filtrowanie dashboardu po edge > X% i lidze.
- Eksport bet trackera do CSV.
- Push/e-mail alert przy edge > 5%.

### P2
- Tryb live (in-play): pobieranie zmian kursów w trakcie meczu.
- Sportbook integration via affiliate links (potencjalny revenue stream).
- Mobile-first refactor pages do widoku karty.

## Next action items
1. Zebrać klucze API-Football + The Odds API od użytkownika i podpiąć real-time pobieranie.
2. Dodać UI listy historycznych analiz w `MatchDetail`.
3. Drobne UX: tooltip wyjaśniający różnicę "edge" vs "predicted winner".
