import time
import pymysql
import requests
import json
from wangzheyingdiManualGrabbing.wzry_rank_data import WZRYDataParser, OSType


# 苹果
def hero_honor():
    # 数据库连接信息
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

    # 查询出token出来
    select_token = "SELECT ssoToken FROM lz_hok_token"
    cursor.execute(select_token)
    result = cursor.fetchone()
    token = result[0]

    # 查询所有英雄ID
    select_hero_ids = "SELECT id FROM lz_hero"
    cursor.execute(select_hero_ids)
    hero_results = cursor.fetchall()

    if not hero_results:
        print("没有找到英雄ID")
        return

    # 请求的URL
    url = "https://kohcamp.qq.com/honor/ranklist"

    # 请求头
    headers = {
        "Host": "kohcamp.qq.com",
        "Connection": "keep-alive",
        "Content-Length": "65",
        "content-type": "application/json",
        "kohdimgender": "2",
        "gameId": "20001",
        "ssoToken": f"f-nF3MbqfpLiE8HZ_BXw-L9iaFjmYSyjVy4Ov2yjs67Q3Q13ENOTbKbhdPwcc8NGmksHEOdLoIpDZ5dW1r2BgHmcRdYDk9PLmUvPRgtXCtvcJh-8MsTFF7woiNQ84sco4kAnHHn6R5l4IHzJVzYpLeD1_TaBSO8Ql4MEQ7MxyWtnOBNBPYOs7vjmFIlZOe-y8Jq2X2Ba_964dSIlSJWqkGfdPbDBc4Oy7bI5HDhEWyL09ZO_vIpYe_NPNe4q4A6M",
        "encodeParam": "sAKURKHqAFJ8P/FnHqiH16z4OsSQ6KGk6UUcFueW3IHtZVmbxI6B4B7/zh4wlGXDNN4xNvzuTK0gkEkaVpt0E6DwJ7Wg9oGcx7i2jIIpHJeGTABnF3oaI4aAdsZPV2nwjjAOOGhWz2w61IcupwhF36nSK4Rj4EwfmH7ohA==",
        "cGameId": "20001",
        "cClientVersionCode": "9999999999",
        "cClientVersionName": "9.99.999",
        "encryptVersion": "3",
        "ssoOpenId": "ydxcx6byB6jM1aX8EpCrUlbD28KfAt9o",
        "ssoBusinessId": "mini",
        "ssoAppId": "campMiniProgram",
        "snsPlatform": "wx",
        "Accept-Encoding": "gzip,compress,br,deflate",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.56(0x18003834) NetType/4G Language/zh_CN",
        "Referer": "https://servicewechat.com/wx898cb4b08963dccb/242/page-frame.html"
    }

    # 循环每个英雄ID进行请求
    for hero in hero_results:
        hero_id = hero[0]  # 获取英雄ID

        # 请求数据
        data = {
            "adcode": 1561,
            "areaId": "4",
            "heroId": hero_id,  # 使用当前英雄ID
            "roleId": "2518068030"
        }

        # 发送POST请求
        response = requests.post(url, headers=headers, data=json.dumps(data), verify=False)

        # 输出响应内容
        if response.status_code == 200:
            print(f"appleHonor 请求成功! 英雄ID: {hero_id}")
            print(response.json())
            appleHonor = response.json().get("data", None)
            if appleHonor:
                WZRYDataParser.parse(json_string=json.dumps(appleHonor), connection=connection,
                                     os=OSType.iOS.value, hero_id=hero_id,
                                     area_id=1)

            else:
                # 记录 英雄ID到一个文件下，这是未请求成功的英雄ID
                with open("ios_failed_hero_requests.txt", "a") as file:
                    file.write(f"未成功抓取的英雄ID: {hero_id}, 状态码: {response.status_code}\n")

            time.sleep(15)  # 调整延时的时间

        else:
            print(f"请求失败, 英雄ID: {hero_id}, 状态码:", response.status_code)

    print("完成")

# 调用函数
hero_honor()
