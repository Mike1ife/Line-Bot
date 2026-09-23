"""Formula 1 client, backed by the Jolpica API.

Jolpica (api.jolpi.ca) is the community-run successor to Ergast, which was shut
down and now returns 404. ESPN is deliberately not used here: its F1 scoreboard
carries no competitors and its standings endpoint returns an empty stub.

Every session comes with an explicit UTC timestamp. That matters more than it
does for the NBA: F1 races land on Saturday, Sunday or Monday in Taiwan
depending on the venue, so there is no fixed date offset to rely on.
"""

import requests
from datetime import datetime, timezone, timedelta

BASE = "https://api.jolpi.ca/ergast/f1"
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


def get_next_race():
    """The next race not yet started, or None once the season is over."""
    now = datetime.now(timezone.utc)
    for race in get_season_races():
        if race["raceUTC"] > now:
            return race
    return None


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
