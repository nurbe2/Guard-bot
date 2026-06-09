import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread

app = Flask(__name__)
@app.route('/')
def home(): return "Umnyaga Bot"
@app.route('/ping')
def ping(): return "PONG"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8833302378:AAExHBexYziQ0wIjxtXyh3zO993H7cZsrhA')
DATA = "/tmp/umnyaga_data.json"

if os.path.exists(DATA):
    with open(DATA) as f: data = json.load(f)
else:
    data = {
        "users": {},
        "admins": ["8306639956"],
        "locations_uz": [],
        "locations_ru": [],
        "offers_uz": [],
        "offers_ru": []
    }

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

def is_admin(uid):
    return str(uid) in data.get("admins", [])

LANG = {
    "uz": {
        "welcome": "🇺🇿 O'zbek tili tanlandi!",
        "menu_locations": "📍 Joylashuv manzillari",
        "menu_feedback": "💬 Fikr bildirish & Shikoyat qilish",
        "menu_offers": "🎯 Takliflar",
        "feedback_prompt": "💬 Fikr yoki shikoyatingizni yozing:",
        "feedback_sent": "✅ Fikringiz qabul qilindi! Rahmat!",
        "location_name": "🏪 Do'kon nomini yozing:",
        "location_send": "📍 Endi lokatsiya tashlang:",
        "location_added": "✅ Manzil qo'shildi!",
        "offer_prompt": "🎯 Taklifni yozing:",
        "offer_added": "✅ Taklif qo'shildi!",
        "admin_id": "👤 Admin ID sini yuboring:",
        "admin_added": "✅ Admin qo'shildi!",
        "no_locations": "📭 Manzillar yo'q",
        "no_offers": "📭 Takliflar yo'q",
        "reply_sent": "✅ Javob yuborildi!",
    },
    "ru": {
        "welcome": "🇷🇺 Выбран русский язык!",
        "menu_locations": "📍 Адреса",
        "menu_feedback": "💬 Отзыв & Жалоба",
        "menu_offers": "🎯 Предложения",
        "feedback_prompt": "💬 Напишите отзыв или жалобу:",
        "feedback_sent": "✅ Отзыв принят! Спасибо!",
        "location_name": "🏪 Название магазина:",
        "location_send": "📍 Отправьте локацию:",
        "location_added": "✅ Адрес добавлен!",
        "offer_prompt": "🎯 Напишите предложение:",
        "offer_added": "✅ Предложение добавлено!",
        "no_locations": "📭 Адресов нет",
        "no_offers": "📭 Предложений нет",
        "reply_sent": "✅ Ответ отправлен!",
    }
}

def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz")],
    ])

def user_menu(lang):
    l = LANG[lang]
    return ReplyKeyboardMarkup([
        [KeyboardButton(l["menu_locations"])],
        [KeyboardButton(l["menu_feedback"])],
        [KeyboardButton(l["menu_offers"])],
    ], resize_keyboard=True)

def admin_menu_uz():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 Manzil kiritish"), KeyboardButton("🗑 Manzil o'chirish")],
        [KeyboardButton("🎯 Taklif qo'shish"), KeyboardButton("👤 Admin qo'shish")],
        [KeyboardButton("🏠 Asosiy menyu")],
    ], resize_keyboard=True)

def admin_menu_ru():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 Добавить адрес"), KeyboardButton("🗑 Удалить адрес")],
        [KeyboardButton("🎯 Добавить предложение")],
        [KeyboardButton("🏠 Главное меню")],
    ], resize_keyboard=True)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    await update.message.reply_text("🌐 Tilni tanlang | Выберите язык:", reply_markup=lang_kb(), parse_mode='HTML')

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    lang = q.data.replace("lang_", "")
    uid = str(q.from_user.id)
    
    data.setdefault("users", {})[uid] = {"lang": lang}
    save()
    
    await q.edit_message_text(LANG[lang]["welcome"])
    await q.message.reply_text("Asosiy menyu:" if lang == "uz" else "Главное меню:", reply_markup=user_menu(lang))
    
    if is_admin(uid):
        if lang == "uz":
            await q.message.reply_text("👑 Admin Panel:", reply_markup=admin_menu_uz())
        else:
            await q.message.reply_text("👑 Админ панель:", reply_markup=admin_menu_ru())

