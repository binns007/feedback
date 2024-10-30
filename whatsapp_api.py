import requests
import os

def send_whatsapp_message(to_number: str, message: str):
    # Replace this with your actual WhatsApp API logic
    url = "https://api.whatsapp.com/send"
    params = {
        'phone': to_number,
        'text': message
    }
    response = requests.post(url, params=params)
    if response.status_code != 200:
        raise Exception("Failed to send message")
