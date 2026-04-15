import os
import requests
from collections import defaultdict
from datetime import datetime

# --- CONFIGURATION ---
USER = "aniketchawardol"
TOKEN = os.getenv("METRICS_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# --- MANUAL STATS (Update these periodically) ---
# Because calculating a 365-day streak requires hundreds of API calls and hits rate limits,
# we define your calendar streak stats here to keep the script fast and safe.
BEST_STREAK = "4 days"
HIGHEST_IN_DAY = 7
AVERAGE_PER_DAY = "~0.48"

def get_commits():
    """Fetch total commits."""
    url = f"https://api.github.com/search/commits?q=author:{USER}"
    headers = HEADERS.copy()
    headers["Accept"] = "application/vnd.github.cloak-preview+json"
    response = requests.get(url, headers=headers)
    return response.json().get("total_count", 0) if response.status_code == 200 else 0

def get_search_count(query):
    """Fetch total counts for Issues and PRs."""
    url = f"https://api.github.com/search/issues?q={query}"
    response = requests.get(url, headers=HEADERS)
    return response.json().get("total_count", 0) if response.status_code == 200 else 0

def get_graphql_data():
    """Fetch profile data, comments, and language usage."""
    query = """
    query {
      user(login: "%s") {
        createdAt
        followers { totalCount }
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
          totalCount
        }
        issueComments { totalCount }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size, node { name, color } }
            }
          }
        }
      }
    }
    """ % USER

    response = requests.post("https://api.github.com/graphql", json={'query': query}, headers=HEADERS)
    data = response.json().get("data", {}).get("user", {})
    
    # Profile Stats
    followers = data.get("followers", {}).get("totalCount", 0)
    contributed_to = data.get("repositoriesContributedTo", {}).get("totalCount", 0)
    comments_count = data.get("issueComments", {}).get("totalCount", 0)
    
    # Calculate Account Age
    created_at = data.get("createdAt")
    years_ago = 0
    if created_at:
        created_year = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").year
        years_ago = datetime.now().year - created_year

    # Language Stats
    repos = data.get("repositories", {}).get("nodes", [])
    lang_sizes = defaultdict(int)
    lang_colors = {}
    total_size = 0

    for repo in repos:
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            size = edge["size"]
            color = edge["node"]["color"] or "#cccccc"
            lang_sizes[name] += size
            lang_colors[name] = color
            total_size += size

    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:8]
    stats = []
    for name, size in sorted_langs:
        percentage = (size / total_size) * 100 if total_size > 0 else 0
        stats.append({"name": name, "percentage": round(percentage, 2), "color": lang_colors[name], "width": percentage})
        
    return followers, contributed_to, years_ago, comments_count, stats, len(lang_sizes)

def main():
    print(f"Generating aesthetic formal card for {USER}...")

    # --- 1. FETCH STATS ---
    commits = get_commits()
    prs_opened = get_search_count(f"type:pr author:{USER}")
    issues_opened = get_search_count(f"type:issue author:{USER}")
    followers, contributed_to, years_ago, comments_count, languages, total_langs = get_graphql_data()

    # --- 2. GENERATE SVG COMPONENTS ---
    progress_bar = ""
    current_x = 0
    for lang in languages:
        width = lang['width'] * 4.2 
        progress_bar += f'<rect x="{current_x}" y="0" width="{width}" height="8" fill="{lang["color"]}"/>\n'
        current_x += width

    lang_list = ""
    col1_x, col2_x = 30, 240
    for i, lang in enumerate(languages):
        x = col1_x if i % 2 == 0 else col2_x
        y = 265 + (i // 2) * 25
        lang_list += f"""
        <g transform="translate({x}, {y})">
            <circle cx="5" cy="5" r="4" fill="{lang['color']}"/>
            <text x="20" y="9" class="text-secondary">{lang['name']}</text>
            <text x="130" y="9" class="text-secondary" text-anchor="end">{lang['percentage']}%</text>
        </g>
        """

    # --- 3. ASSEMBLE SVG ---
    svg_content = f"""
    <svg width="480" height="480" viewBox="0 0 480 480" xmlns="http://www.w3.org/2000/svg">
        <style>
            .title {{ font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58A6FF; }}
            .header {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #E6EDF3; }}
            .text-primary {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #E6EDF3; }}
            .text-secondary {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8B949E; }}
            .bar-bg {{ fill: #161B22; rx: 4px; ry: 4px; }}
            .card-bg {{ fill: #0D1117; stroke: #30363D; stroke-width: 1px; rx: 8px; ry: 8px; }}
        </style>
        
        <rect width="478" height="478" x="1" y="1" class="card-bg"/>
        
        <text x="30" y="40" class="title">{USER}</text>
        <g transform="translate(30, 65)">
            <text class="text-secondary" x="0" y="0">Joined GitHub {years_ago} years ago</text>
            <text class="text-secondary" x="220" y="0">Contributed to {contributed_to} repos</text>
            <text class="text-secondary" x="0" y="25">Followed by {followers} users</text>
        </g>

        <line x1="30" y1="110" x2="450" y2="110" stroke="#21262D" stroke-width="1" />

        <text x="30" y="140" class="header">Activity</text>
        <g transform="translate(30, 165)">
            <text class="text-secondary" x="0" y="0">Code Reviews &amp; Feedback</text>
            <text class="text-primary" x="200" y="0">{comments_count}</text>
            
            <text class="text-secondary" x="250" y="0">PRs Opened</text>
            <text class="text-primary" x="380" y="0">{prs_opened}</text>

            <text class="text-secondary" x="0" y="30">Total Commits</text>
            <text class="text-primary" x="200" y="30">{commits}</text>
            
            <text class="text-secondary" x="250" y="30">Issues Opened</text>
            <text class="text-primary" x="380" y="30">{issues_opened}</text>
        </g>
        
        <line x1="30" y1="215" x2="450" y2="215" stroke="#21262D" stroke-width="1" />

        <text x="30" y="240" class="header">&lt;/&gt; {total_langs} Languages</text>
        <g transform="translate(30, 255)">
            <rect width="420" height="8" class="bar-bg"/>
            <clipPath id="corners"><rect width="420" height="8" rx="4" ry="4"/></clipPath>
            <g clip-path="url(#corners)">{progress_bar}</g>
        </g>
        {lang_list}

        <line x1="30" y1="385" x2="450" y2="385" stroke="#21262D" stroke-width="1" />

        <text x="30" y="415" class="header">Contributions Stats</text>
        <g transform="translate(30, 440)">
            <text class="text-secondary" x="0" y="0">Best streak</text>
            <text class="text-primary" x="120" y="0">{BEST_STREAK}</text>
            
            <text class="text-secondary" x="180" y="0">Highest in a day</text>
            <text class="text-primary" x="300" y="0">{HIGHEST_IN_DAY}</text>

            <text class="text-secondary" x="340" y="0">Daily Avg</text>
            <text class="text-primary" x="420" y="0">{AVERAGE_PER_DAY}</text>
        </g>
    </svg>
    """

    with open("custom_metrics.svg", "w", encoding="utf-8") as file:
        file.write(svg_content.strip())
    print("Generated custom_metrics.svg successfully!")

if __name__ == "__main__":
    main()
