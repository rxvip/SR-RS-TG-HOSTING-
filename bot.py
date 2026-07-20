import os
import sys
import time
import json
import zipfile
import subprocess
import threading
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ================= BOT CONFIG =================
BOT_TOKEN = "8457861380:AAHNWoNDWfHl5yQbqMk8y31pWO26g8rkcRQ"          # <-- Replace with your bot token
OWNER_ID = 8477364397                 # <-- Replace with your Telegram user ID

STORAGE_DIR = "user_files"
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uplo556ads")
DATA_FILE = os.path.join(STORAGE_DIR, "users.json")
BUTTONS_FILE = os.path.join(STORAGE_DIR, "custom_buttons.json")  # কাস্টম বাটন সেভ রাখার ফাইল

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        pass

# ================= GLOBALS =================
users = {}                 # user_id -> {"files": [list_of_filenames]}
custom_buttons = {}        # button_name -> response_text
active_scripts = {}        # user_id -> file_path -> process
logs_store = {}            # user_id -> file_path -> logs (internal only)
install_waiting_users = {}
bot_start_time = time.time()
START_TIME = datetime.now()

RECOMMENDED_PACKAGES = [
    "pip", "setuptools", "wheel", "requests", "numpy", "pandas", "flask", "aiohttp",
    "pyrogram", "python-dotenv", "beautifulsoup4", "lxml", "pillow", "matplotlib",
    "scipy", "scikit-learn", "pytest"
]
PYTG_CALLS_PACKAGE = "git+https://github.com/pytgcalls/pytgcalls.git"

# ================= DATA PERSISTENCE =================
def save_data():
    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(users, f, indent=4)
    os.replace(temp_file, DATA_FILE)

def load_data():
    global users
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                raw_data = json.load(f)
                users.clear()
                for k, v in raw_data.items():
                    users[int(k)] = v
        except Exception as e:
            print(f"Load Error: {e}")
            users = {}

def save_buttons():
    with open(BUTTONS_FILE, "w") as f:
        json.dump(custom_buttons, f, indent=4)

def load_buttons():
    global custom_buttons
    if os.path.exists(BUTTONS_FILE):
        try:
            with open(BUTTONS_FILE, "r") as f:
                custom_buttons = json.load(f)
        except Exception as e:
            print(f"Buttons Load Error: {e}")
            custom_buttons = {}

load_data()
load_buttons()

# ================= UTILITIES =================
def uptime():
    s = int(time.time() - bot_start_time)
    return f"{s//3600}h {(s%3600)//60}m {s%60}s"

def user_folder(uid):
    path = os.path.join(UPLOAD_DIR, str(uid))
    os.makedirs(path, exist_ok=True)
    return path

def install_requirements(folder):
    req_file = os.path.join(folder, "requirements.txt")
    if os.path.exists(req_file):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        except:
            pass

