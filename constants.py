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
# Server init configuration

# Run command for vanilla
# RUN_SERVER_COMMAND = [f"{JAVA_DIR}/java", "-jar",
#                       "-Xmx5G",  # 5GB RAM for running server
#                       "-Xms1G",  # 1GB RAM as initial star-up memory
#                       f"{SERVER_DIR}/server.jar",  # Server instance to be run
#                       "--nogui"]  # Unable GUI / speed up

# Run command mods
RUN_SERVER_COMMAND = [f"{SERVER_DIR}/run.bat"]  # Unable GUI / speed up

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
TCP_RE = r'url=tcp://(.*?)\n'
SERVER_STOPPED_PATTERN = "ThreadedAnvilChunkStorage: All dimensions are saved"
# Ngrok temp log file name
OUT_NGROK_FILE = "output.log"
# Timings
SERVER_STATUS_CHECK_PERIOD_S = 60
SERVER_START_TIMEOUT_S = 5 * 60
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
# Bots working channels
ADMIN_CHANNEL_NAME = "admin_control"
USERS_CHANNEL_NAME = "bot_chatting"
# Upload and download variables
DIRECTORIES_TO_ZIP = [SAVE_DIR, f"{SERVER_DIR}/whitelist.json", f"{SERVER_DIR}/banned-players.json"]
SAVE_FILE_NAME = "world_save.zip"
SAVE_FOLDER_NAME = "world"

