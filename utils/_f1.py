"""Formula 1 client, backed by the Jolpica and OpenF1 APIs.

Jolpica (api.jolpi.ca) is the community-run successor to Ergast, which was shut
down and now returns 404. It supplies the calendar and standings. ESPN is
deliberately not used here: its F1 scoreboard carries no competitors and its
standings endpoint returns an empty stub.

OpenF1 (api.openf1.org) supplies what Jolpica never had: practice results,
3-letter driver codes and in-session timing for f1 live. Its sessions are
matched to Jolpica's by start time.

Every session comes with an explicit UTC timestamp. That matters more than it
does for the NBA: F1 races land on Saturday, Sunday or Monday in Taiwan
depending on the venue, so there is no fixed date offset to rely on.
"""

import requests
from datetime import datetime, timezone, timedelta

BASE = "https://api.jolpi.ca/ergast/f1"
OPENF1 = "https://api.openf1.org/v1"
TIMEOUT = 15
TW = timezone(timedelta(hours=8))
WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]

# Ordered by how a weekend actually runs; the race is handled separately
# because Jolpica puts it on the race object rather than in a sub-object.
SESSION_KEYS = [
    ("FirstPractice", "一練"),
    ("SecondPractice", "二練"),
    ("ThirdPractice", "三練"),
    ("SprintQualifying", "衝刺排位"),
    ("Sprint", "衝刺賽"),
    ("Qualifying", "排位賽"),
]

# OpenF1 session_name -> the same labels, for f1 live.
OPENF1_SESSION_CN = {
    "Practice 1": "一練",
    "Practice 2": "二練",
    "Practice 3": "三練",
    "Sprint Qualifying": "衝刺排位",
    "Sprint Shootout": "衝刺排位",
    "Sprint": "衝刺賽",
    "Qualifying": "排位賽",
    "Race": "正賽",
}

GP_NAME_CN = {
    "Australian": "澳洲", "Chinese": "中國", "Japanese": "日本",
    "Miami": "邁阿密", "Canadian": "加拿大", "Monaco": "摩納哥",
    "Barcelona": "巴塞隆納", "Austrian": "奧地利", "British": "英國",
    "Belgian": "比利時", "Hungarian": "匈牙利", "Dutch": "荷蘭",
    "Italian": "義大利", "Spanish": "西班牙", "Azerbaijan": "亞塞拜然",
    "Singapore": "新加坡", "United States": "美國", "Mexico City": "墨西哥",
    "Brazilian": "巴西", "Las Vegas": "拉斯維加斯", "Qatar": "卡達",
    "Abu Dhabi": "阿布達比", "Bahrain": "巴林", "Saudi Arabian": "沙烏地阿拉伯",
    "Emilia Romagna": "伊莫拉", "French": "法國", "Portuguese": "葡萄牙",
    "Mexican": "墨西哥", "Sao Paulo": "聖保羅",
}

# The calendar changes at most a few times a season, so a warm instance should
# not re-fetch it on every command.
_CACHE_TTL = timedelta(hours=6)
_cache = {"fetchedAt": None, "races": None}


def _parse_utc(dateStr: str, timeStr: str):
    if not dateStr or not timeStr:
        return None
    try:
        return datetime.fromisoformat(f"{dateStr}T{timeStr.replace('Z', '+00:00')}")
    except ValueError:
        return None


def translate_gp(raceName: str):
    head, _, tail = raceName.partition("Grand Prix")
    chinese = GP_NAME_CN.get(head.strip())
    name = f"{chinese}大獎賽" if chinese else raceName
    tail = tail.strip()
    return f"{name} {tail}" if tail else name


