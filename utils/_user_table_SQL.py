SQL_SELECT_USER_IS_ADMIN = """
SELECT is_admin FROM users WHERE uid = %s
"""

SQL_UPDATE_USER_WEEK_GOAT_COUNT = """
UPDATE users
SET week_goat_count = week_goat_count + 1
WHERE week_points = (
    SELECT MAX(week_points) FROM users
);
"""

SQL_UPDATE_USER_MONTH_GOAT_COUNT = """
UPDATE users
SET month_goat_count = month_goat_count + 1
WHERE month_points = (
    SELECT MAX(month_points) FROM users
);
"""

SQL_UPDATE_USER_GOAT_COUNT = {
    "week_points": SQL_UPDATE_USER_WEEK_GOAT_COUNT,
    "month_points": SQL_UPDATE_USER_MONTH_GOAT_COUNT,
}


SQL_DELETE_ACTIVE_MATCH = """
DELETE FROM match WHERE is_active = TRUE
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
    (game_date, team1_name, team2_name, team1_point, team2_point,
     espn_event_id, tipoff_utc)
VALUES (%s, %s, %s, %s, %s, %s, %s)
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

SQL_SELECT_USER_PREDICT_MATCH_COMPARE = """
SELECT team1_name, team2_name, predicted_team, team1_point, team2_point
FROM match
LEFT OUTER JOIN user_predict_match as upm
    ON 
        upm.uid = (SELECT uid FROM users WHERE name = %s)
        AND upm.match_id = match.match_id
WHERE match.is_active = TRUE
ORDER BY match.match_id 
"""

SQL_SELECT_USER_PREDICT_STAT_COMPARE = """
SELECT psb.player_name, psb.stat_type, predicted_outcome, psb.stat_target, psb.over_point, psb.under_point
FROM player_stat_bet AS psb
INNER JOIN match
    ON psb.match_id = match.match_id 
LEFT OUTER JOIN user_predict_stat AS ups
    ON 
        ups.uid = (SELECT uid FROM users WHERE name = %s) 
        AND ups.match_id = match.match_id
        AND ups.player_name = psb.player_name 
        AND ups.stat_type = psb.stat_type
WHERE match.is_active = TRUE
ORDER BY stat_type, player_name
"""

SQL_SELECT_PLAYER_STAT_BET = """
SELECT psb.match_id, psb.player_name, chinese_name, stat_type
FROM player_stat_bet AS psb
INNER JOIN match
    ON psb.match_id = match.match_id
INNER JOIN player
    ON psb.player_name = player.player_name
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

SQL_SELECT_ACTIVE_MATCH = """
SELECT team1_name, team2_name, team1_point, team2_point,
    (SELECT team_standing FROM team WHERE team_name = team1_name),
    (SELECT team_standing FROM team WHERE team_name = team2_name)
FROM match
WHERE is_active = TRUE
"""

SQL_SELECT_ACTIVE_PLAYER_STAT_BET = """
SELECT player_name, stat_type, stat_target, over_point, under_point
FROM player_stat_bet AS psb
INNER JOIN match
    ON match.match_id = psb.match_id
WHERE match.is_active = TRUE
"""


SQL_INSERT_USER_WEEK_POINT_HISTORY = """
INSERT INTO user_point_history (uid, point_type, point_value, period)
SELECT 
    uid, 'week_points', week_points, TO_CHAR(CURRENT_DATE, 'IYYY-"W"IW')
FROM users
ON CONFLICT (uid, point_type, period)
DO UPDATE SET 
    point_value = user_point_history.point_value + EXCLUDED.point_value;
"""

SQL_INSERT_USER_MONTH_POINT_HISTORY = """
INSERT INTO user_point_history (uid, point_type, point_value, period)
SELECT 
    uid, 'month_points', month_points, TO_CHAR(CURRENT_DATE, 'YYYY-Mon')
FROM users
ON CONFLICT (uid, point_type, period)
DO NOTHING;
"""

SQL_INSERT_USER_SEASON_POINT_HISTORY = """
INSERT INTO user_point_history (uid, point_type, point_value, period)
SELECT uid, 'season_points', season_points, 
    (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::text || '-' || RIGHT(EXTRACT(YEAR FROM CURRENT_DATE)::text, 2)
FROM users
ON CONFLICT (uid, point_type, period)
DO NOTHING;
"""

