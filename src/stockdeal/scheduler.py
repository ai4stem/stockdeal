"""APScheduler job registration.

All cron times below are Asia/Seoul. Jobs are stubbed; bind real callables
once each module is implemented.
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from stockdeal.config import get_settings
from stockdeal.logging import get_logger

log = get_logger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    s = get_settings()
    scheduler = AsyncIOScheduler(timezone=s.tz)

    # 09:00  pre-market brief (Telegram)
    scheduler.add_job(
        _noop, CronTrigger(hour=9, minute=0), id="premarket_brief"
    )

    # 15:35  end-of-day data sweep (DART daily summary, KRX investor net, etc.)
    scheduler.add_job(
        _noop, CronTrigger(hour=15, minute=35), id="eod_sweep"
    )

    # 18:00  US/EU news pull
    scheduler.add_job(
        _noop, CronTrigger(hour=18, minute=0), id="overseas_news"
    )

    # 21:00  Claude news analysis batch
    scheduler.add_job(
        _noop, CronTrigger(hour=21, minute=0), id="news_analysis"
    )

    # Daily email report
    scheduler.add_job(
        _noop, CronTrigger(hour=s.daily_report_hour, minute=0), id="daily_report"
    )

    # 23:00  Outcome labeling (D+5/D+20/D+60)
    scheduler.add_job(
        _noop, CronTrigger(hour=23, minute=0), id="outcome_eval"
    )

    # Sun 09:00  Weekly retrospective (Claude DEEP)
    scheduler.add_job(
        _noop, CronTrigger(day_of_week="sun", hour=9, minute=0), id="weekly_retro"
    )

    # Sun 10:00  DL model retrain
    scheduler.add_job(
        _noop, CronTrigger(day_of_week="sun", hour=10, minute=0), id="ml_retrain"
    )

    # 1st of month 06:00  Strategy param auto-tune
    scheduler.add_job(
        _noop, CronTrigger(day=1, hour=6, minute=0), id="param_tune"
    )

    return scheduler


async def _noop() -> None:
    log.info("scheduled_job_noop")