# ==================== HANDLE TEXT ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = str(update.effective_user.id)
    txt = update.message.text.strip()
    user = data["users"].get(uid, {})
    lang = user.get("lang", "uz")
    l = LANG[lang]
    
    # Fikr yozish
    if context.user_data.get('writing_feedback'):
        for admin_id in data.get("admins", []):
            try:
                kb = [[InlineKeyboardButton("📝 Javob yozish", callback_data=f"reply_{uid}")]]
                await context.bot.send_message(
                    int(admin_id),
                    f"💬 Yangi fikr!\n\n👤 {update.effective_user.first_name}\n🆔 {uid}\n🌐 {lang}\n\n📝 {txt}",
                    reply_markup=InlineKeyboardMarkup(kb)
                )
            except: pass
        
        await update.message.reply_text(l["feedback_sent"])
        context.user_data['writing_feedback'] = False
        return
    
    # Admin javob yozish
    if context.user_data.get('replying_to'):
        target = context.user_data['replying_to']
        try:
            await context.bot.send_message(int(target), f"📩 Admin javobi:\n\n💬 {txt}")
            await update.message.reply_text(l["reply_sent"])
        except:
            await update.message.reply_text("❌ Yuborib bo'lmadi!")
        context.user_data['replying_to'] = None
        return
    
    # ===== ADMIN UZ =====
    if is_admin(uid) and lang == "uz":
        if txt == "📍 Manzil kiritish":
            context.user_data['adding_loc'] = 'name'
            await update.message.reply_text(l["location_name"])
            return
        if txt == "🗑 Manzil o'chirish":
            locs = data.get("locations_uz", [])
            if not locs:
                await update.message.reply_text("📭 Manzillar yo'q!"); return
            kb = [[InlineKeyboardButton(f"🗑 {loc['name'][:30]}", callback_data=f"delloc_uz_{i}")] for i, loc in enumerate(locs)]
            await update.message.reply_text("O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            return
        if txt == "🎯 Taklif qo'shish":
            context.user_data['adding_offer'] = True
            await update.message.reply_text(l["offer_prompt"])
            return
        if txt == "👤 Admin qo'shish":
            context.user_data['adding_admin'] = True
            await update.message.reply_text(l["admin_id"])
            return
        if txt == "🏠 Asosiy menyu":
            context.user_data.clear()
            await update.message.reply_text("Asosiy menyu:", reply_markup=user_menu(lang))
            await update.message.reply_text("👑 Admin Panel:", reply_markup=admin_menu_uz())
            return
    
    # ===== ADMIN RU =====
    if is_admin(uid) and lang == "ru":
        if txt == "📍 Добавить адрес":
            context.user_data['adding_loc'] = 'name'
            await update.message.reply_text(l["location_name"])
            return
        if txt == "🗑 Удалить адрес":
            locs = data.get("locations_ru", [])
            if not locs:
                await update.message.reply_text("📭 Адресов нет!"); return
            kb = [[InlineKeyboardButton(f"🗑 {loc['name'][:30]}", callback_data=f"delloc_ru_{i}")] for i, loc in enumerate(locs)]
            await update.message.reply_text("Выберите для удаления:", reply_markup=InlineKeyboardMarkup(kb))
            return
        if txt == "🎯 Добавить предложение":
            context.user_data['adding_offer'] = True
            await update.message.reply_text(l["offer_prompt"])
            return
        if txt == "🏠 Главное меню":
            context.user_data.clear()
            await update.message.reply_text("Главное меню:", reply_markup=user_menu(lang))
            await update.message.reply_text("👑 Админ панель:", reply_markup=admin_menu_ru())
            return
    
    # Manzil nomi
    if context.user_data.get('adding_loc') == 'name':
        context.user_data['loc_name'] = txt
        context.user_data['adding_loc'] = 'location'
        await update.message.reply_text(l["location_send"])
        return
    
    # Taklif
    if context.user_data.get('adding_offer'):
        if lang == "uz":
            data.setdefault("offers_uz", []).append(txt)
        else:
            data.setdefault("offers_ru", []).append(txt)
        save()
        await update.message.reply_text(l["offer_added"])
        context.user_data['adding_offer'] = False
        return
    
    # Admin ID
    if context.user_data.get('adding_admin'):
        if txt not in data.get("admins", []):
            data.setdefault("admins", []).append(txt)
            save()
            await update.message.reply_text(l["admin_added"])
        else:
            await update.message.reply_text("⚠️ Allaqachon admin!")
        context.user_data['adding_admin'] = False
        return
    
    # Menyu
    if txt == l["menu_locations"]:
        locs = data.get(f"locations_{lang}", [])
        if not locs:
            await update.message.reply_text(l["no_locations"])
            return
        for i, loc in enumerate(locs, 1):
            try:
                await context.bot.send_location(
                    update.effective_chat.id,
                    latitude=loc['latitude'],
                    longitude=loc['longitude']
                )
                await update.message.reply_text(f"{i}. 🏪 {loc['name']}")
            except:
                await update.message.reply_text(f"{i}. 🏪 {loc['name']}\n📍 {loc.get('address', '')}")
        return
    
    if txt == l["menu_feedback"]:
        context.user_data['writing_feedback'] = True
        await update.message.reply_text(l["feedback_prompt"])
        return
    
    if txt == l["menu_offers"]:
        offs = data.get(f"offers_{lang}", [])
        if not offs:
            await update.message.reply_text(l["no_offers"])
            return
        text = "🎯 Takliflar:\n\n" if lang == "uz" else "🎯 Предложения:\n\n"
        for i, o in enumerate(offs, 1):
            text += f"{i}. {o}\n\n"
        await update.message.reply_text(text)
        return

# ==================== LOKATSIYA ====================
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    
    if is_admin(uid) and context.user_data.get('adding_loc') == 'location':
        user = data["users"].get(uid, {})
        lang = user.get("lang", "uz")
        l = LANG[lang]
        
        loc = update.message.location
        loc_data = {
            "name": context.user_data['loc_name'],
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "address": f"{loc.latitude}, {loc.longitude}"
        }
        
        if lang == "uz":
            data.setdefault("locations_uz", []).append(loc_data)
        else:
            data.setdefault("locations_ru", []).append(loc_data)
        save()
        
        await update.message.reply_text(l["location_added"])
        context.user_data['adding_loc'] = None

# ==================== CALLBACK ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    
    if d.startswith("reply_"):
        target = d.replace("reply_", "")
        context.user_data['replying_to'] = target
        await q.edit_message_text(f"{q.message.text}\n\n✍️ Javob yozing:")
    
    elif d.startswith("delloc_"):
        parts = d.split("_")
        lang = parts[1]
        index = int(parts[2])
        
        key = f"locations_{lang}"
        if key in data and index < len(data[key]):
            name = data[key][index]["name"]
            del data[key][index]
            save()
            await q.edit_message_text(f"✅ {name} o'chirildi!")

# ==================== MAIN ====================
def main():
    Thread(target=run_flask).start()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^reply_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^delloc_"))
    
    print("✅ Umnyaga Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
