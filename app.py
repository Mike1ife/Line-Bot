from flask import Flask, request, abort
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    PostbackEvent,
)

from config import HANDLER
from utils.handlers import handle_message, handle_postback

app = Flask(__name__)


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/api/cron", methods=["GET", "POST"])
def cron_job():
    return "Cron job executed successfully!"


@app.route("/webhook", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        HANDLER.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


HANDLER.add(MessageEvent, message=TextMessage)(handle_message)
HANDLER.add(PostbackEvent)(handle_postback)

if __name__ == "__main__":
    app.run()
