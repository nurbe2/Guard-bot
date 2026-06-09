import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread

app = Flask(__name__)
@app.route('/')
def home(): return "OK"
@app.route('/ping')
def ping(): return "PONG"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8017075505:AAEe9VAGo2BQDPUUlqUaSgTmHcELOjQFMEo')
DATA = "/tmp/guard_data.json"

if os.path.exists(DATA):
    with open(DATA) as f: data = json.load(f)
else:
    data = {"groups": {}, "warnings": {}}

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

# Reklama so'zlari
SPAM_WORDS = ['http', 'https', '.com', '.uz', '.ru', '.net', '.org', 't.me/', 't.me/joinchat', 'telegram.me']

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    await update.message.reply_text(
        "🛡️ <b>GURUH NAZORATCHI BOT</b>\n\n"
        "👋 Salom! Men guruhingizni himoya qilaman!\n\n"
        "<b>Imkoniyatlar:</b>\n"
        "✅ Link/reklama bloklash\n"
        "✅ @admin chaqirish\n"
        "✅ /ban /mute /unmute /warn\n"
        "✅ Avto ogohlantirish\n\n"
        "<b>Guruhga qo'shish:</b>\n"
        "1. Botni guruhga admin qiling\n"
        "2. Guruhda /setup yozing\n\n"
        "<b>Buyruqlar (guruhda):</b>\n"
        "/setup - Sozlash\n"
        "/settings - Sozlamalarni ko'rish\n"
        "/admin - Admin chaqirish\n"
        "/ban - Bloklash (reply bilan)\n"
        "/mute 1h - Mute (1h/30m/2d)\n"
        "/unmute - Mutedan chiqarish\n"
        "/warn - Ogohlantirish\n"
        "/antispam on/off - Reklama bloklash",
        parse_mode='HTML'
    )

# ==================== GURUHGA QO'SHILGANDA ====================
async def new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            # Bot guruhga qo'shildi
            if chat_id not in data["groups"]:
                keyboard = [
                    [InlineKeyboardButton("✅ Ha", callback_data=f"setup_yes_{chat_id}"),
                     InlineKeyboardButton("❌ Yo'q", callback_data=f"setup_no_{chat_id}")]
                ]
                await update.message.reply_text(
                    "🛡️ <b>Guruh nazoratchisi ulandi!</b>\n\n"
                    "<b>Reklama va linklarni o'chirishim kerakmi?</b>",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )

