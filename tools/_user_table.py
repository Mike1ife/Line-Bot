from gspread import authorize
from google.oauth2.service_account import Credentials


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
    new_row = [name, "0"]
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


def update_sheet(header, rows, worksheet):
    modified_data = [header] + rows
    worksheet.clear()
    worksheet.update("A1", modified_data)
