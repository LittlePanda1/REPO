import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_INFO = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

creds = Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES
)

service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()


def insert_row(phone: str, message: str):
    try:
        values = [[
            datetime.utcnow().isoformat(),
            phone,
            message
        ]]

        body = {"values": values}

        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Raw_Log!A:C",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
    except Exception as e:
        print(f"Error inserting raw log: {e}")

def insert_transaction(phone, parsed, message_id):
    try:
        values = [[
            datetime.utcnow().isoformat(),
            phone,
            parsed["type"],
            parsed["category"],
            parsed["amount"],
            parsed["note"],
            message_id,
        ]]

        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()
    except Exception as e:
        print(f"Error inserting transaction: {e}")

from datetime import datetime, timezone

def get_today_transactions_by_phone(phone: str):
    try:
        today = datetime.utcnow().date().isoformat()

        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()

        rows = result.get("values", [])[1:]  # skip header

        txs = []
        for r in rows:
            if len(r) < 6:
                continue

            ts, r_phone, tx_type, category, amount, note = r[:6]

            if r_phone != phone:
                continue

            if ts.startswith(today):
                txs.append({
                    "type": tx_type,
                    "category": category,
                    "amount": int(amount),
                })
        return txs
    except Exception as e:
        print(f"Error getting today transactions: {e}")
        return []

def get_transactions_by_phone_and_range(phone: str, start_date: str):
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()

        rows = result.get("values", [])[1:]

        txs = []
        for r in rows:
            if len(r) < 6:
                continue

            ts, r_phone, tx_type, category, amount, note = r[:6]

            if r_phone != phone:
                continue

            if ts < start_date:
                continue

            try:
                amount = int(amount)
            except ValueError:
                continue

            txs.append({
                "type": tx_type,
                "category": category,
                "amount": amount
            })

        return txs
    except Exception as e:
        print(f"Error getting transactions by range: {e}")
        return []

def summarize_today_by_phone(phone: str):
    txs = get_today_transactions_by_phone(phone)
    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expense = sum(t["amount"] for t in txs if t["type"] == "expense")
    return income, expense, income - expense

def summarize_week_by_phone(phone: str):
    start = (datetime.utcnow() - timedelta(days=7)).isoformat()
    txs = get_transactions_by_phone_and_range(phone, start)

    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expense = sum(t["amount"] for t in txs if t["type"] == "expense")

    categories = {}
    for t in txs:
        if t["type"] == "expense":
            categories[t["category"]] = categories.get(t["category"], 0) + t["amount"]

    return income, expense, income - expense, categories

def summarize_month_by_phone(phone: str):
    start = (datetime.utcnow() - timedelta(days=30)).isoformat()
    txs = get_transactions_by_phone_and_range(phone, start)

    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expense = sum(t["amount"] for t in txs if t["type"] == "expense")

    categories = {}
    for t in txs:
        if t["type"] == "expense":
            categories[t["category"]] = categories.get(t["category"], 0) + t["amount"]

    return income, expense, income - expense, categories


def has_message_id(message_id: str) -> bool:
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!G:G"
        ).execute()
        ids = [r[0] for r in result.get("values", []) if r]
        return message_id in ids
    except Exception as e:
        print(f"Error checking message ID: {e}")
        return False

def get_last_transaction_row_by_phone(phone: str):
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Sheet1!A:G"
        ).execute()

        rows = result.get("values", [])
        # skip header, cari dari bawah
        for i in range(len(rows) - 1, 0, -1):
            r = rows[i]
            if len(r) >= 2 and r[1] == phone:
                return i + 1  # row index Google Sheets (1-based)

        return None
    except Exception as e:
        print(f"Error getting last transaction row: {e}")
        return None

def delete_row(row_index: int):
    try:
        requests_body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": 0,  # default first sheet
                            "dimension": "ROWS",
                            "startIndex": row_index - 1,
                            "endIndex": row_index
                        }
                    }
                }
            ]
        }

        service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body=requests_body
        ).execute()
    except Exception as e:
        print(f"Error deleting row: {e}")


# ===========================
# FITUR #1: BUDGET ALERT
# ===========================

