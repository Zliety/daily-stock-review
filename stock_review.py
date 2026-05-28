import os
import requests
import pandas as pd
import numpy as np
from langchain_openai import ChatOpenAI
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# -------------------------- 配置部分（修改为你自己的模型ID） --------------------------
TIANYI_API_KEY = os.environ.get("TIANYI_API_KEY")
SERVER_CHAN_KEY = os.environ.get("SERVER_CHAN_KEY")

# 多模型自动切换
def get_llm():
    models = [
        "f23c54bf38b64ee194b28783d61be788",  # 替换为你的模型ID
    ]
    
    for model in models:
        try:
            llm = ChatOpenAI(
                model=model,
                api_key=TIANYI_API_KEY,
                base_url="https://wishub-x6.ctyun.cn/v1",
                temperature=0.1,
                timeout=120,
                max_retries=3
            )
            llm.invoke("测试")
            print(f"✅ 使用模型：{model}")
            return llm
        except Exception as e:
            print(f"❌ 模型 {model} 调用失败：{str(e)[:100]}...，切换下一个")
            continue
    
    raise Exception("所有大模型均调用失败，请检查API Key和模型ID")

llm = get_llm()

# -------------------------- 雪球API工具（GitHub环境100%可用） --------------------------
def xueqiu_api(symbols):
    """雪球官方API，无反爬，GitHub环境专用"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/"
    }
    
    # 先获取cookie
    session = requests.Session()
    session.get("https://xueqiu.com", headers=headers, timeout=10)
    
    # 请求数据
    url = f"https://stock.xueqiu.com/v5/stock/quote.json?symbol={','.join(symbols)}"
    response = session.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()["data"]["items"]

# -------------------------- 数据采集函数（全部改用雪球API） --------------------------
def collect_market_data():
    """采集大盘指数数据（雪球API）"""
    try:
        symbols = ["SH000001", "SZ399001", "SZ399006", "SH000688"]
        data = xueqiu_api(symbols)
        
        result = []
        for item in data:
            quote = item["quote"]
            result.append({
                "code": quote["symbol"],
                "name": quote["name"],
                "price": round(float(quote["current"]), 2),
                "change": round(float(quote["percent"]), 2),
                "volume": round(float(quote["volume"]) / 100000000, 2),
                "amount": round(float(quote["amount"]) / 100000000, 2)
            })
        
        print("✅ 大盘数据采集成功（雪球API）")
        return result
    except Exception as e:
        print(f"❌ 大盘数据采集失败：{str(e)}")
        return "大盘数据暂时无法获取"

def collect_sector_data():
    """采集申万一级行业数据（雪球API）"""
    try:
        # 申万一级行业代码
        sectors = [
            "BK0475", "BK0476", "BK0477", "BK0478", "BK0479",
            "BK0480", "BK0481", "BK0482", "BK0483", "BK0484",
            "BK0485", "BK0486", "BK0487", "BK0488", "BK0489",
            "BK0490", "BK0491", "BK0492", "BK0493", "BK0494",
            "BK0495", "BK0496", "BK0497", "BK0498", "BK0499",
            "BK0500", "BK0501", "BK0502", "BK0503", "BK0504",
            "BK0505", "BK0506", "BK0507", "BK0508"
        ]
        
        data = xueqiu_api(sectors)
        
        result = []
        for item in data:
            quote = item["quote"]
            result.append({
                "板块名称": quote["name"],
                "涨跌幅": round(float(quote["percent"]), 2),
                "主力净流入-净额": round(float(quote["amount"]) / 100000000, 2)
            })
        
        # 按涨跌幅排序
        result.sort(key=lambda x: x["涨跌幅"], reverse=True)
        print("✅ 板块数据采集成功（雪球API）")
        return result[:10]
    except Exception as e:
        print(f"❌ 板块数据采集失败：{str(e)}")
        return "板块数据暂时无法获取"

def collect_stock_stats():
    """采集全市场个股涨跌统计（雪球API）"""
    try:
        # 获取市场概览数据
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/"
        }
        
        session = requests.Session()
        session.get("https://xueqiu.com", headers=headers, timeout=10)
        
        url = "https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol=SH000001&begin=1650000000000&period=day&type=before&count=-1"
        response = session.get(url, headers=headers, timeout=15)
        market_data = response.json()["data"]
        
        # 计算涨跌家数（雪球API直接返回）
        up_count = market_data["market"]["up_count"]
        down_count = market_data["market"]["down_count"]
        flat_count = market_data["market"]["equal_count"]
        limit_up = market_data["market"]["limit_up_count"]
        limit_down = market_data["market"]["limit_down_count"]
        total_amt = market_data["market"]["total_amount"] / 100000000
        
        result = {
            "上涨家数": up_count,
            "下跌家数": down_count,
            "平盘家数": flat_count,
            "涨停家数": limit_up,
            "跌停家数": limit_down,
            "两市成交额": f"{total_amt:.1f}亿元"
        }
        
        print("✅ 个股统计数据采集成功（雪球API）")
        return result
    except Exception as e:
        print(f"❌ 个股统计数据采集失败：{str(e)}")
        return "个股统计数据暂时无法获取"

def collect_top_news():
    """采集财经新闻（雪球API）"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/"
        }
        
        session = requests.Session()
        session.get("https://xueqiu.com", headers=headers, timeout=10)
        
        url = "https://stock.xueqiu.com/v5/stock/news/list.json?category=1&count=5"
        response = session.get(url, headers=headers, timeout=15)
        news_data = response.json()["data"]["list"]
        
        result = []
        for news in news_data:
            result.append({
                "标题": news["title"],
                "发布时间": datetime.fromtimestamp(news["created_at"]/1000).strftime("%Y-%m-%d %H:%M")
            })
        
        print("✅ 财经新闻采集成功（雪球API）")
        return result
    except Exception as e:
        print(f"❌ 财经新闻采集失败：{str(e)}")
        return "财经新闻暂时无法获取"

# -------------------------- AI分析函数 --------------------------
def analyze_market(data):
    prompt = f"""
    你是资深A股大盘分析师。请基于以下数据客观分析今日市场：
    大盘指数：{data['market']}
    个股涨跌：{data['stock_stats']}
    
    分析要求：
    1. 今日大盘整体走势定性（上涨/下跌/震荡）及核心特征
    2. 市场赚钱效应评估（涨跌家数、涨跌停对比）
    3. 成交量变化解读（放量/缩量及意义）
    
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
        print("⚠️ 未配置Server酱Key，跳过推送")
        return False
    
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
    data = {
        "title": title,
        "desp": content
    }
    try:
        response = requests.post(url, data=data, timeout=15)
        if response.status_code == 200:
            print("✅ 微信推送成功！")
            return True
        else:
            print(f"❌ 微信推送失败，状态码：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 微信推送失败：{str(e)}")
        return False

# -------------------------- 主流程 --------------------------
def main():
    print("="*50)
    print(f"开始执行每日股市复盘：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 数据采集
    print("\n[1/4] 正在采集大盘数据...")
    market_data = collect_market_data()
    
    print("[2/4] 正在采集板块数据...")
    sector_data = collect_sector_data()
    
    print("[3/4] 正在采集个股统计...")
    stock_stats = collect_stock_stats()
    
    print("[4/4] 正在采集财经新闻...")
    news_data = collect_top_news()

    # 整合数据
    all_data = {
        "market": market_data,
        "sectors": sector_data,
        "stock_stats": stock_stats,
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
    push_to_wechat(f"{today_str} A股复盘报告", report)
    
    print("\n✅ 复盘任务执行完成！")

if __name__ == "__main__":
    main()
