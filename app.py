from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

import os
import re
import random
import pathlib
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
working_status = os.getenv("DEFALUT_TALKING", default="true").lower() == "true"

app = Flask(__name__)


# domain root
@app.route("/")
def home():
    return "Hello, World!"


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


CLIENT_ID = "427bae956e65de4"
ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"


@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    random_message(event)
    text_message(event)


def text_message(event):
    msg = event.message.text
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

    if msg[:2].lower() == "gg":
        search_name = msg[3:]
        options = webdriver.ChromeOptions()
        options.add_argument(f"user-data-dir={pathlib.Path().resolve()}/tmp")
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        driver.get("https://www.google.com/")
        html = driver.page_source

        text = ""

        try:
            search = driver.find_element(By.NAME, "q")
            search.send_keys(search_name)
            search.send_keys(Keys.ENTER)

            items = driver.find_elements(By.CLASS_NAME, "LC20lb")
            addrs = driver.find_elements(By.CLASS_NAME, "yuRUbf")

            all = zip(items, addrs)

            for item in all:
                addr = item[1].find_element(By.TAG_NAME, "a").get_attribute("href")
                text += f"{item[0].text} - {addr}\n"

        except NoSuchElementException:
            text = "Search Fail"

        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, text_message)

        driver.quit()

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
        date = None
        UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))

        score_elements = []
        score_text = f""

        while True:
            time = f"{TWnow.year}{TWnow.month}{TWnow.day}"

            data = requests.get(
                f"https://secure.espn.com/core/nba/schedule/_/date/{time}?table=true"
            ).text

            soup = BeautifulSoup(data, "html.parser")
            score_elements = soup.find_all(
                "a", {"name": re.compile(r"&lpos=nba:schedule:score")}
            )

            if len(score_elements) == 0:
                TWnow = TWnow - timedelta(hours=24)
                continue
            else:
                for score_element in score_elements:
                    score = score_element.get_text(strip=True)
                    score_text += f"{score}\n"
                break

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
