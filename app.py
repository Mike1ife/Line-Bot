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
)

from os import getenv
from re import compile
from urllib.parse import quote
from random import choice, randint
from requests import get

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

from tools._image import check_url_exists
from tools._table import nba_team_translations
from tools._user_table import *

line_bot_api = LineBotApi(getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(getenv("LINE_CHANNEL_SECRET"))
working_status = getenv("DEFALUT_TALKING", default="true").lower() == "true"

app = Flask(__name__)
CLIENT_ID = "427bae956e65de4"
ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"
MY_UID = "Uba0a4dd4bcfcb11fb91a7f0ba9992843"
GROUP_ID = "Cbb4733349bd2459a4fbe10a1068025ed"
get


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/api/cron", methods=["GET", "POST"])
def cron_job():
    user_id = GROUP_ID

    """Get GS"""
    header, rows, worksheet = init()

    """Calculate points"""
    header, rows = count_points(header, rows)
    update_sheet(header, rows)

    """Reset old matches"""
    header, rows = reset_match(header, rows)

    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

    data = get(f"https://www.foxsports.com/nba/scores?date={time}").text
    soup = BeautifulSoup(data, "html.parser")
    team_rows = soup.find_all(class_="score-team-row")

    team1 = {"name": "x", "standing": "x"}
    team2 = {"name": "x", "standing": "x"}

    i = 1
    match_index = 0
    score_text = "NBA Today:\n"
    columns = []

    for team_row in team_rows:
        team_name_elements = team_row.find_all(class_="score-team-name team")
        team = team_name_elements[0].get_text() if team_name_elements else None
        team = team.split()
        team_name = nba_team_translations[team[0]]
        if team[0] == "TRAIL":
            team_standing = team[2]
        else:
            team_standing = team[1]

        if i == 1:
            team1["name"] = team_name
            team1["standing"] = team_standing
            i += 1
        else:
            team2["name"] = team_name
            team2["standing"] = team_standing

            encoded_team1 = quote(team1["name"])
            encoded_team2 = quote(team2["name"])
            thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team1}_{encoded_team2}.png"
            if not check_url_exists(thumbnail_image_url):
                thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team2}_{encoded_team1}.png"
                team1, team2 = team2, team1

            columns.append(
                CarouselColumn(
                    thumbnail_image_url=thumbnail_image_url,
                    title=f"{team1['name']} {team1['standing']} - {team2['name']} {team2['standing']}",
                    text="預測贏球球隊",
                    actions=[
                        PostbackAction(
                            label=team1["name"], data=f"{team1['name']}贏{team2['name']}"
                        ),
                        PostbackAction(
                            label=team2["name"], data=f"{team2['name']}贏{team1['name']}"
                        ),
                    ],
                ),
            )

            score_text += f"{team1['name']} {team1['standing']} - {team2['name']} {team2['standing']}\n"

            """Insert new match"""
            header, rows = modify_column_name(
                header, rows, match_index, f"{team1['name']}-{team2['name']}"
            )

            match_index += 1
            i = 1

    """Update GS"""
    update_sheet(header, rows, worksheet)

    text_message = TextSendMessage(text=score_text[:-1])
    line_bot_api.push_message(user_id, text_message)

    for i in range(0, len(columns), 10):
        chunk = columns[i : i + 10]
        carousel_template = CarouselTemplate(columns=chunk)
        template_message = TemplateSendMessage(
            alt_text="每日NBA預測", template=carousel_template
        )
        line_bot_api.push_message(user_id, template_message)

    return "Cron job executed successfully!"


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
        split_point = data.find("贏")
        winner = data[:split_point]
        loser = data[split_point + 1 :]

        """Locate column"""
        column = f"{winner}-{loser}"
        if not column_exist(header, column):
            column = f"{loser}-{winner}"

        """Create user if needed"""
        if not check_user_exist(rows, display_name):
            header, rows = add_new_user(header, rows, display_name)

        """User have predicted"""
        if user_predicted(header, rows, display_name, column):
            reply_text = f"{display_name}已經預測{winner}贏{loser}了!"
        else:
            """First time predict"""
            reply_text = f"{display_name}預測{winner}贏{loser}!"
            # Modify GS
            header, rows = modify_value(header, rows, display_name, column, winner)

        update_sheet(header, rows, worksheet)
    except LineBotApiError as e:
        reply_text = "Unknown user."

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


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

    if msg == "河內塔":
        f = open("TextFiles/Hanoi3.txt")
        text = f.read()
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close

    if msg.lower() == "bubble sort":
        f = open("TextFiles/BubbleSort.txt")
        text = f.read()
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close

    if msg.lower() == "nba":
        time = None
        UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
        time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

        data = get(f"https://www.foxsports.com/nba/scores?date={time}").text
        soup = BeautifulSoup(data, "html.parser")
        team_rows = soup.find_all(class_="score-team-row")

        team1 = {"name": "x", "standing": "x", "score": "0"}
        team2 = {"name": "x", "standing": "x", "score": "0"}

        i = 1
        score_text = ""
        for team_row in team_rows:
            team_name_elements = team_row.find_all(class_="score-team-name team")
            team = team_name_elements[0].get_text() if team_name_elements else None
            team = team.split()
            team_name = nba_team_translations[team[0]]
            # team_standing = team[1]

            score_element = team_row.find(class_="score-team-score")
            team_score = score_element.get_text().strip() if score_element else "TBD"

            if i == 1:
                team1["name"] = team_name
                # team1["standing"] = team_standing
                team1["score"] = team_score
                i += 1
            else:
                team2["name"] = team_name
                # team2["standing"] = team_standing
                team2["score"] = team_score

                score_text += f"{team1['name']} {team1['score']} - {team2['name']} {team2['score']}\n"

                i = 1

        text_message = TextSendMessage(text=score_text[:-1])
        line_bot_api.reply_message(event.reply_token, text_message)


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
        f.close

    if msg == "你媽":
        f = open("TextFiles/YourMom.txt")
        sentences = f.readlines()
        index = randint(0, len(sentences) - 1)
        text = sentences[index][:-1]
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close

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


if __name__ == "__main__":
    app.run()
