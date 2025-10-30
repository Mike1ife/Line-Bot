import re
import requests
import psycopg
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import DATABASE_URL
from utils._user_table_SQL import *
from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN, NBA_SIMP_CN_TO_TRAD_CN

STAT_INDEX = {"得分": 3, "籃板": 5, "抄截": 7}
PREDICTION_INDEX = 38

_conn = None


def _get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DATABASE_URL)
    return _conn


def user_is_admin(userUID: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_USER_IS_ADMIN, (userUID,))
        result = cur.fetchone()
        return result[0] if result else False


def get_type_points(rankType: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_TYPE_POINT[rankType])
        return cur.fetchall()


def insert_match(matchList: list):
    # matchList = [(gameDate: str, team1Name: str, team2Name: str, team1Point: int, team2Point: int)]
    conn = _get_connection()
    with conn.cursor() as cur:
        for gameDate, team1Name, team2Name, team1Odd, team2Odd in matchList:
            cur.execute(
                SQL_INSERT_MATCH,
                (gameDate, team1Name, team2Name, team1Odd, team2Odd),
            )
    conn.commit()


def insert_player_stat_bet(playerStatBetList: list):
    # playerStatBetList =
    # [(playerName: str, gameDate: str, team1Name: str, team2Name: str statType: str, statTarget: float, overPoint: int, underPoint: int)]
    conn = _get_connection()
    with conn.cursor() as cur:
        for (
            playerName,
            gameDate,
            team1Name,
            team2Name,
            statType,
            statTarget,
            overPoint,
            underPoint,
        ) in playerStatBetList:
            cur.execute(
                SQL_SELECT_MATCH_ID,
                (
                    gameDate,
                    team1Name,
                    team2Name,
                    team1Name,
                    team2Name,
                ),
            )
            matchID = cur.fetchone()[0]
            cur.execute(
                SQL_INSERT_PLAYER_STAT_BET,
                (playerName, matchID, statType, statTarget, overPoint, underPoint),
            )
    conn.commit()


def insert_user_predict_match(
    userUID: str,
    userPrediction: str,
    team1Name: str,
    team2Name: str,
    gameDate: str,
):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(
            SQL_SELECT_MATCH_ID, (gameDate, team1Name, team2Name, team1Name, team2Name)
        )
        matchID = cur.fetchone()[0]
        cur.execute(
            SQL_INSERT_USER_PREDICT_MATCH,
            (userUID, matchID, userPrediction),
        )
        returnState = "CONFLICT" if cur.rowcount == 0 else "INSERT"
    conn.commit()
    return returnState


def insert_user_predict_stat(
    userUID: str,
    userPrediction: str,
    playerName: str,
    statType: str,
    team1Name: str,
    team2Name: str,
    gameDate: str,
):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(
            SQL_SELECT_MATCH_ID, (gameDate, team1Name, team2Name, team1Name, team2Name)
        )
        matchID = cur.fetchone()[0]
        cur.execute(
            SQL_INSERT_USER_PREDICT_STAT,
            (userUID, playerName, matchID, statType, userPrediction),
        )
        returnState = "CONFLICT" if cur.rowcount == 0 else "INSERT"
    conn.commit()
    return returnState


def update_type_point(updateRankType: list, updateStrategy: list, updateMap: dict):
    # updateRankType = [rankType1, rankType1, ...]
    # updateStrategy = [strategy1, strategy2, ...] ('a' / 'w')
    # updateMap[userName] = [value1, value2, ...]
    conn = _get_connection()
    with conn.cursor() as cur:
        for userName in updateMap:
            cur.execute(SQL_SELECT_UID, (userName,))
            userUID = cur.fetchone()[0]
            for rankType, strategy, value in zip(
                updateRankType, updateStrategy, updateMap[userName]
            ):
                cur.execute(SQL_UPDATE_TYPE_POINT[strategy][rankType], (value, userUID))
    conn.commit()


def reset_nba_prediction():
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_DEACTIVE_MATCH)
        cur.execute(SQL_RESET_DAY_POINT)
    conn.commit()


