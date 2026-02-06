from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os
from app.parser import parse_message
from app.sheets import insert_transaction



from app.config import VERIFY_TOKEN

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

        parsed = parse_message(text)

        if not parsed:
            send_whatsapp_message(
                to=from_number,
                message="❌ Format tidak dikenali. Contoh: Makan siang 25000"
            )
            return {"status": "ok"}

        insert_transaction(from_number, parsed)

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
