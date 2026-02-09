import requests
from app.config import WHATSAPP_API_TOKEN, WHATSAPP_PHONE_NUMBER_ID


def send_whatsapp_message(phone: str, message: str) -> bool:
    """
    Mengirim pesan WhatsApp ke nomor telepon tertentu.
    
    Args:
        phone: Nomor telepon penerima (format: 62xxxxxxxxx)
        message: Isi pesan yang akan dikirim
    
    Returns:
        bool: True jika berhasil dikirim, False jika gagal
    """
    # Use the Facebook Graph API endpoint for WhatsApp Cloud API
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        try:
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError:
            # Log response body to help diagnose 401/403/4xx errors
            print(f"WhatsApp API error {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message to {phone}: {e}")
        return False
