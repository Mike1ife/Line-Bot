SQL_USER_IS_ADMIN = """
SELECT is_admin FROM users WHERE uid = %s
"""

SQL_SELECT_DAY_POINT = """
SELECT name, day_points FROM users ORDER BY created_at
"""

SQL_SELECT_WEEK_POINT = """
SELECT name, week_points FROM users ORDER BY created_at
"""

SQL_SELECT_MONTH_POINT = """
SELECT name, month_points FROM users ORDER BY created_at
"""

SQL_SELECT_SEASON_POINT = """
SELECT name, season_points FROM users ORDER BY created_at
"""

SQL_SELECT_ALL_TIME_POINT = """
SELECT name, all_time_points FROM users ORDER BY created_at
"""

SQL_SELECT_TYPE_POINT = {
    "day_points": SQL_SELECT_DAY_POINT,
    "week_points": SQL_SELECT_WEEK_POINT,
    "month_points": SQL_SELECT_MONTH_POINT,
    "season_points": SQL_SELECT_SEASON_POINT,
    "all_time_points": SQL_SELECT_ALL_TIME_POINT,
}

SQL_INSERT_MATCH = """
INSERT INTO match 
    (game_date, team1_name, team2_name, team1_point, team2_point)
VALUES (%s, %s, %s, %s, %s)
"""

SQL_UPDATE_TEAM_STANDING = """
UPDATE team SET team_standing = %s WHERE team_name = %s
"""

SQL_SELECT_MATCH_ID = """
SELECT match_id
FROM match
WHERE 
    game_date = %s 
    AND (
        (team1_name = %s AND team2_name = %s)
        OR
        (team2_name = %s AND team1_name = %s)
    )
"""

SQL_INSERT_PLAYER_STAT_BET = """
INSERT INTO player_stat_bet
    (player_name, match_id, stat_type, stat_target, over_point, under_point)
VALUES (%s, %s, %s, %s, %s, %s)
"""

SQL_INSERT_USER_PREDICT_MATCH = """
INSERT INTO user_predict_match
    (uid, match_id, predicted_team)
VALUES (%s, %s, %s)
ON CONFLICT 
    (uid, match_id)
    DO NOTHING
"""

SQL_INSERT_USER_PREDICT_STAT = """
INSERT INTO user_predict_stat
    (uid, player_name, match_id, stat_type, predicted_outcome)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT 
    (uid, player_name, match_id, stat_type) 
    DO NOTHING
"""

SQL_SELECT_UID = """
SELECT uid FROM users WHERE name = %s
"""

SQL_ADD_DAY_POINT = """
UPDATE users SET day_points = day_points + %s WHERE uid = %s
"""

SQL_WRITE_DAY_POINT = """
UPDATE users SET day_points = %s WHERE uid = %s
"""

SQL_ADD_WEEK_POINT = """
UPDATE users SET week_points = week_points + %s WHERE uid = %s
"""

SQL_WRITE_WEEK_POINT = """
UPDATE users SET week_points = %s WHERE uid = %s
"""

SQL_ADD_MONTH_POINT = """
UPDATE users SET month_points = month_points + %s WHERE uid = %s
"""

SQL_WRITE_MONTH_POINT = """
UPDATE users SET month_points = %s WHERE uid = %s
"""

SQL_ADD_SEASON_POINT = """
UPDATE users SET season_points = season_points + %s WHERE uid = %s
"""

SQL_WRITE_SEASON_POINT = """
UPDATE users SET season_points = %s WHERE uid = %s
"""

SQL_ADD_ALL_TIME_POINT = """
UPDATE users SET all_time_points = all_time_points + %s WHERE uid = %s
"""

SQL_WRITE_ALL_TIME_POINT = """
UPDATE users SET all_time_points = %s WHERE uid = %s
"""

SQL_ADD_TYPE_POINT = {
    "day_points": SQL_ADD_DAY_POINT,
    "week_points": SQL_ADD_WEEK_POINT,
    "month_points": SQL_ADD_MONTH_POINT,
    "season_points": SQL_ADD_SEASON_POINT,
    "all_time_points": SQL_ADD_ALL_TIME_POINT,
}

SQL_WRITE_TYPE_POINT = {
    "day_points": SQL_WRITE_DAY_POINT,
    "week_points": SQL_WRITE_WEEK_POINT,
    "month_points": SQL_WRITE_MONTH_POINT,
    "season_points": SQL_WRITE_SEASON_POINT,
    "all_time_points": SQL_WRITE_SEASON_POINT,
}

