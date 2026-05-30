"""Background scheduler to refresh odds for imported matches.

Strategy:
  - Every REFRESH_MINUTES (env, default 30) we look at all matches whose
    `external_id` starts with `oddsapi:` and whose `kickoff` is in the
    next 7 days.
  - We group those by `sport_key`, hit The Odds API once per sport, then
    update `odds` + append a new entry to `odds_history` for each matched
    event. Only sports with at least one tracked, soon-to-kickoff match are
    refreshed, so we don't burn quota on idle leagues.

Last run status is exposed via /api/external/refresh-status.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from external_data import fetch_odds_api_event_odds

logger = logging.getLogger("edge-ai.scheduler")

_last_run = {
    "ts": None,
    "ok": None,
    "updated": 0,
    "sports_polled": 0,
    "error": None,
}


def get_last_run_status() -> dict:
    return dict(_last_run)


async def refresh_odds_history(db) -> dict:
    """Refresh odds for tracked, soon-to-kickoff matches from The Odds API."""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)
    cursor = db.matches.find(
        {
            "external_id": {"$regex": "^oddsapi:"},
            "kickoff": {"$gte": now.isoformat(), "$lte": horizon.isoformat()},
            "status": "upcoming",
        },
        {"_id": 0, "id": 1, "external_id": 1, "sport_key": 1, "odds": 1, "odds_history": 1},
    )
    by_sport: dict[str, list[dict]] = {}
    async for m in cursor:
        sk = m.get("sport_key")
        if not sk:
            continue
        by_sport.setdefault(sk, []).append(m)

    updated = 0
    for sport_key, matches in by_sport.items():
        try:
            odds_by_event = await fetch_odds_api_event_odds(sport_key)
        except Exception as e:
            logger.warning("refresh: odds api failed for %s: %s", sport_key, e)
            continue
        ts = datetime.now(timezone.utc).isoformat()
        for m in matches:
            event_id = m["external_id"].split(":", 1)[1] if ":" in m["external_id"] else None
            if not event_id:
                continue
            new_odds = odds_by_event.get(event_id)
            if not new_odds:
                continue
            old = m.get("odds") or {}
            # skip if odds didn't change
            if (
                abs(new_odds["home"] - old.get("home", 0)) < 0.01
                and abs(new_odds["draw"] - old.get("draw", 0)) < 0.01
                and abs(new_odds["away"] - old.get("away", 0)) < 0.01
            ):
                continue
            history = list(m.get("odds_history") or [])
            history.append({"ts": ts, **new_odds})
            history = history[-50:]  # cap history
            await db.matches.update_one(
                {"id": m["id"]},
                {"$set": {"odds": new_odds, "odds_history": history}},
            )
            updated += 1

    _last_run.update(
        ts=datetime.now(timezone.utc).isoformat(),
        ok=True,
        updated=updated,
        sports_polled=len(by_sport),
        error=None,
    )
    logger.info("refresh: %d matches updated across %d sports", updated, len(by_sport))
    return get_last_run_status()


def _wrap(db):
    async def _job():
        try:
            await refresh_odds_history(db)
        except Exception as e:
            _last_run.update(
                ts=datetime.now(timezone.utc).isoformat(),
                ok=False,
                error=str(e),
            )
            logger.exception("scheduled refresh failed")
    return _job


_scheduler: AsyncIOScheduler | None = None


def start_scheduler(db) -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    minutes = int(os.environ.get("REFRESH_MINUTES", "30"))
    sch = AsyncIOScheduler(timezone="UTC")
    sch.add_job(_wrap(db), "interval", minutes=minutes, id="refresh_odds", next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30))
    sch.start()
    _scheduler = sch
    logger.info("scheduler started: every %d minutes", minutes)
    return sch


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
