from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from pytz import timezone
from verify import report_error 
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://chrijismi:appussetten@cluster0.6mo9h.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(MONGO_URI)

@Client.on_message(filters.command("credits"))
async def credits_command(client, message: Message):
    try:
        user_id = message.from_user.id
        db = mongo_client["FileToLink"]
        ist = timezone("Asia/Kolkata")
        today = datetime.now(ist).strftime("%d-%m-%Y")

        # Get temp credits from daily collection
        temp_credits = 0
        daily_collection = db[today]
        temp_doc = daily_collection.find_one({
            "name": "temp_credits",
            "date": today
        })
        if temp_doc and "user_credits" in temp_doc and str(user_id) in temp_doc["user_credits"]:
            temp_credits = temp_doc["user_credits"][str(user_id)]
            if isinstance(temp_credits, dict) and "$numberInt" in temp_credits:
                temp_credits = int(temp_credits["$numberInt"])

        # Get premium credits from premium_credit collection
        premium_credits = 0
        premium_collection = db["premium_credit"]
        premium_doc = premium_collection.find_one({"name": "premium_credit"})
        if premium_doc and "users" in premium_doc and str(user_id) in premium_doc["users"]:
            premium_credits = premium_doc["users"][str(user_id)]
            if isinstance(premium_credits, dict) and "$numberInt" in premium_credits:
                premium_credits = int(premium_credits["$numberInt"])

        # Stylish response
        response = f"""
✨ **Your Credit Status** ✨

🆓 **Temporary Credits**: `{temp_credits}`
💎 **Premium Credits**: `{premium_credits}`

🔹 **Credits refresh daily at 00:00 IST**
🔹 **Premium credits never expire**
        """

        # Reply buttons
        btn = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🪙 ʙᴜʏ ᴄʀᴇᴅɪᴛꜱ 🪙", url="https://t.me/Appuz_007"),
                InlineKeyboardButton("🎁 ɢᴇᴛ ꜰʀᴇᴇ ᴄʀᴇᴅɪᴛꜱ 🎁", url="https://t.me/Bots_Access_Manager_l_Bot?start=FITLETOLINK"),
            ]
        ])

        await message.reply_text(
            text=response,
            reply_markup=btn,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_to_message_id=message.id
        )

    except Exception as e:
        await message.reply_text("❌ Failed to fetch credit information. Please try again later.")
        fnc = "plugins.credits_command"
        await report_error(client, e, fnc)
