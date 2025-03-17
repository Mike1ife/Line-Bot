from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

from config import line_bot_api
from utils.utils import (
    get_nba_match_prediction_postback,
    get_player_stat_prediction_postback,
)
from utils.services import text_message, random_message


def handle_message(event):
    text_message(event)
    random_message(event)


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
    # NBA球隊預測: winner, loser, winner_point, loser_point, gametime
    # NBA球員預測: player, target, over_point, under_point, predict (Anthony Edwards 得分26.5 4 6 大盤)
    postback_type, *params = data.split(";")
    if postback_type == "NBA球隊預測":
        text = get_nba_match_prediction_postback(username, *params)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
    elif postback_type == "NBA球員預測":
        text = get_player_stat_prediction_postback(username, *params)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
