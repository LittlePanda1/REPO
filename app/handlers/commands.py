from app.sheets import (
    summarize_today_by_phone,
    summarize_week_by_phone,
    summarize_month_by_phone,
    get_last_transaction_row_by_phone,
    delete_row,
)

def handle_command(text, phone, send):
    if text == "/undo":
        row = get_last_transaction_row_by_phone(phone)
        if not row:
            send(phone, "⚠️ Tidak ada transaksi yang bisa di-undo.")
            return True

        delete_row(row)
        send(phone, "🗑️ Transaksi terakhir berhasil dihapus.")
        return True

    if text == "/summary":
        income, expense, net = summarize_today_by_phone(phone)
        send(phone, f"📊 Hari ini\nIncome: {income}\nExpense: {expense}\nNet: {net}")
        return True

    if text == "/weekly":
        income, expense, net, _ = summarize_week_by_phone(phone)
        send(phone, f"📊 Mingguan\nIncome: {income}\nExpense: {expense}\nNet: {net}")
        return True

    if text == "/monthly":
        income, expense, net, _ = summarize_month_by_phone(phone)
        send(phone, f"📊 Bulanan\nIncome: {income}\nExpense: {expense}\nNet: {net}")
        return True

    return False