SQL_INSERT_USER_POINT_HISTORY = {
    "week_points": SQL_INSERT_USER_WEEK_POINT_HISTORY,
    "month_points": SQL_INSERT_USER_MONTH_POINT_HISTORY,
    "season_points": SQL_INSERT_USER_SEASON_POINT_HISTORY,
}

SQL_CALL_CALCULATE_DAILY_POINT_PROC = """
CALL calculate_daily_points_proc()
"""

SQL_SELECT_PLAYER_LINK = """
SELECT player_page_url FROM player WHERE player_name = %s
"""

SQL_SELECT_IMAGE_LINK = """
SELECT link FROM ImageLink WHERE category = %s
"""

SQL_INSERT_BOXSCORE = """
INSERT INTO match_of_the_day (boxscore_url)
VALUES (%s)
"""

SQL_SELECT_USER_SETTLE_POINTS = """
SELECT name, week_points, day_points, day_match_points, day_stat_points 
FROM users 
ORDER BY week_points DESC
"""

SQL_SELECT_ACTIVE_MATCHES = """
SELECT team1_name, team1_score, team2_score, team2_name, team1_point, team2_point, match_id
FROM match
WHERE is_active = TRUE
"""

SQL_SELECT_ACTIVE_STATS = """
SELECT player_name, stat_type, stat_result, stat_target, over_point, under_point
FROM player_stat_bet
WHERE match_id IN (SELECT match_id FROM match WHERE is_active = TRUE)
  AND stat_result IS NOT NULL
"""

# ---------------------------------------------------------------- 戰報 / 成就

SQL_SELECT_LAST_SETTLED_DATE = """
SELECT MAX(game_date) FROM match WHERE is_active = FALSE
"""

# Points are recomputed from source rather than read from user_point_history,
# because that history only goes back to 2025-12-08 while match data starts in
# October. This mirrors what calculate_daily_points_proc() does.
SQL_SELECT_DAILY_SCORES = """
WITH match_pts AS (
    SELECT upm.uid,
           CASE WHEN upm.is_correct THEN
                CASE WHEN upm.predicted_team = m.team1_name THEN m.team1_point
                     ELSE m.team2_point END
                ELSE 0 END AS pts,
           upm.is_correct
    FROM user_predict_match AS upm
    JOIN match AS m ON m.match_id = upm.match_id
    WHERE m.game_date = %s AND upm.is_correct IS NOT NULL
),
stat_pts AS (
    SELECT ups.uid,
           CASE WHEN ups.is_correct THEN
                CASE WHEN ups.predicted_outcome = '大盤' THEN psb.over_point
                     ELSE psb.under_point END
                ELSE 0 END AS pts,
           ups.is_correct
    FROM user_predict_stat AS ups
    JOIN match AS m ON m.match_id = ups.match_id
    JOIN player_stat_bet AS psb
        ON  psb.player_name = ups.player_name
        AND psb.match_id    = ups.match_id
        AND psb.stat_type   = ups.stat_type
    WHERE m.game_date = %s AND ups.is_correct IS NOT NULL
),
combined AS (SELECT * FROM match_pts UNION ALL SELECT * FROM stat_pts)
SELECT u.name,
       SUM(c.pts)                             AS points,
       COUNT(*) FILTER (WHERE c.is_correct)   AS hit,
       COUNT(*)                               AS total
FROM combined AS c
JOIN users AS u ON u.uid = c.uid
GROUP BY u.name
ORDER BY points DESC, hit DESC
"""

SQL_SELECT_HEARTBREAK_GAME = """
SELECT m.team1_name, m.team2_name, m.team1_score, m.team2_score,
       COUNT(*) FILTER (WHERE NOT upm.is_correct) AS wrong,
       COUNT(*)                                   AS total
FROM match AS m
JOIN user_predict_match AS upm ON upm.match_id = m.match_id
WHERE m.game_date = %s AND upm.is_correct IS NOT NULL
GROUP BY m.match_id, m.team1_name, m.team2_name, m.team1_score, m.team2_score
HAVING COUNT(*) FILTER (WHERE NOT upm.is_correct) > 0
ORDER BY wrong DESC, total DESC
LIMIT 1
"""