def set_budget(phone: str, category: str, amount: int) -> bool:
    """Set budget untuk kategori tertentu"""
    try:
        values = [[
            datetime.utcnow().isoformat(),
            phone,
            category,
            amount
        ]]
        
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Budget_Settings!A:D",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()
        return True
    except Exception as e:
        print(f"Error setting budget: {e}")
        return False


def get_budget(phone: str, category: str) -> int:
    """Get budget untuk kategori tertentu"""
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Budget_Settings!A:D"
        ).execute()
        
        rows = result.get("values", [])[1:]  # skip header
        for r in rows:
            if len(r) >= 4 and r[1] == phone and r[2].lower() == category.lower():
                return int(r[3])
        return 0
    except Exception as e:
        print(f"Error getting budget: {e}")
        return 0


def get_all_budgets(phone: str) -> dict:
    """Get semua budget untuk user"""
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Budget_Settings!A:D"
        ).execute()
        
        rows = result.get("values", [])[1:]
        budgets = {}
        for r in rows:
            if len(r) >= 4 and r[1] == phone:
                budgets[r[2]] = int(r[3])
        return budgets
    except Exception as e:
        print(f"Error getting all budgets: {e}")
        return {}


# ===========================
# FITUR #2: SPENDING TARGET
# ===========================

def set_spending_target(phone: str, target_type: str, amount: int) -> bool:
    """Set daily/weekly spending target"""
    try:
        values = [[
            datetime.utcnow().isoformat(),
            phone,
            target_type,  # 'daily' atau 'weekly'
            amount
        ]]
        
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Spending_Target!A:D",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()
        return True
    except Exception as e:
        print(f"Error setting spending target: {e}")
        return False


def get_spending_target(phone: str, target_type: str) -> int:
    """Get daily/weekly spending target"""
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Spending_Target!A:D"
        ).execute()
        
        rows = result.get("values", [])[1:]
        for r in rows:
            if len(r) >= 4 and r[1] == phone and r[2].lower() == target_type.lower():
                return int(r[3])
        return 0
    except Exception as e:
        print(f"Error getting spending target: {e}")
        return 0


# ===========================
# FITUR #3: CATEGORY BREAKDOWN
# ===========================

def get_category_breakdown(phone: str, days: int) -> dict:
    """Get pengeluaran breakdown per kategori untuk N hari terakhir"""
    try:
        start = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()
        
        rows = result.get("values", [])[1:]
        breakdown = {}
        
        for r in rows:
            if len(r) < 5:
                continue
            ts, r_phone, tx_type, category, amount, note = r[:6]
            
            if r_phone != phone or tx_type != "expense":
                continue
            if ts < start:
                continue
            
            try:
                amount = int(amount)
                if category not in breakdown:
                    breakdown[category] = 0
                breakdown[category] += amount
            except ValueError:
                continue
        
        return breakdown
    except Exception as e:
        print(f"Error getting category breakdown: {e}")
        return {}


# ===========================
# FITUR #5: INCOME vs EXPENSE RATIO
# ===========================

def get_income_expense_ratio(phone: str, days: int) -> dict:
    """Get income, expense, dan saving rate untuk N hari terakhir"""
    try:
        start = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()
        
        rows = result.get("values", [])[1:]
        income = 0
        expense = 0
        
        for r in rows:
            if len(r) < 5:
                continue
            ts, r_phone, tx_type, category, amount, note = r[:6]
            
            if r_phone != phone:
                continue
            if ts < start:
                continue
            
            try:
                amount = int(amount)
                if tx_type == "income":
                    income += amount
                elif tx_type == "expense":
                    expense += amount
            except ValueError:
                continue
        
        saved = income - expense
        saving_rate = (saved / income * 100) if income > 0 else 0
        
        return {
            "income": income,
            "expense": expense,
            "saved": saved,
            "saving_rate": round(saving_rate, 1)
        }
    except Exception as e:
        print(f"Error getting income expense ratio: {e}")
        return {}


# ===========================
# FITUR #6: TRANSACTION HISTORY SEARCH
# ===========================

