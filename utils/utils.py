import json
import random
from urllib.parse import quote
from utils._user_table import *
from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN
from linebot.models import (
    CarouselColumn,
    PostbackAction,
    ButtonsTemplate,
    MessageAction,
)

ACCESS_TOKEN = "a93827221b1aaca669344e401c8375c6ccdd5ef4"
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
    userPoints = get_user_points(rankType=rankType)
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

    userNextPoints = get_user_points(rankType=NEXT_RANK_TYPE[rankType])
    rankMessage = f"{RANK_TYPE_TRANSLATION[NEXT_RANK_TYPE[rankType]]}排行榜:\n"
    for i, (name, point) in enumerate(userNextPoints, 1):
        rankMessage += f"{i}. {name}: {point}分\n"

    return bestMessage, rankMessage


def get_user_most_correct(userName: str, teamName: str = "", correct: bool = True):
    teamList = list(NBA_ABBR_ENG_TO_ABBR_CN.values())
    correctList = get_user_correct(
        userName=userName, teamList=teamList, correct=correct
    )
    if not teamName:
        mostCorrectTeam = list(correctList.keys())[0]
        if correct:
            return f"{userName}是{mostCorrectTeam}的舔狗"
        else:
            return f"{userName}的傻鳥是{mostCorrectTeam}"

    if teamName not in teamList:
        return f"{teamName} is unknown"

    if correct:
        return f"{userName}舔了{teamName}{correctList[teamName]}口"
    else:
        return f"{userName}被{teamName}肛了{correctList[teamName]}次"


def settle_most_correct_wrong():
    teamList = list(NBA_ABBR_ENG_TO_ABBR_CN.values())
    response = settle_user_correct(teamList=teamList)
    return response


def user_registration(userName: str, userUID: str):
    response = add_user(userName=userName, userUID=userUID)
    return response


def get_user_prediction_check(userName: str):
    return userName + check_user_prediction(userName)


def get_prediction_by_id(userId: int):
    response = get_user_prediction(userId)
    return response


def get_prediction_comparison(user1Id: int, user2Id: int):
    response = compare_user_prediction(user1Id, user2Id)
    return response


def settle_daily_prediction(playoffsLayout: bool):
    """TODO playoffs layout"""
    settle_daily_game_stats(playoffsLayout=playoffsLayout)
    dailyResult = calculate_user_daily_points()

    response = "\n".join(
        [f"{RANK_TYPE_TRANSLATION['week_points']}排行榜:"]
        + [
            f"{i}. {name}: {point}分 (+{plus})"
            for i, (name, point, plus) in enumerate(dailyResult, 1)
        ]
    )
    return response


def _check_url_exist(url: str):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def _pack_game_carousel_column(game: dict, playoffsLayout: bool, tomorrowTW: datetime):
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
                data=f"NBA球隊預測;{teamNames[0]};{teamNames[1]};{teamPoints[0]};{teamPoints[1]};{tomorrowTW.year}-{tomorrowTW.month}-{tomorrowTW.day}-{gameTime}",
            ),
            PostbackAction(
                label=teamNames[1],
                data=f"NBA球隊預測;{teamNames[1]};{teamNames[0]};{teamPoints[1]};{teamPoints[0]};{tomorrowTW.year}-{tomorrowTW.month}-{tomorrowTW.day}-{gameTime}",
            ),
        ],
    )
    return carouselColumn


def get_nba_game_prediction(playoffsLayout: bool = False):
    reset_nba_prediction()
    response = get_user_type_point(rankType="week_points")

    newTableColumns = []
    carouselColumns = []

    gameList, gameOfTheDayPage, gameOfTheDayTime = get_nba_games(
        playoffsLayout=playoffsLayout
    )

    if len(gameList) == 0:
        return "明天沒有比賽", None, None, None

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    tomorrowTW = nowTW + timedelta(days=1)

    for game in gameList:
        carouselColumn = _pack_game_carousel_column(
            game=game, playoffsLayout=playoffsLayout, tomorrowTW=tomorrowTW
        )
        carouselColumns.append(carouselColumn)

        teamNames = game["names"]
        teamPoints = game["points"]
        newTableColumns.append(
            f"{teamNames[0]}-{teamNames[1]} {teamPoints[0]}/{teamPoints[1]}"
        )

    insert_columns(newColumns=newTableColumns)
    return response, carouselColumns, gameOfTheDayPage, gameOfTheDayTime


def _compare_timestring(timeStr1: str, timeStr2: str):
    format = "%Y-%m-%d-%H:%M"

    return datetime.strptime(timeStr1, format) > datetime.strptime(timeStr2, format)


