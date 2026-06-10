import json
import os
import asyncio
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
        "offers_ru": [],
        "feedbacks": []
    }

def save():
    with open(DATA, 'w') as f: json.dump(data, f, ensure_ascii=False)

def is_admin(uid):
    return str(uid) in data.get("admins", [])

def get_lang(uid):
    return data.get("users", {}).get(str(uid), {}).get("lang", "uz")

LANG = {
    "uz": {
        "welcome": "🇺🇿 O'zbek tili tanlandi!",
        "menu_locations": "📍 Manzillar",
        "menu_feedback": "💬 Fikr bildirish",
        "menu_offers": "🎯 Takliflar",
        "menu_settings": "⚙️ Sozlamalar",
        "feedback_prompt": "💬 Fikr yoki shikoyatingizni yozing:",
        "feedback_sent": "✅ Fikringiz qabul qilindi! Rahmat!",
        "offer_prompt": "🎯 Takliflaringizni yozing:",
        "offer_sent": "✅ Taklifingiz adminga yuborildi!",
        "new_offer": "🎯 Yangi taklif!",
        "admin_reply": "📩 Admin javobi:",
        "location_name": "🏪 Do'kon nomini yozing:",
        "location_send": "📍 Endi lokatsiya tashlang:",
        "location_added": "✅ Manzil qo'shildi!",
        "admin_offer_prompt": "🎯 Taklifni yozing:",
        "admin_offer_added": "✅ Taklif qo'shildi!",
        "admin_id": "👤 Admin ID sini yuboring:",
        "admin_added": "✅ Admin qo'shildi!",
        "no_locations": "📭 Manzillar yo'q",
        "no_offers": "📭 Takliflar yo'q",
        "reply_sent": "✅ Javob yuborildi!",
        "add_loc": "📍 Manzil kiritish",
        "delete_loc": "🗑 Manzil o'chirish",
        "add_offer": "🎯 Taklif qo'shish",
        "delete_offer": "🗑 Taklif o'chirish",
        "add_admin": "👤 Admin qo'shish",
        "broadcast": "📢 Post tarqatish",
        "user_menu_text": "📋 Asosiy menyu",
        "choose_shop": "🏪 Do'konni tanlang:",
        "offer_deleted": "✅ Taklif o'chirildi!",
        "loc_deleted": "✅ Manzil o'chirildi!",
        "settings_text": "⚙️ Sozlamalar\n\nTilni o'zgartirish:",
        "lang_changed": "✅ Til o'zgartirildi! /start bosing.",
        "broadcast_prompt": "📢 Post yuboring:\n\nRasm yoki matn yuboring:",
        "broadcast_sent": "✅ Post {count} kishiga yuborildi!",
    },
    "ru": {
        "welcome": "🇷🇺 Выбран русский язык!",
        "menu_locations": "📍 Адреса",
        "menu_feedback": "💬 Отзыв",
        "menu_offers": "🎯 Предложения",
        "menu_settings": "⚙️ Настройки",
        "feedback_prompt": "💬 Напишите отзыв или жалобу:",
        "feedback_sent": "✅ Отзыв принят! Спасибо!",
        "offer_prompt": "🎯 Напишите ваши предложения:",
        "offer_sent": "✅ Ваше предложение отправлено админу!",
        "new_offer": "🎯 Новое предложение!",
        "admin_reply": "📩 Ответ админа:",
        "location_name": "🏪 Название магазина:",
        "location_send": "📍 Отправьте локацию:",
        "location_added": "✅ Адрес добавлен!",
        "admin_offer_prompt": "🎯 Напишите предложение:",
        "admin_offer_added": "✅ Предложение добавлено!",
        "no_locations": "📭 Адресов нет",
        "no_offers": "📭 Предложений нет",
        "reply_sent": "✅ Ответ отправлен!",
        "add_loc": "📍 Добавить адрес",
        "delete_loc": "🗑 Удалить адрес",
        "add_offer": "🎯 Добавить предложение",
        "delete_offer": "🗑 Удалить предложение",
        "broadcast": "📢 Рассылка",
        "user_menu_text": "📋 Главное меню",
        "choose_shop": "🏪 Выберите магазин:",
        "offer_deleted": "✅ Предложение удалено!",
        "loc_deleted": "✅ Адрес удален!",
        "settings_text": "⚙️ Настройки\n\nИзменить язык:",
        "lang_changed": "✅ Язык изменен! Нажмите /start",
        "broadcast_prompt": "📢 Отправьте пост:\n\nОтправьте фото или текст:",
        "broadcast_sent": "✅ Отправлено {count} людям!",
    }
}

def lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz")],
    ])

def settings_lang_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="setlang_uz"),
         InlineKeyboardButton("🇷🇺 Русский язык", callback_data="setlang_ru")],
    ])

def user_menu_kb(lang):
    l = LANG[lang]
    return ReplyKeyboardMarkup([
        [KeyboardButton(l["menu_locations"]), KeyboardButton(l["menu_feedback"])],
        [KeyboardButton(l["menu_offers"]), KeyboardButton(l["menu_settings"])],
    ], resize_keyboard=True)

def admin_menu_kb(lang):
    l = LANG[lang]
    kb = [
        [KeyboardButton(l["menu_locations"]), KeyboardButton(l["menu_feedback"])],
        [KeyboardButton(l["menu_offers"]), KeyboardButton(l["menu_settings"])],
        [KeyboardButton("⚙️ " + l["add_loc"]), KeyboardButton("⚙️ " + l["delete_loc"])],
        [KeyboardButton("⚙️ " + l["add_offer"]), KeyboardButton("⚙️ " + l["delete_offer"])],
        [KeyboardButton("⚙️ " + l["broadcast"])],
    ]
    if lang == "uz":
        kb.append([KeyboardButton("⚙️ " + l["add_admin"])])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = str(update.effective_user.id)
    user_lang = get_lang(uid)
    
    if user_lang and data.get("users", {}).get(uid, {}).get("lang"):
        lang = user_lang
        l = LANG[lang]
        context.user_data.clear()
        
        if is_admin(uid):
            await update.message.reply_text(l["user_menu_text"], reply_markup=admin_menu_kb(lang))
        else:
            await update.message.reply_text(l["user_menu_text"], reply_markup=user_menu_kb(lang))
        return
    
    context.user_data.clear()
    await update.message.reply_text("🌐 Tilni tanlang | Выберите язык:", reply_markup=lang_kb(), parse_mode='HTML')

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    lang = q.data.replace("lang_", "")
    uid = str(q.from_user.id)
    context.user_data.clear()
    
    data.setdefault("users", {})[uid] = {"lang": lang}
    save()
    
    l = LANG[lang]
    await q.edit_message_text(l["welcome"])
    
    if is_admin(uid):
        await q.message.reply_text(l["user_menu_text"], reply_markup=admin_menu_kb(lang))
    else:
        await q.message.reply_text(l["user_menu_text"], reply_markup=user_menu_kb(lang))