def search_transactions(phone: str, category: str = None, days: int = None) -> list:
    """Search transactions by category dan/atau days"""
    try:
        start = (datetime.utcnow() - timedelta(days=days)).isoformat() if days else None
        
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()
        
        rows = result.get("values", [])[1:]
        transactions = []
        
        for r in rows:
            if len(r) < 5:
                continue
            ts, r_phone, tx_type, tx_category, amount, note = r[:6]
            
            if r_phone != phone:
                continue
            if start and ts < start:
                continue
            if category and tx_category.lower() != category.lower():
                continue
            
            try:
                transactions.append({
                    "timestamp": ts,
                    "type": tx_type,
                    "category": tx_category,
                    "amount": int(amount),
                    "note": note
                })
            except ValueError:
                continue
        
        # Sort by timestamp descending
        transactions.sort(key=lambda x: x["timestamp"], reverse=True)
        return transactions
    except Exception as e:
        print(f"Error searching transactions: {e}")
        return []


# ===========================
# FITUR #7: RECURRING TRANSACTIONS
# ===========================

def add_recurring(phone: str, category: str, amount: int, frequency: str, note: str) -> bool:
    """Add recurring transaction (daily/weekly/monthly)"""
    try:
        values = [[
            datetime.utcnow().isoformat(),
            phone,
            category,
            amount,
            frequency,  # 'daily', 'weekly', atau 'monthly'
            datetime.utcnow().isoformat(),  # last_run
            note
        ]]
        
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Recurring_Transactions!A:G",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()
        return True
    except Exception as e:
        print(f"Error adding recurring transaction: {e}")
        return False


def get_recurring(phone: str) -> list:
    """Get semua recurring transactions untuk user"""
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Recurring_Transactions!A:G"
        ).execute()
        
        rows = result.get("values", [])[1:]
        recurring = []
        
        for r in rows:
            if len(r) >= 5 and r[1] == phone:
                recurring.append({
                    "category": r[2],
                    "amount": int(r[3]),
                    "frequency": r[4],
                    "note": r[6] if len(r) > 6 else ""
                })
        
        return recurring
    except Exception as e:
        print(f"Error getting recurring transactions: {e}")
        return []


def process_recurring_transactions(phone: str) -> int:
    """Process dan auto-insert recurring transactions yang sudah saatnya dijalankan. Returns count inserted."""
    try:
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Recurring_Transactions!A:G"
        ).execute()
        
        rows = result.get("values", [])[1:]
        today = datetime.utcnow().date()
        count = 0
        
        for idx, r in enumerate(rows):
            if len(r) < 6 or r[1] != phone:
                continue
            
            category = r[2]
            amount = int(r[3])
            frequency = r[4].lower()
            last_run = datetime.fromisoformat(r[5][:19]).date()
            note = r[6] if len(r) > 6 else f"Recurring: {category}"
            
            should_run = False
            if frequency == "daily" and last_run < today:
                should_run = True
            elif frequency == "weekly" and (today - last_run).days >= 7:
                should_run = True
            elif frequency == "monthly" and (today.year, today.month) > (last_run.year, last_run.month):
                should_run = True
            
            if should_run:
                # Insert as expense transaction
                parsed = {
                    "type": "expense",
                    "category": category,
                    "amount": amount,
                    "note": note
                }
                insert_transaction(phone, parsed, f"recurring-{category}-{datetime.utcnow().timestamp()}")
                count += 1
        
        return count
    except Exception as e:
        print(f"Error processing recurring transactions: {e}")
        return 0


# ===========================
# EXPORT TO PDF
# ===========================