SQL_SELECT_WIPEOUT_GAMES = """
SELECT m.team1_name, m.team2_name, m.team1_score, m.team2_score,
       MIN(upm.predicted_team) AS picked, COUNT(*) AS n
FROM match AS m
JOIN user_predict_match AS upm ON upm.match_id = m.match_id
WHERE m.game_date = %s AND upm.is_correct IS NOT NULL
GROUP BY m.match_id, m.team1_name, m.team2_name, m.team1_score, m.team2_score
HAVING COUNT(DISTINCT upm.predicted_team) = 1
   AND COUNT(*) FILTER (WHERE upm.is_correct) = 0
   AND COUNT(*) > 1
ORDER BY n DESC
"""

SQL_SELECT_LONE_CORRECT = """
SELECT u.name, m.team1_name, m.team2_name, upm.predicted_team,
       CASE WHEN upm.predicted_team = m.team1_name THEN m.team1_point
            ELSE m.team2_point END AS pts
FROM match AS m
JOIN user_predict_match AS upm ON upm.match_id = m.match_id
JOIN users AS u ON u.uid = upm.uid
WHERE m.game_date = %s
  AND upm.is_correct
  AND (SELECT COUNT(*) FROM user_predict_match AS x
       WHERE x.match_id = m.match_id AND x.is_correct) = 1
  AND (SELECT COUNT(*) FROM user_predict_match AS x
       WHERE x.match_id = m.match_id AND x.is_correct IS NOT NULL) > 2
ORDER BY pts DESC
LIMIT 3
"""


SQL_SELECT_PERFECT_DAYS = """
SELECT COUNT(*) FILTER (WHERE allRight), COUNT(*) FILTER (WHERE allWrong)
FROM (
    SELECT bool_and(upm.is_correct)     AS allRight,
           bool_and(NOT upm.is_correct) AS allWrong
    FROM user_predict_match AS upm
    JOIN match AS m ON m.match_id = upm.match_id
    WHERE upm.uid = %s AND upm.is_correct IS NOT NULL
    GROUP BY m.game_date
    HAVING COUNT(*) >= 5
) AS days
"""

# Lone correct pick on a game at least 8 people graded - the contrarian badge.
SQL_SELECT_AGAINST_THE_WORLD = """
SELECT COUNT(*)
FROM match AS m
JOIN user_predict_match AS upm ON upm.match_id = m.match_id
WHERE upm.uid = %s
  AND upm.is_correct
  AND (SELECT COUNT(*) FROM user_predict_match AS x
       WHERE x.match_id = m.match_id AND x.is_correct) = 1
  AND (SELECT COUNT(*) FROM user_predict_match AS x
       WHERE x.match_id = m.match_id AND x.is_correct IS NOT NULL) >= 8
"""

SQL_SELECT_UNDERDOG_HITS = """
SELECT COUNT(*),
       COALESCE(MAX(CASE WHEN upm.predicted_team = m.team1_name
                         THEN m.team1_point ELSE m.team2_point END), 0)
FROM user_predict_match AS upm
JOIN match AS m ON m.match_id = upm.match_id
WHERE upm.uid = %s
  AND upm.is_correct
  AND CASE WHEN upm.predicted_team = m.team1_name
           THEN m.team1_point ELSE m.team2_point END >= 40
"""

SQL_SELECT_LONGEST_STREAK = """
WITH graded AS (
    SELECT upm.is_correct,
           ROW_NUMBER() OVER (ORDER BY m.game_date, upm.match_id) AS seq
    FROM user_predict_match AS upm
    JOIN match AS m ON m.match_id = upm.match_id
    WHERE upm.uid = %s AND upm.is_correct IS NOT NULL
),
islands AS (
    SELECT is_correct,
           seq - ROW_NUMBER() OVER (PARTITION BY is_correct ORDER BY seq) AS grp
    FROM graded
)
SELECT COALESCE(MAX(runLength), 0) FROM (
    SELECT COUNT(*) AS runLength FROM islands WHERE is_correct GROUP BY grp
) AS runs
"""

