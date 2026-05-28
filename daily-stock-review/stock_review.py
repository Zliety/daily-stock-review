import os
import requests
import pandas as pd
import numpy as np
from langchain_community.chat_models import ChatTianyi
from datetime import datetime

# -------------------------- 配置部分（无需修改，密钥从环境变量读取） --------------------------
TIANYI_API_KEY = os.environ.get("TIANYI_API_KEY")
SERVER_CHAN_KEY = os.environ.get("SERVER_CHAN_KEY")

# 多模型自动切换（星辰→GLM5→DeepSeek）
def get_llm():
    models = ["xingchen-3.5-flash", "glm-5-flash", "deepseek-v3-flash"]
    for model in models:
        try:
            llm = ChatTianyi(
                model=model,
                api_key=TIANYI_API_KEY,
                temperature=0.1,
                timeout=60
            )
            # 测试连接
            llm.invoke("测试")
            print(f"使用模型：{model}")
            return llm
        except Exception as e:
            print(f"模型 {model} 调用失败：{e}，切换下一个")
            continue
    raise Exception("所有大模型均调用失败，请检查API Key和网络")

llm = get_llm()

# -------------------------- 数据采集函数 --------------------------
def collect_market_data():
    """采集大盘指数数据（上证/深证/创业板/科创50）"""
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market='std')
        indexes = client.quotes(symbol=['000001', '399001', '399006', '000688'])
        return indexes[['code', 'name', 'price', 'change', 'volume', 'amount']].to_dict('records')
    except Exception as e:
        return f"大盘数据采集失败：{str(e)}"

def collect_sector_data():
    """采集申万一级行业涨跌幅数据"""
    try:
        import akshare as ak
        sector_df = ak.stock_board_industry_name_em()
        return sector_df[['板块名称', '涨跌幅', '主力净流入-净额']].head(10).to_dict('records')
    except Exception as e:
        return f"板块数据采集失败：{str(e)}"

def collect_stock_stats():
    """采集全市场个股涨跌统计"""
    try:
        import akshare as ak
        stock_df = ak.stock_zh_a_spot_em()
        up_count = len(stock_df[stock_df['涨跌幅'] > 0])
        down_count = len(stock_df[stock_df['涨跌幅'] < 0])
        flat_count = len(stock_df[stock_df['涨跌幅'] == 0])
        limit_up = len(stock_df[stock_df['涨跌幅'] >= 9.9])
        limit_down = len(stock_df[stock_df['涨跌幅'] <= -9.9])
        total_amt = stock_df['成交额'].sum() / 100000000  # 转换为亿元
        return {
            "上涨家数": up_count,
            "下跌家数": down_count,
            "平盘家数": flat_count,
            "涨停家数": limit_up,
            "跌停家数": limit_down,
            "两市成交额": f"{total_amt:.1f}亿元"
        }
    except Exception as e:
        return f"个股统计失败：{str(e)}"

def collect_northbound_flow():
    """采集北向资金净流入数据"""
    try:
        import akshare as ak
        nb_df = ak.stock_hsgt_northbound_flow_em()
        return f"北向资金今日净流入：{nb_df['当日净流入-净额'].iloc[0]}亿元"
    except Exception as e:
        return f"北向资金数据采集失败：{str(e)}"

def collect_top_news():
    """采集今日重要财经新闻"""
    try:
        import akshare as ak
        news_df = ak.stock_info_global_em()
        return news_df[['标题', '发布时间']].head(5).to_dict('records')
    except Exception as e:
        return f"新闻数据采集失败：{str(e)}"

# -------------------------- AI分析函数 --------------------------
def analyze_market(data):
    prompt = f"""
    你是资深A股大盘分析师。请基于以下数据客观分析今日市场：
    大盘指数：{data['market']}
    个股涨跌：{data['stock_stats']}
    北向资金：{data['northbound']}
    
    分析要求：
    1. 今日大盘整体走势定性（上涨/下跌/震荡）及核心特征
    2. 市场赚钱效应评估（涨跌家数、涨跌停对比）
    3. 成交量变化解读（放量/缩量及意义）
    4. 北向资金流向的信号意义
    
    语言简洁专业，不超过300字，避免情绪化表达。
    """
    return llm.invoke(prompt).content

def analyze_sectors(data):
    prompt = f"""
    你是板块轮动专家。请基于以下数据分析今日板块表现：
    板块涨跌幅：{data['sectors']}
    
    分析要求：
    1. 列出涨幅前3和跌幅前3的板块及涨跌幅
    2. 简要分析领涨板块的可能驱动因素
    3. 预判哪些板块可能具有短期持续性
    
    每个板块分析不超过50字，结构清晰。
    """
    return llm.invoke(prompt).content

def analyze_news(data):
    prompt = f"""
    你是财经新闻解读专家。请从以下新闻中筛选对A股影响最大的2条：
    今日新闻：{data['news']}
    
    分析要求：
    1. 每条新闻用一句话概括核心内容
    2. 明确指出影响的具体板块
    3. 标注影响程度（正面/负面/中性）
    
    每条分析不超过80字，客观中立。
    """
    return llm.invoke(prompt).content

# -------------------------- 报告生成与推送 --------------------------
def generate_report(analysis):
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""# {today} A股每日复盘报告

## 一、今日大盘概览
{analysis['market']}

## 二、板块热点分析
{analysis['sectors']}

## 三、重要消息解读
{analysis['news']}

## 四、明日操作提示
1. 密切关注大盘量能变化，持续缩量需保持谨慎
2. 聚焦领涨板块的龙头个股，避免追高跟风
3. 控制整体仓位在5成以下，做好风险对冲

---
⚠️ **免责声明**：本报告由AI自动生成，仅供学习参考，不构成任何投资建议。股市有风险，投资需谨慎。
"""

def push_to_wechat(title, content):
    """通过Server酱推送到微信"""
    if not SERVER_CHAN_KEY:
        print("未配置Server酱Key，跳过推送")
        return False
    
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
    data = {
        "title": title,
        "desp": content
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"微信推送失败：{e}")
        return False

# -------------------------- 主流程 --------------------------
def main():
    print("="*50)
    print(f"开始执行每日股市复盘：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 数据采集
    print("\n[1/5] 正在采集大盘数据...")
    market_data = collect_market_data()
    
    print("[2/5] 正在采集板块数据...")
    sector_data = collect_sector_data()
    
    print("[3/5] 正在采集个股统计...")
    stock_stats = collect_stock_stats()
    
    print("[4/5] 正在采集北向资金...")
    northbound_data = collect_northbound_flow()
    
    print("[5/5] 正在采集财经新闻...")
    news_data = collect_top_news()

    # 整合数据
    all_data = {
        "market": market_data,
        "sectors": sector_data,
        "stock_stats": stock_stats,
        "northbound": northbound_data,
        "news": news_data
    }

    # 2. AI分析
    print("\n开始AI分析...")
    analysis = {
        "market": analyze_market(all_data),
        "sectors": analyze_sectors(all_data),
        "news": analyze_news(all_data)
    }

    # 3. 生成报告
    print("生成复盘报告...")
    report = generate_report(analysis)
    print("\n" + "="*50)
    print(report)
    print("="*50 + "\n")

    # 4. 推送报告
    print("推送报告到微信...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    success = push_to_wechat(f"{today_str} A股复盘报告", report)
    
    if success:
        print("✅ 报告推送成功！")
    else:
        print("❌ 报告推送失败，请检查Server酱配置")
        raise Exception("微信推送失败")

if __name__ == "__main__":
    main()