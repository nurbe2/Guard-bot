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
ADMIN_ID = 8306639956
DATA = "/tmp/guard_data.json"

if os.path.exists(DATA):
    with open(DATA) as f: data = json.load(f)
else:
    data = {
        "users": {},
        "warnings": {},
        "welcome": {},
        "bad_words": [
            "dnx", "am", "@m", "qotoq", "sholnax", "pshlnx", "pwlnx",
            "gandon", "g@andon", "oneni ami", "oneni ske", "oneni @mi",
            "jalab", "jaleb", "j@l@b", "j@lab", "suka", "ske"
        ]
    }

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

# ==================== MENYU ====================
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Guruh qo'shish"), KeyboardButton("📋 Guruhlarim")],
        [KeyboardButton("🗑 Guruh o'chirish"), KeyboardButton("⚙️ Sozlamalar")],
        [KeyboardButton("❓ Yordam")],
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Guruh qo'shish"), KeyboardButton("📋 Guruhlarim")],
        [KeyboardButton("🗑 Guruh o'chirish"), KeyboardButton("👑 Admin Panel")],
        [KeyboardButton("❓ Yordam")],
    ], resize_keyboard=True)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = update.effective_user.id
    groups = data["users"].get(str(uid), {})
    is_admin = uid == ADMIN_ID
    
    text = f"🛡️ <b>GURUH NAZORATCHI BOT</b>\n\n"
    text += f"👋 Salom, {update.effective_user.first_name}!\n\n"
    text += f"📋 Guruhlarim: {len(groups)} ta\n\n"
    text += f"<b>➕ Guruh qo'shish:</b> /add @username\n\n"
    text += f"<b>Guruhda ishlatish:</b>\n"
    text += f"/ban /unban /mute 1h /unmute /warn\n"
    text += f"/antispam on/off /antibad on/off\n"
    text += f"/setwelcome - Salomlashish\n"
    text += f"@admin - Admin chaqirish"
    
    kb = admin_menu() if is_admin else main_menu()
    await update.message.reply_text(text, reply_markup=kb, parse_mode='HTML')

# ==================== YANGI A'ZO SALOMLASHISH ====================
async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        
        # Welcome xabari
        welcome_text = data.get("welcome", {}).get(chat_id)
        if welcome_text:
            text = welcome_text.replace("{user}", f"<a href='tg://user?id={member.id}'>{member.first_name}</a>")
            text = text.replace("{chat}", update.effective_chat.title)
        else:
            text = f"👋 Assalomu alaykum <a href='tg://user?id={member.id}'>{member.first_name}</a>!\n<b>{update.effective_chat.title}</b> ga xush kelibsiz!"
        
        try:
            await update.message.reply_text(text, parse_mode='HTML')
        except:
            pass

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(
            "📝 <b>Salomlashish xabarini o'rnatish</b>\n\n"
            "<code>/setwelcome Xabar matni</code>\n\n"
            "<b>O'zgaruvchilar:</b>\n"
            "{user} - Foydalanuvchi nomi\n"
            "{chat} - Guruh nomi\n\n"
            "<b>Misol:</b>\n"
            "<code>/setwelcome Assalom {user}, {chat} ga xush kelibsiz!</code>",
            parse_mode='HTML'
        )
        return
    
    text = ' '.join(context.args)
    if "welcome" not in data:
        data["welcome"] = {}
    data["welcome"][chat_id] = text
    save()
    await update.message.reply_text("✅ Salomlashish xabari saqlandi!")

# ==================== XABAR TEKSHIRISH ====================
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    msg = update.message
    text = (msg.text or msg.caption or "").lower()
    
    if not text:
        return
    
    # Guruh sozlamalarini topish
    group_settings = None
    group_owner = None
    for uid, groups in data["users"].items():
        if chat_id in groups:
            group_owner = uid
            group_settings = groups[chat_id]
            break
    
    if not group_settings:
        return
    
    # @admin chaqirish
    if "@admin" in text or "/admin" in text:
        if group_owner:
            try:
                await msg.forward(int(group_owner))
                await msg.reply_text(f"✅ Admin chaqirildi!", parse_mode='HTML')
            except:
                pass
        return
    
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    should_delete = False
    reason = ""
    
    # Anti-spam (link)
    if group_settings.get("anti_spam", True):
        spam_words = ['http', 'https', '.com', '.uz', '.ru', '.net', '.org', 't.me/', 'telegram.me']
        if any(word in text for word in spam_words):
            should_delete = True
            reason = "reklama"
    
    # Anti-bad words
    if group_settings.get("anti_bad", True):
        for word in data.get("bad_words", []):
            if word.lower() in text:
                should_delete = True
                reason = "haqoratli so'z"
                break
    
    if should_delete:
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
                warn_msg = f"⚠️ {mention} <b>iltimos {reason} qilmang!</b>\nOgohlantirish: {warn_count}/{warn_limit}"
                sent = await context.bot.send_message(chat_id, warn_msg, parse_mode='HTML')
                await asyncio.sleep(5)
                try:
                    await sent.delete()
                except:
                    pass
        except:
            pass

