# Python 文件说明

本文档按目录简单说明项目中各个 Python 文件的用途，方便快速判断脚本负责什么任务。

## FPGPeriodGenerate

### `fpg_tests_data_synthesis.py`

从 `dql_trading_fpg` 表读取 `XAUUSD` 的 `M1` 行情数据，使用 pandas 重采样生成 `M5`、`M15`、`M30`、`H1`、`H4`、`D1`、`W1`、`MN` 等周期 K 线，并写入 `dql_trading_fpg_tests`。脚本使用 APScheduler 每分钟执行一次，并通过 `last_synthesis_time_*.txt` 文件记录各周期已处理到的时间。

## jinshi

### `financial_calendar_api.py`

抓取 FX168 财经日历接口数据，写入 `dql_jinshi_economic_news`，并根据名称规则给部分重要经济数据自动关联标签。脚本会从数据库最新时间开始逐天补数据，并配置了每天 01:00 以及每 3 小时执行一次。

### `inset_market_statistics.py`

从 `dql_jinshi_economic_news` 中筛选美国 CPI、非农、初请、美联储利率、核心 PCE、ADP 等关键经济数据，写入 `dql_market_statistics` 统计表。脚本按小时循环执行。

### `update_real_time_news.py`

抓取金十 `flash_newest.js` 快讯内容，解析时间和正文，增量写入 `dql_jinshi_market_news`。脚本常驻运行，每 5 分钟同步一次最新快讯。

## wangzheAutoCapture

### `new_script_wangzhe.py`

使用 Selenium + undetected_chromedriver 打开 `https://pvp.hayfuon.cn/`，选择 Android 微信区，遍历英雄分类和英雄榜单，抓取第一名、第 10 名、第 50 名、第 80 名、最后一名战力，并更新 `lz_hero_rank` 对应字段。脚本每天 07:30 定时执行。

### `shushu.py`

树树榜单相关的统一定时入口。每天 07:00 更新 `lz_hero.gradientScore`，07:20 写入/更新 `lz_shushu_hero_ranking`，07:40 补充英雄 `performance` 数据。

### `shushu_common.py`

`shushu.py` 使用的公共模块，集中放数据库配置、91m 接口地址、榜单接口参数、数据库连接函数和榜单数据拉取函数。

### `update_hero_rank_scores.py`

从 91m 榜单接口读取英雄战力分位数据，将每个英雄最新一条 `lz_hero_rank` 记录的第一名、第 10 名、第 50 名、最后一名战力更新进去。支持立即执行、定时执行、读取本地 JSON 文件和 dry-run 校验。

### `wzry_rank_spy.py`

王者荣耀英雄排行数据抓取脚本，调用第三方接口 `sapi.run` 获取英雄战力榜信息，并写入 `lz_hero_rank`。目前配置为每天 07:10 定时同步安卓微信平台数据。

### `国际服-英雄列表.py`

通过 Selenium 获取 Honor of Kings 营地页面中的动态参数，再请求国际服英雄热度榜接口，抓取英雄名称、头像、职业、禁用率、登场率、胜率等数据，写入 `lz_hero_abroad`。脚本每天 12:00 定时执行。

### `国际服-英雄详情.py`

读取 `lz_hero_abroad` 中的英雄 ID，逐个请求国际服英雄详情接口，解析双排、三排组合数据，并回写到 `lz_hero_abroad` 的相关字段。脚本每天 12:10 定时执行。

## wangzheyingdiManualGrabbing

### `player_rank_data.py`

玩家英雄荣誉榜数据模型，定义 `PlayerRank` 类，用于保存排名、角色、战力、用户、区服等字段。

### `wzry_rank_data.py`

王者荣耀荣誉榜 JSON 解析和入库逻辑。负责把接口返回的玩家排行数据转换为 `PlayerRank`，并更新 `lz_player`、`lz_player_rank_log`、`lz_player_rank` 等玩家和榜单相关表。

### `王者荣耀榜-苹果.py`

抓取 iOS 侧的王者荣耀英雄荣誉榜。脚本读取 `lz_hero` 英雄 ID，调用 `kohcamp.qq.com/honor/ranklist` 接口，再使用 `WZRYDataParser` 保存国榜玩家排名数据；失败的英雄会记录到 `ios_failed_hero_requests.txt`。

### `顶端排位.py`

调用王者营地接口获取顶端排位分段下的英雄胜率、登场率、Ban 率，并更新 `lz_hero_stats` 最新记录中的 `topHeroWinRate`、`topHeroShowRate`、`topHeroBanRate`。

### `巅峰排位.py`

调用王者营地接口获取巅峰排位分段下的英雄胜率、登场率、Ban 率，并更新 `lz_hero_stats` 最新记录中的 `peakHeroWinRate`、`peakHeroShowRate`、`peakHeroBanRate`。

### `英雄金牌榜.py`

调用王者营地金牌榜接口，获取各英雄金牌玩法数据，先清理旧数据，再写入 `lz_hero_gold_medal`。

### `出装接口.py`

先获取英雄列表，再逐个请求英雄最佳出装接口，解析出装标题、胜率、登场率、图标等信息，刷新写入 `lz_hero_equip`。

### `铭文接口.py`

先获取英雄列表，再逐个请求英雄铭文数据接口，整理铭文名称、数量、胜率、登场率等信息，刷新写入 `lz_hero_rune`。

### `克制-被克制-三排-双排组合.py`

先获取英雄列表，再逐个请求英雄额外信息接口，解析克制、被克制、双排组合、三排组合和英雄职业信息，并更新 `lz_hero_stats` 最新记录。
