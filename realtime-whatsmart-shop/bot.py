# bot.py  –  WhatsApp AI shop  –  NO WooCommerce  –  Google-Sheet-as-JSON  –  India UPI
import os, json, csv, requests, redis, cv2, numpy as np, time, threading
from flask import Flask, request
import whisper, mediapipe as mp

app = Flask(name)
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# --------------------  CONFIG  --------------------
ACCESS_TOKEN   = os.getenv("ACCESS_TOKEN")
PHONE_ID       = os.getenv("PHONE_ID")
VERIFY_TOKEN   = os.getenv("VERIFY_TOKEN")

# RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
# RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_STOREFRONT_TOKEN")
GOOGLE_KEY     = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID")
OWNER_PHONE    = os.getenv("OWNER_PHONE")

# 1-MIN GOOGLE SHEET (zero keys) – best alternative to WooCommerce
SHEET_CSV = os.getenv("SHEET_CSV")  # publish-to-web link

# --------------------  WHATSAPP SEND  --------------------
from twilio.rest import Client

def send_whatsapp(to, kind="text", text=None, image=None, buttons=None):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    from_ = os.getenv("TWILIO_WHATSApp_NUMBER")
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
# --------------------  REAL-TIME DATA  --------------------
# def fetch_shopify():
#     if not SHOPIFY_TOKEN: return []
#     q = """{ products(first: 20) {
#         edges { node {
#             id title vendor
#             images(first:1) { edges { node { url } } }
#             variants(first:1) { edges { node { price quantityAvailable } } }
#         } }
#     } }"""
#     resp = requests.post(f"https://{SHOPIFY_DOMAIN}/api/2023-10/graphql.json",
#                          json={"query": q},
#                          headers={"X-Shopify-Storefront-Access-Token": SHOPIFY_TOKEN}).json()
#     prods = []
#     for e in resp["data"]["products"]["edges"]:
#         n = e["node"]
#         prods.append({
#             "id": n["id"].split("/")[-1],
#             "name": n["title"],
#             "price": float(n["variants"]["edges"][0]["node"]["price"]),
#             "stock": n["variants"]["edges"][0]["node"]["quantityAvailable"],
#             "image": n["images"]["edges"][0]["node"]["url"] if n["images"]["edges"] else "",
#             "vendor": "shopify"
#         })
#     return prods

def fetch_google_shopping(query):
    if not GOOGLE_KEY: return []
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_KEY}&cx={GOOGLE_CSE_ID}&num=5"
    resp = requests.get(url).json()
    prods = []
    for item in resp.get("items", []):
        if "₹" in item["title"]:
            try:
                price = int(item["title"].split("₹")[1].split()[0].replace(",", ""))
                prods.append({
                    "id": item["cacheId"][:10],
                    "name": item["title"][:70],
                    "price": price,
                    "stock": 999,
                    "image": item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", ""),
                    "vendor": "google"
                })
            except: pass
    return prods

# *******  EASIEST WOO-COMMERCE REPLACEMENT  *******
def fetch_sheet():
    """Google Sheet → CSV → products (zero keys, 1-min setup)"""
    if not SHEET_CSV: return []
    r = requests.get(SHEET_CSV)
    r.encoding = 'utf-8'
    return list(csv.DictReader(r.text.splitlines()))

# --------------------  CACHE  --------------------
CACHE_FILE = "products.json"
def load_cache():
    return json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else []
def save_cache(data):
    json.dump(data, open(CACHE_FILE, "w"), indent=2)

def refresh_products():
    shopify  = fetch_shopify()
    google   = fetch_google_shopping("sneakers")
    sheet    = fetch_sheet()          # ← NEW
    merged   = shopify + google + sheet
    save_cache(merged)
    return merged

PRODUCTS = refresh_products()
# background refresh every 5 min
def bg_refresh():
    while True:
        time.sleep(300)
        refresh_products()
threading.Thread(target=bg_refresh, daemon=True).start()

# --------------------  INDIA UPI PAYMENT  --------------------
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET")

def create_stripe_checkout(phone, amount):
    # 1. Create Checkout Session (UPI + Cards)
    session = stripe.checkout.Session.create(
        payment_method_types=["card", "upi"],
        line_items=[{
            "price_data": {
                "currency": "inr",
                "product_data": {"name": "WhatsApp order"},
                "unit_amount": int(amount * 100)   # paisa
            },
            "quantity": 1
        }],
        mode="payment",
        success_url="https://your-app.onrender.com/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://your-app.onrender.com/cancel",
        metadata={"phone": phone}
    )
    # 2. Return pay link + QR (same format as before)
    return {"link": session.url, "qr": f"https://api.qrserver.com/v1/create-qr-code/?data={session.url}&size=200x200", "session_id": session.id}
# --------------------  CART  --------------------
def cart_key(phone): return f"cart:{phone}"
def add_cart(phone, product_id):
    r.hincrby(cart_key(phone), product_id, 1)
def show_cart(phone):
    items = r.hgetall(cart_key(phone))
    if not items:
        send_whatsapp(phone, "text", text="🛒 Cart is empty"); return 0
    total = 0; lines = []
    for pid, qty in items.items():
        p = next(p for p in PRODUCTS if p["id"] == pid.decode())
        sub = int(p["price"]) * int(qty); total += sub
        lines.append(f"{p['name']} x{qty.decode()} = ₹{sub}")
    lines.append(f"Total: ₹{total}")
    send_whatsapp(phone, "text", text="\n".join(lines))
    return total

