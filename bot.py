import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread

app = Flask(__name__)
@app.route('/')
def home(): return "🛡️ Guard Bot"
@app.route('/ping')
def ping(): return "PONG"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8017075505:AAEe9VAGo2BQDPUUlqUaSgTmHcELOjQFMEo')
DATA = "/tmp/guard_data.json"

if os.path.exists(DATA):
    with open(DATA) as f: data = json.load(f)
else:
    data = {"users": {}, "warnings": {}}

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

SPAM_WORDS = ['http', 'https', '.com', '.uz', '.ru', '.net', '.org', 't.me/', 'telegram.me']

# ==================== MENYU ====================
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Guruh qo'shish"), KeyboardButton("📋 Guruhlarim")],
        [KeyboardButton("🗑 Guruh o'chirish"), KeyboardButton("⚙️ Sozlamalar")],
        [KeyboardButton("❓ Yordam")],
    ], resize_keyboard=True)

def group_menu(chat_id):
    group = data["users"].get(str(chat_id), {})
    anti = "✅" if group.get("anti_spam", True) else "❌"
    return f"⚙️ <b>Sozlamalar</b>\n\n🔒 Anti-spam: {anti}\n⚠️ Limit: {group.get('warn_limit', 3)}\n\n/antispam on/off\n/warnlimit 5"

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = str(update.effective_user.id)
    groups = data["users"].get(uid, {})
    
    text = f"🛡️ <b>GURUH NAZORATCHI BOT</b>\n\n"
    text += f"👋 Salom, {update.effective_user.first_name}!\n\n"
    text += f"📋 Guruhlarim: {len(groups)} ta\n\n"
    text += f"<b>Guruh qo'shish:</b>\n➕ Guruh qo'shish tugmasini bosing\n"
    text += f"yoki /add @username yozing\n\n"
    text += f"<b>Guruhda ishlatish:</b>\n"
    text += f"/ban /unban /mute 1h /unmute /warn\n"
    text += f"/antispam on/off /warnlimit 5\n"
    text += f"@admin - admin chaqirish"
    
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode='HTML')

# ==================== GURUH QO'SHISH ====================
async def add_group_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "➕ <b>Guruh qo'shish</b>\n\n"
            "<code>/add @guruh_username</code>\n"
            "yoki\n"
            "<code>/add -100123456</code>\n\n"
            "⚠️ Siz guruhda admin bo'lishingiz kerak!",
            parse_mode='HTML'
        )
        return
    
    group_id = context.args[0]
    
    try:
        chat = await context.bot.get_chat(group_id)
        
        # Foydalanuvchi adminligini tekshirish
        user_member = await chat.get_member(update.effective_user.id)
        if user_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                f"❌ Siz <b>{chat.title}</b> guruhida admin emassiz!\n\n"
                f"Faqat adminlar botni sozlashi mumkin.",
                parse_mode='HTML'
            )
            return
        
        # Bot adminligini tekshirish
        try:
            bot_member = await chat.get_member(context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    f"❌ Bot <b>{chat.title}</b> guruhida admin emas!\n\n"
                    f"Avval botni guruhga admin qiling.",
                    parse_mode='HTML'
                )
                return
        except:
            await update.message.reply_text("❌ Bot guruhda yo'q! Avval qo'shing.")
            return
        
        # Guruh qo'shish
        if uid not in data["users"]:
            data["users"][uid] = {}
        
        if str(chat.id) in data["users"][uid]:
            await update.message.reply_text("⚠️ Bu guruh allaqachon qo'shilgan!")
            return
        
        data["users"][uid][str(chat.id)] = {
            "name": chat.title,
            "username": chat.username or "",
            "anti_spam": True,
            "warn_limit": 3,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save()
        
        await update.message.reply_text(
            f"✅ <b>Guruh qo'shildi!</b>\n\n"
            f"📢 {chat.title}\n"
            f"🆔 <code>{chat.id}</code>\n"
            f"🔒 Anti-spam: Yoqilgan\n"
            f"⚠️ Ogohlantirish limiti: 3\n\n"
            f"<i>Sozlamalarni o'zgartirish uchun guruhda /settings yozing</i>",
            parse_mode='HTML'
        )
    
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

async def add_group_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "➕ <b>Guruh qo'shish</b>\n\n"
        "<code>/add @guruh_username</code>\n"
        "yoki\n"
        "<code>/add -100123456</code>\n\n"
        "⚠️ Siz guruhda admin bo'lishingiz kerak!",
        parse_mode='HTML'
    )

