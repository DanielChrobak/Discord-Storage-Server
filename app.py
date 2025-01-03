import os
import sqlite3
import re
import time
import asyncio
import threading
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, after_this_request
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives import keywrap
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Constants
UPLOAD_FOLDER, DOWNLOAD_FOLDER, CHUNK_SIZE = 'uploads', 'downloads', 25 * 1024 * 1024  # File chunk size: 25 MB
DB_NAME = 'file_metadata_and_users.db'  # SQLite database name

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intents
bot = commands.Bot(command_prefix='!', intents=intents)  # Initialize bot with command prefix
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Discord bot token
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))  # Discord guild (server) ID

# Progress tracking for uploads and downloads
upload_progress, download_progress = {}, {}

# Initialize SQLite database
def init_db():
    """Creates necessary database tables for file metadata and user management."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS file_metadata (
                uuid TEXT PRIMARY KEY, 
                filename TEXT NOT NULL, 
                discord_channel_id TEXT, 
                encryption_key BLOB NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                password TEXT NOT NULL, 
                is_admin BOOLEAN NOT NULL DEFAULT 0
            );
        ''')

# Encryption utility functions
def generate_key():
    """Generate a random 256-bit key."""
    return os.urandom(32)

def encrypt_data(key, plaintext):
    """Encrypts data using AES-CBC."""
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return iv + ciphertext

def decrypt_data(key, ciphertext):
    """Decrypts data using AES-CBC."""
    iv, actual_ciphertext = ciphertext[:16], ciphertext[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(actual_ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_data) + unpadder.finalize()
    return plaintext

# User management functions
def create_user(username, password, is_admin=False):
    """Adds a new user to the database."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', 
                     (username, generate_password_hash(password), is_admin))

def validate_user(username, password):
    """Validates user credentials against the database."""
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT password FROM users WHERE username = ?', (username,)).fetchone()
    return user and check_password_hash(user[0], password)

def is_admin_set():
    """Checks if there is at least one admin user in the database."""
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute('SELECT 1 FROM users WHERE is_admin = 1').fetchone() is not None

