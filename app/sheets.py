import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_INFO = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

creds = Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES
)

service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()


def insert_row(phone: str, message: str):
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

def insert_transaction(phone, parsed, message_id):
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

from datetime import datetime, timezone

def get_today_transactions_by_phone(phone: str):
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

def summarize_today_by_phone(phone: str):
    txs = get_today_transactions_by_phone(phone)
    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expense = sum(t["amount"] for t in txs if t["type"] == "expense")
    return income, expense, income - expense

def has_message_id(message_id: str) -> bool:
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range="Database_Input!G:G"
    ).execute()
    ids = [r[0] for r in result.get("values", []) if r]
    return message_id in ids

