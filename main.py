import requests
import datetime
import re
import logging
from config import BASE_URL, APP_PASSWORD, USERNAME, BLOCKLIST_URI, TARGET_KEYWORDS

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_session():
    """Authenticate using app password and get session tokens."""
    url = f"{BASE_URL}/com.atproto.server.createSession"
    payload = {"identifier": USERNAME, "password": APP_PASSWORD}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    session_data = response.json()
    logging.info("Successfully authenticated.")
    return session_data["accessJwt"], session_data["did"]

def search_posts(auth_token, keyword):
    """Search for posts containing the specified keyword."""
    url = f"{BASE_URL}/app.bsky.feed.searchPosts"
    headers = {"Authorization": f"Bearer {auth_token}"}
    params = {"q": keyword, "limit": 100}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        logging.error(f"Error searching posts for keyword '{keyword}': {response.text}")
        return []
    
    try:
        posts = response.json().get("posts", [])
        if not posts:
            logging.warning(f"No posts found for keyword: {keyword}")
        return posts
    except (KeyError, ValueError) as e:
        logging.error(f"Error parsing response for keyword '{keyword}': {e}")
        return []


def add_user_to_blocklist(auth_token, user_did):
    """Add a user to the blocklist."""
    url = f"{BASE_URL}/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {auth_token}"}
    record = {
        "$type": "app.bsky.graph.listitem",
        "subject": user_did,
        "list": BLOCKLIST_URI,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    response = requests.post(url, headers=headers, json={
        "repo": SESSION_DID,
        "collection": "app.bsky.graph.listitem",
        "record": record
    })
    if response.status_code == 200:
        logging.info(f"Successfully blocked user: {user_did}")
        return True
    else:
        logging.error(f"Failed to block user {user_did}: {response.text}")
        return False

def monitor_and_block(auth_token):
    """Monitor posts for keywords and return detected users."""
    found_users = set()

    for keyword in TARGET_KEYWORDS:
        logging.info(f"Searching for keyword: {keyword}")
        posts = search_posts(auth_token, keyword)
        
        for post in posts:
            # Attempt to extract user DID and content
            user_did = post.get("author", {}).get("did")
            content = post.get("record", {}).get("text", post.get("content", ""))
            
            if not user_did or not content:
                logging.warning("Invalid post structure, skipping.")
                continue

            if keyword.lower() in content.lower():
                logging.info(f"Keyword match found for '{keyword}' by user {user_did}")
                found_users.add(user_did)

    logging.info(f"Found {len(found_users)} users matching the keywords.")
    return list(found_users)

def block_users(auth_token, user_dids):
    """Block a list of users and return the count of blocked users."""
    blocked_count = 0
    for user_did in user_dids:
        if add_user_to_blocklist(auth_token, user_did):
            blocked_count += 1
    return blocked_count

def remove_all_users_from_blocklist(auth_token):
    """Remove all users from the block list."""
    url = f"{BASE_URL}/app.bsky.graph.getList"
    headers = {"Authorization": f"Bearer {auth_token}"}
    params = {"list": BLOCKLIST_URI}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    users = response.json().get("items", [])
    if not users:
        logging.info("The block list is already empty.")
        return 0
    removed_count = 0
    for user in users:
        user_did = user["subject"]
        list_item_uri = user["uri"]
        delete_url = f"{BASE_URL}/com.atproto.repo.deleteRecord"
        delete_payload = {
            "repo": SESSION_DID,
            "collection": "app.bsky.graph.listitem",
            "rkey": list_item_uri.split("/")[-1]
        }
        delete_response = requests.post(delete_url, headers=headers, json=delete_payload)
        if delete_response.status_code == 200:
            logging.info(f"Removed user {user_did} from the block list.")
            removed_count += 1
        else:
            logging.error(f"Failed to remove user {user_did}: {delete_response.text}")
    return removed_count

if __name__ == "__main__":
    ACCESS_TOKEN, SESSION_DID = get_session()
    found_users = monitor_and_block(ACCESS_TOKEN)
    if found_users:
        confirm = input("Block these users? (yes/no): ").strip().lower()
        if confirm == "yes":
            blocked = block_users(ACCESS_TOKEN, found_users)
            logging.info(f"Blocked {blocked} users.")
