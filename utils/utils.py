import random
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import IMGUR_CLIENT_ID
from utils._user_table import *
from utils._team_table import (
    NBA_ABBR_ENG_TO_ABBR_CN,
    NBA_SIMP_CN_TO_TRAD_CN,
    NBA_TRAD_CN_TO_CBS,
)
from linebot.models import (
    CarouselColumn,
    PostbackAction,
    ButtonsTemplate,
    MessageAction,
)

RANK_TYPE_TRANSLATION = {
    "week_points": "本週",
    "month_points": "本月",
    "season_points": "本季",
    "all_time_points": "歷史",
}
NEXT_RANK_TYPE = {
    "week_points": "month_points",
    "month_points": "season_points",
    "season_points": "all_time_points",
}

BET_STAT_TRANSLATION = {
    "PLAYER POINTS": "得分",
    "PLAYER REBOUNDS": "籃板",
    "PLAYER STEALS": "抄截",
}


def get_user_type_point(rankType: str):
    userPoints = get_type_points(rankType=rankType)
    userPoints.sort(key=lambda x: x[1], reverse=True)

    response = "\n".join(
        [f"{RANK_TYPE_TRANSLATION[rankType]}排行榜:"]
        + [f"{i}. {name}: {point}分" for i, (name, point) in enumerate(userPoints, 1)]
    )
    return response


def get_user_type_best(rankType: str):
    rankBest = get_type_best(rankType=rankType, nextRankType=NEXT_RANK_TYPE[rankType])
    if not rankBest:
        return None, f"{RANK_TYPE_TRANSLATION[rankType]}沒有分數"

    bestMessage = f"{RANK_TYPE_TRANSLATION[rankType]}預測GOAT: "
    for name, point in rankBest:
        bestMessage += f"{name}({point}分) "

    userNextPoints = get_type_points(rankType=NEXT_RANK_TYPE[rankType])
    userNextPoints.sort(key=lambda x: x[1], reverse=True)
    rankMessage = (
        f"{RANK_TYPE_TRANSLATION[NEXT_RANK_TYPE[rankType]]}排行榜:\n"
        + "\n".join(
            f"{i}. {name}: {point}分"
            for i, (name, point) in enumerate(userNextPoints, 1)
        )
    )

    return bestMessage, rankMessage[:-1]


def get_user_season_correct_count(userName: str, teamName: str):
    # (team1, season_correct1), (team2, season_correct2), ...
    teamList, seasonCorrect = get_user_season_correct(userName=userName)

    if not teamName:
        return f"{userName}是{teamList[0]}的舔狗"

    if teamName not in teamList:
        return f"{teamName} is unknown"

    return f"{userName}舔了{teamName}{seasonCorrect[teamList.index(teamName)]}口"


def get_user_season_wrong_count(userName: str, teamName: str):
    # (team1, season_wrong1), (team2, season_wrong2), ...
    teamList, seasonWrong = get_user_season_wrong(userName=userName)

    if not teamName:
        return f"{userName}的傻鳥是{teamList[0]}"

    if teamName not in teamList:
        return f"{teamName} is unknown"

    return f"{userName}被{teamName}肛了{seasonWrong[teamList.index(teamName)]}次"


def get_season_most_correct_and_wrong():
    response = settle_season_correct_wrong()
    return response()


def user_registration(userUID: str, userName: str, pictureUrl: str):
    response = add_user(userUID=userUID, userName=userName, pictureUrl=pictureUrl)
    return response


def get_user_prediction_check(userName: str):
    return userName + check_user_prediction(userName)


def get_prediction_by_id(userId: int):
    response = get_user_prediction(userId)
    return response


def get_prediction_comparison(user1Id: int, user2Id: int):
    response = compare_user_prediction(user1Id, user2Id)
    return response


