def hello(event, context):
    """
    GitHub repository statistics handler.
    Returns repository language statistics for the specified user.
    """
    import os, json, requests

    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    
    if not username or not token:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "GITHUB_USERNAME and GITHUB_TOKEN are required"}, ensure_ascii=False),
        }

    try:
        # GitHub GraphQL API endpoint
        url = "https://api.github.com/graphql"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # GraphQL query to get repositories with language data
        query = """
        query($username: String!) {
            user(login: $username) {
                repositories(first: 100, ownerAffiliations: OWNER) {
                    nodes {
                        name
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
            return {
                "statusCode": response.status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"GitHub API error: {response.status_code}"}, ensure_ascii=False),
            }
        
        data = response.json()
        
        if "errors" in data:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": data["errors"]}, ensure_ascii=False),
            }
        
        # Process repository data
        repositories = data["data"]["user"]["repositories"]["nodes"]
        result = []
        
        for repo in repositories:
            repo_data = {
                "name": repo["name"],
                "languages": []
            }
            
            for lang_edge in repo["languages"]["edges"]:
                repo_data["languages"].append({
                    "name": lang_edge["node"]["name"],
                    "size": lang_edge["size"],
                    "color": lang_edge["node"]["color"]
                })
            
            result.append(repo_data)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "username": username,
                "repositories": result
            }, ensure_ascii=False),
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}, ensure_ascii=False),
        }
