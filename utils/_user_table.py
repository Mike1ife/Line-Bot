import re
import requests
import psycopg
from bs4 import BeautifulSoup
from config import DATABASE_URL
from utils._user_table_SQL import *
from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN, NBA_SIMP_CN_TO_TRAD_CN
from datetime import datetime, timezone, timedelta

STAT_INDEX = {"得分": 3, "籃板": 5, "抄截": 7}
SQL_SELECT_TYPE_POINT = {
    "day_points": SQL_SELECT_DAY_POINT,
    "week_points": SQL_SELECT_WEEK_POINT,
    "month_points": SQL_SELECT_MONTH_POINT,
    "season_points": SQL_SELECT_SEASON_POINT,
    "all_time_points": SQL_SELECT_ALL_TIME_POINT,
}
PREDICTION_INDEX = 38


def user_is_admin(userUID: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_USER_IS_ADMIN, (userUID,))
            result = cur.fetchone()
            return result[0] if result else False


def get_type_points(rankType: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_TYPE_POINT[rankType])
            return cur.fetchall()


def insert_match(matchList: list):
    # matchList = [(gameDate: str, team1Name: str, team2Name: str, team1Point: int, team2Point: int)]
    with psycopg.connect(DATABASE_URL) as conn:
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
    with psycopg.connect(DATABASE_URL) as conn:
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
                cur.execute(SQL_SELECT_MATCH_ID, (gameDate, team1Name, team2Name))
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
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_MATCH_ID, (gameDate, team1Name, team2Name))
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
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_MATCH_ID, (gameDate, team1Name, team2Name))
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
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for userName in updateMap:
                cur.execute(SQL_SELECT_UID, (userName,))
                userUID = cur.fetchone()[0]
                for rankType, strategy, value in zip(
                    updateRankType, updateStrategy, updateMap[userName]
                ):
                    if strategy == "a":
                        cur.execute(
                            SQL_ADD_TYPE_POINT,
                            (rankType, rankType, value, userUID),
                        )
                    if strategy == "w":
                        cur.execute(
                            SQL_WRITE_TYPE_POINT,
                            (rankType, value, userUID),
                        )

            conn.commit()


def reset_nba_prediction():
    with psycopg.connect(DATABASE_URL) as conn:
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
        print("no week points")
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
        updateColumns=["week_points", "month_points"],
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
        updateColumns=[rankType, nextRankType],
        updateStrategy=["w", "a"],
        updateMap=updateMap,
    )
    return rankBest


def get_user_season_correct(userName: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_UID, (userName,))
            userUID = cur.fetchone()[0]
            cur.execute(SQL_SELECT_SEASON_CORRECT_COUNTER, (userUID,))
            correctList = cur.fetchall()
            teamList, seasonCorrect = zip(*correctList)
            return teamList, seasonCorrect


def get_user_season_wrong(userName: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_UID, (userName,))
            userUID = cur.fetchone()[0]
            cur.execute(SQL_SELECT_SEASON_WRONG_COUNTER, (userUID,))
            wrongList = cur.fetchall()
            teamList, seasonWrong = zip(*wrongList)
            return teamList, seasonWrong


def settle_season_correct_wrong():
    with psycopg.connect(DATABASE_URL) as conn:
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


def user_exist(userUID: str, userName: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_USER)
            return (userUID, userName) in cur.fetchall()


def add_user(userName: str, userUID: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            if user_exist(userUID=userUID, userName=userName):
                return f"{userName} 已經註冊過了"

            cur.execute(SQL_INSERT_USER, (userName, userUID))
            cur.execute(SQL_INSERT_COUNTER, (userUID,))

        conn.commit()
    return f"{userName} 註冊成功"


def check_user_prediction(userName: str):
    with psycopg.connect(DATABASE_URL) as conn:
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
    with psycopg.connect(DATABASE_URL) as conn:
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
    with psycopg.connect(DATABASE_URL) as conn:
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
                    " ".join(user1PredictStatList[i])
                    if user1PredictStatList[i][2]
                    else ""
                )
                user2PredictStat = (
                    " ".join(user2PredictStatList[i])
                    if user2PredictStatList[i][2]
                    else ""
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
                return f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 都還沒預測任何比賽"
            if isTheSame:
                return f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 的預測相同"
            return "\n".join(
                [f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 的不同預測:"]
                + compareResult
            )


def _get_stat_result(playerName: str, statType: str):
    playerUrl = get_player_url(playerName=playerName)
    playerStatsPageUrl = playerUrl + "-stats"

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
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_active FROM match WHERE game_date = %s", (gameDateStr,)
            )
            isActiveList = cur.fetchone()
        return isActiveList[0] if isActiveList else False


def settle_daily_stat_result():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_PLAYER_STAT_BET)
            playerStatBetList = cur.fetchall()
            for matchId, playerName, statType in playerStatBetList:
                statResult, gameDate = _get_stat_result(
                    playerName=playerName, statType=statType
                )
                if _has_play_today(gameDate=gameDate):
                    cur.execute(
                        SQL_UPDATE_PLAYER_STAT_BET,
                        (statResult, playerName, matchId, statType),
                    )
        conn.commit()


