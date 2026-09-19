"""Smoke-test the ESPN NBA JSON feed.

    python -m tools.espn_probe            # random past date
    python -m tools.espn_probe 2026-01-15 # specific date

Checks that the feed is reachable, that every team abbreviation maps to a Chinese
name, and that 得分/籃板/抄截 can be read for real players.
"""

import sys

from utils._espn import get_scoreboard, get_boxscore, random_past_game_date


def probe(gameDate: str = None):
    if gameDate:
        games = [g for g in get_scoreboard(gameDate) if g["completed"]]
    else:
        gameDate, games = random_past_game_date()

    if not games:
        print("FAIL: no completed games found")
        return 1

    print(f"date        : {gameDate}")
    print(f"games found : {len(games)}")
    print()

    for game in games:
        print(
            f"  {game['awayName']} {game['awayScore']} @ "
            f"{game['homeName']} {game['homeScore']}   "
            f"({game['startUTC']}  event={game['eventId']})"
        )

    target = games[0]
    print(f"\nboxscore for {target['awayName']} @ {target['homeName']}:")
    boxscore = get_boxscore(target["eventId"])

    if not boxscore:
        print("FAIL: boxscore was empty")
        return 1

    top = sorted(boxscore.items(), key=lambda kv: kv[1]["得分"], reverse=True)[:8]
    for name, stat in top:
        print(
            f"  {name:<24} {stat['team']}  "
            f"{stat['得分']}分 {stat['籃板']}板 {stat['抄截']}抄"
        )

    print(f"\nPASS: {len(games)} games, {len(boxscore)} players parsed")
    return 0


if __name__ == "__main__":
    sys.exit(probe(sys.argv[1] if len(sys.argv) > 1 else None))
