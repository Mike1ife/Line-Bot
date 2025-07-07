from os import getenv
from linebot import LineBotApi, WebhookHandler


LINE_BOT_API = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
HANDLER = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
DATABASE_URL = getenv("DATABASE_URL")
