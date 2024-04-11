import sys
import threading
import os
import discord
import asyncio
from datetime import datetime
from sensitive_data import BOT_TOKEN
from constants import USERS_CHANNEL_NAME, ADMIN_CHANNEL_NAME, ADMIN_PREFIX, DISCORD_BOT_STOP_SIGNAL, DISCORD_BOT_STOPPING_LISTNER_SIGNAL

tcp_address = sys.argv[1]

# All intents found on developers side
intents = discord.Intents.all()
bot = discord.Client(intents=intents)


async def send_server_status():
    """
    Sens status of server at start.
    :return:
    """
    channel = discord.utils.get(bot.get_all_channels(), name='admin_control')
    if channel:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await channel.send(f"[{current_time}] [Server control/INFO]: Server status started.")


def wait_for_user_input():
    """
    Redirects info from parent process to specific channel.
    :return:
    """
    stop_app = False
    while True:
        try:
            user_input = input()
        except EOFError:
            break
        channel_name = USERS_CHANNEL_NAME
        if user_input.startswith(USERS_CHANNEL_NAME):
            user_input = user_input.replace(USERS_CHANNEL_NAME, "")
        else:
            user_input = user_input.replace(ADMIN_CHANNEL_NAME, "")
            channel_name = ADMIN_CHANNEL_NAME
            if DISCORD_BOT_STOP_SIGNAL in user_input:
                stop_app = True
                print(DISCORD_BOT_STOPPING_LISTNER_SIGNAL)
        channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
        if stop_app:
            os._exit(0)
        if channel:
            asyncio.run_coroutine_threadsafe(channel.send(user_input), bot.loop)


@bot.event
async def on_ready():
    """
    Bots behaviour when started.
    :return:
    """
    bot.loop.create_task(send_server_status())


@bot.event
async def on_message(message):
    """
    Bots reaction to message
    :param message:
    :return:
    """
    username = str(message.author).split("#")[0]
    channel = str(message.channel.name)
    user_message = str(message.content)

    if message.author == bot.user:
        return

    if channel == USERS_CHANNEL_NAME:
        if user_message.lower() in {"hello", "hi"}:
            await message.channel.send(f'Hello {username}.')
            return
        elif user_message.lower() == "ip":
            await message.channel.send(f'Here you are buddy: {tcp_address}')
        elif user_message.lower() == "bye":
            await message.channel.send(f'Bye {username}.')
    if channel == ADMIN_CHANNEL_NAME:
        if user_message.lower().startswith(ADMIN_PREFIX):
            print(f"{ADMIN_CHANNEL_NAME} message: {user_message}")
        else:
            await message.channel.send(f'{username} "{user_message}" is unrecognized command.')

# Start the thread to wait for user input
input_thread = threading.Thread(target=wait_for_user_input)
input_thread.start()

bot.run(BOT_TOKEN)
