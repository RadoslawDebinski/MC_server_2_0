import sys
import threading

import discord
import asyncio
from datetime import datetime
from sensitive_data import BOT_TOKEN
from constants import USERS_CHANNEL_NAME, ADMIN_CHANNEL_NAME

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
    while True:
        user_input = input()
        channel_name = USERS_CHANNEL_NAME
        if user_input.startswith(USERS_CHANNEL_NAME):
            user_input = user_input.replace(USERS_CHANNEL_NAME, "")
        else:
            user_input = user_input.replace(ADMIN_CHANNEL_NAME, "")
            channel_name = ADMIN_CHANNEL_NAME
        channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
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
        if user_message.lower() == "hello" or user_message.lower() == "hi":
            await message.channel.send(f'Hello {username}.')
            return
        elif user_message.lower() == "ip":
            await message.channel.send(f'Here you are buddy: {tcp_address}')
        elif user_message.lower() == "bye":
            await message.channel.send(f'Bye {username}.')

# Start the thread to wait for user input
input_thread = threading.Thread(target=wait_for_user_input)
input_thread.start()

bot.run(BOT_TOKEN)
