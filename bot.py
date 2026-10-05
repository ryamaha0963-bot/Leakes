import os
import json
import requests
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
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
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))

# Har tool ke saath description bhi
TOOLS = {
    "num_info": {
        "name": "📱 Number Info",
        "desc": "Mobile number ki poori details — owner name, address, operator, SIM info sab kuch",
        "url": "https://num-to-info.asurpapa.workers.dev/api?key=OSINTBOT&number={q}",
        "prompt": "10 digit mobile number bhej",
        "example": "9876543210",
    },
    "aadhar_info": {
        "name": "🆔 Aadhaar Info",
        "desc": "Aadhaar number se registered details — naam, pata, DOB sab",
        "url": "https://aadhaar.asurpapa.workers.dev/api?key=OSINTBOT&aadhaar={q}",
        "prompt": "12 digit Aadhaar number bhej",
        "example": "123456789012",
    },
    "vehicle_info": {
        "name": "🚗 Vehicle Info",
        "desc": "RC number se gaadi ki poori details — owner, insurance, fitness sab",
        "url": "https://vehicle-to-all-info.asurpapa.workers.dev/api?key=OSINTBOT&rc={q}",
        "prompt": "RC number bhej",
        "example": "DL01AB1234",
    },
    "aadhar_family": {
        "name": "👨‍👩‍👧 Aadhaar Family",
        "desc": "Aadhaar se poori family ki details — sab members ka data",
        "url": "https://aadhaar-family.asurpapa.workers.dev/api?key=OSINTBOT&aadhaar={q}",
        "prompt": "Aadhaar number bhej",
        "example": "123456789012",
    },
    "tg_info": {
        "name": "✈️ TG Info",
        "desc": "Telegram username ya ID se user ki info — name, bio, phone sab",
        "url": "https://tg-to-info.asurpapa.workers.dev/api?key=OSINTBOT&query={q}",
        "prompt": "Telegram username ya ID bhej",
        "example": "@username",
    },
    "ifsc_info": {
        "name": "🏦 IFSC Info",
        "desc": "IFSC code se bank branch ki poori details",
        "url": "https://ifsc.asurpapa.workers.dev/api?key=OSINTBOT&ifsc={q}",
        "prompt": "IFSC code bhej",
        "example": "SBIN0001234",
    },
    "truecaller_info": {
        "name": "📞 Truecaller",
        "desc": "Truecaller database se number ka naam nikal",
        "url": "https://truecaller.asurpapa.workers.dev/api?key=OSINTBOT&q={q}",
        "prompt": "Number bhej",
        "example": "9876543210",
    },
    "vehicle_to_num": {
        "name": "🔢 Vehicle → Number",
        "desc": "Gaadi ke RC number se owner ka mobile number nikalo",
        "url": "https://vehicle-to-num.asurpapa.workers.dev/api?key=OSINTBOT&rc={q}",
        "prompt": "RC number bhej",
        "example": "DL01AB1234",
    },
    "call_tracker": {
        "name": "📡 Call Tracker",
        "desc": "Number ki call history aur location details",
        "url": "https://call-tracker.asurpapa.workers.dev/api?key=OSINTBOT&number={q}",
        "prompt": "Number bhej",
        "example": "9876543210",
    },
    "pan_info": {
        "name": "💳 PAN Info",
        "desc": "PAN card number se registered details",
        "url": "https://pan-to-info.asurpapa.workers.dev/api?key=OSINTBOT&pan={q}",
        "prompt": "PAN number bhej",
        "example": "ABCDE1234F",
    },
    "vehicle_pdf": {
        "name": "📄 RC PDF",
        "desc": "Gaadi ka RC certificate PDF meh download karo",
        "url": "https://rc-pdf-one.vercel.app/rc?vehicle={q}",
        "prompt": "Vehicle number bhej",
        "example": "DL01AB1234",
    },
}

LOADING_TEXT = "**KRNX KI BEHEN CHARU RANDIII MANG K LAAH RHI HAI**"

HIDE_KEYS = {"credit", "developer", "footer", "contact", "powered_by"}

# ============ STORAGE ============
user_state = {}
user_results = {}
known_users = set()


def clean_response(data):
    if isinstance(data, dict):
        return {k: clean_response(v) for k, v in data.items() if k.lower() not in HIDE_KEYS}
    if isinstance(data, list):
        return [clean_response(i) for i in data]
    return data


def to_text(data, indent=0):
    """JSON ko clean text meh convert karo."""
    pad = "  " * indent
    lines = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = k.replace("_", " ").title()
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}▸ {key}:")
                lines.append(to_text(v, indent + 1))
            else:
                lines.append(f"{pad}▸ {key}: {v}")
    elif isinstance(data, list):
        if not data:
            lines.append(f"{pad}(khaali)")
        for i, item in enumerate(data, 1):
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{i}.")
                lines.append(to_text(item, indent + 1))
            else:
                lines.append(f"{pad}{i}. {item}")
    else:
        lines.append(f"{pad}{data}")
    return "\n".join(lines)


async def log_to_channel(context, text):
    if LOG_CHANNEL_ID == 0:
        return
    try:
        if len(text) > 4000:
            text = text[:4000] + "\n\n...(truncated)"
        await context.bot.send_message(LOG_CHANNEL_ID, text, parse_mode=None)
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