# ==================== GURUHLARIM ====================
async def my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    groups = data["users"].get(uid, {})
    
    if not groups:
        await update.message.reply_text("📭 Guruhlar yo'q! /add @guruh yozing.")
        return
    
    text = "📋 <b>Guruhlarim:</b>\n\n"
    for gid, g in groups.items():
        anti = "✅" if g.get("anti_spam", True) else "❌"
        text += f"📢 {g['name']}\n"
        text += f"🆔 <code>{gid}</code>\n"
        text += f"🔒 Anti-spam: {anti}\n\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ==================== GURUH O'CHIRISH ====================
async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    groups = data["users"].get(uid, {})
    
    if not groups:
        await update.message.reply_text("📭 Guruhlar yo'q!")
        return
    
    kb = []
    for gid, g in groups.items():
        kb.append([InlineKeyboardButton(f"🗑 {g['name'][:30]}", callback_data=f"delgroup_{gid}")])
    
    await update.message.reply_text(
        "🗑 <b>O'chirish uchun guruhni tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def delete_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    uid = str(q.from_user.id)
    gid = q.data.replace("delgroup_", "")
    
    if uid in data["users"] and gid in data["users"][uid]:
        name = data["users"][uid][gid]["name"]
        del data["users"][uid][gid]
        save()
        await q.edit_message_text(f"✅ {name} o'chirildi!")
    else:
        await q.answer("❌ Xatolik!")

# ==================== REKLAMA TEKSHIRISH ====================
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    msg = update.message
    text = msg.text or msg.caption or ""
    
    if not text:
        return
    
    # Guruh kimga tegishli ekanligini topish
    group_owner = None
    group_settings = None
    for uid, groups in data["users"].items():
        if chat_id in groups:
            group_owner = uid
            group_settings = groups[chat_id]
            break
    
    if not group_settings:
        return
    
    # @admin chaqirish
    if "@admin" in text.lower() or "/admin" in text.lower():
        if group_owner:
            try:
                await msg.forward(int(group_owner))
                await msg.reply_text(
                    f"✅ <b>Admin chaqirildi!</b>\n"
                    f"👤 {user.first_name} sizni chaqirmoqda!",
                    parse_mode='HTML'
                )
            except:
                pass
        return
    
    # Anti-spam
    if group_settings.get("anti_spam", True):
        has_spam = any(word in text.lower() for word in SPAM_WORDS)
        
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
                warn_limit = group_settings.get("warn_limit", 3)
                
                if warn_count >= warn_limit:
                    try:
                        await context.bot.ban_chat_member(chat_id, user.id)
                        await context.bot.send_message(
                            chat_id,
                            f"🚫 {mention} <b>bloklandi!</b> ({warn_count} ogohlantirish)",
                            parse_mode='HTML'
                        )
                    except:
                        pass
                else:
                    sent = await context.bot.send_message(
                        chat_id,
                        f"⚠️ {mention} <b>iltimos reklama qilmang!</b>\n"
                        f"Ogohlantirish: {warn_count}/{warn_limit}",
                        parse_mode='HTML'
                    )
                    await asyncio.sleep(5)
                    try:
                        await sent.delete()
                    except:
                        pass
            except:
                pass

# ==================== BUYRUQLAR ====================
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Foydalanuvchi xabariga reply qiling!")
        return
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, user.id)
        await update.message.reply_text(f"🚫 <b>{user.first_name}</b> bloklandi!", parse_mode='HTML')
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /unban @username yoki /unban ID")
        return
    
    chat_id = update.effective_chat.id
    
    try:
        target = context.args[0]
        if target.startswith("@"):
            target = target[1:]
        
        await context.bot.unban_chat_member(chat_id, target)
        await update.message.reply_text(f"✅ <b>{target}</b> blokdan chiqarildi!", parse_mode='HTML')
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
                until = datetime.now() + timedelta(hours=int(time_str.replace('h', '')))
                time_text = time_str.replace('h', ' soatga')
            elif time_str.endswith('m'):
                until = datetime.now() + timedelta(minutes=int(time_str.replace('m', '')))
                time_text = time_str.replace('m', ' daqiqaga')
            elif time_str.endswith('d'):
                until = datetime.now() + timedelta(days=int(time_str.replace('d', '')))
                time_text = time_str.replace('d', ' kunga')
            else:
                until = datetime.now() + timedelta(hours=int(time_str))
                time_text = f"{time_str} soatga"
            
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
        else:
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            time_text = "butunlay"
        
        await update.message.reply_text(f"🔇 <b>{user.first_name}</b> {time_text} yoza olmaydi!", parse_mode='HTML')
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
        await update.message.reply_text(f"🔊 <b>{user.first_name}</b> yana yoza oladi!", parse_mode='HTML')
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
    
    warn_count = data["warnings"][uid][chat_id]
    
    # Limitni topish
    warn_limit = 3
    for groups in data["users"].values():
        if chat_id in groups:
            warn_limit = groups[chat_id].get("warn_limit", 3)
            break
    
    await update.message.reply_text(
        f"⚠️ <b>{user.first_name}</b> ogohlantirildi!\nJami: {warn_count}/{warn_limit}",
        parse_mode='HTML'
    )
    
    if warn_count >= warn_limit:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"🚫 <b>{user.first_name}</b> bloklandi!", parse_mode='HTML')
        except:
            pass

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    for groups in data["users"].values():
        if chat_id in groups:
            g = groups[chat_id]
            anti = "✅" if g.get("anti_spam", True) else "❌"
            await update.message.reply_text(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"🔒 Anti-spam: {anti}\n"
                f"⚠️ Limit: {g.get('warn_limit', 3)}\n\n"
                f"/antispam on/off\n"
                f"/warnlimit 5",
                parse_mode='HTML'
            )
            return
    
    await update.message.reply_text("❌ Guruh sozlanmagan! Oldin /add qiling.")

