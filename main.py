import requests
import datetime
import re
import logging
import json
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

def validate_with_ollama(content, keyword, image_url=None):
    """
BlueSky Block List Moderator Instructions

Purpose:
Validate post content and images using Ollama to determine if they support the specified keyword. The AI model acts as a BlueSky Block List Moderator designed to block users who support the keyword in question while allowing criticism or reporting related to the keyword.

Process:
1. **Language Translation**:
    - **Text Content**: Detect the language of the post content. If it's not in English, translate the text to English before any further processing.
    - **Image Text**: Extract any text present within images. If the extracted text is not in English, translate it to English.

2. **Image Description**:
    - Use Llava:7b to generate a comprehensive description of the image content.

3. **Content Classification**:
    - **Unified Context Creation**:
        - Combine the translated text content and the image description to create a unified context.
    - **Classification**:
        - Use Deepseek-R1:8b to classify the post based on the combined context.
        - Determine the **intent** of the post:
            - **Supportive**: The user explicitly supports the keyword or show some sort of positivity towards the keyword in a way opposite to the definition of Critical.
            - **Critical**: The user criticizes, mocks, shows doubt, negativity or opposition towards the keyword.
            - **Informative/Reporting**: The user reports on or discusses the keyword without expressing support or opposition.

4. **Decision Making**:
    - **Support Detection**:
        - If the classification determines the user **supports** the keyword, mark the post for blocking.
    - **Critical or Informative**:
        - If the classification determines the user is **criticizing** or **reporting** on the keyword, do not flag the post.
    - **Ambiguous Cases**:
        - If the intent is unclear, perform a secondary analysis or flag for human review to prevent false positives.

Roles and Responsibilities:
- **BlueSky Block List Moderator**: The AI model is tasked with identifying and blocking users who express support for the specified keywords. This involves analyzing both textual and visual content to make informed decisions, while distinguishing between support, criticism, and neutral reporting to minimize false flagging.

Parameters:
    content (str): The text content of the post, translated to English if the original contents are written in a different language.
    keyword (str): The keyword to evaluate support against.
    image_url (str, optional): The URL of the image to evaluate.

Returns:
    dict: A dictionary containing:
        - "is_supportive" (bool): True if the user supports the keyword, False otherwise.
        - "reasoning" (str): Explanation for the classification decision including specific evidence from the content itself.
        - "intent" (str): The detected intent of the post (e.g., "supportive", "critical", "informative").

"""

    # Ollama API endpoint
    ollama_url = "http://localhost:11434/api/generate"  # Ensure Ollama is running on this endpoint

    # Enhanced send_request function
    def send_request(model, prompt):
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": 0.2,  # Lower temperature for more deterministic output
            "top_p": 0.9,         # Slightly restrict sampling
            "stream": False
        }
        try:
            response = requests.post(ollama_url, json=payload, timeout=15)
            response.raise_for_status()
            # Extract the raw response text
            raw_response = response.json().get("response", "").strip()
            
            # Use regex to extract JSON block between ```json and ```
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                parsed = json.loads(json_text)
                return parsed
            else:
                # Attempt to find any JSON object in the response
                try:
                    parsed = json.loads(raw_response)
                    return parsed
                except json.JSONDecodeError:
                    logging.warning(f"Could not find JSON block in the response from model {model}: {raw_response}")
                    return {"classification": "unknown", "reasoning": "Invalid JSON response."}
        except requests.exceptions.RequestException as e:
            logging.error(f"Error communicating with Ollama for model {model}: {e}")
            return {"classification": "unknown", "reasoning": f"Request error: {e}"}
        except json.JSONDecodeError:
            logging.warning(f"Could not parse JSON response from model {model}: {raw_response}")
            return {"classification": "unknown", "reasoning": "Invalid JSON response."}

    # 1. If there's an image, describe it using Llava:7b
    image_description = ""
    if image_url:
        image_prompt = (
            f"You are an image description generator. Provide a detailed description of the image at the following URL:\n\n"
            f"Image URL: {image_url}\n\n"
            "Output *must* be a single descriptive paragraph about the image."
        )
        image_response = send_request("llava:7b", image_prompt)
        if image_response.get("output"):
            image_description = image_response["output"]
            logging.info(f"Image description generated: {image_description}")
        else:
            logging.warning("Failed to generate image description.")
            # Proceed without image description if generation fails

    # 2. Construct the classification prompt for Deepseek-R1:8b
    classification_prompt = (
        f"You are a content moderator. Determine if the following post "
        f"SUPPORTS the idea of '{keyword}'. Analyze both the text and the image description (if provided) "
        f"to make your determination. Provide a reasoning for your classification.\n\n"
        "Output *must* be valid JSON in the following format (and nothing else):\n"
        "{\n"
        '  "classification": "support" or "oppose",\n'
        '  "reasoning": "explanation of why you think the post supports or opposes the keyword."\n'
        "}\n\n"
    )

    if content:
        classification_prompt += f"Text Content: {content}\n"
    if image_description:
        classification_prompt += f"Image Description: {image_description}\n"

    # 3. Send classification request to Deepseek-R1:8b
    classification_response = send_request("deepseek-r1:8b", classification_prompt)

    # 4. Parse the classification and reasoning
    classification = classification_response.get("classification", "").lower().strip()
    reasoning = classification_response.get("reasoning", "").strip()

    if classification not in {"support", "oppose"}:
        logging.warning(f"Unexpected classification from Deepseek-R1: {classification}")
        classification = "unknown"
        reasoning = "Invalid classification returned."

    # 5. Determine if the post is supportive
    if classification == "support":
        is_supportive = True
    else:
        # If classification is "oppose" or "unknown", consider the post as not supportive
        is_supportive = False
        # Set a specific reasoning message for ignored posts
        if classification == "oppose":
            reasoning = "Post does not support the keyword and will be ignored."
        elif classification == "unknown":
            reasoning = "Classification could not be determined confidently; post will be ignored."

    return {"is_supportive": is_supportive, "reasoning": reasoning}

def monitor_and_block(auth_token):
    """
    Monitor posts for keywords and validate text and images with Ollama before blocking users.
    Logs reasoning for each classification.
    Returns a list of user DIDs that matched and are supportive of the target keywords.
    """
    found_users = set()

    for keyword in TARGET_KEYWORDS:
        logging.info(f"Searching for keyword: {keyword}")
        
        # Replace with your actual search logic
        posts = search_posts(auth_token, keyword)

        for post in posts:
            user_did = post.get("author", {}).get("did")
            content = post.get("record", {}).get("text", post.get("content", ""))
            images = post.get("media", [])  # Assuming 'media' holds image URLs

            if not user_did or (not content and not images):
                logging.warning("Invalid post structure, skipping.")
                continue

            # Validate text content
            result = None
            if content:
                result = validate_with_ollama(content, keyword)
                logging.info(
                    f"Ollama reasoning for text by user {user_did}: {result['reasoning']}"
                )

            is_supportive = (result["is_supportive"] if result else False)
            
            # If the text isn't supportive, try images
            if not is_supportive and images:
                for image_url in images:
                    img_result = validate_with_ollama(None, keyword, image_url=image_url)
                    logging.info(
                        f"Ollama reasoning for image {image_url} by user {user_did}: {img_result['reasoning']}"
                    )
                    if img_result["is_supportive"]:
                        is_supportive = True
                        break

            if is_supportive:
                logging.info(f"Validated match for '{keyword}' by user {user_did}")
                found_users.add(user_did)

    logging.info(f"Found {len(found_users)} users matching the keywords and passing validation.")
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
