import requests
import datetime
import pymysql
import time
import json
import re
import warnings

warnings.filterwarnings("ignore")

# ========================
# 数据库连接
# ========================
def get_conn():
    DB_CONFIG = {
        "host": "192.168.1.126",
        "user": "cmdb",
        "password": "cmdb123456",
        "database": "dql",
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.Cursor,
        "autocommit": False,
    }
    return pymysql.connect(**DB_CONFIG)


# ========================
# 查询数据库最新时间
# ========================
def get_latest_time_from_db(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT time FROM dql_jinshi_market_news ORDER BY time DESC LIMIT 1"
        )
        row = cursor.fetchone()

    if not row:
        return None

    last_time = row[0]
    if isinstance(last_time, str):
        last_time = datetime.datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")

    return last_time


# ========================
# 获取 flash_newest.js 数据
# ========================
def fetch_flash_from_js():
    url = "https://www.jin10.com/flash_newest.js"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Referer": "https://www.jin10.com/",
        "Origin": "https://www.jin10.com",
    }

    resp = requests.get(url, headers=headers, timeout=(5, 10), verify=False)
    resp.raise_for_status()

    text = resp.text

    # ==========================
    # 只提取 time + content
    # ==========================
    pattern = re.compile(
        r'"time"\s*:\s*"(?P<time>[^"]+)"[\s\S]*?"content"\s*:\s*"(?P<content>.*?)"',
        re.S,
    )

    result = []
    for m in pattern.finditer(text):
        time_str = m.group("time")
        content = m.group("content")

        # 基础清洗
        content = (
            content.replace("\\n", "")
            .replace("\\\"", "\"")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("<br/>", "")
            .replace("<br />", "")
            .strip()
        )

        result.append(
            {
                "time": time_str,
                "data": {"content": content},
            }
        )

    if not result:
        raise ValueError("未解析到任何快讯数据")

    return result

# ========================
# 入库逻辑
# ========================
def insert_news_from_newest_js():
    conn = get_conn()

    try:
        db_latest_time = get_latest_time_from_db(conn)
        print(f"[INFO] 数据库最新时间：{db_latest_time}")

        data_list = fetch_flash_from_js()
        new_count = 0

        with conn.cursor() as cursor:
            for item in data_list:
                time_str = item.get("time")
                content = item.get("data", {}).get("content", "")

                if not time_str or not content:
                    continue

                # 内容清洗
                content = (
                    content.replace("<b>", "")
                    .replace("</b>", "")
                    .replace("<br/>", "")
                    .replace("<br />", "")
                    .strip()
                )

                item_time = datetime.datetime.strptime(
                    time_str, "%Y-%m-%d %H:%M:%S"
                )

                # 已存在的数据不插
                if db_latest_time and item_time <= db_latest_time:
                    continue

                sql = """
                    INSERT INTO dql_jinshi_market_news (time, content)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        content = VALUES(content),
                        updateTime = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (time_str, content))
                new_count += 1

        conn.commit()
        print("content:{}".format(content))
        print(f"[SUCCESS] 本次新增 {new_count} 条快讯")

    except Exception as e:
        conn.rollback()
        print("[ERROR] 本轮更新失败：", e)

    finally:
        conn.close()


# ========================
# 主循环（5 分钟一次）
# ========================
def run_spider():
    print("🚀 金十快讯同步服务已启动")
    while True:
        insert_news_from_newest_js()
        print("[WAIT] 5 分钟后继续...\n")
        time.sleep(300)


if __name__ == "__main__":
    run_spider()
