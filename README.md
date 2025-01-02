# Discord Storage Bot

This Discord Storage Bot allows you to use Discord servers as a file storage system. It breaks down large files into chunks, uploads them to a designated Discord server, and reassembles them upon download.

## Prerequisites

- Python 3.7+
- Discord Bot Token
- Discord Server (Guild) ID

## Setup

1. Clone the repository or download the source code.

2. Install the required dependencies:

   pip install flask discord.py python-dotenv

3. Create a `.env` file in the root directory with the following content:

   FLASK_SECRET_KEY=your_secret_key_here
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   DISCORD_GUILD_ID=your_discord_guild_id_here

   Replace the placeholders with your actual values.

4. Create the following directories in the project root:
   - `uploads`
   - `downloads`

## Running the Bot

1. Start the bot by running:

   python app.py

2. The Flask server will start, and you should see a message indicating that the bot has connected to Discord.

3. Access the web interface by opening a browser and navigating to `http://localhost:8080`.

## Usage

1. Upload files through the web interface. The bot will chunk the files and upload them to the specified Discord server.

2. To download files, use the provided file UUID through the web interface.

## Important Notes

- The bot creates a new text channel for each uploaded file in the specified Discord server.
- Ensure your Discord bot has the necessary permissions to create channels and send messages in the server.
- The maximum chunk size is set to 25MB by default. Adjust the `CHUNK_SIZE` variable in `app.py` if needed.

## Security Considerations

- This bot stores file metadata in a local SQLite database. Ensure proper access controls for the server running this bot.
- Files are stored in Discord channels. While Discord provides some level of security, consider the sensitivity of the data you're storing.
- The web interface doesn't include authentication. Implement appropriate security measures if deploying in a non-local environment.

## Limitations

- Discord has rate limits and storage limits. This bot may not be suitable for high-volume or large-scale file storage.
- The bot doesn't handle file versioning or advanced file management features.

## Troubleshooting

If you encounter any issues:
- Check that your Discord bot token and Guild ID are correct.
- Ensure the bot has the necessary permissions in the Discord server.
- Review the console output for any error messages.
