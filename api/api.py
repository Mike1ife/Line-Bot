import requests
import psycopg
from bs4 import BeautifulSoup

from api._api_SQL import *
from utils._team_table import NBA_SIMP_CN_TO_TRAD_CN
from utils._user_table_SQL import SQL_UPDATE_MATCH_SCORE
from config import DATABASE_URL

_conn = None


def _get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DATABASE_URL)
    return _conn


def get_user_info_and_type_point(rankType: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER_TYPE_POINT[rankType])
        # [(name1, url1, point1), (name2, url2, point2), ...]
        resultDict = [
            {"userName": userName, "pictureUrl": pictureUrl, "point": point}
            for userName, pictureUrl, point in cur.fetchall()
        ]
        return resultDict


def _get_nba_live_score():
    data = requests.get("https://nba.hupu.com/games").text
    soup = BeautifulSoup(data, "html.parser")

    gameCenter = soup.find("div", class_="gamecenter_content_l")
    gameContainers = gameCenter.find_all("div", class_="list_box")

    gameScores = {}
    gameTimes = {}
    for gameContainer in gameContainers:
        teams = gameContainer.find("div", class_="team_vs_a")
        team1 = teams.find("div", class_="team_vs_a_1 clearfix")
        team2 = teams.find("div", class_="team_vs_a_2 clearfix")
        team1Name = team1.find("div", class_="txt").find("a").text
        team2Name = team2.find("div", class_="txt").find("a").text

        if (
            team1Name not in NBA_SIMP_CN_TO_TRAD_CN
            or team2Name not in NBA_SIMP_CN_TO_TRAD_CN
        ):
            continue

        team1Name = NBA_SIMP_CN_TO_TRAD_CN[team1Name]
        team2Name = NBA_SIMP_CN_TO_TRAD_CN[team2Name]

        team1Score = team2Score = gameTime = ""
        gameStatus = gameContainer.find("div", class_="team_vs").text
        if "进行中" in gameStatus:
            team1Score = team1.find("div", class_="txt").find("span", class_="num").text
            team2Score = team2.find("div", class_="txt").find("span", class_="num").text
        elif "未开始" in gameStatus:
            gameTime = (
                gameContainer.find("div", class_="team_vs_b")
                .find("span", class_="b")
                .find("p")
                .text
            )
            if gameTime == "00:00":
                gameTime = "12:00"
        elif "已结束" in gameStatus:
            team1Win = team1.find("div", class_="txt").find("span", class_="num red")
            if team1Win:
                team1Score = team1Win.text
                team2Score = (
                    team2.find("div", class_="txt").find("span", class_="num").text
                )
            else:
                team1Score = (
                    team1.find("div", class_="txt").find("span", class_="num").text
                )
                team2Score = (
                    team2.find("div", class_="txt").find("span", class_="num red").text
                )

        gameScores[(team1Name, team2Name)] = (
            int(team1Score) if team1Score else 0,
            int(team2Score) if team2Score else 0,
        )
        gameTimes[(team1Name, team2Name)] = gameTime

    return gameScores, gameTimes


def get_daily_match_info():
    conn = _get_connection()

    resultDict = []
    with conn.cursor() as cur:
        gameScores, gameTimes = _get_nba_live_score()
        for team1Name, team2Name in gameScores:
            team1Score, team2Score = gameScores[(team1Name, team2Name)]
            cur.execute(
                SQL_UPDATE_MATCH_SCORE,
                (
                    team1Name,
                    team1Score,
                    team2Score,
                    team2Name,
                    team2Score,
                    team1Score,
                    team1Name,
                    team2Name,
                    team2Name,
                    team1Name,
                ),
            )
        conn.commit()

        cur.execute(SQL_SELECT_MATCH_TODAY)
        # [(team1Name, team2Name, team1Score, team2Score, team1Point, team2Point)]
        matchInfoList = cur.fetchall()
        for (
            team1Name,
            team2Name,
            team1Score,
            team2Score,
            team1Point,
            team2Point,
        ) in matchInfoList:
            # (team1LogoUrl, team1Standing)
            cur.execute(SQL_SELECT_TEAM_LOGO_AND_STANDING, (team1Name,))
            team1LogoUrl, team1Standing = cur.fetchone()
            cur.execute(SQL_SELECT_TEAM_LOGO_AND_STANDING, (team2Name,))
            team2LogoUrl, team2Standing = cur.fetchone()
            resultDict.append(
                {
                    "team1LogoUrl": team1LogoUrl,
                    "team2LogoUrl": team2LogoUrl,
                    "team1Standing": team1Standing,
                    "team2Standing": team2Standing,
                    "team1Score": team1Score,
                    "team2Score": team2Score,
                    "team1Point": team1Point,
                    "team2Point": team2Point,
                    "gameTime": (
                        gameTimes[(team1Name, team2Name)]
                        if (team1Name, team2Name) in gameTimes
                        else (
                            gameTimes[(team2Name, team1Name)]
                            if (team2Name, team1Name) in gameTimes
                            else ""
                        )
                    ),
                }
            )

    return resultDict


def fetch_user_profile(userName: str):
    conn = _get_connection()

    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER_PROFILE, (userName,))
        (
            pictureUrl,
            dayPoints,
            weekPoints,
            monthPoints,
            seasonPoints,
            allTimePoints,
        ) = cur.fetchone()
        resultDict = {
            "userName": userName,
            "pictureUrl": pictureUrl,
            "dayPoints": dayPoints,
            "weekPoints": weekPoints,
            "monthPoints": monthPoints,
            "seasonPoints": seasonPoints,
            "allTimePoints": allTimePoints,
        }
        return resultDict


def fetch_user_point_history(userName: str, rankType: str):
    conn = _get_connection()
    resultDict = []
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER_POINT_HISTORY, (userName, rankType))
        for pointValue, period in cur.fetchall():
            resultDict.append({"pointValue": pointValue, "period": period})

    return resultDict


def fetch_user_counter(userName: str, countType: str, countRange: str):
    conn = _get_connection()
    resultDict = []
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER_COUNTER[countType][countRange], (userName,))
        for teamName, count in cur.fetchall():
            resultDict.append({"teamName": teamName, "count": count})
    return resultDict
