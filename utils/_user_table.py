import re
import requests
import psycopg
from bs4 import BeautifulSoup
from config import DATABASE_URL
from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN
from datetime import datetime, timezone, timedelta

STAT_INDEX = {"得分": 3, "籃板": 5, "抄截": 7}
PREDICTION_INDEX = 38


def get_user_points(rankType: str, isSorted: bool = True):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT name, {rankType} FROM LeaderBoard ORDER BY id;")
            userPoints = cur.fetchall()

    return (
        sorted(userPoints, key=lambda x: x[1], reverse=True) if isSorted else userPoints
    )


def column_exist(column: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # get column names
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'leaderboard'
                ORDER BY ordinal_position
            """
            )
            columns = [row[0] for row in cur.fetchall()]
            return column in columns


def insert_columns(newColumns: list):
    addClauses = ",\n".join(
        [f"ADD COLUMN \"{col}\" TEXT DEFAULT ''" for col in newColumns]
    )
    sql = f"ALTER TABLE LeaderBoard\n{addClauses}"
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def rename_columns(renameMap: dict):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for oldName, newName in renameMap.items():
                cur.execute(
                    f'ALTER TABLE LeaderBoard RENAME COLUMN "{oldName}" TO "{newName}"'
                )
        conn.commit()


def update_columns(updateColumns: list, updateStrategy: list, updateMap: dict):
    names = list(updateMap.keys())
    setClauses = []
    caseValues = []

    for idx, col in enumerate(updateColumns):
        strategy = updateStrategy[idx]
        if strategy == "a":  # add
            caseBlock = f'"{col}" = "{col}" + CASE name\n'
        elif strategy == "w":  # overwrite
            caseBlock = f'"{col}" = CASE name\n'

        for name in names:
            val = updateMap[name][idx]
            caseBlock += "    WHEN %s THEN %s\n"
            caseValues.extend([name, val])
        caseBlock += "END"
        setClauses.append(caseBlock)

    setSQL = ",\n".join(setClauses)
    whereSQL = ", ".join(["%s"] * len(names))

    sql = f"""
        UPDATE LeaderBoard
        SET
        {setSQL}
        WHERE name IN ({whereSQL})
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, caseValues + names)
        conn.commit()


