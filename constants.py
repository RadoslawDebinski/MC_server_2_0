import os
from datetime import datetime
import logging

# Used directories
CURRENT_DIR = os.getcwd()
# https://www.oracle.com/java/technologies/downloads/
JAVA_DIR = f"{CURRENT_DIR}/../../java/jdk-17.0.10/bin"
SERVER_DIR = f"{CURRENT_DIR}/../../server"
NGROK_DIR = f"{CURRENT_DIR}/../../ngrok"
LOGS_DIR = f"{CURRENT_DIR}/logs"
PYTHON_DIR = f"{CURRENT_DIR}/../../python/python"
SAVE_DIR = f"{SERVER_DIR}/world"
CONFIG_DIR = f"{SERVER_DIR}/config"
OUT_NGROK_FILE = "output.log"

# Run command mods
RUN_SERVER_COMMAND = [f"{SERVER_DIR}/run.bat"]

# Create and configure logger / log file
NOT_FILE_NAME_SIGNS = ["-", ":", ".", " "]
os.makedirs("logs", exist_ok=True)
LOG_NAME = f"logs/{''.join([elem if elem not in NOT_FILE_NAME_SIGNS else '_' for elem in str(datetime.now())])}.log"
logging.basicConfig(filename=LOG_NAME,
                    format='%(message)s',
                    filemode='w')
# Regex pattern vanilla
# SERVER_STARTED_RE = r'\[Server thread/INFO\]: Done \((.*?)\)! For help, type "help"'

# Regex pattern mods
SERVER_STARTED_RE = r'\[minecraft/DedicatedServer]: Done \((.*?)\)! For help, type "help"'
ZROK_STARTED_RE = "Run: started"
TCP_RE = r'url=tcp://(.*?)\n'
SERVER_STOPPED_PATTERN = "ThreadedAnvilChunkStorage: All dimensions are saved"
ADMIN_PREFIX = "admin"
EXTERNAL_SAVE_PATTERN = "save"
EXTERNAL_STOP_PATTERN = "exit"

# Timings
SERVER_STATUS_CHECK_PERIOD_S = 60
SERVER_START_TIMEOUT_S = 5 * 60
ZROK_START_TIMEOUT_S = 10
NGROK_STABILIZATION_TIME_S = 3
# Google drive scopes
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file']
# Help message content
HELP_MESSAGE = "\n\n" \
               "* exit - Safely stops the server application with all its sub-processes.\n" \
               "* save - Safely stops the server application with all its sub-processes and sends current content of " \
               "server's world folder to Google Drive.\n" \
               "* /s [command] - Sends [command] to server and redirects its output to current console.\n" \
               "* /b [message] - Sends [message] to discord channel for chatting with bot.\n" \
               "* help - Lists possible server control options.\n"
# Working channels on discord
ADMIN_CHANNEL_NAME = "admin_control"
USERS_CHANNEL_NAME = "bot_chatting"
# Discord constants
DISCORD_BOT_STOP_SIGNAL = "###DISCORD_BOT_STOP_SIGNAL###"
BOT_PREFIX = "BOT"
ZROK_PREFIX = "ZROK"
NGROK_PREFIX = "NGROK"
# Upload and download variables
DIRECTORIES_TO_ZIP = [SAVE_DIR, CONFIG_DIR, f"{SERVER_DIR}/whitelist.json", f"{SERVER_DIR}/banned-players.json",
                      f"{SERVER_DIR}/server.properties"]
SAVE_FILE_NAME = "world_save.zip"
SAVE_FOLDER_NAME = "world"


