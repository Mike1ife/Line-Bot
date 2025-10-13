import psycopg
from utils._api_SQL import *
from config import DATABASE_URL


def get_all_user_info():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SELECT_ALL_USER_INFO)
            # [(name1, url1), (name2, url2), ...]
            resultDict = [
                {"name": userName, "picture_url": pictureUrl}
                for userName, pictureUrl in cur.fetchall()
            ]
            return resultDict