def reset_nba_prediction():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'leaderboard'
                ORDER BY ordinal_position
            """
            )
            columns = [row[0] for row in cur.fetchall()]
            if columns[PREDICTION_INDEX:]:
                dropClauses = ",\n".join(
                    [f'DROP COLUMN "{col}"' for col in columns[PREDICTION_INDEX:]]
                )
                cur.execute(f"ALTER TABLE LeaderBoard\n{dropClauses}")
        conn.commit()


def reset_user_points(rankType: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE LeaderBoard SET {rankType} = 0")
        conn.commit()


def _pre_settle_week_points():
    UTCnow = datetime.now(timezone.utc)
    TWnow = UTCnow.astimezone(timezone(timedelta(hours=8)))
    weekday = TWnow.weekday()  # 0-index, i.e. Monday=0, Sunday=6
    if weekday == 0:
        return
    userDayPoints = get_user_points(rankType="day_points", isSorted=False)
    userWeekPoints = get_user_points(rankType="week_points", isSorted=False)
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
    update_columns(
        updateColumns=["week_points", "month_points"],
        updateStrategy=["w", "a"],
        updateMap=updateMap,
    )


def get_type_best(rankType: str, nextRankType: str):
    if rankType == "month_points":
        _pre_settle_week_points()

    userPoints = get_user_points(rankType=rankType)
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
    update_columns(
        updateColumns=[rankType, nextRankType],
        updateStrategy=["w", "a"],
        updateMap=updateMap,
    )
    return rankBest


def get_user_correct(userName: str, teamList: list, correct: bool):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    sql = f"""
                        SELECT {", ".join([f'"{team}"' for team in teamList])}
                        FROM LeaderBoard
                        WHERE name = %s
                    """
                    cur.execute(sql, (userName,))
                    counter = cur.fetchone()

            i = 0 if correct else 1
            values = [int(val.split()[i]) for val in counter]
            return dict(
                sorted(
                    dict(zip(teamList, values)).items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            )


def settle_user_correct(teamList: list):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    sql = f"""
                        SELECT {", ".join([f'"{team}"' for team in teamList])}
                        FROM LeaderBoard
                    """
                    cur.execute(sql)
                    correctList = {key: 0 for key in teamList}
                    wrongList = {key: 0 for key in teamList}
                    for userResult in cur.fetchall():
                        for teanName, countStr in zip(teamList, userResult):
                            correct, wrong = countStr.split()
                            correctList[teanName] += int(correct)
                            wrongList[teanName] += int(wrong)

                    mostCorrectTeam = max(correctList, key=correctList.get)
                    mostWrongTeam = max(wrongList, key=wrongList.get)
                    # Build: column1 = 'DEFAULT, column2 = 'DEFAULT, ...
                    setClause = ", ".join([f'"{col}" = DEFAULT' for col in teamList])
                    # Reset columns to Default
                    cur.execute(f"UPDATE LeaderBoard SET {setClause}")
                    return f"{mostCorrectTeam}是信仰的GOAT\n{mostWrongTeam}是傻鳥的GOAT"


def user_exist(userName: str, userUID: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, uid FROM LeaderBoard ORDER BY id")
            return (userName, userUID) in cur.fetchall()


def add_user(userName: str, userUID: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Insert initial users (team fields will default to '0 0')
            cur.execute("SELECT name, uid FROM LeaderBoard ORDER BY id")
            userNameList, userUIDList = zip(*cur.fetchall())

            if userName in userNameList and userUID in userUIDList:
                response = f"{userName} 已經註冊過了"
            # Change user name
            elif userUID in userUIDList:
                oldName = userNameList[userUIDList.index(userUID)]
                newName = userName
                cur.execute(
                    "UPDATE LeaderBoard SET name = %s WHERE uid = %s",
                    (newName, userUID),
                )
                response = f"{oldName} 改名為 {newName}"
            # Set user UID
            elif userName in userNameList:
                cur.execute(
                    "UPDATE LeaderBoard SET uid = %s WHERE name = %s",
                    (userUID, userName),
                )
                response = f"{userName} 設定 UID"
            # Add new user
            else:
                cur.execute(
                    "INSERT INTO LeaderBoard (name, uid) VALUES (%s, %s)",
                    (userName, userUID),
                )
                response = f"{userName} 完成註冊"
        conn.commit()
    return response


def check_user_prediction(userName: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # get column names
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'leaderboard'
                ORDER BY ordinal_position
            """
            )
            matchColumns = [row[0] for row in cur.fetchall()][PREDICTION_INDEX:]

            cur.execute("SELECT * FROM LeaderBoard WHERE name = %s", (userName,))
            userPrediction = cur.fetchone()[PREDICTION_INDEX:]

            notPredictedGames = []
            for match, prediction in zip(matchColumns, userPrediction):
                if not prediction:
                    notPredictedGames.append(match)

            n = len(notPredictedGames)
            if n == 0 and len(matchColumns) > 0:
                return "已經完成全部預測"
            if n == len(matchColumns):
                return "還沒預測任何比賽"

            return "\n".join(["還沒預測:"] + notPredictedGames)


def user_predicted(userName: str, column: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT "{column}" FROM LeaderBoard WHERE name = %s',
                (userName,),
            )
            result = cur.fetchone()[0].strip()
            return result != ""


def get_user_prediction(userId: int):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM LeaderBoard ORDER BY id")
            userList = [row for row in cur.fetchall()]
            userIdToName = {id: name for id, name, *_ in userList}
            if userId not in userIdToName.keys():
                return "\n".join(
                    ["使用方式:", "跟盤 id"]
                    + [f"{id}. {name}" for id, name in userIdToName.items()]
                )

            predictList = [
                prediction
                for prediction in list(userList[userId - 1][PREDICTION_INDEX:])
                if prediction
            ]

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
            cur.execute("SELECT * FROM LeaderBoard ORDER BY id")
            userList = [row for row in cur.fetchall()]
            userIdToName = {id: name for id, name, *_ in userList}
            if (
                user1Id not in userIdToName.keys()
                or user2Id not in userIdToName.keys()
                or user1Id == user2Id
            ):
                return "\n".join(
                    ["使用方式:", "比較 id id"]
                    + [f"{id}. {name}" for id, name in userIdToName.items()]
                )

            user1PredictList = list(userList[user1Id - 1][PREDICTION_INDEX:])
            user2PredictList = list(userList[user2Id - 1][PREDICTION_INDEX:])
            if all(s == "" for s in user1PredictList) and all(
                s == "" for s in user2PredictList
            ):
                return f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 都還沒預測任何比賽"

            same = True
            comparison = []
            for user1Predict, user2Predict in zip(user1PredictList, user2PredictList):
                if not user1Predict and not user2Predict:
                    continue
                if user1Predict == user2Predict:
                    comparison.append(user1Predict)
                else:
                    same = False
                    comparison.append(_remove_common_prefix(user1Predict, user2Predict))

            if same:
                return f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 的預測相同"
            return "\n".join(
                [f"{userIdToName[user1Id]} 和 {userIdToName[user2Id]} 的不同預測:"]
                + comparison
            )


