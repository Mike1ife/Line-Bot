from requests import get
from gspread import authorize
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from tools._table import nba_team_translations

static_len = 34


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


def reset_user_points(header, rows):
    all_user_name = [row[0] for row in rows]
    for user_name in all_user_name:
        header, rows = modify_value(header, rows, user_name, "Week Points", 0)
    return header, rows


def reset_match(header, rows):
    header = header[:static_len]
    rows = [row[:static_len] for row in rows]
    return header, rows


def modify_column_name(header, rows, index, new_name):
    # new column
    if (index + static_len) == len(header):
        header.insert(index + static_len, new_name)
        # insert empty value to each row to fill in column
        for i in range(len(rows)):
            fill_num = len(header) - len(rows[i])
            rows[i] += [""] * fill_num
    else:
        header[index + static_len] = new_name

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
    for row in rows:
        user_points = 0
        user_name = ""
        for i, value in enumerate(row):
            if header[i] == "Name":
                user_name = value
            elif header[i] == "Week Points":
                user_points = int(value)
            elif i >= 34:
                predicted_team = value
                winner, winner_point = header[i].split()

                is_winner = predicted_team == winner
                if is_winner:
                    user_points += int(winner_point)
                header, rows = add_belief_count(
                    header, rows, user_name, predicted_team, is_winner=is_winner
                )

        header, rows = modify_value(
            header, rows, user_name, "Week Points", str(user_points)
        )
    return header, rows


def column_exist(header, column):
    return True if column in header else False


def add_new_user(header, rows, name):
    match_num = len(header) - static_len
    new_row = [name, "0"] + [""] * match_num
    rows.append(new_row)
    return header, rows


def get_match_result(header, rows):
    if len(header) == static_len:
        return header, rows

    data = get(f"https://www.foxsports.com/nba/scores").text
    soup = BeautifulSoup(data, "html.parser")

    match_index = 0
    winner = None
    winners = []
    winner_score = 0
    teams = soup.find_all("div", class_="score-team-name abbreviation")
    scores = soup.find_all("div", class_="score-team-score")
    for team, score in zip(teams, scores):
        name = team.find("span", class_="scores-text uc").text.strip()
        point = score.find("span", class_="scores-text uc").text.strip()

        if match_index == 0:
            winner = nba_team_translations[name]
            winner_score = point
        else:
            if int(point) > int(winner_score):
                winner = nba_team_translations[name]
                winner_score = point
            winners.append(winner)

        match_index = (match_index + 1) % 2

    match_index = 0
    for match in header[static_len:]:
        teams, points = match.split()
        teams = teams.split("-")
        points = points.split("/")

        winner = winners[match_index]
        winner_point = points[teams.index(winner)]

        header, rows = modify_column_name(
            header, rows, match_index, f"{winner} {winner_point}"
        )

        match_index += 1

    return header, rows


def get_user_week_points(rows):
    users_info = []
    for row in rows:
        users_info.append((row[0], row[1]))
    user_ranks = sorted(users_info, key=lambda x: int(x[1]), reverse=True)

    return user_ranks


def get_user_month_points(rows):
    users_info = []
    for row in rows:
        users_info.append((row[0], row[2]))
    user_ranks = sorted(users_info, key=lambda x: int(x[1]), reverse=True)

    return user_ranks


def get_week_best(header, rows):
    user_ranks = get_user_week_points(rows)

    total = 100
    week_best = []
    for i, user in enumerate(user_ranks):
        header, rows = add_value(header, rows, user[0], "Month Points", total)
        total -= 10
        if i == 0:
            week_best.append(user)

    return header, rows, week_best


def get_nba_today():
    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    if int(TWnow.month) < 10:
        time = f"{TWnow.year}-0{TWnow.month}-{TWnow.day}"
    else:
        time = f"{TWnow.year}-{TWnow.month}-{TWnow.day}"
    data = get(f"https://www.foxsports.com/nba/scores?date={time}").text
    soup = BeautifulSoup(data, "html.parser")

    matches = []
    match = {}
    match_index = 0
    match_team = soup.find_all("div", class_="score-team-name abbreviation")

    for team in match_team:
        team_name = team.find("span", class_="scores-text uc")
        team_name = nba_team_translations[team_name.text.strip()]

        team_standing = team.find("sup", class_="scores-team-record ffn-gr-11")
        team_standing = team_standing.text.strip()

        if match_index == 0:
            match["name"] = [team_name]
            match["standing"] = [team_standing]
        else:
            match["name"].append(team_name)
            match["standing"].append(team_standing)
            matches.append(match.copy())
            match.clear()

        match_index = (match_index + 1) % 2

    match_index = 0
    values = soup.find_all("span", class_="secondary-text status ffn-11 opac-5 uc")
    for value in values:
        team_name, team_give = value.text.strip().split()
        match = matches[match_index]["name"]
        team_to_give = match.index(nba_team_translations[team_name])
        points = [0, 0]
        points[team_to_give] = int(round(20 + float(team_give)))
        points[1 ^ team_to_give] = int(round(20 + -float(team_give)))

        matches[match_index]["points"] = points
        match_index += 1

    return matches


def get_user_prediction(header, rows, name_index):
    if name_index < len(rows):
        name = rows[name_index][0]
        for row in rows:
            if row[0] == name:
                if row.count("") == len(header) - static_len:
                    return f"{name}還沒預測任何比賽"
                else:
                    response = f"{name}預測的球隊:\n"
                    indices = [i for i, x in enumerate(row) if x != ""]
                    game_names = [row[i].split()[0] for i in indices]
                    for team in game_names[static_len:]:
                        response += f"{team}\n"
                    return response[:-1]
    return "Unknown user"


def get_user_belief(header, rows, name):
    correct = {}
    for row in rows:
        if row[0] == name:
            for i in range(4, 34):
                correct[header[i]] = row[i].split()[0]
            correct = dict(
                sorted(correct.items(), key=lambda item: item[1], reverse=True)
            )
            return correct
    return "Unknown user"


def get_user_hatred(header, rows, name):
    wrong = {}
    for row in rows:
        if row[0] == name:
            for i in range(4, 34):
                wrong[header[i]] = row[i].split()[1]
            wrong = dict(sorted(wrong.items(), key=lambda item: item[1], reverse=True))
            return wrong
    return "Unknown user"


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
            if row.count("") == len(header) - static_len:
                return "還沒預測任何比賽"
            elif row.count("") == 0:
                return "已經完成全部預測"
            else:
                indices = [i for i, x in enumerate(row) if x == ""]
                game_names = [header[i].split()[0] for i in indices]
                response = "還沒預測:\n"
                for game_name in game_names:
                    response += f"{game_name}\n"
                return response[:-1]
    return "Unknown user"


def update_sheet(header, rows, worksheet):
    modified_data = [header] + rows
    worksheet.clear()
    worksheet.update("A1", modified_data)
