import os
import sqlite3
from flask import Flask, render_template, request, jsonify, send_file, after_this_request, redirect, url_for, session
import threading
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import re
import time
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load environment variables from a .env file
load_dotenv()
# Initialize Flask app
app = Flask(__name__)
# Secret key for session management (e.g., cookies)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Constants for file handling (upload and download folders, and chunk size for file uploads)
UPLOAD_FOLDER, DOWNLOAD_FOLDER, CHUNK_SIZE = 'uploads', 'downloads', 25 * 1024 * 1024  # 25MB
DB_NAME = 'file_metadata_and_users.db'  # SQLite database file

# Set up Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Get Discord bot token and server ID from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))

# Dictionaries to track upload and download progress
upload_progress, download_progress = {}, {}

# Initialize the SQLite database with required tables
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS file_metadata (
                uuid TEXT PRIMARY KEY, 
                filename TEXT NOT NULL, 
                discord_channel_id TEXT, 
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                password TEXT NOT NULL, 
                is_admin BOOLEAN NOT NULL DEFAULT 0
            );
        ''')
        conn.commit()

# Utility function to create a new user in the database
def create_user(username, password, is_admin=False):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', 
                     (username, generate_password_hash(password), is_admin))
        conn.commit()

# Function to validate user credentials
def validate_user(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    return user and check_password_hash(user[1], password)

# Check if there is at least one admin user
def is_admin_set():
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute('SELECT 1 FROM users WHERE is_admin = 1').fetchone() is not None

# Insert metadata for a file upload
def insert_file_metadata(file_uuid, filename):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''INSERT INTO file_metadata (uuid, filename) VALUES (?, ?)''', (file_uuid, filename))
        conn.commit()

