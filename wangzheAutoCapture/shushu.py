import json
import time

import requests
import schedule

from shushu_common import API_URL, connect_db, get_ranking_rows


def update_gradient_score():
    print("Start updating lz_hero gradient scores")
    data_list = get_ranking_rows()
    conn = connect_db()

    try:
        with conn.cursor() as cursor:
            for data in data_list:
                hero_id = data["id"]
                gradient_score = data["extraData"]["gradientScore"]

                sql = """
                UPDATE lz_hero
                SET gradientScore=%s
                WHERE id=%s
                """

                cursor.execute(sql, (gradient_score, hero_id))
                print(f"Updated lz_hero {hero_id} -> gradientScore={gradient_score}")

        conn.commit()
        print("lz_hero gradient score update complete")
    finally:
        conn.close()


def upsert_hero_ranking():
    print("Start upserting lz_shushu_hero_ranking")
    data_list = get_ranking_rows()
    conn = connect_db()

    try:
        with conn.cursor() as cursor:
            for data in data_list:
                hero_id = data["id"]
                img = data["img"]
                name = data["name"]
                trend = data["trend"]
                skill = json.dumps(data["skill"], ensure_ascii=False)
                gradient_score = data["extraData"]["gradientScore"]
                avg_new_score = data["extraData"]["avgNewScore"]

                sql = """
                INSERT INTO lz_shushu_hero_ranking
                (heroId, name, img, trend, skill, gradientScore, avgNewScore)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                img = VALUES(img),
                trend = VALUES(trend),
                skill = VALUES(skill),
                gradientScore = VALUES(gradientScore),
                avgNewScore = VALUES(avgNewScore)
                """

                cursor.execute(
                    sql,
                    (
                        hero_id,
                        name,
                        img,
                        trend,
                        skill,
                        gradient_score,
                        avg_new_score,
                    ),
                )
                print(
                    f"Upserted ranking {hero_id} -> "
                    f"gradientScore={gradient_score} avgNewScore={avg_new_score}"
                )

        conn.commit()
        print("lz_shushu_hero_ranking upsert complete")
    finally:
        conn.close()


def update_hero_performance():
    print("Start updating hero performance")

    db = connect_db(cursorclass=None)
    cursor = db.cursor()

    sql = """
    SELECT pkId,name
    FROM lz_shushu_hero_ranking
    """

    try:
        cursor.execute(sql)
        heroes = cursor.fetchall()

        for hero in heroes:
            pk_id = hero[0]
            name = hero[1]

            try:
                params = {
                    "type": "getSearch",
                }

                data = {
                    "q": name,
                }

                res = requests.post(API_URL, params=params, data=data, timeout=10)
                res.raise_for_status()

                result = res.json()
                performance = result["data"]["cardInfo"]["performance"][0]
                performance_json = json.dumps(performance, ensure_ascii=False)

                update_sql = """
                UPDATE lz_shushu_hero_ranking
                SET performance=%s
                WHERE pkId=%s
                """

                cursor.execute(update_sql, (performance_json, pk_id))
                db.commit()

                print(f"Updated performance: {name}")
                time.sleep(0.5)

            except Exception as e:
                print(f"Failed performance update: {name}", e)
    finally:
        cursor.close()
        db.close()

    print("Hero performance update complete")


def register_jobs():
    schedule.every().day.at("07:00").do(update_gradient_score)
    schedule.every().day.at("07:20").do(upsert_hero_ranking)
    schedule.every().day.at("07:40").do(update_hero_performance)


def run_scheduler():
    register_jobs()

    print("Scheduled jobs:")
    print("  07:00 update lz_hero.gradientScore")
    print("  07:20 upsert lz_shushu_hero_ranking")
    print("  07:40 update lz_shushu_hero_ranking.performance")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    run_scheduler()
