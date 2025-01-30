import requests
import datetime
import re
import logging
import json
from typing import Optional, Dict, List
from config import BASE_URL, APP_PASSWORD, USERNAME, BLOCKLIST_URI, TARGET_KEYWORDS

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
OLLAMA_URL = "http://localhost:11434/api/generate"  # Ollama API endpoint

def get_session():
    """Authenticate using app password and get session tokens."""
    url = f"{BASE_URL}/com.atproto.server.createSession"
    payload = {"identifier": USERNAME, "password": APP_PASSWORD}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        session_data = response.json()
        logging.info("Successfully authenticated.")
        return session_data["accessJwt"], session_data["did"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Authentication failed: {e}")
        raise

def search_posts(auth_token: str, keyword: str) -> List[Dict]:
    """Search for posts containing the specified keyword."""
    url = f"{BASE_URL}/app.bsky.feed.searchPosts"
    headers = {"Authorization": f"Bearer {auth_token}"}
    params = {"q": keyword, "limit": 100}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        posts = response.json().get("posts", [])
        if not posts:
            logging.warning(f"No posts found for keyword: {keyword}")
        return posts
    except requests.exceptions.RequestException as e:
        logging.error(f"Error searching posts for keyword '{keyword}': {e}")
        return []
    except (KeyError, ValueError) as e:
        logging.error(f"Error parsing response for keyword '{keyword}': {e}")
        return []

def add_user_to_blocklist(auth_token: str, user_did: str, session_did: str) -> bool:
    """Add a user to the blocklist."""
    url = f"{BASE_URL}/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {auth_token}"}
    record = {
        "$type": "app.bsky.graph.listitem",
        "subject": user_did,
        "list": BLOCKLIST_URI,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    try:
        response = requests.post(url, headers=headers, json={
            "repo": session_did,
            "collection": "app.bsky.graph.listitem",
            "record": record
        })
        response.raise_for_status()
        logging.info(f"Successfully blocked user: {user_did}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to block user {user_did}: {e}")
        return False

def send_request(model: str, prompt: str) -> Dict:
    """
    Send a prompt to the specified model via the Ollama API and retrieve the response.

    Parameters:
        model (str): The name of the model to use.
        prompt (str): The prompt to send to the model.

    Returns:
        dict: The parsed JSON response from the model.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "options": {
            "temperature": 0.2,  # Lower temperature for deterministic output
            "top_p": 0.9,        # Restrict sampling
            "max_tokens": 5000    # Maximum tokens to generate
        },
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        raw_response = response.json().get("response", "").strip()
        
        # Attempt to extract JSON from the response
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
            parsed = json.loads(json_text)
            logging.debug(f"Parsed JSON response from {model}: {parsed}")
            return parsed
        else:
            # Attempt to parse any JSON object in the response
            parsed = json.loads(raw_response)
            logging.debug(f"Parsed JSON response from {model}: {parsed}")
            return parsed
    except requests.exceptions.RequestException as e:
        logging.error(f"API request error for model '{model}': {e}")
        return {"classification": "unknown", "reasoning": f"API request failed: {e}"}
    except json.JSONDecodeError:
        logging.warning(f"JSON parsing failed for model '{model}'. Raw response: {raw_response}")
        return {"classification": "unknown", "reasoning": "Invalid JSON response."}

def generate_image_description(image_url: str) -> Optional[str]:
    """
    Generate a detailed description of the image using the Llava:7b model.

    Parameters:
        image_url (str): The URL of the image.

    Returns:
        Optional[str]: Description of the image or None if generation fails.
    """
    image_prompt = (
        "You are an advanced image description generator. Provide a detailed and comprehensive description "
        f"of the image located at the following URL:\n\nImage URL: {image_url}\n\n"
        "Ensure the description is precise, capturing all relevant elements in a single paragraph."
    )
    response = send_request("llava:7b", image_prompt)
    description = response.get("output", "")
    if description:
        logging.info(f"Image description generated: {description}")
        return description
    else:
        logging.warning("Failed to generate image description.")
        return None

def classify_content(text: Optional[str], image_description: Optional[str], keyword: str) -> Dict:
    """
    Classify the content's intent regarding the specified keyword.

    Parameters:
        text (Optional[str]): The textual content of the post.
        image_description (Optional[str]): Description of the image content.
        keyword (str): The keyword to evaluate support against.

    Returns:
        dict: Classification result with 'intent' and 'reasoning'.
    """
    classification_prompt = (
        "You are a proficient content moderator. Analyze the following post to determine its intent "
        f"regarding the keyword '{keyword}'. Consider both the text and the image description (if provided). "
        "Categorize the intent as one of the following: 'supportive', 'critical', 'informative/reporting'. "
        "Provide a clear and concise reasoning for your classification.\n\n"
        "Ensure the output is valid JSON in the specified format only:\n"
        "{\n"
        '  "intent": "supportive" | "critical" | "informative/reporting",\n'
        '  "reasoning": "Detailed explanation."\n'
        "}\n\n"
    )
    
    if text:
        classification_prompt += f"Text Content: {text}\n"
    if image_description:
        classification_prompt += f"Image Description: {image_description}\n"

    response = send_request("deepseek-r1:8b", classification_prompt)
    intent = response.get("intent", "").lower().strip()
    reasoning = response.get("reasoning", "").strip()

    if intent not in {"supportive", "critical", "informative/reporting"}:
        logging.warning(f"Unexpected intent classification: {intent}")
        intent = "unknown"
        reasoning = "Invalid intent classification returned."

    # Log the classification details
    logging.info(f"Classification Result - Intent: {intent}, Reasoning: {reasoning}")

    return {"intent": intent, "reasoning": reasoning}

def validate_with_ollama(content: Optional[str], keyword: str, image_url: Optional[str] = None) -> Dict:
    """
    Validate the post content and image to determine supportiveness/if the user is in agreement with the idea and/or concept surrounding the keyword.

    Parameters:
        content (Optional[str]): The text content of the post.
        keyword (str): The keyword to evaluate support against.
        image_url (Optional[str]): The URL of the image to evaluate.

    Returns:
        dict: Contains 'is_supportive', 'intent', and 'reasoning'.
    """
    logging.info("Starting validation with Ollama.")

    # Step 1: Language Translation
    if content:
        # Placeholder: Implement actual translation if necessary
        logging.info("Content is assumed to be in English.")
    
    if image_url:
        # Placeholder: Implement actual OCR and translation if necessary
        logging.info("Image text extraction and translation are assumed to be handled elsewhere.")
    
    # Step 2: Image Description
    image_description = ""
    if image_url:
        image_description = generate_image_description(image_url)
        if not image_description:
            logging.warning("Proceeding without image description due to generation failure.")

    # Step 3: Content Classification
    classification_result = classify_content(content, image_description, keyword)
    intent = classification_result.get("intent", "unknown")
    reasoning = classification_result.get("reasoning", "No reasoning provided.")

    # Step 4: Decision Making
    is_supportive = False
    if intent == "supportive":
        is_supportive = True
    elif intent in {"critical", "informative/reporting"}:
        is_supportive = False
    else:
        reasoning = "Intent unclear; post requires human review."

    # Log the final decision
    logging.info(f"Final Decision - Is Supportive: {is_supportive}, Intent: {intent}, Reasoning: {reasoning}")

    return {
        "is_supportive": is_supportive,
        "intent": intent,
        "reasoning": reasoning
    }

def monitor_and_block(auth_token: str, session_did: str) -> List[str]:
    """
    Monitor posts for target keywords, validate them, and identify users who are supportive/in agreement with the ideas/concept of the keyword.

    Parameters:
        auth_token (str): Authentication token for API access.
        session_did (str): DID of the session user.

    Returns:
        List[str]: List of user DIDs who are supportive of the target keywords.
    """
    logging.info("Starting monitoring and blocking process.")
    found_users = set()

    for keyword in TARGET_KEYWORDS:
        logging.info(f"Searching for keyword: {keyword}")
        posts = search_posts(auth_token, keyword)

        for post in posts:
            user_did = post.get("author", {}).get("did")
            content = post.get("record", {}).get("text", post.get("content", ""))
            images = post.get("media", [])  # Assuming 'media' contains image URLs

            if not user_did or (not content and not images):
                logging.warning("Invalid post structure; skipping.")
                continue

            logging.info(f"Processing post by user {user_did} for keyword '{keyword}'.")

            # Initialize validation result
            validation_result = {
                "is_supportive": False,
                "intent": "unknown",
                "reasoning": "No analysis performed."
            }

            # Validate text content
            if content:
                logging.info(f"Validating text content for user {user_did}.")
                result = validate_with_ollama(content, keyword)
                logging.info(f"Ollama reasoning for text by user {user_did}: {result['reasoning']}")
                if result["is_supportive"]:
                    validation_result = result
                else:
                    # If not supportive, proceed to check images
                    logging.info(f"Text content does not indicate support for keyword '{keyword}'.")

            # Validate images if text is not supportive
            if not validation_result["is_supportive"] and images:
                for image_url in images:
                    logging.info(f"Validating image {image_url} for user {user_did}.")
                    img_result = validate_with_ollama(None, keyword, image_url=image_url)
                    logging.info(f"Ollama reasoning for image {image_url} by user {user_did}: {img_result['reasoning']}")
                    if img_result["is_supportive"]:
                        validation_result = img_result
                        logging.info(f"Image {image_url} indicates support for keyword '{keyword}'.")
                        break  # Stop checking other images if supportive
                    else:
                        logging.info(f"Image {image_url} does not indicate support for keyword '{keyword}'.")

            # Decision based on validation results
            if validation_result["is_supportive"]:
                logging.info(f"User {user_did} supports the keyword '{keyword}'. Marking for blocking.")
                found_users.add(user_did)
            else:
                logging.info(f"User {user_did} does not support the keyword '{keyword}'. Intent: {validation_result['intent']}.")

    logging.info(f"Monitoring complete. {len(found_users)} users found supportive of the target keywords.")
    return list(found_users)

def block_users(auth_token: str, user_dids: List[str], session_did: str) -> int:
    """Block a list of users and return the count of blocked users."""
    blocked_count = 0
    for user_did in user_dids:
        if add_user_to_blocklist(auth_token, user_did, session_did):
            blocked_count += 1
    logging.info(f"Total blocked users: {blocked_count}")
    return blocked_count

def remove_all_users_from_blocklist(auth_token: str, session_did: str) -> int:
    """Remove all users from the block list."""
    ...

if __name__ == "__main__":
    try:
        ACCESS_TOKEN, SESSION_DID = get_session()
    except Exception as e:
        logging.critical(f"Exiting due to authentication failure: {e}")
        exit(1)
    
    found_users = monitor_and_block(ACCESS_TOKEN, SESSION_DID)
    if found_users:
        confirm = input("Block these users? (yes/no): ").strip().lower()
        if confirm == "yes":
            blocked = block_users(ACCESS_TOKEN, found_users, SESSION_DID)
            logging.info(f"Blocked {blocked} users.")
        else:
            logging.info("Blocking users canceled by the user.")
    else:
        logging.info("No supportive users found to block.")
