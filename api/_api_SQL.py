SQL_SELECT_USER_DAY_POINT = """
SELECT name, picture_url, day_points 
FROM users
ORDER BY day_points DESC
"""

SQL_SELECT_USER_WEEK_POINT = """
SELECT name, picture_url, week_points 
FROM users
ORDER BY week_points DESC
"""

SQL_SELECT_USER_MONTH_POINT = """
SELECT name, picture_url, month_points 
FROM users
ORDER BY month_points DESC
"""

SQL_SELECT_USER_SEASON_POINT = """
SELECT name, picture_url, season_points 
FROM users
ORDER BY season_points DESC
"""

SQL_SELECT_USER_ALL_TIME_POINT = """
SELECT name, picture_url, all_time_points 
FROM users
ORDER BY all_time_points DESC
"""

SQL_SELECT_USER_TYPE_POINT = {
    "day_points": SQL_SELECT_USER_DAY_POINT,
    "week_points": SQL_SELECT_USER_WEEK_POINT,
    "month_points": SQL_SELECT_USER_MONTH_POINT,
    "season_points": SQL_SELECT_USER_SEASON_POINT,
    "all_time_points": SQL_SELECT_USER_ALL_TIME_POINT,
}

SQL_SELECT_MATCH_TODAY = """
    SELECT team1_name, team2_name, team1_score, team2_score, team1_point, team2_point
    FROM match
    WHERE is_active = TRUE
    ORDER BY match_id
"""

SQL_SELECT_TEAM_LOGO_AND_STANDING = """
    SELECT team_logo, team_standing
    FROM team
    WHERE team_name = %s
"""
