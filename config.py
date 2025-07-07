from os import getenv
from linebot import LineBotApi, WebhookHandler


LINE_BOT_API = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
HANDLER = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
DATABASE_URL = "postgres://neondb_owner:npg_HL8gqNJc5kuf@ep-muddy-mountain-a4gxds6c-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