def _get_daily_game_results():
    data = requests.get("https://nba.hupu.com/games").text
    soup = BeautifulSoup(data, "html.parser")

    gameCenter = soup.find("div", class_="gamecenter_content_l")
    gameContainers = gameCenter.find_all("div", class_="list_box")

    gameResults = {}
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

        team1Score = team2Score = ""

        gameStatus = gameContainer.find("div", class_="team_vs").text
        if "进行中" in gameStatus or "未开始" in gameStatus:
            raise ValueError(f"{team1Name} - {team2Name} Not Finished")

        team1Win = team1.find("div", class_="txt").find("span", class_="num red")
        if team1Win:
            team1Score = team1Win.text
            team2Score = team2.find("div", class_="txt").find("span", class_="num").text
        else:
            team1Score = team1.find("div", class_="txt").find("span", class_="num").text
            team2Score = (
                team2.find("div", class_="txt").find("span", class_="num red").text
            )

        gameResults[(team1Name, team2Name)] = (
            int(team1Score) if team1Score else 0,
            int(team2Score) if team2Score else 0,
        )

    return gameResults


def settle_daily_prediction():
    """TODO playoffs layout"""
    gameResults = _get_daily_game_results()
    update_daily_match_score(gameScores=gameResults)
    settle_daily_stat_result()

    calculate_daily_stat_point()
    calculate_daily_match_point()

    dayPoints = get_type_points(rankType="day_points")
    weekPoints = get_type_points(rankType="week_points")
    userPoints = []
    for i in range(len(dayPoints)):
        userName, userDayPoints = dayPoints[i]
        userWeekPoints = weekPoints[i][1]
        userPoints.append((userName, userWeekPoints, userDayPoints))
    userPoints.sort(key=lambda x: x[1], reverse=True)

    response = "\n".join(
        [f"{RANK_TYPE_TRANSLATION['week_points']}排行榜:"]
        + [
            f"{i}. {userName}: {userWeekPoints}分 (+{userDayPoints})"
            for i, (userName, userWeekPoints, userDayPoints) in enumerate(userPoints, 1)
        ]
    )
    return response


def _check_url_exist(url: str):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def _pack_game_carousel_column(game: dict, playoffsLayout: bool, tomorrowStr: str):
    teamNames = game["names"]
    teamStandings = game["standings"]
    teamPoints = game["points"]
    gameTime = game["gametime"]
    awayHome = ["客", "主"]

    gameNumber = "Game " + game["number"] + "\n" if playoffsLayout else ""

    encodedTeam1 = quote(teamNames[0])
    encodedTeam2 = quote(teamNames[1])
    thumbnailImageUrl = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encodedTeam1}_{encodedTeam2}.png"
    if not _check_url_exist(url=thumbnailImageUrl):
        thumbnailImageUrl = f"https://raw.githubusercontent.com/Mike1ife/Line-Bot/main/images/merge/{encodedTeam2}_{encodedTeam1}.png"
        teamNames.reverse()
        teamStandings.reverse()
        teamPoints.reverse()
        awayHome.reverse()

    # title = 溜馬(主) 1-11 - 老鷹(客) 5-6
    # text = 7:30\n溜馬 31分 / 老鷹 9分
    carouselColumn = CarouselColumn(
        thumbnail_image_url=thumbnailImageUrl,
        title=f"{teamNames[0]}({awayHome[0]}) {teamStandings[0]} - {teamNames[1]}({awayHome[1]}) {teamStandings[1]}",
        text=f"{gameNumber}{gameTime}\n{teamNames[0]} {teamPoints[0]}分 / {teamNames[1]} {teamPoints[1]}分",
        actions=[
            PostbackAction(
                label=teamNames[0],
                data=f"NBA球隊預測;{teamNames[0]};{teamNames[1]};{teamNames[0]};{tomorrowStr};{gameTime}",
            ),
            PostbackAction(
                label=teamNames[1],
                data=f"NBA球隊預測;{teamNames[0]};{teamNames[1]};{teamNames[1]};{tomorrowStr};{gameTime}",
            ),
        ],
    )
    return carouselColumn, teamNames, teamPoints, teamStandings


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

    gameTimeMap = {}
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
        gameTimeMap[(team1Name, team2Name)] = (
            gameTime if gameTime != "00:00" else "12:00"
        )

    return gameTimeMap


