from google.oauth2.service_account import Credentials
from gspread import authorize
from pandas import DataFrame, concat
from numpy import nan


def init():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("gs_credentials.json", scopes=scope)
    gs = authorize(creds)

    sheet = gs.open_by_url(
        "https://docs.google.com/spreadsheets/d/1QajQuyDTjBiaoj1ucQOfbZu99ChWLIRffABoKFohw3A/edit?hl=zh-tw#gid=0"
    )
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_values()

    df = DataFrame(data[1:], columns=data[0])
    return df, worksheet


def modify_column_name(df, index, new_name):
    # new column
    if (index + 2) == len(df.columns):
        df.insert(loc=index + 2, column=new_name, value="")
    else:
        df.columns.values[index + 2] = new_name
    return df


def check_user_exist(df, name):
    return True if name in df["Name"].values else False


def add_new_user(df, name):
    new_row = {"Name": name, "Points": "0"}
    df = concat([df, DataFrame([new_row])], ignore_index=True)
    df.replace({nan: ""}, inplace=True)
    return df


def reset_match(df):
    df.drop(df.iloc[:, 2:], inplace=True, axis=1)
    return df


def modify_value(df, name, column, value):
    df.at[df.index[df["Name"] == name].tolist()[0], column] = value
    return df


def count_points(df, name):
    user_points = 0
    for index, row in df[df["Name"] == name].iterrows():
        for keys, values in row.items():
            if keys != "Name":
                if keys == "Points":
                    user_points = int(values)
                elif values == keys:
                    user_points += 10

    df = modify_value(df, name, "Points", user_points)
    return df


def update_sheet(df, worksheet):
    modified_data = [df.columns.tolist()] + df.values.tolist()
    worksheet.clear()
    worksheet.update("A1", modified_data)