def get_nba_prediction_posback(
    userName: str,
    winner: str,
    loser: str,
    winnerPoint: str,
    loserPoint: str,
    gameTime: str,
):
    if not user_exist(userName=userName):
        return f"{userName} 請先註冊"

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    nowTime = f"{nowTW.year}-{nowTW.month}-{nowTW.day}-{nowTW.hour}:{nowTW.minute}"

    if _compare_timestring(timeStr1=nowTime, timeStr2=gameTime):
        return f"{winner}-{loser} 的比賽已經開始了"

    column = f"{winner}-{loser} {winnerPoint}/{loserPoint}"
    if not column_exist(column=column):
        column = f"{loser}-{winner} {loserPoint}/{winnerPoint}"

    if user_predicted(userName=userName, column=column):
        return f"{userName}已經預測{winner}-{loser}了"

    update_columns(
        updateColumns=[column], updateStrategy=["w"], updateMap={userName: [winner]}
    )
    return f"{userName}預測{winner}贏{loser}"


def _get_game_translation(gameDescription: str):
    awayTeam, _, homeTeam, _, _, _ = gameDescription.split()
    return f"{NBA_ABBR_ENG_TO_ABBR_CN[awayTeam]} @ {NBA_ABBR_ENG_TO_ABBR_CN[homeTeam]}"


def _get_player_bet_info(playerSoup: BeautifulSoup, betTitle: str):
    imgSrc = playerSoup.find("img").get("src")
    playerName = playerSoup.find("img").get("alt")
    gameDescription = playerSoup.find("div", class_="ffn-gr-11").text

    with open("utils/player_link.json", "r", encoding="utf-8") as f:
        playerUrlMap = json.load(f)

    playerStatsUrl = playerUrlMap[playerName] + "-stats"
    playerStatsPage = requests.get(playerStatsUrl).text
    playerStatsSoup = BeautifulSoup(playerStatsPage, "html.parser")
    betTitleToContainerIndex = {
        "PLAYER POINTS": 0,
        "PLAYER REBOUNDS": 1,
        "PLAYER STEALS": 4,
    }

    playerStats = playerStatsSoup.find_all("a", class_="stats-overview")
    statContainer = playerStats[betTitleToContainerIndex[betTitle]]

    statAvg = statContainer.find("div", class_="fs-54 fs-sm-40").text
    statTarget = playerSoup.find("div", class_="fs-30").text

    _odds_msg = (
        playerSoup.find("span", class_="pd-r-2").text
        + " "
        + playerSoup.find("span", class_="cl-og").text
    )
    _odds_items = _odds_msg.split()
    odds = (int(_odds_items[4][1:]) - int(_odds_items[1][1:])) // 2

    return (
        imgSrc,
        playerName,
        _get_game_translation(gameDescription=gameDescription),
        statAvg.split()[0],
        statTarget,
        int(1.5 * odds),
    )


def _pack_stat_carousel_column(
    playerSoup: BeautifulSoup, betTitle: str, gameTime: str, tomorrowTW: datetime
):
    imgSrc, playerName, gameTitle, statAvg, statTarget, odds = _get_player_bet_info(
        playerSoup=playerSoup, betTitle=betTitle
    )
    betTitleCN = BET_STAT_TRANSLATION[betTitle]
    # title = Anthony Edwards
    # text = 場均得分 28.0\n7:00 國王(客) - 灰狼(主)\n大盤 (得分超過 26.5) 4分 / 小盤 (得分低於 26.5) 6分
    # button1 = 大盤
    # button2 = 小盤

    carouselColumn = CarouselColumn(
        thumbnail_image_url=imgSrc,
        title=playerName,
        text=f"場均{betTitleCN} {statAvg}\n{gameTime} {gameTitle}\n大盤 ({betTitleCN}超過{statTarget}) {odds}分\n小盤 ({betTitleCN}低於{statTarget}) {15-odds}分",
        actions=[
            PostbackAction(
                label="大盤",
                data=f"NBA球員預測;{playerName};{betTitleCN}{statTarget};{odds};{15-odds};大盤;{tomorrowTW.year}-{tomorrowTW.month}-{tomorrowTW.day}-{gameTime}",
            ),
            PostbackAction(
                label="小盤",
                data=f"NBA球員預測;{playerName};{betTitleCN}{statTarget};{odds};{15-odds};小盤;{tomorrowTW.year}-{tomorrowTW.month}-{tomorrowTW.day}-{gameTime}",
            ),
        ],
    )
    newTableColumn = f"{playerName} {betTitleCN}{statTarget} {odds}/{15-odds}"
    return carouselColumn, newTableColumn


def get_player_stat_prediction(gamePage: str, gameTime: str):
    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    tomorrowTW = nowTW + timedelta(days=1)

    data = requests.get(gamePage).text
    soup = BeautifulSoup(data, "html.parser")
    betContainer = soup.find_all("div", class_="odds-component-prop-bet")

    newTableColumns = []
    carouselColumns = []

    for betInfo in betContainer:
        # PLAYER POINTS / PLAYER REBOUNDS / PLAYER STEAL
        betTitle = betInfo.find("h2", class_="pb-name fs-30").text.strip()
        playerContainers = betInfo.find_all(
            "div", class_="prop-bet-data pointer prop-future"
        )
        for playerSoup in playerContainers:
            carouselColumn, newTableColumn = _pack_stat_carousel_column(
                playerSoup=playerSoup,
                betTitle=betTitle,
                gameTime=gameTime,
                tomorrowTW=tomorrowTW,
            )

            newTableColumns.append(newTableColumn)
            carouselColumns.append(carouselColumn)

    insert_columns(newColumns=newTableColumns)
    return carouselColumns