# ==================== SETUP ====================
async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    keyboard = [
        [InlineKeyboardButton("✅ Ha", callback_data=f"setup_yes_{chat_id}"),
         InlineKeyboardButton("❌ Yo'q", callback_data=f"setup_no_{chat_id}")]
    ]
    await update.message.reply_text(
        "⚙️ <b>Sozlamalar</b>\n\n"
        "<b>Reklama va linklarni o'chirishim kerakmi?</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    parts = q.data.split("_")
    action = parts[1]
    chat_id = parts[2]
    
    if action == "yes":
        data["groups"][chat_id] = {
            "anti_spam": True,
            "added_by": q.from_user.id,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "warn_limit": 3
        }
        save()
        await q.edit_message_text(
            "✅ <b>Sozlandi!</b>\n\n"
            "🔒 Reklama va linklar o'chiriladi!\n"
            "⚠️ Ogohlantirish beriladi!\n"
            "🚫 3 marta ogohlantirilsa - ban!\n\n"
            "<b>Buyruqlar:</b>\n"
            "/settings - Sozlamalar\n"
            "/antispam on/off - Reklama bloklash",
            parse_mode='HTML'
        )
    
    elif action == "no":
        data["groups"][chat_id] = {
            "anti_spam": False,
            "added_by": q.from_user.id,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save()
        await q.edit_message_text(
            "✅ <b>Sozlandi!</b>\n\n"
            "Reklamalar o'chirilmaydi.\n"
            "Faqat buyruqlar ishlaydi!",
            parse_mode='HTML'
        )

# ==================== SOZLAMALAR ====================
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    group = data["groups"].get(chat_id)
    
    if not group:
        await update.message.reply_text("❌ Bot sozlanmagan! /setup yozing.")
        return
    
    anti_spam = "✅ Yoqilgan" if group.get("anti_spam") else "❌ O'chirilgan"
    warn_limit = group.get("warn_limit", 3)
    
    await update.message.reply_text(
        f"⚙️ <b>Guruh sozlamalari</b>\n\n"
        f"🔒 Reklama bloklash: {anti_spam}\n"
        f"⚠️ Ogohlantirish limiti: {warn_limit}\n\n"
        f"<b>O'zgartirish:</b>\n"
        f"/antispam on - Reklama bloklashni yoqish\n"
        f"/antispam off - Reklama bloklashni o'chirish\n"
        f"/warnlimit 5 - Ogohlantirish limiti",
        parse_mode='HTML'
    )

async def antispam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id not in data["groups"]:
        await update.message.reply_text("❌ Bot sozlanmagan! /setup yozing.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /antispam on yoki /antispam off")
        return
    
    action = context.args[0].lower()
    if action == "on":
        data["groups"][chat_id]["anti_spam"] = True
        save()
        await update.message.reply_text("✅ Reklama bloklash yoqildi!")
    elif action == "off":
        data["groups"][chat_id]["anti_spam"] = False
        save()
        await update.message.reply_text("❌ Reklama bloklash o'chirildi!")

async def warnlimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id not in data["groups"]:
        await update.message.reply_text("❌ Bot sozlanmagan!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /warnlimit 5")
        return
    
    try:
        limit = int(context.args[0])
        data["groups"][chat_id]["warn_limit"] = limit
        save()
        await update.message.reply_text(f"✅ Ogohlantirish limiti: {limit}")
    except:
        await update.message.reply_text("❌ Raqam kiriting!")

# ==================== REKLAMA TEKSHIRISH ====================
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    msg = update.message
    group = data["groups"].get(chat_id)
    
    if not group:
        return
    
    text = msg.text or msg.caption or ""
    if not text:
        return
    
    # @admin chaqirish
    if "@admin" in text.lower() or "/admin" in text.lower():
        owner_id = group.get("added_by")
        if owner_id:
            try:
                await msg.forward(owner_id)
                await msg.reply_text(
                    f"✅ <b>Admin chaqirildi!</b>\n"
                    f"👤 {user.first_name} sizni chaqirmoqda!",
                    parse_mode='HTML'
                )
            except:
                await msg.reply_text("❌ Admin hozircha javob bera olmaydi!")
        return
    
    # Anti-spam
    if group.get("anti_spam", False):
        has_spam = False
        for word in SPAM_WORDS:
            if word in text.lower():
                has_spam = True
                break
        
        if has_spam:
            try:
                await msg.delete()
                
                uid = str(user.id)
                if uid not in data["warnings"]:
                    data["warnings"][uid] = {}
                if chat_id not in data["warnings"][uid]:
                    data["warnings"][uid][chat_id] = 0
                
                data["warnings"][uid][chat_id] += 1
                warn_count = data["warnings"][uid][chat_id]
                save()
                
                mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
                warn_limit = group.get("warn_limit", 3)
                
                if warn_count >= warn_limit:
                    try:
                        await context.bot.ban_chat_member(chat_id, user.id)
                        await context.bot.send_message(
                            chat_id,
                            f"🚫 {mention} <b>bloklandi!</b>\n"
                            f"Sabab: Reklama ({warn_count} marta)",
                            parse_mode='HTML'
                        )
                    except:
                        pass
                else:
                    sent_msg = await context.bot.send_message(
                        chat_id,
                        f"⚠️ {mention} <b>iltimos reklama qilmang!</b>\n"
                        f"Ogohlantirish: {warn_count}/{warn_limit}\n\n"
                        f"<i>Bu xabar 5 soniyada o'chadi</i>",
                        parse_mode='HTML'
                    )
                    # Ogohlantirishni 5 soniyada o'chirish
                    await asyncio.sleep(5)
                    try:
                        await sent_msg.delete()
                    except:
                        pass
            except:
                pass

# ==================== BUYRUQLAR ====================
async def admin_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    group = data["groups"].get(chat_id)
    
    if not group:
        await update.message.reply_text("❌ Bot sozlanmagan!")
        return
    
    owner_id = group.get("added_by")
    if owner_id:
        try:
            await update.message.forward(owner_id)
            await update.message.reply_text("✅ Admin chaqirildi!")
        except:
            await update.message.reply_text("❌ Admin hozircha mavjud emas!")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Foydalanuvchi xabariga reply qiling!")
        return
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, user.id)
        await update.message.reply_text(
            f"🚫 <b>{user.first_name}</b> bloklandi!",
            parse_mode='HTML'
        )
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Xabarga reply qiling! Masalan: /mute 1h")
        return
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    args = context.args
    
    try:
        if args:
            time_str = args[0].lower()
            if time_str.endswith('h'):
                hours = int(time_str.replace('h', ''))
                until = datetime.now() + timedelta(hours=hours)
                time_text = f"{hours} soatga"
            elif time_str.endswith('m'):
                minutes = int(time_str.replace('m', ''))
                until = datetime.now() + timedelta(minutes=minutes)
                time_text = f"{minutes} daqiqaga"
            elif time_str.endswith('d'):
                days = int(time_str.replace('d', ''))
                until = datetime.now() + timedelta(days=days)
                time_text = f"{days} kunga"
            else:
                hours = int(time_str)
                until = datetime.now() + timedelta(hours=hours)
                time_text = f"{hours} soatga"
            
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await update.message.reply_text(
                f"🔇 <b>{user.first_name}</b> {time_text} yoza olmaydi!",
                parse_mode='HTML'
            )
        else:
            # Butunlay mute
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await update.message.reply_text(
                f"🔇 <b>{user.first_name}</b> butunlay yoza olmaydi!\n/unmute bilan ochiladi",
                parse_mode='HTML'
            )
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Xabarga reply qiling!")
        return
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.restrict_chat_member(
            chat_id, user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True
            )
        )
        await update.message.reply_text(
            f"🔊 <b>{user.first_name}</b> yana yoza oladi!",
            parse_mode='HTML'
        )
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Xabarga reply qiling!")
        return
    
    user = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    uid = str(user.id)
    
    if uid not in data["warnings"]:
        data["warnings"][uid] = {}
    if chat_id not in data["warnings"][uid]:
        data["warnings"][uid][chat_id] = 0
    
    data["warnings"][uid][chat_id] += 1
    save()
    
    group = data["groups"].get(chat_id, {})
    warn_count = data["warnings"][uid][chat_id]
    warn_limit = group.get("warn_limit", 3)
    
    await update.message.reply_text(
        f"⚠️ <b>{user.first_name}</b> ogohlantirildi!\n"
        f"Jami: {warn_count}/{warn_limit}",
        parse_mode='HTML'
    )
    
    if warn_count >= warn_limit:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(
                f"🚫 <b>{user.first_name}</b> bloklandi! ({warn_count} ogohlantirish)",
                parse_mode='HTML'
            )
        except:
            pass

# ==================== MAIN ====================
import asyncio

def main():
    Thread(target=run_flask).start()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("antispam", antispam_command))
    application.add_handler(CommandHandler("warnlimit", warnlimit_command))
    application.add_handler(CommandHandler("admin", admin_call))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("warn", warn_user))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    application.add_handler(CallbackQueryHandler(setup_callback, pattern="^setup_"))
    
    print("✅ Guruh Nazoratchi Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
