from gspread import authorize
from google.oauth2.service_account import Credentials

import tools._user_table


def init():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("rank_table.json", scopes=scope)
    gs = authorize(creds)

    sheet = gs.open_by_url(
        "https://docs.google.com/spreadsheets/d/1KCgC7QPpzvfuejk11qEBEn0u7Dej5HKc4OPyhIbneSg/edit#gid=0"
    )
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_values()

    header, rows = data[0], data[1:]
    return header, rows, worksheet


def reset_column(header, rows, columns):
    all_user_name = [row[0] for row in rows]
    for user_name in all_user_name:
        header, rows = modify_value(header, rows, user_name, columns, 0, "modify")
    return header, rows


def modify_value(header, rows, name, column, value, method):
    for i, row in enumerate(rows):
        if row[0] == name:
            if method == "add":
                row[header.index(column)] = int(value) + int(row[header.index(column)])
            elif method == "modify":
                row[header.index(column)] = value
            break
    return header, rows


def get_day_point(header, rows):
    user_table, user_rows, user_worksheet = tools._user_table.init()
    for user_row in user_rows:
        user_name = user_row[0]
        user_point = user_row[1]
        header, rows = modify_value(
            header, rows, user_name, "Day Points", user_point, "modify"
        )
    return header, rows


def get_week_best(header, rows):
    header, rows = get_day_point(header, rows)

    users_info = []
    for row in rows:
        users_info.append((row[0], row[1]))
    user_ranks = sorted(users_info, key=lambda x: int(x[1]), reverse=True)

    week_best = []
    current_best = -1
    for user in user_ranks:
        user_name = user[0]
        user_point = int(user[1])
        if user_point >= current_best:
            week_best.append(user_name)
            current_best = user_point
        else:
            break

    best_point = round(100.0 / len(week_best))
    for best_user in week_best:
        header, rows = modify_value(
            header, rows, best_user, "Week Points", best_point, "add"
        )

    header, rows = reset_column(header, rows, "Day Points")
    return header, rows, week_best


def get_month_best(header, rows):
    pass


def get_year_best(header, rows):
    pass
