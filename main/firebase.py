import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

BASE_DIR = settings.BASE_DIR

cred_path = os.path.join(settings.BASE_DIR, "main", "firebase-key.json")

cred = credentials.Certificate(cred_path)

if not firebase_admin._apps:
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