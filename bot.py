import os
import json
import requests
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
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
FREE_CREDITS = 5

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
user_credits = {}
user_results = {}
pending_requests = {}
req_counter = {"n": 0}


def clean_response(data):
    if isinstance(data, dict):
        return {k: clean_response(v) for k, v in data.items() if k.lower() not in HIDE_KEYS}
    if isinstance(data, list):
        return [clean_response(i) for i in data]
    return data


def get_credits(chat_id):
    if chat_id not in user_credits:
        user_credits[chat_id] = FREE_CREDITS
    return user_credits[chat_id]


def fmt_credits(chat_id):
    c = get_credits(chat_id)
    bar = "🟩" * min(c, 10) + "⬛" * max(0, 10 - c)
    return f"{bar}  `{c}` 💎"


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
    buttons.append([InlineKeyboardButton("💎 ᴄʀᴇᴅɪᴛ ᴘʀᴏꜰɪʟᴇ", callback_data="profile")])
    return InlineKeyboardMarkup(buttons)


def result_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 ɴᴀʏᴀ ꜱᴇᴀʀᴄʜ", callback_data="new_search"),
            InlineKeyboardButton("📜 ᴍᴇʀᴇ ʀᴇꜱᴜʟᴛꜱ", callback_data="my_results"),
        ],
        [InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back")],
    ])


def no_credit_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 ᴀᴅᴍɪɴ ᴋᴏ ʀᴇQᴜᴇꜱᴛ ʙʜᴇᴊ", callback_data="req_credit")],
        [InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back")],
    ])


def profile_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 ᴀᴜʀ ᴄʀᴇᴅɪᴛ ᴍᴀᴀɴɢ", callback_data="req_credit")],
        [InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back")],
    ])


# ============ MAIN MENU TEXT ============
def main_text(chat_id):
    return (
        "╔══════════════════════════╗\n"
        "║   🔥  *ᴏꜱɪɴᴛ ʙᴏᴛ*  🔥   ║\n"
        "╚══════════════════════════╝\n"
        "\n"
        "  ⚡ ᴘʀᴇᴍɪᴜᴍ ᴏꜱɪɴᴛ ᴛᴏᴏʟꜱ ⚡\n"
        "\n"
        f"  💎 ᴄʀᴇᴅɪᴛꜱ: {fmt_credits(chat_id)}\n"
        "\n"
        "  📌 *ᴛᴏᴏʟ ꜱᴇʟᴇᴄᴛ ᴋᴀʀ* 👇"
    )