def _get_daily_game_results(playoffsLayout: bool):
    data = requests.get("https://www.foxsports.com/nba/scores").text
    soup = BeautifulSoup(data, "html.parser")

    gameResults = {}  # (team1Name, team2Name): (team1Score, team2Score, winner)
    gameContainers = soup.find_all("a", class_="score-chip final")
    for gameContainer in gameContainers:
        teamsInfo = gameContainer.find_all("div", class_="score-team-name abbreviation")
        scoresInfo = gameContainer.find_all("div", class_="score-team-score")

        teamNames, teamScores = [], []
        for teamInfo, scoreInfo in zip(teamsInfo, scoresInfo):
            teamName = teamInfo.find(
                "span", class_="scores-text capi pd-b-1 ff-ff"
            ).text.strip()
            teamScore = scoreInfo.text.strip()
            teamNames.append(NBA_ABBR_ENG_TO_ABBR_CN[teamName])
            teamScores.append(int(teamScore))

        winner = teamNames[0] if teamScores[0] > teamScores[1] else teamNames[1]
        gameResults[(teamNames[0], teamNames[1])] = (
            teamScores[0],
            teamScores[1],
            winner,
        )
    return gameResults


def settle_daily_match_result(playoffsLayout: bool):
    # gameResults[(team1Name, team2Name)]: (team1Score, team2Score, winner)
    gameResults = _get_daily_game_results(playoffsLayout=playoffsLayout)
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for team1Name, team2Name in gameResults:
                team1Score, team2Score, winner = gameResults[(team1Name, team2Name)]
                cur.execute(
                    SQL_UPDATE_MATCH_RESULT,
                    (
                        team1Name,
                        team1Score,
                        team2Score,
                        team2Name,
                        team2Score,
                        team1Score,
                        winner,
                        team1Name,
                        team2Name,
                        team2Name,
                        team1Name,
                    ),
                )
        conn.commit()


def calculate_daily_stat_point():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_USER_PREDICT_STAT3)
            userPredictStatList = cur.fetchall()
            for (
                userUID,
                playerName,
                matchId,
                statType,
                statTarget,
                statResult,
            ) in userPredictStatList:
                finalOutcome = "大盤" if statResult >= statTarget else "小盤"
                cur.execute(
                    SQL_UPDATE_USER_PREDICT_STAT,
                    (finalOutcome, userUID, playerName, matchId, statType),
                )
            cur.execute(SQL_UPDATE_USER_STAT_POINT)
        conn.commit()


def calculate_daily_match_point():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_UPDATE_USER_PREDICT_MATCH)
            cur.execute(SQL_UPDATE_USER_MATCH_POINT)
            cur.execute(SQL_UPDATE_CORRECT_COUNTER)
            cur.execute(SQL_UPDATE_WRONG_COUNTER)
            cur.execute(SQL_DEACTIVE_MATCH)
        conn.commit()


def _get_regular_game(gameInfo: BeautifulSoup):
    teamSoups = gameInfo.find("div", class_="teams").find_all(
        "div", class_="score-team-row"
    )

    game = {
        "names": ["", ""],
        "standings": ["", ""],
    }
    for i, teamSoup in enumerate(teamSoups):
        teamInfo = teamSoup.find("div", class_="score-team-name abbreviation")
        teamName = teamInfo.find("span", class_="scores-text capi pd-b-1 ff-ff").text
        teamStanding = teamInfo.find("sup", class_="scores-team-record ffn-gr-10").text

        if teamName not in NBA_ABBR_ENG_TO_ABBR_CN:
            return None

        game["names"][i] = NBA_ABBR_ENG_TO_ABBR_CN[teamName]
        game["standings"][i] = teamStanding

    return game


