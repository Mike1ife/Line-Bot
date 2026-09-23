import time
from linebot.models import (
    TextSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
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
BOXSCORE_PATTERN = re.compile(r"^隨機戰報(?: ([^\s]+))?$")
TW_STOCK_PATTERN = re.compile(r"^台股(?: (.+))?$")
US_STOCK_PATTERN = re.compile(r"^美股(?: (.+))?$")
REPORT_PATTERN = re.compile(r"^戰報(?: ([^\s]+))?$")
ACHIEVEMENT_PATTERN = re.compile(r"^成就(?: ([^\s]+))?$")


def _quick_reply(*labels):
    """Quick replies render in group chats (unlike rich menus), and a tap
    posts the message to the group as that member."""
    return QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label=label, text=label))
            for label in labels
        ]
    )

RANK_COMMANDS = ("週排行", "月排行", "季排行", "總排行")


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

    if message == "test":
        start = time.time()
        time.sleep(100)
        LINE_BOT_API.reply_message(
            event.reply_token, TextSendMessage(text=str(time.time() - start))
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

    if message == "NBA每日預測":
        if not user_is_admin(userUID):
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text="傻狗給老子閉嘴")
            )
        try:
            (
                matchList,
                response,
                matchColumns,
                gameOfTheDayPage,
                gameOfTheDayDate,
                gameOfTheDayTime,
            ) = get_nba_game_prediction(playoffsLayout=True)

            if not matchColumns:
                LINE_BOT_API.reply_message(
                    event.reply_token, TextSendMessage(text=response)
                )
            else:
                statColumns, playerStatBetList = get_player_stat_prediction(
                    gamePage=gameOfTheDayPage,
                    gameDate=gameOfTheDayDate,
                    gameTime=gameOfTheDayTime,
                )
                carouselColumns = matchColumns + statColumns
                respondMessages = [TextSendMessage(text=response)]
                for i in range(0, len(carouselColumns), 10):
                    carouselTemplate = CarouselTemplate(
                        columns=carouselColumns[i : i + 10]
                    )
                    templateMessage = TemplateSendMessage(
                        alt_text="NBA每日預測", template=carouselTemplate
                    )
                    respondMessages.append(templateMessage)

                insert_nba_totay(
                    matchList=matchList, playerStatBetList=playerStatBetList
                )
                LINE_BOT_API.reply_message(event.reply_token, respondMessages)
        except Exception as err:
            LINE_BOT_API.reply_message(
                event.reply_token, TextSendMessage(text=str(err))
            )

    if message == "檢查":
        response = get_user_prediction_check(userName=userName)
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("週排行", "戰報")),
        )

    settleMatch = SETTLE_PATTERN.match(message)
    if settleMatch:
        try:
            source = settleMatch.group(1) if settleMatch.group(1) else "hupu"
            if source not in ("hupu", "fox"):
                LINE_BOT_API.reply_message(
                    event.reply_token, TextSendMessage(text="Invalid Source")
                )
                return
            
            results_message, ranking_message = settle_daily_prediction(source=source)
            respondMessages = [
                TextSendMessage(text=results_message),
                TextSendMessage(text=ranking_message),
            ]
            # 戰報 is a bonus message; never let it break the settlement reply.
            try:
                report = get_battle_report()
                if report:
                    respondMessages.append(TextSendMessage(text=report))
            except Exception:
                pass
            respondMessages[-1].quick_reply = _quick_reply("戰報", "成就", "週排行")
            LINE_BOT_API.reply_message(event.reply_token, respondMessages)
            
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
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("月排行", "季排行", "總排行")),
        )

    if message == "月排行":
        response = get_user_type_point("month_points")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("週排行", "季排行", "總排行")),
        )

    if message == "季排行":
        response = get_user_type_point("season_points")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("週排行", "月排行", "總排行")),
        )

    if message == "總排行":
        response = get_user_type_point("all_time_points")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("週排行", "月排行", "季排行")),
        )

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
        content = get_textfile("TextFiles/NBA_Rule.txt")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=content, quick_reply=_quick_reply("help", "註冊")),
        )

    if message.lower() == "help":
        content = get_textfile("TextFiles/Help.txt")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=content, quick_reply=_quick_reply("規則", "週排行", "戰報")),
        )

    if message.lower() == "nba":
        response = get_nba_scoreboard()
        LINE_BOT_API.reply_message(event.reply_token, TextSendMessage(text=response))

    if message.lower() == "f1":
        response = get_f1_schedule()
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("nba", "help")),
        )

    twStockMatch = TW_STOCK_PATTERN.match(message)
    if twStockMatch:
        response = get_tw_stock(query=twStockMatch.group(1) or "")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("加權", "help")),
        )

    usStockMatch = US_STOCK_PATTERN.match(message)
    if usStockMatch:
        response = get_us_stock(query=usStockMatch.group(1) or "")
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("加權", "help")),
        )

    if message == "加權":
        response = get_taiex()
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("台股 2330", "美股 AAPL")),
        )

    achievementMatch = ACHIEVEMENT_PATTERN.match(message)
    if achievementMatch:
        target = achievementMatch.group(1)
        userId = int(target) if target and target.isdigit() else -1
        try:
            response = get_achievement_message(userName=userName, userId=userId)
        except Exception as err:
            response = f"成就查詢失敗\n{type(err).__name__}: {err}"
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("戰報", "週排行")),
        )

    reportMatch = REPORT_PATTERN.match(message)
    if reportMatch:
        gameDate = reportMatch.group(1) if reportMatch.group(1) else ""
        try:
            response = get_battle_report(gameDate=gameDate)
        except Exception as err:
            response = f"戰報產生失敗\n{type(err).__name__}: {err}"
        LINE_BOT_API.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=_quick_reply("成就", "週排行")),
        )

    boxscoreMatch = BOXSCORE_PATTERN.match(message)
    if boxscoreMatch:
        gameDate = boxscoreMatch.group(1) if boxscoreMatch.group(1) else ""
        response = get_random_boxscore(gameDate=gameDate)
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