def get_nba_games(playoffsLayout: bool):
    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    todayStr = nowTW.strftime("%Y-%m-%d")

    # use a persistent session for connection pooling
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    # get today's score page
    data = session.get(f"https://www.foxsports.com/nba/scores?date={todayStr}").text
    soup = BeautifulSoup(data, "html.parser")

    finalScores = soup.find_all("div", class_="score-team-score")
    if len(finalScores) > 0:
        return [], None, None  # Games already finished

    urlPattern = r'<a href="/nba/scores\?date=(\d{4}-\d{2}-\d{2})"'
    if todayStr not in re.findall(urlPattern, data):
        return [], None, None  # No game page for this date

    tomorrowTW = nowTW + timedelta(days=1)
    tomorrowStr = tomorrowTW.strftime("%Y-%m-%d")
    gameTimeMap = _get_nba_games_time_list(tomorrowStr)

    gameClass = "score-chip-playoff pregame" if playoffsLayout else "score-chip pregame"
    gamesInfo = soup.find_all("a", class_=gameClass)

    game_urls = ["https://www.foxsports.com" + g.attrs["href"] for g in gamesInfo]

    def fetch_page(url):
        resp = session.get(url)
        resp.raise_for_status()
        return url, resp.text

    pages = {}
    with ThreadPoolExecutor(max_workers=min(8, len(game_urls))) as executor:
        futures = [executor.submit(fetch_page, url) for url in game_urls]
        for future in as_completed(futures):
            url, data = future.result()
            pages[url] = data

    gameList = []
    gameOfTheDay = {"diff": 30, "page": "", "index": -1, "gameTime": ""}

    for i, gameInfo in enumerate(gamesInfo):
        gamePageUrl = "https://www.foxsports.com" + gameInfo.attrs["href"]
        gamePageData = pages.get(gamePageUrl)
        if not gamePageData:
            continue

        gamePageSoup = BeautifulSoup(gamePageData, "html.parser")
        oddContainer = gamePageSoup.find("div", class_="odds-row-container")
        if not oddContainer:
            continue

        gameOdds = oddContainer.find_all(
            "div", class_="odds-line fs-20 fs-xl-30 fs-sm-23 lh-1 lh-md-1pt5"
        )
        if len(gameOdds) < 2:
            continue

        # Parse game info
        # game = {
        #   "names": []
        #   "standings": []
        # }
        if playoffsLayout:
            game = _get_playoffs_game(gameInfo)
        else:
            game = _get_regular_game(gameInfo)
        if not game:
            continue

        # Add points and time
        game["points"] = [
            int(round(30 + float(gameOdds[0].text.strip()))),
            int(round(30 + float(gameOdds[1].text.strip()))),
        ]

        team1Name, team2Name = game["names"]
        game["gametime"] = (
            gameTimeMap[(team1Name, team2Name)]
            if (team1Name, team2Name) in gameTimeMap
            else gameTimeMap[(team2Name, team1Name)]
        )

        # Find closest odds (most even match)
        oddDiff = abs(float(gameOdds[0].text.strip()))
        if oddDiff < gameOfTheDay["diff"]:
            gameOfTheDay.update(
                {
                    "diff": oddDiff,
                    "page": gamePageUrl,
                    "index": i,
                    "gameTime": game["gametime"],
                }
            )

        gameList.append(game)

    return (
        gameList,
        (gameOfTheDay["page"] + "?tab=odds" if gameOfTheDay["page"] else None),
        gameOfTheDay["gameTime"],
    )


