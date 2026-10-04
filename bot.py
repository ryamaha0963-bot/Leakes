import os
import json
import requests
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============ CONFIG ============
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))  # private channel id

TOOLS = {
    "num_info":       {"name": "📱 Number Info",        "url": "https://num-to-info.asurpapa.workers.dev/api?key=OSINTBOT&number={q}",       "prompt": "10 digit mobile number bhej"},
    "aadhar_info":    {"name": "🆔 Aadhaar Info",       "url": "https://aadhaar.asurpapa.workers.dev/api?key=OSINTBOT&aadhaar={q}",          "prompt": "12 digit Aadhaar number bhej"},
    "vehicle_info":   {"name": "🚗 Vehicle Info",       "url": "https://vehicle-to-all-info.asurpapa.workers.dev/api?key=OSINTBOT&rc={q}",  "prompt": "RC number bhej (jaise DL01AB1234)"},
    "aadhar_family":  {"name": "👨‍👩‍👧 Aadhaar Family",    "url": "https://aadhaar-family.asurpapa.workers.dev/api?key=OSINTBOT&aadhaar={q}",   "prompt": "Aadhaar number bhej"},
    "tg_info":        {"name": "✈️ TG Info",            "url": "https://tg-to-info.asurpapa.workers.dev/api?key=OSINTBOT&query={q}",         "prompt": "Telegram username ya ID bhej"},
    "ifsc_info":      {"name": "🏦 IFSC Info",          "url": "https://ifsc.asurpapa.workers.dev/api?key=OSINTBOT&ifsc={q}",                "prompt": "IFSC code bhej"},
    "truecaller_info":{"name": "📞 Truecaller",         "url": "https://truecaller.asurpapa.workers.dev/api?key=OSINTBOT&q={q}",             "prompt": "Number bhej"},
    "vehicle_to_num": {"name": "🔢 Vehicle → Number",   "url": "https://vehicle-to-num.asurpapa.workers.dev/api?key=OSINTBOT&rc={q}",        "prompt": "RC number bhej"},
    "call_tracker":   {"name": "📡 Call Tracker",       "url": "https://call-tracker.asurpapa.workers.dev/api?key=OSINTBOT&number={q}",      "prompt": "Number bhej"},
    "pan_info":       {"name": "💳 PAN Info",           "url": "https://pan-to-info.asurpapa.workers.dev/api?key=OSINTBOT&pan={q}",          "prompt": "PAN number bhej"},
    "vehicle_pdf":    {"name": "📄 RC PDF",             "url": "https://rc-pdf-one.vercel.app/rc?vehicle={q}",                                "prompt": "Vehicle number bhej"},
}

LOADING_LINE = "**KRNX KI BEHEN CHARU RANDIII MANG K LAAH RHI HAI**"

HIDE_KEYS = {"credit", "developer", "footer", "contact", "powered_by"}

# ============ STORAGE ============
user_state = {}
user_results = {}
known_users = set()   # naye users track karne ke liye


def clean_response(data):
    if isinstance(data, dict):
        return {k: clean_response(v) for k, v in data.items() if k.lower() not in HIDE_KEYS}
    if isinstance(data, list):
        return [clean_response(i) for i in data]
    return data


def user_info_str(user):
    return (
        f"👤 *{user.first_name or ''} {user.last_name or ''}*\n"
        f"🆔 `{user.id}`\n"
        f"🔗 @{user.username or 'no_username'}"
    )


async def log_to_channel(context, text):
    """Channel peh log bhej"""
    if LOG_CHANNEL_ID == 0:
        return
    try:
        await context.bot.send_message(
            LOG_CHANNEL_ID,
            text,
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Log channel error: {e}")


# ============ MENUS ============
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


def result_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Naya Search", callback_data="new_search"),
            InlineKeyboardButton("📜 Mere Results", callback_data="my_results"),
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
    ])


