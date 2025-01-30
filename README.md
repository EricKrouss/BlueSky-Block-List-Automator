# Bluesky Shield
![image](https://github.com/user-attachments/assets/9576baa5-81ff-45c2-9d8d-1caa2a58e59e)



## Overview

The BlueSky Block List Automator is a tool designed to help users manage and automate their block lists on the BlueSky platform. This program allows users to easily add blocked users by scanning for specified terminology posted on BlueSky, ensuring a more controlled and customized online experience.

## Features

- **Automated Blocking**: Automatically block users based on predefined criteria.
- **User-Friendly Interface**: Easy-to-use interface for managing block lists.

## Limitations
- The main limitation is that it can only scan for 50-100 users at a time. While faster than manually blocking people, you may have to run it multiple times and are going to be limited by Bluesky's rate limits.
- The AI can trip up sometimes, so manual review for some items may still be required!

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

## Usage & Configuration

To use the BlueSky Block List Automator, follow these steps:

1. Create and add an App Password 
(https://bsky.app/settings/app-passwords).

2. Run the server.py file.

3. Start an http server at the root directory of repository.

4. Go to the 'Settings' tab, add your Bluesky Username, App password, and Block List URL and press 'Save Settings'. 

5. Update the list of keywords or hashtags you'd like to scan for in the 'Blocklist' tab.

6. Press "Run Scan".

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.
