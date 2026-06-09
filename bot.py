import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread

app = Flask(__name__)
@app.route('/')
def home(): return "Xentor Maker"
@app.route('/ping')
def ping(): return "PONG"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

MAKER_TOKEN = os.environ.get('BOT_TOKEN', '8922646707:AAHhq7K2Krvu7EKDJ1vOdiid8dUUyD6X2KQ')
ADMIN_ID = 8306639956
CHANNEL = '@xentormaker'
DATA = "/tmp/maker_data.json"

if os.path.exists(DATA):
    with open(DATA) as f: data = json.load(f)
else:
    data = {
        "users": {},
        "user_bots": {},
        "promocodes": {},
        "daily_bonus": {}
    }

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

# Faol foydalanuvchi botlari
active_user_bots = {}

def maker_menu(uid):
    balance = data["users"].get(str(uid), {}).get("balance", 0)
    kb = [
        [KeyboardButton("🤖 Bot yaratish")],
        [KeyboardButton("👛 Hisobim"), KeyboardButton("💰 Pul ishlash")],
        [KeyboardButton("📋 Botlarim"), KeyboardButton("❓ Yordam")],
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def kino_admin_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("🗑 Kino o'chirish")],
        [KeyboardButton("📋 Kinolar ro'yxati"), KeyboardButton("🔙 Maker ga qaytish")],
    ], resize_keyboard=True)

async def check_sub(uid, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, uid)
        return member.status not in ['left', 'kicked']
    except:
        return False

# ==================== MAKER START ====================
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
            f"👋 Salom, {name}!\n\n📢 {CHANNEL} ga obuna bo'ling!",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    
    # Foydalanuvchi boti rejimida emas
    context.user_data['in_bot'] = None
    
    balance = data["users"][str(uid)].get("balance", 0)
    bots_count = len(data["users"][str(uid)].get("bots", {}))
    
    await update.message.reply_text(
        f"🤖 <b>XENTOR MAKER</b>\n\n"
        f"👛 Balans: {balance} so'm\n"
        f"🤖 Botlarim: {bots_count} ta\n\n"
        f"Bugun nima qilamiz? 😊",
        reply_markup=maker_menu(uid),
        parse_mode='HTML'
    )

# ==================== BOT YARATISH ====================
async def create_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['creating_bot'] = True
    context.user_data['bot_step'] = 'token'
    await update.message.reply_text(
        "🤖 <b>Bot yaratish</b>\n\n"
        "1️⃣ <b>@BotFather dan bot tokenini oling</b>\n"
        "2️⃣ Tokenni shu yerga yuboring:\n\n"
        "<i>Masalan: 123456:ABCdef...</i>",
        parse_mode='HTML'
    )

