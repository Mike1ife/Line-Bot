import requests
from bs4 import BeautifulSoup
from _table import nba_team_translations

data = requests.get(f"https://www.foxsports.com/nba/teams").text

f = open("output.txt", "w", encoding="utf-8")
f.write(data)
f.close()

soup = BeautifulSoup(data, "html.parser")
img_tags = soup.select("a.entity-list-row-container.image-logo img")
src_values = [img["src"] for img in img_tags]


for src in src_values:
    dimensions_part = "72.72"
    new_dimensions = "250.250"
    src = src.replace(dimensions_part, new_dimensions)
    response = requests.get(src)
    if response.status_code == 200:
        # Save the image with a filename derived from the URL
        filename = src.split("/")[-1]
        original_filename = filename
        # Extract the team name from the original filename
        team_name = original_filename.split(".")[0]
        # Convert the team name to uppercase
        team_name_uppercase = team_name.upper()
        if team_name_uppercase != "TRAILBLAZERS":
            team_name_uppercase = nba_team_translations[team_name_uppercase]
        # Create the new filename
        new_filename = f"{team_name_uppercase}.png"

        with open(f"images/logo/{new_filename}", "wb") as f:
            f.write(response.content)
        print(f"Image {new_filename} downloaded successfully.")
    else:
        print(
            f"Failed to download image from {src}. Status code: {response.status_code}"
        )