# ==================== GURUH QO'SHISH ====================
async def add_group_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "➕ <code>/add @guruh_username</code>\nyoki\n<code>/add -100123456</code>\n\n⚠️ Siz guruhda admin bo'lishingiz kerak!",
            parse_mode='HTML'
        )
        return
    
    group_id = context.args[0]
    
    try:
        chat = await context.bot.get_chat(group_id)
        
        # Foydalanuvchi adminmi?
        user_member = await chat.get_member(update.effective_user.id)
        if user_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(f"❌ Siz <b>{chat.title}</b> da admin emassiz!", parse_mode='HTML')
            return
        
        # Bot adminmi?
        try:
            bot_member = await chat.get_member(context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(f"❌ Bot <b>{chat.title}</b> da admin emas!", parse_mode='HTML')
                return
        except:
            await update.message.reply_text("❌ Bot guruhda yo'q!")
            return
        
        if uid not in data["users"]:
            data["users"][uid] = {}
        
        if str(chat.id) in data["users"][uid]:
            await update.message.reply_text("⚠️ Bu guruh allaqachon qo'shilgan!")
            return
        
        data["users"][uid][str(chat.id)] = {
            "name": chat.title,
            "username": chat.username or "",
            "anti_spam": True,
            "anti_bad": True,
            "warn_limit": 3,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save()
        
        await update.message.reply_text(
            f"✅ <b>Guruh qo'shildi!</b>\n\n📢 {chat.title}\n🔒 Anti-spam: Yoqilgan\n🤬 Anti-haqorat: Yoqilgan\n⚠️ Limit: 3",
            parse_mode='HTML'
        )
    
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

async def add_group_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "➕ <code>/add @guruh_username</code>\nyoki\n<code>/add -100123456</code>",
        parse_mode='HTML'
    )

# ==================== GURUHLARIM / O'CHIRISH ====================
async def my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    groups = data["users"].get(uid, {})
    
    if not groups:
        await update.message.reply_text("📭 Guruhlar yo'q!")
        return
    
    text = "📋 <b>Guruhlarim:</b>\n\n"
    for gid, g in groups.items():
        text += f"📢 {g['name']}\n🆔 <code>{gid}</code>\n🔒 Spam: {'✅' if g.get('anti_spam',True) else '❌'} | 🤬 Bad: {'✅' if g.get('anti_bad',True) else '❌'}\n\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    groups = data["users"].get(uid, {})
    
    if not groups:
        await update.message.reply_text("📭 Guruhlar yo'q!")
        return
    
    kb = [[InlineKeyboardButton(f"🗑 {g['name'][:30]}", callback_data=f"delgroup_{gid}")] for gid, g in groups.items()]
    await update.message.reply_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

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

# ==================== BUYRUQLAR ====================
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply qiling!"); return
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🚫 <b>{user.first_name}</b> bloklandi!", parse_mode='HTML')
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /unban @username yoki /unban ID"); return
    try:
        target = context.args[0].replace("@", "")
        await context.bot.unban_chat_member(update.effective_chat.id, target)
        await update.message.reply_text(f"✅ <b>{target}</b> blokdan chiqarildi!", parse_mode='HTML')
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply qiling! Masalan: /mute 1h"); return
    
    user = update.message.reply_to_message.from_user
    args = context.args
    
    try:
        if args:
            time_str = args[0].lower()
            if time_str.endswith('h'):
                until = datetime.now() + timedelta(hours=int(time_str.replace('h','')))
                time_text = time_str.replace('h',' soatga')
            elif time_str.endswith('m'):
                until = datetime.now() + timedelta(minutes=int(time_str.replace('m','')))
                time_text = time_str.replace('m',' daqiqaga')
            else:
                until = datetime.now() + timedelta(hours=int(time_str))
                time_text = f"{time_str} soatga"
            
            await context.bot.restrict_chat_member(
                update.effective_chat.id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
        else:
            await context.bot.restrict_chat_member(
                update.effective_chat.id, user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            time_text = "butunlay"
        
        await update.message.reply_text(f"🔇 <b>{user.first_name}</b> {time_text} yoza olmaydi!", parse_mode='HTML')
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply qiling!"); return
    
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        )
        await update.message.reply_text(f"🔊 <b>{user.first_name}</b> yana yoza oladi!", parse_mode='HTML')
    except:
        await update.message.reply_text("❌ Bot admin bo'lishi kerak!")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply qiling!"); return
    
    user = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    uid = str(user.id)
    
    if uid not in data["warnings"]: data["warnings"][uid] = {}
    if chat_id not in data["warnings"][uid]: data["warnings"][uid][chat_id] = 0
    
    data["warnings"][uid][chat_id] += 1
    save()
    
    warn_count = data["warnings"][uid][chat_id]
    warn_limit = 3
    for groups in data["users"].values():
        if chat_id in groups:
            warn_limit = groups[chat_id].get("warn_limit", 3)
            break
    
    await update.message.reply_text(f"⚠️ <b>{user.first_name}</b> ogohlantirildi! {warn_count}/{warn_limit}", parse_mode='HTML')
    
    if warn_count >= warn_limit:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"🚫 <b>{user.first_name}</b> bloklandi!", parse_mode='HTML')
        except: pass

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    for groups in data["users"].values():
        if chat_id in groups:
            g = groups[chat_id]
            await update.message.reply_text(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"🔒 Anti-spam: {'✅' if g.get('anti_spam',True) else '❌'}\n"
                f"🤬 Anti-haqorat: {'✅' if g.get('anti_bad',True) else '❌'}\n"
                f"⚠️ Limit: {g.get('warn_limit',3)}\n\n"
                f"/antispam on/off\n"
                f"/antibad on/off\n"
                f"/warnlimit 5\n"
                f"/setwelcome Xabar",
                parse_mode='HTML'
            )
            return
    
    await update.message.reply_text("❌ Guruh sozlanmagan!")

async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text("❌ /antispam on yoki off"); return
    
    action = context.args[0].lower()
    for groups in data["users"].values():
        if chat_id in groups:
            groups[chat_id]["anti_spam"] = (action == "on")
            save()
            await update.message.reply_text(f"✅ Anti-spam: {action}")
            return

async def antibad_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text("❌ /antibad on yoki off"); return
    
    action = context.args[0].lower()
    for groups in data["users"].values():
        if chat_id in groups:
            groups[chat_id]["anti_bad"] = (action == "on")
            save()
            await update.message.reply_text(f"✅ Anti-haqorat: {action}")
            return

async def warnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text("❌ /warnlimit 5"); return
    
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

# ==================== ADMIN PANEL ====================
async def admin_panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return
    
    total_users = len(data["users"])
    total_groups = sum(len(g) for g in data["users"].values())
    total_warns = sum(len(w) for w in data.get("warnings", {}).values())
    
    await update.message.reply_text(
        f"👑 <b>ADMIN PANEL</b>\n\n"
        f"👥 Foydalanuvchilar: {total_users}\n"
        f"📢 Guruhlar: {total_groups}\n"
        f"⚠️ Ogohlantirishlar: {total_warns}\n"
        f"🔒 Anti-spam: Faol\n"
        f"🤬 Anti-haqorat: Faol\n"
        f"📋 Taqiqlangan so'zlar: {len(data.get('bad_words', []))} ta",
        parse_mode='HTML'
    )

# ==================== HANDLE TEXT ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    txt = update.message.text.strip()
    uid = update.effective_user.id
    is_admin = uid == ADMIN_ID
    
    if txt == "➕ Guruh qo'shish":
        await add_group_button(update, context)
    elif txt == "📋 Guruhlarim":
        await my_groups(update, context)
    elif txt == "🗑 Guruh o'chirish":
        await delete_group(update, context)
    elif txt == "👑 Admin Panel" and is_admin:
        await admin_panel_cmd(update, context)
    elif txt == "⚙️ Sozlamalar":
        await update.message.reply_text("Guruhda /settings yozing")
    elif txt == "❓ Yordam":
        await update.message.reply_text(
            "🛡️ <b>Buyruqlar:</b>\n\n"
            "/add @guruh - Guruh qo'shish\n"
            "/ban - Bloklash (reply)\n"
            "/unban @user - Blokdan chiqarish\n"
            "/mute 1h - Mute qilish\n"
            "/unmute - Mutedan chiqarish\n"
            "/warn - Ogohlantirish\n"
            "/antispam on/off - Reklama bloklash\n"
            "/antibad on/off - Haqorat bloklash\n"
            "/setwelcome - Salomlashish\n"
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
    application.add_handler(CommandHandler("antibad", antibad_cmd))
    application.add_handler(CommandHandler("warnlimit", warnlimit_cmd))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("adminpanel", admin_panel_cmd))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(delete_group_callback, pattern="^delgroup_"))
    
    print("✅ Global Guruh Nazoratchi Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