def get_nba_game_prediction(playoffsLayout: bool = False):
    response = get_user_type_point(rankType="week_points")

    matchList = []
    carouselColumns = []

    gameList, gameOfTheDayPage, gameOfTheDayTime = get_nba_games(
        playoffsLayout=playoffsLayout
    )

    if len(gameList) == 0:
        return "明天沒有比賽", None, None, None, None

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    tomorrowTW = nowTW + timedelta(days=1)
    tomorrowStr = tomorrowTW.strftime("%Y-%m-%d")
    gameOfTheDayDate = tomorrowStr

    for game in gameList:
        carouselColumn, teamNames, teamPoints, teamStandings = (
            _pack_game_carousel_column(
                game=game, playoffsLayout=playoffsLayout, tomorrowStr=tomorrowStr
            )
        )
        carouselColumns.append(carouselColumn)

        matchList.append(
            (
                tomorrowStr,
                teamNames[0],
                teamNames[1],
                teamStandings[0],
                teamStandings[1],
                teamPoints[0],
                teamPoints[1],
            )
        )

    return (
        matchList,
        response,
        carouselColumns,
        gameOfTheDayPage,
        gameOfTheDayDate,
        gameOfTheDayTime,
    )


def _compare_timestring(timeStr1: str, timeStr2: str):
    format = "%Y-%m-%d-%H:%M"

    return datetime.strptime(timeStr1, format) > datetime.strptime(timeStr2, format)


def get_nba_prediction_posback(
    userName: str,
    userUID: str,
    pictureUrl: str,
    team1Name: str,
    team2Name: str,
    userPrediction: str,
    gameDate: str,
    gameTime: str,
):
    if not user_exist(userName=userName, userUID=userUID, pictureUrl=pictureUrl):
        return f"{userName} 請先註冊"

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    nowTWStr = nowTW.strftime("%Y-%m-%d-%H:%M")
    gameTimeStr = f"{gameDate}-{gameTime}"
    if _compare_timestring(timeStr1=nowTWStr, timeStr2=gameTimeStr):
        return f"{team1Name}-{team2Name} 的比賽已經開始了"

    returnState = insert_user_predict_match(
        userUID=userUID,
        userPrediction=userPrediction,
        team1Name=team1Name,
        team2Name=team2Name,
        gameDate=gameDate,
    )

    if returnState == "CONFLICT":
        return f"{userName}已經預測{team1Name}-{team2Name}了"
    # retrunState = "INSERT"
    if userPrediction == team1Name:
        return f"{userName}預測{team1Name}贏{team2Name}"
    else:
        return f"{userName}預測{team2Name}贏{team1Name}"


def _get_game_translation(gameDescription: str):
    awayTeam, _, homeTeam, _, _, _ = gameDescription.split()
    return f"{NBA_ABBR_ENG_TO_ABBR_CN[awayTeam]} @ {NBA_ABBR_ENG_TO_ABBR_CN[homeTeam]}"


def _get_player_bet_info(
    playerSoup: BeautifulSoup, statType: str, session: requests.Session
):
    imgSrc = playerSoup.find("img").get("src")
    playerName = playerSoup.find("img").get("alt")
    gameDescription = playerSoup.find("div", class_="ffn-gr-11").text
    gameTitle = _get_game_translation(gameDescription=gameDescription)

    playerUrl = get_player_url(playerName=playerName)
    playerStatsUrl = playerUrl + "-stats"

    # Use session instead of requests.get
    resp = session.get(playerStatsUrl)
    resp.raise_for_status()
    playerStatsSoup = BeautifulSoup(resp.text, "html.parser")

    statTypeToContainerIndex = {"得分": 0, "籃板": 1, "抄截": 4}
    playerStats = playerStatsSoup.find_all("a", class_="stats-overview")
    statContainer = playerStats[statTypeToContainerIndex[statType]]

    statAvgText = statContainer.find("div", class_="fs-54 fs-sm-40").text
    statAvg = statAvgText.split()[0]
    statTarget = playerSoup.find("div", class_="fs-30").text

    _odds_msg = (
        playerSoup.find("span", class_="pd-r-2").text
        + " "
        + playerSoup.find("span", class_="cl-og").text
    )
    _odds_items = _odds_msg.split()
    odds = (int(_odds_items[4][1:]) - int(_odds_items[1][1:])) // 2
    overPoint = int(1.5 * odds)
    underPoint = 15 - overPoint

    return (
        imgSrc,
        playerName,
        gameTitle,
        statAvg,
        statTarget,
        overPoint,
        underPoint,
    )


