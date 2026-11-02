import time

import pymysql
import requests
import json
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

    # 请求的 URL
    url = "https://kohcamp.qq.com/gametoolbox/hero/getdetailranklistbyid"

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

    # 请求体
    data = {
        "cSystemVersionName": "iOS",
        "gameUserSex": 2,
        "cGzip": 1,
        "bottomTab": "",
        "openId": "oFhrws3vlth5qlMma-3TCe6MPw80",
        "cRand": "1731296985783",
        "cClientVersionCode": "68220107904808",
        "gameServerId": 4104,
        "kohDimGender": "2",
        "position": 0,
        "reportHashValue": "10751691104",
        "segment": 1,
        "recommendPrivacy": 0,
        "cClientVersionName": "8.101.1017",
        "cCurrentGameId": 20001,
        "cSystem": "ios",
        "gameId": 20001,
        "cGameId": 20001,
        "encodeParam": "9h0SVUzqoYQWS87mS6oFsnhMCrF02Mxdg34cRMzF7ES0qnkxJkx3miZetZLBcBqyyR1siAVG3KBGVPbyXt8aqPCecKY8D4BgU04jTxamwOrVGVmlITBolTYArtfttQtWdtXO4Axo3io%3D",
        "specialEncodeParam": "",
        "token": "aMTeB6PC",
        "gameRoleId": "2518068030",
        "gameAreaId": 4,
        "gameOpenId": "owanlspQSFPgKZrjP0mmt03VqVcA",
        "cSystemVersionCode": "15.4",
        "rankId": 14,
        "isTestFlight": 0,
        "cChannelId": 0,
        "userId": "1663513908"
    }

    # 发送请求
    response = requests.post(url, headers=headers, data=json.dumps(data), verify=False)

    # 打印响应结果
    print(response.status_code)
    print(response.json())
    data_list = response.json()["data"]["list"]
    for data in data_list:
        print(data)
        heroId = data["heroId"]
        goldPlay = data["goldPlay"]
        heroName = data["heroInfo"]["heroName"]
        heroIcon = data["heroInfo"]["heroIcon"]
        # 先删除表数据再更新
        sql_delete = """
                        DELETE FROM `lz_hero_gold_medal` WHERE heroId = %s;
                    """
        cursor.execute(sql_delete, (heroId,))
        connection.commit()
        print(f"已清除英雄ID {heroId} 的旧数据")

        sql_insert = """
                       INSERT INTO `lz_hero_gold_medal` (heroId, heroName, goldPlay, heroIcon)
                       VALUES (%s, %s, %s, %s);
                    """
        cursor.execute(sql_insert, (heroId, heroName, goldPlay, heroIcon))
        connection.commit()
        print(f"新增英雄金牌榜 {heroName} 成功")

    print("===========================3===================")


# 定时任务设置，每天13:15执行一次
# schedule.every().day.at("12:10").do(run_scraping_task)
#
# # 持续运行，等待任务触发
# while True:
#     schedule.run_pending()  # 检查是否有需要运行的任务
#     time.sleep(60)  # 每分钟检查一次
run_scraping_task()