# BlueSky Block List Automator

## Overview

The BlueSky Block List Automator is a tool designed to help users manage and automate their block lists on the BlueSky platform. This program allows users to easily add blocked users by scanning for specified terminology posted on BlueSky, ensuring a more controlled and customized online experience.

## Features

- **Automated Blocking**: Automatically block users based on predefined criteria.
- **Batch Processing**: Add multiple users from the block list at once.
- **User-Friendly Interface**: Easy-to-use interface for managing block lists.

## Installation

To install the BlueSky Block List Automator, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/BlueSky-Block-List-Automator.git
    ```
2. Navigate to the project directory:
    ```sh
    cd BlueSky-Block-List-Automator
    ```
3. Install the required dependencies:
    ```sh
    pip install requests
    pip install datetime
    ```

## Usage

To use the BlueSky Block List Automator, follow these steps:

1. Create and add an App Password 
(https://bsky.app/settings/app-passwords).

2. Input your username 
(Example: username.bsky.social)

3. Under Blocklist URI, replace your account ID with your did:plc
 (Found here: https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle=*YOURUSERNAME*.bsky.social) 
 and your List ID which is the last set of characters at the very end of your list URL. 
 (Example: https://bsky.app/profile/yourusername/lists/*LIST_ID*)

4. Update the list of keywords or hashtags you'd like to scan for in the TARGET_HASHTAGS array.

5. Run the main.py file.

## Contributing

We welcome contributions! Please read our [contributing guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.
