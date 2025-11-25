from linebot.exceptions import LineBotApiError
from linebot.models import (
    TextSendMessage,
    MessageEvent,
    PostbackEvent,
    CarouselTemplate,
    TemplateSendMessage,
)

from config import LINE_BOT_API
from utils.utils import (
    get_nba_game_prediction,
    get_player_stat_prediction,
    insert_nba_totay,
    get_nba_prediction_posback,
    get_player_stat_prediction_postback,
)
from utils.services import text_message, random_message


def handle_daily_prediction():
    pass
    # try:
    #     (
    #         matchList,
    #         response,
    #         matchColumns,
    #         gameOfTheDayPage,
    #         gameOfTheDayDate,
    #         gameOfTheDayTime,
    #     ) = get_nba_game_prediction(playoffsLayout=False)

    #     if not matchColumns:
    #         LINE_BOT_API.push_message(GID, TextSendMessage(text=response))
    #     else:
    #         statColumns, playerStatBetList = get_player_stat_prediction(
    #             gamePage=gameOfTheDayPage,
    #             gameDate=gameOfTheDayDate,
    #             gameTime=gameOfTheDayTime,
    #         )
    #         carouselColumns = matchColumns + statColumns
    #         respondMessages = [TextSendMessage(text=response)]
    #         for i in range(0, len(carouselColumns), 10):
    #             carouselTemplate = CarouselTemplate(columns=carouselColumns[i : i + 10])
    #             templateMessage = TemplateSendMessage(
    #                 alt_text="NBA每日預測", template=carouselTemplate
    #             )
    #             respondMessages.append(templateMessage)

    #         insert_nba_totay(matchList=matchList, playerStatBetList=playerStatBetList)
    #         LINE_BOT_API.push_message(GID, respondMessages)
    # except Exception as err:
    #     LINE_BOT_API.push_message(GID, TextSendMessage(text=str(err)))


def handle_message(event: MessageEvent):
    text_message(event=event)
    random_message(event=event)


def handle_postback(event: PostbackEvent):
    try:
        userUID = event.source.user_id
        profile = LINE_BOT_API.get_profile(userUID)
        userName = profile.display_name
        pictureUrl = profile.picture_url
    except LineBotApiError:
        LINE_BOT_API.reply_message(
            event.reply_token, TextSendMessage(text="Unknown User")
        )

    data = event.postback.data
    postbackType, *params = data.split(";")
    # NBA球隊預測: team1Name, team2Name, userPrediction, gameDate, gameTime
    # [國王, 灰狼, 灰狼, 2025-03-18, 11:00]
    # NBA球員預測: playerName, team1Name, team2Name statType, statTarget, userPrediction(大盤/小盤), gameDate, gameTime
    # [Anthony Edwards, 國王, 灰狼, 得分, 26.5, 大盤, 2025-03-18, 11:00]
    if postbackType == "NBA球隊預測":
        response = get_nba_prediction_posback(userName, userUID, pictureUrl, *params)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))
    if postbackType == "NBA球員預測":
        response = get_player_stat_prediction_postback(
            userName, userUID, pictureUrl, *params
        )
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))
