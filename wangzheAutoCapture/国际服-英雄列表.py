import datetime
import pymysql
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import uuid
import requests
import schedule

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


def fetch_and_store_hero_data():

    """获取英雄数据并存储到数据库"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        # 1. 打开网页
        driver.get("https://camp.honorofkings.com/h5/app/index.html?hero-hot-list=%7Bhero-hot-list%7D#/hero-hot-list")

        # 2. 等待页面加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # 3. 调用 getEncodeParam()
        specialEncodeParam = driver.execute_script("return window.__TCSJ__.getEncodeParam();")
        print("specialEncodeParam:", specialEncodeParam)

        # 4. 生成动态参数
        timestamp = int(time.time() * 1000)
        unique_id = str(uuid.uuid4())

        # 5. 请求头
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9",
            "camp-language": "zh-CN",
            "camp-region": "156",
            "campsource": "HOK-CAMP",
            "content-type": "application/json",
            "deviceid": "hF4WChc1ZKEDjPBccsTaDTz2ZNWQCpKx",  # 请确保设备ID有效
            "gameid": "29134",
            "origin": "https://camp.honorofkings.com",
            "priority": "u=1, i",
            "referer": "https://camp.honorofkings.com/",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "specialencodeparam": specialEncodeParam,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "timestamp": str(timestamp),
            "uniqueId": unique_id
        }

        # 6. 请求体
        payload = {
            "rankId": 1,
            "position": 255,
            "segment": 255,
            "bottomTab": "",
            "gameId": 29134
        }

        # 7. 发送请求到英雄列表接口
        response = requests.post(
            "https://api-camp.honorofkings.com/game/hero/getranklist",
            headers=headers,
            json=payload,
            verify=False

        )

        if response.status_code == 200:
            response_data = response.json()
            print("✅ 数据请求成功！")
            connection = get_db_connection()
            with connection.cursor() as cursor:
                insert_query = """
                    INSERT INTO lz_hero_abroad (id, cname, icon, heroCareer, banRate, showRate, winRate, createTime)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        cname=VALUES(cname),
                        icon=VALUES(icon),
                        heroCareer=VALUES(heroCareer),
                        banRate=VALUES(banRate),
                        showRate=VALUES(showRate),
                        winRate=VALUES(winRate),
                        createTime=VALUES(createTime)
                """

                hero_list = response_data.get("data", {}).get("list", [])
                for hero in hero_list:
                    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    hero_id = hero.get("heroId")
                    ban_rate = round(hero.get("banRate") * 100, 2)
                    show_rate = round(hero.get("showRate") * 100, 2)
                    win_rate = round(hero.get("winRate") * 100, 2)

                    hero_info = hero.get("heroInfo", {})
                    hero_name = hero_info.get("heroName")
                    hero_icon = hero_info.get("heroIcon")
                    hero_career = str(hero_info.get("heroCareer"))

                    cursor.execute(
                        insert_query,
                        (hero_id, hero_name, hero_icon, hero_career, ban_rate, show_rate, win_rate, current_time)
                    )

                connection.commit()
                print("✅ 英雄数据已成功保存到数据库！")
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print("响应内容:", response.text)

    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        driver.quit()
        connection.close()
        print("✅ 浏览器和数据库连接已关闭。")


def schedule_task():
    """设置每天12:00执行任务"""
    print("🔄 定时任务已启动，每天12:00执行。")
    schedule.every().day.at("12:00").do(fetch_and_store_hero_data)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    schedule_task()
