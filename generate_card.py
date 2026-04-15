import os
import requests
from collections import defaultdict
from datetime import datetime

# --- CONFIGURATION ---
USER = "aniketchawardol"
TOKEN = os.getenv("METRICS_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# --- MANUAL STATS (Bypassing GitHub's 1-Year API Limits) ---
BEST_STREAK = "4 days"
HIGHEST_IN_DAY = 7
AVERAGE_PER_DAY = "~0.48"
MANUAL_REPOS_CONTRIBUTED = 26 # Hardcoded because the API only checks the last 365 days

def get_rest_count(query):
    """Fetch counts using GitHub's Search API."""
    url = f"https://api.github.com/search/issues?q={query}"
    response = requests.get(url, headers=HEADERS)
    return response.json().get("total_count", 0) if response.status_code == 200 else 0

def get_commits():
    """Fetch all-time commits."""
    url = f"https://api.github.com/search/commits?q=author:{USER}"
    headers = HEADERS.copy()
    headers["Accept"] = "application/vnd.github.cloak-preview+json"
    response = requests.get(url, headers=headers)
    return response.json().get("total_count", 0) if response.status_code == 200 else 0

def get_graphql_data():
    """Fetch profile data and deep language usage."""
    query = """
    query {
      user(login: "%s") {
        createdAt
        followers { totalCount }
        issueComments { totalCount }
        repositories(ownerAffiliations: [OWNER, COLLABORATOR], isFork: false, first: 100) {
          nodes {
            languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
              edges { size, node { name, color } }
            }
          }
        }
      }
    }
    """ % USER

    response = requests.post("https://api.github.com/graphql", json={'query': query}, headers=HEADERS)
    data = response.json().get("data", {}).get("user", {})
    
    followers = data.get("followers", {}).get("totalCount", 0)
    issue_comments = data.get("issueComments", {}).get("totalCount", 0)
    
    # Account Age
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

    # Top 16 Languages
    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:16]
    stats = []
    for name, size in sorted_langs:
        percentage = (size / total_size) * 100 if total_size > 0 else 0
        stats.append({"name": name, "percentage": round(percentage, 2), "color": lang_colors[name], "width": percentage})
        
    return followers, years_ago, issue_comments, stats, len(lang_sizes)

