import requests
from PIL import Image


def build_image(url_team_a, url_team_b):
    img_team_a = Image.open(requests.get(url_team_a, stream=True).raw).convert("RGBA")
    img_team_b = Image.open(requests.get(url_team_b, stream=True).raw).convert("RGBA")

    background_color = (255, 255, 255, 255)
    composite_img = Image.new(
        "RGBA",
        (
            img_team_a.width + img_team_b.width,
            max(img_team_a.height, img_team_b.height),
        ),
        background_color,
    )

    composite_img.paste(img_team_a, (0, 0), mask=img_team_a)
    composite_img.paste(img_team_b, (img_team_a.width, 0), mask=img_team_b)
    composite_img.save("tmp/composite_logo.png")


def check_url_exists(url):
    try:
        response = requests.head(url, allow_redirects=True)
        # You can also use requests.get(url) if you want to follow redirects and check the content
        return response.status_code == 200
    except requests.ConnectionError:
        return False
