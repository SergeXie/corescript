import time
import pymysql
import requests
import schedule


def run_scraping_task():

    # 数据库连接信息
    db_config = {
        'host': '192.168.1.126',
        'user': 'cmdb',
        'password': 'cmdb123456',
        'database': 'game'

    }
    # 连接到数据库
    connection = pymysql.connect(**db_config)
    cursor = connection.cursor()

    # 在执行查询之前，确保连接有效
    connection.ping(reconnect=True)

    # 查询出token 出来
    select_token = "SELECT ssoToken FROM lz_hok_token"

    cursor.execute(select_token)
    result = cursor.fetchone()

    token = result[0]

    url = "https://kohcamp.qq.com/hero/getdetailranklistbyid"

    # 请求头
    headers = {
        "Host": "kohcamp.qq.com",
        "Connection": "keep-alive",
        "Content-Length": "51",
        "ssoToken": f"{token}",
        "ssoAppId": "campMiniProgram",
        "kohDimGender": "2",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 QQ/9.1.71.615 V1_IPH_SQ_9.1.71_1_APP_A Pixel/1170 MiniAppEnable SimpleUISwitch/0 StudyMode/0 CurrentMode/0 CurrentFontScale/1.000000 QQTheme/1000 AppId/537279954 miniProgram QMA/1112105310 QBWebViewType/1 WKType/1",
        "ssoOpenId": "ydxcx6byB6jM1aX8EpCrUlbD28KfAt9o",
        "X-Client-Proto": "https",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encrypt": "",
        "noencrypt": "1",
        "ssoBusinessId": "mini",
        "Content-Type": "application/json",
        "Origin": "https://camp.qq.com",
        "X-Requested-With": "com.tencent.mobileqq",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://camp.qq.com/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    payload = {
        "rankId": None,
        "position": 0,
        "segment": 1,
        "eId": None
    }

    # 出装
    url2 = "https://kohcamp.qq.com/gametoolbox/equip/hero/getherobestequip"

    headers2 = {
        "Host": "kohcamp.qq.com",
        "Connection": "keep-alive",
        "Content-Length": "51",
        "ssoToken": f"{token}",
        "ssoAppId": "campMiniProgram",
        "kohDimGender": "2",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 QQ/9.1.71.615 V1_IPH_SQ_9.1.71_1_APP_A Pixel/1170 MiniAppEnable SimpleUISwitch/0 StudyMode/0 CurrentMode/0 CurrentFontScale/1.000000 QQTheme/1000 AppId/537279954 miniProgram QMA/1112105310 QBWebViewType/1 WKType/1",
        "ssoOpenId": "ydxcx6byB6jM1aX8EpCrUlbD28KfAt9o",
        "X-Client-Proto": "https",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encrypt": "",
        "noencrypt": "1",
        "ssoBusinessId": "mini",
        "Content-Type": "application/json",
        "Origin": "https://camp.qq.com",
        "X-Requested-With": "com.tencent.mobileqq",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://camp.qq.com/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    payload2 = {
        "cSystem": "ios",
        "h5Get": 1,
        "heroId": 0
    }

    # 忽略 SSL 证书验证 (仅限调试，生产环境应避免)
    response = requests.post(url, headers=headers, json=payload, timeout=10, verify=False)
    # 输出响应
    print(response.status_code)
    print(response.json())
    data = response.json()["data"]["list"]  # 输出JSON响应
    print(data)

    try:
        data = response.json()["data"]["list"]  # 输出JSON响应
        for x in data:
            heroName = x["heroInfo"]["heroName"]
            heroId = x["heroInfo"]["heroId"]
            print(f"ID：{x["heroInfo"]["heroId"]} 英雄：{x["heroInfo"]["heroName"]} "
                  f" 胜率：{x["winRate"] * 100}  登场率：{x["showRate"] * 100}  Ban率：{x["banRate"] * 100}")

            # 发送 POST 请求
            payload2["heroId"] = x["heroInfo"]["heroId"]
            response2 = requests.post(url2, headers=headers2, json=payload2, verify=False)

            # 打印响应结果
            try:
                data2 = response2.json()  # 如果响应是JSON格式
                heroId = int(data2["data"]["heroId"])
                if heroId == int(x["heroInfo"]["heroId"]):
                    # 删除之前的数据
                    sql_delete = """
                        DELETE FROM `lz_hero_equip` WHERE heroId = %s;
                    """
                    cursor.execute(sql_delete, (heroId,))
                    connection.commit()
                    print(f"已清除英雄ID {heroId} 的旧数据")

                    # 插入新数据
                    for y in data2["data"]["list"]:
                        print(y)
                        print(f"出装：ID：{heroId} 装备名称: {y['szTitle']}  "
                              f"登场率：{y['showRate']}  胜率：{y['winRate']} 头像 {y['szIcon']}")

                        sql_insert = """
                            INSERT INTO `lz_hero_equip` (heroId, heroName, szTitle, equipwinRate, equipShowRate, szIcon)
                            VALUES (%s, %s, %s, %s, %s, %s);
                        """

                        cursor.execute(sql_insert, (heroId, heroName, y["szTitle"],
                                                    float(y["winRate"]) * 100, float(y["showRate"]) * 100,
                                                    y["szIcon"]))
                        connection.commit()
                        print(f"新增英雄 {heroName} 出装成功")

            except ValueError:
                print(response2.text())  # 如果响应不是JSON格式，打印文本

            print("=====================2==================")

            # time.sleep(1)

    except ValueError:
        print(response.text())  # 如果不是JSON格式，则输出文本响应

    print("完成")

# 定时任务设置，每天13:00执行一次
# schedule.every().day.at("12:25").do(run_scraping_task)
#
# # 持续运行，等待任务触发
# while True:
#     schedule.run_pending()  # 检查是否有需要运行的任务
#     time.sleep(60)  # 每分钟检查一次
run_scraping_task()