# ============ HANDLERS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_state.pop(chat_id, None)
    get_credits(chat_id)

    await update.message.reply_text(
        main_text(chat_id),
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    chat_id = q.message.chat_id
    user = q.from_user

    # ---- Back ----
    if data == "back":
        user_state.pop(chat_id, None)
        await q.edit_message_text(main_text(chat_id), reply_markup=main_menu(), parse_mode="Markdown")
        return

    # ---- Naya search ----
    if data == "new_search":
        user_state.pop(chat_id, None)
        await q.edit_message_text(
            "╔══════════════════════════╗\n"
            "║   🔍  *ɴᴀʏᴀ ꜱᴇᴀʀᴄʜ*   ║\n"
            "╚══════════════════════════╝\n"
            "\n"
            "  📌 *ᴛᴏᴏʟ ꜱᴇʟᴇᴄᴛ ᴋᴀʀ* 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    # ---- Profile ----
    if data == "profile":
        text = (
            "╔══════════════════════════╗\n"
            "║   💎  *ᴄʀᴇᴅɪᴛ ᴘʀᴏꜰɪʟᴇ*   ║\n"
            "╚══════════════════════════╝\n"
            "\n"
            f"  👤 ɴᴀᴀᴍ: *{user.first_name or 'Bhai'}*\n"
            f"  🆔 ɪᴅ: `{chat_id}`\n"
            f"  💎 ᴄʀᴇᴅɪᴛꜱ: {fmt_credits(chat_id)}\n"
            "\n"
            "  📩 ᴀᴜʀ ᴄʜᴀʜɪʏᴇ ᴛᴏʜ ᴀᴅᴍɪɴ ᴋᴏ ʀᴇQᴜᴇꜱᴛ ʙʜᴇᴊ"
        )
        await q.edit_message_text(text, reply_markup=profile_menu(), parse_mode="Markdown")
        return

    # ---- Request credit ----
    if data == "req_credit":
        if chat_id == ADMIN_ID:
            await q.answer("Tu khud admin hai bhai 😂", show_alert=True)
            return

        req_counter["n"] += 1
        req_id = req_counter["n"]
        pending_requests[req_id] = chat_id

        admin_text = (
            "╔══════════════════════════╗\n"
            "║   📩  *ᴄʀᴇᴅɪᴛ ʀᴇQᴜᴇꜱᴛ*   ║\n"
            "╚══════════════════════════╝\n"
            "\n"
            f"  👤 *{user.first_name or 'User'}*\n"
            f"  🆔 `{chat_id}`\n"
            f"  🔗 @{user.username or 'no_username'}\n"
            "\n"
            "  ᴀᴘᴘʀᴏᴠᴇ ᴋᴀʀ ʏᴀ ʀᴇᴊᴇᴄᴛ 👇"
        )
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ᴀᴘᴘʀᴏᴠᴇ +5", callback_data=f"appr:{req_id}"),
                InlineKeyboardButton("❌ ʀᴇᴊᴇᴄᴛ", callback_data=f"rej:{req_id}"),
            ]
        ])

        try:
            await context.bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="Markdown")
            await q.edit_message_text(
                "╔══════════════════════════╗\n"
                "║   ✅  *ʀᴇQᴜᴇꜱᴛ ꜱᴇɴᴛ*   ║\n"
                "╚══════════════════════════╝\n"
                "\n"
                "  📩 ʀᴇQᴜᴇꜱᴛ ᴀᴅᴍɪɴ ᴋᴏ ʙʜᴇᴊ ᴅɪ ɢᴀʏɪ\n"
                "  ⏳ ᴀᴘᴘʀᴏᴠᴀʟ ᴋᴀ ɪɴᴛᴇᴢᴀᴀʀ ᴋᴀʀ",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back")]]
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            await q.edit_message_text(f"❌ Error: `{e}`", parse_mode="Markdown")
        return

    # ---- Approve ----
    if data.startswith("appr:"):
        if chat_id != ADMIN_ID:
            await q.answer("Tu admin nahi hai 😏", show_alert=True)
            return
        req_id = int(data.split(":")[1])
        target = pending_requests.pop(req_id, None)
        if not target:
            await q.edit_message_text("⚠️ Ye request already handle ho gayi.")
            return
        user_credits[target] = get_credits(target) + 5
        await q.edit_message_text(f"✅ ᴀᴘᴘʀᴏᴠᴇᴅ! User `{target}` ko +5 credits.")
        try:
            await context.bot.send_message(
                target,
                "╔══════════════════════════╗\n"
                "║   🎉  *ᴀᴘᴘʀᴏᴠᴇᴅ*   ║\n"
                "╚══════════════════════════╝\n"
                "\n"
                "  💎 +5 ᴄʀᴇᴅɪᴛꜱ ᴀᴅᴅ ʜᴏ ɢᴀʏᴇ\n"
                "  /start ᴋᴀʀᴋᴇ ᴄʜᴇᴄᴋ ᴋᴀʀ",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # ---- Reject ----
    if data.startswith("rej:"):
        if chat_id != ADMIN_ID:
            await q.answer("Tu admin nahi hai 😏", show_alert=True)
            return
        req_id = int(data.split(":")[1])
        target = pending_requests.pop(req_id, None)
        if not target:
            await q.edit_message_text("⚠️ Ye request already handle ho gayi.")
            return
        await q.edit_message_text(f"❌ ʀᴇᴊᴇᴄᴛᴇᴅ request of `{target}`.")
        try:
            await context.bot.send_message(
                target,
                "╔══════════════════════════╗\n"
                "║   😔  *ʀᴇᴊᴇᴄᴛᴇᴅ*   ║\n"
                "╚══════════════════════════╝\n"
                "\n"
                "  ᴀᴅᴍɪɴ ɴᴇ ʀᴇᴊᴇᴄᴛ ᴋᴀʀ ᴅɪʏᴀ\n"
                "  ᴛʜᴏᴅɪ ᴅᴇʀ ʙᴀᴀᴅ ᴅᴏʙᴀʀᴀ ᴛʀʏ ᴋᴀʀ",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # ---- My results ----
    if data == "my_results":
        results = user_results.get(chat_id, [])
        if not results:
            await q.edit_message_text(
                "📭 ᴀʙʜɪ ᴛᴀᴋ ᴋᴏɪ ʀᴇꜱᴜʟᴛ ꜱᴀᴠᴇ ɴᴀʜɪ ʜᴜᴀ.\nᴘᴇʜʟᴇ ꜱᴇᴀʀᴄʜ ᴋᴀʀ.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back")]]
                ),
            )
            return

        buttons = []
        for i, r in enumerate(results, 1):
            label = f"{i}. {r['tool']} — {r['query']}"
            buttons.append([InlineKeyboardButton(label[:60], callback_data=f"view:{i-1}")])
        buttons.append([InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="back")])

        await q.edit_message_text(
            f"╔══════════════════════════╗\n"
            f"║   📜  *ꜱᴀᴠᴇᴅ ʀᴇꜱᴜʟᴛꜱ*   ║\n"
            f"╚══════════════════════════╝\n"
            f"\n"
            f"  ᴛᴏᴛᴀʟ: *{len(results)}*\n"
            f"  ᴋᴏɪ ᴇᴋ ᴘᴇʜ ᴄʟɪᴄᴋ ᴋᴀʀ 👇",
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
            f"╔══════════════════════════╗\n"
            f"║   {r['tool']}\n"
            f"╚══════════════════════════╝\n"
            f"\n"
            f"  🔍 Qᴜᴇʀʏ: `{r['query']}`\n"
            f"\n"
            f"```\n{r['result'][:3500]}\n```"
        )
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 ɴᴀʏᴀ ꜱᴇᴀʀᴄʜ", callback_data="new_search")],
                [InlineKeyboardButton("⬅️ ʀᴇꜱᴜʟᴛꜱ ʟɪꜱᴛ", callback_data="my_results")],
            ]),
            parse_mode="Markdown",
        )
        return

    # ---- Tool select ----
    if data.startswith("tool:"):
        tool_key = data.split(":", 1)[1]
        cfg = TOOLS.get(tool_key)
        if not cfg:
            await q.edit_message_text("❌ Tool nahi mila")
            return
        user_state[chat_id] = tool_key
        text = (
            f"╔══════════════════════════╗\n"
            f"║   {cfg['name']}\n"
            f"╚══════════════════════════╝\n"
            f"\n"
            f"  ➡️ {cfg['prompt']}\n"
            f"\n"
            f"  💎 ᴄʀᴇᴅɪᴛꜱ: {fmt_credits(chat_id)}"
        )
        await q.edit_message_text(text, parse_mode="Markdown")
        return


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tool_key = user_state.get(chat_id)

    if not tool_key:
        await update.message.reply_text(
            "👉 ᴘᴇʜʟᴇ /start ᴋᴀʀᴋᴇ ᴛᴏᴏʟ ꜱᴇʟᴇᴄᴛ ᴋᴀʀ ʙʜᴀɪ.",
            reply_markup=main_menu(),
        )
        return

    # ---- Credit check ----
    if get_credits(chat_id) <= 0:
        await update.message.reply_text(
            "╔══════════════════════════╗\n"
            "║   ⚠️  *ᴄʀᴇᴅɪᴛꜱ ᴋʜᴀᴛᴀᴍ*   ║\n"
            "╚══════════════════════════╝\n"
            "\n"
            "  💎 ᴛᴇʀᴇ ᴘᴀᴀꜱ 0 ᴄʀᴇᴅɪᴛꜱ ʙᴀᴄʜᴇ\n"
            "\n"
            "  📩 ᴀᴅᴍɪɴ ᴋᴏ ʀᴇQᴜᴇꜱᴛ ʙʜᴇᴊ 👇",
            reply_markup=no_credit_menu(),
            parse_mode="Markdown",
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

        user_results.setdefault(chat_id, []).append({
            "tool": cfg["name"],
            "query": q,
            "result": pretty,
        })
        user_results[chat_id] = user_results[chat_id][-20:]

        user_credits[chat_id] = get_credits(chat_id) - 1

        text = (
            f"╔══════════════════════════╗\n"
            f"║   ✅  {cfg['name']}\n"
            f"╚══════════════════════════╝\n"
            f"\n"
            f"  🔍 Qᴜᴇʀʏ: `{q}`\n"
            f"  💎 ᴄʀᴇᴅɪᴛꜱ: {fmt_credits(chat_id)}\n"
            f"\n"
            f"```\n{pretty}\n```"
        )

        await msg.edit_text(text, reply_markup=result_menu(), parse_mode="Markdown")

    except requests.exceptions.Timeout:
        await msg.edit_text(
            "❌ *API timeout* ʜᴏ ɢᴀʏɪ, ᴅᴏʙᴀʀᴀ ᴛʀʏ ᴋᴀʀ.",
            reply_markup=result_menu(),
            parse_mode="Markdown",
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`", parse_mode="Markdown")

    user_state.pop(chat_id, None)


# ============ ADMIN ============
async def addcredit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("❌ Tu admin nahi hai.")
        return
    try:
        uid = int(context.args[0])
        amt = int(context.args[1])
        user_credits[uid] = get_credits(uid) + amt
        await update.message.reply_text(f"✅ User `{uid}` ko +{amt} credits.", parse_mode="Markdown")
        try:
            await context.bot.send_message(uid, f"🎁 ᴀᴅᴍɪɴ ɴᴇ ᴛᴜᴊʜᴇ *+{amt} ᴄʀᴇᴅɪᴛꜱ* ᴅɪʏᴇ!", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        await update.message.reply_text("Usage: `/addcredit <user_id> <amount>`", parse_mode="Markdown")


async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Tera ID: `{update.effective_chat.id}`", parse_mode="Markdown")


# ============ MAIN ============
if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN set nahi hai")
        exit(1)
    if ADMIN_ID == 0:
        print("⚠️ ADMIN_ID set nahi hai")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("addcredit", addcredit_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🔥 Bot chalu ho raha hai...")
    app.run_polling()
