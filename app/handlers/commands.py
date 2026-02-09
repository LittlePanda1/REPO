"""Command handler untuk semua slash commands di WhatsApp bot.

Modul ini menangani:
- Parse dan route semua /command yang dikirim user
- Format dan send reply messages
- Business logic untuk setiap command (summary, budget, goals, dll)

Daftar Commands:
- /summary, /weekly, /monthly - Ringkasan finansial
- /setbudget, /budget, /budgets - Budget management
- /target - Spending target
- /goal, /goals - Goal tracking (FEATURE 3)
- /dalert, /walert - Smart notifications (FEATURE 4)
- /breakdown, /ratio, /history - Expense analysis
- /setrecurring, /recurring - Recurring transactions
- /export - PDF export
- /undo - Delete last transaction
- /help - Command list
"""

from app.sheets import (
    summarize_today_by_phone,
    summarize_week_by_phone,
    summarize_month_by_phone,
    get_last_transaction_row_by_phone,
    delete_row,
    # Budget & Target
    set_budget,
    get_budget,
    get_all_budgets,
    set_spending_target,
    get_spending_target,
    # Analysis
    get_category_breakdown,
    get_income_expense_ratio,
    search_transactions,
    # Recurring
    add_recurring,
    get_recurring,
    # Export
    generate_export_pdf,
    # Feature 3: Goals
    set_goal,
    get_goal,
    get_goal_progress,
    get_all_goals,
    # Feature 4: Smart Notifications
    check_daily_target_exceeded,
    check_weekly_target_exceeded,
)
from app.config import APP_BASE_URL
import re
import base64


def parse_command_args(text: str) -> list:
    """Parse arguments dari command text.
    
    Contoh:
    - Input: "/setbudget makan 500000"
    - Output: ['makan', '500000']
    
    Args:
        text (str): Command text dari user
    
    Returns:
        list: List of arguments setelah command name dihilangkan
    """
    parts = text.split()
    return parts[1:] if len(parts) > 1 else []


def format_currency(amount: int) -> str:
    """Format angka ke format currency Rupiah yang mudah dibaca.
    
    Contoh:
    - 25000 -> "Rp 25,000"
    - 1500000 -> "Rp 1,500,000"
    - 10000000 -> "Rp 10,000,000"
    
    Args:
        amount (int): Jumlah dalam Rupiah
    
    Returns:
        str: Format "Rp X,XXX,XXX" dengan separator comma
    """
    return f"Rp {amount:,.0f}"