def _pre_settle_week_points():
    UTCnow = datetime.now(timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    weekday = TWnow.weekday()  # 0-index, i.e. Monday=0, Sunday=6
    if weekday == 0:
        return
    userDayPoints = get_type_points(rankType="day_points")
    userWeekPoints = get_type_points(rankType="week_points")
    userPoints = []
    for i in range(len(userDayPoints)):
        name, dayPoint = userDayPoints[i]
        weekPoint = userWeekPoints[i][1]
        userPoints.append([name, dayPoint, weekPoint - dayPoint])
    if all(prevPoint == 0 for _, _, prevPoint in userPoints):
        # No week point
        return
    # weekPoint = prevPoint + dayPoint
    userPoints.sort(key=lambda x: x[2], reverse=True)

    monthPoint = 100
    currBestPoint = 0
    reduction = 0
    partial = weekday / 7
    updateMap = {}
    for name, dayPoint, prevPoint in userPoints:
        if prevPoint != currBestPoint:
            monthPoint -= reduction
            reduction = 0
        updateMap[name] = [dayPoint, int(monthPoint * partial)]
        currBestPoint = prevPoint
        reduction += 10

    # write dayPoint to week_points
    # add monthPoint to month_points
    update_type_point(
        updateRankType=["week_points", "month_points"],
        updateStrategy=["w", "a"],
        updateMap=updateMap,
    )


def get_type_best(rankType: str, nextRankType: str):
    if rankType == "month_points":
        _pre_settle_week_points()

    userPoints = get_type_points(rankType=rankType)
    userPoints.sort(key=lambda x: x[1], reverse=True)

    if all(user[1] == 0 for user in userPoints):
        return []

    nextRankPoint = 100
    rankBestPoint = 0
    currBestPoint = 0
    reduction = 0
    rankBest = []
    updateMap = {}
    for name, point in userPoints:
        if point >= rankBestPoint:
            rankBestPoint = point
            rankBest.append((name, point))
        elif point != currBestPoint:
            nextRankPoint -= reduction
            reduction = 0

        updateMap[name] = [0, nextRankPoint]
        currBestPoint = point
        reduction += 10

    # write 0 to rankType
    # add nextRankPoint to nextRankType
    update_type_point(
        updateRankType=[rankType, nextRankType],
        updateStrategy=["w", "a"],
        updateMap=updateMap,
    )
    return rankBest


def get_user_season_correct(userName: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_UID, (userName,))
        userUID = cur.fetchone()[0]
        cur.execute(SQL_SELECT_SEASON_CORRECT_COUNTER, (userUID,))
        correctList = cur.fetchall()
        teamList, seasonCorrect = zip(*correctList)
        return teamList, seasonCorrect


def get_user_season_wrong(userName: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_UID, (userName,))
        userUID = cur.fetchone()[0]
        cur.execute(SQL_SELECT_SEASON_WRONG_COUNTER, (userUID,))
        wrongList = cur.fetchall()
        teamList, seasonWrong = zip(*wrongList)
        return teamList, seasonWrong


def settle_season_correct_wrong():
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT uid FROM users")
        userUIDList = [row[0] for row in cur.fetchall()]

        correctList = {}
        wrongList = {}
        for userUID in userUIDList:
            cur.execute(SQL_SELECT_SEASON_BOTH_COUNTER, (userUID,))
            countList = cur.fetchall()
            for teamName, correctCount, wrongCount in countList:
                correctList[teamName] = correctList.get(teamName, 0) + correctCount
                wrongList[teamName] = wrongList.get(teamName, 0) + wrongCount
        cur.execute(SQL_RESET_SEASON_BOTH_COUNTER)
        conn.commit()

        mostCorrectTeam = max(correctList, key=correctList.get)
        mostWrongTeam = max(wrongList, key=wrongList.get)
        return f"{mostCorrectTeam}是信仰的GOAT\n{mostWrongTeam}是傻鳥的GOAT"


def user_exist(userUID: str, userName: str, pictureUrl: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER_WITH_PICTURE)
        return (userUID, userName, pictureUrl) in cur.fetchall()


def add_user(userUID: str, userName: str, pictureUrl: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        if user_exist(userUID=userUID, userName=userName, pictureUrl=pictureUrl):
            return f"{userName} 已經註冊了"
        cur.execute(SQL_INSERT_USER, (userName, userUID, pictureUrl))
        cur.execute(SQL_INSERT_COUNTER, (userUID,))

    conn.commit()
    return f"{userName} 註冊成功"


def check_user_prediction(userName: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER_PREDICT_MATCH1, (userName,))
        userPredictMatchList = cur.fetchall()

        userNotPredictList = []
        for team1Name, team2Name, userPredictMatch in userPredictMatchList:
            if not userPredictMatch:
                userNotPredictList.append(f"{team1Name} - {team2Name}")

        cur.execute(SQL_SELECT_USER_PREDICT_STAT1, (userName,))
        userPredictStatList = cur.fetchall()

        for playerName, statType, userPredictStat in userPredictStatList:
            if not userPredictStat:
                userNotPredictList.append(f"{playerName} {statType}")

        if not userNotPredictList:
            return "已經完成全部預測"
        if len(userNotPredictList) == len(userPredictMatchList) + len(
            userPredictStatList
        ):
            return "還沒預測任何比賽"
        return "\n".join(["還沒預測:"] + userNotPredictList)


def get_user_prediction(userId: int):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER)
        userUIDList, userNameList = zip(*cur.fetchall())
        userIdToName = {id: userName for id, userName in enumerate(userNameList, 1)}

        if userId not in userIdToName:
            return "\n".join(
                ["使用方式:", "跟盤 id"]
                + [f"{id}. {userName}" for id, userName in userIdToName.items()]
            )

        userUID = userUIDList[userId - 1]

        cur.execute(SQL_SELECT_USER_PREDICT_MATCH2, (userUID,))
        predictTeamList = [row[0] for row in cur.fetchall()]

        cur.execute(SQL_SELECT_USER_PREDICT_STAT2, (userUID,))
        predictStatList = [" ".join(row) for row in cur.fetchall()]

        predictList = predictTeamList + predictStatList
        if len(predictList) == 0:
            return f"{userIdToName[userId]}還沒預測任何比賽"
        return "\n".join([f"{userIdToName[userId]}預測的球隊:"] + predictList)


def _remove_common_prefix(s1: str, s2: str):
    # s1 = "Zach LaVine 大盤"
    # s2 = "Zach LaVine 小盤"
    # return "Zach LaVine 大盤 (小盤)"

    if not s1:
        return f"TBD ({s2})"
    if not s2:
        return f"{s1} (TBD)"

    n = min(len(s1), len(s2))
    index = 0  # the index of the first difference
    while index < n and s1[index] == s2[index]:
        index += 1

    if index == 0:  # no common prefix
        return f"{s1} ({s2})"
    # index < n
    # s1 must not be s2's prefix
    # s2 must not be s1's prefix
    return f"{s1} ({s2[index:]})"


def compare_user_prediction(user1Id: int, user2Id: int):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_USER)
        _, userNameList = zip(*cur.fetchall())
        userIdToName = {id: userName for id, userName in enumerate(userNameList, 1)}
        if (
            user1Id not in userIdToName
            or user2Id not in userIdToName
            or user1Id == user2Id
        ):
            return "\n".join(
                ["使用方式:", "比較 id id"]
                + [f"{id}. {userName}" for id, userName in userIdToName.items()]
            )

        user1Name = userNameList[user1Id - 1]
        user2Name = userNameList[user2Id - 1]

        cur.execute(SQL_SELECT_USER_PREDICT_MATCH1, (user1Name,))
        user1PredictMatchList = cur.fetchall()
        cur.execute(SQL_SELECT_USER_PREDICT_MATCH1, (user2Name,))
        user2PredictMatchList = cur.fetchall()

        isTheSame = True
        hasPredict = False
        compareResult = []
        for i in range(len(user1PredictMatchList)):
            user1PredictMatch = user1PredictMatchList[i][2]
            user2PredictMatch = user2PredictMatchList[i][2]
            if not user1PredictMatch and not user2PredictMatch:
                continue
            hasPredict = True
            if user1PredictMatch == user2PredictMatch:
                compareResult.append(user2PredictMatch)
            else:
                isTheSame = False
                compareResult.append(
                    _remove_common_prefix(user1PredictMatch, user2PredictMatch)
                )

        cur.execute(SQL_SELECT_USER_PREDICT_STAT1, (user1Name,))
        user1PredictStatList = cur.fetchall()
        cur.execute(SQL_SELECT_USER_PREDICT_STAT1, (user2Name,))
        user2PredictStatList = cur.fetchall()

        for i in range(len(user1PredictStatList)):
            user1PredictStat = (
                " ".join(user1PredictStatList[i]) if user1PredictStatList[i][2] else ""
            )
            user2PredictStat = (
                " ".join(user2PredictStatList[i]) if user2PredictStatList[i][2] else ""
            )
            if not user1PredictStat and not user2PredictStat:
                continue
            hasPredict = True
            if user1PredictStat == user2PredictStat:
                compareResult.append(user1PredictStat)
            else:
                isTheSame = False
                compareResult.append(
                    _remove_common_prefix(user1PredictStat, user2PredictStat)
                )

        if not hasPredict:
            return (
                f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 都還沒預測任何比賽"
            )
        if isTheSame:
            return f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 的預測相同"
        return "\n".join(
            [f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 的不同預測:"]
            + compareResult
        )


def _get_stat_result(playerName: str, statType: str):
    playerUrl = get_player_url(playerName=playerName)
    playerStatsPageUrl = playerUrl + "-game-log"

    playerStatsPageData = requests.get(playerStatsPageUrl).text
    playerStatsPageSoup = BeautifulSoup(playerStatsPageData, "html.parser")

    statsContainer = playerStatsPageSoup.find("tbody", class_="row-data lh-1pt43 fs-14")
    mostRecentGame = statsContainer.find("tr")
    gameDate = mostRecentGame.find("span", class_="table-result").text.strip()

    statValue = int(
        mostRecentGame.find("td", {"data-index": STAT_INDEX[statType]}).text.strip()
    )
    return statValue, gameDate


def _has_play_today(gameDate: str):
    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    # MM/DD
    month, day = gameDate.split("/")
    gameDateStr = f"{nowTW}-{month}-{day}"
    gameDateStr = "{}-{:0>2}-{:0>2}".format(nowTW.year, int(month), int(day))
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT is_active FROM match WHERE game_date = %s", (gameDateStr,))
        isActiveList = cur.fetchone()
    return isActiveList[0] if isActiveList else False


def settle_daily_stat_result():
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_PLAYER_STAT_BET)
        playerStatBetList = cur.fetchall()
        for matchId, playerName, statType in playerStatBetList:
            statResult, gameDate = _get_stat_result(
                playerName=playerName, statType=statType
            )
            # if _has_play_today(gameDate=gameDate):
            cur.execute(
                SQL_UPDATE_PLAYER_STAT_BET,
                (statResult, playerName, matchId, statType),
            )
    conn.commit()


def settle_daily_match_result(gameResults: dict, playoffsLayout: bool):
    conn = _get_connection()
    with conn.cursor() as cur:
        for team1Name, team2Name in gameResults:
            team1Score, team2Score = gameResults[(team1Name, team2Name)]
            cur.execute(
                SQL_UPDATE_MATCH_RESULT,
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


def calculate_daily_stat_point():
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_RESET_DAY_POINT)
        cur.execute(SQL_UPDATE_USER_PREDICT_STAT_ALL)
        cur.execute(SQL_UPDATE_USER_STAT_POINT)
    conn.commit()


def calculate_daily_match_point():
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_UPDATE_USER_PREDICT_MATCH)
        cur.execute(SQL_UPDATE_USER_MATCH_POINT)
        cur.execute(SQL_UPDATE_CORRECT_COUNTER)
        cur.execute(SQL_UPDATE_WRONG_COUNTER)
        cur.execute(SQL_DEACTIVE_MATCH)
    conn.commit()


def get_player_url(playerName: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_PLAYER_LINK, (playerName,))
        return cur.fetchone()[0]


def get_image_url(imgKey: str):
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT_IMAGE_LINK, (imgKey,))
        return cur.fetchall()
