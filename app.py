from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from linebot.exceptions import InvalidSignatureError
import os
import json
from flask import Flask, request, abort

# 替換成你的 LINE 認證資訊
LINE_CHANNEL_ACCESS_TOKEN = "xY8MaHCSk0k8iAKz0YRGv09XDcZAtDkDfelgmxjq253w/Eu/o98shf/heH38tD1pG4ApFd4VlgGza0EZoIvnaCjOicxdsiqUT7i0oQtZzUTRQmw/v+W4F9vuZrrVfgFCeG/Zb/COHiA1v+hgRqdepgdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "42f728017abc43d652ce8678c2487eaf"
app = Flask(__name__)
REURL_API_TOKEN = os.getenv("REURL_API_TOKEN", "4070ff49d794e73211543b663c974755ecd7b739979f04df8a38b58d65165567c4f5d6")
# 初始化 LINE Bot
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== 縮網址工具 =====
def is_short_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://reurl.cc/")

def shorten_url(url: str) -> str:
    """使用 reurl.cc API 縮短單一網址；若已縮或失敗則回傳原網址"""
    if not url or not isinstance(url, str):
        return url
    if is_short_url(url):
        return url

    api_url = "https://api.reurl.cc/shorten"
    headers = {
        "Content-Type": "application/json",
        "reurl-api-key": REURL_API_TOKEN
    }
    payload = {"url": url}

    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        return data.get("short_url", url)
    except Exception as e:
        print(f"[reurl] 縮網址失敗：{e}")
        return url


def load_parks() -> list:
    if not os.path.exists(PARKS_FILE):
        print(f"[init] 找不到 {PARKS_FILE}，將使用空清單")
        return []
    with open(PARKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_parks(parks: list) -> None:
    with open(PARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(parks, f, ensure_ascii=False, indent=2)

def shorten_all_map_links_once(parks: list) -> int:
    """啟動時批次縮址，避免重複浪費額度"""
    # 收集需要縮的網址
    to_shorten = []
    for p in parks:
        url = p.get("map_link")
        if url and isinstance(url, str) and not is_short_url(url):
            to_shorten.append(url)
    unique_long_urls = list(set(to_shorten))

    if not unique_long_urls:
        print("[init] 沒有需要縮短的網址")
        return 0

    print(f"[init] 需要縮短的唯一網址數量：{len(unique_long_urls)}")

    # 建立對照表
    mapping = {}
    for long_url in unique_long_urls:
        mapping[long_url] = shorten_url(long_url)

    # 回寫 parks
    updated = 0
    for p in parks:
        url = p.get("map_link")
        if url in mapping and mapping[url] != url:
            p["map_link"] = mapping[url]
            updated += 1

    print(f"[init] 完成縮短並更新的項目數：{updated}")
    return updated


# ===== 啟動前：縮短並更新 parks.json =====
parks = load_parks()
updated_count = shorten_all_map_links_once(parks)
if updated_count > 0:
    save_parks(parks)
    print(f"[init] 已將縮短結果永久寫回 {PARKS_FILE}")
else:
    print("[init] 無需更新 parks.json")
# 載入 parks.json（假設已存在）
with open('parks.json', 'r', encoding='utf-8') as f:
    parks = json.load(f)

# 處理使用者訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    if user_input.startswith("查詢") and (":" in user_input or "：" in user_input):
        # 移除 "查詢" 並統一處理冒號
        query = user_input.replace("查詢", "").replace("：", ":").replace(":", "").strip()
        parts = query.split()  # 分割為行政區和器材
        district = parts[0] if parts else ""
        equipment = parts[1] if len(parts) > 1 else None

        taipei_parks = [p for p in parks if p["city"] == "臺北市" and p["district"] == district]
        if taipei_parks:
            if equipment:
                # 過濾有特定器材的公園，考慮數量格式
                filtered_parks = [p for p in taipei_parks if any(equipment in eq for eq in p.get("equipment", []))]
                if filtered_parks:
                    response = f"【{district} 公園列表有 {equipment}】\n\n"
                    for park in filtered_parks:
                        response += f"- {park['name']}：\n"
                        response += f"  地址 {park.get('map_link', '無地圖連結')}\n"
                        response += f"  器材 {', '.join(park['equipment']) if park['equipment'] else '無'}\n\n"
                else:
                    response = f"【{district}】沒有公園提供 {equipment}：！"
            else:
                response = f"【{district} 公園列表】\n\n"
                for park in taipei_parks:
                    response += f"- {park['name']}：\n"
                    response += f"  地址 {park.get('map_link', '無地圖連結')}\n"
                    response += f"  器材 {', '.join(park['equipment']) if park['equipment'] else '無'}\n\n"
        else:
            response = f"沒有找到 {district} 的公園資料：！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入「查詢：行政區 [器材]」來查詢公園！\n例如：查詢：大安區 漫步器"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # 與 Render 檢測的端口一致
    app.run(host='0.0.0.0', port=port)
