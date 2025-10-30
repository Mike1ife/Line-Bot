from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    PostbackEvent,
)

from config import HANDLER
from utils.api import *
from utils.handlers import handle_message, handle_postback, handle_daily_prediction

app = Flask(__name__)
CORS(app)


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/api/leaderboard/user_day_point", methods=["GET"])
def get_user_day_point():
    response = get_user_info_and_type_point("day_points")
    return jsonify(response)


@app.route("/api/leaderboard/user_week_point", methods=["GET"])
def get_user_week_point():
    response = get_user_info_and_type_point("week_points")
    return jsonify(response)


@app.route("/api/leaderboard/user_month_point", methods=["GET"])
def get_user_month_point():
    response = get_user_info_and_type_point("month_points")
    return jsonify(response)


@app.route("/api/leaderboard/user_season_point", methods=["GET"])
def get_user_season_point():
    response = get_user_info_and_type_point("season_points")
    return jsonify(response)


@app.route("/api/leaderboard/user_all_time_point", methods=["GET"])
def get_user_all_time_point():
    response = get_user_info_and_type_point("all_time_points")
    return jsonify(response)


@app.route("/api/cron", methods=["GET", "POST"])
def cron_job():
    handle_daily_prediction()


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
