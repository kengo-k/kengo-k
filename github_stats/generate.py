import json
import math
import requests
import fnmatch
import os
from collections import defaultdict
from datetime import datetime


def get_github_data(username, token):
    """
    Fetch user repository information from GitHub GraphQL API
    """
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # GraphQL query to get repositories with language data and commit counts
    query = """
    query($username: String!) {
        user(login: $username) {
            repositories(first: 100, ownerAffiliations: OWNER) {
                nodes {
                    name
                    isPrivate
                    defaultBranchRef {
                        target {
                            ... on Commit {
                                history {
                                    totalCount
                                }
                            }
                        }
                    }
                    languages(first: 20) {
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
    """

    response = requests.post(
        url, json={"query": query, "variables": {"username": username}}, headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.status_code}")

    data = response.json()

    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    return data["data"]["user"]["repositories"]["nodes"]


def create_bar_chart(repositories, start_x, start_y, max_width, row_height):
    """
    Create horizontal bar chart for commit counts by repository (Top 10 with gradients)
    """
    # Sort by commit count (Top 10 only)
    sorted_repos = sorted(repositories, key=lambda r: r["commit_count"], reverse=True)[
        :10
    ]

    if not sorted_repos or sorted_repos[0]["commit_count"] == 0:
        return ""

    max_commits = sorted_repos[0]["commit_count"]
    svg_parts = []

    svg_parts.append(
        f"""
    <defs>
        <linearGradient id="barGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#60a5fa;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#93c5fd;stop-opacity:1" />
        </linearGradient>
        <filter id="barShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="1"/>
            <feOffset dx="0" dy="1" result="offset"/>
            <feComponentTransfer>
                <feFuncA type="linear" slope="0.2"/>
            </feComponentTransfer>
            <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>"""
    )

    for i, repo in enumerate(sorted_repos):
        y = start_y + i * row_height
        bar_width = (repo["commit_count"] / max_commits) * max_width

        # Private lock icon (if repository is private)
        if repo.get("isPrivate", False):
            lock_x = start_x - 14
            lock_y = y + 8
            # Professional lock icon from downloaded SVG (smaller scale)
            svg_parts.append(
                f'''
                <g transform="translate({lock_x}, {lock_y}) scale(0.015)">
                    <path d="M407.543,204.886v-53.345c0.016-41.722-17.033-79.835-44.392-107.153C335.849,17.028,297.736-0.016,256.002,0
                        c-41.738-0.016-79.85,17.028-107.153,44.388c-27.38,27.318-44.404,65.431-44.404,107.153v53.345H55.558v210.128
                        c0,53.572,43.437,96.986,97.002,96.986h206.898c53.565,0,96.985-43.413,96.985-96.986V204.886H407.543z M178.017,151.541
                        c0-10.867,2.178-21.035,6.108-30.342c5.889-13.956,15.822-25.937,28.274-34.349c12.513-8.429,27.306-13.274,43.603-13.29
                        c10.864,0,21.032,2.17,30.338,6.104c13.956,5.893,25.934,15.842,34.346,28.294c8.412,12.485,13.277,27.286,13.298,43.583v53.345
                        H178.017V151.541z M256.002,392.378c-27.672,0-50.114-22.442-50.114-50.11c0-27.676,22.442-50.11,50.114-50.11
                        c27.668,0,50.11,22.434,50.11,50.11C306.112,369.936,283.67,392.378,256.002,392.378z" fill="#6b7280"/>
                </g>
                '''
            )

        # Repository name (always start at the same position)
        text_color = "#6b7280"
        svg_parts.append(
            f'<text x="{start_x}" y="{y + 15}" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="500" fill="{text_color}">{repo["name"]}</text>'
        )

        # Bar chart
        bar_x = start_x + 170
        svg_parts.append(
            f'<rect x="{bar_x}" y="{y + 8}" width="{bar_width}" height="6" rx="3" fill="url(#barGradient)" filter="url(#barShadow)"/>'
        )

        # Commit count and size
        commit_x = bar_x + max_width + 10
        size_kb = repo["size"] / 1024
        svg_parts.append(
            f'<text x="{commit_x}" y="{y + 15}" font-family="system-ui, -apple-system, monospace" font-size="9" font-weight="600" fill="#6b7280">{repo["commit_count"]} ({size_kb:.0f}KB)</text>'
        )

    return "\n".join(svg_parts)


def create_pie_chart(languages, center_x, center_y, radius):
    """
    Create pie chart with percentages
    """
    total_size = sum(lang["size"] for lang in languages)
    if total_size == 0:
        return ""

    svg_parts = []
    start_angle = 0

    for i, lang in enumerate(languages):
        angle = (lang["size"] / total_size) * 2 * math.pi
        end_angle = start_angle + angle

        x1 = center_x + radius * math.cos(start_angle)
        y1 = center_y + radius * math.sin(start_angle)
        x2 = center_x + radius * math.cos(end_angle)
        y2 = center_y + radius * math.sin(end_angle)

        large_arc = "1" if angle > math.pi else "0"
        path = f"M {center_x} {center_y} L {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} Z"
        svg_parts.append(
            f'<path d="{path}" fill="{lang["color"]}" stroke="white" stroke-width="1" filter="url(#dropshadow)"/>'
        )
        start_angle = end_angle

    return "\n".join(svg_parts)


