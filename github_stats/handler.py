def hello(event, context):
    """
    GitHub repository statistics handler.
    Generates SVG chart and uploads to S3, then returns success/error status.
    """
    import os, json
    from github_stats import generate_stats
    from s3_uploader import upload_to_s3

    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    
    if not username or not token:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "GITHUB_USERNAME and GITHUB_TOKEN are required"}, ensure_ascii=False),
        }

    # Generate GitHub stats SVG
    result = generate_stats(username, token)
    
    if not result["success"]:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"SVG generation failed: {result['error']}"}, ensure_ascii=False),
        }

    # Upload to S3
    upload_result = upload_to_s3(result["svg"], object_key="github-stats.svg")
    
    if upload_result["success"]:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "GitHub stats generated and uploaded successfully",
                "username": username,
                "s3_url": upload_result["url"],
                "uploaded_at": upload_result["uploaded_at"]
            }, ensure_ascii=False),
        }
    else:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"S3 upload failed: {upload_result['error']}"}, ensure_ascii=False),
        }