def _get_prediction_columns():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # get column names
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'leaderboard'
                ORDER BY ordinal_position
            """
            )
            columns = [row[0] for row in cur.fetchall()]
            return columns[PREDICTION_INDEX:]


def _get_daily_game_results(playoffsLayout: bool):
    data = requests.get("https://www.foxsports.com/nba/scores").text
    soup = BeautifulSoup(data, "html.parser")

    gameResults = {}  # "team1-team2": "winner"
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

        gameResults["-".join(teamNames)] = (
            teamNames[0] if teamScores[0] > teamScores[1] else teamNames[1]
        )
    return gameResults


def _game_is_today(gameDate: str):
    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))

    # MM/DD
    month, day = gameDate.split("/")
    return int(day) == nowTW.day


def _settle_daily_stats_results(statsColumns: list):
    renameMap = {}
    for i, statsColumn in enumerate(statsColumns):
        # Original: Anthony Edwards 得分26.5 4/6
        # Aim: Anthony Edwards 大盤 6
        words = statsColumn.split()
        overPoint, underPoint = words[-1].split("/")
        statType, statTarget = words[-2][:2], float(words[-2][2:])
        playerName = " ".join(words[:-2])

        playerUrl = get_player_url(playerName=playerName)
        playerStatsPageUrl = playerUrl + "-stats"

        playerStatsPageData = requests.get(playerStatsPageUrl).text
        playerStatsPageSoup = BeautifulSoup(playerStatsPageData, "html.parser")

        statsContainer = playerStatsPageSoup.find(
            "tbody", class_="row-data lh-1pt43 fs-14"
        )
        mostRecentGame = statsContainer.find("tr")
        gameDate = mostRecentGame.find("span", class_="table-result").text.strip()

        statValue = int(
            mostRecentGame.find("td", {"data-index": STAT_INDEX[statType]}).text.strip()
        )
        if _game_is_today(gameDate=gameDate):
            if statValue >= statTarget:
                finalResult = f"{playerName} 大盤 {overPoint}"
            else:
                finalResult = f"{playerName} 小盤 {underPoint}"
        else:
            finalResult = f"{playerName} 未出賽{i} 0"

        renameMap[statsColumn] = finalResult

    return renameMap


def settle_daily_game_stats(playoffsLayout: bool):
    predictColumns = _get_prediction_columns()
    gameResults = _get_daily_game_results(playoffsLayout=playoffsLayout)
    statsColumns = []
    renameMap = {}
    for predictColumn in predictColumns:
        words = predictColumn.split()
        if len(words) == 2:
            gameTitle, teamPoints = words
            teamPoints = teamPoints.split("/")

            if gameTitle not in gameResults:
                gameTitle = "-".join(list(reversed(gameTitle.split("-"))))
                teamPoints.reverse()

            team1, team2 = gameTitle.split("-")
            winner = gameResults[gameTitle]
            point = teamPoints[0] if winner == team1 else teamPoints[1]

            renameMap[predictColumn] = f"{winner} {point}"
        else:
            statsColumns.append(predictColumn)

    statsMap = _settle_daily_stats_results(statsColumns=statsColumns)
    renameMap.update(statsMap)

    rename_columns(renameMap=renameMap)


def _update_user_correct(predictMap: dict, currMap: dict):
    # predictMap[team] = is correct
    # currMap[team] = "5 2"
    for teamName in predictMap:
        correct, wrong = currMap[teamName].split()
        correct, wrong = int(correct), int(wrong)
        if predictMap[teamName]:
            correct += 1
        else:
            wrong += 1

        currMap[teamName] = f"{correct} {wrong}"

    return list(currMap.values())


def calculate_user_daily_points():
    updateMap = {}
    dailyResult = []
    teamNames = []
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Get match column names
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'leaderboard'
                ORDER BY ordinal_position
            """
            )
            columns = [row[0] for row in cur.fetchall()]
            teamNames = columns[PREDICTION_INDEX - 30 : PREDICTION_INDEX]

            cur.execute("SELECT * FROM LeaderBoard ORDER BY id")

            for userInfo in cur.fetchall():
                predictMap = {}
                userName = userInfo[1]
                dayPoint = 0
                weekPointCurr = userInfo[3]
                for matchName, predictResult in zip(
                    columns[PREDICTION_INDEX:], userInfo[PREDICTION_INDEX:]
                ):
                    if not predictResult:
                        continue
                    words = matchName.split()
                    if len(words) == 2:
                        result, point = words
                        predictMap[predictResult] = predictResult == result
                    else:
                        result = " ".join(words[:-1])
                        point = words[-1]
                    point = int(point)
                    if predictResult == result:
                        dayPoint += point

                # (userName, week_points, day_points)
                dailyResult.append((userName, weekPointCurr + dayPoint, dayPoint))

                newCorrectList = _update_user_correct(
                    predictMap=predictMap,
                    currMap={
                        key: value
                        for key, value in zip(
                            columns[PREDICTION_INDEX - 30 : PREDICTION_INDEX],
                            userInfo[PREDICTION_INDEX - 30 : PREDICTION_INDEX],
                        )
                    },
                )

                updateMap[userName] = [dayPoint, dayPoint] + newCorrectList

            if columns[PREDICTION_INDEX:]:
                dropClauses = ",\n".join(
                    [f'DROP COLUMN "{col}"' for col in columns[PREDICTION_INDEX:]]
                )
                cur.execute(f"ALTER TABLE LeaderBoard\n{dropClauses}")
        conn.commit()

    # write dayPoint to day_points
    # add dayPoint to week_points
    updateColumns = ["day_points", "week_points"] + teamNames
    updateStrategy = ["w", "a"] + ["w"] * 30
    update_columns(
        updateColumns=updateColumns,
        updateStrategy=updateStrategy,
        updateMap=updateMap,
    )
    return sorted(dailyResult, key=lambda x: x[1], reverse=True)


