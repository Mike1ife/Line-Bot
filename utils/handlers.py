from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage, MessageEvent, PostbackEvent

from config import LINE_BOT_API
from utils.utils import (
    get_nba_prediction_posback,
    get_player_stat_prediction_postback,
)
from utils.services import text_message, random_message


def handle_message(event: MessageEvent):
    text_message(event=event)
    random_message(event=event)


def handle_postback(event: PostbackEvent):
    try:
        userUID = event.source.user_id
        profile = LINE_BOT_API.get_profile(userUID)
        userName = profile.display_name
    except LineBotApiError:
        LINE_BOT_API.reply_message(
            event.reply_token, TextSendMessage(text="Unknown User")
        )

    data = event.postback.data
    postbackType, *params = data.split(";")
    # NBA球隊預測: winner, loser, winner_point, loser_point, gametime(2025-3-18-11:51)
    # NBA球員預測: player, target, over_point, under_point, predict, match_time (Anthony Edwards 得分26.5 4 6 大盤 2025-3-18-11:51)
    if postbackType == "NBA球隊預測":
        response = get_nba_prediction_posback(userName, userUID * params)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))
    if postbackType == "NBA球員預測":
        response = get_player_stat_prediction_postback(userName, userUID * params)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))
