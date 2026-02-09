import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

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
    