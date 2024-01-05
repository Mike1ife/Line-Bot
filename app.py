from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    ImageSendMessage,
    TemplateSendMessage,
    ButtonsTemplate,
    CarouselTemplate,
    CarouselColumn,
    PostbackAction,
    PostbackEvent,
)

import os
import re
import urllib
import random
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

from tools._image import build_image
from tools._table import nba_team_translations

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
working_status = os.getenv("DEFALUT_TALKING", default="true").lower() == "true"

app = Flask(__name__)
CLIENT_ID = "427bae956e65de4"
ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"
MY_UID = "Uba0a4dd4bcfcb11fb91a7f0ba9992843"
GROUP_ID = "Ccd472bcff08c0d73df483615fa795a75"


# domain root
@app.route("/")
def home():
    return "Hello, World!"


@app.route("/api/cron", methods=["GET", "POST"])
def cron_job():
    user_id = GROUP_ID

    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

    data = requests.get(f"https://www.foxsports.com/nba/scores?date={time}").text
    soup = BeautifulSoup(data, "html.parser")
    team_rows = soup.find_all(class_="score-team-row")

    team1 = {"name": "x", "standing": "x"}
    team2 = {"name": "x", "standing": "x"}

    i = 1
    score_text = "NBA Today:\n"

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

            score_text += f"{team1['name']} {team1['standing']} - {team2['name']} {team2['standing']}\n"

            i = 1

    text_message = TextSendMessage(text=score_text[:-1])
    line_bot_api.push_message(user_id, text_message)

    return "Cron job executed successfully!"


@app.route("/api/open_vote_form", methods=["GET"])
def open_vote_form():
    team1 = urllib.parse.quote("公鹿")
    team2 = urllib.parse.quote("馬刺")
    carousel_template = CarouselTemplate(
        columns=[
            CarouselColumn(
                thumbnail_image_url=f"https://github.com/Mike1ife/Line-Bot/blob/main/images/merge/%E5%85%AC%E9%B9%BF_%E9%A6%AC%E5%88%BA.png?raw=true",
                title="公鹿 25-10 - 馬刺 5-29",
                text="預測贏球球隊",
                actions=[
                    PostbackAction(label="公鹿", data="公鹿"),
                    PostbackAction(label="馬刺", data="馬刺"),
                ],
            ),
        ]
    )

    template_message = TemplateSendMessage(
        alt_text="Vote for NBA Teams", template=carousel_template
    )

    line_bot_api.push_message(MY_UID, template_message)
    return "Vote form opened successfully!"


@line_handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    selected_team = event.postback.data
    reply_text = f"你預測{selected_team}!"
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
        data = requests.get(
            f"https://www.youtube.com/results?search_query={search}"
        ).text
        title_pattern = re.compile(r'"videoRenderer".*?"label":"(.*?)"')
        video_id_pattern = re.compile(r'"videoRenderer":{"videoId":"(.*?)"')

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

        data = requests.get(f"https://www.foxsports.com/nba/scores?date={time}").text
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
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = random.choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "抽單字":
        f = open("TextFiles/TOEFL.txt")
        vocabulary = f.readlines()
        word = random.randint(0, len(vocabulary) - 1)
        text = vocabulary[word][:-1]
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close

    if msg == "你媽":
        f = open("TextFiles/YourMom.txt")
        sentences = f.readlines()
        index = random.randint(0, len(sentences) - 1)
        text = sentences[index][:-1]
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)
        f.close

    if msg == "抽牌":
        album_id = "698HGtx"
        endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = random.choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)

    if msg == "大小":
        album_id = "1K6H3WS"
        endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            images = data["data"]
            if images:
                random_image = random.choice(images)
                image_url = random_image["link"]
                image_message = ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                )
                line_bot_api.reply_message(event.reply_token, image_message)


if __name__ == "__main__":
    app.run()