# ============ HANDLERS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_state.pop(chat_id, None)

    text = (
        "🔥 *OSINT BOT* 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Swagat hai bhai!\n\n"
        "📌 Neeche se tool select kar 👇"
    )
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

    # ---- Log naye user ----
    if user.id not in known_users:
        known_users.add(user.id)
        await log_to_channel(
            context,
            f"🆕 *NAYA USER AAYA*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{user_info_str(user)}\n\n"
            f"🕐 `{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}`",
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    chat_id = q.message.chat_id

    if data == "back":
        user_state.pop(chat_id, None)
        text = (
            "🔥 *OSINT BOT* 🔥\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📌 Neeche se tool select kar 👇"
        )
        await q.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")
        return

    if data == "new_search":
        user_state.pop(chat_id, None)
        await q.edit_message_text(
            "🔍 *Naya Search*\n\nTool select kar 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    if data == "my_results":
        results = user_results.get(chat_id, [])
        if not results:
            await q.edit_message_text(
                "📭 Abhi tak koi result save nahi hua.\nPehle koi search kar.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]]
                ),
            )
            return

        buttons = []
        for i, r in enumerate(results, 1):
            label = f"{i}. {r['tool']} — {r['query']}"
            buttons.append([InlineKeyboardButton(label[:60], callback_data=f"view:{i-1}")])
        buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="back")])

        await q.edit_message_text(
            f"📜 *Saved Results* ({len(results)})\n\nKoi ek peh click kar 👇",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    if data.startswith("view:"):
        idx = int(data.split(":")[1])
        results = user_results.get(chat_id, [])
        if idx >= len(results):
            await q.answer("Result nahi mila", show_alert=True)
            return
        r = results[idx]
        text = (
            f"📌 *{r['tool']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔍 Query: `{r['query']}`\n\n"
            f"```\n{r['result'][:3500]}\n```"
        )
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Naya Search", callback_data="new_search")],
                [InlineKeyboardButton("⬅️ Results List", callback_data="my_results")],
            ]),
            parse_mode="Markdown",
        )
        return

    if data.startswith("tool:"):
        tool_key = data.split(":", 1)[1]
        cfg = TOOLS.get(tool_key)
        if not cfg:
            await q.edit_message_text("❌ Tool nahi mila")
            return
        user_state[chat_id] = tool_key
        text = (
            f"📌 *{cfg['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"➡️ {cfg['prompt']}"
        )
        await q.edit_message_text(text, parse_mode="Markdown")
        return


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    tool_key = user_state.get(chat_id)

    if not tool_key:
        await update.message.reply_text(
            "👉 Pehle /start karke tool select kar bhai.",
            reply_markup=main_menu(),
        )
        return

    cfg = TOOLS[tool_key]
    q = update.message.text.strip()
    url = cfg["url"].format(q=q)

    msg = await update.message.reply_text(LOADING_LINE, parse_mode="Markdown")

    try:
        r = requests.get(url, timeout=30)

        try:
            data = r.json()
            cleaned = clean_response(data)
            pretty = json.dumps(cleaned, indent=2, ensure_ascii=False)
        except Exception:
            pretty = r.text

        if len(pretty) > 3800:
            pretty = pretty[:3800] + "\n\n...(truncated)"

        # Save result
        user_results.setdefault(chat_id, []).append({
            "tool": cfg["name"],
            "query": q,
            "result": pretty,
        })
        user_results[chat_id] = user_results[chat_id][-20:]

        text = (
            f"✅ *{cfg['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔍 Query: `{q}`\n\n"
            f"```\n{pretty}\n```"
        )
        await msg.edit_text(text, reply_markup=result_menu(), parse_mode="Markdown")

        # ---- Channel meh log ----
        log_text = (
            f"🔎 *N E W   S E A R C H*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{user_info_str(user)}\n\n"
            f"📌 Tool: *{cfg['name']}*\n"
            f"🔍 Query: `{q}`\n"
            f"🕐 `{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}`\n\n"
            f"📊 *RESULT:*\n"
            f"```\n{pretty[:3500]}\n```"
        )
        await log_to_channel(context, log_text)

    except requests.exceptions.Timeout:
        await msg.edit_text(
            "❌ *API timeout* ho gayi, dobara try kar.",
            reply_markup=result_menu(),
            parse_mode="Markdown",
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`", parse_mode="Markdown")

    user_state.pop(chat_id, None)


async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Tera ID: `{update.effective_chat.id}`", parse_mode="Markdown")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sirf admin ke liye — total users ka count"""
    if LOG_CHANNEL_ID == 0:
        await update.message.reply_text("⚠️ LOG_CHANNEL_ID set nahi hai.")
        return
    await update.message.reply_text(
        f"📊 *Bot Stats*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: *{len(known_users)}*\n"
        f"🔍 Active Sessions: *{len(user_results)}*",
        parse_mode="Markdown",
    )


# ============ MAIN ============
if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN set nahi hai")
        exit(1)
    if LOG_CHANNEL_ID == 0:
        print("⚠️ LOG_CHANNEL_ID set nahi hai — channel logging off rahegi")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🔥 Bot chalu ho raha hai...")
    app.run_polling()
