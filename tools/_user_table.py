from requests import get
from gspread import authorize
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

from _table import nba_team_translations


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
            elif value == header[i]:
                user_points += 10

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
    UTCnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    TWyesterday = UTCnow.astimezone(timezone(timedelta(hours=-16)))
    time = f"{TWyesterday.year}-{TWyesterday.month}-{TWyesterday.day}"

    data = get(f"https://www.foxsports.com/nba/scores?date={time}").text
    soup = BeautifulSoup(data, "html.parser")
    team_rows = soup.find_all(class_="score-team-row")

    team1 = {"name": "x", "score": "0"}
    team2 = {"name": "x", "score": "0"}

    match_index = 0
    i = 1
    for team_row in team_rows:
        team_name_elements = team_row.find_all(class_="score-team-name team")
        team = team_name_elements[0].get_text() if team_name_elements else None
        team = team.split()
        team_name = nba_team_translations[team[0]]

        score_element = team_row.find(class_="score-team-score")
        team_score = score_element.get_text().strip() if score_element else "0"

        if i == 1:
            team1["name"] = team_name
            team1["score"] = team_score
            i += 1
        else:
            team2["name"] = team_name
            team2["score"] = team_score

            winner = ""
            if int(team1["score"]) > int(team2["score"]):
                winner = team1["name"]
            else:
                winner = team2["name"]
            header, rows = modify_column_name(header, rows, match_index, winner)

            match_index += 1
            i = 1

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
