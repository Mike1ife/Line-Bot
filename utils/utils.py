import re
import random
import requests
from urllib.parse import quote
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from linebot.models import CarouselColumn, PostbackAction

from utils._user_table import *
from utils._team_table import (
    NBA_ABBR_ENG_TO_ABBR_CN,
    NBA_TEAM_NAME_ENG_TO_ABBR_CN,
    NBA_ABBR_CN_TO_FULL_CN,
)

ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"
TYPENAME = {"week": "本週", "month": "本月", "season": "本季", "all-time": "歷史"}
TYPEFUNC = {
    "week": get_week_best,
    "month": get_month_best,
    "season": get_season_best,
}
TYPECOL = {"week": "Week Points", "month": "Month Points", "season": "Year Points"}
NEXTTYPE = {"week": "month", "month": "season", "season": "all-time"}

BET_NAME = {
    "PLAYER POINTS": "得分",
    "PLAYER REBOUNDS": "籃板",
    "PLAYER STEALS": "抄截",
}


def check_url_exists(url):
    try:
        response = requests.head(url, allow_redirects=True)
        # You can also use requests.get(url) if you want to follow redirects and check the content
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def get_youtube(msg):
    search = msg[3:]
    data = requests.get(f"https://www.youtube.com/results?search_query={search}").text
    title_pattern = re.compile(r'"videoRenderer".*?"label":"(.*?)"')
    video_id_pattern = re.compile(r'"videoRenderer":{"videoId":"(.*?)"')

    # Find all matches for title and video ID in the text
    titles = title_pattern.findall(data)
    video_ids = video_id_pattern.findall(data)

    for title, video_id in zip(titles, video_ids):
        link = f"https://www.youtube.com/watch?v={video_id}"
        text = f"{title}\n{link}"
        return text


def get_google_image(msg):
    search = msg[3:]
    data = requests.get(f"https://www.google.com/search?q={search}&tbm=isch").text
    soup = BeautifulSoup(data, "html.parser")
    img_src = soup.find("img", class_="DS1iW")["src"]

    response = requests.get(img_src)
    return response.status_code, img_src


def get_textfile(filepath):
    f = open(filepath)
    text = f.read()
    f.close()
    return text


def get_textfile_random(filepath):
    f = open(filepath)
    vocabulary = f.readlines()
    word = random.randint(0, len(vocabulary) - 1)
    f.close()
    return vocabulary[word][:-1]


def get_nba_scoreboard():
    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))

    # if over 19:00, grab tomorrow schedule
    TW7pm = TWnow.replace(hour=19, minute=0, second=0, microsecond=0)
    if TWnow > TW7pm:
        TWnow += timedelta(days=1)

    time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"

    data = requests.get(f"https://tw-nba.udn.com/nba/schedule_boxscore/{time}").text
    soup = BeautifulSoup(data, "html.parser")
    cards = soup.find_all("div", class_="card")

    # get team scoreboard
    score_text = ""
    for card in cards:
        state = card.find("span", class_="during").text.strip()
        team_names = [
            team.find("span", class_="team_name").text.strip()
            for team in card.find_all("div", class_="team")
        ]
        team_scores = [
            team.find("span", class_="team_score").text.strip()
            for team in card.find_all("div", class_="team")
        ]

        score_text += f"{team_names[0]} {team_scores[0]} - {team_names[1]} {team_scores[1]} ({state})\n"

    # get player stat
    header, rows, worksheet = init()
    for i in range(PREDICT_INDEX, len(header)):
        # Anthony Edwards 得分26.5 4/6
        if header[i].count(" ") >= 2:
            header_items = header[i].split()
            player = " ".join(header_items[:-2])
            stat_type, target = header_items[-2][:2], float(header_items[-2][2:])

            with open("utils/player_link.json", "r", encoding="utf-8") as f:
                player_url_table = json.load(f)
            url = player_url_table[player]

            data = requests.get(url).text
            soup = BeautifulSoup(data, "html.parser")
            container = soup.find("tbody", class_="row-data lh-1pt43 fs-14")
            game = container.find("tr")
            against = game.find("a", class_="table-entity-name ff-ffc").text.strip()

            DATA_INDEX = {"得分": 3, "籃板": 5, "抄截": 7}
            value = int(
                game.find("td", {"data-index": DATA_INDEX[stat_type]}).text.strip()
            )

            if value >= target:
                res = "大盤"
            else:
                res = "小盤"

            score_text += f"{player} {stat_type} {value} ({res})\n"

    return score_text[:-1]


