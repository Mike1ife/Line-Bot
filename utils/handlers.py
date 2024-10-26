from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

from config import line_bot_api
from utils.utils import get_postback_message
from utils.services import random_message, text_message


def handle_message(event):
    random_message(event)
    text_message(event)


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
