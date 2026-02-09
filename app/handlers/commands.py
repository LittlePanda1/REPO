from app.sheets import (
    summarize_today_by_phone,
    summarize_week_by_phone,
    summarize_month_by_phone,
    get_last_transaction_row_by_phone,
    delete_row,
    # Fitur baru
    set_budget,
    get_budget,
    get_all_budgets,
    set_spending_target,
    get_spending_target,
    get_category_breakdown,
    get_income_expense_ratio,
    search_transactions,
    add_recurring,
    get_recurring,
)
import re


def parse_command_args(text: str) -> list:
    """Parse command arguments dari text"""
    parts = text.split()
    return parts[1:] if len(parts) > 1 else []


def format_currency(amount: int) -> str:
    """Format angka ke currency (Rupiah)"""
    return f"Rp {amount:,.0f}"


def handle_command(text, phone, send):
    try:
        # Original commands
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
            send(phone, f"📊 Hari ini\nIncome: {format_currency(income)}\nExpense: {format_currency(expense)}\nNet: {format_currency(net)}")
            return True

        if text == "/weekly":
            income, expense, net, _ = summarize_week_by_phone(phone)
            send(phone, f"📊 Mingguan\nIncome: {format_currency(income)}\nExpense: {format_currency(expense)}\nNet: {format_currency(net)}")
            return True

        if text == "/monthly":
            income, expense, net, _ = summarize_month_by_phone(phone)
            send(phone, f"📊 Bulanan\nIncome: {format_currency(income)}\nExpense: {format_currency(expense)}\nNet: {format_currency(net)}")
            return True

        # =========== FITUR #1: BUDGET ALERT ===========
        if text.startswith("/setbudget "):
            args = parse_command_args(text)
            if len(args) < 2:
                send(phone, "❌ Format: /setbudget {kategori} {amount}\nContoh: /setbudget makan 500000")
                return True
            
            category = args[0]
            try:
                amount = int(args[1])
                if set_budget(phone, category, amount):
                    send(phone, f"✅ Budget {category} set ke {format_currency(amount)}")
                else:
                    send(phone, "❌ Gagal set budget")
                return True
            except ValueError:
                send(phone, "❌ Amount harus angka")
                return True

        if text.startswith("/budget "):
            args = parse_command_args(text)
            if len(args) < 1:
                send(phone, "❌ Format: /budget {kategori}\nContoh: /budget makan")
                return True
            
            category = args[0]
            budget = get_budget(phone, category)
            if budget > 0:
                send(phone, f"💰 Budget {category}: {format_currency(budget)}")
            else:
                send(phone, f"❌ Tidak ada budget untuk {category}. Gunakan /setbudget untuk membuat.")
            return True

        if text == "/budgets":
            budgets = get_all_budgets(phone)
            if not budgets:
                send(phone, "❌ Belum ada budget yang di-set. Gunakan /setbudget")
                return True
            
            msg = "💰 Daftar Budget Anda:\n"
            for category, amount in budgets.items():
                msg += f"• {category}: {format_currency(amount)}\n"
            send(phone, msg)
            return True

        # =========== FITUR #2: SPENDING TARGET ===========
        if text.startswith("/target "):
            args = parse_command_args(text)
            if len(args) < 2:
                send(phone, "❌ Format: /target {daily|weekly} {amount}\nContoh: /target daily 200000")
                return True
            
            target_type = args[0].lower()
            if target_type not in ["daily", "weekly"]:
                send(phone, "❌ Type harus 'daily' atau 'weekly'")
                return True
            
            try:
                amount = int(args[1])
                if set_spending_target(phone, target_type, amount):
                    send(phone, f"✅ Target {target_type} set ke {format_currency(amount)}")
                else:
                    send(phone, "❌ Gagal set target")
                return True
            except ValueError:
                send(phone, "❌ Amount harus angka")
                return True

        # =========== FITUR #3: CATEGORY BREAKDOWN ===========
        if text.startswith("/breakdown"):
            args = parse_command_args(text)
            days = 30  # default 30 hari
            
            if args:
                try:
                    days = int(args[0])
                except ValueError:
                    send(phone, "❌ Format: /breakdown [hari]\nContoh: /breakdown 7")
                    return True
            
            breakdown = get_category_breakdown(phone, days)
            if not breakdown:
                send(phone, f"❌ Tidak ada pengeluaran dalam {days} hari terakhir")
                return True
            
            msg = f"📊 Breakdown Pengeluaran ({days} hari):\n"
            total = 0
            for category, amount in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                msg += f"• {category}: {format_currency(amount)}\n"
                total += amount
            msg += f"\nTotal: {format_currency(total)}"
            send(phone, msg)
            return True

        # =========== FITUR #5: INCOME vs EXPENSE RATIO ===========
        if text.startswith("/ratio"):
            args = parse_command_args(text)
            days = 30  # default 30 hari
            
            if args:
                try:
                    days = int(args[0])
                except ValueError:
                    send(phone, "❌ Format: /ratio [hari]\nContoh: /ratio 30")
                    return True
            
            ratio = get_income_expense_ratio(phone, days)
            if not ratio:
                send(phone, "❌ Tidak ada data")
                return True
            
            msg = f"📈 Financial Ratio ({days} hari):\n"
            msg += f"Income: {format_currency(ratio['income'])}\n"
            msg += f"Expense: {format_currency(ratio['expense'])}\n"
            msg += f"Saved: {format_currency(ratio['saved'])}\n"
            msg += f"Saving Rate: {ratio['saving_rate']}%"
            send(phone, msg)
            return True

        # =========== FITUR #6: TRANSACTION HISTORY SEARCH ===========
        if text.startswith("/history"):
            args = parse_command_args(text)
            category = None
            days = 30
            
            if args:
                if args[0].isdigit():
                    days = int(args[0])
                else:
                    category = args[0]
                    if len(args) > 1 and args[1].isdigit():
                        days = int(args[1])
            
            transactions = search_transactions(phone, category, days)
            if not transactions:
                send(phone, f"❌ Tidak ada transaksi ditemukan")
                return True
            
            # Limit to last 10 transactions
            transactions = transactions[:10]
            msg = f"📜 History Transaksi (terakhir {len(transactions)}):\n"
            for tx in transactions:
                msg += f"• {tx['category']} {format_currency(tx['amount'])} ({tx['type']})\n"
                msg += f"  {tx['note']}\n"
            send(phone, msg)
            return True

        # =========== FITUR #7: RECURRING TRANSACTIONS ===========
        if text.startswith("/setrecurring "):
            args = parse_command_args(text)
            if len(args) < 3:
                send(phone, "❌ Format: /setrecurring {kategori} {amount} {daily|weekly|monthly} [note]\nContoh: /setrecurring listrik 300000 monthly")
                return True
            
            category = args[0]
            frequency = args[2].lower()
            
            if frequency not in ["daily", "weekly", "monthly"]:
                send(phone, "❌ Frequency harus 'daily', 'weekly', atau 'monthly'")
                return True
            
            try:
                amount = int(args[1])
                note = " ".join(args[3:]) if len(args) > 3 else f"Recurring {category}"
                
                if add_recurring(phone, category, amount, frequency, note):
                    send(phone, f"✅ Recurring {frequency} untuk {category} {format_currency(amount)} berhasil ditambah")
                else:
                    send(phone, "❌ Gagal menambah recurring transaction")
                return True
            except ValueError:
                send(phone, "❌ Amount harus angka")
                return True

        if text == "/recurring":
            recurring = get_recurring(phone)
            if not recurring:
                send(phone, "❌ Belum ada recurring transaction")
                return True
            
            msg = "🔄 Daftar Recurring Transaction:\n"
            for i, item in enumerate(recurring, 1):
                msg += f"{i}. {item['category']} {format_currency(item['amount'])} ({item['frequency']})\n"
            send(phone, msg)
            return True

        return False
    except Exception as e:
        print(f"Error handling command: {e}")
        send(phone, "❌ Terjadi error saat memproses perintah Anda.")
        return True
