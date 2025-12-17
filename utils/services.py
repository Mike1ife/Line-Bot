import time
from linebot.models import (
    TextSendMessage,
    ImageSendMessage,
    TemplateSendMessage,
    CarouselTemplate,
    MessageEvent,
)
from linebot.exceptions import LineBotApiError

from config import LINE_BOT_API
from utils.utils import *

SETTLE_PATTERN = re.compile(r"^結算(?: ([^\s]+))?$")
CORRECT_PATTERN = re.compile(r"^信仰(?: ([^\s]+))?$")
WRONG_PATTERN = re.compile(r"^傻鳥(?: ([^\s]+))?$")
FOLLOW_PATTERN = re.compile(r"^跟盤(?: ([^\s]+))?$")
COMPARE_PATTERN = re.compile(r"^比較(?: ([^\s]+)(?: ([^\s]+))?)?$")
INJURY_PATTERN = re.compile(r"^傷病(?: ([^\s]+))?$")
YT_PATTERN = re.compile(r"^yt (.+)$")
GG_PATTERN = re.compile(r"^gg (.+)$")
AI_PATTERN = re.compile(r"^ai (.+)$")


def text_message(event: MessageEvent):
    message = event.message.text
    try:
        userUID = event.source.user_id
        profile = LINE_BOT_API.get_profile(userUID)
        userName = profile.display_name
        pictureUrl = profile.picture_url
    except LineBotApiError:
        LINE_BOT_API.reply_message(
            event.reply_token, TextSendMessage(text="Unknown User")
        )

    if message == "清除NBA每日預測":
        if not user_is_admin(userUID):
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text="傻狗給老子閉嘴")
            )
        try:
            remove_active_match()
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text="清除NBA每日預測成功")
            )
        except Exception as err:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=str(err))
            )

    if message == "收集每日比賽預測":
        start = time.time()
        if not user_is_admin(userUID):
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text="傻狗給老子閉嘴")
            )
        try:
            end = time.time()
            gather_nba_game_prediction_match_parallel(playoffsLayout=False)
            LINE_BOT_API.reply_message(
                event.reply_token,
                TextSendMessage(text=f"收集每日比賽預測完成 ({end - start}s)"),
            )
        except Exception as err:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=str(err))
            )

    if message == "收集每日數據預測":
        start = time.time()
        if not user_is_admin(userUID):
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text="傻狗給老子閉嘴")
            )
        try:
            gather_nba_game_prediction_stat_optimized()
            end = time.time()
            LINE_BOT_API.reply_message(
                event.reply_token,
                TextSendMessage(text=f"收集每日數據預測完成 ({end - start}s)"),
            )
        except Exception as err:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=str(err))
            )

    if message == "NBA每日預測":
        if not user_is_admin(userUID):
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text="傻狗給老子閉嘴")
            )
        try:
            response, carouselColumns = get_nba_game_prediction()

            if not carouselColumns:
                LINE_BOT_API.reply_message(
                    event.reply_token, TextSendMessage(text=response)
                )
            else:
                respondMessages = [TextSendMessage(text=response)]
                for i in range(0, len(carouselColumns), 10):
                    carouselTemplate = CarouselTemplate(
                        columns=carouselColumns[i : i + 10]
                    )
                    templateMessage = TemplateSendMessage(
                        alt_text="NBA每日預測", template=carouselTemplate
                    )
                    respondMessages.append(templateMessage)
                LINE_BOT_API.reply_message(event.reply_token, respondMessages)
        except Exception as err:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=str(err))
            )

    if message == "檢查":
        response = get_user_prediction_check(userName=userName)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    settleMatch = SETTLE_PATTERN.match(message)
    if settleMatch:
        try:
            source = settleMatch.group(1) if settleMatch.group(1) else "hupu"
            if source not in ("hupu", "fox"):
                LINE_BOT_API.reply_message(
                    event.reply_token, TextSendMessage(text=response)
                )
            response = settle_daily_prediction(source=source)
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=response)
            )
        except Exception as err:
            errorMessage = TextSendMessage(text=str(err))
            respondMessage = TextSendMessage(
                text="?\n不是\n你們一個個天天都猴急什麼\n你們一急我又要上去查"
            )
            LINE_BOT_API.reply_message(
                event.reply_token, [errorMessage, respondMessage]
            )

    correctMatch = CORRECT_PATTERN.match(message)
    if correctMatch:
        teamName = correctMatch.group(1) if correctMatch.group(1) else ""
        response = get_user_season_correct_count(userName=userName, teamName=teamName)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    wrongMatch = WRONG_PATTERN.match(message)
    if wrongMatch:
        teamName = wrongMatch.group(1) if wrongMatch.group(1) else ""
        response = get_user_season_wrong_count(userName=userName, teamName=teamName)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "結算傻鳥":
        response = get_season_most_correct_and_wrong()
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "週排行":
        response = get_user_type_point("week_points")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "月排行":
        response = get_user_type_point("month_points")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "季排行":
        response = get_user_type_point("season_points")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "總排行":
        response = get_user_type_point("all_time_points")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    followMatch = FOLLOW_PATTERN.match(message)
    if followMatch:
        userId = (
            int(followMatch.group(1))
            if followMatch.group(1) and followMatch.group(1).isdigit()
            else -1
        )
        response = get_prediction_by_id(userId=userId)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    compareMatch = COMPARE_PATTERN.match(message)
    if compareMatch:
        user1Id, user2Id = (
            (int(compareMatch.group(1)), int(compareMatch.group(2)))
            if compareMatch.group(1)
            and compareMatch.group(2)
            and compareMatch.group(1).isdigit()
            and compareMatch.group(2).isdigit()
            else (-1, -1)
        )
        response = get_prediction_comparison(user1Id=user1Id, user2Id=user2Id)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "註冊":
        response = user_registration(
            userUID=userUID, userName=userName, pictureUrl=pictureUrl
        )
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "NBA預測週最佳":
        bestMessage, rankMessage = get_user_type_best("week_points")
        if bestMessage:
            LINE_BOT_API.reply_message(
                event.reply_token,
                [TextSendMessage(text=bestMessage), TextSendMessage(text=rankMessage)],
            )
        else:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=rankMessage)
            )

    if message == "NBA預測月最佳":
        bestMessage, rankMessage = get_user_type_best("month_points")
        if bestMessage:
            LINE_BOT_API.reply_message(
                event.reply_token,
                [TextSendMessage(text=bestMessage), TextSendMessage(text=rankMessage)],
            )
        else:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=rankMessage)
            )

    if message == "NBA預測季最佳":
        bestMessage, rankMessage = get_user_type_best("season_points")
        if bestMessage:
            LINE_BOT_API.reply_message(
                event.reply_token,
                [TextSendMessage(text=bestMessage), TextSendMessage(text=rankMessage)],
            )
        else:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=rankMessage)
            )

    if message == "NBA猜一猜":
        try:
            usage, buttonsTemplate = get_nba_guessing()
            LINE_BOT_API.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text=usage),
                    TemplateSendMessage(
                        alt_text="NBA猜一猜",
                        template=buttonsTemplate,
                    ),
                ],
            )
        except Exception as err:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=str(err))
            )

    if message.lower() == "news":
        response = get_hupu_news()
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    ytMatch = YT_PATTERN.match(message.lower())
    if ytMatch:
        response = get_youtube(keyword=ytMatch.group(1))
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    ggMatch = GG_PATTERN.match(message.lower())
    if ggMatch:
        statusCode, imgSrc = get_google_image(keyword=ggMatch.group(1))
        if statusCode == 200:
            LINE_BOT_API.reply_message(
                event.reply_token,
                ImageSendMessage(original_content_url=imgSrc, preview_image_url=imgSrc),
            )

    if message.lower() == "ai預測":
        response = get_long_cat_prediction()
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    aiMatch = AI_PATTERN.match(message.lower())
    if aiMatch:
        response = get_long_cat_inference(content=aiMatch.group(1))
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message == "牢大":
        content = get_textfile("TextFiles/Mamba.txt")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=content))

    if message == "規則":
        pass

    if message.lower() == "help":
        pass

    if message.lower() == "nba":
        response = get_nba_scoreboard()
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    injuryMatch = INJURY_PATTERN.match(message)
    if injuryMatch:
        teamName = injuryMatch.group(1) if injuryMatch.group(1) else ""
        response = get_team_injury(teamName=teamName)
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))


def random_message(event: MessageEvent):
    message = event.message.text

    if message == "抽單字":
        content = get_textfile_random("TextFiles/TOEFL.txt")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=content))

    if message == "你媽":
        content = get_textfile_random("TextFiles/YourMom.txt")
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=content))

    if message == "抽":
        imgSrc = get_imgur_url(albumHash="ZDcNFCL")
        LINE_BOT_API.reply_message(
            event.reply_token,
            ImageSendMessage(original_content_url=imgSrc, preview_image_url=imgSrc),
        )

    if message == "兄弟":
        imgSrc = get_imgur_url(albumHash="tb0BGKk")
        LINE_BOT_API.reply_message(
            event.reply_token,
            ImageSendMessage(original_content_url=imgSrc, preview_image_url=imgSrc),
        )

    if "goat" in message or "Goat" in message:
        imgSrc = get_random_image(imgKey="goat")
        LINE_BOT_API.reply_message(
            event.reply_token,
            ImageSendMessage(original_content_url=imgSrc, preview_image_url=imgSrc),
        )
