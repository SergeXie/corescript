import os
import sys
import time
import warnings
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
import pandas as pd
import pymysql
from sqlalchemy import create_engine

# 禁用所有 Warning 输出
warnings.filterwarnings("ignore")


def get_base_dir():
    """获取程序当前运行目录 (兼容 PyInstaller 打包与源码运行)"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# 自动加载同目录下的 .env 文件
env_path = os.path.join(get_base_dir(), ".env")
load_dotenv(dotenv_path=env_path)


class KLineDataResampler:
    """K线重采样与合成数据同步服务

    负责从 dql_trading_fpg 表中拉取 M1 基础数据，
    按 5T/15T/30T/1H/4H/1D/1W/1M 重采样合成并写入目标表。
    只对外暴露 run() 方法。
    """

    def __init__(self, trading_goods: str = "XAUUSD", period: str = "M1"):
        self.trading_goods = trading_goods
        self.period = period
        self.base_dir = get_base_dir()

        # 从 .env 中读取数据库参数
        db_host = os.getenv("DB_HOST", "127.0.0.1")
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_DATABASE", "dql")

        self._db_config = {
            "host": db_host,
            "user": db_user,
            "password": db_password,
            "database": db_name,
        }

        # SQLAlchemy engine 实例
        self._engine = create_engine(
            f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
        )

        # 周期时间戳记录文件映射 (写入当前可执行文件同级目录)
        self._last_synthesis_time_files = {
            "5T": os.path.join(self.base_dir, "last_synthesis_time_5T_fpg2.txt"),
            "15T": os.path.join(self.base_dir, "last_synthesis_time_15T_fpg2.txt"),
            "30T": os.path.join(self.base_dir, "last_synthesis_time_30T_fpg2.txt"),
            "1H": os.path.join(self.base_dir, "last_synthesis_time_1H_fpg2.txt"),
            "4H": os.path.join(self.base_dir, "last_synthesis_time_4H_fpg2.txt"),
            "1D": os.path.join(self.base_dir, "last_synthesis_time_1D_fpg2.txt"),
            "1W": os.path.join(self.base_dir, "last_synthesis_time_1W_fpg2.txt"),
            "1M": os.path.join(self.base_dir, "last_synthesis_time_1M_fpg2.txt"),
        }

    # ================= 内部私有方法 =================

    def _get_conn(self):
        """获取 pymysql 数据库连接"""
        return pymysql.connect(**self._db_config)

    def _get_last_synthesis_time(self, file_path):
        """读取周期最后合成时间记录"""
        try:
            with open(file_path, "r") as file:
                last_time_str = file.read().strip()
                if last_time_str:
                    return datetime.strptime(
                        last_time_str, "%Y-%m-%d %H:%M:%S"
                    )
        except FileNotFoundError:
            return None
        return None

    def _update_last_synthesis_time(self, file_path, max_time):
        """更新周期最后合成时间记录"""
        with open(file_path, "w") as file:
            file.write(max_time.strftime("%Y-%m-%d %H:%M:%S"))

    def _resample_dataframe(self, df, interval):
        """对 DataFrame 执行重采样运算"""
        df["tradeDateTime"] = pd.to_datetime(df["tradeDateTime"])
        df = df.set_index("tradeDateTime")

        print(f"原始数据时间范围: {df.index.min()} 到 {df.index.max()}")

        # pandas 3.x 不再支持 T/H 等旧别名，统一映射到新频率写法
        pandas_freq_map = {
            "5T": "5min",
            "15T": "15min",
            "30T": "30min",
            "1H": "1h",
            "4H": "4h",
            "1D": "1d",
            "1W": "1W",
            "1M": "1ME",
        }
        pandas_freq = pandas_freq_map.get(interval, interval)

        type_dict = {
            "5T": "M5",
            "15T": "M15",
            "30T": "M30",
            "1H": "H1",
            "4H": "H4",
            "1D": "D1",
            "1W": "W1",
            "1M": "MN",
        }

        resampled_df = (
            df.resample(pandas_freq)
            .agg(
                {
                    "high": "max",
                    "low": "min",
                    "vol": "sum",
                    "spread": "last",
                }
            )
            .reset_index()
        )

        resampled_df["opening"] = (
            df["opening"].resample(pandas_freq).first().values
        )
        resampled_df["closed"] = (
            df["closed"].resample(pandas_freq).last().values
        )

        if resampled_df.empty:
            print(f"在区间 {interval} 内没有生成合成数据")
        else:
            print(f"重采样结果:\n{resampled_df}")

        resampled_df["opening"] = resampled_df["opening"].round(2)
        resampled_df["high"] = resampled_df["high"].round(2)
        resampled_df["closed"] = resampled_df["closed"].round(2)
        resampled_df["low"] = resampled_df["low"].round(2)
        resampled_df["digits"] = 2
        resampled_df["tradingGoods"] = self.trading_goods
        resampled_df["platform"] = "FPG"
        resampled_df["type"] = type_dict.get(interval)

        # 非周线过滤周六日数据
        if interval != "1W":
            resampled_df = resampled_df[
                ~resampled_df["tradeDateTime"].dt.weekday.isin([5, 6])
            ]

        resampled_df.dropna(inplace=True)

        return resampled_df

    def _sync_data(self):
        """核心数据拉取、重采样与写入同步逻辑"""
        print("开始处理数据")

        # 延迟5秒，确保 M1 已完整写入数据库
        time.sleep(5)

        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            total_inserted = 0
            total_ignored = 0

            # 每个周期独立处理
            for interval in [
                "5T",
                "15T",
                "30T",
                "1H",
                "4H",
                "1D",
                "1W",
                "1M",
            ]:
                inserted_count = 0
                ignored_count = 0

                # 读取该周期最后处理时间
                last_synthesis_time_file = self._last_synthesis_time_files[
                    interval
                ]
                last_synthesis_time = self._get_last_synthesis_time(
                    last_synthesis_time_file
                )
                print(f"[{interval}] 上次处理时间: {last_synthesis_time}")

                # 拉取 M1 数据
                if last_synthesis_time:
                    print(
                        f"查询周期 {interval} 的起始时间: {last_synthesis_time}"
                    )
                    query = (
                        f"SELECT * FROM dql_trading_fpg WHERE "
                        f"type='{self.period}' AND tradingGoods='{self.trading_goods}' "
                        f"AND tradeDateTime > '{last_synthesis_time}' "
                        f"ORDER BY tradeDateTime asc"
                    )
                else:
                    query = (
                        f"SELECT * FROM dql_trading_fpg WHERE "
                        f"type='{self.period}' AND tradingGoods='{self.trading_goods}' "
                        f"ORDER BY tradeDateTime asc"
                    )

                cursor.execute(query)
                results = cursor.fetchall()

                if not results:
                    print(f"[{interval}] 无新增 M1 数据")
                    continue

                # 转为 DataFrame
                df = pd.DataFrame(
                    [
                        {
                            "pkId": x[0],
                            "tradeDateTime": x[4].strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "opening": float(x[9]),
                            "digits": x[5],
                            "spread": int(x[6]),
                            "high": float(x[11]),
                            "low": float(x[12]),
                            "closed": float(x[10]),
                            "vol": x[13],
                        }
                        for x in results
                    ]
                )

                df["tradeDateTime"] = pd.to_datetime(df["tradeDateTime"])
                resampled_df = self._resample_dataframe(df, interval)

                if resampled_df.empty:
                    print(f"[{interval}] 重采样结果为空")
                    continue

                # 去掉最后一条，避免写入尚未收盘的未完成K线
                resampled_df = resampled_df.iloc[:-1]
                if resampled_df.empty:
                    print(f"[{interval}] 仅有未收盘K线，已跳过")
                    continue

                insert_sql = """
                    INSERT IGNORE INTO dql_trading_fpg_tests
                    (tradeDateTime, high, low, vol, spread, opening, closed, digits, tradingGoods, platform, type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                for _, row in resampled_df.iterrows():
                    trade_dt = (
                        row["tradeDateTime"].to_pydatetime()
                        if hasattr(row["tradeDateTime"], "to_pydatetime")
                        else row["tradeDateTime"]
                    )
                    cursor.execute(
                        insert_sql,
                        (
                            trade_dt,
                            float(row["high"]),
                            float(row["low"]),
                            int(row["vol"]),
                            int(row["spread"]),
                            float(row["opening"]),
                            float(row["closed"]),
                            int(row["digits"]),
                            row["tradingGoods"],
                            row["platform"],
                            row["type"],
                        ),
                    )
                    if cursor.rowcount == 1:
                        inserted_count += 1
                    else:
                        ignored_count += 1

                conn.commit()

                # 更新该周期最后处理时间记录文件
                last_time = resampled_df["tradeDateTime"].max()
                self._update_last_synthesis_time(
                    last_synthesis_time_file, last_time
                )

                total_inserted += inserted_count
                total_ignored += ignored_count
                print(
                    f"[{interval}] 插入 {inserted_count} 条，忽略重复 {ignored_count} 条，总计 {len(resampled_df)} 条"
                )

            print(
                f"本轮完成：插入 {total_inserted} 条，忽略重复 {total_ignored} 条"
            )

        except Exception as e:
            print(f"处理数据时发生错误: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    # ================= 唯一对外暴露的方法 =================

    def run(self, minutes: int = 1):
        """启动 BlockingScheduler 定时重采样任务

        :param minutes: 轮询间隔分钟数，默认每 1 分钟执行一次
        """
        scheduler = BlockingScheduler()
        scheduler.add_job(self._sync_data, "interval", minutes=minutes)

        print(f"🚀 K线重采样服务已启动，每 {minutes} 分钟执行一次...")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("服务已停止")


# --- 启动入口示例 ---
if __name__ == "__main__":
    resampler = KLineDataResampler(trading_goods="XAUUSD", period="M1")
    # 启动同步（默认每 1 分钟拉取并重采样）
    resampler.run()