SQL_SELECT_LOYAL_TEAM = """
SELECT team_name, all_time_correct_count + all_time_wrong_count AS picked
FROM counter
WHERE uid = %s
ORDER BY picked DESC
LIMIT 1
"""


SQL_SELECT_ACTIVE_STAT_MATCHES = """
SELECT DISTINCT m.match_id, m.game_date, m.team1_name, m.team2_name, m.espn_event_id
FROM match AS m
JOIN player_stat_bet AS psb ON psb.match_id = m.match_id
WHERE m.is_active = TRUE
"""

SQL_UPDATE_MATCH_ESPN_EVENT_ID = """
UPDATE match SET espn_event_id = %s WHERE match_id = %s
"""

SQL_SELECT_STAT_BETS_FOR_MATCH = """
SELECT player_name, stat_type FROM player_stat_bet WHERE match_id = %s
"""


# ---- date-scoped badge detection, used to announce 成就 inside 戰報 ----

SQL_SELECT_DAY_PERFECT = """
SELECT upm.uid,
       bool_and(upm.is_correct)     AS allRight,
       bool_and(NOT upm.is_correct) AS allWrong,
       COUNT(*)                     AS picks
FROM user_predict_match AS upm
JOIN match AS m ON m.match_id = upm.match_id
WHERE m.game_date = %s AND upm.is_correct IS NOT NULL
GROUP BY upm.uid
HAVING COUNT(*) >= 5
"""

SQL_SELECT_DAY_AGAINST_THE_WORLD = """
SELECT upm.uid, m.team1_name, m.team2_name, upm.predicted_team
FROM match AS m
JOIN user_predict_match AS upm ON upm.match_id = m.match_id
WHERE m.game_date = %s
  AND upm.is_correct
  AND (SELECT COUNT(*) FROM user_predict_match AS x
       WHERE x.match_id = m.match_id AND x.is_correct) = 1
  AND (SELECT COUNT(*) FROM user_predict_match AS x
       WHERE x.match_id = m.match_id AND x.is_correct IS NOT NULL) >= 8
"""

SQL_SELECT_DAY_UNDERDOG = """
SELECT upm.uid, upm.predicted_team,
       CASE WHEN upm.predicted_team = m.team1_name THEN m.team1_point
            ELSE m.team2_point END AS pts
FROM user_predict_match AS upm
JOIN match AS m ON m.match_id = upm.match_id
WHERE m.game_date = %s
  AND upm.is_correct
  AND CASE WHEN upm.predicted_team = m.team1_name THEN m.team1_point
           ELSE m.team2_point END >= 40
"""

# Win runs that are still alive at the end of the given date, with the length
# they had before that date, so the caller can see which milestones were crossed.
SQL_SELECT_DAY_STREAKS = """
WITH graded AS (
    SELECT upm.uid, upm.is_correct, m.game_date,
           ROW_NUMBER() OVER (PARTITION BY upm.uid
                              ORDER BY m.game_date, upm.match_id) AS seq
    FROM user_predict_match AS upm
    JOIN match AS m ON m.match_id = upm.match_id
    WHERE upm.is_correct IS NOT NULL AND m.game_date <= %s
),
islands AS (
    SELECT uid, is_correct, game_date, seq,
           seq - ROW_NUMBER() OVER (PARTITION BY uid, is_correct ORDER BY seq) AS grp
    FROM graded
),
runs AS (
    SELECT uid, COUNT(*) AS runLength, MAX(game_date) AS endedOn,
           COUNT(*) FILTER (WHERE game_date = %s) AS earnedToday
    FROM islands
    WHERE is_correct
    GROUP BY uid, grp
)
SELECT uid, runLength, runLength - earnedToday AS lengthBefore
FROM runs
WHERE endedOn = %s AND earnedToday > 0
"""

SQL_INSERT_ACHIEVEMENT = """
INSERT INTO user_achievement (uid, achievement_key, earned_date, detail)
VALUES (%s, %s, %s, %s)
ON CONFLICT (uid, achievement_key, earned_date) DO NOTHING
"""
