# Discord File Storage Server

This project implements a secure file storage system using Discord as a backend, with a Flask web interface for user management and file operations.

## Setup Instructions

### Prerequisites

- Python 3.7+
- pip (Python package manager)
- A Discord account and a Discord server where you have administrative privileges

### Step 1: Discord Bot Setup

1. Go to the Discord Developer Portal (https://discord.com/developers/applications).
2. Click "New Application" and give it a name.
3. Navigate to the "Bot" tab.
4. Under the "Token" section, click "Reset Token" to copy your bot token. Keep this secure!
5. Enable the following "Privileged Gateway Intents":
   - Message Content Intent
6. I use https://discordapi.com/permissions.html to generate an invite URL for my bot.

### Step 2: Environment Setup

1. Clone this repository to your local machine.
2. Create a .env file in the project root with the following content:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_GUILD_ID=your_guild_id_here
   FLASK_SECRET_KEY=a_random_secret_key
   ```
3. Replace your_bot_token_here with the bot token you copied earlier.
4. Replace your_guild_id_here with the ID of your Discord server.
5. Generate a random secret key for Flask and replace a_random_secret_key with it.

### Step 3: Install Dependencies

Run the following command in your terminal:

```
pip install -r requirements.txt
```

### Step 4: Start the Server

Run the following command to start the Flask server:

python app.py

The server should now be running on `http://127.0.0.1/`.

## Usage

### User Management

## Initial Setup
When you first access the Discord Storage Server, you'll be prompted to create an admin account if one doesn't exist. This can be done by navigating to one of the following addresses:
- LOCAL: `http://127.0.0.1/`
- LAN: `http://private_IP/`
- WAN: `http://public_IP/`

## User Administration
Once the admin account is set up, you can manage users by following these steps:
1. Log in with your admin credentials
2. Access the user management panel at `http://127.0.0.1/admin/users`

| Access Method | URL | Use Case |
|---------------|-----|----------|
| LOCAL | `http://127.0.0.1/` | On the device running the server |
| LAN | `http://private_IP/` | From any device on your local network |
| WAN | `http://public_IP/` | From any device on any network |



## File Operations

# Logging In
1. Open your web browser and go to `http://127.0.0.1/`.
2. You'll see a login page where you can enter your username and password.
3. Enter your credentials and click the "Login" button.

# Uploading Files
1. After logging in, you'll be directed to the main page.
2. Click on the "Upload Your File" button and select the file you want to upload or Drag and Drop a file.

# Viewing and Managing Files
1. From the main page, click on "Go to File Explorer".
2. You'll see a list of all uploaded files, including their filenames and upload dates.
3. To view or download a specific file, click the "View" button next to the file name.

# Downloading Files
1. In the File Explorer, click the "View" button next to the file you want to download.
2. You'll be taken to a File Information page showing details about the file.
3. Click the "Download File" button to start downloading the file to your local machine.
4. You can monitor the download progress using the progress bar at the bottom of the page.

# Logging Out
- To log out of the system, click the "Logout" button on the main page.

## Security Considerations

- Keep your .env file secure and never commit it to version control.
- Regularly rotate your Discord bot token and Flask secret key.
- Implement additional security measures like rate limiting and input validation in a production environment.

## Troubleshooting

- If you encounter any issues with Discord integration, ensure your bot has the necessary permissions in your Discord server.
- Check the console output for any error messages when running the server.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License.
