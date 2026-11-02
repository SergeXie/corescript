from datetime import datetime
import schedule
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pymysql
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc


# 你的抓取任务函数
def run_scraping_task():
    print("执行海异王者定时任务")
    driver = None

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

    print(f"任务开始执行，当前时间：{datetime.now()}")
    try:
        # Keep this in sync with the installed Chrome major version.
        driver = uc.Chrome(version_main=149)
        # ============================
        #   ★ 改为 UC 的部分结束
        # ============================

        # 打开网页
        driver.get("https://pvp.hayfuon.cn/")

        # 等待页面主结构加载
        time.sleep(5)

        # 在执行查询之前，确保连接有效
        connection.ping(reconnect=True)

        # 点击服务器选择的下拉菜单
        server_dropdown_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='haypvpserver']/xm-select"))
        )
        server_dropdown_button.click()
        print("成功打开服务器选择下拉菜单")

        # 等待并选择 'Android微信'
        android_wechat_option = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='xm-option-content' and text()='Android微信']"))
        )
        android_wechat_option.click()
        print("成功选择了服务器：Android微信")

        # 等待页面更新后抓取英雄分类和数据
        time.sleep(2)

        # 获取所有分类的 XPath
        categories_xpath = "//div[@class='xm-option-content']"

        # 获取分类的总数
        total_categories = len(driver.find_elements(By.XPATH, categories_xpath))
        print("total_categories:{}".format(total_categories))
        # 使用索引遍历每个分类
        for i in range(6):
            # 每次遍历都重新获取所有分类
            categories = driver.find_elements(By.XPATH, categories_xpath)

            # 获取当前分类
            category = categories[i]

            try:
                # 打印分类名称
                print(f"当前分类：{category.text}")

                # 滚动到分类元素，使其可见
                driver.execute_script("arguments[0].scrollIntoView(true);", category)

                # 使用 JavaScript 点击分类，确保触发点击事件
                driver.execute_script("arguments[0].click();", category)
                print(f"点击分类：{category.text}")

                # 等待分类下的英雄列表加载
                time.sleep(2)

                # 获取该分类下的所有英雄
                heroes = driver.find_elements(By.XPATH, "//div[@class='xm-tree-box']//div[@class='xm-option-content']")
                print(len(heroes))
                for j in range(len(heroes)):
                    hero = heroes[j]
                    print(j)
                    try:
                        # 获取英雄名字
                        hero_name = hero.text.strip()

                        # 滚动到英雄元素并点击
                        driver.execute_script("arguments[0].scrollIntoView(true);", hero)
                        driver.execute_script("arguments[0].click();", hero)
                        print(f"点击英雄：{hero.text}")
                        # 等待页面数据加载
                        time.sleep(2)

                        # 抓取页面中的玩家信息
                        new_data = driver.find_elements(By.XPATH,
                                                        "//ul[@class='list-group list-group-lg m-b-none distrank-list']/li")

                        if new_data:
                            first_player = new_data[0]
                            last_player = new_data[-1]
                            tenth_player = new_data[9] if len(new_data) >= 10 else None
                            fiftieth_player = new_data[49] if len(new_data) >= 50 else None
                            eightieth_player = new_data[79] if len(new_data) >= 80 else None

                            # 获取第一个玩家信息
                            first_name = first_player.find_element(By.XPATH, ".//span[@class='text-ellipsis']").text
                            first_server_info = first_player.find_element(By.XPATH, ".//small").text
                            first_score = first_player.find_element(By.XPATH,
                                                                    ".//span[contains(@class, 'distrank-list-value')]").text
                            print(f"第一个玩家名称: {first_name}, 服务器信息: {first_server_info}, 战力: {first_score}")

                            # 获取最后一个玩家信息
                            last_name = last_player.find_element(By.XPATH, ".//span[@class='text-ellipsis']").text
                            last_server_info = last_player.find_element(By.XPATH, ".//small").text
                            last_score = last_player.find_element(
                                By.XPATH,".//span[contains(@class, 'distrank-list-value')]").text
                            print(f"最后一个玩家名称: {last_name}, 服务器信息: {last_server_info}, 战力: {last_score}")

                            # 获取第10个玩家信息
                            tenth_score = tenth_player.find_element(
                                By.XPATH,".//span[contains(@class, 'distrank-list-value')]").text if tenth_player else None

                            # 获取第50个玩家信息
                            fiftieth_score = fiftieth_player.find_element(
                                By.XPATH,".//span[contains(@class, 'distrank-list-value')]").text if fiftieth_player else None

                            # 获取第80个玩家信息
                            eightieth_score = eightieth_player.find_element(
                                By.XPATH,".//span[contains(@class, 'distrank-list-value')]").text if eightieth_player else None

                            print(
                                f"英雄名称: {hero_name}, 第一名战力值: {first_score}, 第10名战力值: {tenth_score}, "
                                f"第50名战力值: {fiftieth_score}, 第80名战力值: {eightieth_score}, 最后一名战力值: {last_score}")

                            # 执行 SQL 查询，查找最新的记录，且 createTime 为当天
                            sql_select = """
                            SELECT * FROM `lz_hero_rank`
                            WHERE heroName=%s
                            ORDER BY pkId DESC LIMIT 1
                            """
                            if hero.text == "成吉思汗":
                                hero_name = "苍"
                                cursor.execute(sql_select, (hero_name))
                            else:
                                cursor.execute(sql_select, (hero.text if hero.text else hero_name))

                            result = cursor.fetchone()

                            if result:
                                # 获取最新记录的 pkId
                                pk_id = result[0]  # 假设 pkId 是第一列
                                # 更新数据库的 firstPlaceScore 和 lastPlaceScore 字段
                                sql_update = """
                                            UPDATE `lz_hero_rank`
                                            SET firstPlaceScore=%s, lastPlaceScore=%s,
                                            tenthPlaceScore=%s,fiftyScores=%s,
                                            eightyScores=%s
                                            WHERE pkId=%s
                                            """
                                cursor.execute(sql_update, (first_score, last_score, tenth_score,
                                                            fiftieth_score, eightieth_score, pk_id))
                                connection.commit()

                                print(f"更新英雄 {hero.text} 的 firstPlaceScore 和 lastPlaceScore 成功")
                            else:
                                print(f"未找到英雄 {hero.text} 的数据库记录")

                        # 返回分类页面
                        dropdown_button = WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.XPATH, "//*[@id='haypvphero']/xm-select"))
                        )
                        driver.execute_script("arguments[0].click();", dropdown_button)

                        # 等待返回分类列表
                        time.sleep(2)

                        # 检查是否为最后一个分类和英雄
                        if i == 6 - 1 and j == len(heroes) - 1:
                            print("已抓取最后一个分类和最后一个英雄，程序结束。")
                            driver.quit()  # 停止 Selenium WebDriver
                            cursor.close()  # 关闭数据库 cursor
                            connection.close()  # 关闭数据库连接
                            break

                    except Exception as e:
                        print(f"抓取英雄数据失败：{e}")

                print(f"分类：{category.text}下的英雄抓取完成")

                # 手动折叠当前分类，确保下一个分类能展开
                driver.execute_script("arguments[0].click();", category)
                print(f"折叠分类：{category.text}")

                # 在此判断是否要退出外部分类循环
                if i == 6 - 1:
                    break  # 退出分类循环

            except Exception as e:
                print(f"点击分类失败：{e}")

    except Exception as e:
        print(f"无法找到元素或操作失败: {e}")

    finally:
        # 关闭数据库连接，如果未在上面关闭
        if connection.open:
            cursor.close()
            connection.close()

        # 关闭浏览器，如果未在上面关闭
        if driver:
            driver.quit()

# 定时任务设置，每天13:00执行一次
schedule.every().day.at("07:30").do(run_scraping_task)
# 持续运行，等待任务触发
while True:
    schedule.run_pending()  # 检查是否有需要运行的任务
    time.sleep(60)  # 每分钟检查一次
