import psycopg
import requests
from bs4 import BeautifulSoup
from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN

DATABASE_URL = "your_db_url"


def CREATE_USER_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS users (
                uid TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                picture_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                day_points INTEGER DEFAULT 0,
                week_points INTEGER DEFAULT 0,
                month_points INTEGER DEFAULT 0,
                season_points INTEGER DEFAULT 0,
                all_time_points INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE
            );
            """
            cur.execute(SQL)
            conn.commit()


def CREATE_TEAM_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS team (
                team_name TEXT PRIMARY KEY
            );
            """
            cur.execute(SQL)
            conn.commit()


def CREATE_COUNTER_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS counter (
                uid TEXT NOT NULL,
                team_name TEXT NOT NULL,
                season_correct_count INTEGER DEFAULT 0,
                all_time_correct_count INTEGER DEFAULT 0,
                season_wrong_count INTEGER DEFAULT 0,
                all_time_wrong_count INTEGER DEFAULT 0,
                CONSTRAINT counter_pk PRIMARY KEY (uid, team_name),
                CONSTRAINT counter_user_fk FOREIGN KEY (uid)
                    REFERENCES users(uid)
                    ON DELETE CASCADE,
                CONSTRAINT counter_team_fk FOREIGN KEY (team_name)
                    REFERENCES team(team_name)
                    ON DELETE CASCADE
            );
            """
            cur.execute(SQL)
            conn.commit()


def CREATE_MATCH_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS match (
                match_id SERIAL PRIMARY KEY,
                game_date DATE NOT NULL,
                team1_name TEXT NOT NULL,
                team2_name TEXT NOT NULL,
                team1_score INTEGER DEFAULT 0,
                team2_score INTEGER DEFAULT 0,
                team1_point INTEGER DEFAULT 30,
                team2_point INTEGER DEFAULT 30,
                is_active BOOLEAN DEFAULT TRUE,
                winner TEXT,
                CONSTRAINT date_teams_unique UNIQUE (game_date, team1_name, team2_name),
                CONSTRAINT match_team1_fk FOREIGN KEY (team1_name)
                    REFERENCES team(team_name)
                    ON DELETE CASCADE,
                CONSTRAINT match_team2_fk FOREIGN KEY (team2_name)
                    REFERENCES team(team_name)
                    ON DELETE CASCADE,
                CONSTRAINT match_winner_fk FOREIGN KEY (winner)
                    REFERENCES team(team_name)
                    ON DELETE SET NULL
            );
            """
            cur.execute(SQL)
            conn.commit()


def CREATE_USER_PREDICT_MATCH_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS user_predict_match (
                uid TEXT NOT NULL,
                match_id INTEGER NOT NULL,
                predicted_team TEXT NOT NULL,
                is_correct BOOLEAN,
                CONSTRAINT user_predict_match_pk PRIMARY KEY (uid, match_id),
                CONSTRAINT user_predict_match_user_fk FOREIGN KEY (uid)
                    REFERENCES users(uid)
                    ON DELETE CASCADE,
                CONSTRAINT user_predict_match_match_fk FOREIGN KEY (match_id)
                    REFERENCES match(match_id)
                    ON DELETE CASCADE,
                CONSTRAINT user_predict_match_team_fk FOREIGN KEY (predicted_team)
                    REFERENCES team(team_name)
                    ON DELETE CASCADE
            );
            """
            cur.execute(SQL)
            conn.commit()


def CREATE_PLAYER_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS player (
                player_name TEXT PRIMARY KEY,
                player_page_url TEXT
            );
            """
            cur.execute(SQL)
        conn.commit()