# Update the Discord channel ID associated with a file
def update_discord_channel_id(file_uuid, channel_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('UPDATE file_metadata SET discord_channel_id = ? WHERE uuid = ?', (channel_id, file_uuid))
        conn.commit()

# Upload a file to Discord in chunks
async def upload_to_discord(file_uuid):
    guild = bot.get_guild(GUILD_ID)
    channel = await guild.create_text_channel(file_uuid)
    update_discord_channel_id(file_uuid, str(channel.id))

    # Sort chunks by their index and send them to Discord
    chunks = sorted(os.listdir(os.path.join(UPLOAD_FOLDER, file_uuid)), key=lambda x: int(x.split('-C')[-1]))
    for i, chunk in enumerate(chunks, 1):
        await channel.send(file=discord.File(os.path.join(UPLOAD_FOLDER, file_uuid, chunk)))
        upload_progress[file_uuid] = int((i / len(chunks)) * 100)
        os.remove(os.path.join(UPLOAD_FOLDER, file_uuid, chunk))  # Clean up chunk after sending

    os.rmdir(os.path.join(UPLOAD_FOLDER, file_uuid))  # Clean up the directory after upload

# Flask route decorators for login and admin access management
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def already_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in'):
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Admin page to manage users
@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not is_admin():
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin_user = 'is_admin' in request.form
        create_user(username, password, is_admin_user)
        return redirect(url_for('admin_users'))

    # Fetch all users from the database
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, password, is_admin FROM users')
        users = cursor.fetchall()

    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<username>', methods=['POST'])
@login_required
def delete_user(username):
    if not is_admin():
        return redirect(url_for('home'))  # Ensure only admins can delete users

    # Delete user from the database
    with sqlite3.connect(DB_NAME) as conn:
        # Check if the user exists and is not an admin
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and user[2] == 0:  # Ensure the user is not an admin
            conn.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            return redirect(url_for('admin_users'))  # Redirect back to the admin users page

    return jsonify({'error': 'User not found or cannot delete an admin.'}), 400

# Helper function to check if the current user is an admin
def is_admin():
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT is_admin FROM users WHERE username = ?', (session.get('user'),)).fetchone()
    return user and user[0] == 1

# Flask routes to handle user setup, login, and logout
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if is_admin_set():
        return redirect(url_for('home'))
    if request.method == 'POST':
        create_user(request.form['username'], request.form['password'], True)
        return redirect(url_for('home'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
@already_logged_in
def login():
    if not is_admin_set():
        return redirect(url_for('setup'))
    if request.method == 'POST' and validate_user(request.form['username'], request.form['password']):
        session.update({'user': request.form['username'], 'logged_in': True})
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    if not is_admin_set(): return redirect(url_for('setup'))
    return render_template('index.html')

# Upload file chunk by chunk
@app.route('/upload', methods=['POST'])
@login_required
def upload_chunk():
    file = request.files['file']
    chunk_index = int(request.form['dzchunkindex'])
    total_chunks = int(request.form['dztotalchunkcount'])
    file_uuid = request.form['dzuuid']
    
    # Create directory for the file chunks
    file_dir = os.path.join(UPLOAD_FOLDER, file_uuid)
    os.makedirs(file_dir, exist_ok=True)

    # Save the file chunk
    chunk_path = os.path.join(file_dir, f"{file_uuid}-C{chunk_index + 1}")
    file.save(chunk_path)

    # Insert file metadata on the first chunk
    if chunk_index == 0:
        insert_file_metadata(file_uuid, file.filename)

    # Start uploading to Discord once all chunks are received
    if chunk_index == total_chunks - 1:
        bot.loop.create_task(upload_to_discord(file_uuid))

    return jsonify({'success': True, 'file_uuid': file_uuid})

# Progress tracking for uploads
@app.route('/upload_progress/<file_uuid>')
@login_required
def get_upload_progress(file_uuid):
    return jsonify({'progress': upload_progress.get(file_uuid, 0)})

# Display uploaded files
@app.route('/files')
@login_required
def files():
    # Fetch all file metadata
    with sqlite3.connect(DB_NAME) as conn:
        files = conn.execute('SELECT uuid, filename, upload_date FROM file_metadata').fetchall()

    # Prepare file info for template rendering
    file_info = []
    for file in files:
        file_uuid, filename, upload_date = file
        file_info.append({
            'file_uuid': file_uuid,
            'filename': filename,
            'upload_date': upload_date,
            'file_url': url_for('file_info', file_uuid=file_uuid),
            'download_url': url_for('download_file', file_uuid=file_uuid)
        })

    return render_template('file_explorer.html', file_info=file_info)

# Show detailed information for a file
@app.route('/file/<file_uuid>')
@login_required
def file_info(file_uuid):
    with sqlite3.connect(DB_NAME) as conn:
        result = conn.execute('SELECT filename, upload_date FROM file_metadata WHERE uuid = ?', (file_uuid,)).fetchone()
    if result is None:
        return "File not found", 404

    filename, upload_date = result
    return render_template('file_info.html', file_uuid=file_uuid, filename=filename, upload_date=upload_date)

# Handle file download
@app.route('/download/<file_uuid>')
@login_required
def download_file(file_uuid):
    session_uuid = request.args.get('session_uuid')
    if not session_uuid: return "Session UUID is required", 400

    with sqlite3.connect(DB_NAME) as conn:
        result = conn.execute('SELECT filename, file_extension, discord_channel_id FROM file_metadata WHERE uuid = ?', (file_uuid,)).fetchone()
    if result is None: return "File not found", 404

    # Prepare the download directory for the session and file
    session_download_dir = os.path.join(DOWNLOAD_FOLDER, session_uuid, file_uuid)
    os.makedirs(session_download_dir, exist_ok=True)

    # Download the chunks from Discord asynchronously
    asyncio.run_coroutine_threadsafe(download_chunks_from_discord(file_uuid, result[2], session_uuid, session_download_dir), bot.loop).result()

    # Combine the downloaded chunks into one file
    combined_file_path = os.path.join(session_download_dir, f"{result[0]}{result[1]}")
    combine_chunks(file_uuid, session_download_dir, combined_file_path)

    @after_this_request
    def cleanup(response):
        threading.Thread(target=delayed_cleanup, args=(combined_file_path, session_download_dir), daemon=True).start()
        return response

    # Send the combined file to the user
    return send_file(combined_file_path, as_attachment=True, download_name=f"{result[0]}{result[1]}")

# Track download progress for specific files and sessions
@app.route('/download_progress/<session_uuid>/<file_uuid>')
@login_required
def download_progress_endpoint(session_uuid, file_uuid):
    # Retrieve the download progress for the specific session and file
    progress = download_progress.get(f"{session_uuid}_{file_uuid}", 0)
    return jsonify({'progress': progress})

# Helper functions for handling chunk downloads and cleanup
def combine_chunks(file_uuid, download_dir, combined_file_path):
    # Combine the file chunks into one file
    chunk_files = sorted([f for f in os.listdir(download_dir) if re.match(fr'{file_uuid}-C\d+', f)], 
                         key=lambda x: int(re.search(r'-C(\d+)', x).group(1)))
    with open(combined_file_path, 'wb') as outfile:
        for chunk_file in chunk_files:
            with open(os.path.join(download_dir, chunk_file), 'rb') as infile:
                outfile.write(infile.read())
    for chunk_file in chunk_files:
        os.remove(os.path.join(download_dir, chunk_file))

async def download_chunks_from_discord(file_uuid, channel_id, session_uuid, download_dir):
    # Download the file chunks from Discord
    channel = bot.get_channel(int(channel_id))
    
    total_chunks = 0
    async for message in channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.filename.startswith(file_uuid):
                total_chunks += 1
    
    chunks = 0
    async for message in channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.filename.startswith(file_uuid):
                await attachment.save(os.path.join(download_dir, attachment.filename))
                chunks += 1
                download_progress[f"{session_uuid}_{file_uuid}"] = int((chunks / total_chunks) * 100)

# Clean up files after download
def delayed_cleanup(file_path, directory):
    time.sleep(1)
    try:
        os.remove(file_path)
        for chunk_file in os.listdir(directory):
            os.remove(os.path.join(directory, chunk_file))
        os.rmdir(directory)
        parent_directory = os.path.dirname(directory)
        os.rmdir(parent_directory)
    except Exception as e:
        print(f"Error cleaning up: {e}")

# Run the Flask app and Discord bot in separate threads
if __name__ == '__main__':
    init_db()  # Initialize the database
    threading.Thread(target=bot.run, args=(DISCORD_TOKEN,), daemon=True).start()  # Start Discord bot
    app.run(debug=True, port=8080, host="0.0.0.0")  # Start Flask app
