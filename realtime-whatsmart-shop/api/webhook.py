from flask import Request, jsonify
from bot_logic.ar_tryon import overlay_shoes
import os

def handler(request: Request):
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        # Example: extract image URLs from incoming JSON
        user_img = data.get("user_img_url")
        product_img = data.get("product_img_url")
        if user_img and product_img:
            try:
                composed = overlay_shoes(user_img, product_img)
                return jsonify({"result": "overlay ok", "bytes": len(composed)}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        return jsonify({"message": "no images"}), 200
    return "OK", 200
