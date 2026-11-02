import json
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

    # 请求体
    payload = {
        "cSystemVersionName": "iOS",
        "gameUserSex": 2,
        "cGzip": 1,
        "bottomTab": "",
        "openId": "oFhrws3vlth5qlMma-3TCe6MPw80",
        "cRand": "1731294199621",
        "cClientVersionCode": "68220107904808",
        "gameServerId": 4104,
        "kohDimGender": "2",
        "position": 0,
        "reportHashValue": "10751625968",
        "segment": 1,
        "recommendPrivacy": 0,
        "cClientVersionName": "8.101.1017",
        "cCurrentGameId": 20001,
        "cSystem": "ios",
        "gameId": 20001,
        "cGameId": 20001,
        "encodeParam": "QirTyaL4340hdOosMVTGYNkgXaJsr3MrFRZRhOhNjm94XIvrGQOp%2BbgIgMC1ANg3NE9lussF3N1E29zOFrKLdTYCRtX%2BBVUQDZuPTHfbFWPohNoLDfr4M6NkMs4e4Vizm5UkB9Wghq4%3D",
        "specialEncodeParam": "",
        "token": "aMTeB6PC",
        "gameRoleId": "2518068030",
        "gameAreaId": 4,
        "gameOpenId": "owanlspQSFPgKZrjP0mmt03VqVcA",
        "CampPreloadHTTPHandledIdentifier": 4,
        "cSystemVersionCode": "15.4",
        "rankId": 0,
        "isTestFlight": 0,
        "cChannelId": 0,
        "userId": "1663513908"
    }

    url3 = "https://kohcamp.qq.com/gametoolbox/hero/getherofringedata"

    headers3 = {
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

    payload3 = {
        "cSystemVersionName": "iOS",
        "gameUserSex": 2,
        "cGzip": 1,
        "openId": "oFhrws3vlth5qlMma-3TCe6MPw80",
        "cRand": "1731294835009",
        "cClientVersionCode": "68220107904808",
        "gameServerId": 4104,
        "kohDimGender": "2",
        "reportHashValue": "10752604384",
        "recommendPrivacy": 0,
        "cClientVersionName": "8.101.1017",
        "cCurrentGameId": 20001,
        "cSystem": "ios",
        "gameId": 20001,
        "cGameId": 20001,
        "encodeParam": "Glft68eKdEx1IlF2ltKnd3qO3o%2BjxG5BKdOWdjXpfvtjHWyyhYYS4dNr9y%2BprjD7O9qDug5yp8uDPXKxH5ofDLnO0KjTF0r8x%2BclcYuDn0wl29lB7uQyxX0DJkr5v8vhdT3G%2BbEq2Kk%3D",
        "specialEncodeParam": "",
        "heroId": 505,
        "token": "aMTeB6PC",
        "gameRoleId": "2518068030",
        "gameAreaId": 4,
        "gameOpenId": "owanlspQSFPgKZrjP0mmt03VqVcA",
        "cSystemVersionCode": "15.4",
        "isTestFlight": 0,
        "cChannelId": 0,
        "userId": "1663513908"
    }

    # 忽略 SSL 证书验证 (仅限调试，生产环境应避免)
    response = requests.post(url, headers=headers, json=payload, verify=False)
    # 输出响应
    print(response.status_code)
    try:
        data = response.json()["data"]["list"]  # 输出JSON响应
        for x in data:
            heroName = x["heroInfo"]["heroName"]
            print(f"ID：{x["heroInfo"]["heroId"]} 英雄：{x["heroInfo"]["heroName"]} "
                  f" 胜率：{x["winRate"] * 100}  登场率：{x["showRate"] * 100}  Ban率：{x["banRate"] * 100}")

            print("=====================2==================")

            # 获取铭文出装
            payload3["heroId"] = x["heroInfo"]["heroId"]
            response3 = requests.post(url3, headers=headers3, json=payload3, verify=False)
            # 打印响应结果
            print(response3.status_code)
            data3 = response3.json()["RuneSetList"]
            new_data_list = []
            for u in data3:
                data_dict = {}
                heroId3 = u["heroId"]
                if int(heroId3) == int(x["heroInfo"]["heroId"]):
                    data_dict["showRate"] = u["showRate"]
                    data_dict["heroId"] = heroId3
                    data_dict["winRate"] = u["winRate"]
                    data_dict["runeList"] = u["runeList"]
                    new_data_list.append(data_dict)

            # 使用列表推导式处理数据
            data = [
                {
                    'showRate': item['showRate'],
                    'heroId': item['heroId'],
                    'winRate': item['winRate'],
                    'runeList': [{"szTitle": f"{rune['szTitle'].split(':')[-1]}x{rune['num']}",  # 组织格式为 '铭文名称x数量'
                                 "szIcon": rune["szIcon"] }for rune in item['runeList']]
                }
                for item in new_data_list
            ]

            # 删除之前的数据
            sql_delete = """DELETE FROM `lz_hero_rune` WHERE heroId = %s; """
            cursor.execute(sql_delete, (x["heroInfo"]["heroId"],))
            connection.commit()
            print(f"已清除英雄ID {x["heroInfo"]["heroId"]} 的旧数据")

            for d in data:
                sql_insert = """
                           INSERT INTO `lz_hero_rune` (heroId, heroName, runeDetail, runeshowRate, runeWinRate)
                           VALUES (%s, %s, %s, %s, %s);
                            """
                cursor.execute(sql_insert, (d["heroId"], heroName, json.dumps(d["runeList"]),
                                            float(d["winRate"]) * 100, float(d["showRate"]) * 100))
                connection.commit()
                print(f"新增英雄 {heroName} 符文成功")
            print("===========================3===================")

            # time.sleep(1)

    except ValueError:
        print(response.text())  # 如果不是JSON格式，则输出文本响应

    print("完成")


# # 定时任务设置，每天13:00执行一次
# schedule.every().day.at("12:13").do(run_scraping_task)
#
# # 持续运行，等待任务触发
# while True:
#     schedule.run_pending()  # 检查是否有需要运行的任务
#     time.sleep(60)  # 每分钟检查一次
run_scraping_task()