def result_menu(result_text: str):
    """Result ke baad ke buttons — Copy + Naya Search + Mere Results"""
    buttons = [
        [InlineKeyboardButton("📋 Copy Result", copy_text=CopyTextButton(text=result_text[:256]))],
        [
            InlineKeyboardButton("🔍 Naya Search", callback_data="new_search"),
            InlineKeyboardButton("📜 Mere Results", callback_data="my_results"),
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
    ]
    return InlineKeyboardMarkup(buttons)


def tool_detail_menu(tool_key):
    """Tool select karne ke baad — Back button"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="new_search")],
    ])


# ============ /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_state.pop(chat_id, None)

    text = (
        "🔥 *OSINT BOT* 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 Swagat hai bhai!\n\n"
        "🎯 *11 powerful OSINT tools* —\n"
        "sab kuch ek jagah!\n\n"
        "📌 Neeche se tool select kar 👇"
    )
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

    if user.id not in known_users:
        known_users.add(user.id)
        await log_to_channel(
            context,
            f"🆕 NAYA USER AAYA\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.first_name or ''} {user.last_name or ''}\n"
            f"🆔 {user.id}\n"
            f"🔗 @{user.username or 'no_username'}\n\n"
            f"🕐 {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
        )


# ============ BUTTONS ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    chat_id = q.message.chat_id

    if data == "back":
        user_state.pop(chat_id, None)
        await q.message.reply_text(
            "🔥 *OSINT BOT* 🔥\n━━━━━━━━━━━━━━━━━━━━\n📌 Tool select kar 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    if data == "new_search":
        user_state.pop(chat_id, None)
        await q.message.reply_text(
            "🔍 *Naya Search*\n━━━━━━━━━━━━━━━━━━━━\n📌 Tool select kar 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    if data == "my_results":
        results = user_results.get(chat_id, [])
        if not results:
            await q.message.reply_text("📭 Abhi tak koi result save nahi hua.")
            return

        buttons = []
        for i, r in enumerate(results, 1):
            label = f"{i}. {r['tool']} — {r['query']}"
            buttons.append([InlineKeyboardButton(label[:55], callback_data=f"view:{i-1}")])
        buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="back")])

        await q.message.reply_text(
            f"📜 *Saved Results* ({len(results)})\n━━━━━━━━━━━━━━━━━━━━\nKoi ek peh click kar 👇",
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
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Query: `{r['query']}`\n\n"
            f"{r['result']}"
        )
        buttons = [
            [InlineKeyboardButton("📋 Copy Result", copy_text=CopyTextButton(text=r['result'][:256]))],
            [
                InlineKeyboardButton("🔍 Naya Search", callback_data="new_search"),
                InlineKeyboardButton("⬅️ Results", callback_data="my_results"),
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
        ]
        await q.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    if data.startswith("tool:"):
        tool_key = data.split(":", 1)[1]
        cfg = TOOLS.get(tool_key)
        if not cfg:
            await q.message.reply_text("❌ Tool nahi mila")
            return
        user_state[chat_id] = tool_key
        text = (
            f"{cfg['name']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 *Description:*\n{cfg['desc']}\n\n"
            f"➡️ *Input:* {cfg['prompt']}\n"
            f"💡 *Example:* `{cfg['example']}`\n\n"
            f"👇 Ab apna input bhej"
        )
        await q.message.reply_text(text, reply_markup=tool_detail_menu(tool_key), parse_mode="Markdown")
        return


# ============ TEXT → API CALL ============
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

    # Loading
    msg = await update.message.reply_text(LOADING_TEXT, parse_mode="Markdown")

    try:
        r = requests.get(url, timeout=30)

        try:
            data = r.json()
            cleaned = clean_response(data)
            plain = to_text(cleaned)
        except Exception:
            plain = r.text

        if len(plain) > 3500:
            plain = plain[:3500] + "\n\n...(truncated)"

        user_results.setdefault(chat_id, []).append({
            "tool": cfg["name"],
            "query": q,
            "result": plain,
        })
        user_results[chat_id] = user_results[chat_id][-20:]

        try:
            await msg.delete()
        except Exception:
            pass

        # Result — plain text + copy button
        text = (
            f"✅ *{cfg['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Query: `{q}`\n\n"
            f"{plain}"
        )
        await update.message.reply_text(text, reply_markup=result_menu(plain), parse_mode="Markdown")

        # ---- Channel log ----
        log_text = (
            f"🔎 N E W   S E A R C H\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {user.first_name or ''} {user.last_name or ''}\n"
            f"🆔 {user.id}\n"
            f"🔗 @{user.username or 'no_username'}\n\n"
            f"📌 Tool: {cfg['name']}\n"
            f"🔍 Query: {q}\n"
            f"🕐 {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n\n"
            f"📊 RESULT:\n"
            f"{plain[:3500]}"
        )
        await log_to_channel(context, log_text)

    except requests.exceptions.Timeout:
        try:
            await msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            "❌ API timeout ho gayi, dobara try kar.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Naya Search", callback_data="new_search")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
            ]),
        )
    except Exception as e:
        try:
            await msg.delete()
        except Exception:
            pass
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode="Markdown")

    user_state.pop(chat_id, None)


async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Tera ID: `{update.effective_chat.id}`", parse_mode="Markdown")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 *Bot Stats*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: *{len(known_users)}*\n"
        f"🔍 Sessions: *{len(user_results)}*",
        parse_mode="Markdown",
    )


# ============ MAIN ============
if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN set nahi hai")
        exit(1)
    if LOG_CHANNEL_ID == 0:
        print("⚠️ LOG_CHANNEL_ID set nahi hai")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🔥 Bot chalu ho raha hai...")
    app.run_polling()
