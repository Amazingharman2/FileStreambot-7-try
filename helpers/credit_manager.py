from datetime import datetime
import pytz
from pymongo import MongoClient
from typing import Literal, Union

# Timezone setup
ist = pytz.timezone('Asia/Kolkata')

# MongoDB setup
MONGO_URI = "mongodb+srv://chrijismi:appussetten@cluster0.6mo9h.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["FileToLink"]

async def edit_credit(user_id: int, action: Literal["deduct", "credit"], unit: int, credit_type: Literal["T", "P", None] = None) -> Union[bool, str]:
    """
    Edit user credits in MongoDB
    :param user_id: Telegram user ID
    :param action: "deduct" or "credit"
    :param unit: Amount to deduct/credit
    :param credit_type: Optional: "T" for temp, "P" for premium. If None, uses default deduction logic (T then P).
    :return: "T" if deducted from temp, "P" if deducted from premium, True for credit success, False otherwise
    """
    today = datetime.now(ist).strftime("%d-%m-%Y")
    daily_collection = db[today]
    premium_collection = db["premium_credit"]
    
    try:
        # Initialize daily temp_credits if they don't exist
        daily_collection.update_one(
            {"name": "temp_credits", "date": today},
            {"$setOnInsert": {"name": "temp_credits", "date": today, "user_credits": {}}}, 
            upsert=True
        )
        
        # Initialize premium_credit if it doesn't exist
        premium_collection.update_one(
            {"name": "premium_credit"},
            {"$setOnInsert": {"name": "premium_credit", "users": {}}}, 
            upsert=True
        )

        if action == "credit":
            # Always add to premium credits
            result = premium_collection.update_one(
                {"name": "premium_credit"},
                {"$inc": {f"users.{user_id}": unit}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None

        elif action == "deduct":
            if credit_type == "P":
                # Deduct only from premium credits
                premium_credit_doc = premium_collection.find_one({"name": "premium_credit"})
                user_premium_credit = premium_credit_doc.get("users", {}).get(str(user_id), 0)

                if user_premium_credit >= unit:
                    result = premium_collection.update_one(
                        {"name": "premium_credit"},
                        {"$inc": {f"users.{user_id}": -unit}}
                    )
                    return "P" if result.modified_count > 0 else False
                else:
                    return False

            # Default logic (T then P) or if credit_type is "T"
            temp_credit_doc = daily_collection.find_one({"name": "temp_credits", "date": today})
            user_temp_credit = temp_credit_doc.get("user_credits", {}).get(str(user_id), 0)

            if user_temp_credit >= unit:
                # Deduct from temp credits
                result = daily_collection.update_one(
                    {"name": "temp_credits", "date": today},
                    {"$inc": {f"user_credits.{user_id}": -unit}}
                )
                return "T" if result.modified_count > 0 else False

            elif user_temp_credit > 0 and credit_type is None:
                # Partially deduct from temp credits and rest from premium (Only in default logic)
                remaining = unit - user_temp_credit
                with client.start_session() as session:
                    with session.start_transaction():
                        # Deduct remaining temp credits
                        daily_collection.update_one(
                            {"name": "temp_credits", "date": today},
                            {"$set": {f"user_credits.{user_id}": 0}},
                            session=session
                        )
                        # Deduct remaining from premium
                        premium_collection.update_one(
                            {"name": "premium_credit"},
                            {"$inc": {f"users.{user_id}": -remaining}},
                            session=session
                        )
                return "T"

            elif credit_type is None:
                # Deduct entirely from premium
                premium_credit_doc = premium_collection.find_one({"name": "premium_credit"})
                user_premium_credit = premium_credit_doc.get("users", {}).get(str(user_id), 0)

                if user_premium_credit >= unit:
                    result = premium_collection.update_one(
                        {"name": "premium_credit"},
                        {"$inc": {f"users.{user_id}": -unit}}
                    )
                    return "P" if result.modified_count > 0 else False
                else:
                    return False
            
            # If credit_type is "T" but no temp credit, return False
            return False

    except Exception as e:
        print(f"Error in edit_credit: {e}")
        return False
