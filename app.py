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
    messages = []
    user_id = MY_UID

    # """Get GS"""
    # header, rows, worksheet = init()

    # """Get yesterday winner team"""
    # header, rows = get_match_result(header, rows, "yesterday")

    # """Calculate points"""
    # header, rows = count_points(header, rows)
    # update_sheet(header, rows, worksheet)

    # """Send user results"""
    # user_ranks = get_user_points(rows)
    # message = "預測排行榜:\n"
    # for i, value in enumerate(user_ranks):
    #     message += f"{i+1}. {value[0]}: {value[1]}分\n"
    # text_message = TextSendMessage(text=message[:-1])

    # messages.append(text_message)

    # """Reset old matches"""
    # header, rows = reset_match(header, rows)

    # """Get new matches"""
    # time = None
    # UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    # TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    # time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

    # data = get(f"https://tw-nba.udn.com/nba/schedule_boxscore/{time}").text
    # soup = BeautifulSoup(data, "html.parser")
    # cards = soup.find_all("div", class_="card")

    # match_index = 0
    # columns = []

    # for card in cards:
    #     team_names = [
    #         team.find("span", class_="team_name").text.strip()
    #         for team in card.find_all("div", class_="team")
    #     ]
    #     team_scores = [
    #         team.find("span", class_="team_score").text.strip()
    #         for team in card.find_all("div", class_="team")
    #     ]

    #     if team_names[0] == "塞爾蒂克":
    #         team_names[0] = "塞爾提克"
    #     elif team_names[1] == "塞爾蒂克":
    #         team_names[1] = "塞爾提克"

    #     encoded_team1 = quote(team_names[0])
    #     encoded_team2 = quote(team_names[1])
    #     thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team1}_{encoded_team2}.png"
    #     if not check_url_exists(thumbnail_image_url):
    #         thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team2}_{encoded_team1}.png"
    #         team_names.reverse()
    #         team_scores.reverse()

    #     columns.append(
    #         CarouselColumn(
    #             thumbnail_image_url=thumbnail_image_url,
    #             title=f"{team_names[0]} {team_scores[0]} - {team_names[1]} {team_scores[1]}",
    #             text="預測贏球球隊",
    #             actions=[
    #                 PostbackAction(
    #                     label=team_names[0], data=f"{team_names[0]}贏{team_names[1]}"
    #                 ),
    #                 PostbackAction(
    #                     label=team_names[1], data=f"{team_names[1]}贏{team_names[0]}"
    #                 ),
    #             ],
    #         ),
    #     )

    #     """Insert new match"""
    #     header, rows = modify_column_name(
    #         header, rows, match_index, f"{team_names[0]}-{team_names[1]}"
    #     )

    #     match_index += 1

    # """Update GS"""
    # update_sheet(header, rows, worksheet)

    # for i in range(0, len(columns), 10):
    #     chunk = columns[i : i + 10]
    #     carousel_template = CarouselTemplate(columns=chunk)
    #     template_message = TemplateSendMessage(
    #         alt_text="每日NBA預測", template=carousel_template
    #     )
    #     messages.append(template_message)

    # line_bot_api.push_message(user_id, messages)

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

        """Get yesterday winner team"""
        header, rows = get_match_result(header, rows, "yesterday")

        """Calculate points"""
        header, rows = count_points(header, rows)
        update_sheet(header, rows, worksheet)

        """Send user results"""
        user_ranks = get_user_points(rows)
        message = "預測排行榜:\n"
        for i, value in enumerate(user_ranks):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        text_message = TextSendMessage(text=message[:-1])

        messages.append(text_message)

        """Reset old matches"""
        header, rows = reset_match(header, rows)

        """OLD WAY!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"""
        # """Get new matches"""
        # time = None
        # UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        # TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
        # time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

        # data = get(f"https://tw-nba.udn.com/nba/schedule_boxscore/{time}").text
        # soup = BeautifulSoup(data, "html.parser")
        # cards = soup.find_all("div", class_="card")

        # match_index = 0
        # columns = []

        # for card in cards:
        #     team_names = [
        #         team.find("span", class_="team_name").text.strip()
        #         for team in card.find_all("div", class_="team")
        #     ]
        #     team_scores = [
        #         team.find("span", class_="team_score").text.strip()
        #         for team in card.find_all("div", class_="team")
        #     ]

        #     match_time = card.find("span", class_="during").text.strip()

        #     team_pos = ["客", "主"]

        #     if team_names[0] == "塞爾蒂克":
        #         team_names[0] = "塞爾提克"
        #     elif team_names[1] == "塞爾蒂克":
        #         team_names[1] = "塞爾提克"

        #     encoded_team1 = quote(team_names[0])
        #     encoded_team2 = quote(team_names[1])
        #     thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team1}_{encoded_team2}.png"
        #     if not check_url_exists(thumbnail_image_url):
        #         thumbnail_image_url = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encoded_team2}_{encoded_team1}.png"
        #         team_names.reverse()
        #         team_scores.reverse()
        #         team_pos.reverse()

        #     columns.append(
        #         CarouselColumn(
        #             thumbnail_image_url=thumbnail_image_url,
        #             title=f"{team_names[0]}({team_pos[0]}) {team_scores[0]} - {team_names[1]}({team_pos[1]}) {team_scores[1]}",
        #             text=f"{match_time}",
        #             actions=[
        #                 PostbackAction(
        #                     label=team_names[0], data=f"{team_names[0]}贏{team_names[1]}"
        #                 ),
        #                 PostbackAction(
        #                     label=team_names[1], data=f"{team_names[1]}贏{team_names[0]}"
        #                 ),
        #             ],
        #         ),
        #     )

        #     """Insert new match"""
        #     header, rows = modify_column_name(
        #         header, rows, match_index, f"{team_names[0]}-{team_names[1]}"
        #     )

        #     match_index += 1

        """NEW WAY!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"""
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

        return "Cron job executed successfully!"

    if msg == "結算":
        """Get GS"""
        header, rows, worksheet = init()

        """Get yesterday winner team"""
        header, rows = get_match_result(header, rows, "today")

        """Calculate points"""
        header, rows = count_points(header, rows)
        header, rows = reset_match(header, rows)
        update_sheet(header, rows, worksheet)

        """Send user results"""
        user_ranks = get_user_points(rows)
        message = "預測排行榜:\n"
        for i, value in enumerate(user_ranks):
            message += f"{i+1}. {value[0]}: {value[1]}分\n"
        text_message = TextSendMessage(text=message[:-1])
        line_bot_api.reply_message(event.reply_token, text_message)


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
