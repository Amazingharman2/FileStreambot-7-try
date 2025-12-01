import asyncio
from FileStream.bot import FileStream, multi_clients
from FileStream.utils.bot_utils import is_user_banned, is_user_exist, is_user_joined, gen_link, is_channel_banned, is_channel_exist, is_user_authorized
from FileStream.utils.database import Database
from FileStream.utils.translation import LANG, BUTTON
from FileStream.utils.file_properties import get_file_ids, get_file_info
from FileStream.config import Telegram, verification
from pyrogram import filters, Client
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums.parse_mode import ParseMode
db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)

# NOTE: Assuming this import path and function signature for edit_credit
from verify import is_user_verified
from helpers.credit_manager import edit_credit
import time
import asyncio


@FileStream.on_message(filters.command("add_prem") & filters.private)
async def add_premium_user_command(bot: Client, message: Message):
    if message.from_user.id != Telegram.OWNER_ID:
        return await message.reply_text("You are not authorized to use this command.")

    try:
        user_id_to_add = int(message.text.split(" ", 1)[1])
    except (IndexError, ValueError):
        return await message.reply_text("<b>Usage:</b> /add_prem <i>&lt;user_id&gt;</i>")

    await db.add_premium_user(user_id_to_add)
    await message.reply_text(f"Successfully added user `{user_id_to_add}` to the premium list.")


@FileStream.on_message(
    filters.private
    & (
        filters.document
        | filters.video
        | filters.video_note
        | filters.audio
        | filters.voice
        | filters.animation
        | filters.photo
    ),
    group=4,
)
async def private_receive_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    
    try:
        await bot.get_chat_member(Telegram.FORCE_SUB_ID, user_id)
    except UserNotParticipant:
        return await message.reply(
            LANG.Fsub_text.format(Telegram.UPDATES_CHANNEL, Telegram.UPDATES_CHANNEL_LINK),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🍀join 🍀", url=Telegram.FORCE_SUB_LINK)]])
        )

    
    if not await is_user_authorized(message):
        return
    if await is_user_banned(message):
        return

    
    try:
        client = bot
        if not await is_user_verified(client, message.from_user.id) and verification.verfication == True:
            btn = [[
                InlineKeyboardButton("🪙 Free Credits 🪙", url="https://t.me/Bots_Access_Manager_l_Bot?start=FITLETOLINK")
            ],
            [
                InlineKeyboardButton("🤑 Buy Credits 🤑", url="https://t.me/Appuz_007")
            ]]
            await message.reply_text(
                text=LANG.v_text,
                protect_content=True,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return

        file_data = get_file_info(message)

        # Deduct 1 credit per file upload
        res = await edit_credit(message.from_user.id, "deduct", 1)
        
        inserted_id = None

        if res == "T":
            inserted_id = await db.add_file(file_data, temp=True)
            print("Deducted from temp credits")
        elif res == "P":
            inserted_id = await db.add_file(file_data, temp=False)
            print("Deducted from premium credits")
        elif res is False:
            print("Deduction failed")
            return

        
        await get_file_ids(False, inserted_id, multi_clients, message)
        reply_markup, stream_text = await gen_link(_id=inserted_id)

        reply_markup_list = list(reply_markup.inline_keyboard)

        # Add the new button if 'res' is "T"
        if res == "T":
            stream_text += "\n\n ⚠️ ʟɪɴᴋ ᴡɪʟʟ ᴇxᴘɪʀᴇ ᴡɪᴛʜɪɴ 𝟤𝟦ʜʀꜱ, ᴜꜱᴇ ᴘʀᴇᴍɪᴜᴍ ᴄʀᴇᴅɪᴛꜱ ᴛᴏ ɢᴇᴛ ᴘᴇʀᴍᴀɴᴇɴᴛ ʟɪɴᴋꜱ!! 😊"
            
            callback_data = f"permanent_{inserted_id}"
            new_button = [InlineKeyboardButton("✨ Make Link Permanent ✨", callback_data=callback_data)]
            reply_markup_list.append(new_button)
            
            reply_markup = InlineKeyboardMarkup(reply_markup_list)

        await message.reply_text(
            text=stream_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True
        )
    
    except FloodWait as e:
        print(f"Sleeping for {str(e.value)}s")
        await asyncio.sleep(e.value)
        await bot.send_message(chat_id=Telegram.ULOG_CHANNEL,
                               text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.value)}s ғʀᴏᴍ [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n\n**ᴜsᴇʀ ɪᴅ :** `{str(message.from_user.id)}`",
                               disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)


