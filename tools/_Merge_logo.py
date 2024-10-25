import os
from PIL import Image
from itertools import combinations

folder_path = "./images/logo"

# Get a list of all image filenames in the folder
image_files = [f for f in os.listdir(folder_path) if f.endswith((".png", ".jpg"))]

# Generate all possible pairs of image filenames
image_pairs = list(combinations(image_files, 2))

# Now image_pairs contains all possible pairs of image filenames

# Print the pairs (for demonstration purposes)
for pair in image_pairs:
    images = [Image.open(os.path.join(folder_path, img)) for img in pair]

    img_team_a, img_team_b = images

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
    composite_img.save(
        f"images/merge/{pair[0].split('.')[0]}_{pair[1].split('.')[0]}.png"
    )
