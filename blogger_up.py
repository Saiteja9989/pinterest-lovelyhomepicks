import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import json
from config import BLOGGER_BLOG_ID, GOOGLE_CREDENTIALS

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']
TOKEN_FILE = 'token.json'
CREDS_FILE = 'credentials.json'


def get_blogger_service():
    """Authenticate and return Blogger API service"""
    creds = None

    # Try loading token from environment (GitHub Actions)
    if GOOGLE_CREDENTIALS:
        try:
            token_data = json.loads(GOOGLE_CREDENTIALS)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from env: {e}")

    # Try loading token from file (local run)
    if not creds and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    # If no valid creds, run OAuth flow (local only)
    if not creds or not creds.valid:
        if not os.path.exists(CREDS_FILE):
            raise FileNotFoundError("credentials.json not found. Download from Google Cloud Console.")
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        print(f"\ntoken.json saved. Add its contents to GitHub Secret: GOOGLE_CREDENTIALS_JSON")

    return build('blogger', 'v3', credentials=creds)


def upload_blog_post(title, html_content, labels=None):
    """Upload blog post to Blogger and return the post URL"""
    service = get_blogger_service()

    post_body = {
        "title": title,
        "content": html_content,
        "labels": labels or ["Home Organization", "Amazon Finds", "2026"]
    }

    print(f"\nUploading blog: {title}")
    result = service.posts().insert(
        blogId=BLOGGER_BLOG_ID,
        body=post_body,
        isDraft=False
    ).execute()

    post_url = result.get('url', '')
    print(f"Blog uploaded: {post_url}")
    return post_url


if __name__ == "__main__":
    print("Starting Blogger authentication...")
    service = get_blogger_service()
    print("\n✅ Authentication successful!")
    print("token.json has been saved.")
    print("\nNext step: Copy contents of token.json and add to GitHub Secret as GOOGLE_CREDENTIALS_JSON")
