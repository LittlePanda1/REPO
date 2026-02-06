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

def insert_transaction(phone, parsed):
    values = [[
        datetime.utcnow().isoformat(),
        phone,
        parsed["type"],
        parsed["category"],
        parsed["amount"],
        parsed["note"],
    ]]

    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range="Database_Input!A:F",
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()

from datetime import datetime, timezone

def get_today_transactions():
    today = datetime.utcnow().date().isoformat()

    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range="Database_Input!A:F"
    ).execute()

    rows = result.get("values", [])[1:]  # skip header

    txs = []
    for r in rows:
        ts, phone, tx_type, category, amount, note = r
        if ts.startswith(today):
            txs.append({
                "type": tx_type,
                "category": category,
                "amount": int(amount),
            })
    return txs

def summarize_today():
    txs = get_today_transactions()
    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expense = sum(t["amount"] for t in txs if t["type"] == "expense")
    return income, expense, income - expense
