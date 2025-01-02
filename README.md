# Discord Storage Bot

## Overview

The Discord Storage Bot is an innovative solution that transforms Discord servers into a file storage system. It efficiently handles large files by breaking them into chunks, uploading them to a designated Discord server, and seamlessly reassembling them upon download.

## Features

- Large file support through chunking
- Web interface for easy file management
- Progress tracking for uploads and downloads
- Utilizes Discord's robust infrastructure for storage

## Prerequisites

- Python 3.7+
- Discord Bot Token
- Discord Server (Guild) ID

## Installation

1. Clone the repository or download the source code.

2. Install the required dependencies:

  ```pip install flask discord.py python-dotenv```

  Replace the placeholders with your actual values.

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
- The web interface lacks built-in authentication. Implement security measures for non-local deployments.

## Limitations

- Subject to Discord's rate and storage limits.
- Not suitable for high-volume or large-scale file storage.
- Lacks advanced features like file versioning.

## Troubleshooting

If issues arise:
1. Verify the Discord bot token and Guild ID.
2. Ensure proper bot permissions in the Discord server.
3. Check console output for error messages.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