# --------------------  AR TRY-ON  --------------------
import cv2
import numpy as np
import requests

def overlay_shoes(user_img_url, product_png_url):
    """
    OpenCV-only AR try-on (no Mediapipe)
    Places shoes at bottom-center of image
    """
    # 1. Download images
    img   = cv2.imdecode(np.frombuffer(requests.get(user_img_url).content, np.uint8), cv2.IMREAD_COLOR)
    shoes = cv2.imdecode(np.frombuffer(requests.get(product_png_url).content, np.uint8), cv2.IMREAD_UNCHANGED)

    # 2. Bottom-center placement
    h, w = img.shape[:2]
    shoes = cv2.resize(shoes, (160, 80))
    x, y = (w - 160) // 2, h - 80 - 20

    # 3. Alpha blend
    alpha = shoes[:, :, 3] / 255.0
    for c in range(3):
        img[y:y + 80, x:x + 160, c] = alpha * shoes[:, :, c] + (1 - alpha) * img[y:y + 80, x:x + 160, c]

    # 4. Return PNG bytes
    ok, buf = cv2.imencode('.png', img)
    return buf.tobytes()

# --------------------  WEBHOOK  --------------------
@app.route("/webhook", methods=["GET"])
def verify():
    mode, token, challenge = request.args.get("hub.mode"), request.args.get("hub.verify_token"), request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    return "OK"

@app.route("/webhook", methods=["POST"])
def hook():
    data = request.get_json()
    for entry in data["entry"]:
        for ch in entry["changes"]:
            if ch["field"] == "messages":
                msg = ch["value"]["messages"][0]
                phone = msg["from"]
                # 1. PHOTO -> TRY-ON
                if msg.get("type") == "image":
                    prod = [p for p in PRODUCTS if "shoes" in p["name"].lower()][0]
                    media_url = requests.get(f"https://graph.facebook.com/v18.0/{msg['image']['id']}", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}).json()["url"]
                    overlay = overlay_shoes(media_url, prod["image"])
                    if overlay:
                        imgr = requests.post("https://api.imgur.com/3/image", headers={"Authorization": "Client-ID 546c25a59c58ad7"}, files={"image": overlay}).json()
                        send_whatsapp(phone, "image", image=imgr["data"]["link"])
                    else:
                        send_whatsapp(phone, "text", text="Couldn’t find feet, retake photo.")
                # 2. VOICE
                elif msg.get("type") == "voice":
                    media_url = requests.get(f"https://graph.facebook.com/v18.0/{msg['voice']['id']}", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}).json()["url"]
                    voice = requests.get(media_url).content
                    with open("temp.ogg", "wb") as f: f.write(voice)
                    result = whisper.transcribe("temp.ogg")
                    text = result["text"].lower()
                    # save style pref
                    data = json.loads(r.get(f"style:{phone}") or '{"loves":[],"hates":[]}')
                    if "streetwear" in text or "baggy" in text: data["loves"].append("baggy")
                    if "skinny" in text: data["hates"].append("skinny")
                    r.set(f"style:{phone}", json.dumps(data))
                    send_whatsapp(phone, "text", text=f"👂 Heard: {text}")
                # 3. TEXT
                elif msg.get("type") == "text":
                    txt = msg["text"]["body"].lower()
                    if "shoes" in txt or "search" in txt:
                        p = PRODUCTS[0]
                        buttons = [{"type": "reply", "reply": {"id": f"add_{p['id']}", "title": "Add to cart"}}]
                        send_whatsapp(phone, "buttons", text=f"{p['name']} ₹{p['price']} (stock {p['stock']})", buttons=buttons)
                    elif "cart" in txt:
                        show_cart(phone)
                    elif "checkout" in txt:
                        total = show_cart(phone)
                        if total:
                            pay = create_upi_order(phone, total)
                            buttons = [{"type": "reply", "reply": {"id": f"pay_{pay['order_id']}", "title": "💳 Pay now"}}]
                            send_whatsapp(phone, "buttons", text=f"Total ₹{total}\nTap Pay to open any UPI app.", buttons=buttons)
                            send_whatsapp(phone, "image", image=pay["qr"])
                    else:
                        send_whatsapp(phone, "text", text="Menu: search | cart | checkout")
                # 4. BUTTON INTERACTIVE
                elif msg.get("type") == "interactive":
                    bid = msg["interactive"]["button_reply"]["id"]
                    if bid.startswith("add_"):
                        add_cart(phone, bid.split("_")[1])
                        send_whatsapp(phone, "text", text="✅ Added to cart")
                    elif bid.startswith("pay_"):
                        order_id = bid.split("_")[1]
                        paid = False
                        for _ in range(6):
                            if check_payment(order_id):
                                paid = True; break
                            time.sleep(5)
                        if paid:
                            send_whatsapp(phone, "text", text=f"✅ Payment successful! Order #{order_id[-6:]} confirmed.")
                            r.delete(cart_key(phone))
                        else:
                            send_whatsapp(phone, "text", text="⏰ Payment not completed. Tap Pay again or scan QR.")
    return "OK"

if name == "main":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
