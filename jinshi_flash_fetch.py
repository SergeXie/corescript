import datetime
import json
import os
import re
import sys
import time
import warnings

import pymysql
import requests
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

class Jin10FlashFetcher:
    """金十快讯数据抓取与同步服务

    自动抓取金十快讯 JS 接口并同步入库。只对外暴露 run() 方法。
    """

    def __init__(self):
        # 从 .env 文件中动态读取数据库配置
        self._db_config = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_DATABASE", "dql"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.Cursor,
            "autocommit": False,
        }

    # ================= 内部私有方法 =================

    def _get_conn(self):
        """获取数据库连接"""
        return pymysql.connect(**self._db_config)

    def _get_latest_time_from_db(self, conn):
        """查询数据库中已存在的最新快讯时间"""
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT time FROM dql_jinshi_market_news ORDER BY time DESC LIMIT 1"
            )
            row = cursor.fetchone()

        if not row:
            return None

        last_time = row[0]
        if isinstance(last_time, str):
            last_time = datetime.datetime.strptime(
                last_time, "%Y-%m-%d %H:%M:%S"
            )

        return last_time

    def _fetch_flash_from_js(self):
        """请求 flash_newest.js 并解析快讯内容"""
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

        # 正则提取 time + content
        pattern = re.compile(
            r'"time"\s*:\s*"(?P<time>[^"]+)"[\s\S]*?"content"\s*:\s*"(?P<content>.*?)"',
            re.S,
        )

        result = []
        for m in pattern.finditer(text):
            time_str = m.group("time")
            content = m.group("content")

            # 基础文本清洗
            content = (
                content.replace("\\n", "")
                .replace('\\"', '"')
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

    def _insert_news_from_newest_js(self):
        """把最新抓取到的快讯同步至数据库"""
        conn = self._get_conn()
        last_printed_content = ""

        try:
            db_latest_time = self._get_latest_time_from_db(conn)
            print(f"[INFO] 数据库最新时间：{db_latest_time}")

            data_list = self._fetch_flash_from_js()
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

                    # 增量去重比对
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
                    last_printed_content = content

            conn.commit()
            if last_printed_content:
                print(f"最新内容 preview: {last_printed_content[:50]}...")
            print(f"[SUCCESS] 本次新增 {new_count} 条快讯")

        except Exception as e:
            conn.rollback()
            print("[ERROR] 本轮更新失败：", e)

        finally:
            conn.close()

    # ================= 唯一对外暴露的方法 =================

    def run(self, interval_seconds: int = 300):
        """启动快讯同步循环服务

        :param interval_seconds: 轮询间隔秒数，默认 300 秒（5 分钟）
        """
        print("🚀 金十快讯同步服务已启动")
        while True:
            self._insert_news_from_newest_js()
            print(f"[WAIT] {interval_seconds} 秒后继续...\n")
            time.sleep(interval_seconds)
