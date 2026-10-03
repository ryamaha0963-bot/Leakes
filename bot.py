import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== API KEY =====
API_KEY = "OSINTBOT"

# ===== TOOLS CONFIG =====
TOOLS = {
    "num_info":       {"name": "📱 Number Info",        "url": "https://num-to-info.asurpapa.workers.dev/api?key=OSINTBOT&number={q}",              "param": "number",  "prompt": "10 digit mobile number bhej"},
    "aadhar_info":    {"name": "🆔 Aadhaar Info",       "url": "https://aadhaar.asurpapa.workers.dev/api?key=OSINTBOT&aadhaar={q}",                 "param": "aadhaar", "prompt": "12 digit Aadhaar number bhej"},
    "vehicle_info":   {"name": "🚗 Vehicle Info",       "url": "https://vehicle-to-all-info.asurpapa.workers.dev/api?key=OSINTBOT&rc={q}",         "param": "rc",      "prompt": "RC number bhej (jaise DL01AB1234)"},
    "aadhar_family":  {"name": "👨‍👩‍👧 Aadhaar Family",    "url": "https://aadhaar-family.asurpapa.workers.dev/api?key=OSINTBOT&aadhaar={q}",          "param": "aadhaar", "prompt": "Aadhaar number bhej"},
    "tg_info":        {"name": "✈️ TG Info",            "url": "https://tg-to-info.asurpapa.workers.dev/api?key=OSINTBOT&query={q}",                "param": "query",   "prompt": "Telegram username ya ID bhej"},
    "ifsc_info":      {"name": "🏦 IFSC Info",          "url": "https://ifsc.asurpapa.workers.dev/api?key=OSINTBOT&ifsc={q}",                       "param": "ifsc",    "prompt": "IFSC code bhej"},
    "truecaller_info":{"name": "📞 Truecaller",         "url": "https://truecaller.asurpapa.workers.dev/api?key=OSINTBOT&q={q}",                    "param": "q",       "prompt": "Number bhej"},
    "vehicle_to_num": {"name": "🔢 Vehicle → Number",   "url": "https://vehicle-to-num.asurpapa.workers.dev/api?key=OSINTBOT&rc={q}",               "param": "rc",      "prompt": "RC number bhej"},
    "call_tracker":   {"name": "📡 Call Tracker",       "url": "https://call-tracker.asurpapa.workers.dev/api?key=OSINTBOT&number={q}",             "param": "number",  "prompt": "Number bhej"},
    "pan_info":       {"name": "💳 PAN Info",           "url": "https://pan-to-info.asurpapa.workers.dev/api?key=OSINTBOT&pan={q}",                 "param": "pan",     "prompt": "PAN number bhej"},
    "vehicle_pdf":    {"name": "📄 RC PDF",             "url": "https://rc-pdf-one.vercel.app/rc?vehicle={q}",                                       "param": "vehicle", "prompt": "Vehicle number bhej"},
}

# ===== USER STATE =====
user_state = {}   # {chat_id: tool_key}


# ===== MENU =====
def main_menu():
    buttons = []
    row = []
    for key, cfg in TOOLS.items():
        row.append(InlineKeyboardButton(cfg["name"], callback_data=f"tool:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.pop(update.effective_chat.id, None)
    await update.message.reply_text(
        "🔥 *OSINT Bot* meh swagat hai bhai!\n\nNeeche se tool select kar:",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# ===== BUTTON CLICK =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        user_state.pop(query.message.chat_id, None)
        await query.edit_message_text(
            "🔥 *OSINT Bot* — tool select kar:",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    if data.startswith("tool:"):
        tool_key = data.split(":", 1)[1]
        cfg = TOOLS.get(tool_key)
        if not cfg:
            await query.edit_message_text("❌ Tool nahi mila")
            return
        user_state[query.message.chat_id] = tool_key
        await query.edit_message_text(
            f"*{cfg['name']}* select kiya ✅\n\n➡️ {cfg['prompt']}",
            parse_mode="Markdown",
        )


# ===== TEXT INPUT → API CALL =====
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tool_key = user_state.get(chat_id)

    if not tool_key:
        await update.message.reply_text(
            "Pehle /start karke tool select kar bhai 👇",
            reply_markup=main_menu(),
        )
        return

    cfg = TOOLS[tool_key]
    q = update.message.text.strip()
    url = cfg["url"].format(q=q)

    msg = await update.message.reply_text("⏳ API se data laa raha hu...")

    try:
        r = requests.get(url, timeout=30)
        text = r.text

        # JSON try karo, warna raw text
        try:
            data = r.json()
            import json
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            pretty = text

        # Telegram 4096 char limit
        if len(pretty) > 4000:
            pretty = pretty[:4000] + "\n\n...(truncated)"

        await msg.edit_text(
            f"✅ *{cfg['name']}*\nQuery: `{q}`\n\n```\n{pretty}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]]
            ),
        )

    except requests.exceptions.Timeout:
        await msg.edit_text("❌ API timeout ho gayi bhai, dobara try kar")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`", parse_mode="Markdown")

    user_state.pop(chat_id, None)


# ===== MAIN =====
if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN set nahi hai")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🔥 Bot chalu ho raha hai...")
    app.run_polling()