# Flask decorators
def login_required(f):
    """Decorator to ensure routes require user login."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def is_admin():
    """Checks if the currently logged-in user is an admin."""
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT is_admin FROM users WHERE username = ?', (session.get('user'),)).fetchone()
    return user and user[0]

# Discord upload and file management
async def upload_to_discord(file_uuid):
    guild = bot.get_guild(GUILD_ID)
    channel = await guild.create_text_channel(file_uuid)

    # Update the database with the channel ID
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('UPDATE file_metadata SET discord_channel_id = ? WHERE uuid = ?', (channel.id, file_uuid))

    # Get and sort chunks
    chunks = sorted(os.listdir(os.path.join(UPLOAD_FOLDER, file_uuid)), 
                    key=lambda x: int(x.split('-C')[-1]))
    for i, chunk in enumerate(chunks, 1):
        chunk_path = os.path.join(UPLOAD_FOLDER, file_uuid, chunk)
        chunk_size = os.path.getsize(chunk_path)
        print(f"Uploading chunk {i}/{len(chunks)}: {chunk} (Size: {chunk_size} bytes)")  # Debugging output
        await channel.send(file=discord.File(chunk_path))
        upload_progress[file_uuid] = int((i / len(chunks)) * 100)
        os.remove(chunk_path)  # Delete the chunk after uploading

    os.rmdir(os.path.join(UPLOAD_FOLDER, file_uuid))  # Remove the now-empty directory

def combine_chunks(file_uuid, download_dir, combined_file_path):
    """Combines file chunks into a single file."""
    chunks = sorted([f for f in os.listdir(download_dir) if re.match(fr'{file_uuid}-C\d+', f)], 
                    key=lambda x: int(re.search(r'-C(\d+)', x).group(1)))
    with open(combined_file_path, 'wb') as outfile:
        for chunk in chunks:
            with open(os.path.join(download_dir, chunk), 'rb') as infile:
                outfile.write(infile.read())
            os.remove(os.path.join(download_dir, chunk))  # Remove processed chunk

# Flask routes
@app.route('/')
@login_required
def home():
    """Home page route."""
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Initial setup route for creating the first admin user."""
    if is_admin_set():
        return redirect(url_for('home'))
    if request.method == 'POST':
        create_user(request.form['username'], request.form['password'], True)
        return redirect(url_for('home'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if not is_admin_set():
        return redirect(url_for('setup'))
    if request.method == 'POST' and validate_user(request.form['username'], request.form['password']):
        session.update({'user': request.form['username'], 'logged_in': True})
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    """Logs out the current user."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    """Admin page to manage users."""
    if not is_admin():
        return redirect(url_for('home'))

    if request.method == 'POST':
        create_user(request.form['username'], request.form['password'], 'is_admin' in request.form)
        return redirect(url_for('admin_users'))

    with sqlite3.connect(DB_NAME) as conn:
        users = conn.execute('SELECT username, is_admin FROM users').fetchall()

    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<username>', methods=['POST'])
@login_required
def delete_user(username):
    """Deletes a user (admin-only)."""
    if not is_admin():
        return redirect(url_for('home'))

    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and not user[2]:
            conn.execute('DELETE FROM users WHERE username = ?', (username,))
            return redirect(url_for('admin_users'))

    return jsonify({'error': 'User not found or cannot delete an admin.'}), 400

@app.route('/upload', methods=['POST'])
def upload_chunk():
    """Handles uploading file chunks to the server with encryption."""
    file = request.files['file']
    chunk_index = int(request.form['dzchunkindex'])
    total_chunks = int(request.form['dztotalchunkcount'])
    file_uuid = request.form['dzuuid']

    file_dir = os.path.join(UPLOAD_FOLDER, file_uuid)
    os.makedirs(file_dir, exist_ok=True)
    chunk_path = os.path.join(file_dir, f"{file_uuid}-C{chunk_index + 1}")

    try:
        if chunk_index == 0:
            # Generate and store encryption key for the first chunk
            encryption_key = generate_key()
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute(
                    'INSERT INTO file_metadata (uuid, filename, encryption_key) VALUES (?, ?, ?)',
                    (file_uuid, file.filename, encryption_key)
                )
                print(f"Inserted encryption key for file {file.filename} with UUID {file_uuid}.")
        else:
            # Retrieve the encryption key for subsequent chunks
            with sqlite3.connect(DB_NAME) as conn:
                encryption_key_row = conn.execute(
                    'SELECT encryption_key FROM file_metadata WHERE uuid = ?', (file_uuid,)
                ).fetchone()
                if not encryption_key_row:
                    raise ValueError(f"Encryption key not found for file UUID {file_uuid}.")
                encryption_key = encryption_key_row[0]
                print(f"Retrieved encryption key for file UUID {file_uuid}.")

        # Encrypt and save chunk
        encrypted_data = encrypt_data(encryption_key, file.read())
        with open(chunk_path, 'wb') as f:
            f.write(encrypted_data)

        print(f"Saved chunk {chunk_index + 1}/{total_chunks} for file UUID {file_uuid}.")

        # Trigger upload to Discord after the last chunk
        if chunk_index == total_chunks - 1:
            asyncio.run_coroutine_threadsafe(upload_to_discord(file_uuid), bot.loop)

        return jsonify({'success': True, 'file_uuid': file_uuid})
    except Exception as e:
        print(f"Error uploading chunk {chunk_index + 1}/{total_chunks} for file UUID {file_uuid}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload_progress/<file_uuid>')
@login_required
def get_upload_progress(file_uuid):
    """Returns the upload progress for a file."""
    return jsonify({'progress': upload_progress.get(file_uuid, 0)})

@app.route('/files')
@login_required
def files():
    """Displays uploaded files and their metadata."""
    with sqlite3.connect(DB_NAME) as conn:
        files = conn.execute('SELECT uuid, filename, upload_date FROM file_metadata').fetchall()

    return render_template('file_explorer.html', file_info=[{
        'file_uuid': file[0],
        'filename': file[1],
        'upload_date': file[2],
        'file_url': url_for('file_info', file_uuid=file[0]),
        'download_url': url_for('download_file', file_uuid=file[0])
    } for file in files])

@app.route('/file/<file_uuid>')
@login_required
def file_info(file_uuid):
    """Displays detailed information about a specific file."""
    with sqlite3.connect(DB_NAME) as conn:
        file = conn.execute('SELECT filename, upload_date FROM file_metadata WHERE uuid = ?', (file_uuid,)).fetchone()
    if not file:
        return "File not found", 404

    return render_template('file_info.html', file_uuid=file_uuid, filename=file[0], upload_date=file[1])

@app.route('/download/<file_uuid>')
def download_file(file_uuid):
    """Handles downloading a file from Discord with decryption."""
    session_uuid = request.args.get('session_uuid')
    if not session_uuid:
        return "Session UUID is required", 400

    with sqlite3.connect(DB_NAME) as conn:
        file_metadata = conn.execute(
            'SELECT filename, discord_channel_id, encryption_key FROM file_metadata WHERE uuid = ?', (file_uuid,)
        ).fetchone()

    if not file_metadata:
        return "File not found", 404

    filename, channel_id, encryption_key = file_metadata
    session_download_dir = os.path.join(DOWNLOAD_FOLDER, session_uuid, file_uuid)
    os.makedirs(session_download_dir, exist_ok=True)

    asyncio.run_coroutine_threadsafe(
        download_chunks_from_discord(file_uuid, channel_id, session_uuid, session_download_dir), bot.loop
    ).result()

    combined_file_path = os.path.join(session_download_dir, filename)

    # Filter and validate chunks
    chunk_files = [
        f for f in os.listdir(session_download_dir)
        if re.match(rf'{file_uuid}-C\d+', f)
    ]
    if not chunk_files:
        return "No valid chunks found for the file.", 500

    chunk_files = sorted(
        chunk_files, key=lambda x: int(re.search(r'-C(\d+)', x).group(1))
    )

    with open(combined_file_path, 'wb') as outfile:
        for chunk in chunk_files:
            chunk_path = os.path.join(session_download_dir, chunk)
            with open(chunk_path, 'rb') as infile:
                encrypted_chunk = infile.read()
                decrypted_chunk = decrypt_data(encryption_key, encrypted_chunk)
                outfile.write(decrypted_chunk)
            os.remove(chunk_path)

    @after_this_request
    def cleanup(response):
        threading.Thread(target=delayed_cleanup, args=(combined_file_path, session_download_dir), daemon=True).start()
        return response

    return send_file(combined_file_path, as_attachment=True, download_name=filename)

@app.route('/download_progress/<session_uuid>/<file_uuid>')
@login_required
def download_progress_endpoint(session_uuid, file_uuid):
    """Returns the download progress for a file."""
    return jsonify({'progress': download_progress.get(f"{session_uuid}_{file_uuid}", 0)})

async def download_chunks_from_discord(file_uuid, channel_id, session_uuid, download_dir):
    """Downloads file chunks from Discord."""
    channel = bot.get_channel(int(channel_id))
    total_chunks, chunks = 0, 0

    async for message in channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.filename.startswith(file_uuid):
                total_chunks += 1

    async for message in channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.filename.startswith(file_uuid):
                await attachment.save(os.path.join(download_dir, attachment.filename))
                chunks += 1
                download_progress[f"{session_uuid}_{file_uuid}"] = int((chunks / total_chunks) * 100)

def delayed_cleanup(file_path, directory):
    """Cleans up temporary files and directories after use."""
    time.sleep(3600)  # Delay cleanup to allow file download completion
    try:
        os.remove(file_path)
        for chunk_file in os.listdir(directory):
            os.remove(os.path.join(directory, chunk_file))
        os.rmdir(directory)
        parent_dir = os.path.dirname(directory)
        os.rmdir(parent_dir)
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == '__main__':
    init_db()  # Initialize the database
    threading.Thread(target=bot.run, args=(DISCORD_TOKEN,), daemon=True).start()  # Run Discord bot in a separate thread
    app.run(debug=True, host="0.0.0.0", port=80)  # Run Flask app
