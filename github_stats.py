import json
import math
import requests
from collections import defaultdict
from datetime import datetime


def get_github_data(username, token):
    """
    GitHub GraphQL APIからユーザーのリポジトリ情報を取得
    """
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # GraphQL query to get repositories with language data and commit counts
    query = """
    query($username: String!) {
        user(login: $username) {
            repositories(first: 100, ownerAffiliations: OWNER) {
                nodes {
                    name
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

    response = requests.post(url, json={
        "query": query,
        "variables": {"username": username}
    }, headers=headers)

    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.status_code}")

    data = response.json()

    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    return data["data"]["user"]["repositories"]["nodes"]


def create_pie_chart(languages, center_x, center_y, radius):
    """
    言語別コードサイズの円グラフを作成（グラデーション付き）
    """
    total_size = sum(lang["size"] for lang in languages)
    if total_size == 0:
        return ""

    svg_parts = []
    start_angle = 0

    # ドロップシャドウ効果
    svg_parts.append(f'''
    <defs>
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
    </defs>''')

    for i, lang in enumerate(languages):
        angle = (lang["size"] / total_size) * 2 * math.pi
        end_angle = start_angle + angle

        # 円弧の座標計算
        x1 = center_x + radius * math.cos(start_angle)
        y1 = center_y + radius * math.sin(start_angle)
        x2 = center_x + radius * math.cos(end_angle)
        y2 = center_y + radius * math.sin(end_angle)

        # 大きな弧かどうかを判定
        large_arc = "1" if angle > math.pi else "0"

        # パスを作成
        path = f"M {center_x} {center_y} L {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} Z"

        svg_parts.append(f'<path d="{path}" fill="{lang["color"]}" stroke="#f8f9fa" stroke-width="1.5" filter="url(#dropshadow)"/>')

        start_angle = end_angle

    return "\n".join(svg_parts)


def create_bar_chart(repositories, start_x, start_y, max_width, row_height):
    """
    リポジトリ別コミット数の横棒グラフを作成（Top10・グラデーション付き）
    """
    # コミット数順にソート（Top10のみ）
    sorted_repos = sorted(repositories, key=lambda r: r["commit_count"], reverse=True)[:10]

    if not sorted_repos or sorted_repos[0]["commit_count"] == 0:
        return ""

    max_commits = sorted_repos[0]["commit_count"]
    svg_parts = []

    # グラデーション定義
    svg_parts.append(f'''
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
    </defs>''')

    for i, repo in enumerate(sorted_repos):
        y = start_y + i * row_height
        bar_width = (repo["commit_count"] / max_commits) * max_width

        # リポジトリ名（モダンフォント）
        text_color = "#6b7280"
        svg_parts.append(f'<text x="{start_x}" y="{y + 15}" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="500" fill="{text_color}">{repo["name"]}</text>')

        # 棒グラフ（グラデーション付き）
        bar_x = start_x + 170
        svg_parts.append(f'<rect x="{bar_x}" y="{y + 8}" width="{bar_width}" height="6" rx="3" fill="url(#barGradient)" filter="url(#barShadow)"/>')

        # コミット数とサイズ（スタイリッシュ）
        commit_x = bar_x + max_width + 10
        size_kb = repo["size"] / 1024
        svg_parts.append(f'<text x="{commit_x}" y="{y + 15}" font-family="system-ui, -apple-system, monospace" font-size="9" font-weight="600" fill="#6b7280">{repo["commit_count"]} ({size_kb:.0f}KB)</text>')

    return "\n".join(svg_parts)


def create_legend(languages, start_x, start_y):
    """
    言語別凡例を作成（スタイリッシュ版）
    """
    svg_parts = []

    for i, lang in enumerate(languages):
        y = start_y + i * 16  # 行間を狭める

        # 色のボックス（角丸・シャドウ付き）
        svg_parts.append(f'<rect x="{start_x}" y="{y}" width="10" height="10" rx="2" fill="{lang["color"]}" stroke="rgba(0,0,0,0.1)" stroke-width="0.5" filter="url(#dropshadow)"/>')

        # 言語名（モダンフォント）
        svg_parts.append(f'<text x="{start_x + 15}" y="{y + 8}" font-family="system-ui, -apple-system, sans-serif" font-size="10" font-weight="500" fill="#1f2937">{lang["name"]}</text>')

        # サイズ（KB表示・モノスペース）
        size_kb = lang["size"] / 1024
        svg_parts.append(f'<text x="{start_x + 100}" y="{y + 8}" font-family="system-ui, -apple-system, monospace" font-size="8" font-weight="400" fill="#6b7280">{size_kb:.1f}KB</text>')

    return "\n".join(svg_parts)


def create_summary_stats(languages, repositories):
    """
    サマリー統計を作成
    """
    total_size = sum(lang["size"] for lang in languages)
    active_repos = len([r for r in repositories if r["commit_count"] > 0])
    total_commits = sum(r["commit_count"] for r in repositories)

    svg_parts = []

    # 統計カード
    stats = [
        {"icon": "💻", "value": f"{total_size/1024:.1f}KB", "label": "Total Code Size"},
        {"icon": "📦", "value": str(active_repos), "label": "Active Repositories"},
        {"icon": "📈", "value": str(total_commits), "label": "Total Commits"}
    ]

    card_width = 180
    start_x = 40

    for i, stat in enumerate(stats):
        x = start_x + i * (card_width + 20)

        # カード背景
        svg_parts.append(f'''
        <rect x="{x}" y="20" width="{card_width}" height="80" rx="8" fill="white"
              stroke="#e2e8f0" stroke-width="1" filter="url(#cardShadow)"/>
        ''')

        # アイコン
        svg_parts.append(f'<text x="{x + 15}" y="45" font-size="20">{stat["icon"]}</text>')

        # 値
        svg_parts.append(f'<text x="{x + 50}" y="50" font-family="system-ui, -apple-system, sans-serif" font-size="24" font-weight="700" fill="#1e293b">{stat["value"]}</text>')

        # ラベル
        svg_parts.append(f'<text x="{x + 50}" y="70" font-family="system-ui, -apple-system, sans-serif" font-size="12" font-weight="500" fill="#6b7280">{stat["label"]}</text>')

    return "\n".join(svg_parts)


def create_enhanced_pie_chart(languages, center_x, center_y, radius):
    """
    強化された円グラフ（パーセンテージ付き）
    """
    total_size = sum(lang["size"] for lang in languages)
    if total_size == 0:
        return ""

    svg_parts = []
    start_angle = 0

    for i, lang in enumerate(languages):
        percentage = (lang["size"] / total_size) * 100
        angle = (lang["size"] / total_size) * 2 * math.pi
        end_angle = start_angle + angle

        # 円弧の座標計算
        x1 = center_x + radius * math.cos(start_angle)
        y1 = center_y + radius * math.sin(start_angle)
        x2 = center_x + radius * math.cos(end_angle)
        y2 = center_y + radius * math.sin(end_angle)

        # 大きな弧かどうかを判定
        large_arc = "1" if angle > math.pi else "0"

        # パスを作成
        path = f"M {center_x} {center_y} L {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} Z"

        svg_parts.append(f'<path d="{path}" fill="{lang["color"]}" stroke="white" stroke-width="1" filter="url(#dropshadow)"/>')

        start_angle = end_angle

    return "\n".join(svg_parts)


def create_enhanced_legend(languages, start_x, start_y):
    """
    強化された凡例（パーセンテージ付き）
    """
    total_size = sum(lang["size"] for lang in languages)
    svg_parts = []

    # 全言語表示（最大10言語）
    top_languages = languages[:10]

    for i, lang in enumerate(top_languages):
        y = start_y + i * 28
        percentage = (lang["size"] / total_size) * 100
        size_kb = lang["size"] / 1024

        # 色のドット
        svg_parts.append(f'<circle cx="{start_x + 8}" cy="{y + 8}" r="6" fill="{lang["color"]}"/>')

        # 言語名
        svg_parts.append(f'<text x="{start_x + 25}" y="{y + 6}" font-family="Inter, \'SF Pro Display\', \'Helvetica Neue\', Arial, sans-serif" font-size="9" font-weight="500" fill="#1e293b">{lang["name"]}</text>')

        # パーセンテージ
        svg_parts.append(f'<text x="{start_x + 25}" y="{y + 20}" font-family="Inter, \'SF Pro Display\', \'Helvetica Neue\', Arial, sans-serif" font-size="9" font-weight="400" fill="#6b7280">{percentage:.1f}% ({size_kb:.1f}KB)</text>')

    return "\n".join(svg_parts)


def create_enhanced_bar_chart(repositories, start_x, start_y):
    """
    強化された棒グラフ（ドット形式）
    """
    # コミット数順にソート（Top10のみ）
    sorted_repos = sorted(repositories, key=lambda r: r["commit_count"], reverse=True)[:8]

    if not sorted_repos or sorted_repos[0]["commit_count"] == 0:
        return ""

    max_commits = sorted_repos[0]["commit_count"]
    svg_parts = []

    for i, repo in enumerate(sorted_repos):
        y = start_y + i * 28
        # 正規化された値（0-1）
        normalized = repo["commit_count"] / max_commits

        # リポジトリ名
        svg_parts.append(f'<text x="{start_x}" y="{y + 15}" font-family="Inter, \'SF Pro Display\', \'Helvetica Neue\', Arial, sans-serif" font-size="11" font-weight="500" fill="#1e293b">{repo["name"]}</text>')

        # ドット表示
        dot_x = start_x + 200
        for j in range(20):  # 20個のドット
            dot_opacity = 1.0 if j/20 <= normalized else 0.2
            svg_parts.append(f'<circle cx="{dot_x + j * 12}" cy="{y + 10}" r="3" fill="#4f46e5" opacity="{dot_opacity}"/>')

    return "\n".join(svg_parts)


def create_svg(repositories):
    """
    SVG統計チャートを作成（エンハンス版）
    """
    # 除外する言語のリスト
    excluded_languages = {"html", "css", "dockerfile", "makefile", "shell"}

    # データ処理
    language_stats = defaultdict(lambda: {"size": 0, "color": "#000000"})
    processed_repos = []

    for repo in repositories:
        # 言語統計を集計
        for lang_edge in repo["languages"]["edges"]:
            lang_name = lang_edge["node"]["name"]
            # 除外対象の言語をスキップ
            if lang_name.lower() in excluded_languages:
                continue
            language_stats[lang_name]["size"] += lang_edge["size"]
            language_stats[lang_name]["color"] = lang_edge["node"]["color"]

        # リポジトリ情報を処理
        commit_count = 0
        if repo["defaultBranchRef"] and repo["defaultBranchRef"]["target"]:
            commit_count = repo["defaultBranchRef"]["target"]["history"]["totalCount"]

        # リポジトリのサイズを計算
        repo_size = sum(lang_edge["size"] for lang_edge in repo["languages"]["edges"])

        processed_repos.append({
            "name": repo["name"],
            "commit_count": commit_count,
            "size": repo_size
        })

    # 言語データを配列に変換
    languages = [{"name": name, "size": stats["size"], "color": stats["color"]}
                for name, stats in language_stats.items()]
    languages.sort(key=lambda x: x["size"], reverse=True)

    # SVG作成（ダッシュボード版）
    width = 800
    height = 450

    svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <!-- 定義 -->
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


    <!-- タイトル -->
    <text x="400" y="30" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="700" fill="#1e293b" text-anchor="middle">Repository Insights</text>
    <text x="400" y="50" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="12" font-weight="400" fill="#6b7280" text-anchor="middle">Language usage and commit activity</text>

    <!-- 左側: 言語分布 -->
    <rect x="40" y="80" width="350" height="350" fill="white" stroke="#e2e8f0" stroke-width="1" filter="url(#cardShadow)"/>
    <text x="60" y="110" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="700" fill="#1e293b">Language Distribution</text>
    <text x="60" y="130" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="11" font-weight="400" fill="#6b7280">Languages used in your projects</text>

    {create_enhanced_pie_chart(languages, 140, 270, 70)}

    <!-- 言語凡例 -->
    {create_enhanced_legend(languages, 250, 150)}

    <!-- 右側: トップリポジトリ -->
    <rect x="410" y="80" width="350" height="350" fill="white" stroke="#e2e8f0" stroke-width="1" filter="url(#cardShadow)"/>
    <text x="430" y="110" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="700" fill="#1e293b">Top Repositories</text>
    <text x="430" y="130" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="11" font-weight="400" fill="#6b7280">Most active repositories by commit count</text>

    {create_bar_chart(processed_repos, 430, 150, 80, 24)}

    <!-- 生成時刻 -->
    <text x="750" y="20" font-family="Inter, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif" font-size="9" font-weight="400" fill="#9ca3af" text-anchor="end">Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</text>

    </svg>'''

    return svg


def generate_stats(username, token):
    """
    GitHub統計情報を取得してSVGを生成
    """
    try:
        repositories = get_github_data(username, token)
        svg = create_svg(repositories)
        return {
            "success": True,
            "svg": svg,
            "username": username
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import os

    # 環境変数から取得
    username = os.getenv("GITHUB_USERNAME", "kengo-k")
    token = os.getenv("GITHUB_TOKEN", "")

    if not token:
        print("Error: GITHUB_TOKEN environment variable is required")
        exit(1)

    print(f"Generating stats for {username}...")
    result = generate_stats(username, token)

    if result["success"]:
        # SVGファイルとして保存
        with open("github_stats.svg", "w") as f:
            f.write(result["svg"])
        print("SVG saved as github_stats.svg")
    else:
        print(f"Error: {result['error']}")
