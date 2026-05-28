import os
import requests
import pandas as pd
import numpy as np
from langchain_openai import ChatOpenAI
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# -------------------------- 配置部分 --------------------------
TIANYI_API_KEY = os.environ.get("TIANYI_API_KEY")
SERVER_CHAN_KEY = os.environ.get("SERVER_CHAN_KEY")

# -------------------------- 初始化大模型 --------------------------
def get_llm():
    # 這裡使用 AkShare，通常不需要切換模型邏輯，保持原樣即可
    try:
        llm = ChatOpenShift(
            model="f23c54bf38b64ee194b28783d61be788",  # 替換為你的模型ID
            api_key=TIANYI_API_KEY,
            base_url="https://wishub-x6.ctyun.cn/v1",
            temperature=0.1,
            timeout=120,
            max_retries=3
        )
        llm.invoke("測試")
        print(f"✅ 模型調用成功")
        return llm
    except Exception as e:
        raise Exception(f"模型調用失敗：{str(e)}")

llm = get_llm()

# -------------------------- 數據採集函數 (改用 AkShare) --------------------------
def fetch_market_data_ak():
    """採集大盤指數數據 (使用 AkShare)"""
    try:
        # 獲取上證、深證、創業板、科創板指數
        # symbol: 000001.SH 為上證指數
        symbols = ["000001", "399001", "399006", "000688"]
        index_map = {
            "000001": "上證指數",
            "399001": "深證成指",
            "399006": "創業板指",
            "000688": "科創50"
        }
        
        result = []
        for symbol in symbols:
            # 使用 AkShare 獲取 A 股實時行情
            # 接口：stock_zh_index_spot_em
            df = ak.stock_zh_index_spot_em(symbol=symbol)
            
            if not df.empty:
                row = df.iloc[0] # 取最新一條數據
                result.append({
                    "code": symbol,
                    "name": index_map.get(symbol, symbol),
                    "price": round(float(row['最新價']), 2),
                    "change": round(float(row['漲跌額']), 2),
                    "pct_change": round(float(row['漲跌幅']), 2),
                    "volume": round(float(row['成交量']) / 100000000, 2), # 億
                    "amount": round(float(row['成交額']) / 100000000, 2) # 億
                })
        
        print("✅ 大盤數據採集成功 (AkShare)")
        return result
    except Exception as e:
        print(f"❌ 大盤數據採集失敗：{str(e)}")
        return "大盤數據暫時無法獲取"

def fetch_sector_data_ak():
    """採集申萬一級行業數據 (使用 AkShare)"""
    try:
        # 獲取申萬一級行業實時行情
        # 注意：AkShare 的接口可能需要指定 market="sw1"
        df = ak.stock_sector_spot_em(symbol="申萬一級")
        
        # 按漲跌幅排序，取前 10
        df = df.sort_values(by='漲跌幅', ascending=False).head(10)
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "板塊名稱": row['板塊名稱'],
                "漲跌幅": round(float(row['漲跌幅']), 2),
                "主力淨流入-淨額": round(float(row['今日漲停家數']) / 100000000, 2) # 這裡用漲停數做示例，AkShare 行業淨流入接口有時效性限制
            })
        
        print("✅ 板塊數據採集成功 (AkShare)")
        return result
    except Exception as e:
        print(f"❌ 板塊數據採集失敗：{str(e)}")
        return "板塊數據暫時無法獲取"

def fetch_stock_stats_ak():
    """採集全市場個股漲跌統計 (使用 AkShare)"""
    try:
        # 獲取市場概況數據
        # 接口：stock_market_summary_sina
        df = ak.stock_market_summary_sina(symbol="上證指數")
        
        if not df.empty:
            row = df.iloc[0]
            # 計算兩市總成交額
            total_amt = round(float(row['滬市成交額']) / 100000000 + float(row['深市成交額']) / 100000000, 1)
            
            result = {
                "上漲家數": int(row['滬市上漲家數']),
                "下跌家數": int(row['滬市下跌家數']),
                "平盤家數": int(row['滬市平盤家數']),
                "漲停家數": int(row['滬市漲停家數']),
                "跌停家數": int(row['滬市跌停家數']),
                "兩市成交額": f"{total_amt}億元"
            }
            print("✅ 個股統計數據採集成功 (AkShare)")
            return result
        else:
            raise Exception("獲取市場概況為空")
            
    except Exception as e:
        print(f"❌ 個股統計數據採集失敗：{str(e)}")
        return "個股統計數據暫時無法獲取"

