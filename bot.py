import asyncio
import os
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ---------------- CONFIG ---------------- #

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in Railway Variables!")

ADMIN_ID = 6143033648

CARD_NUMBER = "6219861953148185"
CARD_NAME = "محمد مهدی همیانی"

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

DB = "bot.db"

# ---------------- DB ---------------- #

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            wallet INTEGER DEFAULT 0
        )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT wallet FROM users WHERE user_id=?",
            (user_id,)
        )
        row = await cur.fetchone()

        if not row:
            await db.execute(
                "INSERT INTO users (user_id, wallet) VALUES (?, ?)",
                (user_id, 0)
            )
            await db.commit()
            return 0

        return row[0]

async def add_wallet(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET wallet = wallet + ? WHERE user_id=?",
            (amount, user_id)
        )
        await db.commit()

# ---------------- KEYBOARDS ---------------- #

main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🪙 جم ها", callback_data="coins")],
    [InlineKeyboardButton(text="🎁 بسته پیشنهادی", callback_data="pack")],
    [InlineKeyboardButton(text="💰 کیف پول", callback_data="wallet")],
    [InlineKeyboardButton(text="📞 پشتیبانی", url="https://t.me/mohamadhamiani")]
])

coins_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="200 جم - 110k", callback_data="buy_110000_200")],
    [InlineKeyboardButton(text="525 جم - 200k", callback_data="buy_200000_525")],
    [InlineKeyboardButton(text="1125 جم - 350k", callback_data="buy_350000_1125")],
    [InlineKeyboardButton(text="2350 جم - 650k", callback_data="buy_650000_2350")],
    [InlineKeyboardButton(text="6250 جم - 1.6M", callback_data="buy_1600000_6250")]
])

wallet_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="charge")]
])

admin_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ تایید", callback_data="approve"),
        InlineKeyboardButton(text="❌ رد", callback_data="reject")
    ]
])

# ---------------- START ---------------- #

@dp.message(CommandStart())
async def start(msg: Message):
    await get_user(msg.from_user.id)

    await msg.answer(
        "🎉 به ربات خرید جم ایران OSM خوش آمدید 💎\n\nاز منو انتخاب کن 👇",
        reply_markup=main_kb
    )

# ---------------- MENU ---------------- #

@dp.callback_query(F.data == "coins")
async def coins(c: CallbackQuery):
    await c.message.edit_text("🪙 انتخاب جم:", reply_markup=coins_kb)

@dp.callback_query(F.data == "wallet")
async def wallet(c: CallbackQuery):
    bal = await get_user(c.from_user.id)
    await c.message.edit_text(f"💰 موجودی شما: {bal:,} تومان", reply_markup=wallet_kb)

@dp.callback_query(F.data == "pack")
async def pack(c: CallbackQuery):
    await c.message.answer(
        "🎁 بسته پیشنهادی:\n\n"
        "525 جم + 6M$ + تغییر جایگاه\n"
        "💵 قیمت: 500,000 تومان\n\n"
        f"<code>{CARD_NUMBER}</code>\n{CARD_NAME}"
    )

# ---------------- BUY ---------------- #

@dp.callback_query(F.data.startswith("buy_"))
async def buy(c: CallbackQuery):
    _, price, gems = c.data.split("_")

    await c.message.answer(
        f"""
🧾 سفارش شما

🪙 جم: {gems}
💵 قیمت: {int(price):,} تومان

💳 کارت:
<code>{CARD_NUMBER}</code>
👤 {CARD_NAME}

📸 بعد از پرداخت رسید بفرست
"""
    )

# ---------------- CHARGE ---------------- #

@dp.callback_query(F.data == "charge")
async def charge(c: CallbackQuery):
    await c.message.answer(
        f"""
💰 شارژ کیف پول

💳 کارت:
<code>{CARD_NUMBER}</code>

📸 رسید بفرست
"""
    )

# ---------------- RECEIPT ---------------- #

pending = {}

@dp.message(F.photo)
async def receipt(msg: Message):
    pending[msg.from_user.id] = msg.photo[-1].file_id

    await bot.send_photo(
        ADMIN_ID,
        msg.photo[-1].file_id,
        caption=f"""
📥 رسید جدید

👤 {msg.from_user.full_name}
🆔 {msg.from_user.id}
""",
        reply_markup=admin_kb
    )

    await msg.answer("⏳ رسید ارسال شد")

# ---------------- ADMIN ---------------- #

@dp.callback_query(F.data == "approve")
async def approve(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return

    await c.message.answer("💰 مقدار و آیدی را وارد کن (مثال: 50000 123456789)")

@dp.message(F.text.regexp(r"^\d+ \d+$"))
async def add_balance(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    amount, user_id = map(int, msg.text.split())

    await add_wallet(user_id, amount)

    await bot.send_message(
        user_id,
        f"💰 کیف پول شما شارژ شد\n{amount:,} تومان 🎉"
    )

    await msg.answer("✅ انجام شد")

# ---------------- RUN ---------------- #

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    print("BOT RUNNING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
