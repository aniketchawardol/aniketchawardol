import os
import requests
from collections import defaultdict

# --- CONFIGURATION ---
USER = "aniketchawardol"
TOKEN = os.getenv("METRICS_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

def get_search_count(query):
    """Fetch total counts from GitHub's search API."""
    url = f"https://api.github.com/search/issues?q={query}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("total_count", 0)
    return 0

def get_language_stats():
    """Fetch and calculate language percentages using GitHub's GraphQL API."""
    query = """
    query {
      user(login: "%s") {
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """ % USER

    response = requests.post(
        "https://api.github.com/graphql", 
        json={'query': query}, 
        headers=HEADERS
    )
    
    if response.status_code != 200:
        return [], 0

    data = response.json()
    repos = data.get("data", {}).get("user", {}).get("repositories", {}).get("nodes", [])
    
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

    # Sort and calculate percentages
    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:8]
    
    stats = []
    for name, size in sorted_langs:
        percentage = (size / total_size) * 100 if total_size > 0 else 0
        stats.append({
            "name": name,
            "percentage": round(percentage, 2),
            "color": lang_colors[name],
            "width": percentage # For the progress bar
        })
        
    return stats, len(lang_sizes)

def main():
    print(f"Fetching statistics for {USER}...")

    # --- 1. FETCH STATS ---
    true_reviews = get_search_count(f"is:pr involves:{USER} -author:{USER}")
    prs_opened = get_search_count(f"is:pr author:{USER}")
    issues_opened = get_search_count(f"is:issue author:{USER}")
    commits = get_search_count(f"author:{USER} type:commit")
    
    languages, total_langs = get_language_stats()

    # --- 2. GENERATE SVG COMPONENTS ---
    # Progress Bar Generator
    progress_bar = ""
    current_x = 0
    for lang in languages:
        width = lang['width'] * 4.1 # Scale to fit 410px width
        progress_bar += f'<rect x="{current_x}" y="0" width="{width}" height="8" fill="{lang["color"]}"/>\n'
        current_x += width

    # Language List Generator (2 Columns)
    lang_list = ""
    col1_x, col2_x = 30, 240
    y_start = 220
    
    for i, lang in enumerate(languages):
        x = col1_x if i % 2 == 0 else col2_x
        y = y_start + (i // 2) * 25
        lang_list += f"""
        <g transform="translate({x}, {y})">
            <circle cx="5" cy="5" r="4" fill="{lang['color']}"/>
            <text x="20" y="9" class="text-secondary">{lang['name']}</text>
            <text x="130" y="9" class="text-secondary" text-anchor="end">{lang['percentage']}%</text>
        </g>
        """

    # --- 3. ASSEMBLE SVG ---
    svg_content = f"""
    <svg width="480" height="350" viewBox="0 0 480 350" xmlns="http://www.w3.org/2000/svg">
        <style>
            .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58A6FF; }}
            .text-primary {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #E6EDF3; }}
            .text-secondary {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8B949E; }}
            .bar-bg {{ fill: #161B22; rx: 4px; ry: 4px; }}
            .card-bg {{ fill: #0D1117; stroke: #30363D; stroke-width: 1px; rx: 8px; ry: 8px; }}
        </style>
        
        <rect width="478" height="348" x="1" y="1" class="card-bg"/>
        
        <line x1="30" y1="45" x2="450" y2="45" stroke="#21262D" stroke-width="1" />

        <g transform="translate(30, 70)">
            <text class="text-secondary" x="0" y="0">PR Reviews &amp; Feedback</text>
            <text class="text-primary" x="200" y="0">{true_reviews}</text>
            
            <text class="text-secondary" x="250" y="0">PRs Opened</text>
            <text class="text-primary" x="380" y="0">{prs_opened}</text>

            <text class="text-secondary" x="0" y="30">Total Commits</text>
            <text class="text-primary" x="200" y="30">{commits}</text>
            
            <text class="text-secondary" x="250" y="30">Issues Opened</text>
            <text class="text-primary" x="380" y="30">{issues_opened}</text>
        </g>

        <text x="30" y="155" class="header">{'</>'} {total_langs} Languages</text>
        <text x="240" y="155" class="text-primary" text-anchor="middle">Most used languages</text>
        <line x1="30" y1="165" x2="450" y2="165" stroke="#21262D" stroke-width="1" />

        <g transform="translate(30, 180)">
            <rect width="420" height="8" class="bar-bg"/>
            <clipPath id="corners">
                <rect width="420" height="8" rx="4" ry="4"/>
            </clipPath>
            <g clip-path="url(#corners)">
                {progress_bar}
            </g>
        </g>

        {lang_list}
    </svg>
    """

    # --- 4. SAVE FILE ---
    with open("custom_metrics.svg", "w", encoding="utf-8") as file:
        file.write(svg_content.strip())
    print("Generated custom_metrics.svg successfully!")

if __name__ == "__main__":
    main()
