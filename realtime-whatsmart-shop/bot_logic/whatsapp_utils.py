from twilio.rest import Client
import os

def send_whatsapp(to, kind="text", text=None, image=None, buttons=None):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    from_ = os.getenv("TWILIO_WHATSAPP_NUMBER")
    to = f"whatsapp:{to}"

    if kind == "text":
        return client.messages.create(body=text, from_=from_, to=to).sid
    elif kind == "image":
        return client.messages.create(media_url=[image], from_=from_, to=to).sid
    elif kind == "buttons":
        return client.messages.create(
            body=text,
            from_=from_,
            to=to,
            interactive={
                "type": "button",
                "action": {"buttons": [{"type": "reply", "title": b["reply"]["title"], "id": b["reply"]["id"]} for b in buttons]}
            }
        ).sid
