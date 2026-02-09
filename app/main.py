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
        
        if pdf_bytes is None:
            print(f"ERROR: PDF generation returned None")
            return {
                "error": "Failed to generate PDF - no data or internal error",
                "phone": phone,
                "days": days,
                "detail": "Check if you have transactions"
            }
        
        if isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 0:
            print(f"SUCCESS: Generated {len(pdf_bytes)} bytes")
            filename = f"laporan_{phone}_{days}hari.pdf"
            
            return StreamingResponse(
                iter([pdf_bytes]),
                media_type='application/pdf',
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            print(f"ERROR: PDF bytes invalid - type: {type(pdf_bytes)}, len: {len(pdf_bytes) if pdf_bytes else 0}")
            return {
                "error": "PDF generation failed - invalid output",
                "phone": phone,
                "days": days
            }
        
    except Exception as e:
        print(f"ERROR in export_pdf: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        print(error_trace)
        return {
            "error": str(e),
            "type": type(e).__name__,
            "phone": phone,
            "days": days,
            "trace": error_trace[:500]  # First 500 chars of trace
        }


