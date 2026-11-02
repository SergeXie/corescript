import datetime
import json
import traceback
from enum import StrEnum
from wangzheyingdiManualGrabbing.player_rank_data import PlayerRank


class OSType(StrEnum):
    iOS = "iOS"
    android = "android"


class WZRYDataParser:

    def __init__(self):
        pass

    @classmethod
    def parse(cls, connection, json_string: str, os, hero_id: str, area_id: int):
        json_data = json.loads(json_string)
        data = json_data["list"]
        player_ranks = []
        for item in data:
            if area_id != 1 and int(item["rankValue"]) < 10000:
                print("区域低于一万战力值，continue")
                continue

            player_rank = PlayerRank(
                item['rankNo'],
                item['roleId'],
                item['roleIcon'],
                item['roleName'],
                item['roleJobName'],
                item['rankValue'],
                item['rankChange'],
                item['rankValChange'],
                item['userId'],
                item['userName'],
                item['serverId'],
                item['openid'],
                item['areaId'],
                item['isHide']
            )
            player_ranks.append(player_rank)

        cls.save_data(connection, player_ranks, os, area_id=area_id, hero_id=hero_id)

    @staticmethod
    def save_data(connection, player_ranks: list, os, hero_id: str, area_id: int):
        try:
            cursor = connection.cursor()
            now = datetime.datetime.now()

            for player_rank in player_ranks:
                if int(player_rank.userId) > 0:
                    # 检查记录是否存在
                    sql_check = "SELECT id FROM lz_player WHERE userId = %s"
                    cursor.execute(sql_check, (player_rank.userId,))
                    result = cursor.fetchone()

                    if result:  # 记录存在，更新玩家表
                        record_id = result[0]
                        sql_update = """
                                    UPDATE lz_player
                                    SET avater = %s, userName = %s, roleName = %s, roleJobName = %s, updateTime = %s
                                    WHERE id = %s
                                """
                        values = (
                            player_rank.roleIcon, player_rank.userName, player_rank.roleName, player_rank.roleJobName,
                            now,
                            record_id)
                        cursor.execute(sql_update, values)

                    else:  # 记录不存在，插入玩家表

                        sql_insert = """
                                    INSERT INTO lz_player (userId, avater, userName, roleName, roleJobName)
                                    VALUES (%s, %s, %s, %s, %s)
                                """
                        values = (player_rank.userId, player_rank.roleIcon, player_rank.userName, player_rank.roleName,
                                  player_rank.roleJobName)

                        cursor.execute(sql_insert, values)

                    connection.commit()
                    print("Player data updated or inserted successfully.")
                else:
                    print("userId is not greater than 0, skipping update or insert.")

            for player in player_ranks:
                # 插入 lz_player_rank_log 每日英雄荣誉记录表
                sql_rank_log = """
                    INSERT INTO lz_player_rank_log (userId, heroId, `rank`, power, areaId, os)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values_rank_log = (player.userId, hero_id, player.rankNo, player.rankValue, area_id, os)
                cursor.execute(sql_rank_log, values_rank_log)

            connection.commit()

            # 如果是国榜 那么isInNationalTop 是否在国榜 设置为 0
            if area_id == 1:
                sql = """
                            UPDATE lz_player_rank
                            SET isInNationalTop = 0
                            WHERE heroId = %s AND os = %s
                      """
            else:
                sql = """
                            UPDATE lz_player_rank
                            SET isInRegionalTop = 0
                            WHERE heroId = %s AND os = %s
                      """

            cursor.execute(sql, (hero_id, os))
            connection.commit()

            now = datetime.datetime.now()

            # player_ranks 原始数据
            for player in player_ranks:
                user_id = player.userId
                rank_no = player.rankNo
                rank_value = player.rankValue

                # 检查记录是否存在 用户id和英雄id是否在这次抓取的荣誉榜单里面，
                sql_check = ("SELECT id, nationalTopCount, regionalTopCount,lastNationalTopTime, "
                             "lastHistoryNationalTopTime, isInHistoryNationalTop,"
                             "nationalHistoryPower,nationalHistoryRank FROM lz_player_rank "
                             "WHERE userId = %s AND heroId = %s AND os = %s")
                cursor.execute(sql_check, (user_id, hero_id, os))
                result = cursor.fetchone()

                if result:  # 记录存在，根据id查找，找到成功之后
                    # 获取当前时间
                    now = datetime.datetime.now()
                    # 计算本周的开始时间（周五 00:00:00）
                    week_start = now - datetime.timedelta(days=now.weekday() - 4)  # 4 表示周五
                    current_time_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

                    # 更新 nationalRank 国服排名  nationalPower 国服上榜战力 lastNationalTopTime 最后一次国服上榜时间
                    # isInNationalTop 是否在国榜   nationalTopCount 国服上榜次数
                    (record_id, national_top_count, regional_top_count,
                     last_national_top_time, history_last_national_top_time,
                     is_in_history_national_top, national_history_power, national_history_rank) = result

                    if area_id == 1:  # 国服
                        print("week_start:{}".format(week_start))
                        if current_time_start == week_start:
                            national_top_count += 1  # 只有在每周五加1

                        if current_time_start == week_start:
                            # 如果还没进入过历史国榜
                            if is_in_history_national_top == 0:
                                is_in_history_national_top = 1
                                national_history_power = rank_value  # 记录历史上榜战力
                                national_history_rank = rank_no  # 记录历史最好排名
                            else:
                                # 如果当前战力更高，则更新历史最高战力
                                national_history_power = max(national_history_power, int(rank_value))
                                # 更新历史排名（如果当前排名更好，即值更小）
                                national_history_rank = min(national_history_rank, int(rank_no))

                            # 更新 lz_player_rank
                            sql_update = """
                                UPDATE lz_player_rank
                                SET nationalRank = %s, nationalPower = %s, lastNationalTopTime = %s,
                                    isInNationalTop = 1, nationalTopCount = %s, updateTime = %s,
                                    isInHistoryNationalTop = %s, nationalHistoryPower = %s,
                                    lastHistoryNationalTopTime = %s, nationalHistoryRank = %s
                                WHERE id = %s
                            """
                            values = (rank_no, rank_value, now, national_top_count, now,
                                      is_in_history_national_top, national_history_power, now,
                                      national_history_rank, record_id)
                            print("更新历史记录数据")

                        else:

                            sql_update = """
                                            UPDATE lz_player_rank
                                            SET nationalRank = %s, nationalPower = %s, lastNationalTopTime = %s, isInNationalTop = 1, nationalTopCount = %s, updateTime = %s
                                            WHERE id = %s
                                        """
                            values = (rank_no, rank_value, now, national_top_count, now, record_id)

                        cursor.execute(sql_update, values)
                    else:

                        # 查询当前玩家的历史区域记录
                        sql_check_history = """
                                SELECT isInHistoryRegionalTop, regionalHistoryPower, regionalHistoryRank
                                FROM lz_player_rank WHERE id = %s
                            """
                        cursor.execute(sql_check_history, (record_id,))
                        history_result = cursor.fetchone()
                        is_in_history_regional_top, regional_history_power, regional_history_rank = history_result

                        if current_time_start == week_start:
                            regional_top_count += 1  # 只有在每周五加1

                        if current_time_start == week_start:
                            # 如果玩家还没进过历史区域榜
                            if is_in_history_regional_top == 0:
                                is_in_history_regional_top = 1
                                regional_history_power = rank_value  # 记录历史最高战力
                                regional_history_rank = rank_no  # 记录历史最好排名
                            else:
                                # 更新历史战力（如果当前战力更高）
                                regional_history_power = max(regional_history_power, int(rank_value))
                                # 更新历史排名（如果当前排名更好，即值更小）
                                regional_history_rank = min(regional_history_rank, int(rank_no))

                            # 更新 lz_player_rank
                            sql_update = """
                                    UPDATE lz_player_rank
                                    SET regionalRank = %s, regionalPower = %s, lastRegionalTopTime = %s,
                                        isInRegionalTop = 1, regionalTopCount = %s, updateTime = %s,
                                        isInHistoryRegionalTop = %s, regionalHistoryPower = %s,
                                        lastHistoryRegionalTopTime = %s, regionalHistoryRank = %s
                                    WHERE id = %s
                                """
                            values = (rank_no, rank_value, now, regional_top_count, now,
                                      is_in_history_regional_top, regional_history_power, now,
                                      regional_history_rank, record_id)
                            print("ok1")

                        else:
                            sql_update = """
                                        UPDATE lz_player_rank
                                        SET regionalRank = %s, regionalPower = %s, lastRegionalTopTime = %s, isInRegionalTop = 1, regionalTopCount = %s, updateTime = %s
                                        WHERE id = %s
                                        """
                            values = (rank_no, rank_value, now, regional_top_count, now, record_id)
                            print("ok2")

                    cursor.execute(sql_update, values)

                else:  # 记录不存在，插入
                    if area_id == 1:  # 国服 添加字段数据，
                        sql_insert = """
                            INSERT INTO lz_player_rank (userId, heroId, nationalRank, nationalPower, lastNationalTopTime, isInNationalTop, nationalTopCount, os, isInRegionalTop)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        values = (user_id, hero_id, rank_no, rank_value, now, 1, 1, os, 0)
                        print("insert ok")

                    else:  # 区域 添加字段数据，
                        sql_insert = """
                            INSERT INTO lz_player_rank (userId, heroId, regionalRank, regionalPower, lastRegionalTopTime, isInRegionalTop, regionalTopCount, os, isInNationalTop)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        values = (user_id, hero_id, rank_no, rank_value, now, 1, 1, os, 0)
                        print("insert ok")

                    cursor.execute(sql_insert, values)

        except Exception as e:
            info = traceback.format_exc()
            print(info)
            print(f"数据库错误：{e}")
        finally:
            cursor.close()


if __name__ == '__main__':
    print(OSType.iOS)
    # file_path = "D:\\Desktop\\hero.json"
    # connection = None
    # try:
    #     with open(file_path, 'r', encoding='utf-8') as file:
    #         json_string = file.read()
    #         connection = get_db()
    #         WZRYDataParser.parse(json_string=json_string, connection=connection, os=OSType.android, hero_id=117,
    #                              area_id=0)
    # except FileNotFoundError:
    #     print(f"错误：文件 {file_path} 未找到。")
    # except json.JSONDecodeError as e:
    #     print(f"错误：JSON 解析错误：{e}")
    # finally:
    #     if connection:
    #         connection.close()