def _pack_stat_carousel_column(
    imgSrc: str,
    playerName: str,
    gameTitle: str,
    statAvg: str,
    statTarget: str,
    overPoint: int,
    underPoint: int,
    statType: str,
    tomorrowStr: str,
    gameTime: str,
):
    team1Name, team2Name = gameTitle.split(" @ ")
    # title = Anthony Edwards
    # text = 場均得分 28.0\n7:00 國王 @ 灰狼\n大盤 (得分超過 26.5) 4分 / 小盤 (得分低於 26.5) 6分
    # button1 = 大盤
    # button2 = 小盤
    carouselColumn = CarouselColumn(
        thumbnail_image_url=imgSrc,
        title=playerName,
        text=f"場均{statType} {statAvg}\n{gameTime} {gameTitle}\n大盤 ({statType}超過{statTarget}) {overPoint}分\n小盤 ({statType}低於{statTarget}) {underPoint}分",
        actions=[
            PostbackAction(
                label="大盤",
                data=f"NBA球員預測;{playerName};{team1Name};{team2Name};{statType};{statTarget};大盤;{tomorrowStr};{gameTime}",
            ),
            PostbackAction(
                label="小盤",
                data=f"NBA球員預測;{playerName};{team1Name};{team2Name};{statType};{statTarget};小盤;{tomorrowStr};{gameTime}",
            ),
        ],
    )

    return carouselColumn


def get_player_stat_prediction(gamePage: str, gameDate: str, gameTime: str):
    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    tomorrowTW = nowTW + timedelta(days=1)
    tomorrowStr = tomorrowTW.strftime("%Y-%m-%d")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    data = session.get(gamePage).text
    soup = BeautifulSoup(data, "html.parser")
    betContainer = soup.find_all("div", class_="odds-component-prop-bet")

    playerStatBetList = []
    carouselColumns = []

    # Step 1: gather all (playerSoup, statType)
    playerTasks = []
    for betInfo in betContainer:
        betTitle = betInfo.find("h2", class_="pb-name fs-30").text.strip()
        if betTitle not in BET_STAT_TRANSLATION:
            continue
        statType = BET_STAT_TRANSLATION[betTitle]
        playerContainers = betInfo.find_all(
            "div", class_="prop-bet-data pointer prop-future"
        )

        for playerSoup in playerContainers:
            playerTasks.append((playerSoup, statType))

    # Step 2: run concurrently (limit to 5 threads to avoid blocking site)
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_get_player_bet_info, playerSoup, statType, session): (
                playerSoup,
                statType,
            )
            for playerSoup, statType in playerTasks
        }

        for future in as_completed(futures):
            try:
                (
                    imgSrc,
                    playerName,
                    gameTitle,
                    statAvg,
                    statTarget,
                    overPoint,
                    underPoint,
                ) = future.result()

                carouselColumn = _pack_stat_carousel_column(
                    imgSrc=imgSrc,
                    playerName=playerName,
                    gameTitle=gameTitle,
                    statAvg=statAvg,
                    statTarget=statTarget,
                    overPoint=overPoint,
                    underPoint=underPoint,
                    statType=futures[future][1],
                    tomorrowStr=tomorrowStr,
                    gameTime=gameTime,
                )

                carouselColumns.append(carouselColumn)

                team1Name, team2Name = gameTitle.split(" @ ")
                playerStatBetList.append(
                    (
                        playerName,
                        gameDate,
                        team1Name,
                        team2Name,
                        futures[future][1],
                        float(statTarget),
                        overPoint,
                        underPoint,
                    )
                )

            except Exception as e:
                raise Exception(f"[WARN] Player fetch failed: {e}")

    return carouselColumns, playerStatBetList


