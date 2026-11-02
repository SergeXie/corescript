import datetime
import os
import threading
import time

import pymysql


# 从 `dql_jinshi_economic_news` 中筛选美国 CPI、非农、初请、美联储利率、核心 PCE、ADP 等关键经济数据，写入 `dql_market_statistics` 统计表。脚本按小时循环执行。

class MarketStatisticsUpdater:
    """行情数据统计表更新器

    负责定期检索 dql_jinshi_economic_news 表，提取核心指标并同步到 dql_market_statistics 表。
    只对外暴露 run() 方法。
    """

    def __init__(self):
        # 1. 从 .env 文件中动态读取数据库配置
        self._db_config = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_DATABASE", "dql"),
        }

        # 2. 关键词与新闻类型映射表
        self._keyword_type_map = {
            "未季调消费者物价指数(年率)": 1,
            "季调后非农就业人口变动(千人)": 2,
            "上周季调后初请失业金人数(千人)": 3,
            "联邦基金基准利率": 4,
            "核心个人消费支出物价指数(年率)": 5,
            "ADP就业人数变动(千人)": 6,
        }

        # 1. 增加一个停止事件信号
        self._stop_event = threading.Event()

    # ================= 内部私有方法 =================

    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self._db_config)

    def _check_and_insert(self):
        """执行检查并插入数据的核心逻辑"""
        conn = self._get_connection()
        cursor = conn.cursor()

        print("=== 检查经济日历更新并同步至统计表 ===")
        now = datetime.datetime.now()
        total_insert = 0

        try:
            # 遍历所有关键字
            for kw, news_type in self._keyword_type_map.items():
                sql = """
                    SELECT pkid, time, name 
                    FROM dql_jinshi_economic_news
                    WHERE name LIKE %s
                    ORDER BY time DESC
                """
                # 使用参数化查询防止 SQL 注入
                keyword_pattern = f"%美国%{kw}%"
                cursor.execute(sql, (keyword_pattern,))
                rows = cursor.fetchall()

                for pkid, news_time, name in rows:
                    # 过滤未确定的时间数据
                    if news_time and "待确定" in str(news_time):
                        print(f"跳过（待确定）：{news_time}")
                        continue

                    insert_sql = """
                        INSERT IGNORE INTO dql_market_statistics (economicNewsUid, time, name, newsType)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(
                        insert_sql, (pkid, news_time, name, news_type)
                    )
                    total_insert += cursor.rowcount

            conn.commit()
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 本次新增记录: {total_insert} 条")

        except Exception as e:
            conn.rollback()
            print(f"数据库同步异常: {e}")
        finally:
            conn.close()

    # ================= 对外暴露的方法 =================

    def stop(self):
        """外部调用的停止方法"""
        print("正在发送停止信号...")
        self._stop_event.set()  # 设置停止标志，并唤醒处于 wait 状态的线程

    def run(self, interval_seconds: int = 3600):
        print(f"行情统计更新器已启动，每隔 {interval_seconds} 秒执行一次...\n")

        # 2. 将 while True 改为检查标志位
        while not self._stop_event.is_set():
            try:
                self._check_and_insert()
            except Exception as e:
                print(f"执行出错: {e}")

            # 3. 用 self._stop_event.wait() 代替 time.sleep()
            # wait 会阻塞 interval_seconds 秒，但如果在中途调用了 stop()，会立即被唤醒并跳出循环
            if self._stop_event.wait(timeout=interval_seconds):
                break

        print("行情统计更新器线程已安全退出。")
