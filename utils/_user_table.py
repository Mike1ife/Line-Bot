import re
import json
import requests
from gspread import authorize
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN
from collections import Counter, defaultdict

PREDICT_INDEX = 35


def init():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("user_table.json", scopes=scope)
    gs = authorize(creds)

    sheet = gs.open_by_url(
        "https://docs.google.com/spreadsheets/d/1QajQuyDTjBiaoj1ucQOfbZu99ChWLIRffABoKFohw3A/edit?hl=zh-tw#gid=0"
    )
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_values()

    header, rows = data[0], data[1:]
    return header, rows, worksheet


def reset_user_points(header, rows, column):
    all_user_name = [row[0] for row in rows]
    for user_name in all_user_name:
        header, rows = modify_value(header, rows, user_name, column, 0)
    return header, rows


def reset_match(header, rows):
    header = header[:PREDICT_INDEX]
    rows = [row[:PREDICT_INDEX] for row in rows]
    return header, rows


def modify_column_name(header, rows, index, new_name):
    # new column
    if (index + PREDICT_INDEX) == len(header):
        header.insert(index + PREDICT_INDEX, new_name)
        # insert empty value to each row to fill in column
        for i in range(len(rows)):
            fill_num = len(header) - len(rows[i])
            rows[i] += [""] * fill_num
    else:
        header[index + PREDICT_INDEX] = new_name

    return header, rows


def modify_value(header, rows, name, column, winner):
    for i, row in enumerate(rows):
        if row[0] == name:
            row[header.index(column)] = winner
            break
    return header, rows


def add_belief_count(header, rows, name, predicted_team, is_winner):
    for row in rows:
        if row[0] == name:
            index = header.index(predicted_team)
            correct, wrong = row[index].split()
            if is_winner:
                correct = int(correct) + 1
            else:
                wrong = int(wrong) + 1
            row[index] = f"{correct} {wrong}"
            return header, rows


def add_value(header, rows, name, column, value):
    for i, row in enumerate(rows):
        if row[0] == name:
            row[header.index(column)] = int(value) + int(row[header.index(column)])
            break
    return header, rows


def count_points(header, rows):
    add_points = defaultdict(int)  # record the points added for each user
    for row in rows:
        user_points = 0
        user_name = ""

        for i, value in enumerate(row):
            if header[i] == "Name":
                user_name = value
            elif header[i] == "Week Points":
                user_points = int(value)
            # team: 公牛 30
            elif i >= 34 and header[i].count(" ") == 1:
                predicted_team = value
                if predicted_team not in NBA_ABBR_ENG_TO_ABBR_CN.values():
                    continue

                winner, winner_point = header[i].split()

                is_winner = predicted_team == winner
                if is_winner:
                    user_points += int(winner_point)
                    add_points[user_name] += int(winner_point)
                header, rows = add_belief_count(
                    header, rows, user_name, predicted_team, is_winner=is_winner
                )
            # player: Anthony Edwards 大盤 4
            elif i >= 34 and header[i].count(" ") >= 2:
                prediction = value
                # Anthony Edwards 大盤
                if prediction != "" and prediction in header[i]:
                    user_points += int(header[i].split()[-1])
                    add_points[user_name] += int(header[i].split()[-1])

        header, rows = modify_value(
            header, rows, user_name, "Week Points", str(user_points)
        )
    return header, rows, add_points


def column_exist(header, column):
    return True if column in header else False


def add_new_user(header, rows, name):
    match_num = len(header) - PREDICT_INDEX
    new_row = [name, "0", "0", "0", "0"] + ["0 0"] * 30 + [""] * match_num
    rows.append(new_row)
    return header, rows