def handle_command(text, phone, send):
    """Parse dan handle semua slash commands.
    
    Args:
        text (str): Command text dari user
        phone (str): Nomor WhatsApp user
        send (function): Callback function untuk send messages
    
    Returns:
        bool: True jika command berhasil dihandle, False jika text bukan command
    """
    try:
        # ========== /help ==========
        if text == "/help":
            help_text = """� *MENU PERINTAH BOT KEUANGAN*

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
📊 *RINGKASAN FINANSIAL*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/summary - Ringkasan hari ini
/weekly - Ringkasan minggu lalu
/monthly - Ringkasan bulan lalu

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
💰 *BUDGET & TARGET*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/setbudget {kategori} {jumlah}
/budget {kategori}
/budgets - Lihat semua budget
/target {daily|weekly} {jumlah}

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
🎯 *GOAL & TRACKING*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/goal {kategori} {jumlah} - Simpan goal
/goals - Lihat progress semua goal

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
⚠️ *NOTIFIKASI OTOMATIS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/dalert - Status daily target
/walert - Status weekly target

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
📈 *ANALISIS PENGELUARAN*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/breakdown [{hari}] - Per kategori
/ratio [{hari}] - Income vs Expense
/history [{kategori}] - Cari transaksi

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
🔄 *TRANSAKSI OTOMATIS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/setrecurring {kat} {jml} {freq}
/recurring - Lihat daftar

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
📄 *EXPORT & UNDO*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/export [{hari}] - Download PDF
/undo - Hapus transaksi terakhir

*━━━━━━━━━━━━━━━━━━━━━━━━━━━━*
💵 *FORMAT INPUT TRANSAKSI*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tanpa perintah (hanya ketik):

makan 25000
gaji 10000000
bensin 100000 catatan perjalanan

✨ Bot otomatis alert jika:
  • Budget kategori melebihi
  • Daily/weekly target terlampaui
  • Recurring transaksi jatuh tempo

_Ketik /help lagi untuk update_"""
            send(phone, help_text)
            return True

        # ========== /undo ==========
        if text == "/undo":
            row = get_last_transaction_row_by_phone(phone)
            if not row:
                send(phone, "⚠️ Tidak ada transaksi yang bisa di-undo.")
                return True
            
            delete_row(row)
            send(phone, f"✅ Transaksi {row[3]} {row[4]} dihapus")
            return True

        # ========== /summary ==========
        if text == "/summary":
            income, expense, net = summarize_today_by_phone(phone)
            msg = f"📊 RINGKASAN HARI INI\n\nIncome: {format_currency(income)}\nExpense: {format_currency(expense)}\nNet: {format_currency(net)}\n\nSaving Rate: {((income - expense) / income * 100) if income > 0 else 0:.1f}%"
            send(phone, msg)
            return True

        # ========== /weekly ==========
        if text == "/weekly":
            income, expense, net, count = summarize_week_by_phone(phone)
            msg = f"📊 RINGKASAN MINGGU INI\n\nTransaksi: {count}\nIncome: {format_currency(income)}\nExpense: {format_currency(expense)}\nNet: {format_currency(net)}\n\nSaving Rate: {((income - expense) / income * 100) if income > 0 else 0:.1f}%"
            send(phone, msg)
            return True

        # ========== /monthly ==========
        if text == "/monthly":
            income, expense, net, count = summarize_month_by_phone(phone)
            msg = f"📊 RINGKASAN BULAN INI\n\nTransaksi: {count}\nIncome: {format_currency(income)}\nExpense: {format_currency(expense)}\nNet: {format_currency(net)}\n\nSaving Rate: {((income - expense) / income * 100) if income > 0 else 0:.1f}%"
            send(phone, msg)
            return True

        # ========== /setbudget ==========
        if text.startswith("/setbudget"):
            args = parse_command_args(text)
            if len(args) < 2:
                send(phone, "❌ Format: /setbudget {kategori} {amount}\nContoh: /setbudget makan 500000")
                return True
            
            category = args[0]
            try:
                amount = int(args[1])
                set_budget(phone, category, amount)
                send(phone, f"✅ Budget {category} ditetapkan: {format_currency(amount)}")
            except ValueError:
                send(phone, "❌ Amount harus angka")
            return True

        # ========== /budget ==========
        if text.startswith("/budget") and not text.startswith("/budgets"):
            args = parse_command_args(text)
            if len(args) < 1:
                send(phone, "❌ Format: /budget {kategori}\nContoh: /budget makan")
                return True
            
            category = args[0]
            amount = get_budget(phone, category)
            if amount == 0:
                send(phone, f"❌ Belum ada budget untuk {category}")
            else:
                send(phone, f"💰 Budget {category}: {format_currency(amount)}")
            return True

        # ========== /budgets ==========
        if text == "/budgets":
            budgets = get_all_budgets(phone)
            if not budgets:
                send(phone, "📋 Belum ada budget. Gunakan /setbudget")
                return True
            
            msg = "💰 DAFTAR BUDGET:\n\n"
            for category, amount in budgets.items():
                msg += f"{category}: {format_currency(amount)}\n"
            send(phone, msg)
            return True

        # ========== /target ==========
        if text.startswith("/target"):
            args = parse_command_args(text)
            if len(args) < 2:
                send(phone, "❌ Format: /target {daily|weekly} {amount}\nContoh: /target daily 500000")
                return True
            
            period = args[0].lower()
            if period not in ["daily", "weekly"]:
                send(phone, "❌ Period harus daily atau weekly")
                return True
            
            try:
                amount = int(args[1])
                set_spending_target(phone, period, amount)
                send(phone, f"✅ Target {period} ditetapkan: {format_currency(amount)}")
            except ValueError:
                send(phone, "❌ Amount harus angka")
            return True

        # ========== /breakdown ==========
        if text.startswith("/breakdown"):
            args = parse_command_args(text)
            days = 30
            if args:
                try:
                    days = int(args[0])
                except ValueError:
                    pass
            
            breakdown = get_category_breakdown(phone, days)
            if not breakdown:
                send(phone, f"📊 Tidak ada data untuk {days} hari terakhir")
                return True
            
            msg = f"📊 BREAKDOWN {days} HARI:\n\n"
            for category, data in breakdown.items():
                msg += f"{category}: {format_currency(data['total'])} ({data['count']} transaksi)\n"
            send(phone, msg)
            return True

        # ========== /ratio ==========
        if text.startswith("/ratio"):
            args = parse_command_args(text)
            days = 30
            if args:
                try:
                    days = int(args[0])
                except ValueError:
                    pass
            
            ratio = get_income_expense_ratio(phone, days)
            if not ratio:
                send(phone, f"📊 Tidak ada data untuk {days} hari terakhir")
                return True
            
            msg = f"📊 INCOME vs EXPENSE ({days} hari):\n\n"
            msg += f"Income: {format_currency(ratio['total_income'])}\n"
            msg += f"Expense: {format_currency(ratio['total_expense'])}\n"
            msg += f"Saved: {format_currency(ratio['saved'])}\n"
            msg += f"Saving Rate: {ratio['saving_rate']:.1f}%"
            send(phone, msg)
            return True

        # ========== /history ==========
        if text.startswith("/history"):
            args = parse_command_args(text)
            category = None
            days = 30
            
            if args:
                try:
                    days = int(args[0])
                except ValueError:
                    category = args[0]
                    if len(args) > 1:
                        try:
                            days = int(args[1])
                        except ValueError:
                            pass
            
            history = search_transactions(phone, category, days)
            if not history:
                send(phone, f"📝 Tidak ada transaksi untuk {category or 'semua kategori'}")
                return True
            
            msg = f"📝 HISTORY {category or 'ALL'} ({days} hari):\n\n"
            for tx in history[:20]:  # Limit 20 entries
                msg += f"{tx['category']} {tx['type']}: {format_currency(tx['amount'])}\n"
            send(phone, msg)
            return True

        # ========== /setrecurring ==========
        if text.startswith("/setrecurring"):
            args = parse_command_args(text)
            if len(args) < 3:
                send(phone, "❌ Format: /setrecurring {kategori} {amount} {daily|weekly|monthly}\nContoh: /setrecurring bensin 100000 weekly")
                return True
            
            category = args[0]
            try:
                amount = int(args[1])
                frequency = args[2].lower()
                if frequency not in ["daily", "weekly", "monthly"]:
                    send(phone, "❌ Frequency harus daily, weekly, atau monthly")
                    return True
                
                add_recurring(phone, category, amount, frequency, f"Auto {frequency}")
                send(phone, f"✅ Recurring {category} {format_currency(amount)} ({frequency}) ditambahkan")
            except ValueError:
                send(phone, "❌ Amount harus angka")
            return True

        # ========== /recurring ==========
        if text == "/recurring":
            recurring = get_recurring(phone)
            if not recurring:
                send(phone, "❌ Belum ada recurring transaction")
                return True
            
            msg = "🔄 DAFTAR RECURRING TRANSACTION:\n"
            for i, item in enumerate(recurring, 1):
                msg += f"\n{i}. {item['category']} {format_currency(item['amount'])} ({item['frequency']})"
            send(phone, msg)
            return True

        # ========== /export ==========
        if text.startswith("/export"):
            args = parse_command_args(text)
            days = 30
            
            if args:
                try:
                    days = int(args[0])
                except ValueError:
                    send(phone, "❌ Format: /export [hari]\nContoh: /export 30")
                    return True
            
            try:
                pdf_bytes = generate_export_pdf(phone, days)
                if pdf_bytes:
                    download_link = f"{APP_BASE_URL}/export/{phone}/{days}"
                    send(phone, f"📄 Laporan Anda siap!\n\nKlik link di bawah untuk download:\n{download_link}\n\nLaporan berisi {days} hari transaksi terakhir Anda.")
                    return True
                else:
                    send(phone, "❌ Gagal generate laporan")
                    return True
            except Exception as e:
                print(f"[Export] Error: {e}")
                send(phone, "❌ Error saat membuat laporan")
                return True

        # ========== FEATURE 3: GOAL TRACKING ====================================
        
        if text.startswith("/goal"):
            # Handle: /goal {kategori} {amount}
            args = parse_command_args(text)
            
            if len(args) < 2:
                send(phone, "❌ Format: /goal {kategori} {amount}\nContoh: /goal saving 500000")
                return True
            
            category = args[0]
            try:
                amount = int(args[1])
                if set_goal(phone, category, amount):
                    send(phone, f"🎯 Goal {category} ditetapkan: {format_currency(amount)}")
                else:
                    send(phone, "❌ Error membuat goal")
            except ValueError:
                send(phone, "❌ Amount harus berupa angka")
            return True

        if text == "/goals":
            # Display semua goals dengan progress bar visual
            goals = get_all_goals(phone)
            
            if not goals:
                send(phone, "📋 Belum ada goals. Gunakan /goal untuk membuat.\nContoh: /goal saving 500000")
                return True
            
            # Build message dengan progress bars
            msg = "🎯 PROGRESS GOALS:\n\n"
            for goal in goals:
                progress = goal["progress"]
                saved = progress["saved"]
                target = progress["goal"]
                percent = progress["percent"]
                
                # Create visual progress bar
                filled = int(percent / 10)
                bar = "█" * filled + "░" * (10 - filled)
                
                msg += f"{goal['category']}:\n"
                msg += f"{bar} {percent:.0f}%\n"
                msg += f"{format_currency(saved)} / {format_currency(target)}\n\n"
            
            send(phone, msg)
            return True

        # ========== FEATURE 4: SMART NOTIFICATIONS ==================================
        
        if text == "/dalert" or text == "/dailyalert":
            # Display daily target status
            alert = check_daily_target_exceeded(phone)
            
            if not alert:
                send(phone, "📊 Belum ada daily target. Gunakan /target daily {amount}\nContoh: /target daily 500000")
                return True
            
            # Build status message
            msg = f"📊 DAILY TARGET STATUS\n\n"
            msg += f"Target: {format_currency(alert['target'])}\n"
            msg += f"Spent: {format_currency(alert['spent'])}\n"
            
            if alert['exceeded']:
                msg += f"⚠️ Over: {format_currency(alert['over_by'])}"
            else:
                remaining = alert['target'] - alert['spent']
                msg += f"✅ Remaining: {format_currency(remaining)}"
            
            send(phone, msg)
            return True

        if text == "/walert" or text == "/weeklyalert":
            # Display weekly target status dengan days remaining
            alert = check_weekly_target_exceeded(phone)
            
            if not alert:
                send(phone, "📊 Belum ada weekly target. Gunakan /target weekly {amount}\nContoh: /target weekly 3500000")
                return True
            
            # Build status message
            msg = f"📊 WEEKLY TARGET STATUS\n\n"
            msg += f"Target: {format_currency(alert['target'])}\n"
            msg += f"Spent: {format_currency(alert['spent'])}\n"
            msg += f"Days Left: {alert['days_remaining']}\n"
            
            if alert['exceeded']:
                msg += f"⚠️ Over: {format_currency(alert['over_by'])}"
            else:
                remaining = alert['target'] - alert['spent']
                msg += f"✅ Remaining: {format_currency(remaining)}"
            
            send(phone, msg)
            return True

        return False
    except Exception as e:
        print(f"[Command Handler] Error: {e}")
        send(phone, "❌ Terjadi error saat memproses perintah Anda.")
        return True

