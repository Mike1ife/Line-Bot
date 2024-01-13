from requests import get
from gspread import authorize
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from tools._table import nba_team_translations


def init():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("gs_credentials.json", scopes=scope)
    gs = authorize(creds)

    sheet = gs.open_by_url(
        "https://docs.google.com/spreadsheets/d/1QajQuyDTjBiaoj1ucQOfbZu99ChWLIRffABoKFohw3A/edit?hl=zh-tw#gid=0"
    )
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_values()

    header, rows = data[0], data[1:]
    return header, rows, worksheet


def modify_column_name(header, rows, index, new_name):
    # new column
    if (index + 2) == len(header):
        header.insert(index + 2, new_name)
        # insert empty value to each row to fill in column
        for i in range(len(rows)):
            fill_num = len(header) - len(rows[i])
            rows[i] += [""] * fill_num
    else:
        header[index + 2] = new_name

    return header, rows


def check_user_exist(rows, name):
    return any(name in row for row in rows)


def add_new_user(header, rows, name):
    match_num = len(header) - 2
    new_row = [name, "0"] + [""] * match_num
    rows.append(new_row)
    return header, rows


def reset_match(header, rows):
    header = header[:2]
    rows = [[row[0], row[1]] for row in rows]
    return header, rows


def modify_value(header, rows, name, column, value):
    for i, row in enumerate(rows):
        if row[0] == name:
            row[header.index(column)] = value
            break
    return header, rows


def count_points(header, rows):
    for row in rows:
        user_points = 0
        user_name = ""
        for i, value in enumerate(row):
            if header[i] == "Name":
                user_name = value
            elif header[i] == "Points":
                user_points = int(value)
            else:
                predicted_team = value
                winner, winner_point = header[i].split()
                if predicted_team == winner:
                    user_points += int(winner_point)

        header, rows = modify_value(header, rows, user_name, "Points", str(user_points))
    return header, rows


def column_exist(header, column):
    return True if column in header else False


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


def get_match_result(header, rows):
    if len(header) == 2:
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
    for match in header[2:]:
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


def get_user_points(rows):
    users_info = []
    for row in rows:
        users_info.append((row[0], row[1]))
    user_ranks = sorted(users_info, key=lambda x: int(x[1]), reverse=True)

    return user_ranks


def update_sheet(header, rows, worksheet):
    modified_data = [header] + rows
    worksheet.clear()
    worksheet.update("A1", modified_data)


def get_nba_today():
    time = None
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=-16)))
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
