import psycopg
from utils._api_SQL import *
from config import DATABASE_URL

_conn = None


def _get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DATABASE_URL)
    return _conn


def get_user_info_and_day_point():
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SELECT_USER_DAY_POINT)
        # [(name1, url1, point1), (name2, url2, point2), ...]
        resultDict = [
            {"name": userName, "picture_url": pictureUrl, "point": point}
            for userName, pictureUrl, point in cur.fetchall()
        ]
        return resultDict
