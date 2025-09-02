from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from linebot.exceptions import InvalidSignatureError
from flask import Flask, request, abort
import os
import json
import requests

# 替換成你的 LINE 認證資訊
LINE_CHANNEL_ACCESS_TOKEN = "你的_LINE_CHANNEL_ACCESS_TOKEN"
LINE_CHANNEL_SECRET = "你的_LINE_CHANNEL_SECRET"
REURL_API_TOKEN = "你的_reurl_api_token"

app = Flask(__name__)
# 初始化 LINE Bot
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def shorten_url(url):
    """使用 reurl.cc API 縮短網址"""
    if not url or url == "無地圖連結":
        return url
    api_url = "https://api.reurl.cc/shorten"
    headers = {
        "Content-Type": "application/json",
        "reurl-api-key": REURL_API_TOKEN
    }
    payload = {"url": url}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=5)
        result = response.json()
        if result.get("short_url"):
            return result["short_url"]
        else:
            return url
    except Exception as e:
        print("縮網址失敗:", e)
        return url


# 載入 parks.json 並縮短所有網址
with open("parks.json", "r", encoding="utf-8") as f:
    parks = json.load(f)

for park in parks:
    if "map_link" in park:
        park["map_link"] = shorten_url(park["map_link"])

# 如果要把縮短結果存回 parks.json（避免下次重複縮），可以啟用這行
# with open("parks.json", "w", encoding="utf-8") as f:
#     json.dump(parks, f, ensure_ascii=False, indent=2)


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
                # 過濾有特定器材的公園
                filtered_parks = [p for p in taipei_parks if any(equipment in eq for eq in p.get("equipment", []))]
                if filtered_parks:
                    response = f"【{district} 公園列表有 {equipment}】\n\n"
                    for park in filtered_parks:
                        response += f"- {park['name']}：\n"
                        response += f"  地址 {park.get('map_link', '無地圖連結')}\n"
                        response += f"  器材 {', '.join(park['equipment']) if park['equipment'] else '無'}\n\n"
                else:
                    response = f"【{district}】沒有公園提供 {equipment}！"
            else:
                response = f"【{district} 公園列表】\n\n"
                for park in taipei_parks:
                    response += f"- {park['name']}：\n"
                    response += f"  地址 {park.get('map_link', '無地圖連結')}\n"
                    response += f"  器材 {', '.join(park['equipment']) if park['equipment'] else '無'}\n\n"
        else:
            response = f"沒有找到 {district} 的公園資料！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入「查詢：行政區 [器材]」來查詢公園！\n例如：查詢：大安區 漫步器")
        )


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # 與 Render 檢測的端口一致
    app.run(host="0.0.0.0", port=port)
