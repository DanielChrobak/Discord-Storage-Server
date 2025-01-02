# Discord Storage Server

This README provides instructions on how to set up and use the Discord Storage Server application.

## Overview

The Discord Storage Bot is an innovative solution that transforms Discord servers into a file storage system. It efficiently handles large files by breaking them into chunks, uploading them to a designated Discord server, and seamlessly reassembling them upon download.

## Features

- Large file support through chunking
- Web interface for easy file management
- Progress tracking for uploads and downloads
- Utilizes Discord's robust infrastructure for storage

## Prerequisites

- Python 3.7+
- Flask
- discord.py
- python-dotenv
- SQLite3

## Installation

1. Clone the repository or download the source code.

2. Install the required dependencies:

  ```pip install flask discord.py python-dotenv```

3. Create a .env file in the project root directory with the following contents:

  ```
  DISCORD_BOT_TOKEN=your_discord_bot_token

  DISCORD_GUILD_ID=your_discord_guild_id

  FLASK_SECRET_KEY=your_flask_secret_key
  ```

  Replace the placeholders with your actual Discord bot token, guild ID, and a secure secret key for Flask.

4. Directory structure:

  The following directories will be automatically generated in the project root:
  - `uploads`
  - `downloads`

## Usage

1. Start the bot:

  ```python app.py```

2. The Flask server will initialize, and you'll see confirmation messages in the console:
  - Flask server start message
  - Discord connection confirmation (appears twice in debug mode)

3. Access the web interface:
  - Local: `http://localhost:8080`
  - Remote (LAN): `http://server_private_ip:8080`
  - Remote (WAN): `http://server_punblic_ip:8080`

  If this is the first time running the application, you'll be redirected to the setup page to create an admin account.

Note: On Windows, find your private IP using `ipconfig /all` in Command Prompt.

Note: To access the Discord Storage Server through your public IP, you'll need to forward the port being used, in this case `8080`.

## File Management

1. **Uploading**: Use the web interface to upload files. The bot will chunk and distribute them across the Discord server.

2. **Downloading**: Enter the file UUID in the web interface to retrieve and reassemble the file.

## Technical Details

- **Channel Creation**: The bot generates a new text channel for each uploaded file.
- **Chunk Size**: Default is 25MB, adjustable in `app.py` (`CHUNK_SIZE` variable).
- **Database**: File metadata is stored in a local SQLite database.

## Security Considerations

- Implement access controls for the server hosting the bot.
- Be mindful of data sensitivity when using Discord for storage.
- The web interface has a basic built-in authentication system. Implement security measures for non-local deployments.

## Limitations

- Subject to Discord's rate and storage limits.
- May not be suitable for high-volume or large-scale file storage.

## Troubleshooting

If issues arise:
1. Verify the Discord bot token and Guild ID.
2. Ensure proper bot permissions in the Discord server.
3. Check console output for error messages.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
