"""FastAPI application setup dan route handlers.

Modul ini menghandle:
- WhatsApp webhook listener untuk incoming messages
- Command dan transaction routing
- PDF export endpoint
- Health check endpoints
- Background scheduler untuk daily auto reports (FEATURE 2)
"""

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse
from time import time
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import VERIFY_TOKEN
from app.state import RATE_LIMIT, SEEN_MESSAGE_IDS, cleanup_seen_ids
from app.handlers.commands import handle_command
from app.handlers.messages import handle_transaction
from app.whatsapp import send_whatsapp_message
from app.sheets import generate_export_pdf, get_all_user_phones, get_daily_summary
import os
from datetime import datetime
import io

app = FastAPI()

# ===========================
# FEATURE 2: DAILY AUTO REPORT SCHEDULER
# Fitur untuk mengirim ringkasan pengeluaran otomatis setiap hari
# ===========================

scheduler = BackgroundScheduler()

def send_daily_reports():
    """Background job yang berjalan setiap hari pada jam yang ditentukan.
    
    Fungsi ini:
    1. Ambil semua user yang pernah transaksi
    2. Generate summary untuk masing-masing user
    3. Kirim via WhatsApp secara otomatis
    
    Notes:
    - Jika ada error pada user tertentu, continue ke user berikutnya
    - Error logged tapi tidak menghentikan job
    - Dipanggil otomatis oleh APScheduler setiap hari jam 21:00 UTC
    """
    try:
        # Ambil semua nomor user yang active
        phones = get_all_user_phones()
        print(f"[SCHEDULER] Starting daily report job for {len(phones)} users")
        
        # Kirim report ke setiap user
        for phone in phones:
            try:
                # Generate summary khusus untuk user ini
                summary = get_daily_summary(phone)
                if summary:
                    # Kirim via WhatsApp
                    send_whatsapp_message(phone, summary)
                    print(f"[SCHEDULER] OK Daily report sent to {phone}")
                else:
                    print(f"[SCHEDULER] SKIP No summary for {phone}")
            except Exception as e:
                print(f"[SCHEDULER] ERR {phone}: {e}")
    except Exception as e:
        print(f"[SCHEDULER] FATAL: {e}")

# Schedule daily report at 21:00 UTC (9 PM Jakarta time = 02:00 next day)
scheduler.add_job(
    send_daily_reports, 
    'cron', 
    hour=21,
    minute=0,
    id='daily_report',
    name='Daily Report Job'
)

@app.on_event("startup")
async def startup_event():
    """Dijalankan saat aplikasi start (deployment atau restart).
    
    Tugas:
    - Start APScheduler background scheduler
    - Scheduler akan mulai menjalankan scheduled jobs
    """
    try:
        scheduler.start()
        print("[SCHEDULER] OK Background scheduler started")
        print("[SCHEDULER] Daily reports at 21:00 UTC")
    except Exception as e:
        print(f"[SCHEDULER] ERR startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Dijalankan saat aplikasi shutdown atau restart.
    
    Tugas:
    - Stop APScheduler dengan graceful shutdown
    - Ensure tidak ada zombie processes
    """
    try:
        scheduler.shutdown()
        print("[SCHEDULER] OK Background scheduler stopped")
    except Exception as e:
        print(f"[SCHEDULER] ERR shutdown: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint - verifikasi bot masih berjalan."""
    return {"status": "ok", "message": "Bot is running"}

@app.get("/config")
async def config_check():
    """Debug config endpoint - lihat konfigurasi APP_BASE_URL."""
    from app.config import APP_BASE_URL
    return {
        "status": "ok",
        "app_base_url": APP_BASE_URL,
        "example_export_url": f"{APP_BASE_URL}/export/6282210401127/30"
    }

@app.post("/webhook")
async def webhook(request: Request):
    """WhatsApp webhook listener - menerima dan memproses incoming messages.
    
    Flow:
    1. Terima JSON dari WhatsApp Cloud API
    2. Extract nomor pengirim (phone), text message, message ID
    3. Anti-duplicate check via SEEN_MESSAGE_IDS
    4. Route ke /command handler atau /transaction handler
    5. Return status response ke WhatsApp
    """
    try:
        data = await request.json()
        msg = data["entry"][0]["changes"][0]["value"].get("messages")
        if not msg:
            return {"status": "ok"}

        msg = msg[0]
        phone = msg["from"]
        text = msg["text"]["body"].lower().strip()
        message_id = msg["id"]

        # Cleanup old seen message IDs dan cek duplicate
        now = time()
        cleanup_seen_ids(now)

        if message_id in SEEN_MESSAGE_IDS:
            return {"status": "ok"}  # Duplicate, ignore
        SEEN_MESSAGE_IDS[message_id] = now

        # Try command handler first
        if handle_command(text, phone, send_whatsapp_message):
            return {"status": "ok"}

        # If not command, handle as transaction
        handle_transaction(text, phone, message_id, send_whatsapp_message)
        return {"status": "ok"}
    except Exception as e:
        print(f"[Webhook] Error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/export/{phone}/{days}")
async def export_pdf(phone: str, days: int = 30):
    """Generate dan download PDF laporan transaksi.
    
    Endpoint ini:
    1. Generate PDF report untuk periode N hari terakhir
    2. Return sebagai downloadable file dengan proper headers
    3. Filename format: laporan_{phone}_{days}hari.pdf
    
    Args:
        phone (str): Nomor WhatsApp user
        days (int): Jumlah hari (default: 30)
    
    Example URLs:
    /export/6282210401127/30  -> 30 hari terakhir
    /export/6282210401127/7   -> 7 hari terakhir
    
    Returns:
        PDF file sebagai StreamingResponse (untuk download)
        atau JSON error jika ada masalah
    """
    try:
        print(f"[Export] Generating report - Phone: {phone}, Days: {days}")
        
        # Panggil sheet function untuk generate PDF
        pdf_bytes = generate_export_pdf(phone, days)
        
        # Validation: PDF generation failed
        if pdf_bytes is None:
            print(f"[Export] ERROR: PDF generation returned None")
            return {
                "error": "Failed to generate PDF - no data or internal error",
                "phone": phone,
                "days": days
            }
        
        # Validation: PDF bytes invalid
        if not isinstance(pdf_bytes, bytes) or len(pdf_bytes) == 0:
            print(f"[Export] ERROR: PDF bytes invalid")
            return {
                "error": "PDF generation failed - invalid output",
                "phone": phone,
                "days": days,
                "bytes_received": len(pdf_bytes) if pdf_bytes else 0
            }
        
        print(f"[Export] OK PDF ready - {len(pdf_bytes)} bytes")
        
        # Set filename untuk download
        filename = f"laporan_{phone}_{days}hari.pdf"
        
        # Return PDF as StreamingResponse dengan proper headers
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"[Export] FATAL: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        print(error_trace)
        return {
            "error": str(e),
            "type": type(e).__name__,
            "phone": phone,
            "days": days,
            "trace": error_trace[:300]
        }


