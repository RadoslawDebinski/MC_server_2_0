# Used python version
# https://www.python.org/downloads/release/python-3118/
# My libraries
import argparse
import errno
import io
import re
import signal
import shutil
import socket
import subprocess
import sys
import threading
import time
import datetime
# Google stuff
import pickle
import zipfile

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from constants import *


class ManageServer:
    def __init__(self, standard_process: bool = True, reset_flag: bool = False):
        """
        Initializes all class variables, checks for free port for server on device, starts app.
        :param standard_process: Flag which indicated default processing strategy execution.
        :param reset_flag: Indicates that app is during reset and input from user should not be proceeded.
        """
        # Processes
        self.server_process = None
        self.ssh_process = None
        self.discord_bot_process = None
        # Main threads
        self.server_listener_thread = None
        self.discord_bot_thread = None
        # Logger set up
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        # Flags
        self.standard_process = standard_process
        self.server_started = False
        self.tcp_address_found = False
        self.server_stopped = False
        self.reset_app = False
        self.external_stop = False
        # Port variable
        self.free_port = None
        self.log_file_message("Searching for free port.")
        self.find_free_port()
        # Google drive processing variables
        self.drive_files_list = []
        # Tcp communication variables
        self.extracted_address = ""

        if self.standard_process:
            standard_start = not reset_flag
            self.run_app(standard_start)

    def find_free_port(self) -> None:
        """
        Function searches for free port in localhost in range from 49152 to 65536.
        If found will be saved to variable if not further app execution will be stopped.
        :return:
        """
        # https://en.wikipedia.org/wiki/Registered_port
        port_out = None
        for port in range(49152, 65536):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:  # If the connection was successful, the port is not free
                continue
            elif result == errno.ECONNREFUSED:  # Connection refused, likely means the port is free
                port_out = port
                break
            else:
                # Handle other error cases if needed
                self.log_file_message(f"Error checking port {port}: {result}")

        self.free_port = port_out
        if self.free_port:
            self.log_file_message(f"Free port found: {self.free_port}.")
        else:
            self.log_file_message("Free port not found.")
            self.standard_process = False

    def run_app(self, start_flag: bool = True):
        """
        Calls functions which: changes port in server's properties, starts server, starts ngrok connection, activates
        console interface.
        :param start_flag: Indicates that app is during standard start, not reboot.
        :return:
        """
        self.check_credentials()
        self.download_last_save(start_flag)
        self.change_config_port()
        self.run_server()
        if self.server_started:
            self.connect_serveo()
            if self.tcp_address_found:
                self.log_file_message("Starting discord bot thread.")
                self.discord_bot_thread = threading.Thread(target=self.run_discord_bot)
                self.discord_bot_thread.start()
                # Run while true console
                while True:
                    self.console_interface()
                    if self.server_stopped:
                        if self.reset_app:
                            run_main_command = ["./restart.sh"]
                            subprocess.call(run_main_command, shell=True)
                        # wait a moment to make output visible
                        time.sleep(5)
                        break

        else:
            self.log_file_message(f"Server starting time out exceeded: "
                                  f"{SERVER_START_TIMEOUT_S} limit.")

    def check_credentials(self):
        """
        Informs user about current status of credentials.json used by Google Drive service. If modify date of this file
        is not within 1 week from the current date gives a warning.
        :return:
        """
        credentials_name = "credentials.json"
        if os.path.exists(credentials_name):
            modification_time = os.path.getmtime(credentials_name)
            modification_date = datetime.fromtimestamp(modification_time)
            self.log_file_message(f"Modify date of {credentials_name} is {modification_date}.")
            current_date = datetime.now()
            # Calculate the difference between current date and modification date
            difference = current_date - modification_date
            # Check if the difference is not bigger than 7 days
            if difference.days <= 7:
                self.log_file_message(f"The modification date of '{credentials_name}' "
                                      f"is within 1 week from the current date.")
            else:
                self.log_file_message(f"!!!WARNING The modification date of '{credentials_name}' "
                                      f"is not within 1 week from the current date!!!")
        else:
            self.log_file_message(f"No {credentials_name} file found.")
            raise Exception("Stopping further execution.")

    def change_config_port(self):
        """
        After finding free port to connect server, changes its value in server's properties file before starting
        server's instance.
        :return:
        """
        with open(f"{SERVER_DIR}/server.properties", "r+") as server_properties:
            l_server_configs = server_properties.readlines()
            server_properties.seek(0)
            i_server_port_id = ["server-port=" in line for line in l_server_configs].index(True)
            l_server_configs[i_server_port_id] = f"server-port={self.free_port}\n"
            server_properties.writelines(l_server_configs)
        server_properties.close()

    def log_file_message(self, message_content: str, sent_by_bot: bool = False) -> None:
        """
        Takes input message and creates communicate with time prefix. Then info is sent to console and logg file.
        :param message_content: String which should be sent.
        :param sent_by_bot: Set to True to mark it is a bots message.
        :return:
        """
        if sent_by_bot:
            message = f"[{str(datetime.now()).split(' ')[-1].split('.')[0]}] [Server control/BOT]: {message_content}"
        else:
            message = f"[{str(datetime.now()).split(' ')[-1].split('.')[0]}] [Server control/INFO]: {message_content}"
        print(message)
        self.logger.info(f"{message}")

    def run_server(self):
        """
        Runs server's thread and waits in case of start-up timeout.
        After correct activation calls server's listener thread.
        :return:
        """
        # Create a Thread object and pass server run function to it
        server_start_time = time.time()
        self.log_file_message("Starting server thread.")
        serv_thread = threading.Thread(target=self.run_server_proc)
        serv_thread.start()
        while int(time.time() - server_start_time) < SERVER_START_TIMEOUT_S and not self.server_started:
            pass
        serv_thread.join()
        self.log_file_message("Server started properly.")
        self.log_file_message("Starting server listener thread.")
        if self.server_started:
            self.server_listener_thread = threading.Thread(target=self.server_listener)
            self.server_listener_thread.start()

    def run_server_proc(self):
        """
        Runs server's subprocess and check by Regex if everything started correctly.
        :return:
        """
        # https://minecraft.wiki/w/Tutorials/Setting_up_a_server
        # https://discordpy.readthedocs.io/en/latest/intents.html
        # https://stackoverflow.com/questions/70920148/pycord-message-content-is-empty
        os.chdir(SERVER_DIR)
        self.log_file_message("Starting server subprocess.")
        self.server_process = subprocess.Popen(RUN_SERVER_COMMAND, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        server_start_time = time.time()
        self.log_file_message("Recording server console...")
        for line in iter(self.server_process.stdout.readline, ""):
            line = line.decode('utf-8', errors='ignore')
            print(line[:-1])
            if match := re.search(SERVER_STARTED_RE, line):
                result = match[1]
                self.log_file_message(f"Server started in: {result}.")
                self.log_file_message(f"Whole server environment build process took: ~.-"
                                      f"{int(time.time() - server_start_time)}s.")
                self.server_started = True
                break
            elif int(time.time() - server_start_time) > SERVER_START_TIMEOUT_S:
                self.log_file_message(f"Server starting time out exceeded: "
                                      f"{SERVER_START_TIMEOUT_S} limit.")
        os.chdir(CURRENT_DIR)
        self.log_file_message("Server thread ended.")

    def server_listener(self):
        """
        Function called by server sub-process listening thread to provide output from console to user.
        If output line will equal standard last line after /stop command, changes flag of app termination.
        :return:
        """
        for line in iter(self.server_process.stdout.readline, b''):
            line_text = line.decode('utf-8')[:-1]
            print(line_text)
            if line_text.endswith(SERVER_STOPPED_PATTERN):
                self.server_stopped = True
                break

    def connect_serveo(self):
        """
        Runs serveo ssh command and saves new ip.
        :return:
        """
        # https://serveo.net/
        # Clearing the previous log
        # run_ssh_command = f"sudo ssh -R {self.free_port}:localhost:{self.free_port} serveo.net"
        run_ssh_command = ["ssh", "-R", f"{self.free_port}:localhost:{self.free_port}", "serveo.net"]
        self.log_file_message("Staring serveo subprocess.")
        self.ssh_process = subprocess.Popen(run_ssh_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        ssh_start_time = time.time()
        for line in iter(self.ssh_process.stdout.readline, ""):
            line = line.decode('utf-8', errors='ignore')
            print(line)
            if re.search(SSH_STARTED_RE, line):
                self.extracted_address = f"{socket.gethostbyname('serveo.net')}:{self.free_port}"
                self.tcp_address_found = True
                break
            elif int(time.time() - ssh_start_time) > SSH_START_TIMEOUT_S:
                self.log_file_message(f"SSH with serveo starting time out exceeded: "
                                      f"{SERVER_START_TIMEOUT_S} limit.")

    def run_discord_bot(self):
        """
        Runs bots subprocess and redirects its output to current console with Bot prefix.
        :return:
        """
        # https://www.geeksforgeeks.org/discord-bot-in-python/
        self.log_file_message("Starting discord bot subprocess.")
        run_bot_command = ["python3", "discord_bot.py", f"{self.extracted_address}"]
        self.discord_bot_process = subprocess.Popen(run_bot_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        for line in iter(self.discord_bot_process.stdout.readline, ""):
            line_text = line.decode('utf-8')[:-1]
            if not line_text:
                self.log_file_message(line_text, sent_by_bot=True)
            if line_text.lower().startswith(ADMIN_PREFIX) and EXTERNAL_SAVE_PATTERN in line_text.lower():
                self.log_file_message(f"Admin save command received.")
                self.send_bot_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                      f"[Server control/INFO]:Admin save command received.", send_to_admin=True)
                self.external_stop = True
                self.stop_app(update_saves=True)
                break
            if line_text.lower().startswith(ADMIN_PREFIX) and EXTERNAL_STOP_PATTERN in line_text.lower():
                self.log_file_message(f"Admin stop command received.")
                self.send_bot_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                      f"[Server control/INFO]:Admin stop command received.", send_to_admin=True)
                self.external_stop = True
                self.stop_app()
                break
            if self.server_stopped:
                break

    def console_interface(self):
        """
        Simple interface to communicate with instance of server and main app.
        :return:
        """
        command = input()
        if command.lower() == "exit":
            self.stop_app()
        elif command.lower() == "save":
            self.stop_app(update_saves=True)
        elif command.lower() == "reset":
            self.reset_app = True
            self.send_bot_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                  f"[Server control/INFO]: Server status reset.", send_to_admin=True)
            self.stop_app(update_saves=True)
        elif command.startswith("/s "):
            self.send_server_command(command[3:])
        elif command.startswith("/b "):
            self.send_bot_message(command[3:])
        elif command.lower() == "help":
            self.log_file_message(HELP_MESSAGE)
        else:
            self.log_file_message(f"Command: '{command}' not recognized.")

    def stop_app(self, update_saves: bool = False):
        """
        Stops app is a safety way. Especially sends /stop command to server. And make server save to drive.
        :param update_saves: Indicates saving current world to drive.
        :return:
        """
        # Disconnect players
        self.log_file_message("Stopping ssh subprocess.")
        os.system(f"sudo kill {self.ssh_process.pid}")
        # Safely stop server
        self.log_file_message("Stopping server subprocess.")
        self.send_server_command("/stop")
        self.log_file_message("Waiting for server to stop.")
        while not self.server_stopped:
            pass
        self.send_bot_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                              f"[Server control/INFO]: Server status stopped.", send_to_admin=True)
        # If yes send world folder to drive
        if update_saves:
            self.send_bot_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                  f"[Server control/INFO]: Saving to Google Drive.", send_to_admin=True)
            self.save_server_to_drive()
            self.send_bot_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                  f"[Server control/INFO]: New save made on Google Drive.", send_to_admin=True)
        # Stop bot
        self.log_file_message("Stopping bot subprocess.")
        self.send_bot_message(DISCORD_BOT_STOP_SIGNAL, send_to_admin=True)
        self.discord_bot_process.terminate()
        if self.external_stop:
            sys.exit()

    """
    ****** Send Info To Sub-process Functions ******
    """

    def send_server_command(self, serv_command: str):
        """
        Sends command to server and waits some constant time to avoid mess in console.
        :param serv_command: Input command without newline at the end only content.
        :return:
        """
        self.log_file_message(f"Server command '{serv_command}' redirected.")
        # Send a command to the subprocess (replace with your actual command)
        command_to_send = f"{serv_command}\n"
        self.server_process.stdin.write(command_to_send.encode('utf-8'))
        self.server_process.stdin.flush()

    def send_bot_message(self, bot_message: str, send_to_admin: bool = False):
        """
        Send string via bot to specific channel.
        :param send_to_admin: Indicates adding specific channel's prefix.
        :param bot_message: Input message without newline at the end only content. Prefix is a name of channel.
        :return:
        """
        if not bot_message == DISCORD_BOT_STOP_SIGNAL:
            self.log_file_message(f"Bots message '{bot_message}' redirected.")
        # Send a command to the subprocess (replace with your actual command)
        if send_to_admin:
            command_to_send = f"{ADMIN_CHANNEL_NAME}{bot_message}\n"
        else:
            command_to_send = f"{USERS_CHANNEL_NAME}{bot_message}\n"
        self.discord_bot_process.stdin.write(command_to_send.encode('utf-8'))
        self.discord_bot_process.stdin.flush()
        time.sleep(1)

    """
    ****** Google Drive Functions ******
    """

    def download_last_save(self, user_flag: bool = True):
        """
        Call functions which will download .zip file with last save, remove current last save from your device and unzip
        file with new one. Then it will remove all temporary files.
        :param user_flag: Flag which indicates that user input is needed.
        :return:
        """
        self.log_file_message("Would you like to download last save from Google Drive:")
        while user_flag:
            decision = input("(Y/N)")
            if decision.lower().startswith("n"):
                self.log_file_message("Last save will not be downloaded.")
                return
            elif decision.lower().startswith("y"):
                self.log_file_message("Last save will be downloaded.")
                break
            else:
                self.log_file_message("Please provide correct input:")
        self.log_file_message("Removing current save from device.")
        # shutil.rmtree(SAVE_DIR, ignore_errors=True)
        self.log_file_message("Getting access to drive.")
        service = self.get_gdrive_service(SCOPES)
        # Call the Drive v3 API
        items = self.drive_list_files(service)
        self.translate_files(items)
        self.find_save_and_download()
        self.remove_directories_and_files(DIRECTORIES_TO_ZIP)
        self.unzip_folder(f"{SERVER_DIR}/{SAVE_FILE_NAME}", SERVER_DIR)
        self.remove_directories_and_files([f"{SERVER_DIR}/{SAVE_FILE_NAME}"])
        self.log_file_message("Current server was updated with the latest save.")

    @staticmethod
    def get_gdrive_service(scopes: list):
        """
        Function taken from: https://thepythoncode.com/article/using-google-drive--api-in-python?utm_content=cmp-true
        :param scopes: list of scopes
        :return:
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        # return Google Drive API service
        return build('drive', 'v3', credentials=creds)

    def drive_list_files(self, service):
        """
        Retrieves all files from Google Drive excluding files from the trash, using pagination.
        :param service: Google Drive API service object.
        """
        self.log_file_message("Listing all files names from drive.")
        page_token = None
        all_files = []

        while True:
            results = service.files().list(
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime)",
                pageToken=page_token,
                q="trashed=false"  # Exclude files from the trash
            ).execute()

            items = results.get('files', [])
            all_files.extend(items)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return all_files

    def translate_files(self, items: list):
        """
        Function taken from: https://thepythoncode.com/article/using-google-drive--api-in-python?utm_content=cmp-true
        given items returned by Google Drive API, prints them in a tabular way
        :param items:
        :return:
        """
        self.log_file_message("Files names translation.")
        if not items:
            # empty drive
            self.log_file_message('No files found.')
        else:
            rows = []
            for item in items:
                # get the File ID
                id = item["id"]
                # get the name of file
                name = item["name"]
                try:
                    # parent directory ID
                    parents = item["parents"]
                except:
                    # has no parrents
                    parents = "N/A"
                try:
                    # get the size
                    size = int(item["size"])
                except:
                    # not a file, may be a folder
                    size = "N/A"
                # get the Google Drive type of file
                mime_type = item["mimeType"]
                # get last modified date time
                modified_time = item["modifiedTime"]
                # append everything to the list
                rows.append((id, name, parents, size, mime_type, modified_time))
            self.drive_files_list = rows

    def find_save_and_download(self):
        """
        Finds the newest .zip save file and downloads it to server location.
        :return:
        """
        self.log_file_message("Searching from newest save file.")
        youngest_folder_id = None
        youngest_folder_name = ""
        youngest_folder_date = ""
        youngest_folder_date_time = datetime.min
        worlds = []
        for item in self.drive_files_list:
            if item[4] == "application/zip" or item[4] == "application/x-zip-compressed":
                if item[1] == SAVE_FILE_NAME:
                    worlds.append(item)
                    self.log_file_message(f"Found folder with name: {item[1]} and date {item[5]}.")
                    # Parse date-time string into datetime object
                    item_datetime = datetime.strptime(item[5], "%Y-%m-%dT%H:%M:%S.%fZ")
                    if item_datetime > youngest_folder_date_time:
                        youngest_folder_id = item[0]
                        youngest_folder_name = item[1]
                        youngest_folder_date = item[5]
                        youngest_folder_date_time = item_datetime

        if youngest_folder_id:
            self.log_file_message(f"Downloading last save: {youngest_folder_name}, from: {youngest_folder_date}.")
            self.download_file(youngest_folder_id, youngest_folder_name, SERVER_DIR)
        else:
            self.log_file_message(f"No save found. Stop app.")
            sys.exit()

    def download_file(self, file_id, file_name, output_dir):
        """
        Downloads a file from Google Drive to a specific directory.
        :param file_id: ID of the file to download.
        :param file_name: Name to give the downloaded file.
        :param output_dir: Directory to save the downloaded file.
        """
        service = self.get_gdrive_service(SCOPES)
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(os.path.join(output_dir, file_name), 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
            self.log_file_message(f"Download {int(status.progress() * 100)}%.")

        self.log_file_message(f"File '{file_name}' downloaded successfully to '{output_dir}'.")

    @staticmethod
    def unzip_folder(zip_file: str, destination: str):
        """
        Unzips downloaded save to the specific directory.
        :param zip_file: Directory to file which should be unzipped.
        :param destination: Directory where this file should be unzipped.
        :return:
        """
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(destination)

    def save_server_to_drive(self):
        """
        Calls functions which removes the eldest world folder from drive and saves the current one.
        :return:
        """
        # https://thepythoncode.com/article/using-google-drive--api-in-python?utm_content=cmp-true
        self.log_file_message("Getting access to drive.")
        service = self.get_gdrive_service(SCOPES)
        # Call the Drive v3 API
        items = self.drive_list_files(service)
        self.translate_files(items)
        self.remove_eldest_folder()
        self.log_file_message(f"Sending world folder to drive.")
        self.zip_directories(DIRECTORIES_TO_ZIP, SAVE_FILE_NAME)
        self.upload_zip_file(SAVE_FILE_NAME, SAVE_FOLDER_NAME)
        self.remove_directories_and_files([f"{CURRENT_DIR}/{SAVE_FILE_NAME}"])

    def remove_eldest_folder(self):
        """
        Removes the eldest world folder from drive's main directory.
        :return:
        """
        self.log_file_message("Removing eldest world folder from the drive.")
        self.drive_files_list.sort(key=lambda x: datetime.fromisoformat(x[-1].replace("Z", "")), reverse=True)
        eldest_folder_id = None
        eldest_folder_name = ""
        eldest_folder_date = ""
        eldest_folder_date_time = datetime.now()
        worlds = []
        for item in self.drive_files_list:
            if item[4] == "application/vnd.google-apps.folder":
                if item[1] == SAVE_FOLDER_NAME:
                    worlds.append(item)
                    self.log_file_message(f"Found folder with name: {item[1]} and date {item[5]}.")
                    # Parse date-time string into datetime object
                    item_datetime = datetime.strptime(item[5], "%Y-%m-%dT%H:%M:%S.%fZ")
                    if item_datetime < eldest_folder_date_time:
                        eldest_folder_id = item[0]
                        eldest_folder_name = item[1]
                        eldest_folder_date = item[5]
                        eldest_folder_date_time = item_datetime

        if eldest_folder_id:
            service = self.get_gdrive_service(SCOPES)
            service.files().delete(fileId=eldest_folder_id).execute()
            self.log_file_message(f"Eldest folder with name: {eldest_folder_name} and modified-date "
                                  f"{eldest_folder_date} has been removed.")
        else:
            self.log_file_message("No folders found.")

    @staticmethod
    def zip_directories(directory_list: list, output_zip_name: str):
        """
        Zips directories from given list to one file in working directory.
        :param directory_list: List of directories which should be zipped.
        :param output_zip_name: Name of output zip.
        :return:
        """
        with zipfile.ZipFile(output_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in directory_list:
                if os.path.isfile(item):
                    zipf.write(item, os.path.basename(item))
                elif os.path.isdir(item):
                    base_name = os.path.basename(item)
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.join(base_name, os.path.relpath(file_path, item)))

    def upload_zip_file(self, zip_file_path, folder_name):
        """
        Uploads a specific .zip file to Google Drive inside a folder.
        """
        # Authenticate account
        service = self.get_gdrive_service(SCOPES)

        # Create folder if not exists
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        file = service.files().create(body=folder_metadata, fields="id").execute()
        folder_id = file.get("id")

        # Upload the zip file
        file_metadata = {
            "name": os.path.basename(zip_file_path),
            "parents": [folder_id]
        }
        media = MediaFileUpload(zip_file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        self.log_file_message(f"Zip file uploaded successfully, id: {file.get('id')}")

    def remove_directories_and_files(self, directory_list):
        """
        Removes directories and files specified in the directory list.
        :param directory_list: List of directories and files to remove.
        """
        for item in directory_list:
            if os.path.isfile(item):
                os.remove(item)
                self.log_file_message(f"File '{item}' removed successfully.")
            elif os.path.isdir(item):
                shutil.rmtree(item, ignore_errors=True)
                self.log_file_message(f"Directory '{item}' and its contents removed successfully.")
            else:
                self.log_file_message(f"Path '{item}' does not exist.")

    def upload_files_from_directory(self, directory_path, parent_folder_id=None):
        """
        Recursively uploads all files from a specific directory and its subdirectories to Google Drive while maintaining
        the folder structure.
        :param directory_path: Path to the directory containing files to upload.
        :param parent_folder_id: The ID of the parent folder in Google Drive. If None, a new folder will be created.
        """
        # Authenticate account
        service = self.get_gdrive_service(SCOPES)

        # If parent_folder_id is None, create a new folder on Google Drive
        if parent_folder_id is None:
            folder_metadata = {
                "name": os.path.basename(directory_path),
                "mimeType": "application/vnd.google-apps.folder"
            }
            file = service.files().create(body=folder_metadata, fields="id").execute()
            parent_folder_id = file.get("id")
            self.log_file_message("Folder ID:", parent_folder_id)

        # Iterate through files and subdirectories in the directory
        for filename in os.listdir(directory_path):
            filepath = os.path.join(directory_path, filename)
            if os.path.isfile(filepath):
                # Upload the file to the current parent folder
                file_metadata = {
                    "name": filename,
                    "parents": [parent_folder_id]
                }
                media = MediaFileUpload(filepath, resumable=True)
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                self.log_file_message(f"File '{filename}' uploaded successfully. ID: {file.get('id')}.")
            elif os.path.isdir(filepath):
                # Create a new folder on Google Drive for the subdirectory
                folder_metadata = {
                    "name": filename,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_folder_id]
                }
                sub_folder_file = service.files().create(body=folder_metadata, fields="id").execute()
                sub_folder_id = sub_folder_file.get("id")
                self.log_file_message(f"Sub-folder '{filename}' created successfully. ID: {sub_folder_id}.")

                # Recursively call the function for the subdirectory, using the new sub-folder as the parent folder
                self.upload_files_from_directory(filepath, sub_folder_id)


if __name__ == '__main__':
    # Create argument parser
    parser = argparse.ArgumentParser(description="This is main script of server control.")

    # Add boolean flag argument
    parser.add_argument("--reset", action="store_true", default=False, help="Set this flag to reset app.")

    # Parse the arguments
    args = parser.parse_args()

    ManageServer(reset_flag=args.reset)
