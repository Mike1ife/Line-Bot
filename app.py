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
    CarouselColumn,
    PostbackAction,
    PostbackEvent,
    FlexSendMessage,
)

from os import getenv
from re import compile
from urllib.parse import quote
from random import choice, randint
from requests import get

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

from tools._image import check_url_exists
from tools._user_table import *
from tools._table import *

line_bot_api = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
working_status = getenv("DEFALUT_TALKING", default="true").lower() == "true"

app = Flask(__name__)
CLIENT_ID = "427bae956e65de4"
ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"
MY_UID = "Uba0a4dd4bcfcb11fb91a7f0ba9992843"
GROUP_ID = "Cbb4733349bd2459a4fbe10a1068025ed"


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/api/cron", methods=["GET", "POST"])
def cron_job():
    messages = []
    user_id = MY_UID
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

    if msg == "uid":
        text = event.source.group_id
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg[:2].lower() == "yt":
        search = msg[3:]
        data = get(f"https://www.youtube.com/results?search_query={search}").text
        title_pattern = compile(r'"videoRenderer".*?"label":"(.*?)"')
        video_id_pattern = compile(r'"videoRenderer":{"videoId":"(.*?)"')

        # Find all matches for title and video ID in the text
        titles = title_pattern.findall(data)
        video_ids = video_id_pattern.findall(data)

        for title, video_id in zip(titles, video_ids):
            link = f"https://www.youtube.com/watch?v={video_id}"
            text = f"{title}\n{link}"
            text_message = TextSendMessage(text=text)
            line_bot_api.reply_message(event.reply_token, text_message)
            break

    if msg[:2].lower() == "gg":
        search = msg[3:]
        data = get(f"https://www.google.com/search?q={search}&tbm=isch").text
        soup = BeautifulSoup(data, "html.parser")
        img_src = soup.find("img", class_="DS1iW")["src"]

        response = get(img_src)
        if response.status_code == 200:
            image_message = ImageSendMessage(
                original_content_url=img_src,  # Replace with the public URL of your image
                preview_image_url=img_src,  # Replace with the public URL of your image
            )
            line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "河內塔":
        f = open("TextFiles/Hanoi3.txt")
        text = f.read()
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close()

    if msg.lower() == "bubble sort":
        f = open("TextFiles/BubbleSort.txt")
        text = f.read()
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close()

    if msg.lower() == "nba":
        time = None
        UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
        time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

        data = get(f"https://tw-nba.udn.com/nba/schedule_boxscore/{time}").text
        soup = BeautifulSoup(data, "html.parser")
        cards = soup.find_all("div", class_="card")

        score_text = ""
        for card in cards:
            team_names = [
                team.find("span", class_="team_name").text.strip()
                for team in card.find_all("div", class_="team")
            ]
            team_scores = [
                team.find("span", class_="team_score").text.strip()
                for team in card.find_all("div", class_="team")
            ]

            score_text += (
                f"{team_names[0]} {team_scores[0]} - {team_names[1]} {team_scores[1]}\n"
            )

        text_message = TextSendMessage(text=score_text[:-1])
        line_bot_api.reply_message(event.reply_token, text_message)

    if msg == "NBA每日預測":
        messages = []

        """Get GS"""
        header, rows, worksheet = init()

        """Send user results"""
        user_ranks = get_user_week_points(rows)
        message = "預測排行榜:\n"
        for i, value in enumerate(user_ranks):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        text_message = TextSendMessage(text=message[:-1])

        messages.append(text_message)

        """Reset old matches"""
        header, rows = reset_match(header, rows)

        try:
            """Get NBA Today"""
            columns = []
            matches = get_nba_today()
            for match_index, match in enumerate(matches):
                """Match infomation"""
                team_name = match["name"]
                team_standing = match["standing"]
                team_points = match["points"]
                team_pos = ["客", "主"]

                """Create template"""
                encoded_team1 = quote(team_name[0])
                encoded_team2 = quote(team_name[1])
                thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team1}_{encoded_team2}.png"
                if not check_url_exists(thumbnail_image_url):
                    thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team2}_{encoded_team1}.png"
                    team_name.reverse()
                    team_standing.reverse()
                    team_points.reverse()
                    team_pos.reverse()

                # title = 溜馬-老鷹 31/9
                # text = 溜馬 31分 / 老鷹 9分
                columns.append(
                    CarouselColumn(
                        thumbnail_image_url=thumbnail_image_url,
                        title=f"{team_name[0]}({team_pos[0]}) {team_standing[0]} - {team_name[1]}({team_pos[1]}) {team_standing[1]}",
                        text=f"{team_name[0]} {team_points[0]}分 / {team_name[1]} {team_points[1]}分",
                        actions=[
                            PostbackAction(
                                label=team_name[0],
                                data=f"{team_name[0]} {team_name[1]} {team_points[0]} {team_points[1]}",
                            ),
                            PostbackAction(
                                label=team_name[1],
                                data=f"{team_name[1]} {team_name[0]} {team_points[1]} {team_points[0]}",
                            ),
                        ],
                    ),
                )

                header, rows = modify_column_name(
                    header,
                    rows,
                    match_index,
                    f"{team_name[0]}-{team_name[1]} {team_points[0]}/{team_points[1]}",
                )

            """Update GS"""
            update_sheet(header, rows, worksheet)

            for i in range(0, len(columns), 10):
                chunk = columns[i : i + 10]
                carousel_template = CarouselTemplate(columns=chunk)
                template_message = TemplateSendMessage(
                    alt_text="每日NBA預測", template=carousel_template
                )
                messages.append(template_message)

            line_bot_api.reply_message(event.reply_token, messages)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))

    if msg == "結算":
        """Get GS"""
        header, rows, worksheet = init()

        """Get yesterday winner team"""
        try:
            header, rows = get_match_result(header, rows)

            """Calculate points"""
            header, rows = count_points(header, rows)
            header, rows = reset_match(header, rows)
            update_sheet(header, rows, worksheet)

            """Send user results"""
            user_ranks = get_user_week_points(rows)
            message = "預測排行榜:\n"
            for i, value in enumerate(user_ranks):
                message += f"{i+1}. {value[0]}: {value[1]}分\n"
            text_message = TextSendMessage(text=message[:-1])
            line_bot_api.reply_message(event.reply_token, text_message)
        except Exception as e:
            error_message = TextSendMessage(text=str(e))
            bot_message = TextSendMessage(
                text="?\n不是\n你們一個個天天都猴急什麼\n你們一急我又要上去查"
            )
            line_bot_api.reply_message(event.reply_token, [error_message, bot_message])

    if msg == "檢查":
        header, rows, worksheet = init()
        reply_text = ""
        user_id = event.source.user_id
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
            response = check_user_prediction(header, rows, display_name)
            reply_text = display_name + response
        except LineBotApiError as e:
            reply_text = "Unknown user."

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    if msg[:2] == "信仰":
        header, rows, worksheet = init()
        reply_text = ""
        user_id = event.source.user_id
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name

            correct = get_user_belief(header, rows, display_name)
            first_team = list(correct.keys())[0]
            correct_time = correct[first_team]

            if len(msg) == 2:
                reply_text = f"{display_name}是{first_team}的舔狗"
            elif msg[2] == " ":
                team_name = msg.split()[1]
                if team_name not in nba_team_translations.values():
                    reply_text = "Unknown team"
                else:
                    reply_text = f"{display_name}舔了{team_name}{correct[team_name]}口"
        except LineBotApiError as e:
            reply_text = "Unknown user."

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    if msg[:2] == "傻鳥":
        header, rows, worksheet = init()
        reply_text = ""
        user_id = event.source.user_id
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name

            wrong = get_user_hatred(header, rows, display_name)
            first_team = list(wrong.keys())[0]
            wrong_time = wrong[first_team]

            if len(msg) == 2:
                reply_text = f"{display_name}的傻鳥是{first_team}"
            elif msg[2] == " ":
                team_name = msg.split()[1]
                if team_name not in nba_team_translations.values():
                    reply_text = "Unknown team"
                else:
                    reply_text = f"{display_name}被{team_name}肛了{wrong[team_name]}次"
        except LineBotApiError as e:
            reply_text = "Unknown user."

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    if msg == "NBA預測週最佳":
        """Get week best"""
        header, rows, worksheet = init()
        header, rows, week_best = get_week_best(header, rows)

        """Send user ranks"""
        user_month_point = get_user_month_points(rows)
        message = "本月排行榜:\n"
        for i, value in enumerate(user_month_point):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        week_point_message = TextSendMessage(text=message[:-1])

        """Reset current points"""
        header, rows = reset_user_points(header, rows, "Week Points")
        update_sheet(header, rows, worksheet)

        reply_text = "本週預測GOAT: "
        for user in week_best:
            reply_text += f"{user[0]}({user[1]}分) "
        week_best_message = TextSendMessage(text=reply_text[:-1])

        line_bot_api.reply_message(
            event.reply_token, [week_best_message, week_point_message]
        )

    if msg == "NBA預測月最佳":
        """Get week best"""
        header, rows, worksheet = init()
        header, rows, month_best = get_month_best(header, rows)

        """Send user ranks"""
        user_month_point = get_user_year_points(rows)
        message = "本季排行榜:\n"
        for i, value in enumerate(user_month_point):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        month_point_message = TextSendMessage(text=message[:-1])

        """Reset current points"""
        header, rows = reset_user_points(header, rows, "Month Points")
        update_sheet(header, rows, worksheet)

        reply_text = "本月預測GOAT: "
        for user in month_best:
            reply_text += f"{user[0]}({user[1]}分) "
        month_best_message = TextSendMessage(text=reply_text[:-1])

        line_bot_api.reply_message(
            event.reply_token, [month_best_message, month_point_message]
        )

    if msg == "規則":
        f = open("TextFiles/NBA_Rule.txt")
        text = f.read()
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close()

    if msg.lower() == "help":
        f = open("TextFiles/Help.txt")
        text = f.read()
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close()

    if msg == "週排行":
        """Get week best"""
        header, rows, worksheet = init()
        """Send user ranks"""
        user_month_point = get_user_week_points(rows)
        message = "本週排行榜:\n"
        for i, value in enumerate(user_month_point):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        week_point_message = TextSendMessage(text=message[:-1])
        line_bot_api.reply_message(event.reply_token, week_point_message)

    if msg == "月排行":
        """Get week best"""
        header, rows, worksheet = init()
        """Send user ranks"""
        user_month_point = get_user_month_points(rows)
        message = "本月排行榜:\n"
        for i, value in enumerate(user_month_point):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        month_point_message = TextSendMessage(text=message[:-1])
        line_bot_api.reply_message(event.reply_token, month_point_message)

    if msg == "季排行":
        """Get week best"""
        header, rows, worksheet = init()
        """Send user ranks"""
        user_year_point = get_user_year_points(rows)
        message = "本季排行榜:\n"
        for i, value in enumerate(user_year_point):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        year_point_message = TextSendMessage(text=message[:-1])
        line_bot_api.reply_message(event.reply_token, year_point_message)

    if msg == "跟盤":
        header, rows, worksheet = init()
        message = "使用方式:\n跟盤 id\n"
        for i, row in enumerate(rows):
            message += f"{i}.{row[0]}\n"
        text_message = TextSendMessage(text=message[:-1])
        line_bot_api.reply_message(event.reply_token, text_message)
    elif msg[:2] == "跟盤":
        try:
            name_index = int(msg.split()[1])
            header, rows, worksheet = init()
            response = get_user_prediction(header, rows, name_index)
            text_message = TextSendMessage(text=response)
            line_bot_api.reply_message(event.reply_token, text_message)
        except:
            text_message = TextSendMessage(text="錯誤使用方式")
            line_bot_api.reply_message(event.reply_token, text_message)

    if msg == "傷病":
        message = "使用方式:\傷病 {球隊}"
        text_message = TextSendMessage(text=message)
        line_bot_api.reply_message(event.reply_token, text_message)
    elif msg[:2] == "傷病":
        try:
            team_name = NBA_TEAM_COMPLETE_NAME[msg.split()[1]]
            team_data = {}

            data = get(
                "https://hooptheball.com/nba-injury-report",
                headers={"User-Agent": "Agent"},
            ).text
            soup = BeautifulSoup(data, "html.parser")
            team_names = soup.find_all("h3", class_=None)
            for team_name in team_names[1:]:
                team_players = []
                table = team_name.find_next_sibling("table")
                rows = table.find_all("tr", class_="TableBase-bodyTr")
                for row in rows:
                    player_name = row.find("td").text
                    reason = row.find_all("td")[-2].text.strip()
                    Return = row.find_all("td")[-1].text.strip()
                    team_players.append(f"{player_name} ({reason} / {Return})")
                team_data[team_name.text] = team_players

            message = f"{team_name}傷病名單:\n"
            for player in team_data[team_name]:
                message += f"{player}\n"
            print(message[:-1])
        except:
            text_message = TextSendMessage(text="錯誤使用方式")
            line_bot_api.reply_message(event.reply_token, text_message)

    if msg == "註冊":
        header, rows, worksheet = init()
        user_id = event.source.user_id
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
            header, rows = add_new_user(header, rows, display_name)
            update_sheet(header, rows, worksheet)
            text_message = TextSendMessage(text=f"{display_name} 已完成註冊")
            line_bot_api.reply_message(event.reply_token, text_message)
        except:
            text_message = TextSendMessage(text="Unknown user")
            line_bot_api.reply_message(event.reply_token, text_message)

    if msg.lower() == "lck":
        data = get(
            f"https://dotesports.com/league-of-legends/news/2024-lck-spring-split-scores-standings-and-schedule"
        ).text
        soup = BeautifulSoup(data, "html.parser")

        UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
        month = TWnow.month
        day = TWnow.day
        weekday = TWnow.weekday()

        if weekday == 0 or weekday == 1:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="No LCK today")
            )

        target_date = f"{week_day[weekday]}, {month_abbreviation[month-1]}. {day}"
        time = None
        if weekday == 5 or weekday == 6:
            time = ["14:00", "16:30"]
        else:
            time = ["16:00", "18:30"]

        days = soup.find_all("strong")
        for day in days:
            date = day.text.strip()
            if date == target_date:
                matches = day.find_next("ul").find_all("li")
                matches_for_target_date = [match.text.strip() for match in matches]

                message = f"Matches for {target_date}:\n"
                for i, match in enumerate(matches_for_target_date):
                    match = match.split(" ", 1)
                    message += f"- {time[i]} {match[1]}\n"

                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=message[:-1])
                )