def get_player_stat_prediction_postback(
    userName: str,
    userUID: str,
    pictureUrl: str,
    playerName: str,
    team1Name: str,
    team2Name: str,
    statType: str,
    statTarget: str,
    userPrediction: str,
    gameDate: str,
    gameTime: str,
):
    if not user_exist(userName=userName, userUID=userUID, pictureUrl=pictureUrl):
        return f"{userName} 請先註冊"

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    nowTWStr = nowTW.strftime("%Y-%m-%d-%H:%M")
    gameTimeStr = f"{gameDate}-{gameTime}"
    if _compare_timestring(timeStr1=nowTWStr, timeStr2=gameTimeStr):
        return f"{playerName} 的比賽已經開始了"

    returnState = insert_user_predict_stat(
        userUID=userUID,
        userPrediction=userPrediction,
        playerName=playerName,
        statType=statType,
        team1Name=team1Name,
        team2Name=team2Name,
        gameDate=gameDate,
    )

    if returnState == "CONFLICT":
        return f"{userName}已經預測{playerName}{statType}超過(低於){statTarget}了"
    # returnState = "INSERT"
    if userPrediction == "大盤":
        return f"{userName}預測{playerName}{statType}超過{statTarget}"
    if userPrediction == "小盤":
        return f"{userName}預測{playerName}{statType}低於{statTarget}"


def insert_nba_totay(matchList: list, playerStatBetList: list):
    insert_match(matchList=matchList)
    if playerStatBetList:
        insert_player_stat_bet(playerStatBetList=playerStatBetList)


def get_nba_guessing():
    BASEURL = "https://www.foxsports.com/"

    def getTeamList():
        url = BASEURL + "nba/teams"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        teamList = soup.find_all("a", class_="entity-list-row-container image-logo")
        return teamList

    def getPlayerList(teamList: list):
        team = random.choice(teamList)
        url = BASEURL + team.attrs["href"] + "-roster"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        playerList = soup.find_all("a", class_="table-entity-name ff-ffc")

        if len(playerList) == 0:
            return getPlayerList(teamList)
        return playerList

    def getPlayerStats(playerList: list):
        player = random.choice(playerList)
        url = BASEURL + player.attrs["href"] + "-stats"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        playerName = soup.find("span", class_="lh-sm-25")
        statsOverview = soup.find_all("a", class_="stats-overview")

        if len(statsOverview) == 0:
            return getPlayerStats(playerList)
        return playerName, statsOverview

    def parseStatData(stat: BeautifulSoup):
        url = BASEURL + stat.attrs["href"]
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        allYears = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all("tr")
        return allYears

    def processScoringData(allYears: list, playerInfo: dict):
        for eachYear in allYears:
            tdList = eachYear.find_all("td")
            YEAR = tdList[0].getText().strip()
            TEAM = tdList[1].getText().strip()

            if TEAM == "TOTAL":
                continue

            yearData = {
                "Year": YEAR,
                "Team": TEAM,
                "GP": tdList[2].getText().strip(),
                "GS": tdList[3].getText().strip(),
                "MPG": tdList[4].getText().strip(),
                "PPG": tdList[5].getText().strip(),
                "FPR": tdList[10].getText().strip(),
            }
            playerInfo["stats"].append(yearData)

    def processReboundingData(allYears: list, playerInfo: dict):
        statIndex = 0
        for eachYear in allYears:
            tdList = eachYear.find_all("td")
            TEAM = tdList[1].getText().strip()

            if TEAM == "TOTAL":
                continue

            RPG = tdList[5].getText().strip()
            playerInfo["stats"][statIndex]["RPG"] = RPG
            statIndex += 1

    def processAssistsData(allYears: list, playerInfo: dict):
        statIndex = 0
        for eachYear in allYears:
            tdList = eachYear.find_all("td")
            TEAM = tdList[1].getText().strip()

            if TEAM == "TOTAL":
                continue

            APG = tdList[6].getText().strip()
            playerInfo["stats"][statIndex]["APG"] = APG
            statIndex += 1

    def formatHistoryStrings(playerInfo: dict):
        historyTeams = []
        historyGame = []
        historyStats = []

        for stat in playerInfo["stats"]:
            year = stat["Year"].replace("-", "\u200b-")

            historyTeams.append("{:<8} {:<8}".format(year, stat["Team"]) + "\n")
            historyGame.append(
                "{:<8} {:<8} {:<8}".format(
                    year, f"{stat['GS']}/{stat['GP']}", stat["MPG"]
                )
                + "\n"
            )
            historyStats.append(
                "{:<8} {:<8}".format(
                    year, f"{stat['PPG']}/{stat['RPG']}/{stat['APG']}/{stat['FPR']}%"
                )
                + "\n"
            )

        return "\n".join(historyTeams), "\n".join(historyGame), "\n".join(historyStats)

    teamList = getTeamList()
    playerList = getPlayerList(teamList)
    playerName, statsOverview = getPlayerStats(playerList)

    playerInfo = {"name": playerName.getText().title(), "stats": []}

    for stat in statsOverview:
        statType = (
            stat.find("h3", class_="stat-name uc fs-18 fs-md-14 fs-sm-14")
            .getText()
            .strip()
        )

        if statType == "SCORING":
            allYears = parseStatData(stat)
            processScoringData(allYears, playerInfo)
        elif statType == "REBOUNDING":
            allYears = parseStatData(stat)
            processReboundingData(allYears, playerInfo)
        elif statType == "ASSISTS":
            allYears = parseStatData(stat)
            processAssistsData(allYears, playerInfo)

    # Format output strings
    historyTeams, historyGame, historyStats = formatHistoryStrings(playerInfo)

    usage = "使用提示:\n生涯球隊: 球員生涯球隊\n上場時間: 先發場次/出場場次, 平均上場時間\n賽季平均: 得分/籃板/助攻/命中率"
    buttonsTemplate = ButtonsTemplate(
        title="NBA猜一猜",
        text="生涯資料猜球員",
        actions=[
            MessageAction(label="生涯球隊", text=f"生涯球隊\n{historyTeams}"),
            MessageAction(label="上場時間", text=f"上場時間\n{historyGame}"),
            MessageAction(label="賽季平均", text=f"賽季平均\n{historyStats}"),
            MessageAction(label="看答案", text=f"答案是 {playerInfo['name']}"),
        ],
    )
    return usage, buttonsTemplate