SQL_UPDATE_TYPE_POINT = {"a": SQL_ADD_TYPE_POINT, "w": SQL_WRITE_TYPE_POINT}


SQL_SELECT_SEASON_CORRECT_COUNTER = """
SELECT team_name, season_correct_count
FROM counter
WHERE uid = %s
ORDER BY season_correct_count DESC
"""

SQL_SELECT_SEASON_WRONG_COUNTER = """
SELECT team_name, season_wrong_count
FROM counter
WHERE uid = %s
ORDER BY season_wrong_count DESC
"""

SQL_SELECT_SEASON_BOTH_COUNTER = """
SELECT team_name, season_correct_count, season_wrong_count
FROM counter 
WHERE uid = %s
"""

SQL_RESET_SEASON_BOTH_COUNTER = """
UPDATE counter 
SET season_correct_count = 0, season_wrong_count = 0
"""

SQL_SELECT_USER = """
SELECT uid, name FROM users ORDER BY created_at
"""

SQL_SELECT_USER_WITH_PICTURE = """
SELECT uid, name, picture_url FROM users ORDER BY created_at
"""

SQL_INSERT_USER = """
INSERT INTO users (name, uid, picture_url)
VALUES (%s, %s, %s)
ON CONFLICT (uid)
DO UPDATE
SET
    name = EXCLUDED.name,
    picture_url = EXCLUDED.picture_url
"""


SQL_INSERT_COUNTER = """
INSERT INTO counter (uid, team_name)
SELECT %s, team_name FROM team
ON CONFLICT (uid, team_name) DO NOTHING 
"""

SQL_SELECT_USER_PREDICT_MATCH1 = """
SELECT team1_name, team2_name, predicted_team
FROM match
LEFT OUTER JOIN user_predict_match as upm
    ON 
        upm.uid = (SELECT uid FROM users WHERE name = %s)
        AND upm.match_id = match.match_id
WHERE match.is_active = TRUE
ORDER BY match.match_id 
"""

SQL_SELECT_USER_PREDICT_STAT1 = """
SELECT psb.player_name, psb.stat_type, predicted_outcome
FROM player_stat_bet AS psb
INNER JOIN match
    ON 
        psb.match_id = match.match_id 
LEFT OUTER JOIN user_predict_stat AS ups
    ON 
        ups.uid = (SELECT uid FROM users WHERE name = %s) 
        AND ups.match_id = match.match_id
        AND ups.player_name = psb.player_name 
        AND ups.stat_type = psb.stat_type
WHERE match.is_active = TRUE
ORDER BY stat_type, player_name
"""

SQL_SELECT_USER_PREDICT_MATCH2 = """
SELECT predicted_team
FROM user_predict_match AS upm
INNER JOIN match
    ON upm.match_id = match.match_id
WHERE 
    upm.uid = %s 
    AND match.is_active = TRUE           
ORDER BY match.match_id 
"""

SQL_SELECT_USER_PREDICT_STAT2 = """
SELECT player_name, stat_type, predicted_outcome
FROM user_predict_stat AS ups
INNER JOIN match
    ON ups.match_id = match.match_id
WHERE 
    ups.uid = %s 
    AND match.is_active = TRUE
ORDER BY stat_type, player_name
"""

SQL_SELECT_PLAYER_STAT_BET = """
SELECT psb.match_id, player_name, stat_type
FROM player_stat_bet AS psb
INNER JOIN match
    ON psb.match_id = match.match_id
WHERE is_active = TRUE
"""

SQL_UPDATE_PLAYER_STAT_BET = """
UPDATE player_stat_bet
SET stat_result = %s
WHERE
    player_name = %s 
    AND match_id = %s 
    AND stat_type = %s
"""

SQL_UPDATE_MATCH_SCORE = """
UPDATE match
SET
    team1_score = CASE
        WHEN team1_name = %s THEN %s
        ELSE %s
    END,
    team2_score = CASE
        WHEN team2_name = %s THEN %s
        ELSE %s
    END
WHERE 
    is_active = TRUE
    AND (
        (team1_name = %s AND team2_name = %s)
        OR (team1_name = %s AND team2_name = %s)
    )
"""

SQL_CALL_CALCULATE_DAILY_POINT_PROC = """
CALL calculate_daily_points_proc()
"""

SQL_SELECT_PLAYER_LINK = """
SELECT player_page_url FROM player WHERE player_name = %s
"""

SQL_SELECT_IMAGE_LINK = """
SELECT link FROM ImageLink WHERE category = %s
"""
