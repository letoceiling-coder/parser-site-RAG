"""Celery tasks for scheduled crawling."""

import os

from celery import Celery
from celery.schedules import crontab

redis_password = os.getenv("REDIS_PASSWORD", "")
redis_host = os.getenv("REDIS_HOST", "redis")
broker_url = f"redis://:{redis_password}@{redis_host}:6379/0"

app = Celery("crawler", broker=broker_url, backend=broker_url)
app.conf.timezone = "Europe/Moscow"
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]


@app.task(name="crawl_source_task")
def crawl_source_task(source_id: str):
    import asyncio
    from crawler_engine import crawl_source, load_sources

    sources = load_sources()
    source = next((s for s in sources if s["id"] == source_id), None)
    if not source:
        return {"error": f"Source {source_id} not found"}

    return asyncio.run(crawl_source(source))


@app.task(name="crawl_all_sources")
def crawl_all_sources():
    import asyncio
    from crawler_engine import crawl_source, load_sources

    sources = load_sources()
    results = []
    for source in sources:
        result = asyncio.run(crawl_source(source))
        results.append(result)
    return results


def build_beat_schedule():
    from crawler_engine import load_sources

    schedule = {}
    for source in load_sources():
        cron = source.get("schedule")
        if cron:
            parts = cron.split()
            if len(parts) == 5:
                schedule[f"crawl_{source['id']}"] = {
                    "task": "crawl_source_task",
                    "schedule": crontab(
                        minute=parts[0],
                        hour=parts[1],
                        day_of_month=parts[2],
                        month_of_year=parts[3],
                        day_of_week=parts[4],
                    ),
                    "args": (source["id"],),
                }
    return schedule


app.conf.beat_schedule = build_beat_schedule()
