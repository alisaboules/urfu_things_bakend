import os
import json
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
load_dotenv()

firebase_json = os.environ.get("FIREBASE_CREDENTIALS")

if not firebase_json:
    raise Exception("FIREBASE_CREDENTIALS is missing")

try:
    cred_dict = json.loads(firebase_json)
except json.JSONDecodeError as e:
    raise Exception(f"Invalid FIREBASE_CREDENTIALS JSON: {e}")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)


def send_push(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    return messaging.send(message)