# Bluesky Shield
![image](https://github.com/user-attachments/assets/9576baa5-81ff-45c2-9d8d-1caa2a58e59e)

## Overview
Bluesky Shield is an AI-powered block list automator designed to help users manage and automate their block lists on the BlueSky platform. This program allows users to easily add blocked users by scanning for specified terminology posted on Bluesky, and having AI reason over the context of the post, ensuring a safer, more controlled, and customized online experience.

## Features
- **Automated Blocking:** Automatically block users based on predefined criteria.
- **User-Friendly Interface:** Easy-to-use interface for managing block lists.
- **Real-Time Monitoring:** Continuously monitor and update block lists based on AI-driven analysis.
- **Comprehensive Logging:** Keep track of all actions and changes for accountability and review.

## Limitations
- **User Scan Limit:** Can only scan for 50-100 users at a time. To manage larger block lists, multiple scans may be necessary, keeping in mind Bluesky's rate limits.
- **AI Accuracy:** While the AI provides robust reasoning, occasional manual reviews may still be required to ensure accuracy.

---

## Installation

### Prerequisites
Before installing Bluesky Shield, ensure you have the following installed on your system:

- **Python 3.12:** [Download and Install Python 3.12](https://www.python.org/downloads/)
- **Node.js & npm:** [Download and Install Node.js](https://nodejs.org/) (npm is included with Node.js)
- **Ollama:** [Download and Install Ollama](https://ollama.ai/)

### 1. Clone the Repository
Clone the Bluesky Shield repository to your local machine:

```sh
git clone https://github.com/EricKrouss/Bluesky-Shield.git
```

### 2. Navigate to the Project Directory
```sh
cd BlueSky-Shield
```


### 3. Install Python Dependencies
Run the following commands in a terminal.

```sh
pip install flask
pip install flask_cors
pip install requests
```


### 5. Install and Run Ollama Models
Bluesky Shield utilizes AI models from Ollama for processing and reasoning.

**a. Install Deepseek-R1 (Reasoning Model)**
```sh
ollama run deepseek-r1:8b
```

**b. Install Llava (Image Description Model)**
```sh
ollama run llava:7b
```

### 6. Install HTTP Server
Bluesky Shield's frontend is served using `http-server`. Install it globally using npm:

```sh
npm install -g http-server
```

**Note:** You may need administrative privileges to install global npm packages. If you encounter permission issues, consider using `sudo` on macOS/Linux:

```sh
sudo npm install -g http-server
```

---

## Usage & Configuration

### 1. Create and Add an App Password
- Navigate to your BlueSky account settings: [BlueSky App Passwords](https://bsky.app/settings/app-passwords)
- Create a new App Password and note it down securely.

### 2. Configure Settings in Bluesky Shield
- Go to the **Settings** tab in the application.
- Enter your **BlueSky Username**, **App Password**, and **Blocklist URL**.
- Click on **Save Settings**.

### 3. Manage Keywords or Hashtags
- Navigate to the **Control Panel** tab.
- Add or remove keywords/hashtags you want Bluesky Shield to scan for.
- Click **Run Scan** to initiate the scanning process.

### 4. Review Scan Results
- Go to the **Results** tab to view flagged users and those needing human evaluation.
- Perform actions such as blocking users, deleting posts, or overriding classifications as needed.

### 5. Monitor Server Logs
- Access the **Logs** tab to view real-time server logs for monitoring and debugging purposes.

---

## Starting the Application

### Start the Backend Server:
```sh
python server.py
```

**Note:** Ensure that the virtual environment is activated if you set one up earlier.

### Start the Frontend HTTP Server:
In a new terminal window/tab, navigate to the project directory and run:

```sh
http-server -p 5173
```

### Access the Application:
- Open your browser and go to [http://localhost:5173](http://localhost:5173).



## License
This project is licensed under the **MIT License**. See the `LICENSE` file for more information.

---

## Additional Notes

### Environment Variables:
For enhanced security, especially for sensitive information like `APP_PASSWORD`, consider using environment variables instead of hardcoding them. Tools like [python-dotenv](https://pypi.org/project/python-dotenv/) can help manage environment variables.

### Production Deployment:
For deploying Bluesky Shield in a production environment, consider using:
- A production-ready web server like **Gunicorn** for the Flask backend.
- A more robust solution for serving the frontend.

### Contribution:
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

---

Feel free to further customize this `README.md` to better fit your project's specifics and additional features. If you have any more requirements or need further assistance, feel free to ask!
