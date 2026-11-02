import json
import pymysql
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import random
import schedule
from datetime import datetime


# 数据库连接信息
db_config = {
    'host': '192.168.1.126',
    'user': 'cmdb',
    'password': 'cmdb123456',
    'database': 'game'

}


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)


def get_special_encode_param(driver):
    """获取 specialEncodeParam 参数"""
    return driver.execute_script("return window.__TCSJ__.getEncodeParam();")


def generate_headers(driver):
    """动态生成请求头，减少封禁风险"""
    return {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "camp-language": "zh-CN",
        "camp-region": "156",
        "campsource": "HOK-CAMP",
        "content-type": "application/json",
        "deviceid": "hF4WChc1ZKEDjPBccsTaDTz2ZNWQCpKx",
        "gameid": "29134",
        "origin": "https://camp.honorofkings.com",
        "referer": "https://camp.honorofkings.com/",
        "specialencodeparam": get_special_encode_param(driver),
        "user-agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120, 131)}.0.0.0 Safari/537.36",
    }


def fetch_hero_details(hero_id, driver, retry=3):
    """获取单个英雄详情，带重试机制"""
    payload = {"heroId": hero_id}
    for attempt in range(retry):
        try:
            headers = generate_headers(driver)
            response = requests.post(
                "https://api-camp.honorofkings.com/api/herowiki/getheroalldata",
                headers=headers,
                json=payload,
                verify=False
            )
            if response.status_code == 200:
                hero_info = response.json().get("data", {}).get("heroInfo", {})
                hero_info_heroid = hero_info.get("heroId")
                hero_name = hero_info.get("heroName")
                print(f"[成功] 英雄ID: {hero_info_heroid} 英雄名称：{hero_name}")

                # 获取英雄详情组排
                combination = response.json().get("data", {}).get("combination", [])

                tf_combinations = []  # 存储双排组合
                df_combinations = []  # 存储三排组合
                group_id_counter = 1

                for com in combination:
                    combination_type = com.get("combinationType")
                    hero_combination = com.get("heroCombination", [])
                    combination_data = com.get("combinationData", [])

                    combination_value = (
                        combination_data[0].get("dataValue", "").replace("%", "")
                        if combination_data else "0"
                    )

                    group_data = {
                        "groupId": group_id_counter,
                        "combinationValue": float(combination_value) if combination_value else 0,
                        "heroes": [
                            {
                                "heroId": hero.get("heroId"),
                                "heroName": hero.get("heroName"),
                                "heroIcon": hero.get("heroIcon")
                            }
                            for hero in hero_combination
                        ]
                    }

                    if combination_type == 1:
                        tf_combinations.append(group_data)
                    elif combination_type == 2:
                        df_combinations.append(group_data)

                    group_id_counter += 1

                save_to_database(hero_id, hero_name, "双排", json.dumps(tf_combinations), "lz_hero_abroad", "dfInfo")
                save_to_database(hero_id, hero_name, "三排", json.dumps(df_combinations), "lz_hero_abroad", "tfInfo")

                return hero_info
            else:
                print(f"[失败] 英雄ID: {hero_id}, 状态码: {response.status_code}")
        except Exception as e:
            print(f"[异常] 英雄ID: {hero_id}, 错误: {str(e)}")
        time.sleep(random.uniform(1, 3))
    return None


def save_to_database(hero_id, hero_name, combination_type, hero_combination, table, info_field):
    """保存英雄组排详情到数据库"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            update_query = f"""
                UPDATE {table}
                SET {info_field} = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (hero_combination, hero_id))
        connection.commit()
        print(f"[数据库] 英雄ID: {hero_id}，{combination_type} 数据已存储。")
    except Exception as e:
        print(f"[数据库错误] 英雄ID: {hero_id}，错误: {str(e)}")
    finally:
        connection.close()


def main_task():
    """主任务：获取并保存英雄详情"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get("https://camp.honorofkings.com/h5/app/index.html?hero-hot-list=%7Bhero-hot-list%7D#/hero-hot-list")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM lz_hero_abroad")
            result = cursor.fetchall()
            for row in result:
                hero_id = row['id']
                fetch_hero_details(hero_id, driver)
                time.sleep(random.uniform(2, 5))
    except Exception as e:
        print(f"[主任务错误]: {e}")
    finally:
        driver.quit()
        connection.close()


def schedule_task():
    """设置每天凌晨1:00执行任务"""
    print("🔄 定时任务已启动，每天凌晨12:10执行。")
    schedule.every().day.at("12:10").do(main_task)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    schedule_task()