def get_hupu_news():
    url = "https://bbs.hupu.com/4860"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0 Safari/537.36",
        "Referer": "https://bbs.hupu.com/",
    }
    data = requests.get(url, headers=headers)

    soup = BeautifulSoup(data.text, "html.parser")

    newsThread = soup.find_all("a", class_="p-title")
    top5News = []
    for news in newsThread[:5]:
        title = news.get_text(strip=True)
        top5News.append(title.replace("[流言板]", ""))

    spliter = "\n" + "-" * 53 + "\n"
    return spliter.join(top5News)


def get_youtube(keyword: str):
    data = requests.get(f"https://www.youtube.com/results?search_query={keyword}").text
    titlePattern = re.compile(r'"videoRenderer".*?"label":"(.*?)"')
    videoIdPattern = re.compile(r'"videoRenderer":{"videoId":"(.*?)"')

    titleList = titlePattern.findall(data)
    videoIdList = videoIdPattern.findall(data)

    for title, videoId in zip(titleList, videoIdList):
        videoUrl = f"https://www.youtube.com/watch?v={videoId}"
        response = title + "\n" + videoUrl
        return response


def get_google_image(keyword: str):
    data = requests.get(f"https://www.google.com/search?q={keyword}&tbm=isch").text
    soup = BeautifulSoup(data, "html.parser")
    imgSrc = soup.find("img", class_="DS1iW")["src"]
    return requests.get(imgSrc).status_code, imgSrc


def get_textfile(filePath: str):
    with open(filePath, encoding="utf-8") as f:
        content = f.read()
    return content


