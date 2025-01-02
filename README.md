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
3. Navigate to the "Bot" tab and click "Add Bot".
4. Under the "Token" section, click "Copy" to copy your bot token. Keep this secure!
5. Enable the following "Privileged Gateway Intents":
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
6. Go to the "OAuth2" tab, select "bot" under "Scopes", and choose necessary permissions.
7. Copy the generated OAuth2 URL and use it to invite the bot to your Discord server.

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

pip install -r requirements.txt

### Step 4: Database Initialization

Run the following command to initialize the SQLite database:

   ```
   python
   >>> from app import init_db
   >>> init_db()
   >>> exit()
   ```

### Step 5: Start the Server

Run the following command to start the Flask server:

python app.py

The server should now be running on http://localhost:8080.

## Usage

### User Management

- Navigate to http://localhost:8080/setup to create the initial admin account.
- Use the admin account to log in and manage users at http://localhost:8080/admin/users.

### File Operations

- Log in to access the file management interface.
- Use the upload form to send files to the server.
- View and download files from the file explorer.

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