def get_season_races(force: bool = False):
    """Full calendar for the current season, cached."""
    now = datetime.now(timezone.utc)
    if (
        not force
        and _cache["races"]
        and _cache["fetchedAt"]
        and now - _cache["fetchedAt"] < _CACHE_TTL
    ):
        return _cache["races"]

    response = requests.get(f"{BASE}/current/races/?format=json", timeout=TIMEOUT)
    response.raise_for_status()
    table = response.json()["MRData"]["RaceTable"]

    races = []
    for raw in table.get("Races", []):
        raceUTC = _parse_utc(raw.get("date"), raw.get("time"))
        if not raceUTC:
            continue

        sessions = []
        for key, label in SESSION_KEYS:
            block = raw.get(key)
            if not block:
                continue
            startUTC = _parse_utc(block.get("date"), block.get("time"))
            if startUTC:
                sessions.append((label, startUTC))
        sessions.append(("正賽", raceUTC))
        sessions.sort(key=lambda item: item[1])

        location = raw["Circuit"]["Location"]
        races.append(
            {
                "season": table.get("season"),
                "round": raw["round"],
                "name": translate_gp(raw["raceName"]),
                "circuit": raw["Circuit"]["circuitName"],
                "locality": location.get("locality", ""),
                "country": location.get("country", ""),
                "raceUTC": raceUTC,
                "sessions": sessions,
                "isSprint": any(label == "衝刺賽" for label, _ in sessions),
            }
        )

    races.sort(key=lambda r: r["raceUTC"])
    _cache.update({"fetchedAt": now, "races": races})
    return races


def get_current_weekend():
    """The race weekend to show: the next race, or the one that just ran until a
    day after its start so its podium stays visible. None once the season is over."""
    now = datetime.now(timezone.utc)
    for race in get_season_races():
        if race["raceUTC"] + RACE_SHOWN_AFTER > now:
            return race
    return None


# Race start to "本站已結束": long enough for any race plus a red flag.
RACE_DURATION = timedelta(hours=3)
RACE_SHOWN_AFTER = timedelta(days=1)

# Labels whose results are shown as a podium, and those shown as a pole time.
PODIUM_SESSIONS = ("衝刺賽", "正賽")
POLE_SESSIONS = ("衝刺排位", "排位賽")

_openf1Cache = {"sessions": {}, "drivers": {}, "results": {}}


