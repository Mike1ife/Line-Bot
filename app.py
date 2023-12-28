from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

import os
import requests
import random

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
working_status = os.getenv("DEFALUT_TALKING", default="true").lower() == "true"

app = Flask(__name__)


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/webhook", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


CLIENT_ID = "427bae956e65de4"
ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"
endpoint = "https://api.imgur.com/3/account/me/images"
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}


@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # echo
    msg = event.message.text

    if msg == "抽":
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = random.choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)


if __name__ == "__main__":
    app.run()
