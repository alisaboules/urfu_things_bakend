import os
import json
import firebase_admin
from firebase_admin import credentials
import firebase_admin.messaging as messaging
firebase_json = os.environ.get("FIREBASE_CREDENTIALS")

cred_dict = json.loads(firebase_json)

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