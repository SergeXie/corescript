import os
import random
import time
from datetime import datetime, timedelta

import pymysql
import requests
import schedule


class EconomicNewsScheduler:
    """财经日历爬虫与数据调度器"""

    def __init__(self):
        # 从 .env 中读取配置，如果读取不到则使用默认保底值
        self._db_config = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_DATABASE", "dql"),
        }
        self._pcc = os.getenv("PCC_TOKEN", "")

        self._tag_rules = {
            "黄金": ["美国", "非农就业"],
            "原油": ["美国", "石油"],
        }
        self._ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]

    def _get_tag_by_name(self, name: str) -> str | None:
        if not name:
            return None
        for tag, keywords in self._tag_rules.items():
            if all(kw in name for kw in keywords):
                return tag
        return None

    def _execute_one(self, sql, params):
        conn = pymysql.connect(**self._db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
        except Exception as e:
            print("SQL执行失败:", e)
            conn.rollback()
        finally:
            conn.close()

    def _fetch_one(self, sql, params):
        conn = pymysql.connect(**self._db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        except Exception as e:
            print(f"[fetch_one ERROR] {e}\nSQL: {sql}\nParams: {params}")
            return None
        finally:
            conn.close()

    def _get_latest_time_from_db(self, conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT time FROM dql_jinshi_economic_news ORDER BY time DESC LIMIT 1"
        )
        result = cursor.fetchone()
        cursor.close()

        if not result:
            return None

        last = result[0]
        print(f"last:{last}")

        if isinstance(last, datetime):
            return last

        last = str(last).strip()
        try:
            if len(last) == 10:
                return datetime.strptime(last, "%Y-%m-%d")
            elif len(last) == 16:
                return datetime.strptime(last, "%Y-%m-%d %H:%M")
            elif len(last) == 19:
                return datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
            else:
                raise ValueError(f"未知时间格式: {last}")
        except Exception as e:
            print("时间解析失败：", e)
            return None

    def _apply_tag_relation(self, news_id, name):
        tag_name = self._get_tag_by_name(name)
        if not tag_name:
            return

        sql_tag = "SELECT pkId FROM dql_calendar_tag WHERE tagName=%s"
        tag_row = self._fetch_one(sql_tag, (tag_name,))
        if not tag_row:
            print(f"警告：标签表中找不到标签 {tag_name}，请先插入 dql_tag")
            return

        tag_id = tag_row[0]
        sql_check = "SELECT pkId FROM dql_economic_news_tag_relation WHERE newsId=%s AND tagId=%s"
        if self._fetch_one(sql_check, (news_id, tag_id)):
            print("已有，不重复插入")
            return

        sql_insert = "INSERT INTO dql_economic_news_tag_relation (newsId, tagId) VALUES (%s, %s)"
        self._execute_one(sql_insert, (news_id, tag_id))
        print(f"标签关系已插入: newsId={news_id}, tagId={tag_id} ({tag_name})")

    def _insert_news(self, name, time_, preValue, pubValue, estimateValue):
        sql = """
              INSERT INTO dql_jinshi_economic_news
                  (time, name, prevValue, expectValue, publishValue)
              VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY \
              UPDATE \
                  prevValue = \
              VALUES (prevValue), expectValue = \
              VALUES (expectValue), publishValue = \
              VALUES (publishValue), updateTime = CURRENT_TIMESTAMP \
              """
        params = (time_, name, preValue, estimateValue, pubValue)
        self._execute_one(sql, params)

        sql_get_id = "SELECT pkId FROM dql_jinshi_economic_news WHERE time=%s AND name=%s LIMIT 1"
        row = self._fetch_one(sql_get_id, (time_, name))
        if not row:
            print("严重错误：插入后找不到记录，请检查唯一索引！")
            return

        self._apply_tag_relation(row[0], name)
        print(
            f"插入成功: {name} | {time_} | pre={preValue}, pub={pubValue}, est={estimateValue}"
        )

    def _get_calendar_by_date(self, target_date):
        url = "https://centerapi.fx168api.com/cms/api/economic/calendar/getCalendarList"

        # 动态读取最新的 _pcc
        current_pcc = os.getenv("PCC_TOKEN", self._pcc)

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9",
            "origin": "https://www.fx168news.com",
            "referer": "https://www.fx168news.com/",
            "site-channel": "001",
            "_pcc": current_pcc,
            "user-agent": random.choice(self._ua_list),
        }

        params = {
            "pageSize": "20",
            "isPaging": "0",
            "siteCode": "001",
            "pubDateTimeStart": f"{target_date} 00:00:00",
            "pubDateTimeEnd": f"{target_date} 23:59:59",
        }

        delay = round(random.uniform(1.2, 4.0), 2)
        print(f"[{target_date}] 等待 {delay}s …")
        time.sleep(delay)

        try:
            res = requests.get(
                url, headers=headers, params=params, timeout=10, verify=False
            )
            if res.status_code == 200 and res.content != b"":
                data_json = res.json()
                items = data_json.get("data", {}).get("items", [])
                if not items:
                    print(f"[{target_date}] 无数据")
                    return

                for data in items:
                    name = data["countryName"] + data["calendarName"]
                    time_ = target_date + " " + data["pubTime"]
                    self._insert_news(
                        name,
                        time_,
                        data.get("preValue", 0),
                        data.get("pubValue", 0),
                        data.get("estimateValue", 0),
                    )
            else:
                print(f"[{target_date}] 接口返回为空或错误，请检查 _pcc 参数是否过期。")
        except Exception as e:
            print(f"[{target_date}] 请求失败：{e}")

    def _run_from_2015(self):
        try:
            connect = pymysql.connect(**self._db_config)
            db_latest_time = self._get_latest_time_from_db(connect)
            connect.close()

            if not db_latest_time:
                db_latest_time = datetime(2015, 1, 1)

            print(f"数据库最新时间：{db_latest_time}")
            current = datetime(
                db_latest_time.year, db_latest_time.month, db_latest_time.day
            )
            end_date = datetime.now()

            while current <= end_date:
                date_str = current.strftime("%Y-%m-%d")
                print(f"正在处理: {date_str}")
                self._get_calendar_by_date(date_str)
                current += timedelta(days=1)
        except Exception as e:
            print(f"调度任务异常: {e}")

    # ================= 对外暴露的 run 方法 =================

    def run(self):
        print("开始同步数据...")
        self._run_from_2015()

        schedule.clear()
        schedule.every().day.at("01:00").do(self._run_from_2015)
        schedule.every(3).hours.do(self._run_from_2015)
        print("已启动定时任务：每天 01:00 及每 3 小时自动同步")

        while True:
            schedule.run_pending()
            time.sleep(60)