import requests
from datetime import datetime

# 配置区（这些值我们会从环境变量读，不再硬编码）
import os

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
JUHE_API_KEY = os.environ.get("JUHE_API_KEY")
WECHAT_WEBHOOK = os.environ.get("WECHAT_WEBHOOK")

def fetch_financial_news():
    # 获取财经新闻（和之前一样，但加上环境变量读取）
    print("[1/3] 正在获取财经新闻...")
    url = "http://v.juhe.cn/toutiao/index"
    params = {"type": "caijing", "key": JUHE_API_KEY, "page_size": 20}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("error_code") == 0:
            articles = data["result"]["data"]
            news_list = []
            for a in articles:
                news_list.append({
                    "title": a.get("title", ""),
                    "source": a.get("author_name", "未知来源"),
                    "time": a.get("date", ""),
                    "url": a.get("url", ""),
                })
            print(f"  获取 {len(news_list)} 条")
            return news_list
        else:
            print(f"  新闻API错误: {data.get('reason')}")
            return fallback_news()
    except Exception as e:
        print(f"  请求失败: {e}")
        return fallback_news()

def fallback_news():
    # 备用源（之前写的）
    print("  使用备用源...")
    try:
        resp = requests.get(
            "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        data = resp.json()
        news_list = []
        for item in data.get("data", {}).get("roll_data", [])[:15]:
            news_list.append({
                "title": item.get("title", ""),
                "source": "财联社",
                "time": datetime.fromtimestamp(item.get("ctime", 0)).strftime("%Y-%m-%d %H:%M"),
                "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
            })
        return news_list
    except:
        return []

def deepseek_summarize(news_list):
    print("[2/3] 调用 DeepSeek 整理...")
    if not news_list:
        return "今日暂无重要财经新闻。"
    raw_text = "\n---\n".join([
        f"【第{i+1}条】{n['title']}\n来源：{n['source']} | {n['time']}\n链接：{n['url']}"
        for i, n in enumerate(news_list)
    ])
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""你是资深财经编辑。请把以下今日财经新闻整理成精炼早报。

要求：
1. 标题用「📊 每日财经早报 | {datetime.now().strftime('%Y年%m月%d日')}」
2. 三部分：🏛️ 宏观要闻（3-4条一句话）、🏭 行业与公司（3-5条）、🔍 市场观察（1-2句）
3. 每条含原文链接
4. 结尾用「📌 今日关注」
5. Markdown 格式

新闻：
{raw_text}"""
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "专业财经编辑，回复干净、高密度。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  DeepSeek 错误: {e}")
        return f"日报生成失败：{e}"

def send_wechat(content):
    print("[3/3] 推送到微信...")
    full_text = f"# 📊 每日财经早报 | {datetime.now().strftime('%m月%d日')}\n\n{content}"
    if len(full_text) > 4000:
        # 分片发送
        mid = len(full_text) // 2
        send_single(full_text[:mid])
        send_single(full_text[mid:])
    else:
        send_single(full_text)

def send_single(text):
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": text[:4000]}
    }
    try:
        resp = requests.post(WECHAT_WEBHOOK, json=payload, timeout=10)
        if resp.json().get("errcode") == 0:
            print("  推送成功")
        else:
            print(f"  微信错误: {resp.json()}")
    except Exception as e:
        print(f"  推送失败: {e}")

if __name__ == "__main__":
    print("🚀 开始执行财经早报任务...")
    news = fetch_financial_news()
    report = deepseek_summarize(news)
    send_wechat(report)
    print("✅ 完成")
