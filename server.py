from flask import Flask, request, jsonify
import logging
import re
import requests
import io
import datetime
import json

import main
import config

from main import (
    get_session, 
    block_users, 
    remove_all_users_from_blocklist, 
    search_posts, 
    validate_with_ollama
)

# =============================================================================
# LOGGING SETUP (same as before)
# =============================================================================
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

app = Flask(__name__)
app.logger.handlers = []  # Remove default Flask logger handlers
app.logger.propagate = True

# =============================================================================
# IN-MEMORY STORES
# =============================================================================
scanned_posts = {} 
# e.g. scanned_posts = {
#   "did:plc:xxx|rkey:yyyy": {
#       "keyword": "",
#       "is_supportive": True,
#       "reasoning": "...",
#       "post_uri": "at://did:plc:xxx/app.bsky.feed.post/yyyy",
#       "authorDid": "did:plc:xxx",
#       "content": "...",
#   },
#   ...
# }


# =============================================================================
# HELPER: Resolve handle -> DID
# =============================================================================
def resolve_handle_to_did(handle: str) -> str:
    """
    Calls identity.resolveHandle to get a DID from a handle 
    (mirroring the logic from your old gui.py).
    """
    if not handle:
        return ""
    
    url = f"{config.BASE_URL}/com.atproto.identity.resolveHandle?handle={handle}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("did", "")
    except Exception as e:
        logging.warning(f"Could not resolve handle {handle} to DID: {e}")
        return ""


# =============================================================================
# /api/logs
# =============================================================================
@app.route("/api/logs", methods=["GET"])
def get_logs():
    """
    Return the in-memory logs from log_stream as plain text.
    """
    return log_stream.getvalue(), 200, {'Content-Type': 'text/plain'}


# =============================================================================
# /api/config - Returns current config.py data
# =============================================================================
@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({
        "username": config.USERNAME,
        "password": config.APP_PASSWORD,
        "blocklistLink": config.BLOCKLIST_URI,
        "keywords": config.TARGET_KEYWORDS
    })


