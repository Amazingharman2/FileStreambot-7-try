import string
import random
import asyncio
import aiohttp
from pytz import timezone
from datetime import datetime
from pyrogram import Client
from pymongo import MongoClient
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MONGO_URI = <Verification DB ID>

mongo_client = MongoClient(MONGO_URI)

async def report_error(client: Client, error_message: str, fnc):
    try:
        await client.send_message(
            chat_id=-10012345678,
            text=f"""
**#Error:**
fnc: {fnc}

**Error: {error_message}**""",
            reply_to_message_id=17929
        )
    except Exception as e:
        print(f"Failed to report error: {e}")

premium_users = []

async def is_user_verified(client, user_id):
    try:
        # Always return True if the user is in the premium_users list
        if user_id in premium_users:
            return True

        # Connect to the "FileToLink" database
        db = mongo_client["FileToLink"]
        
        # Set the timezone to "Asia/Kolkata" and get today's date in DD-MM-YYYY format
        ist = timezone("Asia/Kolkata")
        today = datetime.now(ist).strftime("%d-%m-%Y")
        
        # Select the collection for the current date (for daily credits)
        daily_collection = db[today]
        # Select the premium_credit collection
        premium_collection = db["premium_credit"]
        
        # Initialize daily_free with date if not exists (in daily collection)
        daily_collection.update_one(
            {"name": "daily_free"},
            {
                "$setOnInsert": {
                    "users": [],
                    "date": today  # Added date field
                }
            },
            upsert=True
        )
        
        # Initialize temp_credits if not exists (in daily collection)
        daily_collection.update_one(
            {"name": "temp_credits", "date": today},
            {"$setOnInsert": {"user_credits": {}}},
            upsert=True
        )
        
        # Initialize premium_credit if not exists (in premium_credit collection)
        premium_collection.update_one(
            {"name": "premium_credit"},
            {"$setOnInsert": {"users": {}}},
            upsert=True
        )
        
        # Check if user is in daily_free document
        daily_free_user = daily_collection.find_one({
            "name": "daily_free",
            "users": {"$in": [user_id]}
        })
        
        if daily_free_user is None:
            # User not in daily_free, add them to daily_free
            daily_collection.update_one(
                {"name": "daily_free"},
                {"$push": {"users": user_id}}
            )
            
            # Give them 5 temp credits
            daily_collection.update_one(
                {"name": "temp_credits", "date": today},
                {
                    "$inc": {f"user_credits.{user_id}": 5},
                    "$set": {"date": today}
                },
                upsert=True
            )
            return True  # New user gets access
        
        # If user is in daily_free, check their credits
        # Check temp_credits in daily collection
        temp_credits_doc = daily_collection.find_one({
            "name": "temp_credits",
            "date": today,
            f"user_credits.{user_id}": {"$exists": True, "$gt": 0}
        })
        
        # Check premium_credit in premium_credit collection
        premium_credit_doc = premium_collection.find_one({
            "name": "premium_credit",
            f"users.{user_id}": {"$exists": True, "$gt": 0}
        })
        
        # Return True if user has credits in either temp_credits or premium_credit
        return temp_credits_doc is not None or premium_credit_doc is not None

    except Exception as e:
        # Log and report any errors
        fnc = "utils.is_user_verified"
        await report_error(client, e, fnc)
        print(f"Error checking user verification status: {e}")
        return False