def _openf1(query: str):
    """GET an OpenF1 endpoint. query carries OpenF1's own filter syntax
    (e.g. "position<=3"), so it is passed through rather than via params."""
    response = requests.get(f"{OPENF1}/{query}", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def _cached(bucket: str, key, fetch):
    entry = _openf1Cache[bucket].get(key)
    now = datetime.now(timezone.utc)
    if entry and now - entry[0] < _CACHE_TTL:
        return entry[1]
    value = fetch()
    # Empty means "not published yet" (e.g. a session just ended), so ask again next time.
    if value:
        _openf1Cache[bucket][key] = (now, value)
    return value


def _openf1_sessions(year):
    return _cached("sessions", year, lambda: _openf1(f"sessions?year={year}"))


def _driver_codes(meetingKey):
    """driver_number -> 3-letter code for one race weekend."""
    return _cached(
        "drivers",
        meetingKey,
        lambda: {
            driver["driver_number"]: driver["name_acronym"]
            for driver in _openf1(f"drivers?meeting_key={meetingKey}")
        },
    )


def _session_top(session, count: int):
    """Top `count` classified rows of a finished OpenF1 session as
    [{"code", "duration", "gap"}]; duration/gap are lists in qualifying."""

    def fetch():
        rows = _openf1(
            f"session_result?session_key={session['session_key']}&position<={count}"
        )
        rows = sorted(
            (row for row in rows if isinstance(row.get("position"), int)),
            key=lambda row: row["position"],
        )
        codes = _driver_codes(session["meeting_key"])
        return [
            {
                "code": codes.get(row["driver_number"], str(row["driver_number"])),
                "duration": row.get("duration"),
                "gap": row.get("gap_to_leader"),
            }
            for row in rows[:count]
        ]

    return _cached("results", session["session_key"], fetch)


def get_weekend_results(race: dict):
    """{session label: top-3 rows} for every session of this weekend that has
    ended and been classified. Sessions without results are left out."""
    now = datetime.now(timezone.utc)
    openf1Sessions = _openf1_sessions(race["raceUTC"].year)

    results = {}
    for label, startUTC in race["sessions"]:
        if startUTC > now:
            continue
        # Same session in OpenF1: the one starting within the hour.
        match = next(
            (
                session
                for session in openf1Sessions
                if abs(datetime.fromisoformat(session["date_start"]) - startUTC)
                <= timedelta(hours=1)
            ),
            None,
        )
        if not match or datetime.fromisoformat(match["date_end"]) > now:
            continue
        top = _session_top(match, count=3)
        if top:
            results[label] = top
    return results


def get_standings():
    """(round, drivers, constructors) after the latest race, where drivers is
    [(position, code, points)] and constructors [(position, name, points)]."""
    drivers = requests.get(
        f"{BASE}/current/driverStandings/?format=json", timeout=TIMEOUT
    )
    drivers.raise_for_status()
    constructors = requests.get(
        f"{BASE}/current/constructorStandings/?format=json", timeout=TIMEOUT
    )
    constructors.raise_for_status()

    driverLists = drivers.json()["MRData"]["StandingsTable"]["StandingsLists"]
    constructorLists = constructors.json()["MRData"]["StandingsTable"]["StandingsLists"]
    if not driverLists:
        return None, [], []
    return (
        driverLists[0]["round"],
        [
            (row["position"], row["Driver"].get("code") or row["Driver"]["familyName"], row["points"])
            for row in driverLists[0]["DriverStandings"]
        ],
        [
            (row["position"], row["Constructor"]["name"], row["points"])
            for row in (constructorLists[0]["ConstructorStandings"] if constructorLists else [])
        ],
    )


def _track_status(messages: list):
    """Current track status from race control: SC / VSC / red / chequered, or
    None while green. Replays the messages in order so ENDING clears a deploy."""
    status = None
    for message in sorted(messages, key=lambda m: m["date"]):
        text = (message.get("message") or "").upper()
        if message["category"] == "SafetyCar":
            if "ENDING" in text or "IN THIS LAP" in text:
                status = None
            elif "VSC" in text or "VIRTUAL" in text:
                status = "🟡 VSC"
            elif "DEPLOYED" in text:
                status = "🟡 SC"
        elif message["category"] == "Flag" and message.get("scope") == "Track":
            flag = message.get("flag")
            if flag == "RED":
                status = "🔴 紅旗"
            elif flag == "CHEQUERED":
                status = "🏁"
            elif flag in ("GREEN", "CLEAR"):
                status = None
    return status


def get_live_snapshot(count: int = 5):
    """What f1 live shows for OpenF1's latest session.

    Returns {"session", "state", "lap", "status", "top": [(code, gap)]} where
    state is "pre", "live" or "post". Raises requests.HTTPError, which is how
    OpenF1 answers when live data needs an account.
    """
    session = _openf1("sessions?session_key=latest")[0]
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(session["date_start"])
    end = datetime.fromisoformat(session["date_end"])
    snapshot = {"session": session, "lap": None, "status": None, "top": []}
    if now < start:
        snapshot["state"] = "pre"
        return snapshot
    # A little past the scheduled end, since sessions overrun.
    snapshot["state"] = "post" if now > end + timedelta(minutes=30) else "live"
    if snapshot["state"] == "post":
        return snapshot

    key = session["session_key"]
    # Position rows are only written on a change, so the latest per driver wins.
    latest = {}
    for row in sorted(_openf1(f"position?session_key={key}"), key=lambda r: r["date"]):
        latest[row["driver_number"]] = row["position"]
    order = sorted(latest, key=latest.get)[:count]

    # Intervals stream every few seconds during races; a recent window has everyone.
    since = (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
    gaps = {}
    try:
        for row in sorted(
            _openf1(f"intervals?session_key={key}&date>={since}"), key=lambda r: r["date"]
        ):
            gaps[row["driver_number"]] = row.get("gap_to_leader")
    except requests.HTTPError:
        pass  # not published outside races

    # A lap count only means something when everyone runs the same distance.
    if order and session["session_name"] in ("Race", "Sprint"):
        laps = _openf1(f"laps?session_key={key}&driver_number={order[0]}")
        snapshot["lap"] = max((lap["lap_number"] for lap in laps), default=None)

    snapshot["status"] = _track_status(_openf1(f"race_control?session_key={key}"))
    codes = _driver_codes(session["meeting_key"])
    snapshot["top"] = [(codes.get(number, str(number)), gaps.get(number)) for number in order]
    return snapshot


def format_tw(momentUTC: datetime):
    """UTC -> '09/26 (六) 19:00' in Taiwan time."""
    local = momentUTC.astimezone(TW)
    return f"{local:%m/%d} ({WEEKDAY_CN[local.weekday()]}) {local:%H:%M}"


def countdown_to(momentUTC: datetime):
    """Human gap from now until momentUTC, or None if it has passed."""
    delta = momentUTC - datetime.now(timezone.utc)
    if delta.total_seconds() <= 0:
        return None
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if days:
        return f"{days}天 {hours}小時"
    if hours:
        return f"{hours}小時 {minutes}分"
    return f"{minutes}分"
