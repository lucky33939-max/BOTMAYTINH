import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ===== INIT =====
app = FastAPI()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== IMPORT DB =====
from db import (
    init_db,
    add_transaction,
    get_transactions,
    get_trial_code,
    has_claimed_free_trial,
    mark_claimed_free_trial
)

# ===== BASIC ROUTE =====
@app.get("/")
def home():
    return {"status": "ok"}

# ===== WEBHOOK =====
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        update = Update.model_validate(data)

        try:
            await dp.feed_update(bot, update)
        except Exception:
            import traceback
            print("❌ HANDLER ERROR:")
            traceback.print_exc()

        return JSONResponse({"ok": True})

    except Exception:
        import traceback
        print("❌ WEBHOOK ERROR:")
        traceback.print_exc()
        return JSONResponse({"ok": False})


# ===== HANDLERS =====

@dp.message()
async def handle_all(m: types.Message):
    try:
        text = m.text or ""

        # ===== TEST =====
        if text.lower() == "ping":
            await m.reply("pong")
            return

        # ===== TRIAL =====
        if text.startswith("/trial"):
            code = text.replace("/trial", "").strip()

            real_code = (get_trial_code() or "").strip()

            if not code:
                await m.reply("❌ Nhập mã trial")
                return

            if code != real_code:
                await m.reply("❌ Sai mã")
                return

            if has_claimed_free_trial(m.from_user.id):
                await m.reply("❌ Bạn đã dùng rồi")
                return

            mark_claimed_free_trial(m.from_user.id)

            await m.reply("✅ Nhận trial thành công")
            return

        # ===== FAKE TRANSACTION =====
        if text.startswith("+"):
            amount = float(text.replace("+", "").strip())

            add_transaction(
                chat_id=m.chat.id,
                user_id=m.from_user.id,
                username=m.from_user.username or "",
                display_name=m.from_user.full_name,
                target_name="test",
                kind="in",
                raw_amount=amount,
                unit_amount=amount,
                rate_used=1,
                fee_used=0,
                note="manual",
                original_text=text
            )

            await m.reply(f"✅ Đã cộng {amount}")
            return

        if text == "/list":
            rows = get_transactions(m.chat.id)

            if not rows:
                await m.reply("❌ Không có dữ liệu")
                return

            msg = "📊 Giao dịch:\n"

            for r in rows[-10:]:
                msg += f"{r[4]} | {r[6]} | {r[7]}\n"

            await m.reply(msg)
            return

    except Exception:
        import traceback
        print("❌ MESSAGE ERROR:")
        traceback.print_exc()


# ===== BACKGROUND TASK =====
async def auto_check_payments():
    while True:
        try:
            print("🔄 checking payments...")
        except Exception:
            import traceback
            traceback.print_exc()

        await asyncio.sleep(10)


# ===== STARTUP =====
@app.on_event("startup")
async def on_startup():
    print("🚀 Starting app...")

    # init DB
    init_db()

    # set webhook
    await bot.set_webhook(WEBHOOK_URL)

    # run background
    asyncio.create_task(auto_check_payments())


# ===== LOCAL RUN (OPTIONAL) =====
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