def get_match_result(header, rows):
    if len(header) == PREDICT_INDEX:
        return header, rows

    data = requests.get(f"https://www.foxsports.com/nba/scores").text
    soup = BeautifulSoup(data, "html.parser")

    teams = soup.find_all("div", class_="score-team-name abbreviation")
    cancelled_teams = []  # 比賽取消隊伍 ["LAL","DAL"]
    if cancelled_teams:
        teams = [
            team
            for team in teams
            if (
                team_name_tag := team.find(
                    "span", class_="scores-text capi pd-b-1 ff-ff"
                )
            )
            and team_name_tag.text.strip() not in cancelled_teams
        ]
    scores = soup.find_all("div", class_="score-team-score")
    match_team = []
    match_point = []
    match_result = {}
    match_index = 0

    for team, score in zip(teams, scores):
        name = team.find("span", class_="scores-text capi pd-b-1 ff-ff").text.strip()
        point = score.find("span", class_="scores-text").text.strip()

        if match_index == 1 and len(match_point) == 0:
            match_index = 0
            continue

        try:
            match_team.append(NBA_ABBR_ENG_TO_ABBR_CN[name])
        except:
            if match_index == 0:
                match_index = 1
            else:
                match_index = 0
            match_team.clear()
            match_point.clear()
            continue

        # handle finished games bug (as unfinished)
        # finished_points = [104, 116]
        # if point == "-":
        #     point = finished_points[match_index]

        match_point.append(int(point))

        if match_index != 0:
            match_result["-".join(match_team)] = match_team[
                int(match_point[1] > match_point[0])
            ]
            match_team.clear()
            match_point.clear()

        match_index = (match_index + 1) % 2

    match_index = 0
    for match in header[PREDICT_INDEX:]:
        if match.count(" ") >= 2:
            break
        teams, points = match.split()
        try:
            winner = match_result[teams]
        except:
            temp = teams
            temp = temp.split("-")
            temp.reverse()
            winner = match_result["-".join(temp)]

        teams = teams.split("-")
        points = points.split("/")

        winner_point = points[teams.index(winner)]

        header, rows = modify_column_name(
            header, rows, match_index, f"{winner} {winner_point}"
        )

        match_index += 1

    return header, rows


def get_player_result(header, rows):
    for i in range(PREDICT_INDEX, len(header)):
        # Original: Anthony Edwards 得分26.5 4/6
        # Aim: Anthony Edwards 大盤 6
        if header[i].count(" ") >= 2:
            header_items = header[i].split()
            player = " ".join(header_items[:-2])
            stat_type, target = header_items[-2][:2], float(header_items[-2][2:])
            over_point, under_point = header_items[-1].split("/")

            with open("utils/player_link.json", "r", encoding="utf-8") as f:
                player_url_table = json.load(f)
            url = player_url_table[player]

            data = requests.get(url).text
            soup = BeautifulSoup(data, "html.parser")
            container = soup.find("tbody", class_="row-data lh-1pt43 fs-14")
            game = container.find("tr")

            DATA_INDEX = {"得分": 3, "籃板": 5, "抄截": 7}
            value = int(
                game.find("td", {"data-index": DATA_INDEX[stat_type]}).text.strip()
            )

            if value >= target:
                new_header = f"{player} 大盤 {over_point}"
            else:
                new_header = f"{player} 小盤 {under_point}"
            header, rows = modify_column_name(
                header, rows, i - PREDICT_INDEX, new_header
            )

    return header, rows


def get_user_points(rows, rank_type="week"):
    mapping = {"week": 1, "month": 2, "season": 3, "all-time": 4}
    users_info = []

    for row in rows:
        users_info.append((row[0], row[mapping[rank_type]]))
    user_ranks = sorted(users_info, key=lambda x: int(x[1]), reverse=True)

    return user_ranks


def get_week_best(header, rows):
    user_ranks = get_user_points(rows, "week")
    if all([x[1] == "0" for x in user_ranks]):
        return header, rows, []

    point = 100.0
    total_best = 0.0
    current_best = 0.0
    reduction = 0.0
    week_best = []
    for i, user in enumerate(user_ranks):
        if i == 0:
            total_best = user[1]
            week_best.append(user)
        elif user[1] == total_best:
            week_best.append(user)
        elif user[1] != current_best:
            point -= reduction
            reduction = 0.0

        # print(user[0], user[1], point, current_best)

        header, rows = add_value(header, rows, user[0], "Month Points", point)

        current_best = user[1]
        reduction += 10

    return header, rows, week_best