# =============================================================================
# /api/save-config - Update config.py
# =============================================================================
@app.route("/api/save-config", methods=["POST"])
def save_config():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    new_username = data.get("username", "").strip()
    new_password = data.get("password", "").strip()
    new_link = data.get("blocklistLink", "").strip()
    new_keywords = data.get("keywords", [])

    # (1) Resolve new_username -> DID
    resolved_did = resolve_handle_to_did(new_username)

    # (2) Extract old blocklist DID + ID
    old_uri_pattern = r'^at://(did:plc:[^/]+)/app.bsky.graph.list/(.+)$'
    old_match = re.match(old_uri_pattern, config.BLOCKLIST_URI)
    old_did = ""
    old_blocklist_id = ""
    if old_match:
        old_did = old_match.group(1)
        old_blocklist_id = old_match.group(2)

    # (3) Attempt to parse blocklist ID from new_link
    new_blocklist_id = old_blocklist_id
    if new_link:
        try:
            link_pattern = r"profile/[^/]+/lists/([^/]+)"
            link_match = re.search(link_pattern, new_link)
            if link_match:
                new_blocklist_id = link_match.group(1)
            else:
                logging.warning("Could not parse new blocklist link; using old blocklist ID.")
        except Exception as e:
            logging.warning(f"Error parsing blocklist link: {e}. Using old blocklist ID.")

    # (4) Final DID & blocklist URI
    final_did = resolved_did if resolved_did else old_did
    if final_did and new_blocklist_id:
        final_blocklist_uri = f"at://{final_did}/app.bsky.graph.list/{new_blocklist_id}"
    else:
        final_blocklist_uri = config.BLOCKLIST_URI

    # (5) Update in-memory config
    config.USERNAME = new_username
    config.APP_PASSWORD = new_password
    config.BLOCKLIST_URI = final_blocklist_uri

    config.TARGET_KEYWORDS.clear()
    for kw in new_keywords:
        config.TARGET_KEYWORDS.append(kw)

    logging.info(f"Saving config: USERNAME={config.USERNAME}, DID={final_did}, blocklistID={new_blocklist_id}")

    # (6) Write config.py
    try:
        update_config_file()
    except Exception as e:
        logging.error(f"Error writing config.py: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True})


def update_config_file():
    """
    Rewrites config.py with new values (USERNAME, APP_PASSWORD, BLOCKLIST_URI, TARGET_KEYWORDS).
    """
    with open("config.py", "r") as f:
        lines = f.readlines()

    updated_lines = []
    in_keywords_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("APP_PASSWORD"):
            updated_lines.append(f'APP_PASSWORD = "{config.APP_PASSWORD}"  # Your app password\n')
        elif stripped.startswith("USERNAME"):
            updated_lines.append(f'USERNAME = "{config.USERNAME}"  # Your Bluesky username\n')
        elif stripped.startswith("BLOCKLIST_URI"):
            updated_lines.append(f'BLOCKLIST_URI = "{config.BLOCKLIST_URI}"  # Your blocklist URI\n')
        elif stripped.startswith("TARGET_KEYWORDS"):
            updated_lines.append("TARGET_KEYWORDS = [\n")
            for kw in config.TARGET_KEYWORDS:
                updated_lines.append(f'    "{kw}",\n')
            updated_lines.append("]\n")
            in_keywords_section = True
        elif in_keywords_section:
            if stripped == "]":
                in_keywords_section = False
        else:
            updated_lines.append(line)

    with open("config.py", "w") as f:
        f.writelines(updated_lines)


# =============================================================================
# RUN-SCAN /api/run-scan
# We store post-level classification in scanned_posts for later display
# =============================================================================
@app.route("/api/run-scan", methods=["POST"])
def run_scan():
    try:
        access_token, session_did = main.get_session()
        main.SESSION_DID = session_did

        # Clear old results
        scanned_posts.clear()

        found_users = set()

        for keyword in config.TARGET_KEYWORDS:
            logging.info(f"Searching for keyword: {keyword}")
            posts = search_posts(access_token, keyword)

            for post in posts:
                user_did = post.get("author", {}).get("did")
                content = post.get("record", {}).get("text", post.get("content", ""))
                images = post.get("media", [])
                post_uri = post.get("uri")  # at://did:plc:XXXX/app.bsky.feed.post/YYYY
                rkey = (post_uri or "").split("/")[-1] if post_uri else None

                if not user_did or (not content and not images):
                    logging.warning("Invalid post structure, skipping.")
                    continue

                # Classify text
                classification_result = None
                is_supportive = False
                reasoning = ""

                if content:
                    res = validate_with_ollama(content, keyword)
                    is_supportive = res["is_supportive"]
                    reasoning = res["reasoning"]
                    classification_result = res

                # If text wasn't supportive, check images
                if not is_supportive and images:
                    for image_url in images:
                        img_res = validate_with_ollama(None, keyword, image_url=image_url)
                        if img_res["is_supportive"]:
                            is_supportive = True
                            reasoning = img_res["reasoning"]
                            classification_result = img_res
                            break

                # Store classification in scanned_posts
                unique_id = f"{user_did}|{rkey}"  # e.g. did:plc:xxx|yyyy
                scanned_posts[unique_id] = {
                    "keyword": keyword,
                    "is_supportive": is_supportive,
                    "reasoning": reasoning,
                    "post_uri": post_uri,
                    "authorDid": user_did,
                    "content": content,
                }

                if is_supportive:
                    found_users.add(user_did)

        logging.info(f"Scan complete. Found {len(found_users)} supportive user(s).")
        return jsonify({"foundUsers": list(found_users)})

    except Exception as e:
        logging.error(f"Error during run-scan: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# GET /api/results - Return supportive vs. oppose from scanned_posts
# =============================================================================
@app.route("/api/results", methods=["GET"])
def get_results():
    supportive = []
    oppose = []
    for unique_id, info in scanned_posts.items():
        if info["is_supportive"]:
            supportive.append(info)
        else:
            oppose.append(info)
    return jsonify({"supportive": supportive, "oppose": oppose})


# =============================================================================
# POST /api/override - Manually override classification
# =============================================================================
@app.route("/api/override", methods=["POST"])
def override_classification():
    """
    Expects JSON: { "postUri": string, "isSupportive": bool }
    We'll parse postUri to find the unique_id => "did:plc:xxx|rkey"
    Then override in scanned_posts.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    post_uri = data.get("postUri")
    new_is_supportive = data.get("isSupportive")
    if post_uri is None or new_is_supportive is None:
        return jsonify({"error": "postUri and isSupportive required"}), 400

    # parse at://did:plc:xxxx/app.bsky.feed.post/yyyy
    match = re.match(r"^at://([^/]+)/app\.bsky\.feed\.post/(.+)$", post_uri)
    if not match:
        return jsonify({"error": "Cannot parse postUri"}), 400

    did_part = match.group(1)
    rkey_part = match.group(2)
    unique_id = f"{did_part}|{rkey_part}"

    if unique_id not in scanned_posts:
        return jsonify({"error": "Post not found in current scan results"}), 404

    scanned_posts[unique_id]["is_supportive"] = bool(new_is_supportive)
    scanned_posts[unique_id]["reasoning"] = "(Manually overridden by user.)"

    return jsonify({"success": True})


# =============================================================================
# BLOCK / UNBLOCK
# =============================================================================
@app.route("/api/block", methods=["POST"])
def block_users_endpoint():
    data = request.get_json()
    if not data or "userDids" not in data:
        return jsonify({"error": "No userDids provided"}), 400

    try:
        access_token, session_did = main.get_session()
        main.SESSION_DID = session_did
        blocked_count = block_users(access_token, data["userDids"])
        return jsonify({"blockedCount": blocked_count})
    except Exception as e:
        logging.error(f"Error blocking users: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/unblock-all", methods=["POST"])
def unblock_all_endpoint():
    try:
        access_token, session_did = main.get_session()
        main.SESSION_DID = session_did
        removed_count = remove_all_users_from_blocklist(access_token)
        return jsonify({"removedCount": removed_count})
    except Exception as e:
        logging.error(f"Error unblocking all: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
