import os
import requests
import pandas as pd
import numpy as np
from langchain_openai import ChatOpenAI
from datetime import datetime
import akshare as ak
import warnings
warnings.filterwarnings("ignore")

# -------------------------- 配置部分（修改为你自己的模型ID） --------------------------
TIANYI_API_KEY = os.environ.get("TIANYI_API_KEY")
SERVER_CHAN_KEY = os.environ.get("SERVER_CHAN_KEY")

# 全球免费CORS代理列表（按稳定性排序，自动切换）
PROXIES = [
    "http://api.allorigins.win:80/raw?url={url}",
    "http://corsproxy.io:80/?{url}",
    "http://thingproxy.freeboard.io:80/fetch/{url}",
    "http://cors-proxy.fringe.zone:80/{url}",
    "http://proxy.cors.sh:80/{url}"
]

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

# -------------------------- AkShare代理自动切换工具 --------------------------
def set_akshare_proxy():
    """自动为AkShare设置可用的代理"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for proxy_template in PROXIES:
        try:
            # 测试代理是否可用
            test_url = proxy_template.format(url="https://www.baidu.com")
            response = requests.get(test_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 设置AkShare全局代理
            ak.proxy = proxy_template
            print(f"✅ AkShare代理设置成功：{proxy_template.split('//')[1].split('/')[0]}")
            return True
        except Exception as e:
            print(f"⚠️ 代理不可用：{proxy_template.split('//')[1].split('/')[0]}，错误：{str(e)[:50]}")
            continue
    
    print("❌ 所有代理均不可用，将尝试直连（可能失败）")
    ak.proxy = None
    return False

# -------------------------- 数据采集函数（纯AkShare接口） --------------------------
def collect_market_data():
    """采集大盘指数数据（AkShare新浪财经接口）"""
    try:
        set_akshare_proxy()
        index_df = ak.stock_zh_index_spot_sina()
        target_indexes = {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
            "sh000688": "科创50"
        }
        
        result = []
        for code, name in target_indexes.items():
            index_row = index_df[index_df["代码"] == code].iloc[0]
            result.append({
                "code": code,
                "name": name,
                "price": round(float(index_row["最新价"]), 2),
                "change": round(float(index_row["涨跌幅"]), 2),
                "volume": round(float(index_row["成交量"]) / 100000000, 2),
                "amount": round(float(index_row["成交额"]) / 100000000, 2)
            })
        
        print("✅ 大盘数据采集成功（AkShare+新浪财经）")
        return result
    except Exception as e:
        print(f"❌ 大盘数据采集失败：{str(e)}")
        return "大盘数据暂时无法获取"

def collect_sector_data():
    """采集申万一级行业数据（AkShare东方财富接口）"""
    try:
        set_akshare_proxy()
        sector_df = ak.stock_board_industry_name_em()
        result = sector_df[['板块名称', '涨跌幅', '主力净流入-净额']].head(10).to_dict('records')
        print("✅ 板块数据采集成功（AkShare+东方财富）")
        return result
    except Exception as e:
        print(f"❌ 板块数据采集失败：{str(e)}")
        return "板块数据暂时无法获取"

def collect_stock_stats():
    """采集全市场个股涨跌统计（AkShare东方财富接口）"""
    try:
        set_akshare_proxy()
        stock_df = ak.stock_zh_a_spot_em()
        up_count = len(stock_df[stock_df['涨跌幅'] > 0])
        down_count = len(stock_df[stock_df['涨跌幅'] < 0])
        flat_count = len(stock_df[stock_df['涨跌幅'] == 0])
        limit_up = len(stock_df[stock_df['涨跌幅'] >= 9.9])
        limit_down = len(stock_df[stock_df['涨跌幅'] <= -9.9])
        total_amt = stock_df['成交额'].sum() / 100000000
        
        result = {
            "上涨家数": up_count,
            "下跌家数": down_count,
            "平盘家数": flat_count,
            "涨停家数": limit_up,
            "跌停家数": limit_down,
            "两市成交额": f"{total_amt:.1f}亿元"
        }
        
        print("✅ 个股统计数据采集成功（AkShare+东方财富）")
        return result
    except Exception as e:
        print(f"❌ 个股统计数据采集失败：{str(e)}")
        return "个股统计数据暂时无法获取"

def collect_top_news():
    """采集财经新闻（AkShare东方财富接口）"""
    try:
        set_akshare_proxy()
        news_df = ak.stock_info_global_em()
        result = news_df[['标题', '发布时间']].head(5).to_dict('records')
        print("✅ 财经新闻采集成功（AkShare+东方财富）")
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
    
    print("\n[2/4] 正在采集板块数据...")
    sector_data = collect_sector_data()
    
    print("\n[3/4] 正在采集个股统计...")
    stock_stats = collect_stock_stats()
    
    print("\n[4/4] 正在采集财经新闻...")
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