def get_month_best(header, rows):
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    weekday = TWnow.weekday()

    if weekday != 0:
        user_ranks = get_user_points(rows, "week")
        if any([x[1] != "0" for x in user_ranks]):
            point = 100.0
            current_best = 0.0
            reduction = 0.0
            for i, user in enumerate(user_ranks):
                if user[1] != current_best and i != 0:
                    point -= reduction
                    reduction = 0.0

                header, rows = add_value(
                    header,
                    rows,
                    user[0],
                    "Month Points",
                    round(point * ((weekday) / 7.0)),
                )

                current_best = user[1]
                reduction += 10

    user_ranks = get_user_points(rows, "month")
    if all([x[1] == "0" for x in user_ranks]):
        return header, rows, []

    point = 100.0
    total_best = 0.0
    current_best = 0.0
    reduction = 0.0
    month_best = []
    for i, user in enumerate(user_ranks):
        if i == 0:
            total_best = user[1]
            month_best.append(user)
        elif user[1] == total_best:
            month_best.append(user)
        elif user[1] != current_best:
            point -= reduction
            reduction = 0.0

        # print(user[0], user[1], point, current_best)

        header, rows = add_value(header, rows, user[0], "Year Points", point)

        current_best = user[1]
        reduction += 10

    return header, rows, month_best


def get_season_best(header, rows):
    user_ranks = get_user_points(rows, "season")

    if all([x[1] == "0" for x in user_ranks]):
        return header, rows, []

    point = 100.0
    total_best = 0.0
    current_best = 0.0
    reduction = 0.0
    season_best = []
    for i, user in enumerate(user_ranks):
        if i == 0:
            total_best = user[1]
            season_best.append(user)
        elif user[1] == total_best:
            season_best.append(user)
        elif user[1] != current_best:
            point -= reduction
            reduction = 0.0

        print(user[0], user[1], point, current_best)

        header, rows = add_value(header, rows, user[0], "All-time Points", point)

        current_best = user[1]
        reduction += 10

    return header, rows, season_best


def _get_nba_gametime():
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
    gametimes = []
    for card in cards:
        gametimes.append(card.find("span", class_="during").text.strip())

    return gametimes


def get_nba_today():
    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    year, month, day = TWnow.year, TWnow.month, TWnow.day
    if month < 10:
        month = f"0{month}"
    if day < 10:
        day = f"0{day}"
    time = f"{year}-{month}-{day}"

    data = requests.get(f"https://www.foxsports.com/nba/scores?date={time}").text
    soup = BeautifulSoup(data, "html.parser")
    scores = soup.find_all("div", class_="score-team-score")

    pattern = r'<a href="/nba/scores\?date=(\d{4}-\d{2}-\d{2})"'
    if len(scores) != 0 or time not in re.findall(pattern, data):
        return []

    gametimes = _get_nba_gametime()
    matches_info = soup.find_all("a", class_="score-chip pregame")
    matches = []

    for match_info, gametime in zip(matches_info, gametimes):
        teams = match_info.find("div", class_="teams").find_all(
            "div", class_="score-team-row"
        )
        match_page_link = "https://www.foxsports.com" + match_info.attrs["href"]
        match_page_data = requests.get(match_page_link).text
        match_page_soup = BeautifulSoup(match_page_data, "html.parser")
        match_page_odd_container = match_page_soup.find(
            "div", class_="odds-row-container"
        )
        odds = match_page_odd_container.find_all(
            "div", class_="odds-line fs-20 fs-xl-30 fs-sm-23 lh-1 lh-md-1pt5"
        )

        match = {
            "name": ["", ""],
            "standing": ["", ""],
            "points": [0, 0],
            "gametime": gametime,
        }
        for i, team in enumerate(teams):
            team_info = team.find("div", class_="score-team-name abbreviation")
            teamname = team_info.find(
                "span", class_="scores-text capi pd-b-1 ff-ff"
            ).text
            teamstanding = team_info.find(
                "sup", class_="scores-team-record ffn-gr-10"
            ).text
            match["name"][i] = NBA_ABBR_ENG_TO_ABBR_CN[teamname]
            match["standing"][i] = teamstanding
            match["points"][i] = int(round(30 + float(odds[i].text.strip())))

        matches.append(match)

    return matches