def create_legend(languages, start_x, start_y):
    """
    Create legend with percentages
    """
    total_size = sum(lang["size"] for lang in languages)
    svg_parts = []

    top_languages = languages[:10]

    for i, lang in enumerate(top_languages):
        y = start_y + i * 28
        percentage = (lang["size"] / total_size) * 100
        size_kb = lang["size"] / 1024

        svg_parts.append(
            f'<circle cx="{start_x + 8}" cy="{y + 8}" r="6" fill="{lang["color"]}"/>'
        )

        svg_parts.append(
            f'<text x="{start_x + 25}" y="{y + 6}" font-family="Inter, \'SF Pro Display\', \'Helvetica Neue\', Arial, sans-serif" font-size="9" font-weight="500" fill="#1e293b">{lang["name"]}</text>'
        )

        svg_parts.append(
            f'<text x="{start_x + 25}" y="{y + 20}" font-family="Inter, \'SF Pro Display\', \'Helvetica Neue\', Arial, sans-serif" font-size="9" font-weight="400" fill="#6b7280">{percentage:.1f}% ({size_kb:.1f}KB)</text>'
        )

    return "\n".join(svg_parts)


def load_config():
    """
    Load configuration from config.json
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        # Default configuration if file doesn't exist
        return {
            "excluded_languages": ["html", "css", "dockerfile", "makefile", "shell"],
            "excluded_repositories": ["zenn-posts", "kengo-k", "*example"]
        }
    except json.JSONDecodeError:
        print("Warning: Invalid config.json format, using default configuration")
        return {
            "excluded_languages": ["html", "css", "dockerfile", "makefile", "shell"],
            "excluded_repositories": ["zenn-posts", "kengo-k", "*example"]
        }


def create_svg(repositories):
    """
    Create SVG statistics chart
    """
    # Load configuration
    config = load_config()
    excluded_languages = set(config["excluded_languages"])
    excluded_repositories = set(config["excluded_repositories"])

    # Data processing
    language_stats = defaultdict(lambda: {"size": 0, "color": "#000000"})
    processed_repos = []

    for repo in repositories:
        # Skip excluded repositories (with wildcard support)
        if any(
            fnmatch.fnmatch(repo["name"], pattern) for pattern in excluded_repositories
        ):
            continue

        # Aggregate language statistics
        for lang_edge in repo["languages"]["edges"]:
            lang_name = lang_edge["node"]["name"]
            # Skip excluded languages
            if lang_name.lower() in excluded_languages:
                continue
            language_stats[lang_name]["size"] += lang_edge["size"]
            language_stats[lang_name]["color"] = lang_edge["node"]["color"]

        # Process repository information
        commit_count = 0
        if repo["defaultBranchRef"] and repo["defaultBranchRef"]["target"]:
            commit_count = repo["defaultBranchRef"]["target"]["history"]["totalCount"]

        # Calculate repository size
        repo_size = sum(lang_edge["size"] for lang_edge in repo["languages"]["edges"])

        processed_repos.append(
            {
                "name": repo["name"], 
                "commit_count": commit_count, 
                "size": repo_size,
                "isPrivate": repo.get("isPrivate", False)
            }
        )

    # Convert language data to array
    languages = [
        {"name": name, "size": stats["size"], "color": stats["color"]}
        for name, stats in language_stats.items()
    ]
    languages.sort(key=lambda x: x["size"], reverse=True)

    # Create SVG (dashboard version)
    width = 850
    height = 450

    svg = f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Definitions -->
    <defs>
        <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#f8fafc;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#f1f5f9;stop-opacity:1" />
        </linearGradient>
        <filter id="dropshadow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
            <feOffset dx="2" dy="2" result="offset"/>
            <feComponentTransfer>
                <feFuncA type="linear" slope="0.3"/>
            </feComponentTransfer>
            <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <filter id="cardShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
            <feOffset dx="0" dy="1" result="offset"/>
            <feComponentTransfer>
                <feFuncA type="linear" slope="0.05"/>
            </feComponentTransfer>
            <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>


    <!-- Title -->
    <text x="400" y="30" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="700" fill="#1e293b" text-anchor="middle">Repository Insights</text>
    <text x="400" y="50" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="12" font-weight="400" fill="#6b7280" text-anchor="middle">Language usage and commit activity</text>

    <!-- Left side: Language distribution -->
    <rect x="40" y="80" width="375" height="350" fill="white" stroke="#e2e8f0" stroke-width="1" filter="url(#cardShadow)"/>
    <text x="60" y="110" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="700" fill="#1e293b">Language Distribution</text>
    <text x="60" y="130" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="11" font-weight="400" fill="#6b7280">Languages used in your projects</text>

    {create_pie_chart(languages, 140, 270, 70)}

    <!-- Language legend -->
    {create_legend(languages, 250, 150)}

    <!-- Right side: Top repositories -->
    <rect x="435" y="80" width="375" height="350" fill="white" stroke="#e2e8f0" stroke-width="1" filter="url(#cardShadow)"/>
    <text x="455" y="110" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="700" fill="#1e293b">Top Repositories</text>
    <text x="455" y="130" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="11" font-weight="400" fill="#6b7280">Most active repositories by commit count</text>

    {create_bar_chart(processed_repos, 465, 150, 85, 24)}

    <!-- Generation time -->
    <text x="800" y="20" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="9" font-weight="400" fill="#9ca3af" text-anchor="end">Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC</text>

    </svg>"""

    return svg


def generate_stats(username, token):
    """
    Fetch GitHub statistics and generate SVG
    """
    try:
        repositories = get_github_data(username, token)
        svg = create_svg(repositories)
        return {"success": True, "svg": svg, "username": username}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import os

    username = os.getenv("GITHUB_USERNAME", "kengo-k")
    token = os.getenv("GITHUB_TOKEN", "")

    if not token:
        print("Error: GITHUB_TOKEN environment variable is required")
        exit(1)

    print(f"Generating stats for {username}...")
    result = generate_stats(username, token)

    if result["success"]:
        with open("github_stats.svg", "w") as f:
            f.write(result["svg"])
        print("SVG saved as github_stats.svg")
    else:
        print(f"Error: {result['error']}")