def generate_export_pdf(phone: str, days: int = 30) -> bytes:
    """Generate formatted PDF report untuk transaksi user"""
    try:
        print(f"[PDF] Starting PDF generation for {phone}, days={days}")
        
        # Get data
        start = (datetime.utcnow() - timedelta(days=days)).isoformat()
        print(f"[PDF] Fetching data from {start}")
        
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()
        
        rows = result.get("values", [])[1:]
        print(f"[PDF] Got {len(rows)} total rows from sheet")
        
        transactions = []
        
        for r in rows:
            if len(r) < 5:
                continue
            ts, r_phone, tx_type, category, amount, note = r[:6]
            
            if r_phone != phone or ts < start:
                continue
            
            try:
                transactions.append({
                    "timestamp": ts,
                    "type": tx_type,
                    "category": category,
                    "amount": int(amount),
                    "note": note
                })
            except ValueError as ve:
                print(f"[PDF] Skipping invalid transaction: {ve}")
                continue
        
        print(f"[PDF] Filtered to {len(transactions)} transactions for {phone}")
        
        transactions.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Calculate summary
        income = sum(t["amount"] for t in transactions if t["type"] == "income")
        expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
        saved = income - expense
        saving_rate = (saved / income * 100) if income > 0 else 0
        
        print(f"[PDF] Summary: Income={income}, Expense={expense}, Saved={saved}")
        
        # Create PDF in memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Header style
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER
        )
        
        # Add title
        story.append(Paragraph("📊 LAPORAN KEUANGAN PRIBADI", title_style))
        
        # Add date info
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%d/%m/%Y')
        end_date = datetime.utcnow().strftime('%d/%m/%Y')
        info_text = f"Periode: {start_date} - {end_date} ({days} hari)<br/>Nomor: {phone}<br/>Generated: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}"
        story.append(Paragraph(info_text, header_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Summary section
        summary_data = [
            ["RINGKASAN KEUANGAN", ""],
            ["Income", f"Rp {income:,.0f}"],
            ["Expense", f"Rp {expense:,.0f}"],
            ["Saved", f"Rp {saved:,.0f}"],
            ["Saving Rate", f"{saving_rate:.1f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Transactions table
        if transactions:
            table_data = [["Tanggal", "Kategori", "Tipe", "Amount", "Catatan"]]
            
            for tx in transactions:
                date_str = tx["timestamp"][:10]
                type_emoji = "➕" if tx["type"] == "income" else "➖"
                table_data.append([
                    date_str,
                    tx["category"],
                    f"{type_emoji} {tx['type']}",
                    f"Rp {tx['amount']:,.0f}",
                    tx["note"][:30] + "..." if len(tx["note"]) > 30 else tx["note"]
                ])
            
            trans_table = Table(table_data, colWidths=[1.2*inch, 1.2*inch, 1*inch, 1.3*inch, 1.3*inch])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            story.append(Paragraph("DAFTAR TRANSAKSI", styles['Heading2']))
            story.append(trans_table)
        else:
            story.append(Paragraph("<b>Tidak ada transaksi untuk periode ini</b>", styles['Normal']))
        
        # Build PDF
        print("[PDF] Building PDF document...")
        doc.build(story)
        pdf_buffer.seek(0)
        pdf_data = pdf_buffer.getvalue()
        print(f"[PDF] SUCCESS: Generated {len(pdf_data)} bytes")
        return pdf_data
        
    except Exception as e:
        print(f"[PDF] ERROR generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


# ===========================
# FEATURE 1: BUDGET ALERT OTOMATIS
# Fitur untuk alert otomatis ketika pengeluaran melebihi budget kategori
# ===========================

def check_budget_exceeded(phone: str, category: str, amount: int) -> dict:
    """Check apakah pengeluaran baru akan melebihi budget kategori.
    
    Fungsi ini digunakan untuk:n    - Mengecek apakah user sudah melebihi budget saat record transaksi
    - Menampilkan alert otomatis jika budget terlampaui
    
    Args:
        phone (str): Nomor WhatsApp user
        category (str): Kategori transaksi (misal: 'makan', 'bensin')
        amount (int): Jumlah pengeluaran baru dalam Rupiah
    
    Returns:
        dict atau None jika tidak ada budget yang ditetapkan:
        {
            'exceeded': bool - Apakah sudah melebihi budget
            'budget': int - Budget total untuk kategori ini
            'spent_today': int - Sudah dikeluarkan hari ini
            'amount_added': int - Pengeluaran baru yang akan ditambah
            'new_total': int - Total pengeluaran setelah transaksi baru
            'remaining': int - Sisa budget (bisa negatif jika exceeded)
            'percent': float - Persentase penggunaan budget (0-100+)
        }
    """
    try:
        # Ambil budget untuk kategori ini
        budget = get_budget(phone, category)
        if budget == 0:
            return None  # Tidak ada budget set, skip alert
        
        # Hitung total pengeluaran hari ini di kategori ini
        txs = get_today_transactions_by_phone(phone)
        spent_today = sum(t["amount"] for t in txs 
                         if t["category"].lower() == category.lower() 
                         and t["type"] == "expense")
        
        # Hitung total setelah transaksi baru
        new_total = spent_today + amount
        exceeded = new_total > budget
        remaining = budget - new_total
        percent = (new_total / budget * 100) if budget > 0 else 0
        
        return {
            "exceeded": exceeded,
            "budget": budget,
            "spent_today": spent_today,
            "amount_added": amount,
            "new_total": new_total,
            "remaining": remaining,
            "percent": round(percent, 1)
        }
    except Exception as e:
        print(f"[Budget Alert] Error checking budget: {e}")
        return None


# ===========================
# FEATURE 2: DAILY AUTO REPORT
# Fitur untuk mengirim ringkasan pengeluaran otomatis setiap hari
# ===========================

def get_all_user_phones() -> list:
    """Ambil semua nomor WhatsApp unique yang pernah mencatat transaksi.
    
    Fungsi ini digunakan untuk:
    - Mendapatkan daftar user yang akan menerima daily report otomatis
    - Memastikan hanya user aktif yang menerima notifikasi
    
    Returns:
        list: Daftar nomor WhatsApp unik (misal: ['6287123456789', '6281234567890'])
              Jika tidak ada transaksi, return list kosong []
    """
    try:
        # Ambil kolom B (nomor WhatsApp) dari sheet Database_Input
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!B:B"
        ).execute()
        
        # Gunakan set untuk menghilangkan duplikat
        phones = set()
        rows = result.get("values", [])[1:]  # skip header row
        for r in rows:
            if r:  # skip empty rows
                phones.add(r[0])
        
        return list(phones)
    except Exception as e:
        print(f"[Daily Report] Error getting user phones: {e}")
        return []


def get_daily_summary(phone: str) -> str:
    """Generate ringkasan pengeluaran harian untuk dikirim via WhatsApp.
    
    Fungsi ini membuat pesan yang mencakup:
    - Total income dan expense hari ini
    - Saving rate (persentase uang yang disimpan)
    - Status budget (warning jika ada kategori yang melebihi budget)
    - Status daily target (warning jika total pengeluaran melebihi target harian)
    
    Args:
        phone (str): Nomor WhatsApp user
    
    Returns:
        str: Pesan ringkasan dalam format text yang siap dikirim via WhatsApp
             Contoh:
             📊 LAPORAN HARIAN
             Income: Rp 500,000
             Expense: Rp 150,000
             Net: Rp 350,000
             Saving Rate: 70%
    """
    try:
        # Hitung summary hari ini
        income, expense, net = summarize_today_by_phone(phone)
        
        # Cek status budget untuk setiap kategori
        budgets = get_all_budgets(phone)
        budget_status = ""
        
        if budgets:
            over_budget = []
            txs = get_today_transactions_by_phone(phone)
            
            # Cek setiap kategori yang punya budget
            for category, budget_amount in budgets.items():
                spent = sum(t["amount"] for t in txs 
                           if t["category"].lower() == category.lower() 
                           and t["type"] == "expense")
                
                # Jika sudah melebihi, tambahkan ke warning
                if spent > budget_amount:
                    overage = spent - budget_amount
                    over_budget.append(
                        f"\n⚠️ {category}: Rp {spent:,.0f} / Rp {budget_amount:,.0f} (+Rp {overage:,.0f})"
                    )
            
            if over_budget:
                budget_status = "\n\n🚨 BUDGET STATUS:" + "".join(over_budget)
        
        # Cek status daily target jika ada
        daily_target = get_spending_target(phone, "daily")
        target_status = ""
        if daily_target > 0 and expense > daily_target:
            target_status = f"\n\n⚠️ Daily Target: {format_currency(expense)} / {format_currency(daily_target)}"
        
        # Susun pesan final
        saving_rate = ((income - expense) / income * 100) if income > 0 else 0
        
        summary_text = f"""📊 LAPORAN HARIAN

Income: {format_currency(income)}
Expense: {format_currency(expense)}
Net: {format_currency(net)}

Saving Rate: {saving_rate:.1f}%{budget_status}{target_status}

Time: {datetime.utcnow().strftime('%H:%M')}"""
        
        return summary_text
    except Exception as e:
        print(f"[Daily Report] Error getting daily summary: {e}")
        return None


# ===========================
# FEATURE 3: MONTHLY GOAL TRACKING
# Fitur untuk tracking saving goals user (contoh: nabung Rp 5juta untuk repair motor)
# ===========================

def set_goal(phone: str, category: str, target_amount: int) -> bool:
    """Set saving goal untuk kategori tertentu.
    
    Contoh penggunaan:
    - Set goal "saving" dengan target Rp 5,000,000 untuk 30 hari
    - Set goal "vacation" dengan target Rp 10,000,000 untuk liburan akhir tahun
    
    Args:
        phone (str): Nomor WhatsApp user
        category (str): Nama kategori goal (misal: 'saving', 'vacation', 'repair_motor')
        target_amount (int): Target saving dalam Rupiah
    
    Returns:
        bool: True jika berhasil disimpan, False jika ada error
    """
    try:
        # Siapkan data baru untuk ditambahkan ke Google Sheets
        values = [[
            datetime.utcnow().isoformat(),  # Timestamp kapan goal dibuat
            phone,
            category,
            target_amount
        ]]
        
        # Append row ke sheet Goals_Settings
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Goals_Settings!A:D",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()
        
        return True
    except Exception as e:
        print(f"[Goal Tracking] Error setting goal: {e}")
        return False


def get_goal(phone: str, category: str) -> int:
    """Ambil target amount untuk goal kategori tertentu.
    
    Args:
        phone (str): Nomor WhatsApp user
        category (str): Nama kategori goal
    
    Returns:
        int: Target amount dalam Rupiah. Jika goal tidak ditemukan, return 0
    """
    try:
        # Ambil semua data dari sheet Goals_Settings
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Goals_Settings!A:D"
        ).execute()
        
        # Cari goal yang cocok dengan phone dan category
        rows = result.get("values", [])[1:]  # skip header
        for r in rows:
            if len(r) >= 4 and r[1] == phone and r[2].lower() == category.lower():
                return int(r[3])
        
        return 0  # Goal tidak ditemukan
    except Exception as e:
        print(f"[Goal Tracking] Error getting goal: {e}")
        return 0


def get_goal_progress(phone: str, category: str, days: int = 30) -> dict:
    """Track progress saving goal dalam periode tertentu.
    
    Fitur ini membantu user melihat:
    - Berapa target yang ingin dicapai
    - Berapa sudah dikumpulkan di periode ini
    - Berapa persen progress yang sudah dicapai
    - Sisa yang dibutuhkan
    
    Args:
        phone (str): Nomor WhatsApp user
        category (str): Nama kategori goal
        days (int): Periode tracking dalam hari (default: 30 hari = 1 bulan)
    
    Returns:
        dict atau None jika goal tidak ditemukan:
        {
            'goal': int - Target total dalam Rupiah
            'saved': int - Sudah dikumpulkan dalam periode
            'percent': float - Progress dalam persentase (0-100%)
            'remaining': int - Sisa yang dibutuhkan
            'days': int - Periode tracking
        }
    """
    try:
        # Ambil target goal
        goal = get_goal(phone, category)
        if goal == 0:
            return None  # Goal tidak ada
        
        # Hitung periode
        start = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Ambil semua transaksi
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Database_Input!A:G"
        ).execute()
        
        # Hitung total income yang masuk ke kategori ini dalam periode
        rows = result.get("values", [])[1:]
        saved = 0
        
        for r in rows:
            if len(r) < 5:
                continue  # Skip incomplete rows
            
            ts, r_phone, tx_type, tx_category, amount = r[:5]
            
            # Filter: harus user yang sama, dalam periode, kategori dan tipe income
            if r_phone != phone or ts < start:
                continue
            if tx_category.lower() != category.lower() or tx_type != "income":
                continue
            
            # Kumulatifkan amount
            try:
                saved += int(amount)
            except ValueError:
                continue
        
        # Hitung progress
        percent = (saved / goal * 100) if goal > 0 else 0
        remaining = max(0, goal - saved)
        
        return {
            "goal": goal,
            "saved": saved,
            "percent": round(percent, 1),
            "remaining": remaining,
            "days": days
        }
    except Exception as e:
        print(f"[Goal Tracking] Error getting goal progress: {e}")
        return None


def get_all_goals(phone: str) -> list:
    """Ambil semua goals user dengan progress masing-masing.
    
    Berguna untuk comando /goals yang menampilkan semua goals beserta progress bar.
    
    Args:
        phone (str): Nomor WhatsApp user
    
    Returns:
        list: List of goals dengan progress. Contoh:
        [
            {
                'category': 'saving',
                'goal': 5000000,
                'progress': {
                    'goal': 5000000,
                    'saved': 3000000,
                    'percent': 60.0,
                    'remaining': 2000000,
                    'days': 30
                }
            },
            ...
        ]
    """
    try:
        # Ambil semua goals untuk user ini
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range="Goals_Settings!A:D"
        ).execute()
        
        rows = result.get("values", [])[1:]
        goals = []
        
        # Untuk setiap goal, hitung progress-nya
        for r in rows:
            if len(r) >= 4 and r[1] == phone:
                goal_progress = get_goal_progress(phone, r[2])
                # Hanya include goal yang ada progress data
                if goal_progress:
                    goals.append({
                        "category": r[2],
                        "goal": int(r[3]),
                        "progress": goal_progress
                    })
        
        return goals
    except Exception as e:
        print(f"[Goal Tracking] Error getting all goals: {e}")
        return []


# ===========================
# FEATURE 4: SMART NOTIFICATIONS
# Fitur untuk smart alerts ketika spending patterns mencapai threshold targets
# ===========================

def check_daily_target_exceeded(phone: str) -> dict:
    """Check apakah pengeluaran hari ini sudah melebihi daily spending target.
    
    Fungsi ini digunakan untuk:
    - Trigger alert otomatis ketika user berbelanja melebihi daily budget
    - Display status progress daily target via /dalert command
    
    Args:
        phone (str): Nomor WhatsApp user
    
    Returns:
        dict atau None jika belum ada daily target:
        {
            'exceeded': bool - Apakah sudah melebihi target
            'target': int - Daily target dalam Rupiah
            'spent': int - Total pengeluaran hari ini
            'over_by': int - Berapa Rupiah sudah over (0 jika belum)
        }
    """
    try:
        # Ambil daily target yang sudah ditetapkan user
        target = get_spending_target(phone, "daily")
        if target == 0:
            return None  # Belum ada daily target set
        
        # Hitung total pengeluaran hari ini
        income, expense, net = summarize_today_by_phone(phone)
        
        # Cek apakah sudah exceeded
        exceeded = expense > target
        over_by = max(0, expense - target)  # 0 jika belum exceeded
        
        return {
            "exceeded": exceeded,
            "target": target,
            "spent": expense,
            "over_by": over_by
        }
    except Exception as e:
        print(f"[Smart Notifications] Error checking daily target: {e}")
        return None


def check_weekly_target_exceeded(phone: str) -> dict:
    """Check apakah pengeluaran minggu ini sudah melebihi weekly spending target.
    
    Fungsi ini:
    - Monitor weekly spending dengan informasi hari tersisa
    - Membantu user project spending untuk sisa minggu
    - Trigger alert ketika melebihi weekly budget
    
    Args:
        phone (str): Nomor WhatsApp user
    
    Returns:
        dict atau None jika belum ada weekly target:
        {
            'exceeded': bool - Apakah sudah melebihi target minggu ini
            'target': int - Weekly target dalam Rupiah
            'spent': int - Total pengeluaran minggu ini
            'over_by': int - Berapa Rupiah sudah over (0 jika belum)
            'days_remaining': int - Sisa hari dalam minggu (1-6)
        }
    """
    try:
        # Ambil weekly target yang sudah ditetapkan user
        target = get_spending_target(phone, "weekly")
        if target == 0:
            return None  # Belum ada weekly target set
        
        # Hitung total pengeluaran minggu ini
        income, expense, net, _ = summarize_week_by_phone(phone)
        
        # Cek apakah sudah exceeded
        exceeded = expense > target
        over_by = max(0, expense - target)  # 0 jika belum exceeded
        
        # Hitung sisa hari dalam minggu (Monday=0, Sunday=6)
        # Jika hari Senin, days_remaining = 6 (Tue-Sun)
        # Jika hari Minggu, days_remaining = 0 (weekend)
        today = datetime.utcnow()
        days_remaining = 6 - today.weekday()
        
        return {
            "exceeded": exceeded,
            "target": target,
            "spent": expense,
            "over_by": over_by,
            "days_remaining": days_remaining
        }
    except Exception as e:
        print(f"[Smart Notifications] Error checking weekly target: {e}")
        return None


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
