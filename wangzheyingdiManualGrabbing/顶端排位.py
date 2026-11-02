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
        "cSystemVersionName": "iOS",
        "gameUserSex": 2,
        "cGzip": 1,
        "bottomTab": "",
        "openId": "oFhrws3vlth5qlMma-3TCe6MPw80",
        "cRand": "1731296312107",
        "cClientVersionCode": "68220107904808",
        "gameServerId": 4104,
        "kohDimGender": "2",
        "position": 0,
        "reportHashValue": "10751644672",
        "segment": 4,
        "recommendPrivacy": 0,
        "cClientVersionName": "8.101.1017",
        "cCurrentGameId": 20001,
        "cSystem": "ios",
        "gameId": 20001,
        "cGameId": 20001,
        "encodeParam": "ZgIaLw0lNOBT%2F0xcRxdYyShCUhdWbin2axhfUaQt8l36toWFw1WvrLfbvhXqVCjYFuUWql0lyih%2FTq725GMLnxpcuMIdPmffIh1u4cDesUyMJ9IPs61UWzKYQDY1MTUHGT0BEQH0%2BbA%3D",
        "specialEncodeParam": "",
        "token": "aMTeB6PC",
        "gameRoleId": "2518068030",
        "gameAreaId": 4,
        "gameOpenId": "owanlspQSFPgKZrjP0mmt03VqVcA",
        "cSystemVersionCode": "15.4",
        "rankId": 0,
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
            print(x)
            heroWinRate = round(x["winRate"] * 100, 2)
            heroShowRate = round(x["showRate"] * 100, 2)
            heroBanRate = round(x["banRate"] * 100, 2)
            heroName = x["heroInfo"]["heroName"]
            heroId = x["heroInfo"]["heroId"]
            print(f"ID：{x["heroInfo"]["heroId"]} 英雄：{x["heroInfo"]["heroName"]} "
                  f" 胜率：{x["winRate"] * 100}  登场率：{x["showRate"] * 100}  Ban率：{x["banRate"] * 100}")

            # 执行 SQL 查询，查找最新的记录，且 createTime 为当天
            sql_select = """
            SELECT * FROM `lz_hero_stats`
            WHERE heroId=%s
            ORDER BY createTime DESC LIMIT 1
            """
            cursor.execute(sql_select, (heroId))
            result = cursor.fetchone()

            if result:
                # 获取最新记录的 pkId
                pk_id = result[0]  # 假设 pkId 是第一列

                # 更新数据库的 firstPlaceScore 和 lastPlaceScore 字段
                sql_update = """
                            UPDATE `lz_hero_stats`
                            SET topHeroWinRate=%s, topHeroShowRate=%s,
                            topHeroBanRate=%s
                            WHERE pkId=%s
                            """
                cursor.execute(sql_update, (heroWinRate, heroShowRate, heroBanRate, pk_id))
                connection.commit()

                print(f"更新英雄 {heroName} 的 topHeroWinRate 和 topHeroShowRate  topHeroShowRate 成功")
            else:
                print(f"未找到英雄 {heroName} 的数据库记录")

            print("=======================1===================")

            # time.sleep(1)

    except ValueError:
        print(response.text())  # 如果不是JSON格式，则输出文本响应


# 定时任务设置，每天13:00执行一次
# schedule.every().day.at("12:24").do(run_scraping_task)
#
# # 持续运行，等待任务触发
# while True:
#     schedule.run_pending()  # 检查是否有需要运行的任务
#     time.sleep(60)  # 每分钟检查一次
run_scraping_task()