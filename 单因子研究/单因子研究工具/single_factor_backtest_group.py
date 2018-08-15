from gm.api import *
import QuantLib as ql
import pandas as pd
from WindPy import w
import json
import numpy as np
# 引入工具函数和学习器
from tools import get_trading_date_from_now, list_gm2wind, list_wind2jq
# 引入因子类路径
import sys
sys.path.append('D:\\programs\\多因子策略开发\\单因子研究')
from single_factor import PE

# 俺们但一字分组测试盈亏效果的代码
# 回测的基本参数的设定
BACKTEST_START_DATE = '2013-08-01'  # 回测开始日期
BACKTEST_END_DATE = '2018-08-14'  # 回测结束日期，测试结束日期不运用算法
INDEX = 'SHSE.000300'  # 股票池代码
FACTOR = PE  # 需要获取的因子列表，用单因子研究中得模块
FACTOR_COEFF = {}  # 因子获取的具体参数
QUANTILE = [0.8, 1.0]  # 因子分组的分位数
TRADING_DATE = '10'  # 每月的调仓日期，非交易日寻找下一个最近的交易日

# 用于记录调仓信息的字典
stock_dict = {}
w.start()

# 根据回测阶段选取好调仓日期
trading_date_list = []  # 记录调仓日期的列表
i = 0
while True:
    date_now = get_trading_date_from_now(BACKTEST_START_DATE, i, ql.Days)  # 遍历每个交易日
    date_trading = get_trading_date_from_now(date_now.split('-')[0] + '-' + date_now.split('-')[1] + '-' + TRADING_DATE, 0, ql.Days)
    if date_now == date_trading:
        trading_date_list.append(date_now)
    i += 1
    if date_now == BACKTEST_END_DATE:
        break
BACKTEST_START_DATE = trading_date_list[0]  # 调整回测起始日为第一次调仓的日子


def init(context):
    # 按照回测的将股票池的历史股票组成提出并合并
    history_constituents = get_history_constituents(INDEX, start_date=BACKTEST_START_DATE, end_date=BACKTEST_END_DATE)
    history_constituents = [set(temp['constituents'].keys()) for temp in history_constituents]
    history_constituents_all = set()
    for temp in history_constituents:
        history_constituents_all = history_constituents_all | temp
    history_constituents_all = list(history_constituents_all)
    pd.DataFrame(history_constituents_all).to_csv('data\\涉及到的股票代码.csv')  # 存储股票代码以方便调试
    # 根据板块的历史数据组成订阅数据
    # subscribe(symbols=history_constituents_all, frequency='1d')
    # 每天time_rule定时执行algo任务，time_rule处于09:00:00和15:00:00之间
    schedule(schedule_func=algo, date_rule='daily', time_rule='10:00:00')


def algo(context):
    date_now = context.now.strftime('%Y-%m-%d')
    date_previous = get_trading_date_from_now(date_now, -1, ql.Days)  # 前一个交易日，用于获取因子数据的日期
    if date_now not in trading_date_list:  # 非调仓日
        pass  # 预留非调仓日的微调空间
    else:  # 调仓日执行算法
        print(date_now+'日回测程序执行中...')
        code_list = list_gm2wind(list(get_history_constituents(INDEX, start_date=date_previous, end_date=date_previous)[0]['constituents'].keys()))
        factor = FACTOR(date_previous, code_list, **FACTOR_COEFF)  # 读取单因子的代码
        df = factor.get_factor().dropna()
        quantiles = df.quantile(QUANTILE).values  # 取对应的分位数值
        stock_codes = list(df[(df[factor.factor_name] >= quantiles[0][0]) & (df[factor.factor_name] < quantiles[1][0])].index.values)
        stock_codes = list_wind2jq(stock_codes)
        stock_now = {}
        for stock_code in stock_codes:
            stock_now[stock_code] = 1.0 / len(stock_codes)
        stock_dict[date_now] = stock_now


def on_backtest_finished(context, indicator):
    # 输出回测指标
    print(indicator)
    stock_json = json.dumps(stock_dict)
    stock_file = open('data\\stock_json.json', 'w')
    stock_file.write(stock_json)
    stock_file.close()


if __name__ == '__main__':
    run(strategy_id='4d2f6b1c-8f0a-11e8-af59-305a3a77b8c5',
        filename='single_factor_backtest_group.py',
        mode=MODE_BACKTEST,
        token='d7b08e7e21dd0315a510926e5a53ade8c01f9aaa',
        backtest_initial_cash=10000000,
        backtest_adjust=ADJUST_PREV,
        backtest_commission_ratio=0.0001,
        backtest_slippage_ratio=0.0001,
        backtest_start_time=BACKTEST_START_DATE+' 09:00:00',
        backtest_end_time=BACKTEST_END_DATE+' 15:00:00')