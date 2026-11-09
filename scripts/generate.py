"""Generate standalone SVG profile panels from a photograph and public GitHub data."""

import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def github(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Masood-zone-profile"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{path}", headers=headers)
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def fetch_stats(username):
    user = github(f"users/{quote(username)}")
    repos = []
    page = 1
    while True:
        batch = github(f"users/{quote(username)}/repos?type=owner&sort=created&direction=asc&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    repos = list({r["id"]: r for r in repos if not r.get("private", True) and r["owner"]["login"].lower() == username.lower()}.values())
    return {"public_repos": len(repos), "stars": sum(r["stargazers_count"] for r in repos), "followers": user["followers"]}


THEMES = {
    "dark": {"bg": "#0d1117", "panel": "#161b22", "border": "#30363d", "text": "#c9d1d9", "muted": "#8b949e", "gold": "#c3a278", "blue": "#8cbbdd", "art": "#aac4b1"},
    "light": {"bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de", "text": "#24292f", "muted": "#57606a", "gold": "#80602f", "blue": "#225c88", "art": "#315a45"},
}


def artwork():
    with Image.open(ROOT / "assets/waterfall.png") as source:
        gray = ImageOps.grayscale(source.convert("RGB").resize((78, 58), Image.Resampling.LANCZOS))
    return ImageEnhance.Contrast(gray).enhance(1.25)


def render(config, stats, theme, art):
    colors = THEMES[theme]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="550" viewBox="0 0 1000 550" role="img" aria-labelledby="title desc">',
           '<title id="title">Masood Acheampong — GitHub profile</title>',
           '<desc id="desc">ASCII waterfall artwork beside professional details and public GitHub statistics.</desc>',
           f'<rect width="1000" height="550" rx="14" fill="{colors["bg"]}"/>',
           f'<rect x="16" y="16" width="968" height="518" rx="10" fill="{colors["panel"]}" stroke="{colors["border"]}"/>',
           '<g font-family="Consolas, Liberation Mono, Menlo, monospace">']

    def text(x, y, content, color="text", size=13, weight="normal"):
        out.append(f'<text x="{x}" y="{y}" fill="{colors[color]}" font-size="{size}" font-weight="{weight}" xml:space="preserve">{escape(str(content))}</text>')

    text(38, 48, "Masood-zone / README.md", "muted", 11)
    ramp = ".,:;i1tfLCG08@"
    for row in range(art.height):
        for col in range(78):
            brightness = art.getpixel((col, row))
            # Keep the photograph's black circular surround empty.
            if brightness < 10:
                continue
            char = ramp[min(len(ramp) - 1, brightness * len(ramp) // 256)]
            color = "text" if brightness > 150 else "art"
            text(round(36 + col * 4.65, 2), round(105 + row * 6.3, 2), char, color, 7.8)

    text(438, 92, config["username"], "text", 17, "bold")
    out.append(f'<path d="M438 107H950" stroke="{colors["border"]}"/>')

    def field(y, label, value):
        text(438, y, label, "gold")
        text(551, y, value, "blue")

    field(139, "Name", config["name"])
    field(163, "Company", config["company"])
    field(187, "Location", config["location"])
    field(223, "Languages", ", ".join(config["languages"][:2]))
    field(247, "", ", ".join(config["languages"][2:]))
    text(438, 295, "Contact", "gold", 13, "bold")
    out.append(f'<path d="M507 291H950" stroke="{colors["border"]}"/>')
    field(323, "Website", config["website"].removeprefix("https://www."))
    field(347, "GitHub", "github.com/" + config["username"])
    text(438, 395, "GitHub Stats", "gold", 13, "bold")
    out.append(f'<path d="M547 391H950" stroke="{colors["border"]}"/>')
    field(423, "Repos", format(stats["public_repos"], ","))
    field(447, "Stars", format(stats["stars"], ","))
    field(471, "Followers", format(stats["followers"], ","))
    text(438, 507, "Public data / refreshed daily", "muted", 10)
    out.append("</g></svg>\n")
    return "\n".join(out)


def main():
    config = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    # Fetch and render everything before touching published assets.
    stats = fetch_stats(config["username"])
    art = artwork()
    panels = {theme: render(config, stats, theme, art) for theme in THEMES}
    for theme, panel in panels.items():
        target = ROOT / f"assets/profile-{theme}.svg"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(panel, encoding="utf-8", newline="\n")
        temporary.replace(target)
    print(json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
