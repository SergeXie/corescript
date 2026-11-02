import requests
import random
import time
from datetime import datetime, timedelta
import pymysql
import schedule
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 网站
# https://www.fx168news.com/calendar

DB_CONFIG = {
    'host': '192.168.1.126',
    'user': 'cmdb',
    'password': 'cmdb123456',
    'database': 'dql'
}


TAG_RULES = {
    "黄金": ["美国", "非农就业"],
    "原油": ["美国", "石油"],
}


def get_tag_by_name(name: str) -> str | None:
    if not name:
        return None

    for tag, keywords in TAG_RULES.items():
        if all(kw in name for kw in keywords):
            return tag

    return None


def execute_one(sql, params):
    """执行单条 SQL"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        print("SQL执行失败:", e)
        conn.rollback()
    finally:
        conn.close()


def fetch_one(sql, params):
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return row
    except Exception as e:
        print(f"[fetch_one ERROR] {e}\nSQL: {sql}\nParams: {params}")
        return None
    finally:
        conn.close()


def get_latest_time_from_db(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT time FROM dql_jinshi_economic_news ORDER BY time DESC LIMIT 1")
    result = cursor.fetchone()
    cursor.close()

    if not result:
        return None

    last = result[0]

    print("last:{}".format(last))

    # 1. 如果是 datetime 类型，直接返回
    if isinstance(last, datetime):
        return last

    # 2. 去除空格
    last = last.strip()

    # 3. 根据长度判断格式
    try:
        if len(last) == 10:  # 只有 YYYY-MM-DD
            return datetime.strptime(last, "%Y-%m-%d")
        elif len(last) == 16:  # YYYY-MM-DD HH:MM
            return datetime.strptime(last, "%Y-%m-%d %H:%M")
        elif len(last) == 19:  # YYYY-MM-DD HH:MM:SS
            return datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        else:
            raise ValueError("未知时间格式: {}".format(last))
    except Exception as e:
        print("时间解析失败：", e)
        return None

def apply_tag_relation(news_id, name):
    # 1. 根据名称匹配标签名称
    tag_name = get_tag_by_name(name)
    if not tag_name:
        return  # 无标签

    # 2. 根据 tagName 查 tagId
    sql_tag = "SELECT pkId FROM dql_calendar_tag WHERE tagName=%s"
    tag_row = fetch_one(sql_tag, (tag_name,))
    if not tag_row:
        print(f"警告：标签表中找不到标签 {tag_name}，请先插入 dql_tag")
        return

    # !!! 关键修复 !!!
    tag_id = tag_row[0]

    # 3. 检查是否已存在关系
    sql_check = """
        SELECT pkId FROM dql_economic_news_tag_relation
        WHERE newsId=%s AND tagId=%s
    """
    exist = fetch_one(sql_check, (news_id, tag_id))
    if exist:
        print("已有，不重复插入")
        return  # 已有，不重复插入

    # 4. 插入关系表
    sql_insert = """
        INSERT INTO dql_economic_news_tag_relation (newsId, tagId)
        VALUES (%s, %s)
    """
    execute_one(sql_insert, (news_id, tag_id))

    print(f"标签关系已插入: newsId={news_id}, tagId={tag_id} ({tag_name})")


def insert_news(name, time_, preValue, pubValue, estimateValue):

    # 1. 先插入 / 更新日历数据
    sql = """
        INSERT INTO dql_jinshi_economic_news
        (time, name, prevValue, expectValue, publishValue)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            prevValue = VALUES(prevValue),
            expectValue = VALUES(expectValue),
            publishValue = VALUES(publishValue),
            updateTime = CURRENT_TIMESTAMP
    """

    params = (time_, name, preValue, estimateValue, pubValue)
    execute_one(sql, params)

    # 2. 查询这条数据的 pkId（新闻主键）
    sql_get_id = """
        SELECT pkId 
        FROM dql_jinshi_economic_news
        WHERE time=%s AND name=%s
        LIMIT 1
    """
    row = fetch_one(sql_get_id, (time_, name))
    if not row:
        print("严重错误：插入后找不到记录，请检查唯一索引！")
        return

    news_id = row[0]
    #
    # # 3. 调用标签关联逻辑
    apply_tag_relation(news_id, name)

    print(f"插入成功: {name} | {time_} | pre={preValue}, pub={pubValue}, est={estimateValue}")


def get_calendar_by_date(target_date):
    """请求某一天的数据"""

    url = "https://centerapi.fx168api.com/cms/api/economic/calendar/getCalendarList"

    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "origin": "https://www.fx168news.com",
        "referer": "https://www.fx168news.com/",
        "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "sec-fetch-storage-access": "active",
        "site-channel": "001",
        "_pcc": "KEhXMYmHUuVrPxeaBAeo1EOOr/pm0mWYEeI7PiTRgxGhs30qXseXJ0rctIWVe5Zlw1+9zBxKqVdN2txW7w8Yveva8kXEgBo6xzBS2ZyfcU/AOODfJnHj46QUvy8gmyoOsAFxEKfkhWLQk7H376ImweuumY8ld3eS/P0WiSIPe7w=",
        "user-agent": random.choice(ua_list),
    }

    date_start = f"{target_date} 00:00:00"
    date_end = f"{target_date} 23:59:59"

    params = {
        "calendarName": "",
        "star": "",
        "countryCode": "",
        "starList": "",
        "countryCodeList": "",
        "pageSize": "20",
        "orderCol": "",
        "isPaging": "0",
        "siteCode": "001",
        "pubDateTimeStart": date_start,
        "pubDateTimeEnd": date_end,
    }

    # 随机延迟（防爬）
    delay = round(random.uniform(1.2, 4.0), 2)
    print(f"[{target_date}] 等待 {delay}s …")
    time.sleep(delay)

    # 自动重试
    for retry in range(1):
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10,verify=False)
            print("res:{}".format(res.content))
            if not res.content == '':
                print("无数据！！！！！！！！！！！ 接口请求请新替换_pcc参数")
            if res.status_code == 200:
                print(f"[{target_date}] 请求成功！")
                data_json = res.json()
                print("data_json:{}".format(data_json))
                if not data_json["data"]["items"]:
                    print(f"[{target_date}] 无数据")
                    return

                for data in data_json["data"]["items"]:
                    countryName = data["countryName"]
                    pubTime = data["pubTime"]
                    calendarName = data["calendarName"]
                    preValue = data.get("preValue", 0)  # 前值
                    pubValue = data.get("pubValue", 0)  # 公布值
                    estimateValue = data.get("estimateValue", 0)  # 预测值

                    name = countryName + calendarName
                    time_ = target_date + " " + pubTime

                    insert_news(name, time_, preValue, pubValue, estimateValue)

        except Exception as e:
            print(f"[{target_date}] 请求失败：{e}")

        time.sleep(round(random.uniform(1.0, 2.0), 2))

    return None


def run_from_2015():

    connect = pymysql.connect(**DB_CONFIG)

    db_latest_time = get_latest_time_from_db(connect)
    print(f"数据库最新时间：{db_latest_time}")
    # """从 2015-01-01 开始到今天，逐天请求"""
    start_date = datetime(db_latest_time.year, db_latest_time.month, db_latest_time.day)
    end_date = datetime.now()

    current = start_date
    # get_calendar_by_date(date_str)
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        print("date_str:{}".format(date_str))

        get_calendar_by_date(date_str)

        # 下一天
        current += timedelta(days=1)


# --- 每天凌晨 1 点执行 ---
schedule.every().day.at("01:00").do(run_from_2015)
schedule.every(3).hours.do(run_from_2015)

print("已启动定时任务：每天 01:00 自动执行 run_from_2015()")

if __name__ == '__main__':

    run_from_2015()

    # --- 永久循环（脚本不会退出） ---
    while True:
        schedule.run_pending()
        time.sleep(60)
