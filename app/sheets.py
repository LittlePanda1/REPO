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
