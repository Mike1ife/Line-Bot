import random
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from tools._table import NBA_TEAM_NAME


def nba_guessing():
    BASE = "https://www.foxsports.com/"

    def get_teams():
        url = BASE + "nba/teams"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        teams = soup.find_all("a", class_="entity-list-row-container image-logo")
        return teams

    def get_players(teams):
        team = random.choice(teams)
        url = BASE + team.attrs["href"] + "-roster"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        players = soup.find_all("a", class_="table-entity-name ff-ffc")
        if len(players) == 0:
            return get_players(teams)
        else:
            return players, url

    def get_stats(players):
        player = random.choice(players)
        url = BASE + player.attrs["href"] + "-stats"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        name = soup.find("span", class_="lh-sm-25")
        stats = soup.find_all("a", class_="stats-overview")
        if len(stats) == 0:
            return get_stats(players)
        else:
            return name, stats, url

    teams = get_teams()
    players, team_url = get_players(teams)
    name, stats, player_url = get_stats(players)

    # print(team_url)
    # print(player_url)

    player_info = {"name": name.getText().title(), "stats": []}
    for stat in stats:
        stat_type = (
            stat.find("h3", class_="stat-name uc fs-18 fs-md-14 fs-sm-14")
            .getText()
            .strip()
        )

        if stat_type == "SCORING":
            url = BASE + stat.attrs["href"]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            all_years = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all(
                "tr"
            )
            for each_year in all_years:
                data = defaultdict()
                YEAR, TEAM, GP, GS, MPG, PPG = [
                    value.getText().strip() for value in each_year.find_all("td")[:6]
                ]
                if TEAM == "TOTAL":
                    continue
                FPR = each_year.find_all("td")[10].getText().strip()
                data["Year"] = YEAR
                data["Team"] = TEAM
                data["GP"] = GP
                data["GS"] = GS
                data["MPG"] = MPG
                data["PPG"] = PPG
                data["FPR"] = FPR
                player_info["stats"].append(data)
        elif stat_type == "REBOUNDING":
            url = BASE + stat.attrs["href"]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            all_years = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all(
                "tr"
            )
            delta = 0
            for i, each_year in enumerate(all_years):
                TEAM = each_year.find_all("td")[1].getText().strip()
                if TEAM == "TOTAL":
                    delta += 1
                    continue
                RPG = each_year.find_all("td")[5].getText().strip()
                player_info["stats"][i - delta]["RPG"] = RPG
        elif stat_type == "ASSISTS":
            url = BASE + stat.attrs["href"]
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            all_years = soup.find("tbody", class_="row-data lh-1pt43 fs-14").find_all(
                "tr"
            )
            delta = 0
            for i, each_year in enumerate(all_years):
                TEAM = each_year.find_all("td")[1].getText().strip()
                if TEAM == "TOTAL":
                    delta += 1
                    continue
                APG = each_year.find_all("td")[6].getText().strip()
                player_info["stats"][i - delta]["APG"] = APG

    history_teams = ""
    history_game = ""
    history_stats = ""
    for stat in player_info["stats"]:
        year, TEAM, GP, GS, MPG, PPG, FPR, RPG, APG = stat.values()
        year = year.replace("-", "\u200B-")
        history_teams += "{:<8} {:<8}".format(year, NBA_TEAM_NAME[TEAM]) + "\n"
        history_game += "{:<8} {:<8} {:<8}".format(year, f"{GS}/{GP}", MPG) + "\n"
        history_stats += "{:<8} {:<8}".format(year, f"{PPG}/{RPG}/{APG}/{FPR}%") + "\n"

    return (
        player_info["name"],
        history_teams[:-1],
        history_game[:-1],
        history_stats[:-1],
    )