# ================= SCRIPT RUNNING & LOGGING =================
def run_script_thread(user_id, file_path):
    try:
        proc = subprocess.Popen(
            [sys.executable, os.path.abspath(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        active_scripts.setdefault(user_id, {})[file_path] = proc
        logs_store.setdefault(user_id, {})[file_path] = []

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                logs_store[user_id][file_path].append(line.strip())
                logs_store[user_id][file_path] = logs_store[user_id][file_path][-50:]
        proc.wait()
    except Exception as e:
        print(f"Error in script {file_path}: {e}")
    finally:
        if user_id in active_scripts:
            active_scripts[user_id].pop(file_path, None)

def start_script(user_id, file_path):
    thread = threading.Thread(target=run_script_thread, args=(user_id, file_path), daemon=True)
    thread.start()

# ================= TELEGRAM BOT INIT =================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ===== MAIN MENU =====
def control_buttons():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    # আপনার অনুরোধ অনুযায়ী Speed, Status, Recommended Install বাটন তিনটি বাদ দেওয়া হয়েছে
    markup.row(
        KeyboardButton("🌏 Upload"),
        KeyboardButton("📁 𝐌𝐲 𝐅𝐢𝐥𝐞𝐬")
    )
    markup.row(
        KeyboardButton("🔄 𝐑𝐞𝐬𝐭𝐚𝐫𝐭"),
        KeyboardButton("⏹ 𝐒𝐭𝐨𝐩")
    )

    # এডমিন যেসব কাস্টম বাটন এড করবে সেগুলো এখানে ডাইনামিকালি শো হবে
    custom_list = list(custom_buttons.keys())
    for i in range(0, len(custom_list), 2):
        row_buttons = [KeyboardButton(btn) for btn in custom_list[i:i+2]]
        markup.row(*row_buttons)

    return markup

# ================= ADMIN COMMANDS =================
@bot.message_handler(commands=['addbutton'])
def add_button_command(message):
    uid = message.from_user.id
    if uid != OWNER_ID:
        return

    try:
        # Format: /addbutton বাটন নাম | বাটনে চাপ দিলে যে লেখা আসবে
        text = message.text.split('/addbutton ', 1)[1]
        btn_name, btn_text = text.split('|', 1)
        btn_name = btn_name.strip()
        btn_text = btn_text.strip()

        custom_buttons[btn_name] = btn_text
        save_buttons()
        bot.reply_to(message, f"✅ '{btn_name}' বাটনটি সফলভাবে যোগ করা হয়েছে।", reply_markup=control_buttons())
    except Exception as e:
        bot.reply_to(message, "❌ ভুল ফরম্যাট! সঠিক ফরম্যাট:\n`/addbutton বাটন_নাম | বাটন_টেক্সট`", parse_mode="Markdown")

@bot.message_handler(commands=['delbutton'])
def del_button_command(message):
    uid = message.from_user.id
    if uid != OWNER_ID:
        return

    try:
        btn_name = message.text.split('/delbutton ', 1)[1].strip()
        if btn_name in custom_buttons:
            del custom_buttons[btn_name]
            save_buttons()
            bot.reply_to(message, f"✅ '{btn_name}' বাটনটি ডিলিট করা হয়েছে।", reply_markup=control_buttons())
        else:
            bot.reply_to(message, "❌ এই নামের কোনো কাস্টম বাটন পাওয়া যায়নি।")
    except Exception as e:
        bot.reply_to(message, "❌ ভুল ফরম্যাট! সঠিক ফরম্যাট:\n`/delbutton বাটন_নাম`", parse_mode="Markdown")


# ================= COMMAND /start =================
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.from_user.id
    if uid not in users:
        users[uid] = {"files": []}
        save_data()

    welcome = (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃   🚀 SR-RS  HOSTING      ┃\n"
        "┃      VERSION 0.1.0        ┃\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"👤 Wᴇʟᴄᴏᴍᴇ {message.from_user.first_name}!\n"
        f"🆔 Uꜱᴇʀ ID: {uid}\n\n"
        f"📁 Fɪʟᴇꜱ: {len(users[uid]['files'])}\n\n"
        "⚡ Fᴇᴀᴛᴜʀᴇꜱ:\n"
        "• Aᴜᴛᴏ-Rᴇᴄᴏᴠᴇʀʏ Sʏꜱᴛᴇม\n"
        "• Pʏᴛʜᴏɴ / Jꜱ / Zɪᴘ Sᴜᴘᴘᴏʀᴛ\n\n"
        "Uꜱᴇ ᴛʜᴇ Bᴜᴛᴛᴏɴꜱ Bᴇʟᴏᴡ Tᴏ Nᴀᴠɪɢᴀᴛ惠."
    )
    bot.send_message(uid, welcome, reply_markup=control_buttons())

# ================= TEXT HANDLER =================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def text_handler(message):
    uid = message.from_user.id
    text = message.text
    user_data = users.setdefault(uid, {"files": []})

    # প্রথমে চেক করবে ইউজার কোনো কাস্টম বাটনে চাপ দিয়েছে কি না
    if text in custom_buttons:
        bot.reply_to(message, custom_buttons[text])
        return

    if text.startswith("🌏"):
        bot.reply_to(message, "📤 𝐒𝐞𝐧𝐝 𝐲𝐨𝐮𝐫 .𝐩𝐲, .𝐳𝐢𝐩, .𝐭𝐱𝐭 𝐟𝐢𝐥𝐞 𝐧𝐨𝐰.")

    elif text.startswith("📁"):
        files = user_data["files"]
        if not files:
            bot.reply_to(message, "❌ No files.")
            return
        buttons = [[InlineKeyboardButton(f"{f}", callback_data=f"file_{f}")] for f in files]
        bot.reply_to(message, "📁 𝐘𝐨𝐮𝐫 𝐅𝐢𝐥𝐞𝐬:", reply_markup=InlineKeyboardMarkup(buttons))

    elif text.startswith("🔄"):
        if uid in active_scripts:
            for p in active_scripts[uid].values():
                p.kill()
            active_scripts[uid] = {}
        folder = user_folder(uid)
        for fname in user_data["files"]:
            if fname.endswith(".py"):
                path = os.path.join(folder, fname)
                if os.path.exists(path):
                    start_script(uid, path)
        bot.reply_to(message, "🔄 All your scripts have been restarted.")

    elif text.startswith("⏹"):
        if uid in active_scripts:
            for p in active_scripts[uid].values():
                p.kill()
            active_scripts[uid] = {}
        bot.reply_to(message, "⏹ Stopped all your scripts.")

# ================= FILE HANDLER =================
@bot.message_handler(content_types=['document'])
def document_handler(message):
    uid = message.from_user.id
    user_data = users.setdefault(uid, {"files": []})
    if uid != OWNER_ID and len(user_data["files"]) >= 2:
        bot.reply_to(message, "❌ You have reached the limit of 2 files. Contact the owner for more.")
        return

    doc = message.document
    filename = doc.file_name
    if not filename.endswith((".py", ".zip", ".txt")):
        bot.reply_to(message, "❌ Only .py, .zip, .txt allowed.")
        return

    folder = user_folder(uid)
    save_path = os.path.join(folder, filename)
    msg = bot.reply_to(message, "⬇ Downloading...")

    file_info = bot.get_file(doc.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(save_path, 'wb') as f:
        f.write(downloaded_file)

    if filename not in user_data["files"]:
        user_data["files"].append(filename)
        save_data()

    if filename.endswith(".zip"):
        with zipfile.ZipFile(save_path, 'r') as zip_ref:
            zip_ref.extractall(folder)
        install_requirements(folder)
        bot.edit_message_text("📦 ZIP extracted.", chat_id=message.chat.id, message_id=msg.message_id)
    elif filename.endswith(".txt"):
        install_requirements(folder)
        bot.edit_message_text("📦 Requirements installed.", chat_id=message.chat.id, message_id=msg.message_id)
    elif filename.endswith(".py"):
        start_script(uid, save_path)
        bot.edit_message_text(f"⚡ Starting {filename}...", chat_id=message.chat.id, message_id=msg.message_id)

# ================= CALLBACK HANDLER =================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    user_data = users.get(uid, {"files": []})
    data = call.data

    if data.startswith("file_"):
        filename = data[5:]
        user_name = call.from_user.first_name or "User"
        msg = (
            f"⚡ <b>𝐀𝐜𝐭𝐢𝐨𝐧𝐬 𝐟𝐨𝐫</b><code> {filename}</code>\n\n"
            f"🆔 <b>𝐔𝐬𝐞𝐫 𝐈𝐃:</b> <code>{uid}</code>\n"
            f"👤 <b>𝐍𝐚𝐦𝐞:</b><code> {user_name}</code>\n"
            f"🟢 <b>𝐑𝐮𝐧𝐧𝐢ﻨ𝐠:</b> <code> 1</code>"
        )
        buttons = [
            [InlineKeyboardButton("▶ Run", callback_data=f"run_{filename}"),
             InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{filename}")],
            [InlineKeyboardButton("⬅ Back", callback_data="myfiles")]
        ]
        bot.edit_message_text(
            msg,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML"
        )

    elif data == "myfiles":
        files = user_data["files"]
        if not files:
            bot.edit_message_text("❌ No files.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        buttons = [[InlineKeyboardButton(f"{f}", callback_data=f"file_{f}")] for f in files]
        bot.edit_message_text(
            "📁 𝐘𝐨𝐮𝐫 𝐅𝐢𝐥𝐞𝐬:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("run_"):
        fname = data[4:]
        path = os.path.join(user_folder(uid), fname)
        if os.path.exists(path):
            start_script(uid, path)
            bot.answer_callback_query(call.id, f"▶ {fname} started")
        else:
            bot.answer_callback_query(call.id, "❌ File not found")

    elif data.startswith("stop_"):
        fname = data[5:]
        path = os.path.join(user_folder(uid), fname)
        proc = active_scripts.get(uid, {}).get(path)
        if proc:
            proc.kill()
            active_scripts[uid].pop(path, None)
            bot.answer_callback_query(call.id, f"⏹ {fname} stopped")
        else:
            bot.answer_callback_query(call.id, "❌ Script not running")

# ================= AUTO-RESTORE ON START =================
def restore_all():
    load_data()
    print("🔄 Restoring scripts...")
    for uid, data in users.items():
        folder = user_folder(uid)
        for f in data.get("files", []):
            if f.endswith(".py"):
                path = os.path.join(folder, f)
                if os.path.exists(path):
                    start_script(uid, path)
    print("✅ System Ready")

# ================= POLLING =================
if __name__ == "__main__":
    restore_all()
    print(" SR-RS  HOSTING BoT IS RUNNING 🏃")
    bot.polling(none_stop=True)
