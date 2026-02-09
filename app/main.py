from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse
from time import time

from app.config import VERIFY_TOKEN
from app.state import RATE_LIMIT, SEEN_MESSAGE_IDS, cleanup_seen_ids
from app.handlers.commands import handle_command
from app.handlers.messages import handle_transaction
from app.whatsapp import send_whatsapp_message  # kalau mau pisah lagi
from app.sheets import generate_export_pdf
import os
from datetime import datetime
import io

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Bot is running"}

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


@app.get("/export/{phone}/{days}")
async def export_pdf(phone: str, days: int = 30):
    """Generate and download PDF report
    
    Example: /export/628xxxxxxxxx/30
    """
    try:
        print(f"=== Generating PDF ===")
        print(f"Phone: {phone}, Days: {days}")
        
        pdf_bytes = generate_export_pdf(phone, days)
        
        if not pdf_bytes:
            print(f"ERROR: PDF generation returned None")
            return {"error": "Failed to generate PDF", "phone": phone, "days": days}
        
        print(f"SUCCESS: Generated {len(pdf_bytes)} bytes")
        
        # Return PDF as streaming response
        pdf_buffer = io.BytesIO(pdf_bytes)
        filename = f"laporan_{phone}_{days}hari.pdf"
        
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"ERROR in export_pdf: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "type": type(e).__name__, "phone": phone, "days": days}


