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
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

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

LOADING_TEXT = "**KRNX KI BEHEN CHARU RANDIII MANG K LAAH RHI HAI**"

HIDE_KEYS = {"credit", "developer", "footer", "contact", "powered_by"}

# ============ STORAGE ============
user_state = {}
user_results = {}
known_users = set()
loading_image_id = None
waiting_for_pic = set()


def clean_response(data):
    if isinstance(data, dict):
        return {k: clean_response(v) for k, v in data.items() if k.lower() not in HIDE_KEYS}
    if isinstance(data, list):
        return [clean_response(i) for i in data]
    return data


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


def after_result_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Naya Search", callback_data="new_search"),
            InlineKeyboardButton("📜 Mere Results", callback_data="my_results"),
        ],
    ])


# ============ /setpic ============
async def setpic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_ID != 0 and user_id != ADMIN_ID:
        await update.message.reply_text("❌ Sirf admin ye command use kar sakta hai.")
        return
    waiting_for_pic.add(user_id)
    await update.message.reply_text("📸 Ab mujhe photo bhej.")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global loading_image_id
    user_id = update.effective_user.id
    if user_id not in waiting_for_pic:
        return
    waiting_for_pic.discard(user_id)
    # Sabse chhoti size ki photo lo — compression
    photo = update.message.photo[0]
    loading_image_id = photo.file_id
    await update.message.reply_text(
        f"✅ Pic set ho gayi (chhoti size).\n\n🆔 `{loading_image_id}`",
        parse_mode="Markdown",
    )


# ============ /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_state.pop(chat_id, None)

    caption = "🔥 *OSINT BOT* 🔥\n👋 Swagat hai bhai!\n📌 Tool select kar 👇"

    if loading_image_id:
        try:
            await update.message.reply_photo(
                photo=loading_image_id,
                caption=caption,
                reply_markup=main_menu(),
                parse_mode="Markdown",
            )
        except Exception:
            await update.message.reply_text(caption, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, reply_markup=main_menu(), parse_mode="Markdown")

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
            "🔥 *OSINT BOT* 🔥\n📌 Tool select kar 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    if data == "new_search":
        user_state.pop(chat_id, None)
        await q.message.reply_text(
            "🔍 *Naya Search*\n📌 Tool select kar 👇",
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
            f"📜 *Saved Results* ({len(results)})",
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
        caption = f"📌 {r['tool']}\n🔍 {r['query']}"

        if loading_image_id:
            try:
                await q.message.reply_photo(
                    photo=loading_image_id,
                    caption=caption[:900],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Naya Search", callback_data="new_search")],
                        [InlineKeyboardButton("⬅️ Results", callback_data="my_results")],
                    ]),
                    parse_mode="Markdown",
                )
                await q.message.reply_text(f"```\n{r['result'][:3500]}\n```", parse_mode="Markdown")
                return
            except Exception:
                pass

        text = f"{caption}\n\n```\n{r['result'][:3500]}\n```"
        await q.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Naya Search", callback_data="new_search")],
                [InlineKeyboardButton("⬅️ Results", callback_data="my_results")],
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
        await q.edit_message_text(f"📌 *{cfg['name']}*\n➡️ {cfg['prompt']}", parse_mode="Markdown")
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

    # ===== LOADING =====
    if loading_image_id:
        try:
            msg = await update.message.reply_photo(
                photo=loading_image_id,
                caption=LOADING_TEXT,
                parse_mode="Markdown",
            )
        except Exception:
            msg = await update.message.reply_text(LOADING_TEXT, parse_mode="Markdown")
    else:
        msg = await update.message.reply_text(LOADING_TEXT, parse_mode="Markdown")

    try:
        r = requests.get(url, timeout=30)

        try:
            data = r.json()
            cleaned = clean_response(data)
            pretty = json.dumps(cleaned, indent=2, ensure_ascii=False)
        except Exception:
            pretty = r.text

        if len(pretty) > 3500:
            pretty = pretty[:3500] + "\n\n...(truncated)"

        user_results.setdefault(chat_id, []).append({
            "tool": cfg["name"],
            "query": q,
            "result": pretty,
        })
        user_results[chat_id] = user_results[chat_id][-20:]

        try:
            await msg.delete()
        except Exception:
            pass

        # ===== RESULT: chhota caption + pic =====
        # Caption sirf 2 lines — taaki chhota dikhe
        short_caption = f"✅ {cfg['name']}\n🔍 {q}"

        if loading_image_id:
            try:
                await update.message.reply_photo(
                    photo=loading_image_id,
                    caption=short_caption,
                    reply_markup=after_result_menu(),
                    parse_mode="Markdown",
                )
                # Full result alag message meh (monospace, compact)
                await update.message.reply_text(
                    f"```\n{pretty}\n```",
                    parse_mode="Markdown",
                )
            except Exception:
                text = f"{short_caption}\n\n```\n{pretty}\n```"
                await update.message.reply_text(text, reply_markup=after_result_menu(), parse_mode="Markdown")
        else:
            text = f"{short_caption}\n\n```\n{pretty}\n```"
            await update.message.reply_text(text, reply_markup=after_result_menu(), parse_mode="Markdown")

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
            f"{pretty[:3500]}"
        )
        await log_to_channel(context, log_text)

    except requests.exceptions.Timeout:
        try:
            await msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            "❌ API timeout ho gayi, dobara try kar.",
            reply_markup=after_result_menu(),
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
        f"👥 Users: *{len(known_users)}*\n"
        f"🔍 Sessions: *{len(user_results)}*\n"
        f"🖼 Pic: *{'Set ✅' if loading_image_id else 'Not set ❌'}*",
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
    if ADMIN_ID == 0:
        print("⚠️ ADMIN_ID set nahi hai")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("setpic", setpic_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🔥 Bot chalu ho raha hai...")
    app.run_polling()
