import os
import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

USERNAME = os.environ.get("GITHUB_USERNAME", "arpitagni1")
TOKEN = os.environ.get("GITHUB_TOKEN")

OUTPUT_FILE = os.environ.get(
    "OUTPUT_FILE",
    "assets/github-activity.svg"
)

if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not available")


# ---------------------------------------------------------
# GitHub GraphQL API
# ---------------------------------------------------------

today = datetime.now(timezone.utc)
from_date = today - timedelta(days=364)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {

    contributionsCollection(from: $from, to: $to) {

      contributionCalendar {
        totalContributions

        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
            weekday
          }
        }
      }

      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
  }
}
"""

variables = {
    "login": USERNAME,
    "from": from_date.isoformat().replace("+00:00", "Z"),
    "to": today.isoformat().replace("+00:00", "Z")
}

payload = json.dumps({
    "query": query,
    "variables": variables
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-profile-animated-activity"
    }
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read().decode("utf-8"))


if "errors" in result:
    raise RuntimeError(
        "GitHub GraphQL error:\n"
        + json.dumps(result["errors"], indent=2)
    )


user = result.get("data", {}).get("user")

if not user:
    raise RuntimeError(
        f"GitHub user '{USERNAME}' was not found"
    )


collection = user["contributionsCollection"]
calendar = collection["contributionCalendar"]

total_contributions = calendar["totalContributions"]
weeks = calendar["weeks"]


# ---------------------------------------------------------
# Activity statistics
# ---------------------------------------------------------

commits = collection["totalCommitContributions"]
issues = collection["totalIssueContributions"]
pull_requests = collection["totalPullRequestContributions"]
reviews = collection["totalPullRequestReviewContributions"]

activity_total = commits + issues + pull_requests + reviews


def percentage(value):
    if activity_total == 0:
        return 0

    return round((value / activity_total) * 100)


commit_percent = percentage(commits)
issue_percent = percentage(issues)
pr_percent = percentage(pull_requests)
review_percent = percentage(reviews)


# ---------------------------------------------------------
# SVG configuration
# ---------------------------------------------------------

WIDTH = 1000
HEIGHT = 650

BG = "#0d1117"
BORDER = "#30363d"

TEXT = "#f0f6fc"
MUTED = "#8b949e"

GREEN = "#3fb950"
LIGHT_GREEN = "#7ee787"
BLUE = "#58a6ff"

COLORS = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353"
}


# ---------------------------------------------------------
# Calendar geometry
# ---------------------------------------------------------

GRID_X = 90
GRID_Y = 100

CELL = 11
GAP = 4

svg = []


def add(line):
    svg.append(line)


# ---------------------------------------------------------
# SVG start
# ---------------------------------------------------------

add(
    f'''
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}"
>

<style>

text {{
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Helvetica,
        Arial,
        sans-serif;
}}

.title {{
    fill: {TEXT};
    font-size: 21px;
    font-weight: 500;
}}

.text {{
    fill: {TEXT};
    font-size: 15px;
}}

.muted {{
    fill: {MUTED};
    font-size: 14px;
}}

.percent {{
    fill: #79c0ff;
    font-size: 14px;
}}

</style>

<rect
    width="{WIDTH}"
    height="{HEIGHT}"
    rx="10"
    fill="{BG}"
/>

<rect
    x="8"
    y="55"
    width="984"
    height="580"
    rx="8"
    fill="{BG}"
    stroke="{BORDER}"
/>

<text
    x="18"
    y="36"
    class="title"
>
{total_contributions:,} contributions in the last year
</text>
'''
)


# ---------------------------------------------------------
# Weekday labels
# ---------------------------------------------------------

weekday_labels = {
    1: "Mon",
    3: "Wed",
    5: "Fri"
}

for day, label in weekday_labels.items():

    y = GRID_Y + day * (CELL + GAP) + 10

    add(
        f'''
<text
    x="48"
    y="{y}"
    class="text"
>
{label}
</text>
'''
    )


# ---------------------------------------------------------
# Month labels
# ---------------------------------------------------------

last_month = None

for week_index, week in enumerate(weeks):

    if not week["contributionDays"]:
        continue

    first_day = week["contributionDays"][0]["date"]

    date = datetime.strptime(
        first_day,
        "%Y-%m-%d"
    )

    month = date.strftime("%b")

    if month != last_month:

        x = GRID_X + week_index * (CELL + GAP)

        add(
            f'''
<text
    x="{x}"
    y="88"
    class="text"
>
{month}
</text>
'''
        )

        last_month = month


# ---------------------------------------------------------
# Contribution cells
# ---------------------------------------------------------

for week_index, week in enumerate(weeks):

    for day in week["contributionDays"]:

        weekday = day["weekday"]

        level = day["contributionLevel"]

        count = day["contributionCount"]

        date = day["date"]

        x = GRID_X + week_index * (CELL + GAP)
        y = GRID_Y + weekday * (CELL + GAP)

        color = COLORS.get(
            level,
            COLORS["NONE"]
        )

        delay = (
            (
                week_index * 7
                + weekday
            )
            % 50
        ) * 0.07

        if count > 0:

            add(
                f'''
<rect
    x="{x}"
    y="{y}"
    width="{CELL}"
    height="{CELL}"
    rx="2"
    fill="{color}"
>

<title>{date}: {count} contributions</title>

<animate
    attributeName="opacity"
    values="0.55;1;0.75;1"
    dur="3s"
    begin="{delay:.2f}s"
    repeatCount="indefinite"
/>

</rect>
'''
            )

        else:

            add(
                f'''
<rect
    x="{x}"
    y="{y}"
    width="{CELL}"
    height="{CELL}"
    rx="2"
    fill="{color}"
>
<title>{date}: 0 contributions</title>
</rect>
'''
            )


# ---------------------------------------------------------
# Moving scanner
# ---------------------------------------------------------

END_X = (
    GRID_X
    + len(weeks) * (CELL + GAP)
)


add(
    f'''
<line
    x1="{GRID_X}"
    y1="{GRID_Y - 8}"
    x2="{GRID_X}"
    y2="{GRID_Y + 110}"
    stroke="{BLUE}"
    stroke-width="2"
    stroke-opacity="0.30"
>

<animate
    attributeName="x1"
    values="{GRID_X};{END_X};{GRID_X}"
    dur="9s"
    repeatCount="indefinite"
/>

<animate
    attributeName="x2"
    values="{GRID_X};{END_X};{GRID_X}"
    dur="9s"
    repeatCount="indefinite"
/>

</line>
'''
)


# ---------------------------------------------------------
# Legend
# ---------------------------------------------------------

add(
    f'''
<text
    x="65"
    y="235"
    class="muted"
>
Animated contribution activity
</text>

<text
    x="785"
    y="235"
    class="muted"
>
Less
</text>
'''
)

legend_colors = list(COLORS.values())

for index, color in enumerate(legend_colors):

    x = 820 + index * 18

    add(
        f'''
<rect
    x="{x}"
    y="223"
    width="12"
    height="12"
    rx="2"
    fill="{color}"
/>
'''
    )


add(
    '''
<text
    x="920"
    y="235"
    class="muted"
>
More
</text>
'''
)


# ---------------------------------------------------------
# Divider
# ---------------------------------------------------------

add(
    f'''
<line
    x1="8"
    y1="260"
    x2="992"
    y2="260"
    stroke="{BORDER}"
/>

<text
    x="30"
    y="305"
    class="title"
>
Activity overview
</text>

<line
    x1="485"
    y1="285"
    x2="485"
    y2="610"
    stroke="{BORDER}"
/>
'''
)


# ---------------------------------------------------------
# Left side activity details
# ---------------------------------------------------------

add(
    f'''
<text
    x="58"
    y="355"
    class="text"
>
GitHub activity for
</text>

<text
    x="190"
    y="355"
    fill="{BLUE}"
    font-size="16"
>
@{USERNAME}
</text>

<text
    x="58"
    y="395"
    class="muted"
>
Commits
</text>

<text
    x="180"
    y="395"
    class="text"
>
{commits:,}
</text>

<text
    x="58"
    y="425"
    class="muted"
>
Pull requests
</text>

<text
    x="180"
    y="425"
    class="text"
>
{pull_requests:,}
</text>

<text
    x="58"
    y="455"
    class="muted"
>
Code reviews
</text>

<text
    x="180"
    y="455"
    class="text"
>
{reviews:,}
</text>

<text
    x="58"
    y="485"
    class="muted"
>
Issues
</text>

<text
    x="180"
    y="485"
    class="text"
>
{issues:,}
</text>
'''
)


# ---------------------------------------------------------
# Radar graph
# ---------------------------------------------------------

CX = 745
CY = 455

RADIUS = 120


activity = {
    "Code review": review_percent,
    "Issues": issue_percent,
    "Pull requests": pr_percent,
    "Commits": commit_percent
}


angles = {
    "Code review": -math.pi / 2,
    "Issues": 0,
    "Pull requests": math.pi / 2,
    "Commits": math.pi
}


def radar_point(label, value):

    angle = angles[label]

    distance = RADIUS * (value / 100)

    x = CX + distance * math.cos(angle)
    y = CY + distance * math.sin(angle)

    return x, y


order = [
    "Code review",
    "Issues",
    "Pull requests",
    "Commits"
]


target_points = [
    radar_point(
        label,
        activity[label]
    )
    for label in order
]


target_string = " ".join(
    f"{x:.1f},{y:.1f}"
    for x, y in target_points
)


center_string = " ".join(
    f"{CX},{CY}"
    for _ in order
)


# ---------------------------------------------------------
# Radar axes
# ---------------------------------------------------------

for label in order:

    angle = angles[label]

    x = CX + RADIUS * math.cos(angle)
    y = CY + RADIUS * math.sin(angle)

    add(
        f'''
<line
    x1="{CX}"
    y1="{CY}"
    x2="{x:.1f}"
    y2="{y:.1f}"
    stroke="{GREEN}"
    stroke-width="2"
/>
'''
    )


# ---------------------------------------------------------
# Animated radar polygon
# ---------------------------------------------------------

add(
    f'''
<polygon
    points="{center_string}"
    fill="{GREEN}"
    fill-opacity="0.28"
    stroke="{GREEN}"
    stroke-width="2"
>

<animate
    attributeName="points"
    values="
        {center_string};
        {target_string};
        {target_string};
        {center_string};
        {target_string}
    "
    keyTimes="0;0.22;0.62;0.78;1"
    dur="6s"
    repeatCount="indefinite"
/>

</polygon>
'''
)


# ---------------------------------------------------------
# Moving radar points
# ---------------------------------------------------------

for index, label in enumerate(order):

    tx, ty = target_points[index]

    delay = index * 0.15

    add(
        f'''
<circle
    cx="{CX}"
    cy="{CY}"
    r="5"
    fill="{BG}"
    stroke="{LIGHT_GREEN}"
    stroke-width="3"
>

<animate
    attributeName="cx"
    values="
        {CX};
        {tx:.1f};
        {tx:.1f};
        {CX};
        {tx:.1f}
    "
    keyTimes="0;0.22;0.62;0.78;1"
    dur="6s"
    begin="{delay}s"
    repeatCount="indefinite"
/>

<animate
    attributeName="cy"
    values="
        {CY};
        {ty:.1f};
        {ty:.1f};
        {CY};
        {ty:.1f}
    "
    keyTimes="0;0.22;0.62;0.78;1"
    dur="6s"
    begin="{delay}s"
    repeatCount="indefinite"
/>

<animate
    attributeName="r"
    values="5;8;5"
    dur="1.4s"
    repeatCount="indefinite"
/>

</circle>
'''
    )


# ---------------------------------------------------------
# Center pulse
# ---------------------------------------------------------

add(
    f'''
<circle
    cx="{CX}"
    cy="{CY}"
    r="4"
    fill="{BG}"
    stroke="{LIGHT_GREEN}"
    stroke-width="2"
>

<animate
    attributeName="r"
    values="4;8;4"
    dur="1.6s"
    repeatCount="indefinite"
/>

</circle>
'''
)


# ---------------------------------------------------------
# Radar labels
# ---------------------------------------------------------

add(
    f'''
<text
    x="{CX}"
    y="{CY - RADIUS - 28}"
    text-anchor="middle"
    class="percent"
>
{review_percent}%
</text>

<text
    x="{CX}"
    y="{CY - RADIUS - 8}"
    text-anchor="middle"
    class="muted"
>
Code review
</text>


<text
    x="{CX + RADIUS + 25}"
    y="{CY - 5}"
    class="percent"
>
{issue_percent}%
</text>

<text
    x="{CX + RADIUS + 18}"
    y="{CY + 17}"
    class="muted"
>
Issues
</text>


<text
    x="{CX}"
    y="{CY + RADIUS + 28}"
    text-anchor="middle"
    class="percent"
>
{pr_percent}%
</text>

<text
    x="{CX}"
    y="{CY + RADIUS + 50}"
    text-anchor="middle"
    class="muted"
>
Pull requests
</text>


<text
    x="{CX - RADIUS - 38}"
    y="{CY - 5}"
    text-anchor="end"
    class="percent"
>
{commit_percent}%
</text>

<text
    x="{CX - RADIUS - 38}"
    y="{CY + 17}"
    text-anchor="end"
    class="muted"
>
Commits
</text>
'''
)


# ---------------------------------------------------------
# SVG end
# ---------------------------------------------------------

add("</svg>")


# ---------------------------------------------------------
# Write file
# ---------------------------------------------------------

output = Path(OUTPUT_FILE)

output.parent.mkdir(
    parents=True,
    exist_ok=True
)

output.write_text(
    "\n".join(svg),
    encoding="utf-8"
)

print(
    f"Generated {OUTPUT_FILE}"
)

print(
    f"Total contributions: {total_contributions}"
)

print(
    f"Commits: {commits}"
)

print(
    f"Pull requests: {pull_requests}"
)

print(
    f"Reviews: {reviews}"
)

print(
    f"Issues: {issues}"
)
