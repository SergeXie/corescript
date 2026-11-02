import time
import pandas as pd
import pymysql
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')  # 绂佺敤鎵€鏈夌殑璀﹀憡
engine = create_engine('mysql+pymysql://cmdb:cmdb123456@192.168.1.126/dql')

# 鍛ㄦ湡
period = "M1"
# 浜ゆ槗鍝佺
tradingGoods = "XAUUSD"


def get_last_synthesis_time(file_path):
    try:
        with open(file_path, 'r') as file:
            last_time_str = file.read().strip()
            if last_time_str:
                return datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
    except FileNotFoundError:
        return None
    return None


def update_last_synthesis_time(file_path, max_time):
    with open(file_path, 'w') as file:
        file.write(max_time.strftime('%Y-%m-%d %H:%M:%S'))


def resample_dataframe(df, interval):
    df['tradeDateTime'] = pd.to_datetime(df['tradeDateTime'])
    df = df.set_index('tradeDateTime')

    print(f"原始数据时间范围: {df.index.min()} 到 {df.index.max()}")

    # pandas 3.x 不再支持 T/H 等旧别名，统一映射到新频率写法
    pandas_freq_map = {
        '5T': '5min',
        '15T': '15min',
        '30T': '30min',
        '1H': '1h',
        '4H': '4h',
        '1D': '1d',
        '1W': '1W',
        '1M': '1ME',
    }
    pandas_freq = pandas_freq_map.get(interval, interval)

    type_dict = {
        '5T': 'M5',
        '15T': 'M15',
        '30T': 'M30',
        '1H': 'H1',
        '4H': 'H4',
        '1D': 'D1',
        '1W': 'W1',
        '1M': 'MN',
    }

    resampled_df = df.resample(pandas_freq).agg({
        'high': 'max',
        'low': 'min',
        'vol': 'sum',
        'spread': 'last'
    }).reset_index()

    resampled_df['opening'] = df['opening'].resample(pandas_freq).first().values
    resampled_df['closed'] = df['closed'].resample(pandas_freq).last().values

    if resampled_df.empty:
        print(f"在区间 {interval} 内没有生成合成数据")
    else:
        print(f"重采样结果:\n{resampled_df}")

    resampled_df['opening'] = resampled_df['opening'].round(2)
    resampled_df['high'] = resampled_df['high'].round(2)
    resampled_df['closed'] = resampled_df['closed'].round(2)
    resampled_df['low'] = resampled_df['low'].round(2)
    resampled_df['digits'] = 2
    resampled_df['tradingGoods'] = 'XAUUSD'
    resampled_df['platform'] = 'FPG'
    resampled_df['type'] = type_dict.get(interval)

    if interval != '1W':
        resampled_df = resampled_df[~resampled_df['tradeDateTime'].dt.weekday.isin([5, 6])]

    resampled_df.dropna(inplace=True)

    return resampled_df


def sync_data():
    print("开始处理数据")
    # 各周期时间戳文件
    last_synthesis_time_files = {
        '5T': 'last_synthesis_time_5T_fpg2.txt',
        '15T': 'last_synthesis_time_15T_fpg2.txt',
        '30T': 'last_synthesis_time_30T_fpg2.txt',
        '1H': 'last_synthesis_time_1H_fpg2.txt',
        '4H': 'last_synthesis_time_4H_fpg2.txt',
        '1D': 'last_synthesis_time_1D_fpg2.txt',
        '1W': 'last_synthesis_time_1W_fpg2.txt',
        '1M': 'last_synthesis_time_1M_fpg2.txt',
    }

    # 延迟5秒，确保 M1 已完整写入
    time.sleep(5)

    conn = pymysql.connect(
        host='192.168.1.126',
        user='cmdb',
        password='cmdb123456',
        database='dql'
    )
    cursor = conn.cursor()

    try:
        total_inserted = 0
        total_ignored = 0

        # 每个周期独立处理
        for interval in ['5T', '15T', '30T', '1H', '4H', '1D', '1W', '1M']:
            inserted_count = 0
            ignored_count = 0

            # 读取该周期最后处理时间
            last_synthesis_time_file = last_synthesis_time_files[interval]
            last_synthesis_time = get_last_synthesis_time(last_synthesis_time_file)
            print(f"[{interval}] 上次处理时间: {last_synthesis_time}")

            # 拉取 M1 数据
            if last_synthesis_time:
                print(f"查询周期 {interval} 的起始时间: {last_synthesis_time}")
                query = (f"SELECT * FROM dql_trading_fpg WHERE "
                         f"type='{period}' AND tradingGoods='{tradingGoods}' "
                         f"AND tradeDateTime > '{last_synthesis_time}' "
                         f"ORDER BY tradeDateTime asc")
            else:
                query = (f"SELECT * FROM dql_trading_fpg WHERE "
                         f"type='{period}' AND tradingGoods='{tradingGoods}' "
                         f"ORDER BY tradeDateTime asc")

            cursor.execute(query)
            results = cursor.fetchall()

            if not results:
                print(f"[{interval}] 无新增 M1 数据")
                continue

            # 转为 DataFrame
            df = pd.DataFrame([{
                "pkId": x[0],
                "tradeDateTime": x[4].strftime("%Y-%m-%d %H:%M:%S"),
                "opening": float(x[9]),
                "digits": x[5],
                "spread": int(x[6]),
                "high": float(x[11]),
                "low": float(x[12]),
                "closed": float(x[10]),
                "vol": x[13]
            } for x in results])

            df['tradeDateTime'] = pd.to_datetime(df['tradeDateTime'])
            resampled_df = resample_dataframe(df, interval)

            # 去掉最后一条，避免写入尚未收盘的K线
            if resampled_df.empty:
                print(f"[{interval}] 重采样结果为空")
                continue

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
                cursor.execute(insert_sql, (
                    row['tradeDateTime'].to_pydatetime() if hasattr(row['tradeDateTime'], 'to_pydatetime') else row['tradeDateTime'],
                    float(row['high']),
                    float(row['low']),
                    int(row['vol']),
                    int(row['spread']),
                    float(row['opening']),
                    float(row['closed']),
                    int(row['digits']),
                    row['tradingGoods'],
                    row['platform'],
                    row['type']
                ))
                if cursor.rowcount == 1:
                    inserted_count += 1
                else:
                    ignored_count += 1

            conn.commit()

            # 更新该周期最后处理时间
            last_time = resampled_df['tradeDateTime'].max()
            update_last_synthesis_time(last_synthesis_time_file, last_time)

            total_inserted += inserted_count
            total_ignored += ignored_count
            print(f"[{interval}] 插入 {inserted_count} 条，忽略重复 {ignored_count} 条，总计 {len(resampled_df)} 条")

        print(f"本轮完成：插入 {total_inserted} 条，忽略重复 {total_ignored} 条")
    except Exception as e:
        print(f"处理数据时发生错误: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# 璁剧疆瀹氭椂浠诲姟锛屾瘡鍒嗛挓鎵ц涓€娆?sync_data
scheduler = BlockingScheduler()
scheduler.add_job(sync_data, 'interval', minutes=1)

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    pass




