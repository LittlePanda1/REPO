"""Handler untuk transaksi reguler (non-command messages).

Modul ini menangani:
- Parsing input transaksi dari user (contoh: "makan 25000")
- Menyimpan transaksi ke Google Sheets
- Trigger automatic alerts (budget exceeded, daily target exceeded)
"""

from app.parser import parse_message
from app.sheets import (
    insert_transaction, 
    has_message_id, 
    check_budget_exceeded, 
    check_daily_target_exceeded
)


def handle_transaction(text, phone, message_id, send):
    """Handle regular transaction input dari user (bukan command).
    
    Flow:
    1. Parse input text menjadi struktur (kategori, amount, tipe)
    2. Simpan ke database jika belum pernah (anti-duplicate via message_id)
    3. Kirim konfirmasi ke user
    4. Check budget alerts (FEATURE 1)
    5. Check daily/weekly target alerts (FEATURE 4)
    
    Args:
        text (str): Input dari user (misal: "makan 25000" atau "gaji 5000000")
        phone (str): Nomor WhatsApp user
        message_id (str): Unique ID dari WhatsApp untuk anti-duplicate
        send (function): Fungsi untuk mengirim pesan balik ke user
    
    Returns:
        None (result hanya via send() callback)
    """
    try:
        # Parse input text menjadi struktur data
        parsed = parse_message(text)
        if not parsed:
            send(phone, "❌ Format tidak dikenali. Contoh: Makan siang 25000")
            return

        # Simpan transaksi hanya jika belum pernah diproses sebelumnya
        if not has_message_id(message_id):
            insert_transaction(phone, parsed, message_id)

        # Kirim konfirmasi kesuksesan
        send(phone, f"✅ {parsed['category']} {parsed['amount']} dicatat")
        
        # ========== FEATURE 1: BUDGET ALERT OTOMATIS ==========
        # Kirim alert jika pengeluaran melebihi budget kategori
        if parsed["type"] == "expense":
            budget_alert = check_budget_exceeded(
                phone, 
                parsed["category"], 
                parsed["amount"]
            )
            
            # Hanya send alert jika budget terlampaui
            if budget_alert and budget_alert["exceeded"]:
                overage = budget_alert["new_total"] - budget_alert["budget"]
                alert_msg = (
                    f"⚠️ BUDGET ALERT\n"
                    f"Kategori: {parsed['category']}\n"
                    f"Budget: Rp {budget_alert['budget']:,.0f}\n"
                    f"Spent: Rp {budget_alert['new_total']:,.0f}\n"
                    f"Over: Rp {overage:,.0f}"
                )
                send(phone, alert_msg)
        
        # ========== FEATURE 4: SMART NOTIFICATION - Daily Target ==========
        # Kirim alert jika pengeluaran harian melebihi target
        if parsed["type"] == "expense":
            daily_alert = check_daily_target_exceeded(phone)
            
            # Hanya send alert jika daily target terlampaui
            if daily_alert and daily_alert["exceeded"]:
                alert_msg = (
                    f"⚠️ DAILY TARGET EXCEEDED\n"
                    f"Target: Rp {daily_alert['target']:,.0f}\n"
                    f"Spent: Rp {daily_alert['spent']:,.0f}\n"
                    f"Over: Rp {daily_alert['over_by']:,.0f}"
                )
                send(phone, alert_msg)
                
    except Exception as e:
        print(f"[Transaction Handler] Error: {e}")
        send(phone, "❌ Terjadi error saat mencatat transaksi.")
