from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from time import time

from app.config import VERIFY_TOKEN
from app.state import RATE_LIMIT, SEEN_MESSAGE_IDS, cleanup_seen_ids
from app.handlers.commands import handle_command
from app.handlers.messages import handle_transaction
from app.whatsapp import send_whatsapp_message  # kalau mau pisah lagi

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        msg = data["entry"][0]["changes"][0]["value"].get("messages")
        if not msg:
            return {"status": "ok"}

        msg = msg[0]
        phone = msg["from"]
        text = msg["text"]["body"].lower().strip()
        message_id = msg["id"]

        now = time()
        cleanup_seen_ids(now)

        if message_id in SEEN_MESSAGE_IDS:
            return {"status": "ok"}
        SEEN_MESSAGE_IDS[message_id] = now

        if handle_command(text, phone, send_whatsapp_message):
            return {"status": "ok"}

        handle_transaction(text, phone, message_id, send_whatsapp_message)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}