def get_textfile_random(filePath: str):
    with open(filePath, encoding="utf-8") as f:
        fileLines = f.readlines()
    return random.choice(fileLines).replace("\n", "")


def get_random_image(imgKey: str):
    imageUrls = get_image_url(imgKey=imgKey)
    return random.choice(imageUrls)[0]


def get_nba_scoreboard():
    data = requests.get("https://nba.hupu.com/games").text
    soup = BeautifulSoup(data, "html.parser")

    gameCenter = soup.find("div", class_="gamecenter_content_l")
    gameContainers = gameCenter.find_all("div", class_="list_box")

    gameStrList = []
    gameScores = {}
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

        team1Score = team2Score = ""

        gameStatus = gameContainer.find("div", class_="team_vs").text
        if "进行中" in gameStatus:
            team1Score = team1.find("div", class_="txt").find("span", class_="num").text
            team2Score = team2.find("div", class_="txt").find("span", class_="num").text
            gameTime = (
                gameContainer.find("div", class_="team_vs_c")
                .find("span", class_="b")
                .find("p")
                .text
            )
        elif "未开始" in gameStatus:
            gameTime = (
                gameContainer.find("div", class_="team_vs_b")
                .find("span", class_="b")
                .find("p")
                .text
            )
            if gameTime == "00:00":
                gameTime = "12:00"
        elif "已结束" in gameStatus:
            gameTime = "Finish"
            team1Win = team1.find("div", class_="txt").find("span", class_="num red")
            if team1Win:
                team1Score = team1Win.text
                team2Score = (
                    team2.find("div", class_="txt").find("span", class_="num").text
                )
            else:
                team1Score = (
                    team1.find("div", class_="txt").find("span", class_="num").text
                )
                team2Score = (
                    team2.find("div", class_="txt").find("span", class_="num red").text
                )

        gameStrList.append(
            f"{team1Name} {team1Score} - {team2Name} {team2Score} ({gameTime})"
        )
        gameScores[(team1Name, team2Name)] = (
            int(team1Score) if team1Score else 0,
            int(team2Score) if team2Score else 0,
        )

    update_daily_match_score(gameScores=gameScores)
    return "\n".join(gameStrList)


def get_team_injury(teamName: str):
    if teamName not in NBA_TRAD_CN_TO_CBS:
        return "使用方式: 傷病 球隊"

    response = requests.get("https://www.cbssports.com/nba/injuries/")
    soup = BeautifulSoup(response.text, "html.parser")
    teamContainers = soup.find_all("div", class_="TableBaseWrapper")

    teamInjury = {cbsTeamName: [] for cbsTeamName in NBA_TRAD_CN_TO_CBS.values()}
    for teamContainer in teamContainers:
        cbsTeamName = teamContainer.find("span", class_="TeamName").text.strip()
        teamInjury[cbsTeamName] = []

        injuredPlayers = (
            teamContainer.find("table", class_="TableBase-table")
            .find("tbody")
            .find_all("tr", class_="TableBase-bodyTr")
        )
        for injuredPlayer in injuredPlayers:
            playerInfo = injuredPlayer.find_all("td")
            playerName = (
                playerInfo[0].find("span", class_="CellPlayerName--long").text.strip()
            )
            injuryStatus = playerInfo[4].text.strip()
            teamInjury[cbsTeamName].append(f"{playerName}: {injuryStatus}")

    if len(teamInjury[NBA_TRAD_CN_TO_CBS[teamName]]) == 0:
        return f"{teamName} 沒有任何傷病"
    spliter = "\n" + "-" * 53 + "\n"
    return spliter.join(teamInjury[NBA_TRAD_CN_TO_CBS[teamName]])


def get_imgur_url(albumHash: str):
    endPoint = f"https://api.imgur.com/3/album/{albumHash}/images"
    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
    response = requests.get(endPoint, headers=headers)
    if response.status_code == 200:
        data = response.json()
        images = data["data"]
        if images:
            randomImage = random.choice(images)
            imageUrl = randomImage["link"]
            return imageUrl
