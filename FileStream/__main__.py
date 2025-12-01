import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers
from FileStream.config import Telegram, Server
from pyrogram import idle
from pyrogram.errors import FloodWait
from flask import Flask
import threading
import httpx  # <--- Added

from FileStream.bot import FileStream
from FileStream.bot.clients import initialize_clients
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

web_app = Flask(__name__)

@web_app.route('/')
def hello_world():
    return "Hello, World!"

# Run the Flask app in a separate thread
def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# Logger Setup
logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        handlers.RotatingFileHandler(
            "streambot.log", mode="a", maxBytes=104857600, backupCount=2, encoding="utf-8"
        ),
    ],
)

logging.getLogger("pyrogram").setLevel(logging.ERROR)

loop = asyncio.get_event_loop()

# ------------------- NEW PING FUNCTION -------------------
async def ping_server():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(Server.PING_URL, timeout=10)
                logging.info(f"PING to {Server.PING_URL} => {r.status_code}")
        except Exception as e:
            logging.error(f"PING request failed: {e}")

        await asyncio.sleep(40)  # Run every 1 minute
# ---------------------------------------------------------

async def start_services():
    print()
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Start ping function if Server.PING_URL exists
    if getattr(Server, "PING_URL", None):
        asyncio.create_task(ping_server())
        logging.info(f"Periodic PING enabled => {Server.PING_URL}")

    if Telegram.SECONDARY:
        print("------------------ Starting as Secondary Server ------------------")
    else:
        print("------------------- Starting as Primary Server -------------------")

    print()
    print("-------------------- Initializing Telegram Bot --------------------")

    await FileStream.start()
    bot_info = await FileStream.get_me()
    FileStream.id = bot_info.id
    FileStream.username = bot_info.username
    FileStream.fname = bot_info.first_name

    print("------------------------------ DONE ------------------------------")
    print()
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    print()
    print("------------------------- Service Started -------------------------")
    print(f"                        bot =>> {bot_info.first_name}")
    if bot_info.dc_id:
        print(f"                        DC ID =>> {bot_info.dc_id}")
    print("------------------------------------------------------------------")

    # Send "Bot started" message with FloodWait handling
    while True:
        try:
            await FileStream.send_message(6883997969, "Bot started")
            break
        except FloodWait as e:
            wait_time = e.value
            logging.warning(f"FloodWait: sleeping for {wait_time} seconds before retrying send_message.")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logging.error(f"Failed to send 'Bot started' message: {e}")
            break

    await idle()


async def cleanup():
    await FileStream.stop()


if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logging.error(traceback.format_exc())
    finally:
        loop.run_until_complete(cleanup())
        loop.stop()
        print("------------------------ Stopped Services ------------------------")
