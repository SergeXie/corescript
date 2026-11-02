# 更新最新行情到统计表中
import time

import pymysql
import datetime

# 数据库配置
DB_CONFIG = {
    'host': '192.168.1.126',
    'user': 'cmdb',
    'password': 'cmdb123456',
    'database': 'dql'

}

# 需要监控的关键字（模糊搜索用）
# KEYWORD_TYPE_MAP = {
#     "未季调CPI年率(万人)": 1,  # 第三方财经网站称之为 未季调消费者物价指数(年率)
#     "季调后非农就业人口": 2,  # 第三方财经网站称之为 季调后非农就业人口变动(千人)
#     "初请失业金人数(万人)": 3,  # 上周季调后初请失业金人数(千人)
#     "美联储利率决定(上限)": 4,  # 美国联邦基金基准利率
#     "核心PCE物价指数年率": 5,  # 核心个人消费支出物价指数(年率)
# }

# 关键核心财经日历名称变更
# 系统名称（金十原名称）	第三方财经日历名称(变更后)
# 未季调CPI年率(万人)	未季调消费者物价指数(年率)
# 季调后非农就业人口	季调后非农就业人口变动(千人)
# 初请失业金人数(万人)	上周季调后初请失业金人数(千人)
# 美联储利率决定(上限)	美国联邦基金基准利率
# 核心PCE物价指数年率	核心个人消费支出物价指数(年率)


KEYWORD_TYPE_MAP = {
    "未季调消费者物价指数(年率)": 1,
    "季调后非农就业人口变动(千人)": 2,
    "上周季调后初请失业金人数(千人)": 3,
    "联邦基金基准利率": 4,
    "核心个人消费支出物价指数(年率)": 5,
    "ADP就业人数变动(千人)": 6
}


# 每天执行的时间（默认早上 9 点）
EXECUTE_HOUR = 9
EXECUTE_MINUTE = 0

def check_and_insert():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("=== 每小时检查经济日历更新 ===")
    now = datetime.datetime.now()

    total_insert = 0

    # 遍历所有关键字
    for kw, newsType in KEYWORD_TYPE_MAP.items():
        sql = f"""
            SELECT pkid, time, name 
            FROM dql_jinshi_economic_news
            WHERE name LIKE '%%美国%%{kw}%%'
            ORDER BY time DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()

        for pkid, time, name in rows:
            if '待确定' in time:
                # 如果包含，则跳过当前循环的剩余部分，进入下一个item
                print(f"跳过（待确定）：{time}")
                continue

            insert_sql = """
                INSERT IGNORE INTO dql_market_statistics (economicNewsUid, time, name, newsType)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (pkid, time, name, newsType))
            total_insert += cursor.rowcount

    conn.commit()
    conn.close()

    print(f"{now} - 本次新增记录: {total_insert} 条")


def run_hourly():
    print("脚本已启动，每隔 1 小时执行一次...\n")

    while True:
        try:
            check_and_insert()
        except Exception as e:
            print(f"执行出错: {e}")

        # 每隔 1 小时执行一次
        time.sleep(60 * 60)


if __name__ == "__main__":
    run_hourly()
    # check_and_insert()