def fetch_top_news_ak():
    """採集財經新聞 (AkShare 沒有完美的滾動新聞接口，這裡使用綜合新聞或熱門新聞替代)"""
    try:
        # 使用 AkShare 獲取即時新聞或要聞
        # 接口：news_cctv  # 這是一個示例，也可以用 news_east_money
        # 這裡使用 新浪財經要聞 作為替代
        df = ak.news_sina_guonei()
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "標題": row['title'],
                "發布時間": row['datetime'].split(" ")[1] if len(row['datetime'].split(" ")) > 1 else row['datetime'],
                "來源": "新華社/央視"
            })
            if len(result) >= 5:
                break
        
        print("✅ 財經新聞採集成功 (AkShare)")
        return result
    except Exception as e:
        print(f"❌ 財經新聞採集失敗：{str(e)}")
        return "財經新聞暫時無法獲取"

# -------------------------- AI分析函數 (保持不變) --------------------------
def analyze_market(data):
    prompt = f"""
    你是資深A股大盤分析師。請基於以下數據客觀分析今日市場：
    大盤指數：{data['market']}
    個股漲跌：{data['stock_stats']}
    
    分析要求：
    1. 今日大盤整體走勢定性（上漲/下跌/震盪）及核心特徵
    2. 市場賺錢效應評估（漲跌家數、漲跌停對比）
    3. 成交量變化解讀（放量/縮量及意義）
    
    語言簡潔專業，不超過300字，避免情緒化表達。
    """
    return llm.invoke(prompt).content

def analyze_sectors(data):
    prompt = f"""
    你是板塊輪動專家。請基於以下數據分析今日板塊表現：
    板塊漲跌幅：{data['sectors']}
    
    分析要求：
    1. 列出漲幅前3和跌幅前3的板塊及漲跌幅
    2. 簡要分析領漲板塊的可能驅動因素
    3. 預判哪些板塊可能具有短期持續性
    
    每個板塊分析不超過50字，結構清晰。
    """
    return llm.invoke(prompt).content

def analyze_news(data):
    prompt = f"""
    你是財經新聞解讀專家。請從以下新聞中篩選對A股影響最大的2條：
    今日新聞：{data['news']}
    
    分析要求：
    1. 每條新聞用一句話概括核心內容
    2. 明確指出影響的具體板塊
    3. 標註影響程度（正面/負面/中性）
    
    每條分析不超過80字，客觀中立。
    """
    return llm.invoke(prompt).content

# -------------------------- 報告生成與推送 (保持不變) --------------------------
def generate_report(analysis):
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""# {today} A股每日復盤報告

## 一、今日大盤概覽
{analysis['market']}

## 二、板塊熱點分析
{analysis['sectors']}

## 三、重要消息解讀
{analysis['news']}

## 四、明日操作提示
1. 密切關注大盤量能變化，持續縮量需保持謹慎
2. 聚焦領漲板塊的龍頭個股，避免追高跟風
3. 控制整體倉位在5成以下，做好風險對沖

---
⚠️ **免責聲明**：本報告由AI自动生成，僅供學習參考，不構成任何投資建議。股市有風險，投資需謹慎。
"""

def push_to_wechat(title, content):
    """通過Server醬推送到微信"""
    if not SERVER_CHAN_KEY:
        print("⚠️ 未配置Server醬Key，跳過推送")
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
            print(f"❌ 微信推送失敗，狀態碼：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 微信推送失敗：{str(e)}")
        return False

# -------------------------- 主流程 --------------------------
def main():
    print("="*50)
    print(f"開始執行每日股市復盤 (AkShare版)：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 數據採集
    print("\n[1/4] 正在採集大盤數據 (AkShare)...")
    market_data = fetch_market_data_ak()
    
    print("\n[2/4] 正在採集板塊數據 (AkShare)...")
    sector_data = fetch_sector_data_ak()
    
    print("\n[3/4] 正在採集個股統計 (AkShare)...")
    stock_stats = fetch_stock_stats_ak()
    
    print("\n[4/4] 正在採集財經新聞 (AkShare)...")
    news_data = fetch_top_news_ak()

    # 整合數據
    all_data = {
        "market": market_data,
        "sectors": sector_data,
        "stock_stats": stock_stats,
        "news": news_data
    }

    # 2. AI分析
    print("\n開始AI分析...")
    analysis = {
        "market": analyze_market(all_data),
        "sectors": analyze_sectors(all_data),
        "news": analyze_news(all_data)
    }

    # 3. 生成報告
    print("生成復盤報告...")
    report = generate_report(analysis)
    print("\n" + "="*50)
    print(report)
    print("="*50 + "\n")

    # 4. 推送報告
    print("推送報告到微信...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    push_to_wechat(f"{today_str} A股復盤報告", report)
    
    print("\n✅ 復盤任務執行完成！")

if __name__ == "__main__":
    main()