async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text("❌ /antispam on yoki /antispam off")
        return
    
    action = context.args[0].lower()
    
    for groups in data["users"].values():
        if chat_id in groups:
            groups[chat_id]["anti_spam"] = (action == "on")
            save()
            await update.message.reply_text(f"✅ Anti-spam: {action}")
            return
    
    await update.message.reply_text("❌ Guruh sozlanmagan!")

async def warnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text("❌ /warnlimit 5")
        return
    
    try:
        limit = int(context.args[0])
        for groups in data["users"].values():
            if chat_id in groups:
                groups[chat_id]["warn_limit"] = limit
                save()
                await update.message.reply_text(f"✅ Limit: {limit}")
                return
    except:
        await update.message.reply_text("❌ Raqam kiriting!")

# ==================== HANDLE TEXT ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    txt = update.message.text.strip()
    
    if txt == "➕ Guruh qo'shish":
        await add_group_button(update, context)
    elif txt == "📋 Guruhlarim":
        await my_groups(update, context)
    elif txt == "🗑 Guruh o'chirish":
        await delete_group(update, context)
    elif txt == "⚙️ Sozlamalar":
        await update.message.reply_text(
            "⚙️ <b>Sozlamalar</b>\n\n"
            "Guruhda /settings yozing\n"
            "yoki /antispam on/off",
            parse_mode='HTML'
        )
    elif txt == "❓ Yordam":
        await update.message.reply_text(
            "❓ <b>Yordam</b>\n\n"
            "/add @guruh - Guruh qo'shish\n"
            "/ban - Bloklash (reply)\n"
            "/unban @user - Blokdan chiqarish\n"
            "/mute 1h - Mute qilish\n"
            "/unmute - Mutedan chiqarish\n"
            "/warn - Ogohlantirish\n"
            "/antispam on/off - Reklama bloklash\n"
            "@admin - Admin chaqirish",
            parse_mode='HTML'
        )

# ==================== MAIN ====================
def main():
    Thread(target=run_flask).start()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_group_cmd))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("settings", settings_cmd))
    application.add_handler(CommandHandler("antispam", antispam_cmd))
    application.add_handler(CommandHandler("warnlimit", warnlimit_cmd))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    application.add_handler(CallbackQueryHandler(delete_group_callback, pattern="^delgroup_"))
    
    print("✅ Global Guruh Nazoratchi Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
