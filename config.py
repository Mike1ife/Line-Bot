from os import getenv
from linebot import LineBotApi, WebhookHandler


line_bot_api = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
DB_CONN_STR = getenv("DATABASE_URL")
