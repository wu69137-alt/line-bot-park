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
# 初始化 LINE Bot
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 載入 parks.json（假設已存在）
with open('parks.json', 'r', encoding='utf-8') as f:
    parks = json.load(f)

# 處理使用者訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    if user_input.startswith("查詢") and (":" in user_input or "：" in user_input):
        # 移除 "查詢" 並統一處理冒號
        query = user_input.replace("查詢", "").replace("：", ":").split(":", 1)[-1].strip()
        parts = query.split()

        # 支援縣市 + 行政區 + 可選器材
        city = parts[0] if len(parts) > 0 else ""
        district = parts[1] if len(parts) > 1 else ""
        equipment = parts[2] if len(parts) > 2 else None

        # 篩選符合條件的公園
        filtered_parks = [p for p in parks if p.get("city") == city and p.get("district") == district]

        if not filtered_parks:
            response = f"沒有找到 {city} {district} 的公園資料！"
        else:
            if equipment:
                # 過濾有特定器材的公園
                filtered_parks = [p for p in filtered_parks if any(equipment in eq for eq in p.get("equipment", []))]
                if not filtered_parks:
                    response = f"【{city} {district}】沒有公園提供 {equipment}！"
                else:
                    response = f"【{city} {district} 公園列表有 {equipment}】\n\n"
            else:
                response = f"【{city} {district} 公園列表】\n\n"

            # 建立回覆文字
            lines = []
            for park in filtered_parks:
                name = park.get("name") or "（未命名）"
                link = park.get("map_link") or "無地圖連結"
                equip_list = park.get("equipment") or []
                equip_text = ", ".join(equip_list) if equip_list else "無"
                lines.append(f"- {name}：")
                lines.append(f"  地圖 {link}")
                lines.append(f"  器材 {equip_text}\n")
            response += "\n".join(lines)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入「查詢：縣市 行政區 [器材]」來查詢公園！\n例如：查詢：臺北市 大安區 漫步器")
        )


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
