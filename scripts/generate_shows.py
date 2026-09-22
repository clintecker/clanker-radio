#!/usr/bin/env python3
"""Generate upcoming scheduled shows ahead of their air time.

Runs from a systemd timer. For every active schedule whose next air time is
within ``config.show_generation_lead_hours``, this ensures a generated_shows
row exists and drives it through ShowGenerator until it is READY (or has
exhausted ``config.show_generation_max_retries``).

The companion ``schedule_shows.py`` only *enqueues* READY shows at air time;
without this script nothing ever becomes READY.

Usage:
    generate_shows.py                # normal timer run
    generate_shows.py --schedule 1 --date 2026-09-23   # force one show now
"""
import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.show_generator import ShowGenerator
from ai_radio.show_models import GeneratedShow, ShowSchedule, ShowStatus
from ai_radio.show_repository import ShowRepository
from ai_radio.show_scheduling import air_dates_needing_generation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

RETRYABLE = {ShowStatus.PENDING, ShowStatus.SCRIPT_COMPLETE,
             ShowStatus.SCRIPT_FAILED, ShowStatus.AUDIO_FAILED}


def needs_generation(show: GeneratedShow, max_retries: int) -> bool:
    """Decide whether a show row should be (re)generated on this run."""
    if show.status == ShowStatus.READY:
        return False
    if show.status not in RETRYABLE:
        logger.warning(f"Show {show.id} has unknown status {show.status!r}; skipping")
        return False
    if show.status in (ShowStatus.SCRIPT_FAILED, ShowStatus.AUDIO_FAILED) \
            and show.retry_count >= max_retries:
        logger.error(
            f"Show {show.id} ({show.air_date}) gave up after {show.retry_count} retries: "
            f"{show.error_message}"
        )
        return False
    return True


def generate_one(repository: ShowRepository, generator: ShowGenerator,
                 schedule: ShowSchedule, air_date: date, max_retries: int) -> Optional[str]:
    """Generate a single show. Returns the final status, or None if skipped."""
    show = repository.get_or_create_show(schedule.id, air_date)
    if not needs_generation(show, max_retries):
        return None

    was_failed = show.status in (ShowStatus.SCRIPT_FAILED, ShowStatus.AUDIO_FAILED)
    if was_failed:
        # AUDIO_FAILED keeps its script; SCRIPT_FAILED restarts from research.
        resume_from = ShowStatus.SCRIPT_COMPLETE if show.status == ShowStatus.AUDIO_FAILED \
            else ShowStatus.PENDING
        repository.update_show_status(show.id, resume_from)
        show.status = resume_from
        logger.info(f"Retrying show {show.id} (attempt {show.retry_count + 1}/{max_retries})")

    logger.info(f"Generating '{schedule.name}' for {air_date} (show {show.id}, status {show.status})")
    generator.generate(schedule, show)

    final = repository.get_or_create_show(schedule.id, air_date)
    if final.status != ShowStatus.READY:
        attempts = repository.increment_retry_count(show.id)
        logger.error(f"Show {show.id} ended in {final.status} (attempt {attempts}/{max_retries}): "
                     f"{final.error_message}")
    else:
        logger.info(f"Show {show.id} READY with asset {final.asset_id}")
    return final.status


def run(now: Optional[datetime] = None, only_schedule: Optional[int] = None,
        only_date: Optional[date] = None) -> int:
    """Process every schedule. Returns number of shows that ended READY."""
    now = now or datetime.now(timezone.utc)
    repository = ShowRepository(str(config.paths.db_path))
    generator = ShowGenerator(repository)
    lead = timedelta(hours=config.show_generation_lead_hours)
    max_retries = config.show_generation_max_retries

    ready = 0
    for schedule in repository.get_active_schedules():
        if only_schedule is not None and schedule.id != only_schedule:
            continue
        dates = [only_date] if only_date else air_dates_needing_generation(schedule, now, lead)
        if not dates:
            logger.debug(f"'{schedule.name}': next airing is more than {lead} away")
        for air_date in dates:
            try:
                if generate_one(repository, generator, schedule, air_date, max_retries) == ShowStatus.READY:
                    ready += 1
            except Exception:
                # One broken schedule must not block the others.
                logger.exception(f"Unhandled error generating '{schedule.name}' for {air_date}")
    return ready


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schedule", type=int, help="Only process this schedule id")
    parser.add_argument("--date", type=date.fromisoformat, help="Force this air date (YYYY-MM-DD)")
    args = parser.parse_args()
    if args.date and args.schedule is None:
        parser.error("--date requires --schedule")
    try:
        ready = run(only_schedule=args.schedule, only_date=args.date)
        logger.info(f"Done: {ready} show(s) ready")
        return 0
    except Exception:
        logger.exception("Show generation run failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