def _utc_to_tw_time(gameTimeUTC: str):
    # gameTimeUTC = "1:00 AM"
    timeUTC = datetime.strptime(gameTimeUTC, "%I:%M%p").replace(tzinfo=timezone.utc)
    timeTW = timeUTC.astimezone(timezone(timedelta(hours=8)))
    gameTimeTW = timeTW.strftime("%H:%M")
    return gameTimeTW


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

    gameClass = "score-chip-playoff pregame" if playoffsLayout else "score-chip pregame"
    gamesInfo = soup.find_all("a", class_=gameClass)
    gameList = []

    gameOfTheDay = {
        "diff": 30,
        "page": "",
        "gametime": "",
    }  # Get the game page and game time of the most intensive game

    for gameInfo in gamesInfo:
        gameTimeUTC = gameInfo.find("span", class_="time ffn-gr-11").text.strip()
        gameTimeTW = _utc_to_tw_time(gameTimeUTC=gameTimeUTC)

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

        game["points"] = [
            int(round(30 + float(gameOdds[0].text.strip()))),
            int(round(30 + float(gameOdds[1].text.strip()))),
        ]
        game["gametime"] = gameTimeTW

        oddDiff = abs(float(gameOdds[0].text.strip()))
        if oddDiff < gameOfTheDay["diff"]:
            gameOfTheDay["diff"] = oddDiff
            gameOfTheDay["page"] = gamePageUrl
            gameOfTheDay["gametime"] = gameTimeTW

        gameList.append(game)

    return gameList, gameOfTheDay["page"] + "?tab=odds", gameOfTheDay["gametime"]


def get_player_url(playerName: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT link FROM PlayerLink WHERE name = %s", (playerName,))
            return cur.fetchone()[0]


def get_image_url(imgKey: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT link FROM ImageLink WHERE category = %s", (imgKey,))
            return cur.fetchall()
