from app.parser import parse_message
from app.sheets import insert_transaction, has_message_id

def handle_transaction(text, phone, message_id, send):
    try:
        parsed = parse_message(text)
        if not parsed:
            send(phone, "❌ Format tidak dikenali. Contoh: Makan siang 25000")
            return

        if not has_message_id(message_id):
            insert_transaction(phone, parsed, message_id)

        send(phone, f"✅ {parsed['category']} {parsed['amount']} dicatat")
    except Exception as e:
        print(f"Error handling transaction: {e}")
        send(phone, "❌ Terjadi error saat mencatat transaksi.")