def _get_playoffs_game(gameInfo: BeautifulSoup):
    team1 = gameInfo.find("img", class_="team-logo-1").attrs["alt"]
    team2 = gameInfo.find("img", class_="team-logo-2").attrs["alt"]

    standingText = gameInfo.find(
        "div", class_="playoff-game-info ffn-gr-11 uc fs-sm-10"
    ).text.strip()

    standingInfo = standingText.split()
    # 3 Cases:
    # GM 4 TIED 2-2
    # GM 5 LAL LEADS 3-1
    # CONF SEMIS GAME 1
    if standingInfo[2] == "TIED":
        gameNumber = standingInfo[1]
        tie = standingInfo[-1].split("-")[0]
        teamStandings = [tie, tie]
    else:
        if standingInfo[0] == "GM":
            gameNumber = standingInfo[1]
            leadingTeam = standingInfo[2]
            gameStatus = standingInfo[-1]
            teamStandings = gameStatus.split("-")
            if leadingTeam == team2:
                teamStandings.reverse()
        else:
            gameNumber = "1"
            teamStandings = ["0", "0"]

    game = {
        "names": [
            NBA_ABBR_ENG_TO_ABBR_CN[team1],
            NBA_ABBR_ENG_TO_ABBR_CN[team2],
        ],
        "standings": teamStandings,
        "number": gameNumber,
    }

    return game


def _get_nba_games_time_list(timeStr: str):
    data = requests.get(f"https://nba.hupu.com/games/{timeStr}").text
    soup = BeautifulSoup(data, "html.parser")

    gameCenter = soup.find("div", class_="gamecenter_content_l")
    gameContainers = gameCenter.find_all("div", class_="list_box")

    gameTimeList = []
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

        gameTime = (
            gameContainer.find("div", class_="team_vs_b")
            .find("span", class_="b")
            .find("p")
            .text
        )
        gameTimeList.append(gameTime)

    return gameTimeList


def get_nba_games(playoffsLayout: bool):
    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    year = str(nowTW.year)
    month = str(nowTW.month) if nowTW.month >= 10 else "0" + str(nowTW.month)
    day = str(nowTW.day) if nowTW.day >= 10 else "0" + str(nowTW.day)
    todayStr = "-".join([year, month, day])

    data = requests.get(f"https://www.foxsports.com/nba/scores?date={todayStr}").text
    soup = BeautifulSoup(data, "html.parser")

    finalScores = soup.find_all("div", class_="score-team-score")

    if len(finalScores) > 0:
        return [], None, None  # Games already finished -> Previous games (Not today)

    urlPattern = r'<a href="/nba/scores\?date=(\d{4}-\d{2}-\d{2})"'
    if todayStr not in re.findall(urlPattern, data):
        return (
            [],
            None,
            None,
        )  # No game page for this date -> No games today

    tomorrowTW = nowTW + timedelta(days=1)
    tomorrowStr = tomorrowTW.strftime("%Y-%m-%d")
    gameTimeList = _get_nba_games_time_list(tomorrowStr)

    gameClass = "score-chip-playoff pregame" if playoffsLayout else "score-chip pregame"
    gamesInfo = soup.find_all("a", class_=gameClass)
    gameList = []

    # Get the game page and game time of the most intensive game
    gameOfTheDay = {"diff": 30, "page": "", "index": -1, "gameTime": ""}

    for i, (gameInfo, gameTimeTW) in enumerate(zip(gamesInfo, gameTimeList)):
        gamePageUrl = "https://www.foxsports.com" + gameInfo.attrs["href"]
        gamePageData = requests.get(gamePageUrl).text
        gamePageSoup = BeautifulSoup(gamePageData, "html.parser")

        oddContainer = gamePageSoup.find("div", class_="odds-row-container")
        gameOdds = oddContainer.find_all(
            "div", class_="odds-line fs-20 fs-xl-30 fs-sm-23 lh-1 lh-md-1pt5"
        )

        if playoffsLayout:
            game = _get_playoffs_game(gameInfo=gameInfo)
        else:
            game = _get_regular_game(gameInfo=gameInfo)

        if not game:
            continue

        game["points"] = [
            int(round(30 + float(gameOdds[0].text.strip()))),
            int(round(30 + float(gameOdds[1].text.strip()))),
        ]
        game["gametime"] = gameTimeTW

        oddDiff = abs(float(gameOdds[0].text.strip()))
        if oddDiff < gameOfTheDay["diff"]:
            gameOfTheDay["diff"] = oddDiff
            gameOfTheDay["page"] = gamePageUrl
            gameOfTheDay["index"] = i
            gameOfTheDay["gameTime"] = gameTimeTW
        gameList.append(game)

    return gameList, gameOfTheDay["page"] + "?tab=odds", gameOfTheDay["gameTime"]


def get_player_url(playerName: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_PLAYER_LINK, (playerName,))
            return cur.fetchone()[0]


def get_image_url(imgKey: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT_IMAGE_LINK, (imgKey,))
            return cur.fetchall()
