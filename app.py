from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
import json
from flask import Flask

   # 替換成你的 LINE 認證資訊（後續步驟會獲取）
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
       if user_input.startswith("查詢:"):
           district = user_input.replace("查詢:", "").strip()
           # 過濾臺北市的公園
           taipei_parks = [p for p in parks if p["city"] == "臺北市" and p["district"] == district]
           if taipei_parks:
               response = f"【{district} 公園列表】\n"
               for park in taipei_parks:
                   response += f"- {park['name']}: 器材 {', '.join(park['equipment']) if park['equipment'] else '無'}\n"
           else:
               response = f"沒有找到 {district} 的公園資料！"
           line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
       else:
           line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入「查詢:行政區」來查詢公園！\n例如：查詢:大安區"))

if __name__ == "__main__":
    app.run()