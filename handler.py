def hello(event, context):
    """
    Simple AWS Lambda handler for connectivity test.
    Returns a greeting string and echoes the received event.
    """
    import os, json

    greeting = "Hello " + os.getenv("GREETING", "World!")
    body = {
        "greeting": greeting,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
