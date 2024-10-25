from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    ImageSendMessage,
    TemplateSendMessage,
    CarouselTemplate,
    PostbackEvent,
    ButtonsTemplate,
    MessageAction,
)

from os import getenv

from utils.team_table import *
from utils.utils import *

line_bot_api = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
working_status = getenv("DEFALUT_TALKING", default="true").lower() == "true"

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
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    random_message(event)
    text_message(event)


def text_message(event):
    msg = event.message.text
    user_id = event.source.user_id
    try:
        profile = line_bot_api.get_profile(user_id)
        username = profile.display_name
    except LineBotApiError as e:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="Unknown user")
        )

    if msg == "uid":
        text = event.source.group_id
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg[:2].lower() == "yt":
        text = get_youtube(msg)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg[:2].lower() == "gg":
        status_code, img_src = get_google_image(msg)
        if status_code == 200:
            image_message = ImageSendMessage(
                original_content_url=img_src,  # Replace with the public URL of your image
                preview_image_url=img_src,  # Replace with the public URL of your image
            )
            line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "牢大":
        text = get_textfile("TextFiles/Mamba.txt")
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg == "規則":
        text = get_textfile("TextFiles/NBA_Rule.txt")
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg.lower() == "help":
        text = get_textfile("TextFiles/Help.txt")
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg.lower() == "nba":
        score_text = get_nba_scoreboard()
        text_message = TextSendMessage(text=score_text)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg == "NBA每日預測":
        user_id = event.source.user_id
        if username not in ["林家龍", "戴廣逸"]:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="傻狗給老子閉嘴")
            )
        else:
            try:
                text, columns = get_nba_match_prediction()
                if columns is None:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=text)
                    )
                else:
                    messages = [TextMessage(text=text)]
                    for i in range(0, len(columns), 10):
                        carousel_template = CarouselTemplate(
                            columns=columns[i : i + 10]
                        )
                        template_message = TemplateSendMessage(
                            alt_text="每日NBA預測", template=carousel_template
                        )
                        messages.append(template_message)

                    line_bot_api.reply_message(event.reply_token, messages)
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=str(e))
                )

    if msg == "結算":
        try:
            text = get_daily_predict_result()
            text_message = TextSendMessage(text=text[:-1])
            line_bot_api.reply_message(event.reply_token, text_message)
        except Exception as e:
            error_message = TextSendMessage(text=str(e))
            bot_message = TextSendMessage(
                text="?\n不是\n你們一個個天天都猴急什麼\n你們一急我又要上去查"
            )
            line_bot_api.reply_message(event.reply_token, [error_message, bot_message])

    if msg == "檢查":
        text = get_user_predict_check(username)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg[:2] == "信仰":
        text = get_user_most_belief(msg, username)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg[:2] == "傻鳥":
        text = get_user_most_hatred(msg, username)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "結算傻鳥":
        text = get_most_belief_hatred_team()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "NBA預測週最佳":
        best_users, type_rank = get_user_type_best("week")
        if best_users is None:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=type_rank)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(text=best_users), TextSendMessage(text=type_rank)],
            )

    if msg == "NBA預測月最佳":
        best_users, type_rank = get_user_type_best("month")
        if best_users is None:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=type_rank)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(text=best_users), TextSendMessage(text=type_rank)],
            )

    if msg == "NBA預測季最佳":
        best_users, type_rank = get_user_type_best("season")
        if best_users is None:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=type_rank)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(text=best_users), TextSendMessage(text=type_rank)],
            )

    if msg == "週排行":
        text = get_user_type_point("week")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "月排行":
        text = get_user_type_point("month")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "季排行":
        text = get_user_type_point("season")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "總排行":
        text = get_user_type_point("all-time")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg[:2] == "跟盤":
        text = get_others_prediction(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg[:2] == "傷病":
        text = get_team_injury(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "註冊":
        text = get_user_registered(username)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "NBA猜一猜":
        try:
            name, history_teams, history_game, history_stats = get_nba_guessing()
            # Define the buttons
            tip = "使用提示:\n生涯球隊: 球員生涯球隊\n上場時間: 先發場次/出場場次, 平均上場時間\n賽季平均: 得分/籃板/助攻/命中率"
            buttons_template = ButtonsTemplate(
                title="Menu",
                text="Please select",
                actions=[
                    MessageAction(label="生涯球隊", text=f"生涯球隊\n{history_teams}"),
                    MessageAction(label="上場時間", text=f"上場時間\n{history_game}"),
                    MessageAction(label="賽季平均", text=f"賽季平均\n{history_stats}"),
                    MessageAction(label="看答案", text=f"答案是 {name}"),
                ],
            )
            # Create the template message
            template_message = TemplateSendMessage(
                alt_text="NBA猜一猜",
                template=buttons_template,
            )

            line_bot_api.reply_message(
                event.reply_token, [TextSendMessage(text=tip), template_message]
            )
        except Exception as e:
            error_message = TextSendMessage(text=str(e))
            line_bot_api.reply_message(event.reply_token, error_message)


@line_handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    try:
        profile = line_bot_api.get_profile(user_id)
        username = profile.display_name
    except LineBotApiError as e:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="Unknown user")
        )

    """Get user prediction"""
    data = event.postback.data
    winner, loser, winner_point, loser_point = data.split()
    text = get_postback_message(username, winner, loser, winner_point, loser_point)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))


def random_message(event):
    msg = event.message.text

    if msg == "抽單字":
        text = get_textfile_random("TextFiles/TOEFL.txt")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "你媽":
        text = get_textfile_random("TextFiles/YourMom.txt")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

    if msg == "抽":
        image_url = get_random_picture("ZDcNFCL")
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=image_url, preview_image_url=image_url
            ),
        )

    if msg == "抽牌":
        image_url = get_random_picture("698HGtx")
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=image_url, preview_image_url=image_url
            ),
        )

    if msg == "大小":
        album_id = "1K6H3WS"
        image_url = get_random_picture("1K6H3WS")
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=image_url, preview_image_url=image_url
            ),
        )

    if msg == "兄弟":
        image_url = get_random_picture("tb0BGKk")
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=image_url, preview_image_url=image_url
            ),
        )


if __name__ == "__main__":
    app.run()