def get_nba_playoffs():
    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    year, month, day = TWnow.year, TWnow.month, TWnow.day
    if month < 10:
        month = f"0{month}"
    if day < 10:
        day = f"0{day}"
    time = f"{year}-{month}-{day}"

    data = requests.get(f"https://www.foxsports.com/nba/scores?date={time}").text
    soup = BeautifulSoup(data, "html.parser")
    scores = soup.find_all("div", class_="score-team-score")

    pattern = r'<a href="/nba/scores\?date=(\d{4}-\d{2}-\d{2})"'
    if len(scores) != 0 or time not in re.findall(pattern, data):
        return []

    gametimes = _get_nba_gametime()
    matches_info = soup.find_all("a", class_="score-chip-playoff pregame")
    matches = []

    for match_info, gametime in zip(matches_info, gametimes):
        team1 = match_info.find("img", class_="team-logo-1").attrs["alt"]
        team2 = match_info.find("img", class_="team-logo-2").attrs["alt"]

        standing_text = match_info.find(
            "div", class_="playoff-game-info ffn-gr-11 uc fs-sm-10"
        ).text.strip()

        standing_info = standing_text.split()
        game_id = standing_info[1]
        # GM 4 TIED 2-2
        if standing_info[2] == "TIED":
            tie = standing_info[-1].split("-")[0]
            teamstandings = [tie, tie]
        # GM 5 LAL LEADS 3-1
        else:
            leading_team = standing_info[2]
            teamstandings_text = standing_info[-1]
            s1, s2 = teamstandings_text.split("-")
            if leading_team == team1:
                teamstandings = [s1, s2]
            else:
                teamstandings = [s2, s1]

        match_page_link = "https://www.foxsports.com" + match_info.attrs["href"]
        match_page_data = requests.get(match_page_link).text
        match_page_soup = BeautifulSoup(match_page_data, "html.parser")
        match_page_odd_container = match_page_soup.find(
            "div", class_="odds-row-container"
        )
        odds = match_page_odd_container.find_all(
            "div", class_="odds-line fs-20 fs-xl-30 fs-sm-23 lh-1 lh-md-1pt5"
        )

        match = {
            "name": ["", ""],
            "standing": ["", ""],
            "points": [0, 0],
            "game_id": game_id,
            "gametime": gametime,
        }

        match["name"] = [NBA_ABBR_ENG_TO_ABBR_CN[team1], NBA_ABBR_ENG_TO_ABBR_CN[team2]]
        match["standing"] = teamstandings
        match["points"] = [
            int(round(30 + float(odds[0].text.strip()))),
            int(round(30 + float(odds[1].text.strip()))),
        ]

        matches.append(match)

    return matches


def get_user_prediction(header, rows, name_index):
    if name_index < len(rows):
        name = rows[name_index][0]
        for row in rows:
            if row[0] == name:
                if row.count("") == len(header) - PREDICT_INDEX:
                    return f"{name}還沒預測任何比賽"
                else:
                    response = f"{name}預測的球隊:\n"
                    indices = [i for i, x in enumerate(row) if x != ""]
                    game_names = [row[i] for i in indices]
                    for team in game_names[PREDICT_INDEX:]:
                        response += f"{team}\n"
                    return response[:-1]
    return "Unknown user"


def shorten_common_prefix(a_str, b_str):
    """
    a_str = "Zach LaVine 大盤"
    b_str = "Zach LaVine 小盤"
    => "Zach LaVine 大盤 (小盤)"
    """
    # 兩者都空
    if not a_str and not b_str:
        return ""
    # 一方空
    if not a_str and b_str:
        return f"( {b_str} )"
    if a_str and not b_str:
        return f"{a_str} ( )"
    # 找出相同的前綴
    a_words = a_str.split()
    b_words = b_str.split()
    idx = 0
    while idx < min(len(a_words), len(b_words)) and a_words[idx] == b_words[idx]:
        idx += 1

    if idx == 0:
        # 無相同前綴
        return f"{a_str} ({b_str})"
    else:
        # 有相同前綴
        prefix = " ".join(a_words[:idx])
        suffix_a = " ".join(a_words[idx:])
        suffix_b = " ".join(b_words[idx:])

        if suffix_a == "" and suffix_b == "":
            # 完全相同
            return a_str
        elif suffix_a != "" and suffix_b != "":
            return f"{prefix} {suffix_a} ({suffix_b})"
        elif suffix_a == "" and suffix_b != "":
            return f"{prefix} ({suffix_b})"
        else:
            return f"{prefix} {suffix_a} ( )"


