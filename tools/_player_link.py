import psycopg
import requests
from bs4 import BeautifulSoup

conn_str = ""

output = {}

response = requests.get("https://www.foxsports.com/nba/teams")
soup = BeautifulSoup(response.text, "html.parser")
teams = soup.find("div", class_="entity-list-group")
teams_url = teams.find_all("a")

for team_url in teams_url:
    url = f"https://www.foxsports.com{team_url.get('href')}-roster"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    player_groups = soup.find_all("tbody", class_="row-data lh-1pt43 fs-14")
    for player_group in player_groups[:-1]:
        player_containers = player_group.find_all("tr")
        for player_container in player_containers:
            player_info = player_container.find(
                "td", class_="cell-entity fs-18 lh-1pt67"
            )
            player_url = (
                f"https://www.foxsports.com{player_info.find('a').get('href')}-game-log"
            )
            player_name = player_info.find("h3").text.strip()
            print(player_name)
            output[player_name] = player_url

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS PlayerLink (
            name TEXT PRIMARY KEY,
            link TEXT
        )
        """
        )

        for name, link in output.items():
            cur.execute(
                "INSERT INTO PlayerLink (name, link) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET link = EXCLUDED.link",
                (name, link),
            )
    conn.commit()
