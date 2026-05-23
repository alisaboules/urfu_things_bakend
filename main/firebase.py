import os
import json
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
load_dotenv()

firebase_json = os.environ.get("FIREBASE_CREDENTIALS")

firebase_app = None

if firebase_json:
  try:
    cred_dict = json.loads(firebase_json)
    if not firebase_admin._apps:
            cred = credentials.Certificate(cred_dict)
            firebase_app = firebase_admin.initialize_app(cred)

            print("Firebase initialized")

  except Exception as e:
    print("Firebase init failed:", e)

else:
    print("Firebase disabled (no FIREBASE_CREDENTIALS)")


def send_push(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    return messaging.send(message)