import argparse
import json
import os
import time

import requests
import schedule

from shushu_common import API_URL, connect_db


RANKING_PARAMS = {
    "type": "getRanking",
    "aid": 19,
    "bid": 0,
    "cid": 0,
    "did": 0,
    "gameType": "wzry",
}

# Defaults used when this file is started directly from an IDE.
# Use "once" for an immediate single update, or "schedule" for daily execution.
DEFAULT_RUN_MODE = "once"
DEFAULT_SCHEDULE_TIME = "07:30"

UPDATE_SQL = """
UPDATE lz_hero_rank
SET firstPlaceScore=%s,
    tenthPlaceScore=%s,
    fiftyScores=%s,
    lastPlaceScore=%s
WHERE pkId=%s
"""


def fetch_ranking_rows():
    response = requests.get(API_URL, params=RANKING_PARAMS, timeout=20)
    response.raise_for_status()
    return parse_ranking_rows(response.json())


def load_ranking_rows(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return parse_ranking_rows(json.load(file))


def parse_ranking_rows(payload):
    try:
        rows = payload["data"]["result"]["rows"]
    except (KeyError, TypeError) as exc:
        raise ValueError("API response is missing data.result.rows") from exc

    if not isinstance(rows, list):
        raise ValueError("API response data.result.rows must be a list")
    return rows


def build_update_values(rows):
    values = []
    skipped = []
    seen_hero_ids = set()

    for row in rows:
        hero_id = row.get("id")
        fight_power = row.get("fightPower")

        if hero_id is None or not isinstance(fight_power, list) or len(fight_power) < 4:
            skipped.append(hero_id)
            continue
        if hero_id in seen_hero_ids:
            raise ValueError(f"Duplicate hero id in API response: {hero_id}")

        seen_hero_ids.add(hero_id)
        values.append(
            (
                str(fight_power[0]),
                str(fight_power[1]),
                str(fight_power[2]),
                str(fight_power[3]),
                hero_id,
            )
        )

    return values, skipped


def update_latest_hero_rank(rows, dry_run=False):
    values, skipped = build_update_values(rows)
    if skipped:
        print(f"Skipped {len(skipped)} invalid rows, hero ids: {skipped}")

    if dry_run:
        print(f"Dry run: validated {len(values)} hero score records")
        return len(values), 0
    if not values:
        print("No valid hero score records to update")
        return 0, 0

    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            hero_ids = [value[-1] for value in values]
            placeholders = ",".join(["%s"] * len(hero_ids))
            cursor.execute(
                f"""
                SELECT heroId, pkId
                FROM lz_hero_rank
                WHERE heroId IN ({placeholders})
                ORDER BY heroId, createTime DESC, pkId DESC
                """,
                hero_ids,
            )

            latest_pk_ids = {}
            for record in cursor.fetchall():
                latest_pk_ids.setdefault(record["heroId"], record["pkId"])

            update_values = []
            missing_hero_ids = []
            for first, tenth, fifty, last, hero_id in values:
                pk_id = latest_pk_ids.get(hero_id)
                if pk_id is None:
                    missing_hero_ids.append(hero_id)
                else:
                    update_values.append((first, tenth, fifty, last, pk_id))

            if update_values:
                cursor.executemany(UPDATE_SQL, update_values)

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(
        f"Hero rank score update complete: input={len(values)}, "
        f"matched={len(update_values)}, not_found={len(missing_hero_ids)}"
    )
    if missing_hero_ids:
        print(f"No lz_hero_rank record for hero ids: {missing_hero_ids}")
    return len(update_values), len(missing_hero_ids)


def run_once(file_path=None, dry_run=False):
    rows = load_ranking_rows(file_path) if file_path else fetch_ranking_rows()
    return update_latest_hero_rank(rows, dry_run=dry_run)


def run_scheduler(run_at, file_path=None):
    schedule.every().day.at(run_at).do(run_once, file_path=file_path)
    print(f"Scheduled hero rank score update every day at {run_at}")
    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(
        description="Update the latest lz_hero_rank row for each API hero id."
    )
    parser.add_argument("--file", help="Read ranking response from a local JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not update DB")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Keep running and execute once every day (default behavior)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute immediately once instead of starting the scheduler",
    )
    parser.add_argument(
        "--at",
        default=os.getenv("HERO_RANK_UPDATE_TIME", DEFAULT_SCHEDULE_TIME),
        help="Daily run time in HH:MM format (default: 07:30)",
    )
    args = parser.parse_args()

    run_once_now = (
        args.once
        or args.dry_run
        or (not args.schedule and DEFAULT_RUN_MODE == "schedule")
    )
    if run_once_now:
        run_once(file_path=args.file, dry_run=args.dry_run)
    else:
        run_scheduler(args.at, file_path=args.file)


if __name__ == "__main__":
    main()
