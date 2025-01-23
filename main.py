import requests
import datetime

# Constants
BASE_URL = "https://bsky.social/xrpc" # DON'T CHANGE THIS
APP_PASSWORD = "xxxx-xxxx-xxxx"  # Replace with your app password, which can be generated in the BlueSky Account Settings.
USERNAME = "user.bsky.social"  # Replace with your Bluesky username
BLOCKLIST_URI = "at://did:plc:YOUR_ACCOUNT_ID/app.bsky.graph.list/YOUR_LIST_ID"  # Replace with your blocklist ID and Account ID.

# Hashtags or phrases to monitor. Replace them with whichever ones you want.
TARGET_HASHTAGS = ["#MAGA", "Democrats", "Republicans"]

def get_session():
    """Authenticate using app password and get session tokens."""
    url = f"{BASE_URL}/com.atproto.server.createSession"
    payload = {"identifier": USERNAME, "password": APP_PASSWORD}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    session_data = response.json()
    return session_data["accessJwt"], session_data["did"]

def search_posts(auth_token, hashtag):
    """Search for posts containing the specified hashtag."""
    url = f"{BASE_URL}/app.bsky.feed.searchPosts"
    headers = {"Authorization": f"Bearer {auth_token}"}
    params = {"q": hashtag, "limit": 100}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()["posts"]

def add_user_to_blocklist(auth_token, user_did):
    """Add a user to the blocklist."""
    url = f"{BASE_URL}/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {auth_token}"}
    record = {
        "$type": "app.bsky.graph.listitem",
        "subject": user_did,  # User's DID
        "list": BLOCKLIST_URI,  # Blocklist URI
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    response = requests.post(url, headers=headers, json={
        "repo": SESSION_DID,
        "collection": "app.bsky.graph.listitem",
        "record": record
    })
    if response.status_code == 200:
        print(f"User {user_did} added to blocklist.")
    else:
        print(f"Failed to block user {user_did}: {response.text}")


def monitor_and_block(auth_token):
    """Monitor posts for target hashtags and block users."""
    for hashtag in TARGET_HASHTAGS:
        posts = search_posts(auth_token, hashtag)
        for post in posts:
            user_did = post["author"]["did"]
            print(f"Detected post with target hashtag by user {user_did}. Blocking...")
            add_user_to_blocklist(auth_token, user_did)

if __name__ == "__main__":
    # Authenticate and get session tokens
    ACCESS_TOKEN, SESSION_DID = get_session()

    # Start monitoring and blocking
    monitor_and_block(ACCESS_TOKEN)