async def handle_bot_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('creating_bot'):
        return
    
    txt = update.message.text.strip()
    step = context.user_data.get('bot_step')
    
    if step == 'token':
        # Tokenni tekshirish
        try:
            test_app = Application.builder().token(txt).build()
            bot_info = await test_app.bot.get_me()
            
            context.user_data['new_bot_token'] = txt
            context.user_data['new_bot_name'] = bot_info.first_name
            context.user_data['new_bot_username'] = bot_info.username
            context.user_data['bot_step'] = 'pro_price'
            
            await update.message.reply_text(
                f"✅ Bot: @{bot_info.username}\n\n"
                f"💰 <b>PRO narxini kiriting (so'm):</b>\n"
                f"<i>Masalan: 14000</i>",
                parse_mode='HTML'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Noto'g'ri token! Qaytadan yuboring.\n\nXatolik: {e}")
    
    elif step == 'pro_price':
        try:
            pro_price = int(txt)
            uid = str(update.effective_user.id)
            username = context.user_data['new_bot_username']
            token = context.user_data['new_bot_token']
            
            # Bot ma'lumotlarini saqlash
            bot_data = {
                "token": token,
                "name": context.user_data['new_bot_name'],
                "username": username,
                "pro_price": pro_price,
                "owner": uid,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "movies": {},
                "pro_users": [],
                "payments": []
            }
            
            data.setdefault("user_bots", {})[username] = bot_data
            data["users"][uid].setdefault("bots", {})[username] = bot_data
            save()
            
            # Botni ishga tushirish
            await start_user_kino_bot(username, token, uid, pro_price)
            
            await update.message.reply_text(
                f"🎉 <b>Bot yaratildi va ishga tushdi!</b>\n\n"
                f"🤖 @{username}\n"
                f"💰 PRO: {pro_price} so'm\n\n"
                f"<b>Endi nima qilish kerak:</b>\n"
                f"1. @{username} ga /start yozing\n"
                f"2. Siz admin sifatida kino qo'sha olasiz!\n\n"
                f"<b>Admin panel uchun:</b> @{username} da /admin yozing",
                parse_mode='HTML'
            )
            
            context.user_data['creating_bot'] = False
            context.user_data['bot_step'] = None
            
        except:
            await update.message.reply_text("❌ Raqam kiriting!")

# ==================== FOYDALANUVCHI BOTINI ISHGA TUSHIRISH ====================
async def start_user_kino_bot(username, token, owner_id, pro_price):
    """Foydalanuvchi boti uchun kino funksiyalarini ishga tushirish"""
    try:
        user_app = Application.builder().token(token).build()
        
        # Bot ma'lumotlari
        bot_data = {
            "app": user_app,
            "owner": str(owner_id),
            "pro_price": pro_price,
            "username": username
        }
        
        # Kino bot handlerlari
        async def user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.effective_chat.type != 'private':
                return
            
            uid = update.effective_user.id
            movies = data["user_bots"].get(username, {}).get("movies", {})
            
            if str(uid) == str(owner_id):
                await update.message.reply_text(
                    f"🎬 <b>KINO BOT</b>\n\n"
                    f"👋 Admin, xush kelibsiz!\n\n"
                    f"🔢 Kod yuboring yoki /admin",
                    reply_markup=kino_admin_menu(),
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    f"🎬 <b>KINO BOT</b>\n\n"
                    f"🔢 Kino kodini yuboring va toping!\n\n"
                    f"📊 Jami kinolar: {len(movies)} ta"
                )
        
        async def user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if str(update.effective_user.id) != str(owner_id):
                await update.message.reply_text("❌ Siz admin emassiz!")
                return
            await update.message.reply_text("👑 Admin Panel", reply_markup=kino_admin_menu())
        
        async def user_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            uid = str(update.effective_user.id)
            txt = update.message.text.strip()
            movies = data["user_bots"].get(username, {}).get("movies", {})
            
            # Admin funksiyalari
            if uid == str(owner_id):
                if txt == "🎬 Kino qo'shish":
                    context.user_data['user_adding'] = True
                    context.user_data['user_step'] = 'code'
                    await update.message.reply_text("🔢 <b>Kino kodini yuboring:</b>", parse_mode='HTML')
                    return
                
                if txt == "🗑 Kino o'chirish":
                    if not movies:
                        await update.message.reply_text("📭 Kinolar yo'q!"); return
                    kb = [[InlineKeyboardButton(f"🗑 {code} - {m['name'][:30]}", callback_data=f"udel_{username}_{code}")] for code, m in movies.items()]
                    await update.message.reply_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
                    return
                
                if txt == "📋 Kinolar ro'yxati":
                    if not movies:
                        await update.message.reply_text("📭 Kinolar yo'q!"); return
                    text = "📋 <b>Kinolar:</b>\n\n"
                    for code, m in movies.items():
                        text += f"🎬 {code} | {m['name']} | 👁{m.get('views', 0)}\n"
                    await update.message.reply_text(text, parse_mode='HTML')
                    return
                
                if txt == "🔙 Maker ga qaytish":
                    context.user_data['user_adding'] = False
                    await update.message.reply_text("🔙 Maker ga qaytdingiz. /start bosing.")
                    return
                
                # Kino qo'shish bosqichlari
                if context.user_data.get('user_adding'):
                    step = context.user_data.get('user_step')
                    if step == 'code':
                        context.user_data['user_code'] = txt
                        context.user_data['user_step'] = 'name'
                        await update.message.reply_text("📝 <b>Kino nomini yuboring:</b>", parse_mode='HTML')
                    elif step == 'name':
                        code = context.user_data['user_code']
                        data["user_bots"][username]["movies"][code] = {
                            "name": txt,
                            "desc": "",
                            "genre": "",
                            "parts_count": 1,
                            "parts": {},
                            "rating": 0,
                            "views": 0,
                            "added": datetime.now().strftime("%Y-%m-%d")
                        }
                        save()
                        context.user_data['user_adding'] = False
                        await update.message.reply_text(f"✅ <b>Kino qo'shildi!</b>\n🎬 {txt}\n🔢 Kod: {code}", parse_mode='HTML')
                    return
            
            # Kino kodini qidirish
            movie = movies.get(txt)
            if movie:
                data["user_bots"][username]["movies"][txt]["views"] = data["user_bots"][username]["movies"][txt].get("views", 0) + 1
                save()
                
                text = f"🎬 <b>{movie['name']}</b>\n\n"
                text += f"⭐ Reyting: {movie.get('rating', 0)}/5\n"
                text += f"🎭 Janr: {movie.get('genre', 'Nomalum')}\n"
                text += f"🔢 Kod: <code>{txt}</code>\n"
                text += f"🎞 Qismlar: {movie.get('parts_count', 1)}\n"
                text += f"👁 Ko'rishlar: {movie.get('views', 0)}\n"
                text += f"📅 Qo'shilgan: {movie.get('added', '?')}"
                
                parts = movie.get("parts", {})
                kb = []
                parts_row = []
                for i in range(1, movie.get('parts_count', 1) + 1):
                    if str(i) in parts:
                        parts_row.append(InlineKeyboardButton(f"▶️{i}", callback_data=f"uplay_{username}_{txt}_{i}"))
                if parts_row:
                    kb.append(parts_row)
                
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode='HTML')
                return
            
            await update.message.reply_text("❌ Kino topilmadi!")
        
        async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            q = update.callback_query
            await q.answer()
            d = q.data
            
            if d.startswith("udel_"):
                parts = d.split("_")
                bot_username = parts[1]
                code = parts[2]
                
                if bot_username in data["user_bots"] and code in data["user_bots"][bot_username]["movies"]:
                    name = data["user_bots"][bot_username]["movies"][code]["name"]
                    del data["user_bots"][bot_username]["movies"][code]
                    save()
                    await q.edit_message_text(f"✅ {name} o'chirildi!")
            
            elif d.startswith("uplay_"):
                parts = d.split("_")
                bot_username = parts[1]
                code = parts[2]
                part_num = parts[3]
                
                movie = data["user_bots"].get(bot_username, {}).get("movies", {}).get(code, {})
                video_id = movie.get("parts", {}).get(part_num)
                if video_id:
                    await q.message.reply_video(video_id, caption=f"🎬 {movie['name']} - Qism {part_num}")
        
        # Handlerlarni qo'shish
        user_app.add_handler(CommandHandler("start", user_start))
        user_app.add_handler(CommandHandler("admin", user_admin))
        user_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_handle_text))
        user_app.add_handler(CallbackQueryHandler(user_callback))
        
        # Botni ishga tushirish
        await user_app.initialize()
        await user_app.start()
        asyncio.create_task(user_app.updater.start_polling())
        
        active_user_bots[username] = bot_data
        print(f"✅ Bot ishga tushdi: @{username}")
        
    except Exception as e:
        print(f"❌ Bot ishga tushmadi: {e}")