@FileStream.on_callback_query(filters.regex(r"^permanent\_"))
async def make_link_permanent_handler(bot: Client, query: CallbackQuery):
    print("called me")
    user_id = query.from_user.id
    
    # Attempt to deduct 1 premium credit
    # NOTE: Assuming edit_credit supports a credit_type="P" argument for premium credits
    res = await edit_credit(user_id, "deduct", 1, credit_type="P")

    if res is False:
        await query.answer(
            "🚫 Insufficient Premium Credits! Send /credits to know more.",
            show_alert=True
        )
        return

    try:
        inserted_id = query.data.split("_", 1)[1]
    except IndexError:
        await query.answer("❌ Error: Missing file ID.", show_alert=True)
        return

    try:
        await db.make_file_permanent(inserted_id)
    except FIleNotFound:
        await query.answer("❌ Error: File not found in database.", show_alert=True)
        return
    except Exception as e:
        print(f"Error making file permanent: {e}")
        await query.answer("❌ An unexpected error occurred.", show_alert=True)
        return

    # Update message text to show link is permanent and remove the button
    new_text = query.message.text.replace(
        "⚠️ ʟɪɴᴋ ᴡɪʟʟ ᴇxᴘɪʀᴇ ᴡɪᴛʜɪɴ 𝟤𝟦ʜʀꜱ, ᴜꜱᴇ ᴘʀᴇᴍɪᴜᴍ ᴄʀᴇᴅɪᴛꜱ ᴛᴏ ɢᴇᴛ ᴘᴇʀᴍᴀɴᴇɴᴛ ʟɪɴᴋꜱ!! 😊",
        "✅ Link is now PERMANENT!"
    )
    
    # Filter out the 'Make Link Permanent' button
    new_reply_markup = [
        row for row in query.message.reply_markup.inline_keyboard
        if not (len(row) == 1 and row[0].callback_data and row[0].callback_data.startswith("permanent_"))
    ]
    
    try:
        await query.message.edit_text(
            text=new_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(new_reply_markup),
            disable_web_page_preview=True
        )
        await query.answer("✅ Your link is now permanent!")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await query.answer("✅ Your link is now permanent!")
    except Exception as e:
        print(f"Error editing message: {e}")
        await query.answer("✅ Your link is now permanent! (Could not edit message text)")


@FileStream.on_message(
    filters.channel
    & ~filters.forwarded
    & ~filters.media_group
    & (
            filters.document
            | filters.video
            | filters.video_note
            | filters.audio
            | filters.voice
            | filters.photo
    )
)
async def channel_receive_handler(bot: Client, message: Message):
    if await is_channel_banned(bot, message):
        return
    await is_channel_exist(bot, message)

    try:
        client = bot
        if not await is_user_verified(client, message.from_user.id) and Config.verfication == True:
            btn = [[
                InlineKeyboardButton("👨‍💻 ᴠᴇʀɪғʏ", url="https://t.me/Bots_Access_Manager_l_Bot?start=terabox")
            ],[
                InlineKeyboardButton("🔻 ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋ ᴀɴᴅ ᴠᴇʀɪғʏ 🔺", url=f"{Config.TECH_VJ_TUTORIAL}")
            ]]
            await message.reply_text(
                text=text,
                protect_content=True,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return

        inserted_id = await db.add_file(get_file_info(message))
        await get_file_ids(False, inserted_id, multi_clients, message)
        reply_markup, stream_link = await gen_link(_id=inserted_id)
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.id,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Dᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ 📥",
                                     url=f"https://t.me/{FileStream.username}?start=stream_{str(inserted_id)}")]])
        )

    except FloodWait as w:
        print(f"Sleeping for {str(w.x)}s")
        await asyncio.sleep(w.x)
        await bot.send_message(chat_id=Telegram.ULOG_CHANNEL,
                               text=f"ɢᴏᴛ ғʟᴏᴏᴅᴡᴀɪᴛ ᴏғ {str(w.x)}s ғʀᴏᴍ {message.chat.title}\n\n**ᴄʜᴀɴɴᴇʟ ɪᴅ :** `{str(message.chat.id)}`",
                               disable_web_page_preview=True)
    except Exception as e:
        await bot.send_message(chat_id=Telegram.ULOG_CHANNEL, text=f"**#EʀʀᴏʀTʀᴀᴄᴋᴇʙᴀᴄᴋ:** `{e}`",
                               disable_web_page_preview=True)
        print(f"Cᴀɴ'ᴛ Eᴅɪᴛ Bʀᴏᴀᴅᴄᴀsᴛ Mᴇssᴀɢᴇ!\nEʀʀᴏʀ:  **Gɪᴠᴇ ᴍᴇ ᴇᴅɪᴛ ᴘᴇʀᴍɪssɪᴏɴ ɪɴ ᴜᴘᴅᴀᴛᴇs ᴀɴᴅ ʙɪɴ Cʜᴀɴɴᴇʟ!{e}**")