def main():
    print(f"Generating mathematically aligned card for {USER}...")

    # --- 1. FETCH STATS ---
    commits = get_commits()
    prs_opened = get_rest_count(f"type:pr author:{USER}")
    issues_opened = get_rest_count(f"type:issue author:{USER}")
    
    # True Code Reviews
    formal_reviews = get_rest_count(f"type:pr reviewed-by:{USER}")
    followers, years_ago, issue_comments, languages, total_langs = get_graphql_data()
    true_reviews = formal_reviews + issue_comments

    # --- 2. GENERATE SVG COMPONENTS ---
    progress_bar = ""
    current_x = 0
    # Map percentage to a 440px wide bar
    for lang in languages:
        width = (lang['width'] / 100) * 440 
        progress_bar += f'<rect x="{current_x}" y="0" width="{width}" height="8" fill="{lang["color"]}"/>\n'
        current_x += width

    # Language List (2 Columns, strictly mathematically aligned)
    lang_list = ""
    col1_name_x, col1_val_x = 60, 240
    col2_name_x, col2_val_x = 300, 480
    
    for i, lang in enumerate(languages):
        is_col1 = (i % 2 == 0)
        name_x = col1_name_x if is_col1 else col2_name_x
        val_x = col1_val_x if is_col1 else col2_val_x
        # Y-coordinate fixed: Starts safely below the progress bar with 28px spacing
        y = 315 + (i // 2) * 28 
        
        lang_list += f"""
        <g transform="translate(0, {y})">
            <circle cx="{name_x - 12}" cy="-4" r="4" fill="{lang['color']}"/>
            <text x="{name_x}" y="0" class="text-secondary">{lang['name']}</text>
            <text x="{val_x}" y="0" class="text-secondary" text-anchor="end">{lang['percentage']}%</text>
        </g>
        """

    # --- 3. ASSEMBLE SVG ---
    # Dynamic height calculation properly synced with the new Y-coordinates
    svg_height = 370 + ((len(languages) + 1) // 2) * 28
    
    svg_content = f"""
    <svg width="520" height="{svg_height}" viewBox="0 0 520 {svg_height}" xmlns="http://www.w3.org/2000/svg">
        <style>
            .title {{ font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58A6FF; }}
            .header {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #E6EDF3; }}
            .text-primary {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #E6EDF3; }}
            .text-secondary {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8B949E; }}
            .bar-bg {{ fill: #161B22; rx: 4px; ry: 4px; }}
            .card-bg {{ fill: #0D1117; stroke: #30363D; stroke-width: 1px; rx: 8px; ry: 8px; }}
        </style>
        
        <rect width="518" height="{svg_height - 2}" x="1" y="1" class="card-bg"/>
        
        <text x="40" y="45" class="title">{USER}</text>
        
        <text class="text-secondary" x="40" y="75">Joined GitHub {years_ago} years ago</text>
        <text class="text-secondary" x="280" y="75">Contributed to {MANUAL_REPOS_CONTRIBUTED} repos</text>
        
        <text class="text-secondary" x="40" y="100">Followed by {followers} users</text>

        <line x1="40" y1="125" x2="480" y2="125" stroke="#21262D" stroke-width="1" />

        <text x="40" y="155" class="header">Activity</text>
        
        <text class="text-secondary" x="40" y="185">Code Reviews &amp; Feedback</text>
        <text class="text-primary" x="240" y="185" text-anchor="end">{true_reviews}</text>
        
        <text class="text-secondary" x="280" y="185">PRs Opened</text>
        <text class="text-primary" x="480" y="185" text-anchor="end">{prs_opened}</text>

        <text class="text-secondary" x="40" y="215">Total Commits</text>
        <text class="text-primary" x="240" y="215" text-anchor="end">{commits}</text>
        
        <text class="text-secondary" x="280" y="215">Issues Opened</text>
        <text class="text-primary" x="480" y="215" text-anchor="end">{issues_opened}</text>
        
        <line x1="40" y1="245" x2="480" y2="245" stroke="#21262D" stroke-width="1" />

        <text x="40" y="275" class="header">&lt;/&gt; {total_langs} Languages</text>
        
        <g transform="translate(40, 295)">
            <rect width="440" height="8" class="bar-bg"/>
            <clipPath id="corners"><rect width="440" height="8" rx="4" ry="4"/></clipPath>
            <g clip-path="url(#corners)">{progress_bar}</g>
        </g>
        
        {lang_list}

        <line x1="40" y1="{svg_height - 75}" x2="480" y2="{svg_height - 75}" stroke="#21262D" stroke-width="1" />

        <text x="40" y="{svg_height - 45}" class="header">Contributions Stats</text>
        
        <text class="text-secondary" x="40" y="{svg_height - 20}">Best streak</text>
        <text class="text-primary" x="140" y="{svg_height - 20}">{BEST_STREAK}</text>
        
        <text class="text-secondary" x="200" y="{svg_height - 20}">Highest in a day</text>
        <text class="text-primary" x="320" y="{svg_height - 20}">{HIGHEST_IN_DAY}</text>

        <text class="text-secondary" x="375" y="{svg_height - 20}">Daily Avg</text>
        <text class="text-primary" x="480" y="{svg_height - 20}" text-anchor="end">{AVERAGE_PER_DAY}</text>
        
    </svg>
    """

    with open("custom_metrics.svg", "w", encoding="utf-8") as file:
        file.write(svg_content.strip())
    print("Generated custom_metrics.svg successfully!")

if __name__ == "__main__":
    main()