# ==================== MAKER HANDLE TEXT ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    # Bot yaratish jarayoni
    if context.user_data.get('creating_bot'):
        await handle_bot_creation(update, context)
        return
    
    # Admin amallari
    if uid == ADMIN_ID and context.user_data.get('admin_action'):
        action = context.user_data['admin_action']
        
        if action == 'user_id':
            context.user_data['target_uid'] = txt
            context.user_data['admin_action'] = 'user_amount'
            await update.message.reply_text("💰 Qancha pul qo'shmoqchisiz?", parse_mode='HTML')
        
        elif action == 'user_amount':
            try:
                amount = int(txt)
                target = context.user_data['target_uid']
                data.setdefault("users", {}).setdefault(target, {})
                data["users"][target]["balance"] = data["users"][target].get("balance", 0) + amount
                save()
                await update.message.reply_text(f"✅ {amount} so'm qo'shildi!")
                context.user_data['admin_action'] = None
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif action == 'promo_name':
            context.user_data['promo_name'] = txt
            context.user_data['admin_action'] = 'promo_reward'
            await update.message.reply_text("🎁 Mukofot miqdori:")
        
        elif action == 'promo_reward':
            try:
                context.user_data['promo_reward'] = int(txt)
                context.user_data['admin_action'] = 'promo_limit'
                await update.message.reply_text("👥 Necha kishi ishlata oladi?")
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif action == 'promo_limit':
            try:
                limit = int(txt)
                data.setdefault("promocodes", {})[context.user_data['promo_name']] = {
                    "reward": context.user_data['promo_reward'],
                    "limit": limit,
                    "used_by": []
                }
                save()
                await update.message.reply_text(f"✅ Promokod yaratildi!")
                context.user_data['admin_action'] = None
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif action == 'post_text':
            text = f"📢 {txt}"
            users = data.get("users", {})
            count = 0
            for u in users:
                try:
                    await context.bot.send_message(int(u), text)
                    count += 1
                except: pass
            await update.message.reply_text(f"✅ {count} kishiga yuborildi!")
            context.user_data['admin_action'] = None
        
        return
    
    # Promokod kiritish
    if context.user_data.get('entering_promo'):
        promo = txt.upper()
        promo_data = data.get("promocodes", {}).get(promo)
        
        if not promo_data:
            await update.message.reply_text("❌ Bunday promokod yo'q!")
        elif str(uid) in promo_data.get("used_by", []):
            await update.message.reply_text("❌ Siz ishlatgansiz!")
        elif len(promo_data.get("used_by", [])) >= promo_data.get("limit", 1):
            await update.message.reply_text("❌ Limit to'lgan!")
        else:
            reward = promo_data["reward"]
            data["promocodes"][promo]["used_by"].append(str(uid))
            data["users"][str(uid)]["balance"] = data["users"][str(uid)].get("balance", 0) + reward
            save()
            await update.message.reply_text(f"🎉 +{reward} so'm qo'shildi!")
        
        context.user_data['entering_promo'] = False
        return
    
    # Menyu tugmalari
    if txt == "🤖 Bot yaratish":
        await create_bot_start(update, context)
    elif txt == "👛 Hisobim":
        balance = data["users"].get(str(uid), {}).get("balance", 0)
        await update.message.reply_text(f"👛 Balans: {balance} so'm\n\n💳 To'lov: 4916 9903 1619 3280")
    elif txt == "💰 Pul ishlash":
        kb = [
            [InlineKeyboardButton("🎁 Kunlik bonus (20 so'm)", callback_data="daily_bonus")],
            [InlineKeyboardButton("🎟 Promokod", callback_data="promo_enter")],
        ]
        await update.message.reply_text("💰 Pul ishlash:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    elif txt == "📋 Botlarim":
        bots = data["users"].get(str(uid), {}).get("bots", {})
        if not bots:
            await update.message.reply_text("📭 Botlar yo'q!")
        else:
            text = "🤖 Botlarim:\n\n"
            for username, bot in bots.items():
                text += f"🤖 @{username}\n💰 PRO: {bot['pro_price']} so'm\n\n"
            await update.message.reply_text(text)
    elif txt == "👑 Admin Panel" and uid == ADMIN_ID:
        kb = [
            [InlineKeyboardButton("👥 Foydalanuvchiga pul", callback_data="admin_user")],
            [InlineKeyboardButton("🎟 Promokod yaratish", callba