def get_player_stat_prediction_postback(
    userName: str,
    player: str,
    targetStat: str,
    overPoint: str,
    UnderPoint: str,
    userPrediction: str,
    gameTime: str,
):
    if not user_exist(userName=userName):
        return f"{userName} 請先註冊"

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    nowTime = f"{nowTW.year}-{nowTW.month}-{nowTW.day}-{nowTW.hour}:{nowTW.minute}"

    if _compare_timestring(timeStr1=nowTime, timeStr2=gameTime):
        return f"{player} 的比賽已經開始了"

    # # Anthony Edwards 得分26.5 4/6
    column = f"{player} {targetStat} {overPoint}/{UnderPoint}"

    if user_predicted(userName=userName, column=column):
        return f"{userName}已經預測{player}{targetStat[:2]}超過(低於){targetStat[2:]}了"

    update_columns(
        updateColumns=[column],
        updateStrategy=["w"],
        updateMap={userName: [f"{player} {userPrediction}"]},
    )

    if userPrediction == "大盤":
        return f"{userName}預測{player}{targetStat[:2]}超過{targetStat[2:]}"
    if userPrediction == "小盤":
        return f"{userName}預測{player}{targetStat[:2]}低於{targetStat[2:]}"


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
        title="Menu",
        text="Please select",
        actions=[
            MessageAction(label="生涯球隊", text=f"生涯球隊\n{historyTeams}"),
            MessageAction(label="上場時間", text=f"上場時間\n{historyGame}"),
            MessageAction(label="賽季平均", text=f"賽季平均\n{historyStats}"),
            MessageAction(label="看答案", text=f"答案是 {playerInfo['name']}"),
        ],
    )
    return usage, buttonsTemplate


def get_hupu_news():
    data = requests.get("https://bbs.hupu.com/4860").text
    soup = BeautifulSoup(data, "html.parser")

    newsThread = soup.find_all("a", class_="p-title")
    top5News = []
    for news in newsThread[:5]:
        title = news.text.strip()
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


def get_random_imgur(albumId: str):
    imgurUrl = f"https://api.imgur.com/3/album/{albumId}/images"
    response = requests.get(imgurUrl, {"Authorization": f"Bearer {ACCESS_TOKEN}"})
    if response.status_code == 200:
        data = response.json()
        imgList = data["data"]
        if imgList:
            return random.choice(imgList)["link"]


def get_nba_scoreboard():
    pass


def get_team_injury(teamName: str):
    pass


def get_nba_prediction_demo():
    reset_nba_prediction()
    response = get_user_type_point(rankType="week_points")

    newTableColumns = []
    carouselColumns = []

    nowUTC = datetime.now(timezone.utc)
    nowTW = nowUTC.astimezone(timezone(timedelta(hours=8)))
    tomorrowTW = nowTW + timedelta(days=1)
    gameList = [
        {
            "names": ["勇士", "湖人"],
            "standings": ["73-9", "50-22"],
            "points": [30, 30],
            "gametime": "08:00",
        },
        {
            "names": ["塞爾提克", "公牛"],
            "standings": ["73-9", "50-22"],
            "points": [25, 28],
            "gametime": "09:30",
        },
        {
            "names": ["熱火", "尼克"],
            "standings": ["73-9", "50-22"],
            "points": [32, 27],
            "gametime": "07:00",
        },
        {
            "names": ["太陽", "快艇"],
            "standings": ["73-9", "50-22"],
            "points": [29, 33],
            "gametime": "10:00",
        },
        {
            "names": ["公鹿", "溜馬"],
            "standings": ["73-9", "50-22"],
            "points": [35, 22],
            "gametime": "06:30",
        },
        {
            "names": ["灰熊", "雷霆"],
            "standings": ["73-9", "50-22"],
            "points": [28, 30],
            "gametime": "11:00",
        },
        {
            "names": ["拓荒者", "國王"],
            "standings": ["73-9", "50-22"],
            "points": [20, 19],
            "gametime": "05:00",
        },
        {
            "names": ["騎士", "籃網"],
            "standings": ["73-9", "50-22"],
            "points": [26, 30],
            "gametime": "08:30",
        },
        {
            "names": ["獨行俠", "馬刺"],
            "standings": ["73-9", "50-22"],
            "points": [31, 28],
            "gametime": "07:30",
        },
        {
            "names": ["金塊", "鵜鶘"],
            "standings": ["73-9", "50-22"],
            "points": [33, 29],
            "gametime": "09:00",
        },
    ]

    for game in gameList:
        carouselColumn = _pack_game_carousel_column(
            game=game, playoffsLayout=False, tomorrowTW=tomorrowTW
        )
        carouselColumns.append(carouselColumn)

        teamNames = game["names"]
        teamPoints = game["points"]
        newTableColumns.append(
            f"{teamNames[0]}-{teamNames[1]} {teamPoints[0]}/{teamPoints[1]}"
        )

    insert_columns(newColumns=newTableColumns)
    return response, carouselColumns
