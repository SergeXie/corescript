import pymysql
import requests
import time
import json

import schedule

# --- 配置区 ---
DB_CONFIG = {
    'host': '192.168.1.126',
    'user': 'root',
    'password': '7CVJpyHm8XcU',
    'database': 'game',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

API_URL = 'https://www.sapi.run/hero/select.php'
PLATFORMS = [("wx", "安卓微信")]


def fetch_and_sync_rank():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    hero_count = 0

    try:
        # 1. 核心调整：同时查询 id 和 cname
        sql_select = "SELECT id, cname FROM lz_hero ORDER BY heroType"
        cursor.execute(sql_select)
        heroes = cursor.fetchall()

        print(f"🚀 开始同步，共 {len(heroes)} 个英雄...")

        for hero in heroes:
            local_hero_id = hero['id']  # 来自 lz_hero 表的 id
            name = hero['cname']

            for p_code, p_name in PLATFORMS:
                params = {'hero': name, 'type': p_code}
                try:
                    response = requests.get(API_URL, params=params, timeout=10, verify=False)

                    if response.status_code == 200:
                        rsp_data = response.json()

                        # 判断 API 响应是否成功并包含 data
                        if rsp_data.get('code') == 200 and rsp_data.get('data'):
                            data = rsp_data['data']

                            # 2. 核心调整：SQL 插入时使用本地 local_hero_id
                            sql_insert = """
                                INSERT INTO lz_hero_rank (
                                    heroId, heroName, platform, photo, area, 
                                    areaPower, city, cityPower, province, 
                                    provincePower, guobiao, updateTime, stamp
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """

                            # 注意：这里 heroId 填充的是 local_hero_id
                            values = (
                                local_hero_id,  # 使用本地数据库 ID
                                name,
                                p_code,
                                data.get('photo', ''),
                                data.get('area', '未知'),
                                data.get('areaPower', 0),
                                data.get('city', '未知'),
                                data.get('cityPower', 0),
                                data.get('province', '未知'),
                                data.get('provincePower', 0),
                                data.get('guobiao', ''),
                                data.get('updatetime', ''),
                                data.get('stamp', int(time.time()))
                            )

                            cursor.execute(sql_insert, values)
                            conn.commit()
                            hero_count += 1
                            print(f"✅ [ID:{local_hero_id}] {name} ({p_name}) 同步成功")
                        else:
                            print(f"⚠️  API 数据异常: {name} (可能未查询到战力)")
                    else:
                        print(f"🚫 API 请求失败: {name}, HTTP {response.status_code}")

                except Exception as req_e:
                    print(f"🔥 网络异常: {name}, 错误: {req_e}")

                # 频率控制
                time.sleep(0.5)

    finally:
        cursor.close()
        conn.close()
        print(f"\n✨ 同步任务结束，成功更新 {hero_count} 条数据。")


# 定时任务设置，每天13:00执行一次
schedule.every().day.at("07:10").do(fetch_and_sync_rank)
# 持续运行，等待任务触发
while True:
    schedule.run_pending()  # 检查是否有需要运行的任务
    time.sleep(60)  # 每分钟检查一次

# if __name__ == "__main__":
#     requests.packages.urllib3.disable_warnings()
#     fetch_and_sync_rank()