# BlueSky Block List Automator
![image](https://github.com/user-attachments/assets/0baadc77-1d2e-4a5b-ae75-6fe5b39fd385)


## Overview

The BlueSky Block List Automator is a tool designed to help users manage and automate their block lists on the BlueSky platform. This program allows users to easily add blocked users by scanning for specified terminology posted on BlueSky, ensuring a more controlled and customized online experience.

## Features

- **Automated Blocking**: Automatically block users based on predefined criteria.
- **User-Friendly Interface**: Easy-to-use interface for managing block lists.

## Limitations
- The main limitation is that it can only scan for 50-100 users at a time. While faster than manually blocking people, you may have to run it multiple times and are going to be limited by BlueSky's rate limits. 

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

2. Run the gui.py file.

3. Go to the 'Settings' tab, add your BlueSky Username, App password, and Block List URL and press 'Save Settings'. 

4. Update the list of keywords or hashtags you'd like to scan for in the 'Blocklist' tab.

5. Run the main.py file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.
