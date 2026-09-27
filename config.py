from os import getenv
from linebot import LineBotApi, WebhookHandler


LINE_BOT_API = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
HANDLER = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
DATABASE_URL = getenv("DATABASE_URL")
IMGUR_CLIENT_ID = getenv("IMGUR_CLIENT_ID")
GEMINI_API_KEY = getenv("GEMINI_API_KEY")
# Flash-Lite, not Flash. On the free tier the binding limit is requests per
# DAY, and the flagship Flash models allow only 20/day (5/min) versus 500/day
# (15/min) for Lite. Lite also answers in 1-2s rather than 4-5s and follows
# the 預測 output format just as reliably, so there is no quality reason to
# spend the scarce quota here.
GEMINI_MODEL = getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
# A second Lite model doubles the daily allowance to ~1000 requests and covers
# transient 503s. Avoid "-latest" aliases: they can resolve to a thinking model
# that spends the whole token budget reasoning and returns only MAX_TOKENS.
GEMINI_FALLBACK_MODEL = getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
