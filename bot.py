import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread

app = Flask(__name__)
@app.route('/')
def home(): return "Xentor Maker"
@app.route('/ping')
def ping(): return "PONG"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8922646707:AAHhq7K2Krvu7EKDJ1vOdiid8dUUyD6X2KQ')
ADMIN_ID = 8306639956
CHANNEL = '@xentormaker'
DATA = "/tmp/maker_data.json"

if os.path.exists(DATA):
    with open(DATA) as f: data = json.load(f)
else:
    data = {
        "users": {},
        "bots": {},
        "promocodes": {},
        "daily_bonus": {}
    }

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

# Conversation states
BOT_API, BOT_PRO_PRICE = range(2)

def main_menu(uid):
    balance = data["users"].get(str(uid), {}).get("balance", 0)
    kb = [
        [KeyboardButton("🤖 Bot qo'shish")],
        [KeyboardButton("👛 Hisobim"), KeyboardButton("💰 Pul ishlash")],
        [KeyboardButton("📋 Botlarim"), KeyboardButton("❓ Yordam")],
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ==================== START ====================
async def check_sub(uid, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, uid)
        return member.status not in ['left', 'kicked']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = update.effective_user.id
    name = update.effective_user.first_name
    
    if str(uid) not in data["users"]:
        data["users"][str(uid)] = {"name": name, "balance": 0, "bots": {}, "joined": datetime.now().strftime("%Y-%m-%d")}
        save()
    
    if not await check_sub(uid, context):
        kb = [[InlineKeyboardButton("📢 Obuna bo'lish", url=f"https://t.me/{CHANNEL[1:]}")],
              [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]]
        await update.message.reply_text(
            f"👋 Salom, {name}!\n\n📢 Botdan foydalanish uchun {CHANNEL} ga obuna bo'ling!",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    
    balance = data["users"][str(uid)].get("balance", 0)
    bots_count = len(data["users"][str(uid)].get("bots", {}))
    
    await update.message.reply_text(
        f"🤖 <b>XENTOR MAKER BOT</b>\n\n"
        f"👋 Xush kelibsiz, {name}!\n\n"
        f"👛 Balans: {balance} so'm\n"
        f"🤖 Botlarim: {bots_count} ta\n\n"
        f"Bugun nima qilamiz? 😊",
        reply_markup=main_menu(uid),
        parse_mode='HTML'
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if await check_sub(q.from_user.id, context):
        await q.delete_message()
        await start(update, context)
    else:
        await q.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)

# ==================== BOT QO'SHISH ====================
async def add_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🎬 Kino Bot Pro - 0 so'm (1/1)", callback_data="bot_type_kino")]]
    await update.message.reply_text(
        "🤖 <b>Qaysi bot turini tanlaysiz?</b>",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def bot_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    context.user_data['bot_type'] = 'kino'
    await q.edit_message_text(
        "🔑 <b>Bot API Tokenini yuboring:</b>\n\n"
        "<i>@BotFather dan olingan tokenni yuboring</i>",
        parse_mode='HTML'
    )
    return BOT_API

async def bot_api_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    
    # Tokenni tekshirish
    try:
        test_bot = Application.builder().token(token).build()
        bot_info = await test_bot.bot.get_me()
        
        context.user_data['bot_token'] = token
        context.user_data['bot_name'] = bot_info.first_name
        context.user_data['bot_username'] = bot_info.username
        
        await update.message.reply_text(
            f"✅ Bot topildi: @{bot_info.username}\n\n"
            f"💰 <b>PRO narxini kiriting (so'm):</b>\n"
            f"<i>Masalan: 14000</i>",
            parse_mode='HTML'
        )
        return BOT_PRO_PRICE
        
    except Exception as e:
        await update.message.reply_text(f"❌ Noto'g'ri token! Qaytadan yuboring.")
        return BOT_API

async def bot_pro_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pro_price = int(update.message.text.strip())
        uid = str(update.effective_user.id)
        
        bot_data = {
            "token": context.user_data['bot_token'],
            "name": context.user_data['bot_name'],
            "username": context.user_data['bot_username'],
            "pro_price": pro_price,
            "owner": uid,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": context.user_data['bot_type'],
            "movies": {},
            "pro_users": [],
            "payments": []
        }
        
        data.setdefault("bots", {})[context.user_data['bot_username']] = bot_data
        data["users"][uid].setdefault("bots", {})[context.user_data['bot_username']] = bot_data
        save()
        
        await update.message.reply_text(
            f"🎉 <b>Bot yaratildi!</b>\n\n"
            f"🤖 Nomi: {context.user_data['bot_name']}\n"
            f"🔗 @{context.user_data['bot_username']}\n"
            f"💰 PRO narxi: {pro_price} so'm\n\n"
            f"<b>Keyingi qadamlar:</b>\n"
            f"1. Botni guruhingizga admin qiling\n"
            f"2. /start bosib ishlatishni boshlang\n"
            f"3. Kino qo'shish uchun /admin",
            parse_mode='HTML'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except:
        await update.message.reply_text("❌ Raqam kiriting!")
        return BOT_PRO_PRICE

# ==================== HISOBIM ====================
async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    balance = data["users"].get(uid, {}).get("balance", 0)
    bots = data["users"].get(uid, {}).get("bots", {})
    
    await update.message.reply_text(
        f"👛 <b>Hisobim</b>\n\n"
        f"💰 Balans: {balance} so'm\n"
        f"🤖 Botlar: {len(bots)} ta\n\n"
        f"<b>Pul to'ldirish:</b>\n"
        f"💳 4916 9903 1619 3280\n"
        f"📸 To'lov qilib chek yuboring!",
        parse_mode='HTML'
    )

# ==================== PUL ISHLASH ====================
async def earn_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    kb = [
        [InlineKeyboardButton("🎁 Kunlik bonus (20 so'm)", callback_data="daily_bonus")],
        [InlineKeyboardButton("🎟 Promokod kiritish", callback_data="promo_enter")],
    ]
    await update.message.reply_text(
        "💰 <b>Pul ishlash</b>\n\n"
        "🎁 Kunlik bonus: 20 so'm\n"
        "🎟 Promokod: maxsus kodlar",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def daily_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    uid = str(q.from_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if data.get("daily_bonus", {}).get(uid) == today:
        await q.answer("❌ Bugun allaqachon oldingiz!", show_alert=True)
        return
    
    data.setdefault("daily_bonus", {})[uid] = today
    data["users"][uid]["balance"] = data["users"][uid].get("balance", 0) + 20
    save()
    
    await q.edit_message_text(
        f"🎁 <b>Kunlik bonus!</b>\n\n"
        f"✅ +20 so'm qo'shildi!\n"
        f"💰 Yangi balans: {data['users'][uid]['balance']} so'm",
        parse_mode='HTML'
    )

async def promo_enter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    context.user_data['entering_promo'] = True
    await q.edit_message_text("🎟 <b>Promokodni kiriting:</b>", parse_mode='HTML')

# ==================== BOTLARIM ====================
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    bots = data["users"].get(uid, {}).get("bots", {})
    
    if not bots:
        await update.message.reply_text("📭 Hali bot yaratilmagan!")
        return
    
    text = "🤖 <b>Botlarim:</b>\n\n"
    for username, bot in bots.items():
        text += f"🤖 @{username}\n💰 PRO: {bot['pro_price']} so'm\n📅 {bot['created']}\n\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ==================== ADMIN PANEL ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    kb = [
        [InlineKeyboardButton("👥 Foydalanuvchi boshqarish", callback_data="admin_user")],
        [InlineKeyboardButton("🎟 Promokod nazorat", callback_data="admin_promo")],
        [InlineKeyboardButton("📢 Post tarqatish", callback_data="admin_post")],
    ]
    await update.message.reply_text("👑 <b>Admin Panel</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def admin_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID: return
    await q.answer()
    
    context.user_data['admin_action'] = 'user_id'
    await q.edit_message_text("👤 <b>Foydalanuvchi ID sini yuboring:</b>", parse_mode='HTML')

async def admin_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID: return
    await q.answer()
    
    context.user_data['admin_action'] = 'promo_name'
    await q.edit_message_text("🎟 <b>Promokod nomini kiriting:</b>", parse_mode='HTML')

# ==================== HANDLE TEXT ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    # Admin amallari
    if uid == ADMIN_ID and context.user_data.get('admin_action'):
        action = context.user_data['admin_action']
        
        if action == 'user_id':
            context.user_data['target_uid'] = txt
            context.user_data['admin_action'] = 'user_amount'
            await update.message.reply_text("💰 <b>Qancha pul qo'shmoqchisiz?</b>\nMin: 1 | Max: 100000000000", parse_mode='HTML')
        
        elif action == 'user_amount':
            try:
                amount = int(txt)
                target = context.user_data['target_uid']
                
                data.setdefault("users", {}).setdefault(target, {})
                data["users"][target]["balance"] = data["users"][target].get("balance", 0) + amount
                save()
                
                await update.message.reply_text(
                    f"✅ <b>Pul qo'shildi!</b>\n\n"
                    f"👤 ID: {target}\n"
                    f"💰 Miqdor: {amount} so'm\n"
                    f"💎 Yangi balans: {data['users'][target]['balance']} so'm",
                    parse_mode='HTML'
                )
                context.user_data['admin_action'] = None
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif action == 'promo_name':
            context.user_data['promo_name'] = txt
            context.user_data['admin_action'] = 'promo_reward'
            await update.message.reply_text("🎁 <b>Mukofot miqdori (so'm):</b>", parse_mode='HTML')
        
        elif action == 'promo_reward':
            try:
                reward = int(txt)
                context.user_data['promo_reward'] = reward
                context.user_data['admin_action'] = 'promo_limit'
                await update.message.reply_text("👥 <b>Necha kishi ishlata oladi?</b>", parse_mode='HTML')
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif action == 'promo_limit':
            try:
                limit = int(txt)
                promo_name = context.user_data['promo_name']
                reward = context.user_data['promo_reward']
                
                data.setdefault("promocodes", {})[promo_name] = {
                    "reward": reward,
                    "limit": limit,
                    "used_by": [],
                    "created_by": str(uid)
                }
                save()
                
                await update.message.reply_text(
                    f"✅ <b>Promokod yaratildi!</b>\n\n"
                    f"🎟 Kod: {promo_name}\n"
                    f"💰 Mukofot: {reward} so'm\n"
                    f"👥 Limit: {limit} kishi",
                    parse_mode='HTML'
                )
                context.user_data['admin_action'] = None
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif action == 'post_text':
            text = f"📢 <b>E'lon</b>\n\n{txt}"
            users = data.get("users", {})
            count = 0
            for uid in users:
                try:
                    await context.bot.send_message(int(uid), text, parse_mode='HTML')
                    count += 1
                except: pass
            await update.message.reply_text(f"✅ {count} kishiga yuborildi!")
            context.user_data['admin_action'] = None
        
        return
    
    # Foydalanuvchi amallari
    if txt == "🤖 Bot qo'shish":
        await add_bot_start(update, context)
    elif txt == "👛 Hisobim":
        await my_balance(update, context)
    elif txt == "💰 Pul ishlash":
        await earn_money(update, context)
    elif txt == "📋 Botlarim":
        await my_bots(update, context)
    elif txt == "👑 Admin Panel" and uid == ADMIN_ID:
        await admin_panel(update, context)
    elif txt == "❓ Yordam":
        await update.message.reply_text(
            "❓ <b>Yordam</b>\n\n"
            "🤖 Bot qo'shish - @BotFather dan token oling\n"
            "👛 Hisobim - Balans va to'lov\n"
            "💰 Pul ishlash - Bonus va promokod\n\n"
            "<b>Admin:</b> @aktived01",
            parse_mode='HTML'
        )
    
    # Promokod kiritish
    elif context.user_data.get('entering_promo'):
        promo = txt.upper()
        promo_data = data.get("promocodes", {}).get(promo)
        
        if not promo_data:
            await update.message.reply_text("❌ Bunday promokod mavjud emas!")
        elif str(uid) in promo_data.get("used_by", []):
            await update.message.reply_text("❌ Siz bu promokodni ishlatgansiz!")
        elif len(promo_data.get("used_by", [])) >= promo_data.get("limit", 1):
            await update.message.reply_text("❌ Limit to'lgan!")
        else:
            reward = promo_data["reward"]
            data["promocodes"][promo]["used_by"].append(str(uid))
            data["users"][str(uid)]["balance"] = data["users"][str(uid)].get("balance", 0) + reward
            save()
            await update.message.reply_text(
                f"🎉 <b>Promokod qabul qilindi!</b>\n\n"
                f"💰 +{reward} so'm\n"
                f"💎 Yangi balans: {data['users'][str(uid)]['balance']} so'm",
                parse_mode='HTML'
            )
        
        context.user_data['entering_promo'] = False
    
    # Chek rasmi (pul to'ldirish)
    elif context.user_data.get('buying_balance'):
        # Rasmni kutish kerak, bu yerda oddiy xabar
        pass

# ==================== CALLBACK ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    
    if d == "check_sub":
        await check_sub_callback(update, context)
    elif d == "bot_type_kino":
        context.user_data['bot_type'] = 'kino'
        await q.edit_message_text("🔑 <b>Bot API Tokenini yuboring:</b>\n\n<i>@BotFather dan olingan token</i>", parse_mode='HTML')
        return BOT_API
    elif d == "daily_bonus":
        await daily_bonus_callback(update, context)
    elif d == "promo_enter":
        await promo_enter_callback(update, context)
    elif d == "admin_user":
        await admin_user_callback(update, context)
    elif d == "admin_promo":
        await admin_promo_callback(update, context)
    elif d == "admin_post":
        context.user_data['admin_action'] = 'post_text'
        await q.edit_message_text("📢 <b>E'lon matnini yuboring:</b>", parse_mode='HTML')

# ==================== PHOTO HANDLER ====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if context.user_data.get('buying_balance'):
        photo = update.message.photo[-1]
        kb = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"bal_yes_{uid}"),
               InlineKeyboardButton("❌ Bekor", callback_data=f"bal_no_{uid}")]]
        await context.bot.send_photo(ADMIN_ID, photo.file_id,
            caption=f"📩 Pul to'ldirish\n👤 {update.effective_user.first_name}\n🆔 {uid}",
            reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ Chek yuborildi!")
        context.user_data['buying_balance'] = False

async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.from_user.id != ADMIN_ID: return
    
    parts = q.data.split("_")
    action = parts[1]
    target = parts[2]
    
    if action == "yes":
        # Bu yerda admin miqdorni kiritishi kerak
        context.user_data['balance_target'] = target
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ Tasdiqlandi! /addmoney {target} MIQDOR")

# ==================== MAIN ====================
def main():
    Thread(target=run_flask).start()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(bot_type_callback, pattern="^bot_type_")],
        states={
            BOT_API: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_api_received)],
            BOT_PRO_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_pro_price_received)],
        },
        fallbacks=[]
    ))
    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(CallbackQueryHandler(balance_callback, pattern="^bal_"))
    
    print("✅ Xentor Maker Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