@line_handler.add(PostbackEvent)
def handle_postback(event):
    """Get GS"""
    header, rows, worksheet = init()

    reply_text = ""
    user_id = event.source.user_id
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name

        """Get user prediction"""
        data = event.postback.data

        winner, loser, winner_point, loser_point = data.split()

        """Locate column"""
        column = f"{winner}-{loser} {winner_point}/{loser_point}"
        if not column_exist(header, column):
            column = f"{loser}-{winner} {loser_point}/{winner_point}"

        """Create user if needed"""
        if not check_user_exist(rows, display_name):
            header, rows = add_new_user(header, rows, display_name)

        """User have predicted"""
        if user_predicted(header, rows, display_name, column):
            reply_text = f"{display_name}已經預測{winner}/{loser}了!"
        else:
            """First time predict"""
            reply_text = f"{display_name}預測{winner}贏{loser}!"
            # Modify GS
            header, rows = modify_value(header, rows, display_name, column, winner)

        update_sheet(header, rows, worksheet)
    except LineBotApiError as e:
        reply_text = "Unknown user."

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


def random_message(event):
    msg = event.message.text
    if msg == "抽":
        album_id = "ZDcNFCL"
        endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "抽單字":
        f = open("TextFiles/TOEFL.txt")
        vocabulary = f.readlines()
        word = randint(0, len(vocabulary) - 1)
        text = vocabulary[word][:-1]
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close()

    if msg == "你媽":
        f = open("TextFiles/YourMom.txt")
        sentences = f.readlines()
        index = randint(0, len(sentences) - 1)
        text = sentences[index][:-1]
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close()

    if msg == "抽牌":
        album_id = "698HGtx"
        endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "大小":
        album_id = "1K6H3WS"
        endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "兄弟":
        album_id = "tb0BGKk"
        endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)


if __name__ == "__main__":
    app.run()