def CREATE_PLAYER_STAT_BET_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS player_stat_bet (
                player_name TEXT NOT NULL,
                match_id INTEGER NOT NULL,
                stat_type TEXT NOT NULL CHECK (stat_type IN ('得分', '籃板', '抄截')),
                stat_target FLOAT NOT NULL,
                stat_result FLOAT,
                over_point INTEGER NOT NULL,
                under_point INTEGER NOT NULL,
                CONSTRAINT player_stat_bet_pk PRIMARY KEY (player_name, match_id, stat_type),
                CONSTRAINT player_stat_bet_match_fk FOREIGN KEY (match_id)
                    REFERENCES match(match_id)
                    ON DELETE CASCADE,
                CONSTRAINT player_stat_bet_player_fk FOREIGN KEY (player_name)
                    REFERENCES player(player_name)
                    ON DELETE CASCADE
            );
            """
            cur.execute(SQL)
            conn.commit()


def CREATE_USER_PREDICT_STAT_TABLE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            SQL = """
            CREATE TABLE IF NOT EXISTS user_predict_stat (
                uid TEXT NOT NULL,
                player_name TEXT NOT NULL,
                match_id INTEGER NOT NULL,
                stat_type TEXT NOT NULL CHECK (stat_type IN ('得分', '籃板', '抄截')),
                predicted_outcome TEXT NOT NULL CHECK (predicted_outcome IN ('大盤', '小盤')),
                is_correct BOOLEAN,
                CONSTRAINT user_predict_stat_pk PRIMARY KEY (uid, player_name, match_id, stat_type),
                CONSTRAINT user_predict_stat_user_fk FOREIGN KEY (uid)
                    REFERENCES users(uid)
                    ON DELETE CASCADE,
                CONSTRAINT user_predict_stat_stat_fk FOREIGN KEY (player_name, match_id, stat_type)
                    REFERENCES player_stat_bet(player_name, match_id, stat_type)
                    ON DELETE CASCADE
            );
            """
            cur.execute(SQL)
            conn.commit()


def DROP_DATABASE():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS player CASCADE;")
            cur.execute("DROP TABLE IF EXISTS user_predict_stat CASCADE;")
            cur.execute("DROP TABLE IF EXISTS player_stat_bet CASCADE;")
            cur.execute("DROP TABLE IF EXISTS user_predict_match CASCADE;")
            cur.execute("DROP TABLE IF EXISTS match CASCADE;")
            cur.execute("DROP TABLE IF EXISTS counter CASCADE;")
            cur.execute("DROP TABLE IF EXISTS team CASCADE;")
            cur.execute("DROP TABLE IF EXISTS users CASCADE;")
            conn.commit()


def INSERT_PLAYER():
    output = {}
    response = requests.get("https://www.foxsports.com/nba/teams")
    soup = BeautifulSoup(response.text, "html.parser")
    teams = soup.find("div", class_="entity-list-group")
    teamURLs = teams.find_all("a")
    for teamURL in teamURLs:
        url = f"https://www.foxsports.com{teamURL.get('href')}-roster"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        playerGroups = soup.find_all("tbody", class_="row-data lh-1pt43 fs-14")
        for playerGroup in playerGroups[:-1]:
            playerContainers = playerGroup.find_all("tr")
            for playerContainer in playerContainers:
                playerInfo = playerContainer.find(
                    "td", class_="cell-entity fs-18 lh-1pt67"
                )
                playerPageUrl = (
                    f"https://www.foxsports.com{playerInfo.find('a').get('href')}"
                )
                playerName = playerInfo.find("h3").text.strip()
                print(playerName)
                output[playerName] = playerPageUrl

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for playerName, playerPageUrl in output.items():
                SQL = """
                INSERT INTO player (player_name, player_page_url)
                VALUES (%s, %s)
                ON CONFLICT (player_name)
                DO UPDATE SET player_page_url = EXCLUDED.player_page_url
                """
                cur.execute(SQL, (playerName, playerPageUrl))
        conn.commit()


def INSERT_NBA_TEAM():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for teamName in NBA_ABBR_ENG_TO_ABBR_CN.values():
                cur.execute(
                    "INSERT INTO team (team_name) VALUES (%s) ON CONFLICT (team_name) DO NOTHING;",
                    (teamName,),
                )
            conn.commit()


DROP_DATABASE()
CREATE_USER_TABLE()
CREATE_TEAM_TABLE()
CREATE_COUNTER_TABLE()
CREATE_MATCH_TABLE()
CREATE_USER_PREDICT_MATCH_TABLE()
CREATE_PLAYER_TABLE()
CREATE_PLAYER_STAT_BET_TABLE()
CREATE_USER_PREDICT_STAT_TABLE()
INSERT_NBA_TEAM()
INSERT_PLAYER()
