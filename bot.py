import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import asyncio
import aiosqlite
import datetime

API_TOKEN = "7887971695:AAGFMEdwQmWpXZyjlmXHLWZa6qMUHso9NbY"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

rules_text = "Правила пока не заданы."
admins = set()

async def setup_db():
    global db, cursor
    db = await aiosqlite.connect("i3hdbot.db")
    cursor = await db.cursor()
    await cursor.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        user_id INTEGER,
        action TEXT,
        timestamp TEXT
    )
    """)
    await db.commit()

def is_admin(uid):
    return uid in admins

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply("Бот активен. Используй команды /info, /free, /rules и т.п.")

@dp.message_handler(commands=["addadmin", "аддадм"])
async def add_admin(message: types.Message):
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id
        admins.add(uid)
        await message.reply(f"✅ Пользователь {uid} добавлен в админы.")
    else:
        await message.reply("Ответь на сообщение пользователя, чтобы добавить его в админы.")

@dp.message_handler(commands=["rules", "правила"])
async def show_rules(message: types.Message):
    await message.reply(f"📜 Правила чата:\n{rules_text}")

@dp.message_handler(commands=["setrules", "задатьправила"])
async def set_rules(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    global rules_text
    rules_text = message.get_args()
    await message.reply("✅ Правила обновлены.")

@dp.message_handler(lambda msg: msg.text.lower() in ["/free", "free", "фри"])
async def toggle_free(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id
        await cursor.execute("SELECT * FROM actions WHERE user_id=? AND action='free_given'", (uid,))
        current = await cursor.fetchone()
        if current:
            await cursor.execute("DELETE FROM actions WHERE user_id=? AND action='free_given'", (uid,))
            await db.commit()
            await message.reply("❌ Free статус снят.")
        else:
            await cursor.execute("INSERT INTO actions (user_id, action, timestamp) VALUES (?, 'free_given', ?)",
                                 (uid, datetime.datetime.utcnow().isoformat()))
            await db.commit()
            await message.reply("✅ Free выдан.")

@dp.message_handler(commands=["info", "инфо"])
async def user_info(msg: types.Message):
    if msg.reply_to_message:
        target_user = msg.reply_to_message.from_user
    else:
        args = msg.get_args()
        if not args:
            target_user = msg.from_user
        else:
            try:
                target_user = await bot.get_chat_member(msg.chat.id, int(args)).user
            except:
                await msg.reply("Не удалось получить пользователя.")
                return

    uid = target_user.id
    await cursor.execute("SELECT COUNT(*) FROM actions WHERE user_id = ? AND action LIKE 'warn%'", (uid,))
    warn_count = (await cursor.fetchone())[0]
    await cursor.execute("SELECT COUNT(*) FROM actions WHERE user_id = ? AND action LIKE 'mute%'", (uid,))
    mute_count = (await cursor.fetchone())[0]
    await cursor.execute("SELECT action, timestamp FROM actions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (uid,))
    last_action = await cursor.fetchone()
    last_action_str = f"{last_action[0]} в {last_action[1]}" if last_action else "Нет"
    await cursor.execute("SELECT action FROM actions WHERE user_id = ? AND action='free_given'", (uid,))
    is_free = await cursor.fetchone() is not None

    await msg.reply(
        f"📊 Информация о пользователе <b>{target_user.full_name}</b> [<code>{uid}</code>]:\n"
        f"🔹 Варны: <b>{warn_count}</b>\n"
        f"🔸 Муты: <b>{mute_count}</b>\n"
        f"💠 Free: {'✅' if is_free else '❌'}\n"
        f"🕓 Последнее действие: <b>{last_action_str}</b>",
        parse_mode="HTML"
    )

async def on_startup(dp):
    await setup_db()

if __name__ == "__main__":
    async def main():
        await setup_db()
        await dp.start_polling(bot)

    asyncio.run(main())