def get_nba_match_prediction(playoffs=False):
    """Get GS"""
    header, rows, worksheet = init()
    text = get_user_type_point("week")

    """Reset old matches"""
    header, rows = reset_match(header, rows)

    """Get NBA Today"""
    columns = []
    if playoffs:
        matches, match_page, match_time = get_nba_playoffs()
    else:
        matches = get_nba_today()

    if len(matches) == 0:
        return "明天沒有比賽", None, None, None
    else:
        UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
        Tomorrow = TWnow + timedelta(days=1)
        for match_index, match in enumerate(matches):
            """Match infomation"""
            gametime = match["gametime"]
            team_name = match["name"]
            team_standing = match["standing"]
            try:
                team_points = match["points"]
            except:
                team_points = [30, 30]
            team_pos = ["客", "主"]

            game_id = ""
            if playoffs:
                game_id = "Game " + match["game_id"] + "\n"

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

            # title = 溜馬(主) 1-11 - 老鷹(客) 5-6
            # text = 7:30\n溜馬 31分 / 老鷹 9分
            columns.append(
                CarouselColumn(
                    thumbnail_image_url=thumbnail_image_url,
                    title=f"{team_name[0]}({team_pos[0]}) {team_standing[0]} - {team_name[1]}({team_pos[1]}) {team_standing[1]}",
                    text=f"{game_id}{gametime}\n{team_name[0]} {team_points[0]}分 / {team_name[1]} {team_points[1]}分",
                    actions=[
                        PostbackAction(
                            label=team_name[0],
                            data=f"NBA球隊預測;{team_name[0]};{team_name[1]};{team_points[0]};{team_points[1]};{Tomorrow.year}-{Tomorrow.month}-{Tomorrow.day}-{gametime}",
                        ),
                        PostbackAction(
                            label=team_name[1],
                            data=f"NBA球隊預測;{team_name[1]};{team_name[0]};{team_points[1]};{team_points[0]};{Tomorrow.year}-{Tomorrow.month}-{Tomorrow.day}-{gametime}",
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
        return text, columns, match_page, match_time


def _compare_timestring(timestr1, timestr2):
    time_format = "%Y-%m-%d-%H:%M"

    return datetime.strptime(timestr1, time_format) > datetime.strptime(
        timestr2, time_format
    )


def get_nba_match_prediction_postback(
    username, winner, loser, winner_point, loser_point, gametime
):
    """Get GS"""
    header, rows, worksheet = init()

    """Check if the game is already started"""
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    timenow = f"{TWnow.year}-{TWnow.month}-{TWnow.day}-{TWnow.hour}:{TWnow.minute}"

    if _compare_timestring(timenow, gametime):
        return f"{winner}-{loser} 的比賽已經開始了"

    text = ""
    """Locate column"""
    column = f"{winner}-{loser} {winner_point}/{loser_point}"
    if not column_exist(header, column):
        column = f"{loser}-{winner} {loser_point}/{winner_point}"

    """Create user if needed"""
    if not check_user_exist(rows, username):
        header, rows = add_new_user(header, rows, username)

    """User have predicted"""
    if user_predicted(header, rows, username, column):
        text = f"{username}已經預測{winner}/{loser}了！"
    else:
        """First time predict"""
        text = f"{username}預測{winner}贏{loser}！"
        # Modify GS
        header, rows = modify_value(header, rows, username, column, winner)

    update_sheet(header, rows, worksheet)
    return text


def _get_player_bet_info(player, title):
    img_src = player.find("img").get("src")
    name = player.find("img").get("alt")
    match = player.find("div", class_="ffn-gr-11").text

    with open("utils/player_link.json", "r", encoding="utf-8") as f:
        player_url_table = json.load(f)

    player_page = requests.get(player_url_table[name].replace("game-log", "stats")).text
    player_soup = BeautifulSoup(player_page, "html.parser")
    title_to_class = {"PLAYER POINTS": 0, "PLAYER REBOUNDS": 1, "PLAYER STEALS": 4}
    player_stats = player_soup.find_all("a", class_="stats-overview")
    avg = player_stats[title_to_class[title]].find("div", class_="fs-54 fs-sm-40").text
    target = player.find("div", class_="fs-30").text
    _odds_msg = (
        player.find("span", class_="pd-r-2").text
        + " "
        + player.find("span", class_="cl-og").text
    )
    _odds_items = _odds_msg.split()
    odds = (int(_odds_items[4][1:]) - int(_odds_items[1][1:])) // 2
    return (
        img_src,
        name,
        _get_match_translation(match),
        avg.split()[0],
        target,
        int(1.5 * odds),
    )


def _get_match_translation(match):
    away, _, home, _, _, _ = match.split()
    return f"{NBA_ABBR_ENG_TO_ABBR_CN[away]} @ {NBA_ABBR_ENG_TO_ABBR_CN[home]}"


def get_player_stat_prediction(match_count, match_page, match_time):
    header, rows, worksheet = init()

    data = requests.get(match_page).text
    soup = BeautifulSoup(data, "html.parser")
    bets = soup.find_all("div", class_="odds-component-prop-bet")

    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    Tomorrow = TWnow + timedelta(days=1)
    columns = []
    column_id = 0
    for bet in bets:
        title = bet.find("h2", class_="pb-name fs-30").text.strip()
        players = bet.find_all("div", class_="prop-bet-data pointer prop-future")
        for player in players:
            img_src, name, match, avg, target, odds = _get_player_bet_info(
                player, title
            )
            # title = Anthony Edwards
            # text = 場均得分 28.0\n7:00 國王(客) - 灰狼(主)\n大盤 (得分超過 26.5) 4分 / 小盤 (得分低於 26.5) 6分
            # button1 = 大盤
            # button2 = 小盤
            columns.append(
                CarouselColumn(
                    thumbnail_image_url=img_src,
                    title=name,
                    text=f"場均{BET_NAME[title]} {avg}\n{match_time} {match}\n大盤 ({BET_NAME[title]}超過{target}) {odds}分\n小盤 ({BET_NAME[title]}低於{target}) {15-odds}分",
                    actions=[
                        PostbackAction(
                            label="大盤",
                            data=f"NBA球員預測;{name};{BET_NAME[title]}{target};{odds};{15-odds};大盤;{Tomorrow.year}-{Tomorrow.month}-{Tomorrow.day}-{match_time}",
                        ),
                        PostbackAction(
                            label="小盤",
                            data=f"NBA球員預測;{name};{BET_NAME[title]}{target};{odds};{15-odds};小盤;{Tomorrow.year}-{Tomorrow.month}-{Tomorrow.day}-{match_time}",
                        ),
                    ],
                ),
            )

            header, rows = modify_column_name(
                header,
                rows,
                column_id + match_count,
                f"{name} {BET_NAME[title]}{target} {odds}/{15-odds}",
            )
            column_id += 1

    update_sheet(header, rows, worksheet)
    return columns


def get_player_stat_prediction_postback(
    username, player, target, over_point, under_point, predict, match_time
):
    """Check if the game is already started"""
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    timenow = f"{TWnow.year}-{TWnow.month}-{TWnow.day}-{TWnow.hour}:{TWnow.minute}"
    if _compare_timestring(timenow, match_time):
        return f"{player} 的比賽已經開始了"

    """Get GS"""
    header, rows, worksheet = init()

    text = ""
    """Locate column"""
    # Anthony Edwards 得分26.5 4/6
    column = f"{player} {target} {over_point}/{under_point}"

    """Create user if needed"""
    if not check_user_exist(rows, username):
        header, rows = add_new_user(header, rows, username)

    """User have predicted"""
    if user_predicted(header, rows, username, column):
        text = f"{username}已經預測{player}的盤了！"
    else:
        """First time predict"""
        if predict == "大盤":
            text = f"{username}預測{player}{target[:2]}超過{target[2:]}！"
            header, rows = modify_value(
                header, rows, username, column, f"{player} {predict}"
            )
        elif predict == "小盤":
            text = f"{username}預測{player}{target[:2]}低於{target[2:]}！"
            header, rows = modify_value(
                header, rows, username, column, f"{player} {predict}"
            )

    update_sheet(header, rows, worksheet)
    return text


def get_daily_predict_result():
    """Get GS"""
    header, rows, worksheet = init()
    """Get yesterday winner team"""
    header, rows = get_match_result(header, rows)
    header, rows = get_player_result(header, rows)

    """Calculate points"""
    header, rows, add_points = count_points(header, rows)
    header, rows = reset_match(header, rows)
    update_sheet(header, rows, worksheet)

    """Send user results"""
    user_ranks = get_user_points(rows, "week")
    text = "預測排行榜:\n"
    for i, (username, point) in enumerate(user_ranks):
        text += f"{i+1}. {username}: {point}分"
        if add_points[username] > 0:
            text += f" (+{add_points[username]})\n"
        else:
            text += "\n"
    return text[:-1]


def get_user_predict_check(username):
    header, rows, worksheet = init()
    return username + check_user_prediction(header, rows, username)


def get_user_most_belief(msg, username):
    header, rows, worksheet = init()
    correct = get_user_belief(header, rows, username)
    first_team = list(correct.keys())[0]

    if len(msg) == 2:
        text = f"{username}是{first_team}的舔狗"
    elif msg[2] == " ":
        team_name = msg.split()[1]
        if team_name not in NBA_ABBR_ENG_TO_ABBR_CN.values():
            text = "Unknown team"
        else:
            text = f"{username}舔了{team_name}{correct[team_name]}口"

    return text


def get_user_most_hatred(msg, username):
    header, rows, worksheet = init()
    wrong = get_user_hatred(header, rows, username)
    first_team = list(wrong.keys())[0]

    if len(msg) == 2:
        text = f"{username}的傻鳥是{first_team}"
    elif msg[2] == " ":
        team_name = msg.split()[1]
        if team_name not in NBA_ABBR_ENG_TO_ABBR_CN.values():
            text = "Unknown team"
        else:
            text = f"{username}被{team_name}肛了{wrong[team_name]}次"

    return text


def get_most_belief_hatred_team():
    header, rows, worksheet = init()
    rows, belief, hatred = reset_belief_hatred(header, rows)
    update_sheet(header, rows, worksheet)
    return f"{belief}是信仰的GOAT\n{hatred}是傻鳥的GOAT"


def get_user_type_best(type: str):
    """Get best"""
    header, rows, worksheet = init()
    header, rows, best = TYPEFUNC[type](header, rows)

    if len(best) == 0:
        return None, f"{TYPENAME[type]}沒有分數"
    else:
        best_users = f"{TYPENAME[type]}預測GOAT: "
        for user in best:
            best_users += f"{user[0]}({user[1]}分) "

        """Send next_type ranks"""
        type_point = get_user_points(rows, NEXTTYPE[type])
        type_rank = f"{TYPENAME[NEXTTYPE[type]]}排行榜:\n"
        for i, value in enumerate(type_point):
            type_rank += f"{i+1}. {value[0]}: {value[1]}分\n"

        """Reset current points"""
        header, rows = reset_user_points(header, rows, TYPECOL[type])
        update_sheet(header, rows, worksheet)

        return best_users, type_rank[:-1]


def get_user_type_point(type: str):
    """Get points"""
    header, rows, worksheet = init()
    """Send user ranks"""
    user_month_point = get_user_points(rows, type)
    text = f"{TYPENAME[type]}排行榜:\n"
    for i, value in enumerate(user_month_point):
        text += f"{i+1}. {value[0]}: {value[1]}分\n"
    return text[:-1]


def get_prediction_comparison(msg):
    if msg.strip() == "比較":
        header, rows, worksheet = init()
        text = "使用方式:\n比較 id id\n"
        for i, row in enumerate(rows):
            text += f"{i}.{row[0]}\n"
        return text.rstrip()

    if msg.startswith("比較 "):
        try:
            _, index_a, index_b = msg.split()
            header, rows, worksheet = init()
            return compare_user_prediction(header, rows, int(index_a), int(index_b))
        except:
            return "錯誤使用方式"


def get_others_prediction(msg):
    if msg.strip() == "跟盤":
        header, rows, worksheet = init()
        text = "使用方式:\n跟盤 id\n"
        for i, row in enumerate(rows):
            text += f"{i}.{row[0]}\n"
        return text.rstrip()

    if msg.startswith("跟盤 "):
        try:
            name_index = int(msg.split()[1])
            header, rows, worksheet = init()
            return get_user_prediction(header, rows, name_index)
        except:
            return "錯誤使用方式"


def get_team_injury(msg):
    if msg == "傷病":
        return "使用方式: 傷病 {球隊}"
    elif msg[:2] == "傷病":
        try:
            team_name = NBA_ABBR_CN_TO_FULL_CN[msg.split()[1]]
            team_data = {}
            """
            data = requests.get(
                "https://hooptheball.com/nba-injury-report",
                headers={"User-Agent": "Agent"},
            ).text
            """
            data = requests.get(
                "https://hooptheball.com/nba-injury-report",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)\
                        AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/115.0.0.0 Safari/537.36"
                },  # 避免被阻擋
            ).text

            soup = BeautifulSoup(data, "html.parser")
            teams = soup.find_all("h3", class_=None)

            for team in teams[1:]:
                team_players = []
                table = team.find_next_sibling("table")
                rows = table.find_all("tr", class_="TableBase-bodyTr")
                for row in rows:
                    player_name = row.find("td").text.strip()
                    # player_name = row.find("td").text
                    reason = row.find_all("td")[-2].text.strip()
                    Return = row.find_all("td")[-1].text.strip()
                    # 調整此處只使用兩行結構
                    team_players.append(f"{player_name} {reason}\n({Return})")
                team_data[team.text.strip()] = team_players

            text = f"{team_name}傷病名單:\n"
            try:
                for player in team_data[team_name]:
                    """
                    name, reason, time = player.strip().split("\n")
                    text += f"{name.strip()} {reason.strip()} {time.strip()}\n"
                    """
                    lines = player.strip().split("\n")
                    # lines[0]範例: "Luka Doncic 個人原因"
                    # lines[1]範例: "(預計缺陣至少到 12月 21)"
                    parts = lines[0].split(
                        " ", 1
                    )  # 只切一次, parts[0] = name, parts[1] = reason
                    name = parts[0]
                    reason = parts[1]
                    time = lines[1].strip("()")
                    text += f"{name} {reason} {time}\n"

                return text[:-1]
            except KeyError:
                return f"{team_name}沒有傷兵"
        except Exception as e:
            return "錯誤使用方式"


def get_user_registered(username):
    header, rows, worksheet = init()
    for row in rows:
        if row[0] == username:
            return f"{username} 不需要註冊"

    header, rows = add_new_user(header, rows, username)
    update_sheet(header, rows, worksheet)
    return f"{username} 已完成註冊"


def get_nba_guessing():
    BASE = "https://www.foxsports.com/"

    def get_teams():
        url = BASE + "nba/teams"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        teams = soup.find_all("a", class_="entity-list-row-container image-logo")
        return teams

    def get_players(teams):
        team = random.choice(teams)
        url = BASE + team.attrs["href"] + "-roster"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        players = soup.find_all("a", class_="table-entity-name ff-ffc")
        if len(players) == 0:
            return get_players(teams)
        else:
            return players, url

    def get_stats(players):
        player = random.choice(players)
        url = BASE + player.attrs["href"] + "-stats"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        name = soup.find("span", class_="lh-sm-25")
        stats = soup.find_all("a", class_="stats-overview")
        if len(stats) == 0:
            return get_stats(players)
        else:
            return name, stats, url

    teams = get_teams()
    players, team_url = get_players(teams)
    name, stats, player_url = get_stats(players)

    # print(team_url)
    # print(player_url)

    player_info = {"name": name.getText().title(), "stats": []}
    for stat in stats:
        stat_type = (
            stat.find("h3", class_="stat-name uc fs-18 fs-md-14 fs-sm-14")
            .getText()
            .strip()
        )

        if stat_type == "SCORING":
            url = BASE + stat.attrs["href"]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            all_years = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all(
                "tr"
            )
            for each_year in all_years:
                data = defaultdict()
                YEAR, TEAM, GP, GS, MPG, PPG = [
                    value.getText().strip() for value in each_year.find_all("td")[:6]
                ]
                if TEAM == "TOTAL":
                    continue
                FPR = each_year.find_all("td")[10].getText().strip()
                data["Year"] = YEAR
                data["Team"] = TEAM
                data["GP"] = GP
                data["GS"] = GS
                data["MPG"] = MPG
                data["PPG"] = PPG
                data["FPR"] = FPR
                player_info["stats"].append(data)
        elif stat_type == "REBOUNDING":
            url = BASE + stat.attrs["href"]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            all_years = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all(
                "tr"
            )
            delta = 0
            for i, each_year in enumerate(all_years):
                TEAM = each_year.find_all("td")[1].getText().strip()
                if TEAM == "TOTAL":
                    delta += 1
                    continue
                RPG = each_year.find_all("td")[5].getText().strip()
                player_info["stats"][i - delta]["RPG"] = RPG
        elif stat_type == "ASSISTS":
            url = BASE + stat.attrs["href"]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            all_years = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all(
                "tr"
            )
            delta = 0
            for i, each_year in enumerate(all_years):
                TEAM = each_year.find_all("td")[1].getText().strip()
                if TEAM == "TOTAL":
                    delta += 1
                    continue
                APG = each_year.find_all("td")[6].getText().strip()
                player_info["stats"][i - delta]["APG"] = APG

    history_teams = ""
    history_game = ""
    history_stats = ""
    for stat in player_info["stats"]:
        year, TEAM, GP, GS, MPG, PPG, FPR, RPG, APG = stat.values()
        year = year.replace("-", "\u200b-")
        history_teams += "{:<8} {:<8}".format(year, TEAM) + "\n"
        history_game += "{:<8} {:<8} {:<8}".format(year, f"{GS}/{GP}", MPG) + "\n"
        history_stats += "{:<8} {:<8}".format(year, f"{PPG}/{RPG}/{APG}/{FPR}%") + "\n"

    return (
        player_info["name"],
        history_teams[:-1],
        history_game[:-1],
        history_stats[:-1],
    )


def get_random_picture(album_id):
    endpoint = f"https://api.imgur.com/3/album/{album_id}/images"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        data = response.json()
        images = data["data"]
        if images:
            random_image = random.choice(images)
            image_url = random_image["link"]
            return image_url


def get_hupu_news():
    data = requests.get("https://bbs.hupu.com/4860").text
    soup = BeautifulSoup(data, "html.parser")

    newsThread = soup.find_all("a", class_="p-title")
    top5News = []
    for news in newsThread[:5]:
        title = news.text.strip()
        top5News.append(title.replace("[流言板]", ""))

    spliter = "\n" + "-" * 53 + "\n"
    return spliter.join(top5News)
