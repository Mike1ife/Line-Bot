"""ESPN NBA JSON client.

ESPN publishes undocumented but stable JSON at site.api.espn.com with no API key.
Preferred over scraping Fox/Hupu HTML because it is not tied to CSS class names,
and over cdn.nba.com because that host is Akamai-blocked for datacenter IPs.
"""

import random
import requests
from datetime import datetime, timezone, timedelta

from utils._team_table import NBA_ABBR_ENG_TO_ABBR_CN

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
TIMEOUT = 15

# ESPN spells six teams differently from NBA_ABBR_ENG_TO_ABBR_CN. Without this the
# lookups silently skip those teams' games.
ESPN_ABBR_ALIAS = {
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
    "UTAH": "UTA",
    "WSH": "WAS",
}

# Column labels in the ESPN boxscore player table, mapped to the bot's stat types.
ESPN_STAT_LABEL = {"得分": "PTS", "籃板": "REB", "抄截": "STL"}


def espn_abbr_to_cn(abbr: str):
    """ESPN team abbreviation -> Traditional Chinese short name, or None."""
    return NBA_ABBR_ENG_TO_ABBR_CN.get(ESPN_ABBR_ALIAS.get(abbr, abbr))


def espn_date_for_tw_date(twDate: str):
    """Taiwan game date -> ESPN (US Eastern) game date.

    NBA games tip in the US evening, so an ET game day always lands on the next
    calendar day in Taiwan (UTC+8): ET 19:30 -> TW 08:30 tomorrow. The bot
    stores the Taiwan date, ESPN indexes the Eastern date, so the offset is -1.
    """
    return (datetime.strptime(twDate, "%Y-%m-%d") - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )


def tw_date_for_espn_date(espnDate: str):
    """Inverse of espn_date_for_tw_date."""
    return (datetime.strptime(espnDate, "%Y-%m-%d") + timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )


def _get(path: str, params: dict = None):
    response = requests.get(f"{BASE}/{path}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_scoreboard(espnDate: str):
    """espnDate is YYYY-MM-DD in **US Eastern**, which is how ESPN indexes a
    game day. This is NOT the Taiwan date the bot stores in match.game_date -
    use espn_date_for_tw_date() to convert. Returns a list of game dicts."""
    data = _get("scoreboard", {"dates": espnDate.replace("-", "")})

    games = []
    for event in data.get("events", []):
        competition = event["competitions"][0]
        competitors = competition["competitors"]

        away = next((c for c in competitors if c["homeAway"] == "away"), None)
        home = next((c for c in competitors if c["homeAway"] == "home"), None)
        if not away or not home:
            continue

        awayName = espn_abbr_to_cn(away["team"]["abbreviation"])
        homeName = espn_abbr_to_cn(home["team"]["abbreviation"])
        if not awayName or not homeName:
            continue

        games.append(
            {
                "eventId": event["id"],
                "state": event["status"]["type"]["state"],  # pre / in / post
                "completed": event["status"]["type"]["completed"],
                "startUTC": event["date"],
                "awayName": awayName,
                "homeName": homeName,
                "awayScore": int(away["score"]) if away.get("score") else 0,
                "homeScore": int(home["score"]) if home.get("score") else 0,
            }
        )

    return games


def get_boxscore(eventId: str):
    """Returns {playerName: {"得分": int, "籃板": int, "抄截": int, "team": str}}."""
    data = _get("summary", {"event": eventId})

    playerStats = {}
    for group in data.get("boxscore", {}).get("players", []):
        teamName = espn_abbr_to_cn(group["team"]["abbreviation"])
        for block in group.get("statistics", []):
            labels = block.get("labels", [])
            index = {
                statType: labels.index(label)
                for statType, label in ESPN_STAT_LABEL.items()
                if label in labels
            }
            if len(index) != len(ESPN_STAT_LABEL):
                continue

            for athlete in block.get("athletes", []):
                stats = athlete.get("stats") or []
                if len(stats) <= max(index.values()):
                    continue  # DNP rows carry an empty stat list

                entry = {"team": teamName}
                for statType, position in index.items():
                    try:
                        entry[statType] = int(stats[position])
                    except ValueError:
                        entry = None
                        break
                if entry:
                    playerStats[athlete["athlete"]["displayName"]] = entry

    return playerStats


def random_past_game_date(maxTries: int = 12):
    """Pick a random date from the last NBA season that actually had games."""
    nowTW = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

    # The season spans roughly late October to mid June of the following year.
    endYear = nowTW.year if nowTW.month >= 10 else nowTW.year - 1
    seasonStart = datetime(endYear, 10, 25)
    seasonEnd = min(datetime(endYear + 1, 6, 15), nowTW.replace(tzinfo=None))
    if seasonEnd <= seasonStart:
        seasonStart = datetime(endYear - 1, 10, 25)
        seasonEnd = datetime(endYear, 6, 15)

    span = (seasonEnd - seasonStart).days
    for _ in range(maxTries):
        espnDate = (seasonStart + timedelta(days=random.randint(0, span))).strftime(
            "%Y-%m-%d"
        )
        games = [g for g in get_scoreboard(espnDate) if g["completed"]]
        if games:
            # Report the Taiwan date so every date the bot shows means the same thing.
            return tw_date_for_espn_date(espnDate), games

    return None, []


def find_event_id(twGameDate: str, team1Name: str, team2Name: str):
    """Resolve an ESPN event id from a Taiwan game date and two Chinese names.

    Tries the correct Eastern date first; the Taiwan date itself is only a
    safety net for oddly-scheduled games (e.g. international tip-offs) that do
    not follow the usual -1 offset.
    """
    wanted = {team1Name, team2Name}
    for candidate in (espn_date_for_tw_date(twGameDate), twGameDate):
        for game in get_scoreboard(candidate):
            if {game["awayName"], game["homeName"]} == wanted:
                return game["eventId"]
    return None


def get_event_map(twGameDate: str):
    """Map the slate for one Taiwan game date to ESPN ids and real tip-off times.

    Returns {frozenset({teamA, teamB}): (eventId, tipoffUTC)}. One request covers
    the whole slate. Returns {} rather than raising if ESPN is unreachable, so
    slate creation degrades to NULL columns instead of failing outright.
    """
    events = {}
    try:
        games = get_scoreboard(espn_date_for_tw_date(twGameDate))
    except Exception:
        return events

    for game in games:
        try:
            tipoffUTC = datetime.fromisoformat(game["startUTC"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            tipoffUTC = None
        events[frozenset((game["awayName"], game["homeName"]))] = (
            game["eventId"],
            tipoffUTC,
        )
    return events
