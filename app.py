import os
import sqlite3
import re
import time
import asyncio
import threading
from flask import (Flask, render_template, request, jsonify, send_file, 
                   redirect, url_for, session, after_this_request)
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Constants
UPLOAD_FOLDER, DOWNLOAD_FOLDER, CHUNK_SIZE = 'uploads', 'downloads', 25 * 1024 * 1024
DB_NAME = 'file_metadata_and_users.db'

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))

# Progress tracking
upload_progress, download_progress = {}, {}

# Initialize database
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

# User management
def create_user(username, password, is_admin=False):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', 
                     (username, generate_password_hash(password), is_admin))

def validate_user(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT password FROM users WHERE username = ?', (username,)).fetchone()
    return user and check_password_hash(user[0], password)

def is_admin_set():
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute('SELECT 1 FROM users WHERE is_admin = 1').fetchone() is not None

# Flask decorators
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def is_admin():
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT is_admin FROM users WHERE username = ?', (session.get('user'),)).fetchone()
    return user and user[0]

# Discord upload/download
async def upload_to_discord(file_uuid):
    guild = bot.get_guild(GUILD_ID)
    channel = await guild.create_text_channel(file_uuid)

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('UPDATE file_metadata SET discord_channel_id = ? WHERE uuid = ?', (channel.id, file_uuid))

    chunks = sorted(os.listdir(os.path.join(UPLOAD_FOLDER, file_uuid)), 
                    key=lambda x: int(x.split('-C')[-1]))
    for i, chunk in enumerate(chunks, 1):
        await channel.send(file=discord.File(os.path.join(UPLOAD_FOLDER, file_uuid, chunk)))
        upload_progress[file_uuid] = int((i / len(chunks)) * 100)

    os.rmdir(os.path.join(UPLOAD_FOLDER, file_uuid))

def combine_chunks(file_uuid, download_dir, combined_file_path):
    chunks = sorted([f for f in os.listdir(download_dir) if re.match(fr'{file_uuid}-C\d+', f)], 
                    key=lambda x: int(re.search(r'-C(\d+)', x).group(1)))
    with open(combined_file_path, 'wb') as outfile:
        for chunk in chunks:
            with open(os.path.join(download_dir, chunk), 'rb') as infile:
                outfile.write(infile.read())
            os.remove(os.path.join(download_dir, chunk))

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if is_admin_set():
        return redirect(url_for('home'))
    if request.method == 'POST':
        create_user(request.form['username'], request.form['password'], True)
        return redirect(url_for('home'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
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

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
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
    if not is_admin():
        return redirect(url_for('home'))

    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and not user[2]:
            conn.execute('DELETE FROM users WHERE username = ?', (username,))
            return redirect(url_for('admin_users'))

    return jsonify({'error': 'User not found or cannot delete an admin.'}), 400

@app.route('/upload', methods=['POST'])
@login_required
def upload_chunk():
    file = request.files['file']
    chunk_index = int(request.form['dzchunkindex'])
    total_chunks = int(request.form['dztotalchunkcount'])
    file_uuid = request.form['dzuuid']

    file_dir = os.path.join(UPLOAD_FOLDER, file_uuid)
    os.makedirs(file_dir, exist_ok=True)
    chunk_path = os.path.join(file_dir, f"{file_uuid}-C{chunk_index + 1}")
    file.save(chunk_path)

    if chunk_index == 0:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('INSERT INTO file_metadata (uuid, filename) VALUES (?, ?)', (file_uuid, file.filename))

    if chunk_index == total_chunks - 1:
        asyncio.run_coroutine_threadsafe(upload_to_discord(file_uuid), bot.loop)

    return jsonify({'success': True, 'file_uuid': file_uuid})

@app.route('/upload_progress/<file_uuid>')
@login_required
def get_upload_progress(file_uuid):
    return jsonify({'progress': upload_progress.get(file_uuid, 0)})

@app.route('/files')
@login_required
def files():
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
    with sqlite3.connect(DB_NAME) as conn:
        file = conn.execute('SELECT filename, upload_date FROM file_metadata WHERE uuid = ?', (file_uuid,)).fetchone()
    if not file:
        return "File not found", 404

    return render_template('file_info.html', file_uuid=file_uuid, filename=file[0], upload_date=file[1])

@app.route('/download/<file_uuid>')
@login_required
def download_file(file_uuid):
    session_uuid = request.args.get('session_uuid')
    if not session_uuid:
        return "Session UUID is required", 400

    with sqlite3.connect(DB_NAME) as conn:
        file = conn.execute('SELECT filename, discord_channel_id FROM file_metadata WHERE uuid = ?', (file_uuid,)).fetchone()
    if not file:
        return "File not found", 404

    session_download_dir = os.path.join(DOWNLOAD_FOLDER, session_uuid, file_uuid)
    os.makedirs(session_download_dir, exist_ok=True)

    asyncio.run_coroutine_threadsafe(download_chunks_from_discord(file_uuid, file[1], session_uuid, session_download_dir), bot.loop).result()

    combined_file_path = os.path.join(session_download_dir, file[0])
    combine_chunks(file_uuid, session_download_dir, combined_file_path)

    @after_this_request
    def cleanup(response):
        threading.Thread(target=delayed_cleanup, args=(combined_file_path, session_download_dir), daemon=True).start()
        return response

    return send_file(combined_file_path, as_attachment=True, download_name=file[0])

@app.route('/download_progress/<session_uuid>/<file_uuid>')
@login_required
def download_progress_endpoint(session_uuid, file_uuid):
    return jsonify({'progress': download_progress.get(f"{session_uuid}_{file_uuid}", 0)})

async def download_chunks_from_discord(file_uuid, channel_id, session_uuid, download_dir):
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
    time.sleep(600)
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
    init_db()
    threading.Thread(target=bot.run, args=(DISCORD_TOKEN,), daemon=True).start()
    app.run(debug=True, host="0.0.0.0", port=80)
