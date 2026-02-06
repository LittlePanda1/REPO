from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os

from app.parser import parse_message
from app.sheets import insert_transaction, summarize_today_by_phone, has_message_id
from app.config import VERIFY_TOKEN
from time import time
RATE_LIMIT = {}



WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

app = FastAPI()


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")
       

        if not messages:
            return {"status": "ok"}

        from_number = messages[0]["from"]
        text = messages[0]["text"]["body"]
        text_lower = text.lower().strip()
        message_id = messages[0]["id"]
        now = time()
        last = RATE_LIMIT.get(from_number, 0)

        # ===== RATE LIMIT =====
        if now - last < 2:
            return {"status": "ok"}
        RATE_LIMIT[from_number] = now
        
        if has_message_id(message_id):
          return {"status": "ok"}

        # ===== COMMANDS =====
        if text_lower == "/summary":
            income, expense, net = summarize_today_by_phone(from_number)
            send_whatsapp_message(
                to=from_number,
                message=(
                    f"📊 Ringkasan Hari Ini\n"
                    f"Income: {income}\n"
                    f"Expense: {expense}\n"
                    f"Net: {net}"
                )
            )
            return {"status": "ok"}

        if text_lower == "/chart":
            send_whatsapp_message(
                to=from_number,
                message=(
                    "📈 Lihat chart di Google Sheets:\n"
                    "https://docs.google.com/spreadsheets/d/1mWOvHMEgjaiELA4moQeZLQipqMYG_K5MQFXcqcMUFpo/edit?gid=860588708#gid=860588708"
                )
            )
            return {"status": "ok"}

        # ===== TRANSACTION PARSER =====
        parsed = parse_message(text)

        if not parsed:
            send_whatsapp_message(
                to=from_number,
                message="❌ Format tidak dikenali. Contoh: Makan siang 25000"
            )
            return {"status": "ok"}

        insert_transaction(from_number, parsed, message_id)

        send_whatsapp_message(
            to=from_number,
            message=f"✅ {parsed['category']} {parsed['amount']} dicatat"
        )

    except Exception as e:
        print("ERROR:", e)

    return {"status": "ok"}


def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message},
    }

    r = requests.post(url, headers=headers, json=payload)
    print("SEND STATUS:", r.status_code, r.text)