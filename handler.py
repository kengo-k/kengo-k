def hello(event, context):
    """
    GitHub repository statistics handler.
    Returns SVG chart of repository statistics for the specified user.
    """
    import os, json
    from github_stats import generate_stats

    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    
    if not username or not token:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "GITHUB_USERNAME and GITHUB_TOKEN are required"}, ensure_ascii=False),
        }

    result = generate_stats(username, token)
    
    if result["success"]:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "image/svg+xml"},
            "body": result["svg"],
        }
    else:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": result["error"]}, ensure_ascii=False),
        }
