import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError


def upload_to_s3(svg_content, bucket_name=None, object_key=None):
    """
    SVGコンテンツをS3にアップロード
    
    Args:
        svg_content (str): アップロードするSVGの内容
        bucket_name (str): S3バケット名（環境変数S3_BUCKET_NAMEから取得可能）
        object_key (str): S3オブジェクトキー（デフォルト: github-stats.svg）
    
    Returns:
        dict: アップロード結果
    """
    try:
        # バケット名を環境変数から取得
        if not bucket_name:
            bucket_name = os.getenv("S3_BUCKET_NAME")
            
        if not bucket_name:
            raise ValueError("S3 bucket name is required. Set S3_BUCKET_NAME environment variable or pass bucket_name parameter.")
        
        # オブジェクトキーのデフォルト設定
        if not object_key:
            object_key = "github-stats.svg"
        
        # S3クライアントを作成
        s3_client = boto3.client('s3')
        
        # SVGをS3にアップロード
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=svg_content.encode('utf-8'),
            ContentType='image/svg+xml',
            CacheControl='max-age=3600'  # 1時間キャッシュ
        )
        
        # パブリックURLを生成
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
        
        return {
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "url": s3_url,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
    except NoCredentialsError:
        return {
            "success": False,
            "error": "AWS credentials not found. Configure AWS credentials."
        }
    except ClientError as e:
        return {
            "success": False,
            "error": f"AWS S3 error: {e.response['Error']['Message']}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}"
        }


def upload_stats_to_s3(svg_content, username=None):
    """
    GitHub統計SVGをS3にアップロード（ユーザー名ベースのキー）
    
    Args:
        svg_content (str): アップロードするSVGの内容
        username (str): GitHubユーザー名（ファイル名に使用）
    
    Returns:
        dict: アップロード結果
    """
    # ユーザー名ベースのオブジェクトキーを生成
    if username:
        object_key = f"github-stats/{username}.svg"
    else:
        object_key = "github-stats.svg"
    
    return upload_to_s3(svg_content, object_key=object_key)


if __name__ == "__main__":
    # github_stats.svgファイルが存在するかチェック
    svg_file = "github_stats.svg"
    
    if not os.path.exists(svg_file):
        print(f"Error: Required file '{svg_file}' not found in current directory.")
        print("Please run 'python github_stats.py' first to generate the SVG file.")
        exit(1)
    
    print(f"Found {svg_file}, uploading to S3...")
    
    # ファイルからSVGを読み込み
    with open(svg_file, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    # S3にアップロード
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