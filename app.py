from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    PostbackEvent,
)
from urllib.parse import unquote

from config import HANDLER
from api.api import *
from utils.handlers import handle_message, handle_postback

app = Flask(__name__)
CORS(app)


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/api/home/leaderboard/<rankType>", methods=["GET"])
def get_user_day_point(rankType: str):
    response = get_user_info_and_type_point(rankType)
    return jsonify(response)


@app.route("/api/home/nba_today", methods=["GET"])
def get_nba_today():
    response = get_daily_match_info()
    return jsonify(response)


@app.route("/api/users/<userName>", methods=["GET"])
def get_user_profile(userName: str):
    userName = unquote(userName)
    response = fetch_user_profile(userName=userName)
    return jsonify(response)


@app.route("/api/users/<userName>/points/<rankType>", methods=["GET"])
def get_user_point_history(userName: str, rankType: str):
    userName = unquote(userName)
    response = fetch_user_point_history(userName=userName, rankType=rankType)
    return jsonify(response)


@app.route("/api/users/<userName>/count/<countType>/<countRange>", methods=["GET"])
def get_user_counter(userName: str, countType: str, countRange: str):
    # countType: correct / wrong
    # countRange: season / all_time
    userName = unquote(userName)
    response = fetch_user_counter(
        userName=userName, countType=countType, countRange=countRange
    )
    return jsonify(response)


@app.route("api/users", methods=["GET"])
def get_users():
    response = fetch_users()
    return jsonify(response)


@app.route("/api/cron", methods=["GET"])
def cron_job():
    pass


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