def compare_user_prediction(header, rows, index_a, index_b):
    """
    比較 rows[index_a] 和 rows[index_b] 的預測
    """
    any_diff = False
    # 判斷是否超出範圍
    if index_a >= len(rows) or index_b >= len(rows):
        return "比對錯誤，未知使用者"

    row_a = rows[index_a]
    row_b = rows[index_b]
    name_a = row_a[0]
    name_b = row_b[0]

    # 都沒預測
    if (row_a.count("") == len(header) - PREDICT_INDEX) and (
        row_b.count("") == len(header) - PREDICT_INDEX
    ):
        return f"{name_a} 和 {name_b} 都還沒預測任何比賽"

    lines = []
    # 從 PREDICT_INDEX比較到最後
    for col_index in range(PREDICT_INDEX, len(header)):
        predict_a = row_a[col_index].strip()
        predict_b = row_b[col_index].strip()
        # 兩方都空，不輸出
        if not predict_a and not predict_b:
            continue
        # 相同只印一次
        if predict_a == predict_b:
            lines.append(predict_a)
        else:
            # 不同，省略前綴
            any_diff = True
            merged = shorten_common_prefix(predict_a, predict_b)
            lines.append(merged)
    # 無任何差異
    if not any_diff:
        return f"{name_a} 與 {name_b} 的預測相同。"
    # 輸出結果
    response = f"{name_a} 與 {name_b} 的不同預測：\n"
    response += "\n".join(lines)
    return response


def get_user_belief(header, rows, name):
    correct = {}
    for row in rows:
        if row[0] == name:
            for i in range(PREDICT_INDEX - 30, PREDICT_INDEX):
                correct[header[i]] = int(row[i].split()[0])
            correct = dict(
                sorted(correct.items(), key=lambda item: item[1], reverse=True)
            )
            return correct
    return "Unknown user"


def get_user_hatred(header, rows, name):
    wrong = {}
    for row in rows:
        if row[0] == name:
            for i in range(PREDICT_INDEX - 30, PREDICT_INDEX):
                wrong[header[i]] = int(row[i].split()[1])
            wrong = dict(sorted(wrong.items(), key=lambda item: item[1], reverse=True))
            return wrong
    return "Unknown user"


def reset_belief_hatred(header, rows):
    # get most belief/hatred
    all_user_belief, all_user_hatred = [], []
    for row in rows:
        correct, wrong = {}, {}
        for i in range(PREDICT_INDEX - 30, PREDICT_INDEX):
            correct[header[i]] = int(row[i].split()[0])
            wrong[header[i]] = int(row[i].split()[1])
        correct = dict(sorted(correct.items(), key=lambda item: item[1], reverse=True))
        wrong = dict(sorted(wrong.items(), key=lambda item: item[1], reverse=True))

        belief = max(correct.keys(), key=(lambda key: correct[key]))
        all_user_belief.append(belief)

        hatred = max(wrong.keys(), key=(lambda key: wrong[key]))
        all_user_hatred.append(hatred)
    # Counter(all_user_belief).most_common(1) = [('塞爾提克', 6)]
    most_belief_team = Counter(all_user_belief).most_common(1)[0][0]
    most_hatred_team = Counter(all_user_hatred).most_common(1)[0][0]

    # reset
    for row in rows:
        for i in range(PREDICT_INDEX - 30, PREDICT_INDEX):
            row[i] = "0 0"
    return rows, most_belief_team, most_hatred_team


def check_user_exist(rows, name):
    return any(name in row for row in rows)


def user_predicted(header, rows, name, column):
    col_index = header.index(column)
    user_info = None
    for row in rows:
        if row[0] == name:
            user_info = row
            break

    # have not predicted

    if user_info[col_index] == "":
        return False

    return True


def check_user_prediction(header, rows, name):
    for row in rows:
        if row[0] == name:
            if row.count("") == len(header) - PREDICT_INDEX:
                return "還沒預測任何比賽"
            elif row.count("") == 0:
                return "已經完成全部預測"
            else:
                game_names = []
                indices = [i for i, x in enumerate(row) if x == ""]
                for i in indices:
                    hearder_items = header[i].split()
                    if len(hearder_items) == 2:
                        game_names.append(hearder_items[0])
                    else:
                        game_names.append(" ".join(hearder_items[:-2]))
                response = "還沒預測:\n"
                for game_name in game_names:
                    response += f"{game_name}\n"
                return response[:-1]
    return "Unknown user"


def update_sheet(header, rows, worksheet):
    modified_data = [header] + rows
    worksheet.clear()
    worksheet.update("A1", modified_data)