# ==================== HANDLE TEXT ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    uid = str(update.effective_user.id)
    txt = update.message.text.strip()
    lang = get_lang(uid)
    l = LANG[lang]
    
    # ===== FIKR YOZISH =====
    if context.user_data.get('writing_feedback'):
        data.setdefault("feedbacks", []).append({
            "uid": uid, "name": update.effective_user.first_name,
            "text": txt, "lang": lang,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        save()
        
        for admin_id in data.get("admins", []):
            try:
                kb = [[InlineKeyboardButton("📝 Javob yozish", callback_data=f"reply_{uid}")]]
                await context.bot.send_message(
                    int(admin_id),
                    f"💬 <b>Yangi fikr!</b>\n\n👤 {update.effective_user.first_name}\n🆔 <code>{uid}</code>\n🌐 {lang}\n\n📝 {txt}",
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
                )
            except: pass
        
        await update.message.reply_text(l["feedback_sent"])
        context.user_data['writing_feedback'] = False
        return
    
    # ===== TAKLIF YOZISH (foydalanuvchi) =====
    if context.user_data.get('writing_offer'):
        offer_text = txt
        
        for admin_id in data.get("admins", []):
            try:
                kb = [[InlineKeyboardButton("📝 Javob yozish", callback_data=f"reply_{uid}")]]
                await context.bot.send_message(
                    int(admin_id),
                    f"{l['new_offer']}\n\n👤 {update.effective_user.first_name}\n🆔 <code>{uid}</code>\n🌐 {lang}\n\n📝 {offer_text}",
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
                )
            except: pass
        
        await update.message.reply_text(l["offer_sent"])
        context.user_data['writing_offer'] = False
        return
    
    # ===== ADMIN JAVOB YOZISH =====
    if context.user_data.get('replying_to'):
        target = context.user_data['replying_to']
        try:
            await context.bot.send_message(
                int(target),
                f"{l['admin_reply']}\n\n💬 {txt}",
                parse_mode='HTML'
            )
            await update.message.reply_text(l["reply_sent"])
        except:
            await update.message.reply_text("❌ Yuborib bo'lmadi!")
        context.user_data['replying_to'] = None
        return
    
    # ===== ADMIN - BROADCAST MATN =====
    if context.user_data.get('broadcasting'):
        users = data.get("users", {})
        count = 0
        for u in users:
            try:
                await context.bot.send_message(int(u), f"📢 <b>E'lon</b>\n\n{txt}", parse_mode='HTML')
                count += 1
            except: pass
        await update.message.reply_text(l["broadcast_sent"].format(count=count))
        context.user_data['broadcasting'] = False
        return
    
    # ===== ADMIN - MANZIL NOMI =====
    if context.user_data.get('adding_loc') == 'name':
        context.user_data['loc_name'] = txt
        context.user_data['adding_loc'] = 'location'
        await update.message.reply_text(l["location_send"])
        return
    
    # ===== ADMIN - TAKLIF QO'SHISH =====
    if context.user_data.get('adding_offer'):
        key = f"offers_{lang}"
        data.setdefault(key, []).append(txt)
        save()
        await update.message.reply_text(l["admin_offer_added"])
        context.user_data['adding_offer'] = False
        return
    
    # ===== ADMIN - ID =====
    if context.user_data.get('adding_admin'):
        if txt not in data.get("admins", []):
            data.setdefault("admins", []).append(txt)
            save()
            await update.message.reply_text(l["admin_added"])
        else:
            await update.message.reply_text("⚠️ Allaqachon admin!")
        context.user_data['adding_admin'] = False
        return
    
    # ===== ADMIN FUNKSIYALARI =====
    if is_admin(uid):
        if txt in [l["add_loc"], "⚙️ " + l["add_loc"]]:
            context.user_data['adding_loc'] = 'name'
            await update.message.reply_text(l["location_name"])
            return
        
        if txt in [l["delete_loc"], "⚙️ " + l["delete_loc"]]:
            locs = data.get(f"locations_{lang}", [])
            if not locs:
                await update.message.reply_text(l["no_locations"]); return
            kb = [[InlineKeyboardButton(f"🗑 {loc['name'][:30]}", callback_data=f"delloc_{lang}_{i}")] for i, loc in enumerate(locs)]
            await update.message.reply_text("O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            return
        
        if txt in [l["add_offer"], "⚙️ " + l["add_offer"]]:
            context.user_data['adding_offer'] = True
            await update.message.reply_text(l["admin_offer_prompt"])
            return
        
        if txt in [l["delete_offer"], "⚙️ " + l["delete_offer"]]:
            offs = data.get(f"offers_{lang}", [])
            if not offs:
                await update.message.reply_text(l["no_offers"]); return
            kb = [[InlineKeyboardButton(f"🗑 {o[:30]}", callback_data=f"deloffer_{lang}_{i}")] for i, o in enumerate(offs)]
            await update.message.reply_text("O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            return
        
        if txt in [l["broadcast"], "⚙️ " + l["broadcast"]]:
            context.user_data['broadcasting'] = True
            await update.message.reply_text(l["broadcast_prompt"], parse_mode='HTML')
            return
        
        if lang == "uz" and txt in [l["add_admin"], "⚙️ " + l["add_admin"]]:
            context.user_data['adding_admin'] = True
            await update.message.reply_text(l["admin_id"])
            return
    
    # ===== FOYDALANUVCHI MENYUSI =====
    if txt == l["menu_locations"]:
        locs = data.get(f"locations_{lang}", [])
        if not locs:
            await update.message.reply_text(l["no_locations"]); return
        kb = [[InlineKeyboardButton(f"🏪 {loc['name']}", callback_data=f"viewloc_{lang}_{i}")] for i, loc in enumerate(locs)]
        await update.message.reply_text(l["choose_shop"], reply_markup=InlineKeyboardMarkup(kb))
        return
    
    if txt == l["menu_feedback"]:
        context.user_data['writing_feedback'] = True
        await update.message.reply_text(l["feedback_prompt"])
        return
    
    if txt == l["menu_offers"]:
        context.user_data['writing_offer'] = True
        await update.message.reply_text(l["offer_prompt"])
        return
    
    if txt == l["menu_settings"]:
        await update.message.reply_text(l["settings_text"], reply_markup=settings_lang_kb(), parse_mode='HTML')
        return

# ==================== LOKATSIYA & RASM ====================
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    
    if is_admin(uid) and context.user_data.get('adding_loc') == 'location':
        lang = get_lang(uid)
        loc = update.message.location
        loc_data = {
            "name": context.user_data['loc_name'],
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "address": f"{loc.latitude}, {loc.longitude}"
        }
        
        key = f"locations_{lang}"
        data.setdefault(key, []).append(loc_data)
        save()
        
        await update.message.reply_text(f"✅ Manzil qo'shildi!\n\n🏪 {loc_data['name']}")
        context.user_data['adding_loc'] = None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_lang(uid)
    l = LANG[lang]
    
    if is_admin(uid) and context.user_data.get('broadcasting'):
        photo = update.message.photo[-1]
        caption = update.message.caption or "📢 E'lon"
        
        users = data.get("users", {})
        count = 0
        for u in users:
            try:
                await context.bot.send_photo(int(u), photo.file_id, caption=f"📢 <b>E'lon</b>\n\n{caption}", parse_mode='HTML')
                count += 1
            except: pass
        
        await update.message.reply_text(l["broadcast_sent"].format(count=count))
        context.user_data['broadcasting'] = False

# ==================== CALLBACK ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    
    if d.startswith("reply_"):
        target = d.replace("reply_", "")
        context.user_data['replying_to'] = target
        await q.edit_message_text(f"{q.message.text}\n\n✍️ Javob yozing:")
        return
    
    if d.startswith("delloc_"):
        parts = d.split("_")
        lang = parts[1]
        index = int(parts[2])
        key = f"locations_{lang}"
        if key in data and index < len(data[key]):
            name = data[key][index]["name"]
            del data[key][index]
            save()
            await q.edit_message_text(f"✅ {name} o'chirildi!")
        return
    
    if d.startswith("deloffer_"):
        parts = d.split("_")
        lang = parts[1]
        index = int(parts[2])
        key = f"offers_{lang}"
        if key in data and index < len(data[key]):
            del data[key][index]
            save()
            await q.edit_message_text(LANG[lang]["offer_deleted"])
        return
    
    if d.startswith("viewloc_"):
        parts = d.split("_")
        lang = parts[1]
        index = int(parts[2])
        key = f"locations_{lang}"
        if key in data and index < len(data[key]):
            loc = data[key][index]
            try:
                await context.bot.send_location(q.from_user.id, latitude=loc['latitude'], longitude=loc['longitude'])
                await q.edit_message_text(f"🏪 {loc['name']}\n📍 Yukoridagi lokatsiyada")
            except:
                await q.edit_message_text(f"🏪 {loc['name']}\n📍 {loc.get('address', '')}")
        return
    
    if d.startswith("setlang_"):
        new_lang = d.replace("setlang_", "")
        data.setdefault("users", {})[str(q.from_user.id)] = {"lang": new_lang}
        save()
        await q.edit_message_text(LANG[new_lang]["lang_changed"])
        return

# ==================== MAIN ====================
def main():
    Thread(target=run_flask).start()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^reply_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^delloc_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^deloffer_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^viewloc_"))
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^setlang_"))
    
    print("✅ Umnyaga Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
