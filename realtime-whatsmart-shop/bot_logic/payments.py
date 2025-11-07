import stripe
import os

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
        success_url="https://your-app.vercel.app/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://your-app.vercel.app/cancel",
        metadata={"phone": phone}
    )
    # 2. Return pay link + QR (same format as before)
    return {"link": session.url, "qr": f"https://api.qrserver.com/v1/create-qr-code/?data={session.url}&size=200x200", "session_id": session.id}
