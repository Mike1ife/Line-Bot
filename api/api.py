import requests
import psycopg
from bs4 import BeautifulSoup

from api._api_SQL import *
from utils._user_table_SQL import SQL_UPDATE_MATCH_SCORE
from utils.utils import get_daily_game_results
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
            {"name": userName, "picture_url": pictureUrl, "point": point}
            for userName, pictureUrl, point in cur.fetchall()
        ]
        return resultDict


def get_daily_match_info():
    conn = _get_connection()

    resultDict = []
    with conn.cursor() as cur:
        gameScores = get_daily_game_results()
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
                    "team1_logo_url": team1LogoUrl,
                    "team2_logo_url": team2LogoUrl,
                    "team1_standing": team1Standing,
                    "team2_standing": team2Standing,
                    "team1_score": team1Score,
                    "team2_score": team2Score,
                    "team1_point": team1Point,
                    "team2_point": team2Point,
                }
            )

        return resultDict
