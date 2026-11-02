import pymysql
import requests


DB_CONFIG = {
    "host": "192.168.1.126",
    "user": "root",
    "password": "7CVJpyHm8XcU",
    "database": "game",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

API_URL = "https://api.91m.top/hero/app"

RANKING_PARAMS = {
    "type": "getRanking",
    "aid": 16,
    "bid": 0,
    "cid": 0,
    "did": 0,
    "setId": "",
    "lang": "zh-CN",
    "ref": "",
    "host": "pvp.91m.top",
    "gameType": "wzry",
}


def connect_db(**overrides):
    config = {**DB_CONFIG}
    for key, value in overrides.items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    return pymysql.connect(**config)


def get_ranking_rows():
    resp = requests.get(API_URL, params=RANKING_PARAMS, timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]["result"]["rows"]
