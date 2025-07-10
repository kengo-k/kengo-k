import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError


def upload_to_s3(svg_content, bucket_name=None, object_key=None):
    """
    Upload SVG content to S3

    Args:
        svg_content (str): SVG content to upload
        bucket_name (str): S3 bucket name (can be obtained from S3_BUCKET_NAME env var)
        object_key (str): S3 object key (default: github-stats.svg)

    Returns:
        dict: Upload result
    """
    try:
        if not bucket_name:
            bucket_name = os.getenv("S3_BUCKET_NAME")

        if not bucket_name:
            raise ValueError(
                "S3 bucket name is required. Set S3_BUCKET_NAME environment variable or pass bucket_name parameter."
            )

        if not object_key:
            object_key = "github-stats.svg"

        s3_client = boto3.client("s3")

        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=svg_content.encode("utf-8"),
            ContentType="image/svg+xml",
            CacheControl="max-age=3600",
        )

        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

        return {
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "url": s3_url,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

    except NoCredentialsError:
        return {
            "success": False,
            "error": "AWS credentials not found. Configure AWS credentials.",
        }
    except ClientError as e:
        return {
            "success": False,
            "error": f"AWS S3 error: {e.response['Error']['Message']}",
        }
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {str(e)}"}


def upload_stats_to_s3(svg_content, username=None):
    """
    Upload GitHub stats SVG to S3 with username-based key

    Args:
        svg_content (str): SVG content to upload
        username (str): GitHub username (used in filename)

    Returns:
        dict: Upload result
    """
    if username:
        object_key = f"github-stats/{username}.svg"
    else:
        object_key = "github-stats.svg"

    return upload_to_s3(svg_content, object_key=object_key)


if __name__ == "__main__":
    svg_file = "github_stats.svg"

    if not os.path.exists(svg_file):
        print(f"Error: Required file '{svg_file}' not found in current directory.")
        print("Please run 'python generate.py' first to generate the SVG file.")
        exit(1)

    print(f"Found {svg_file}, uploading to S3...")

    with open(svg_file, "r", encoding="utf-8") as f:
        svg_content = f.read()

    result = upload_to_s3(svg_content, object_key="github-stats.svg")

    if result["success"]:
        print(f"Upload successful!")
        print(f"Bucket: {result['bucket']}")
        print(f"Key: {result['key']}")
        print(f"URL: {result['url']}")
        print(f"Uploaded at: {result['uploaded_at']}")
    else:
        print(f"Upload failed: {result['error']}")
        exit(1)
