# -*- coding: utf-8 -*-

import os
import json
import asyncio
import logging
import random
import string
import io
import re
import time
import threading
import sqlite3
import uuid
from datetime import datetime, timedelta
import requests
from aiohttp import web
import qrcode
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji, ReactionTypeCustomEmoji
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.request import HTTPXRequest

# ============================================
# ✅ CONFIG
# ============================================

TOKEN = "8833898625:AAEW18HVT9CIzvTW0lP7U6nub8FuXjX2bUI"
ADMIN_ID = 8373276191

KARANPAY_KEY_1 = "guru131e012b5141689b9135317fb6fa7f"
KARANPAY_KEY_2 = "guru1eff587f747b3df8c7a355570f90ce"
KARANPAY_CREATE_URL = "https://gurupaygateway.com/api/create-order"
KARANPAY_STATUS_URL = "https://gurupaygateway.com/api/check-status"
RECEIVER_UPI = "vikrambhaiyaaa@fam"
MIN_AMOUNT = 1
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store_data.db")
RESELLER_DISCOUNT_PERCENT = 15
REFERRAL_COMMISSION_PERCENT = 0.5

API_ENDPOINT = "https://xyzcheats.com/api/reseller_v1.php"
API_KEY = "2c59f7c31055b7b9b61f5bb6a0ae85e0"
MASTER_KEY = "a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8"
ANDROID_ID = "0b9b969bc2e7997b"

# ============================================
# 🎯 BALA MOD PRODUCTS - Android ID Required
# ============================================

BALA_MOD_PRODUCTS = [
    "BALA MOD XYZ FF",  # V1 - Android ID MANDATORY
]

# ============================================
# 🎯 PREMIUM EMOJI IDs - ONLY FOR BUTTONS
# ============================================


EDITABLE_TEXTS = {
    "welcome": "Welcome Menu",
    "shop": "Store",
    "profile": "Profile",
    "add_balance": "Add Balance",
    "order_history": "Order History",
    "deposit_history": "Deposit History",
    "tutorial": "Tutorial",
    "support": "Support",
    "download": "Download",
    "referral": "Referral",
    "maintenance_msg": "Maintenance Message",
    "transfer_caption": "Transfer Balance Caption",
    "transfer_amount_caption": "Transfer Amount Prompt",
    "transfer_success_msg": "Transfer Success Message",
    "transfer_received_msg": "Transfer Received Message"
}

def get_text_safe(key, default):
    return db.get_text(key, default)

def notify_admin_deposit(user_id, order_id, amount, utr, sender):
    try:
        user_data = db.get_user(user_id)
        username = f"@{user_data[1]}" if user_data and user_data[1] else user_id
        admin_msg = f"🌟 <b>NEW DEPOSIT RECEIVED!</b>\n\n👤 <b>User:</b> {username} (<code>{user_id}</code>)\n<tg-emoji emoji-id=\"6215156189454409086\">💰</tg-emoji> <b>Amount:</b> ₹{amount:.2f}\n⏰ <b>Time:</b> {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <b>Order ID:</b> <code>{order_id}</code>"
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": int(ADMIN_ID), "text": admin_msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")


BUTTON_EMOJIS = {
    "shop": "6334784630809435068",
    "profile": "6215104357789081549",
    "add_balance": "6212764498260925926",
    "order_history": "6147464060305676048",
    "deposit_history": "6147902731085420231",
    "referral": "6237871554223412862",
    "tutorial": "6237742262822901946",
    "support": "6147460667281511517",
    "download": "6235475653961979149",
    "back": "6235445786759402354",
    "confirm": "6235234890980269200",
    "cancel": "6237755976653477546",
    "clear": "6237704110628413424",
    "android_nonroot": "6235234190900598910",
    "android_root": "6235593671073339928",
    "pc": "6235289248086365655",
    "ios": "6237941218592960218",
    "star": "6235285623133968567",
    "plan": "5895753894151067082",
    "warning": "6242147417504879292",
    "broadcast": "6147427845007214747",
    "users": "6215104357789081549",
    "stats": "6235216396884641617",
    "remove": "6235451296715901306",
    "add": "6235456420611885406",
    "phonepe": "5334890573281114250",
    "googlepay": "6215156189454409086",
    "refresh": "6235234890980269200",
    "pay": "6244617272808183303",
}

# ============================================
# 🎨 EMOJI HELPERS
# ============================================

def get_button_emoji(name):
    # Try fetching from DB, fallback to hardcoded list
    return db.get_emoji(name, BUTTON_EMOJIS.get(name, ""))


def get_price_for_user(base_price, user_id):
    if db.is_reseller(user_id):
        return round(base_price * (1 - RESELLER_DISCOUNT_PERCENT / 100), 2)
    return base_price

def parse_product_line(text):
    text = (text or "").strip()
    parts = text.split("|")
    if len(parts) < 5:
        raise ValueError(
            "Format galat hai. Usage:\n"
            "CATEGORY | NAME | PRODUCT_ID | PLAN | PRICE | ANDROID_ID (optional)"
        )

    category = parts[0].strip().upper()
    name = parts[1].strip()
    product_id = parts[2].strip()
    plan = parts[3].strip()
    price_raw = parts[4].strip()

    if not category or not name or not product_id or not plan:
        raise ValueError("CATEGORY, NAME, PRODUCT_ID aur PLAN khaali nahi ho sakte.")

    price_clean = re.sub(r'[^\d.]', '', price_raw)
    if not price_clean:
        raise ValueError(f"PRICE samajh nahi aayi: '{price_raw}'. Sirf number likho, jaise 150")
    try:
        price = float(price_clean)
    except ValueError:
        raise ValueError(f"PRICE samajh nahi aayi: '{price_raw}'. Sirf number likho, jaise 150")
    if price <= 0:
        raise ValueError("PRICE 0 se zyada honi chahiye.")

    android_id = parts[5].strip() if len(parts) > 5 and parts[5].strip() else ANDROID_ID

    return {
        "category": category,
        "name": name,
        "product_id": product_id,
        "plan": plan,
        "price": price,
        "android_id": android_id,
    }

# ============================================
# 🎨 STYLED BUTTON
# ============================================

class ColoredButton(InlineKeyboardButton):
    def __init__(self, text, style=None, icon=None, **kwargs):
        super().__init__(text, **kwargs)
        self._style = style
        self._icon = icon

    def to_dict(self, **kwargs):
        data = super().to_dict(**kwargs)
        if self._style:
            data['style'] = self._style
        if self._icon:
            data['icon_custom_emoji_id'] = self._icon
        return data

def to_monospace(text):
    result = ''
    for char in text:
        if 'A' <= char <= 'Z':
            result += chr(ord(char) + 120367)
        elif 'a' <= char <= 'z':
            result += chr(ord(char) + 120361)
        elif '0' <= char <= '9':
            result += chr(ord(char) + 120774)
        else:
            result += char
    return result

def CB(text, style="primary", icon=None, **kwargs):
    if "ADMIN" in text.upper() or "OWNER" in text.upper():
        style = "danger"
    else:
        try:
            global db
            if 'db' in globals() and db is not None:
                custom_style = db.get_setting(f"color_{text}")
                if custom_style:
                    style = custom_style
        except Exception:
            pass
    
    # Apply monospace font for button UI
    mono_text = to_monospace(text)
    return ColoredButton(mono_text, style=style, icon=icon, **kwargs)

def get_category_emoji(category):
    cat = (category or "").upper()
    if "ROOT" in cat and "NON" not in cat:
        return get_button_emoji("android_root")
    if "PC" in cat:
        return get_button_emoji("pc")
    if "IOS" in cat:
        return get_button_emoji("ios")
    return get_button_emoji("android_nonroot")

# ============================================
# SEPARATOR
# ============================================

SEP = "|||"

def encode_cb(*args):
    return SEP.join([str(arg) for arg in args])

def decode_cb(data):
    return data.split(SEP)

logging.basicConfig(
    format='%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("KaranPayBot")

# ============================================
# 🎲 RANDOM AMOUNT GENERATOR
# ============================================

def generate_random_amount(base_amount):
    decimals = [0.1, 0.3, 0.5, 0.7, 0.9]
    random_decimal = random.choice(decimals)
    
    if float(base_amount).is_integer():
        return float(base_amount) + random_decimal
    else:
        return float(base_amount)

# ============================================
# DATABASE
# ============================================


class Database:
    def __init__(self):
        self.client = MongoClient(
            "mongodb+srv://notchff644_db_user:n6ghmq4Cuz3ViMcf@cluster0.pqt6pea.mongodb.net/?appName=Cluster0",
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
        )
        self.db = self.client["karanpay_bot"]
        logger.info("🗄️ MongoDB Database ready!")

    def get_setting(self, key):
        doc = self.db.bot_settings.find_one({"key": key})
        return doc["value"] if doc else None

    def set_setting(self, key, value):
        self.db.bot_settings.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

    def delete_setting(self, key):
        self.db.bot_settings.delete_one({"key": key})


    def get_emoji(self, name, default=""):
        return self.get_setting(f"emoji_{name}") or default

    def set_emoji(self, name, emoji_id):
        self.set_setting(f"emoji_{name}", emoji_id)

    def get_text(self, name, default=""):
        return self.get_setting(f"text_{name}") or default

    def set_text(self, name, text):
        self.set_setting(f"text_{name}", text)

    def get_welcome_media(self):
        media_type = self.get_setting("welcome_media_type")
        file_id = self.get_setting("welcome_media_file_id")
        if media_type and file_id:
            return media_type, file_id
        return None, None

    def set_welcome_media(self, media_type, file_id):
        self.set_setting("welcome_media_type", media_type)
        self.set_setting("welcome_media_file_id", file_id)

    def clear_welcome_media(self):
        self.delete_setting("welcome_media_type")
        self.delete_setting("welcome_media_file_id")

    def get_screen_media(self, screen_key):
        media_type = self.get_setting(f"screen_media_type:{screen_key}")
        file_id = self.get_setting(f"screen_media_file_id:{screen_key}")
        if media_type and file_id:
            return media_type, file_id
        return None, None

    def set_screen_media(self, screen_key, media_type, file_id):
        self.set_setting(f"screen_media_type:{screen_key}", media_type)
        self.set_setting(f"screen_media_file_id:{screen_key}", file_id)

    def clear_screen_media(self, screen_key):
        self.delete_setting(f"screen_media_type:{screen_key}")
        self.delete_setting(f"screen_media_file_id:{screen_key}")

    def init_user(self, user_id, username):
        user = self.db.users.find_one({"user_id": user_id})
        if not user:
            self.db.users.insert_one({
                "user_id": user_id,
                "username": username,
                "balance": 0.0,
                "is_reseller": 0,
                "referred_by": None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })


    def get_all_user_ids(self):
        return [str(u["user_id"]) for u in self.db.users.find({}, {"user_id": 1})]

    def get_recent_users(self, limit=20):
        users = self.db.users.find().sort("created_at", -1).limit(limit)
        return [(u["user_id"], u["username"], u["balance"]) for u in users]

    def set_reseller(self, user_id, is_reseller: bool):
        result = self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_reseller": 1 if is_reseller else 0}}
        )
        return result.modified_count > 0

    def is_reseller(self, user_id):
        user = self.db.users.find_one({"user_id": user_id})
        return bool(user.get("is_reseller", 0)) if user else False

    def get_resellers(self):
        users = self.db.users.find({"is_reseller": 1})
        return [(u["user_id"], u["username"]) for u in users]

    def set_referrer(self, user_id, referrer_id):
        user = self.db.users.find_one({"user_id": user_id})
        if user and not user.get("referred_by"):
            self.db.users.update_one({"user_id": user_id}, {"$set": {"referred_by": referrer_id}})
            return True
        return False

    def get_referrer(self, user_id):
        user = self.db.users.find_one({"user_id": user_id})
        return user.get("referred_by") if user else None

    def get_referral_stats(self, user_id):
        total_referred = self.db.users.count_documents({"referred_by": user_id})
        
        # Aggregate earnings
        pipeline = [
            {"$match": {"referrer_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$bonus_amount"}}}
        ]
        result = list(self.db.referral_earnings.aggregate(pipeline))
        total_earnings = result[0]["total"] if result else 0.0
        
        return {"total_referred": total_referred, "total_earnings": total_earnings}

    def get_stats(self):
        total_users = self.db.users.count_documents({})
        
        pipeline_bal = [{"$group": {"_id": None, "total": {"$sum": "$balance"}}}]
        bal_res = list(self.db.users.aggregate(pipeline_bal))
        total_balance = bal_res[0]["total"] if bal_res else 0.0
        
        total_orders = self.db.orders.count_documents({"status": "completed"})
        
        pipeline_ord = [{"$match": {"status": "completed"}}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
        ord_res = list(self.db.orders.aggregate(pipeline_ord))
        total_spent = ord_res[0]["total"] if ord_res else 0.0

        return total_users, total_balance, total_orders, total_spent

    def get_user(self, user_id):
        user = self.db.users.find_one({"user_id": user_id})
        if user:
            return (user["user_id"], user["username"], user["balance"], user.get("is_reseller", 0))
        return None

    def get_balance(self, user_id):
        user = self.db.users.find_one({"user_id": user_id})
        return user["balance"] if user else 0.0

    def update_balance(self, user_id, amount):
        self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )

    def deduct_balance(self, user_id, amount):
        user = self.db.users.find_one({"user_id": user_id})
        if user and user.get("balance", 0.0) >= float(amount):
            self.db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": -float(amount)}}
            )
            return True
        return False

    def create_order(self, order_id, user_id, amount):
        self.db.orders.insert_one({
            "order_id": order_id,
            "user_id": user_id,
            "amount": amount,
            "status": "pending",
            "utr": "",
            "sender": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    def update_order(self, order_id, status, utr="", sender=""):
        self.db.orders.update_one(
            {"order_id": order_id},
            {"$set": {"status": status, "utr": utr, "sender": sender}}
        )

    def complete_order_atomic(self, order_id, utr="", sender=""):
        result = self.db.orders.update_one(
            {"order_id": order_id, "status": "pending"},
            {"$set": {"status": "completed", "utr": utr, "sender": sender}}
        )
        return result.modified_count > 0

    def get_order(self, order_id):
        order = self.db.orders.find_one({"order_id": order_id})
        if order:
            return (order["order_id"], order["user_id"], order["amount"], order["status"], order["utr"], order["sender"], order["timestamp"])
        return None

    def get_pending_by_amount(self, amount):
        orders = self.db.orders.find({"amount": amount, "status": "pending"})
        return [(o["order_id"], o["user_id"], o["amount"], o["status"], o["utr"], o["sender"]) for o in orders]

    def get_all_pending(self):
        orders = self.db.orders.find({"status": "pending"})
        return [(o["order_id"], o["user_id"], o["amount"], o["status"], o["utr"], o["sender"]) for o in orders]

    def get_user_orders(self, user_id, limit=10):
        orders = self.db.orders.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return [(o["order_id"], o["amount"], o["status"], o["timestamp"]) for o in orders]

    def add_history(self, user_id, product, plan, price, license_key, android_id=""):
        self.db.history.insert_one({
            "user_id": user_id,
            "product": product,
            "plan": plan,
            "price": price,
            "license_key": license_key,
            "android_id": android_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    def get_history(self, user_id, limit=5):
        hist = self.db.history.find({"user_id": {"$in": [user_id, str(user_id)]}}).sort("date", -1).limit(limit)
        return [(str(h.get("_id", "")), h.get("user_id", user_id), h.get("product", "Unknown"), h.get("plan", "Unknown"), h.get("price", 0), h.get("license_key", ""), h.get("android_id", ""), h.get("date", "")) for h in hist]

    def get_products(self):
        products = self.db.products.find({}).sort([("order", 1), ("name", 1)])
        d = {}
        for p in products:
            cat = p.get("category", "")
            name = p.get("name", "")
            if not cat or not name: continue
            
            if cat not in d:
                d[cat] = {}
            if name not in d[cat]:
                d[cat][name] = {
                    "product_id": p.get("product_id"),
                    "plans": {},
                    "plan_ids": {},
                    "android_id": p.get("android_id", "0b9b969bc2e7997b")
                }
            
            plan_name = p.get("plan_name", "")
            if plan_name:
                d[cat][name]["plans"][plan_name] = p.get("price", 0)
                d[cat][name]["plan_ids"][plan_name] = p.get("id")
                
        cat_order_str = self.get_setting("category_order")
        if cat_order_str:
            order_list = [c.strip() for c in cat_order_str.split(",")]
            sorted_d = {}
            for c in order_list:
                if c in d:
                    sorted_d[c] = d[c]
            for c in d:
                if c not in sorted_d:
                    sorted_d[c] = d[c]
            return sorted_d
        return d

    def get_plan_by_id(self, plan_row_id):
        plan = self.db.products.find_one({"id": int(plan_row_id)})
        if plan:
            return {
                "category": plan["category"],
                "name": plan["name"],
                "product_id": plan["product_id"],
                "plan": plan["plan_name"],
                "price": plan["price"],
                "android_id": plan.get("android_id", "0b9b969bc2e7997b")
            }
        return None

    def get_all_products_flat(self):
        products = self.db.products.find({}).sort([("order", 1), ("name", 1)])
        grouped = {}
        for p in products:
            key = (p.get("category", ""), p.get("name", ""))
            grouped[key] = grouped.get(key, 0) + 1
            
        flat_list = [(cat, name, count) for (cat, name), count in grouped.items() if cat and name]
        
        cat_order_str = self.get_setting("category_order")
        if cat_order_str:
            order_list = [c.strip() for c in cat_order_str.split(",")]
            order_map = {c: i for i, c in enumerate(order_list)}
            flat_list.sort(key=lambda x: order_map.get(x[0], 99999))
            
        return flat_list

    def add_product(self, category, name, product_id, plan, price, android_id):
        # Find max id to simulate autoincrement
        max_doc = self.db.products.find_one(sort=[("id", -1)])
        new_id = (max_doc["id"] + 1) if max_doc and "id" in max_doc else 1
        self.db.products.insert_one({
            "id": new_id,
            "category": category,
            "name": name,
            "product_id": product_id,
            "plan_name": plan,
            "price": price,
            "android_id": android_id
        })

    def delete_product(self, category, name):
        self.db.products.delete_many({"category": category, "name": name})

    def update_product_price(self, plan_row_id, new_price):
        res = self.db.products.update_one({"id": int(plan_row_id)}, {"$set": {"price": new_price}})
        return res.modified_count > 0 or res.matched_count > 0

    def set_product_voice(self, product_id, voice_file_id):
        self.db.products.update_many({"product_id": product_id}, {"$set": {"voice_file_id": voice_file_id}})

    def set_product_link(self, product_id, link):
        self.db.products.update_many({"product_id": product_id}, {"$set": {"product_link": link}})

    def init_products(self):
        # Legacy initialization. Not needed strictly if we migrated, 
        # but to keep the signature intact.
        count = self.db.products.count_documents({})
        if count == 0:
            logger.info("Initializing 51 blank products...")
            for i in range(1, 52):
                self.add_product("Default", f"Product {i}", f"prod_{i}", "Lifetime", 99.0, "0b9b969bc2e7997b")

    def add_deposit_history(self, user_id, order_id, amount, utr="", sender="", status="completed"):
        self.db.deposit_history.insert_one({
            "user_id": user_id,
            "order_id": order_id,
            "amount": amount,
            "utr": utr,
            "sender": sender,
            "status": status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    def get_deposit_history(self, user_id, limit=10):
        deps = self.db.deposit_history.find({"user_id": {"$in": [user_id, str(user_id)]}}).sort("timestamp", -1).limit(limit)
        return [(d["order_id"], d["amount"], d.get("utr", "-"), d.get("sender", "-"), d["status"], d["timestamp"]) for d in deps]

db = Database()
db.init_products()

# ============================================
# 💳 KARANPAY PAYMENT GATEWAY
# ============================================

def get_karanpay_key(order_id):
    if order_id.startswith("ADD2_"):
        return KARANPAY_KEY_2
    return KARANPAY_KEY_1

def create_karanpay_order(amount, order_id, customer_name):
    import re
    # Use dynamic key based on order_id
    key = get_karanpay_key(order_id)
    payload = {
        "amount": f"{float(amount):.2f}",
        "order_id": order_id,
        "customer_name": customer_name,
    }
    headers = {
        "X-Guru-Key": key,
        "Content-Type": "application/json"
    }
    logger.info(f"📤 Creating KaranPay order → {order_id} | ₹{amount} | {customer_name}")
    try:
        resp = requests.post(KARANPAY_CREATE_URL, json=payload, headers=headers, timeout=20)
        data = resp.json()
        if data.get("status") == "success":
            payment_url = data.get("data", {}).get("payment_url") or data.get("payment_url")
            if payment_url:
                logger.info(f"🔗 Order {order_id} created → {payment_url}")
                upi_url = payment_url
                try:
                    html_resp = requests.get(payment_url, timeout=10).text
                    matches = re.findall(r'upi://pay\?[^\"\'<>]+', html_resp)
                    if matches:
                        upi_url = matches[0]
                        logger.info(f"✅ Extracted UPI Intent: {upi_url}")
                except Exception as ex:
                    logger.error(f"Failed to extract UPI intent: {ex}")
                return payment_url, upi_url, None
        logger.warning(f"⚠️ KaranPay create-order failed for {order_id}: {data}")
        return None, None, data.get("message") or "Order create nahi ho paaya."
    except Exception as e:
        logger.error(f"❌ KaranPay create-order error for {order_id}: {e}")
        return None, None, str(e)


def check_karanpay_status(order_id):
    key = get_karanpay_key(order_id)
    headers = {
        "X-Guru-Key": key,
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(KARANPAY_STATUS_URL, json={"order_id": order_id}, headers=headers, timeout=20)
        data = resp.json()
        if data.get("status") == "success":
            d = data.get("data", {})
            if d.get("payment_status") == "success":
                logger.info(f"💰 Payment CONFIRMED for {order_id} | UTR: {d.get('utr', 'N/A')} | ₹{d.get('amount')}")
                return d
        return None
    except Exception as e:
        logger.error(f"❌ KaranPay check-status error for {order_id}: {e}")
        return None


def generate_qr_image(data_str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio

def generate_ref_code():
    return "DBX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

import cloudscraper
global_scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def fetch_license_key(product_id, duration, android_id=ANDROID_ID):
    payload = {
        'api_key': API_KEY,
        'action': 'buy',
        'product_id': str(product_id),
        'duration': str(duration),
        'android_id': android_id
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-master-key': MASTER_KEY
    }
    try:
        response = global_scraper.post(API_ENDPOINT, data=payload, headers=headers, timeout=30)
        logger.info(f"API Response: {response.text}")
        
        try:
            res_data = response.json()
            if isinstance(res_data, dict):
                if "key" in res_data:
                    return res_data["key"]
                if "license" in res_data:
                    return res_data["license"]
                if "message" in res_data:
                    return f"Error: {res_data['message']}"
                if "msg" in res_data:
                    return f"Error: {res_data['msg']}"
                return f"Error: {str(res_data)}"
        except:
            pass
        
        if response.status_code != 200:
            return f"Error: API HTTP {response.status_code}"
            
        text_resp = response.text.strip()
        if "<!DOCTYPE" in text_resp.upper() or "<HTML" in text_resp.upper():
            return "Error: API is down (Returned HTML page)"
            
        if text_resp and "Error" not in text_resp:
            return text_resp
        
        return f"Error: Unknown response"
            
    except Exception as e:
        logger.error(f"API Request Failed: {e}")
        return f"Error: {str(e)}"

# ============================================
# 💳 AUTO-PAYMENT MONITOR (KaranPay)
# ============================================

class KaranPayMonitor:
    def __init__(self, db, bot):
        self.db = db
        self.bot = bot
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
        logger.info("🟢 KaranPay auto-payment monitor started!")

    def stop(self):
        self.running = False

    def _monitor(self):
        while self.running:
            try:
                self._check_pending_orders()
            except Exception as e:
                logger.error(f"⚠️ Monitor error: {e}")
            time.sleep(10)

    def _check_pending_orders(self):
        pending = self.db.get_all_pending()
        for p in pending:
            order_id, user_id, amount = p[0], p[1], p[2]
            result = check_karanpay_status(order_id)
            if not result:
                continue

            utr = result.get("utr", "N/A")
            paid_amount = result.get("amount", amount)
            sender = result.get("customer_name", "Unknown")
            if self.db.complete_order_atomic(order_id, utr, sender):
                self.db.update_balance(user_id, paid_amount)
                self.db.add_deposit_history(user_id, order_id, paid_amount, utr, sender)
                logger.info(f"✅ Order {order_id} COMPLETED via KaranPay! (User: {user_id}, ₹{paid_amount})")

                try:
                    self._send_user_success(user_id, order_id, paid_amount, utr, sender)
                except Exception:
                    pass
                self._credit_referral(user_id, paid_amount)

    def _send_user_success(self, user_id, order_id, amount, utr, sender):
        msg = f"""
<tg-emoji emoji-id="6235234890980269200">✅</tg-emoji> <b>PAYMENT AUTO-VERIFIED!</b>
━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji> <b>Order ID:</b> <code>{order_id}</code>
<tg-emoji emoji-id="6215156189454409086">💰</tg-emoji> <b>Amount:</b> ₹{amount:.2f}
<tg-emoji emoji-id="6034969813032374911">🧾</tg-emoji> <b>UTR:</b> <code>{utr}</code>
<tg-emoji emoji-id="6215104357789081549">👤</tg-emoji> <b>Sender:</b> {sender}
━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="6033106828018062225">💰</tg-emoji> ₹{amount:.2f} added to your wallet!
"""
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": int(user_id), "text": msg, "parse_mode": "HTML"},
                timeout=10
            )
        except:
            pass
            
        notify_admin_deposit(user_id, order_id, amount, utr, sender)

    def _credit_referral(self, referred_user_id, deposit_amount):
        try:
            referrer_id = self.db.get_referrer(referred_user_id)
            if not referrer_id:
                return
            bonus = self.db.credit_referral_bonus(referrer_id, referred_user_id, deposit_amount, REFERRAL_COMMISSION_PERCENT)
            if bonus and bonus > 0:
                logger.info(f"🎁 Referral bonus: ₹{bonus:.2f} → {referrer_id} (from {referred_user_id}'s ₹{deposit_amount:.2f} deposit)")
                msg = (
                    f'<tg-emoji emoji-id="6242389503336518600">🎉</tg-emoji> <b>REFERRAL BONUS!</b>\n\n'
                    f"Aapke referral se ek user ne ₹{deposit_amount:.2f} deposit kiya.\n"
                    f'<tg-emoji emoji-id="6033106828018062225">💰</tg-emoji> <b>₹{bonus:.2f}</b> aapke wallet mein add ho gaye!'
                )
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        json={"chat_id": int(referrer_id), "text": msg, "parse_mode": "HTML"},
                        timeout=10
                    )
                except:
                    pass
        except Exception as e:
            logger.warning(f"Referral credit failed: {e}")

# ============================================
# 🔵 KEYBOARDS - ONLY PREMIUM EMOJIS IN BUTTONS
# ============================================

def get_main_menu_keyboard(is_admin=False):
    rows = [
        [CB("Product Store", style="primary", icon=get_button_emoji("shop"), callback_data="menu_shop")],
        [CB("My Profile", style="primary", icon=get_button_emoji("profile"), callback_data="menu_profile"),
         CB("Add Balance", style="success", icon=get_button_emoji("add_balance"), callback_data="menu_add_balance")],

        [CB("Order History", style="primary", icon=get_button_emoji("order_history"), callback_data="menu_history"),
         CB("Deposit History", style="primary", icon=get_button_emoji("deposit_history"), callback_data="menu_deposit_history")],
        [CB("Referral", style="primary", icon=get_button_emoji("referral"), callback_data="menu_referral"),
         CB("Tutorial", style="primary", icon=get_button_emoji("tutorial"), callback_data="menu_tutorial")],
        [CB("Support", style="primary", icon=get_button_emoji("support"), callback_data="menu_support"),
         CB("Download Hack", style="danger", icon=get_button_emoji("download"), callback_data="menu_download")],
        [CB("Transfer Balance", style="success", icon=get_button_emoji("star"), callback_data="transfer_balance_start")]
    ]
    if is_admin:
        rows.append([CB("ADMIN PANEL", style="danger", icon=get_button_emoji("warning"), callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)

def get_admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [CB("Broadcast", style="danger", icon=get_button_emoji("broadcast"), callback_data="admin_broadcast"),
         CB("Manage Devices", style="danger", icon=get_button_emoji("star"), callback_data="admin_devices")],
        [CB("Add Product", style="danger", icon=get_button_emoji("add"), callback_data="admin_addproduct"),
         CB("Remove Product", style="danger", icon=get_button_emoji("remove"), callback_data="admin_removeproduct")],
        [CB("Change Price", style="danger", icon=get_button_emoji("add_balance"), callback_data="admin_changeprice"),
         CB("Set Voice/Link", style="danger", icon=get_button_emoji("star"), callback_data="admin_voicelink")],
        [CB("Add Balance", style="danger", icon=get_button_emoji("add_balance"), callback_data="admin_addbalance"),
         CB("Remove Balance", style="danger", icon=get_button_emoji("remove"), callback_data="admin_removebalance")],
        [CB("Manage Resellers", style="danger", icon=get_button_emoji("star"), callback_data="admin_resellers"),
         CB("Stats", style="danger", icon=get_button_emoji("stats"), callback_data="admin_stats")],
        [CB("Users", style="danger", icon=get_button_emoji("users"), callback_data="admin_users"),
         CB("Welcome Media", style="danger", icon=get_button_emoji("star"), callback_data="admin_welcomemedia")],
        [CB("Menu Media", style="danger", icon=get_button_emoji("star"), callback_data="admin_menumedia"),
         CB("Manage Texts", style="danger", icon=get_button_emoji("tutorial"), callback_data="admin_texts")],
        [CB("Manage Emojis", style="danger", icon=get_button_emoji("star"), callback_data="admin_emojis"),
         CB("Button Colors", style="danger", icon=get_button_emoji("star"), callback_data="admin_colors")],
        [CB("Maintenance Mode", style="danger", icon=get_button_emoji("star"), callback_data="admin_maintenance_menu"),
         CB("Export Users", style="danger", icon=get_button_emoji("clear"), callback_data="admin_export_users")],
        [CB("Reorder Store", style="danger", icon=get_button_emoji("star"), callback_data="admin_reorder_store"),
         CB("Manage Captions", style="danger", icon=get_button_emoji("tutorial"), callback_data="admin_manage_captions")],
        [CB("Welcome Reaction", style="danger", icon=get_button_emoji("star"), callback_data="admin_welcome_reaction")],
        [CB("Back to Menu", style="danger", icon=get_button_emoji("back"), callback_data="back_to_menu")]
    ])

def get_welcome_media_keyboard(current_type):
    rows = [
        [CB("Set Welcome Photo", style="primary", icon=get_button_emoji("add"), callback_data="admin_setwelcomephoto")],
        [CB("Set Welcome Video", style="primary", icon=get_button_emoji("add"), callback_data="admin_setwelcomevideo")],
    ]
    if current_type:
        rows.append([CB("Remove Welcome Media", style="danger", icon=get_button_emoji("remove"), callback_data="admin_removewelcomemedia")])
    rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)

def get_reseller_panel_keyboard():
    return InlineKeyboardMarkup([
        [CB("Add Reseller", style="success", icon=get_button_emoji("add"), callback_data="admin_addreseller")],
        [CB("Remove Reseller", style="danger", icon=get_button_emoji("remove"), callback_data="admin_removereseller")],
        [CB("List Resellers", style="primary", icon=get_button_emoji("users"), callback_data="admin_listresellers")],
        [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]
    ])

def get_numeric_keypad():
    return InlineKeyboardMarkup([
        [CB("1", style="primary", callback_data="kp_1"), 
         CB("2", style="primary", callback_data="kp_2"), 
         CB("3", style="primary", callback_data="kp_3")],
        [CB("4", style="primary", callback_data="kp_4"), 
         CB("5", style="primary", callback_data="kp_5"), 
         CB("6", style="primary", callback_data="kp_6")],
        [CB("7", style="primary", callback_data="kp_7"), 
         CB("8", style="primary", callback_data="kp_8"), 
         CB("9", style="primary", callback_data="kp_9")],
        [CB("Clear", style="danger", icon=get_button_emoji("clear"), callback_data="kp_clear"),
         CB("0", style="primary", callback_data="kp_0"),
         CB("Confirm", style="success", icon=get_button_emoji("confirm"), callback_data="kp_confirm")],
        [CB("BACK", style="danger", icon=get_button_emoji("back"), callback_data="back_to_menu")]
    ])

def get_verify_button(order_id):
    return InlineKeyboardMarkup([
        [CB("Verify Payment", style="success", icon=get_button_emoji("confirm"), callback_data=f"verify_{order_id}")],
        [CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="menu_add_balance")]
    ])

def get_back_button():
    return InlineKeyboardMarkup([
        [CB("Back", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]
    ])

# ============================================
# 📱 ANDROID ID HANDLERS - NEW
# ============================================

async def ask_android_id(update: Update, context: ContextTypes.DEFAULT_TYPE, product_data):
    """Ask user to enter their Android ID for BALA MOD products"""
    query = update.callback_query
    
    # Store product data in context
    context.user_data["pending_product"] = product_data
    context.user_data["awaiting_android_id"] = True
    
    text = f"""
🔐 <b>ANDROID ID REQUIRED</b>

📦 <b>Product:</b> {product_data['name']}
⏳ <b>Plan:</b> {product_data['plan']}
💰 <b>Price:</b> ₹{product_data['price']}

━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>BALA MOD requires your Android ID</b>

📱 <b>How to get Android ID:</b>
1️⃣ Open your Free Fire app
2️⃣ Go to Settings → About
3️⃣ Copy your Android Device ID

OR use any Android ID finder app.

━━━━━━━━━━━━━━━━━━━━━

✏️ <b>Send your Android ID now:</b>
<code>Example: 0b9b969bc2e7997b</code>

Type <b>/cancel</b> to cancel purchase.
"""
    
    keyboard = [
        [CB("❌ Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="cancel_purchase")]
    ]
    
    await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's general text inputs (Android ID, Transfer)"""
    user_id = str(update.effective_user.id)
    text_input = (update.message.text or "").strip()
    
    if text_input.lower() == "/cancel":
        context.user_data["awaiting_android_id"] = False
        context.user_data["awaiting_transfer_userid"] = False
        context.user_data["awaiting_transfer_amount"] = False
        context.user_data["pending_product"] = None
        await update.message.reply_text("❌ Action cancelled.")
        return

    if context.user_data.get("awaiting_android_id"):
        if not re.match(r'^[0-9a-fA-F]{16}$', text_input):
            await update.message.reply_text("❌ <b>Invalid Android ID!</b>\nAndroid ID should be 16 characters (hex).\nExample: <code>0b9b969bc2e7997b</code>\nPlease send again or type /cancel", parse_mode="HTML")
            return
        product_data = context.user_data.get("pending_product")
        if not product_data:
            await update.message.reply_text("❌ Session expired. Please start again.")
            return
        context.user_data["awaiting_android_id"] = False
        context.user_data["pending_product"] = None
        await process_purchase_with_android_id(update, context, product_data, text_input)
        return

    if context.user_data.get("awaiting_transfer_userid"):
        if text_input.isdigit():
            target_user = db.get_user(text_input)
        elif text_input.startswith("@") or text_input.isalnum() or "_" in text_input:
            clean_username = text_input.lstrip("@")
            user_doc = db.db.users.find_one({"username": {"$regex": f"^{clean_username}$", "$options": "i"}})
            target_user = (user_doc["user_id"], user_doc.get("username")) if user_doc else None
        else:
            await update.message.reply_text("❌ Invalid Input. Must be a User ID or @username. Type /cancel to abort.")
            return

        if not target_user:
            await update.message.reply_text("❌ User not found! Please check the ID/Username and try again, or type /cancel.")
            return
            
        target_id = str(target_user[0])
        if target_id == user_id:
            await update.message.reply_text("❌ You cannot transfer balance to yourself! Type /cancel to abort.")
            return
            
        context.user_data["awaiting_transfer_userid"] = False
        context.user_data["transfer_target_id"] = target_id
        context.user_data["awaiting_transfer_amount"] = True
        
        username = f"@{target_user[1]}" if target_user[1] else target_id
        
        default_amount_prompt = "<tg-emoji emoji-id=\"6267291337171670780\">✅</tg-emoji> User found: {username}\n\n<tg-emoji emoji-id=\"5262559368351602280\">💸</tg-emoji> <b>Enter Amount to Transfer:</b>\n(Min ₹1)\nType /cancel to abort."
        prompt_template = get_text_safe("transfer_amount_caption", default_amount_prompt)
        text_to_send = prompt_template.replace("{username}", username)
        
        await update.message.reply_text(text_to_send, parse_mode="HTML")
        return

    if context.user_data.get("awaiting_transfer_amount"):
        try:
            amt = float(text_input)
            if amt < 1:
                raise ValueError()
        except:
            await update.message.reply_text("❌ Invalid amount. Must be a number >= 1. Type /cancel to abort.")
            return
        sender_balance = db.get_balance(user_id)
        if sender_balance < amt:
            await update.message.reply_text(f"❌ Insufficient balance! You have ₹{sender_balance:.2f}. Type /cancel to abort.")
            return
        target_id = context.user_data["transfer_target_id"]
        db.update_balance(user_id, -amt)
        db.update_balance(target_id, amt)
        context.user_data["awaiting_transfer_amount"] = False
        context.user_data["transfer_target_id"] = None
        sender_new = db.get_balance(user_id)
        
        default_success_msg = "<tg-emoji emoji-id=\"6267291337171670780\">✅</tg-emoji> <b>Transfer Successful!</b>\n\nSent ₹{amt} to <code>{target_id}</code>\nYour new balance: ₹{sender_new}"
        success_template = get_text_safe("transfer_success_msg", default_success_msg)
        success_text = success_template.replace("{amt}", f"{amt:.2f}").replace("{target_id}", target_id).replace("{sender_new}", f"{sender_new:.2f}")
        
        await update.message.reply_text(success_text, parse_mode="HTML")
        try:
            default_received_msg = "💰 <b>You received ₹{amt}!</b>\nFrom User ID: <code>{user_id}</code>"
            received_template = get_text_safe("transfer_received_msg", default_received_msg)
            received_text = received_template.replace("{amt}", f"{amt:.2f}").replace("{user_id}", user_id)
            await context.bot.send_message(chat_id=int(target_id), text=received_text, parse_mode="HTML")
        except:
            pass
        return

async def process_purchase_with_android_id(update: Update, context: ContextTypes.DEFAULT_TYPE, product_data, android_id):
    """Process purchase with user's Android ID"""
    user_id = str(update.effective_user.id)
    
    product_name = product_data['name']
    plan_name = product_data['plan']
    product_id = product_data['product_id']
    price = product_data['price']
    
    # Deduct balance
    if not db.deduct_balance(user_id, price):
        await update.message.reply_text("❌ Insufficient balance!")
        return
    
    await update.message.reply_text("⏳ Processing your order with your Android ID...")
    
    # Fetch license key with user's Android ID
    license_key = fetch_license_key(product_id, plan_name, android_id)
    
    if "Error:" in str(license_key):
        # Refund if failed
        db.update_balance(user_id, price)
        admin_user = db.db.users.find_one({"user_id": str(ADMIN_ID)})
        admin_username = f"@{admin_user['username']}" if admin_user and admin_user.get("username") else "the Owner"
        
        await update.message.reply_text(
            f"❌ <b>Purchase Failed!</b>\n\nServer problem, contact owner {admin_username}\n\n💰 Your balance has been refunded.",
            parse_mode="HTML"
        )
        return
    
    # Save to history with android_id
    db.add_history(user_id, product_name, plan_name, price, license_key, android_id)
    
    # Success message
    text = f"""
<tg-emoji emoji-id="6073308817125282940">⭐</tg-emoji> <b>PURCHASE SUCCESSFUL!</b>

📦 <b>Product:</b> {product_name}
⏳ <b>Validity:</b> {plan_name}
💰 <b>Price:</b> ₹{price}
📱 <b>Android ID:</b> <code>{android_id}</code>

<tg-emoji emoji-id="6071312005224993914">⭐</tg-emoji> <b>YOUR LICENSE KEY:</b>
<code>{license_key}</code>

✅ Key saved to history!
"""
    
    keyboard = [[CB("Main Menu", style="primary", icon=get_button_emoji("shop"), callback_data="back_to_menu")]]
    
    await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    product_doc = db.db.products.find_one({"product_id": product_id})
    if product_doc:
        voice_id = product_doc.get("voice_file_id")
        link = product_doc.get("product_link")
        if voice_id:
            try: await context.bot.send_voice(chat_id=update.effective_chat.id, voice=voice_id)
            except Exception: pass
        if link:
            try: await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔗 <b>Product Link:</b>\n{link}", parse_mode="HTML")
            except Exception: pass

# ============================================
# 📢 BROADCAST
# ============================================

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):
        await update.message.reply_text("❌ You are not authorized!")
        return

    context.user_data["awaiting_broadcast"] = True
    await update.message.reply_text(
        "📢 <b>Broadcast Mode ON</b>\n\n"
        "Ab jo bhi message bhejoge (text, photo, video, voice, audio, document, sticker — kuch bhi) "
        "wo sabhi users ko bhej diya jaayega.\n\n"
        "Cancel karne ke liye /cancel bhejo.",
        parse_mode="HTML"
    )

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):
        return
    flags = ["awaiting_broadcast", "awaiting_addproduct", "awaiting_addbalance", "awaiting_removebalance",
             "awaiting_addreseller", "awaiting_removereseller", "awaiting_android_id",
             "awaiting_newprice_id", "awaiting_welcome_photo", "awaiting_welcome_video",
             "awaiting_screen_photo", "awaiting_screen_video", "awaiting_text_key", "awaiting_emoji_key"]
    was_active = any(context.user_data.get(f) for f in flags)
    for f in flags:
        context.user_data[f] = False
    if was_active:
        await update.message.reply_text("❌ Cancelled.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):
        return

    if context.user_data.get("awaiting_welcome_reaction"):
        context.user_data["awaiting_welcome_reaction"] = False
        if (update.message.text or "").strip() == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
            
        emoji_id = ""
        # Check if premium emoji
        if update.message.entities:
            for ent in update.message.entities:
                if ent.type == "custom_emoji":
                    emoji_id = ent.custom_emoji_id
                    break
                    
        if emoji_id:
            db.set_setting("welcome_reaction", emoji_id)
            await update.message.reply_text(f"✅ Welcome reaction updated to premium custom emoji: {emoji_id}\n\n⚠️ <b>NOTE:</b> Telegram bots CANNOT use premium custom emojis as reactions in private chats! Only standard emojis (👍, ❤️, 🔥, 🎉) work. If the reaction doesn't appear on /start, please change it to a standard emoji.", parse_mode="HTML")
        else:
            # Assume it's a standard emoji
            emoji_str = (update.message.text or "").strip()
            if len(emoji_str) > 0:
                db.set_setting("welcome_reaction", emoji_str)
                await update.message.reply_text(f"✅ Welcome reaction updated to standard emoji: {emoji_str}\n\n⚠️ <b>NOTE:</b> Telegram only allows a specific list of standard emojis for reactions (👍, ❤️, 🔥, 🎉, 🤩). If it doesn't appear on /start, it means Telegram blocked that specific emoji for bots.", parse_mode="HTML")
        return

    if context.user_data.get("awaiting_product_voice"):
        product_id = context.user_data["awaiting_product_voice"]
        text = (update.message.text or "").strip()
        if text == "/cancel":
            context.user_data["awaiting_product_voice"] = None
            await update.message.reply_text("❌ Cancelled.")
            return
        
        file_id = None
        if update.message.voice:
            file_id = update.message.voice.file_id
        elif update.message.audio:
            file_id = update.message.audio.file_id
            
        if file_id:
            db.set_product_voice(product_id, file_id)
            context.user_data["awaiting_product_voice"] = None
            await update.message.reply_text(f"✅ Voice message set for product!")
        else:
            await update.message.reply_text("❌ Please send a valid Voice or Audio message, or /cancel.")
        return

    if context.user_data.get("awaiting_product_link"):
        product_id = context.user_data["awaiting_product_link"]
        text = (update.message.text or "").strip()
        if text == "/cancel":
            context.user_data["awaiting_product_link"] = None
            await update.message.reply_text("❌ Cancelled.")
            return
            
        if not text.startswith("http"):
            text = "http://" + text
            
        db.set_product_link(product_id, text)
        context.user_data["awaiting_product_link"] = None
        await update.message.reply_text(f"✅ Link set for product!")
        return

    if context.user_data.get("awaiting_text_key"):
        key = context.user_data["awaiting_text_key"]
        text = (update.message.text or update.message.caption or "").strip()
        context.user_data["awaiting_text_key"] = None
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        
        # Sanitize text to prevent HTML parsing errors
        text = text.replace("& ", "&amp; ")
        if " & " in text: text = text.replace(" & ", " &amp; ")
        # Strip accidental Python string quotes if they copied the source code
        if text.startswith('f"') or text.startswith("f'"): text = text[2:]
        if text.startswith('"') or text.startswith("'"): text = text[1:]
        if text.endswith('"') or text.endswith("'"): text = text[:-1]
        text = text.replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n')
        
        db.set_text(key, text)
        await update.message.reply_text(f"✅ Text for {EDITABLE_TEXTS.get(key, key)} successfully updated!")
        return

    if context.user_data.get("awaiting_emoji_key"):
        key = context.user_data["awaiting_emoji_key"]
        context.user_data["awaiting_emoji_key"] = None
        text = (update.message.text or "").strip()
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
            
        emoji_id = text
        # If they sent a premium emoji, telegram puts it in entities
        if update.message.entities:
            for ent in update.message.entities:
                if ent.type == "custom_emoji":
                    emoji_id = ent.custom_emoji_id
                    break
                    
        if not emoji_id.isdigit():
            await update.message.reply_text("❌ Invalid Emoji. Please send a valid Premium Custom Emoji or an Emoji ID number.")
            return
            
        db.set_emoji(key, emoji_id)
        await update.message.reply_text(f"✅ Emoji for '{key}' successfully updated to: {emoji_id}")
        return

    if context.user_data.get("awaiting_newprice_id"):
        plan_row_id = context.user_data["awaiting_newprice_id"]
        context.user_data["awaiting_newprice_id"] = None
        text = (update.message.text or "").strip()
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        price_clean = re.sub(r'[^\d.]', '', text)
        if not price_clean:
            await update.message.reply_text("❌ Sirf number bhejo, jaise 150")
            return
        try:
            new_price = float(price_clean)
        except ValueError:
            await update.message.reply_text("❌ Sirf number bhejo, jaise 150")
            return
        if new_price <= 0:
            await update.message.reply_text("❌ Price 0 se zyada honi chahiye.")
            return
        updated = db.update_product_price(plan_row_id, new_price)
        if updated:
            await update.message.reply_text(f"✅ Price update ho gayi! Naya price: ₹{new_price:.2f}")
        else:
            await update.message.reply_text("❌ Plan nahi mila, update fail ho gaya.")
        return

    if context.user_data.get("awaiting_welcome_photo"):
        context.user_data["awaiting_welcome_photo"] = False
        if (update.message.text or "").strip() == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        if not update.message.photo:
            await update.message.reply_text("❌ Ye photo nahi hai. Ek photo bhejo, ya /cancel karo.")
            return
        file_id = update.message.photo[-1].file_id
        db.set_welcome_media("photo", file_id)
        await update.message.reply_text("✅ Welcome photo set ho gayi! Ab /start karke check kar lo.")
        return

    if context.user_data.get("awaiting_welcome_video"):
        context.user_data["awaiting_welcome_video"] = False
        if (update.message.text or "").strip() == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        if not update.message.video:
            await update.message.reply_text("❌ Ye video nahi hai. Ek video bhejo, ya /cancel karo.")
            return
        file_id = update.message.video.file_id
        db.set_welcome_media("video", file_id)
        await update.message.reply_text("✅ Welcome video set ho gayi! Ab /start karke check kar lo.")
        return

    if context.user_data.get("awaiting_screen_photo"):
        screen_key = context.user_data["awaiting_screen_photo"]
        context.user_data["awaiting_screen_photo"] = None
        if (update.message.text or "").strip() == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        if not update.message.photo:
            await update.message.reply_text("❌ Ye photo nahi hai. Ek photo bhejo, ya /cancel karo.")
            return
        file_id = update.message.photo[-1].file_id
        db.set_screen_media(screen_key, "photo", file_id)
        label = SCREEN_LABELS.get(screen_key, screen_key)
        await update.message.reply_text(f"✅ {label} ki photo set ho gayi!")
        return

    if context.user_data.get("awaiting_screen_video"):
        screen_key = context.user_data["awaiting_screen_video"]
        context.user_data["awaiting_screen_video"] = None
        if (update.message.text or "").strip() == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        if not update.message.video:
            await update.message.reply_text("❌ Ye video nahi hai. Ek video bhejo, ya /cancel karo.")
            return
        file_id = update.message.video.file_id
        db.set_screen_media(screen_key, "video", file_id)
        label = SCREEN_LABELS.get(screen_key, screen_key)
        await update.message.reply_text(f"✅ {label} ki video set ho gayi!")
        return

    if context.user_data.get("awaiting_addreseller"):
        context.user_data["awaiting_addreseller"] = False
        target_id = (update.message.text or "").strip()
        if not target_id.isdigit():
            await update.message.reply_text("❌ Invalid USER_ID.")
            return
        changed = db.set_reseller(target_id, True)
        if changed:
            await update.message.reply_text(f"✅ User <code>{target_id}</code> ab reseller hai ({RESELLER_DISCOUNT_PERCENT}% discount).", parse_mode="HTML")
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"👑 <b>Congratulations!</b> Aap ab Reseller ban gaye ho — sabhi products par {RESELLER_DISCOUNT_PERCENT}% discount milega!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ User not found. Pehle usko /start karwao.")
        return

    if context.user_data.get("awaiting_removereseller"):
        context.user_data["awaiting_removereseller"] = False
        target_id = (update.message.text or "").strip()
        if not target_id.isdigit():
            await update.message.reply_text("❌ Invalid USER_ID.")
            return
        changed = db.set_reseller(target_id, False)
        if changed:
            await update.message.reply_text(f"✅ User <code>{target_id}</code> ka reseller status hata diya.", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ User not found.")
        return

    if context.user_data.get("awaiting_addproduct"):
        context.user_data["awaiting_addproduct"] = False
        text = (update.message.text or "").strip()
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled.")
            return
        try:
            p = parse_product_line(text)
        except ValueError as e:
            await update.message.reply_text(f"❌ {e}")
            return

        try:
            db.add_product(p["category"], p["name"], p["product_id"], p["plan"], p["price"], p["android_id"])
            await update.message.reply_text(
                f"✅ Product Added!\n"
                f"📦 {p['name']}\n"
                f"⏳ {p['plan']}\n"
                f"💰 ₹{p['price']:.2f}\n"
                f"🆔 ID: {p['product_id']}\n"
                f"📂 Category: {p['category']}"
            )
        except Exception as e:
            logger.error(f"add_product DB error: {e}")
            await update.message.reply_text(f"❌ Product save nahi ho paya: {e}")
        return

    if context.user_data.get("awaiting_addbalance"):
        context.user_data["awaiting_addbalance"] = False
        try:
            text = (update.message.text or "").strip()
            target_id, amt = text.split()
            amt = float(amt)
            db.update_balance(target_id, amt)
            new_balance = db.get_balance(target_id)
            await update.message.reply_text(
                f"✅ ₹{amt:.2f} added to user <code>{target_id}</code>\n"
                f"💰 New balance: ₹{new_balance:.2f}",
                parse_mode="HTML"
            )
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"💰 <b>₹{amt:.2f} added to your wallet by admin!</b>\nNew balance: ₹{new_balance:.2f}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}\n\nFormat: USER_ID AMOUNT")
        return

    if context.user_data.get("awaiting_removebalance"):
        context.user_data["awaiting_removebalance"] = False
        try:
            text = (update.message.text or "").strip()
            target_id, amt = text.split()
            amt = float(amt)
            db.update_balance(target_id, -amt)
            new_balance = db.get_balance(target_id)
            await update.message.reply_text(
                f"✅ ₹{amt:.2f} removed from user <code>{target_id}</code>\n"
                f"💰 New balance: ₹{new_balance:.2f}",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}\n\nFormat: USER_ID AMOUNT")
        return

    if not context.user_data.get("awaiting_broadcast"):
        await handle_user_message(update, context)
        return

    context.user_data["awaiting_broadcast"] = False

    user_ids = db.get_all_user_ids()
    total = len(user_ids)
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(f"⏳ Broadcasting to {total} users...")

    for uid in user_ids:
        try:
            await context.bot.copy_message(
                chat_id=int(uid),
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed for {uid}: {e}")
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"📤 Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {total}",
        parse_mode="HTML"
    )

# ============================================
# BOT HANDLERS
# ============================================

SCREEN_LABELS = {
    "shop": "🛍 Store",
    "profile": "👤 My Profile",
    "history": "📜 Order History",
    "deposit_history": "💳 Deposit History",
    "referral": "⭐ Referral",
    "tutorial": "📘 Tutorial",
    "support": "🆘 Support",
    "download": "⬇️ Download Hack",
    "payment": "💳 Payment",
}

async def _safe_edit_text(msg, text, reply_markup, parse_mode):
    try:
        await msg.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        elif "Document_invalid" in str(e) or "entities" in str(e).lower():
            import re
            clean = re.sub(r'<tg-emoji[^>]*>', '', text).replace('</tg-emoji>', '')
            try:
                await msg.edit_text(text=clean, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as inner_e:
                import logging
                logging.getLogger("KaranPayBot").error(f"Inner safe edit failed silently: {inner_e}")
        else:
            raise

async def safe_edit(query, text, reply_markup=None, parse_mode="HTML"):
    """Edit the callback's message text — but if the current message is media
    (photo/video, e.g. a welcome/screen with custom media set), delete and
    resend as plain text, since Telegram can't text-edit a media message."""
    msg = query.message
    is_media = bool(msg.photo or msg.video or msg.document or msg.animation or msg.audio or msg.voice or msg.sticker)
    if is_media:
        try:
            await msg.delete()
        except Exception:
            pass
        await query.get_bot().send_message(chat_id=msg.chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        await _safe_edit_text(msg, text, reply_markup, parse_mode)

async def send_screen(query, text, reply_markup, screen_key=None, parse_mode="HTML"):
    """Like safe_edit, but if the admin set a custom photo/video for this
    screen (Admin Panel -> Menu Media), always render that media with the
    text as caption."""
    media_type, file_id = db.get_screen_media(screen_key) if screen_key else (None, None)
    msg = query.message
    is_media = bool(msg.photo or msg.video or msg.document or msg.animation or msg.audio or msg.voice or msg.sticker)

    try:
        if media_type and file_id:
            try:
                await msg.delete()
            except Exception:
                pass
            bot = query.get_bot()
            if media_type == "video":
                await bot.send_video(chat_id=msg.chat_id, video=file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await bot.send_photo(chat_id=msg.chat_id, photo=file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif is_media:
            try:
                await msg.delete()
            except Exception:
                pass
            await query.get_bot().send_message(chat_id=msg.chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await _safe_edit_text(msg, text, reply_markup, parse_mode)
    except BadRequest as e:
        if "Document_invalid" in str(e) or "entities" in str(e).lower():
            import re
            clean = re.sub(r'<tg-emoji[^>]*>', '', text).replace('</tg-emoji>', '')
            try:
                if media_type and file_id:
                    bot = query.get_bot()
                    if media_type == "video":
                        await bot.send_video(chat_id=msg.chat_id, video=file_id, caption=clean, reply_markup=reply_markup, parse_mode=parse_mode)
                    else:
                        await bot.send_photo(chat_id=msg.chat_id, photo=file_id, caption=clean, reply_markup=reply_markup, parse_mode=parse_mode)
                elif is_media:
                    await query.get_bot().send_message(chat_id=msg.chat_id, text=clean, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception:
                pass
        else:
            pass

WELCOME_TEXT = (
    f'<tg-emoji emoji-id="6071312005224993914">💎</tg-emoji> <b>Product Store : all key purchase &amp; instantly delivery</b>\n'
    f'<tg-emoji emoji-id="6071074330324768982">👤</tg-emoji> <b>My Profile : check your account information</b>\n'
    f'<tg-emoji emoji-id="6071132024620455409">💰</tg-emoji> <b>Add Balance : deposit balance &amp; secure service</b>\n'
    f'<tg-emoji emoji-id="6070878939377571385">📜</tg-emoji> <b>Order History : check all key purchase history</b>\n'
    f'<tg-emoji emoji-id="6071126054615913700">💳</tg-emoji> <b>Deposit History : check all your deposits</b>\n'
    f'<tg-emoji emoji-id="6073116574389113063">📘</tg-emoji> <b>Tutorial : view tutorial and work this bot</b>\n'
    f'<tg-emoji emoji-id="6071312005224993914">🆘</tg-emoji> <b>Support : bot problem fixed for support admin</b>\n'
    f'<tg-emoji emoji-id="6071074330324768982">⬇️</tg-emoji> <b>Download Hack : download latest apk for safety.</b>'
)

async def send_welcome(bot, chat_id, is_admin):
    keyboard = get_main_menu_keyboard(is_admin=is_admin)
    media_type, file_id = db.get_welcome_media()
    dynamic_welcome = get_text_safe('welcome', WELCOME_TEXT)
    
    try:
        if media_type == "video":
            await bot.send_video(chat_id=chat_id, video=file_id, caption=dynamic_welcome, reply_markup=keyboard, parse_mode="HTML")
        elif media_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=file_id, caption=dynamic_welcome, reply_markup=keyboard, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=chat_id, text=dynamic_welcome, reply_markup=keyboard, parse_mode="HTML")
    except telegram.error.BadRequest as e:
        if "parse entities" in str(e).lower():
            logger.warning("Caught HTML parsing error in welcome text. Resetting to default.")
            # Automatically delete the corrupted text from DB
            db.set_text('welcome', WELCOME_TEXT)
            # Fallback to the safe hardcoded text
            fallback_text = WELCOME_TEXT
            
            error_notice = "⚠️ <b>Admin Notice:</b> Your custom welcome text was corrupted and caused an error! It has been automatically reset to default.\n\n"
            final_text = error_notice + fallback_text if is_admin else fallback_text
            
            if media_type == "video":
                await bot.send_video(chat_id=chat_id, video=file_id, caption=final_text, reply_markup=keyboard, parse_mode="HTML")
            elif media_type == "photo":
                await bot.send_photo(chat_id=chat_id, photo=file_id, caption=final_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=chat_id, text=final_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    reaction_enabled = db.get_setting("welcome_reaction_enabled")
    if reaction_enabled is None:
        reaction_enabled = "1"
    if reaction_enabled == "1":
        reaction_str = db.get_setting("welcome_reaction")
        # Removed fallback to allow no reaction when cleared
        if reaction_str and hasattr(update.message, 'set_reaction'):
            try:
                if reaction_str.isdigit():
                    await update.message.set_reaction([ReactionTypeCustomEmoji(reaction_str)], is_big=True)
                else:
                    await update.message.set_reaction([ReactionTypeEmoji(reaction_str)], is_big=True)
                await asyncio.sleep(1.0) # Delay so user sees the reaction animation before the menu pushes it up
            except Exception as e:
                logger.error(f"Reaction error: {e}")

    if db.get_setting("maintenance_mode") == "1" and user_id != str(ADMIN_ID):
        msg = get_text_safe("maintenance_msg", "🛠 <b>Bot is currently under maintenance. Please try again later.</b>")
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    is_new_user = db.get_user(user_id) is None
    db.init_user(user_id, user.username or "User")

    if context.args:
        payload = context.args[0].strip()
        referrer_id = payload.replace("ref_", "").strip()
        logger.info(f"Referral attempt: user={user_id} is_new={is_new_user} payload='{payload}' referrer={referrer_id}")

        if not is_new_user:
            logger.info(f"Referral skipped: {user_id} already existed in DB before this /start (not a new user).")
        elif not referrer_id.isdigit():
            logger.info(f"Referral skipped: payload '{payload}' is not a valid numeric id.")
        else:
            linked = db.set_referrer(user_id, referrer_id)
            if linked:
                logger.info(f"Referral linked: {user_id} -> referred by {referrer_id}")
                try:
                    join_msg = (
                        f"🎉 <b>Naya Referral!</b>\n\n"
                        f"Aapke link se ek naya user join hua hai. "
                        f"Jab wo deposit karega, aapko {REFERRAL_COMMISSION_PERCENT}% bonus milega!"
                    )
                    await context.bot.send_message(chat_id=int(referrer_id), text=join_msg, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Could not notify referrer {referrer_id}: {e}")
            else:
                logger.info(f"Referral NOT linked: referrer {referrer_id} not found in DB, or {user_id} already had a referrer.")
    
    if update.message:
        is_admin = str(user.id) == str(ADMIN_ID)
        await send_welcome(context.bot, update.message.chat_id, is_admin)

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id != str(ADMIN_ID):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    text = update.message.text.replace("/addproduct", "", 1).strip()
    if not text:
        await update.message.reply_text(
            "❌ Usage:\n"
            "/addproduct CATEGORY | NAME | PRODUCT_ID | PLAN | PRICE | ANDROID_ID\n\n"
            "Categories:\n"
            "🤖 ANDROID NON ROOT\n"
            "👑 ANDROID ROOT\n"
            "💻 PC\n"
            "🍎 IOS\n\n"
            "Example:\n"
            "/addproduct ANDROID NON ROOT | BALA MOD PRO | 133 | 1 Day | 150 | 0b9b969bc2e7997b"
        )
        return

    try:
        p = parse_product_line(text)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    try:
        db.add_product(p["category"], p["name"], p["product_id"], p["plan"], p["price"], p["android_id"])
        await update.message.reply_text(
            f"✅ Product Added!\n"
            f"📦 {p['name']}\n"
            f"⏳ {p['plan']}\n"
            f"💰 ₹{p['price']:.2f}\n"
            f"🆔 ID: {p['product_id']}\n"
            f"📂 Category: {p['category']}"
        )
    except Exception as e:
        logger.error(f"add_product DB error: {e}")
        await update.message.reply_text(f"❌ Product save nahi ho paya: {e}")

async def check_payment_later(context: ContextTypes.DEFAULT_TYPE, chat_id, message_id, order_id, delay=15):
    await asyncio.sleep(delay)
    order = db.get_order(order_id)
    if not order:
        return
    if order[3] == "completed":
        return

    msg = f"""
❌ <b>PAYMENT NOT FOUND</b>
━━━━━━━━━━━━━━━━━━
🆔 <b>Order:</b> <code>{order_id}</code>
💰 <b>Amount:</b> ₹{order[2]:.2f}
━━━━━━━━━━━━━━━━━━
Hume abhi tak aapka payment nahi mila.
Agar aapne payment kar diya hai, thodi der baad "Check Again" try karein.
Agar payment nahi kiya, to "Cancel" dabayein aur naya QR banayein.
"""
    keyboard = [
        [CB("Check Again", style="primary", icon=get_button_emoji("refresh"), callback_data=f"verify_{order_id}")],
        [CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="menu_add_balance")]
    ]
    try:
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"check_payment_later edit failed: {e}")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Auto-clear any dangling input states when navigating via buttons
    for key in list(context.user_data.keys()):
        if key.startswith("awaiting_"):
            context.user_data[key] = False

    if db.get_setting("maintenance_mode") == "1" and str(update.effective_user.id) != str(ADMIN_ID) and not query.data.startswith("admin_"):
        msg = get_text_safe("maintenance_msg", "🛠 <b>Bot is currently under maintenance. Please try again later.</b>")
        try:
            await query.answer("Bot is under maintenance!", show_alert=True)
            await safe_edit(query, text=msg, parse_mode="HTML")
        except:
            pass
        return

    try:
        await _handle_callbacks_inner(update, context)
    except Exception as e:
        logger.error(f"handle_callbacks error on data='{query.data}': {e}", exc_info=True)
        alert_shown = False
        try:
            await query.answer(f"❌ Error: {str(e)[:180]}", show_alert=True)
            alert_shown = True
        except Exception:
            pass
        if not alert_shown:
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"❌ <b>Error:</b> <code>{str(e)[:300]}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        if str(update.effective_user.id) == str(ADMIN_ID):
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ <b>Bot Error</b>\n\n🔘 Button: <code>{query.data}</code>\n❌ Error: <code>{str(e)[:500]}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

async def _handle_callbacks_inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = str(update.effective_user.id)
    
    try:
        if not data.startswith("kp_confirm"):
            await query.answer()
    except Exception:
        pass
    db.init_user(user_id, update.effective_user.username or "User")
    
    if "kp_amt" not in context.user_data:
        context.user_data["kp_amt"] = ""

    if data == "back_to_menu":
        context.user_data["kp_amt"] = ""
        is_admin = user_id == str(ADMIN_ID)
        try:
            await query.message.delete()
        except Exception:
            pass
        await send_welcome(context.bot, query.message.chat_id, is_admin)

    elif data == "menu_shop":
        products = db.get_products()
        default_shop = f"<b>📊 HACK STORE — SHOP 💭</b>\n\n<tg-emoji emoji-id=\"6070873970100409600\">⭐</tg-emoji> <b>Choose your device category:</b>"
        text = get_text_safe("shop", default_shop)
        keyboard = []
        
        hidden_cats = db.get_setting("hidden_devices")
        hidden_list = hidden_cats.split(",") if hidden_cats else []

        for cat in products.keys():
            if cat in hidden_list: continue
            cb = encode_cb("cat", cat)
            keyboard.append([CB(f"{cat}", style="primary", icon=get_category_emoji(cat), callback_data=cb)])
        
        keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="back_to_menu")])
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="shop", parse_mode="HTML")

    elif data.startswith("cat" + SEP):
        parts = decode_cb(data)
        category = parts[1]
        products = db.get_products()
        default_text = f"<b>📂 Category: {category}</b>\n\nSelect a product to purchase:"
        text = get_text_safe(f"cat_{category}", default_text)
        keyboard = []
        for prod_name in products.get(category, {}).keys():
            cb = encode_cb("prod", category, prod_name)
            emoji = get_button_emoji(f"prod_{prod_name}")
            if not emoji: emoji = get_button_emoji("star")
            keyboard.append([CB(f"{prod_name}", style="primary", icon=emoji, callback_data=cb)])
        keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="menu_shop")])
        await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("prod" + SEP):
        parts = decode_cb(data)
        category = parts[1]
        prod_name = parts[2]
        products = db.get_products()
        plans = products[category][prod_name]["plans"]
        plan_ids = products[category][prod_name]["plan_ids"]
        is_reseller = db.is_reseller(user_id)

        text = f"<b>💎 Product: {prod_name}</b>\n\nChoose expiration pack period below:"
        if is_reseller:
            text += f"\n👑 <b>Reseller Price ({RESELLER_DISCOUNT_PERCENT}% OFF)</b>"
        keyboard = []
        for plan_name, price in plans.items():
            final_price = get_price_for_user(price, user_id)
            if is_reseller:
                label = f"{plan_name} - ₹{final_price:.0f} (was ₹{price:.0f})"
            else:
                label = f"{plan_name} - ₹{price:.0f}"
            cb = encode_cb("buy", plan_ids[plan_name])
            keyboard.append([CB(label, style="primary", icon=get_button_emoji("plan"), callback_data=cb)])
        keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=encode_cb("cat", category))])
        await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("buy" + SEP):
        parts = decode_cb(data)
        plan_row_id = parts[1]

        plan_info = db.get_plan_by_id(plan_row_id)
        if not plan_info:
            await query.answer("❌ Ye product/plan ab available nahi hai.", show_alert=True)
            return

        category = plan_info["category"]
        prod_name = plan_info["name"]
        plan_name = plan_info["plan"]
        product_id = plan_info["product_id"]
        base_price = plan_info["price"]
        price = get_price_for_user(base_price, user_id)
        android_id = plan_info["android_id"]
        
        balance = db.get_balance(user_id)
        
        if balance < price:
            await query.answer(f"❌ Insufficient Balance! Need ₹{price}, You have ₹{balance}", show_alert=True)
            text = f"""
<tg-emoji emoji-id="6010080962883361959">⭐</tg-emoji> <b>INSUFFICIENT BALANCE!</b>

💸 Required: <b>₹{price}</b>
<tg-emoji emoji-id="6010080962883361959">⭐</tg-emoji> Your Balance: <b>₹{balance}</b>

Please add balance first.
"""
            keyboard = [
                [CB("Add Balance", style="success", icon=get_button_emoji("add_balance"), callback_data="menu_add_balance")],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=encode_cb("prod", category, prod_name))]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            return
        
        # ========== BALA MOD CHECK - Android ID Required ==========
        is_bala_mod = any(bala in prod_name for bala in BALA_MOD_PRODUCTS)
        
        if is_bala_mod:
            # Ask user for Android ID
            product_data = {
                "name": prod_name,
                "plan": plan_name,
                "product_id": product_id,
                "price": price,
                "category": category
            }
            await ask_android_id(update, context, product_data)
            return
        # ==========================================================
        
        # Regular product - use default android_id
        if db.deduct_balance(user_id, price):
            await query.answer("⏳ Processing your order...")
            
            license_key = fetch_license_key(product_id, plan_name, android_id)
            
            if "Error:" in str(license_key):
                db.update_balance(user_id, price)
                admin_user = db.db.users.find_one({"user_id": str(ADMIN_ID)})
                admin_username = f"@{admin_user['username']}" if admin_user and admin_user.get("username") else "the Owner"
                
                await query.answer(f"❌ Purchase Failed: Server problem", show_alert=True)
                text = f"❌ <b>PURCHASE FAILED!</b>\n\nServer problem, contact owner {admin_username}\n\n💰 Your balance has been refunded."
                keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=encode_cb("prod", category, prod_name))]]
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                return
            
            db.add_history(user_id, prod_name, plan_name, price, license_key)
            
            text = f"""
<tg-emoji emoji-id="6073308817125282940">⭐</tg-emoji> <b>PURCHASE SUCCESSFUL!</b>

📦 <b>Product:</b> {prod_name}
⏳ <b>Validity:</b> {plan_name}
💰 <b>Price:</b> ₹{price}

<tg-emoji emoji-id="6071312005224993914">⭐</tg-emoji> <b>YOUR LICENSE KEY:</b>
<code>{license_key}</code>

✅ Key saved to history!
"""
            keyboard = [[CB("Main Menu", style="primary", icon=get_button_emoji("shop"), callback_data="back_to_menu")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

            product_doc = db.db.products.find_one({"product_id": product_id})
            if product_doc:
                voice_id = product_doc.get("voice_file_id")
                link = product_doc.get("product_link")
                if voice_id:
                    try: await context.bot.send_voice(chat_id=query.message.chat_id, voice=voice_id)
                    except Exception: pass
                if link:
                    try: await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 <b>Product Link:</b>\n{link}", parse_mode="HTML")
                    except Exception: pass

        else:
            await query.answer("❌ Insufficient balance!", show_alert=True)

    elif data == "cancel_purchase":
        context.user_data["awaiting_android_id"] = False
        context.user_data["pending_product"] = None
        await safe_edit(query, "❌ Purchase cancelled.")
        # Go back to shop
        products = db.get_products()
        text = f"<b>📊 HACK STORE — SHOP 💭</b>\n\n<tg-emoji emoji-id=\"6070873970100409600\">⭐</tg-emoji> <b>Choose your device category:</b>"
        keyboard = []
        for cat in products.keys():
            cb = encode_cb("cat", cat)
            keyboard.append([CB(f"{cat}", style="primary", icon=get_category_emoji(cat), callback_data=cb)])
        keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="back_to_menu")])
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "menu_profile":
        user_data = db.get_user(user_id)
        balance = db.get_balance(user_id)
        reseller_line = f"\n👑 <b>Status:</b> Reseller ({RESELLER_DISCOUNT_PERCENT}% OFF)" if db.is_reseller(user_id) else ""
        default_prof = "<tg-emoji emoji-id=\"6071074330324768982\">⭐</tg-emoji> <b>MY ACCOUNT PROFILE</b>"
        db_text = get_text_safe("profile", default_prof)
        text = f"""{db_text}

👤 <b>Username:</b> @{user_data[1] if user_data else 'User'}
🆔 <b>User ID:</b> <code>{user_id}</code>
<tg-emoji emoji-id="6010080962883361959">⭐</tg-emoji> <b>Wallet Balance:</b> <b>₹{balance}</b>{reseller_line}
"""
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="profile", parse_mode="HTML")

    elif data == "transfer_balance_start":
        context.user_data["awaiting_transfer_userid"] = True
        context.user_data["awaiting_transfer_amount"] = False
        text = get_text_safe("transfer_caption", "💸 <b>USER TO USER BALANCE TRANSFER</b>\n\nPlease enter the <b>User ID or @Username</b> of the person you want to send money to:\n(Type /cancel to abort)")
        keyboard = [[CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="back_to_menu")]]
        await safe_edit(query, text, InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "menu_history":
        import html
        # Premium Emoji IDs
        ORDER_EMOJI = "6070878939377571385"          # 📜 — Header
        PRODUCT_EMOJI = "6176966310920983412"        # 🛒 — Product ke aage
        KEY_EMOJI = "5465443379917629504"            # 💎 — Key ke aage (NEW)
        
        history = db.get_history(user_id, 10)
        
        if not history:
            text = f"""<blockquote>
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="{ORDER_EMOJI}">📜</tg-emoji> <b>ORDER HISTORY</b>
━━━━━━━━━━━━━━━━━━━━

❌ No orders yet.

━━━━━━━━━━━━━━━━━━━━
</blockquote>"""
        else:
            lines = [
                "<blockquote>",
                "━━━━━━━━━━━━━━━━━━━━",
                f'<tg-emoji emoji-id="{ORDER_EMOJI}">📜</tg-emoji> <b>ORDER HISTORY</b>',
                "━━━━━━━━━━━━━━━━━━━━",
                ""
            ]
            
            for item in history:
                safe_prod = html.escape(str(item[2]))
                safe_plan = html.escape(str(item[3]))
                price = item[4]
                safe_key = html.escape(str(item[5]))
                safe_android = html.escape(str(item[6])) if len(item) > 6 and item[6] else ""
                
                lines.append(f'<tg-emoji emoji-id="{PRODUCT_EMOJI}">🛒</tg-emoji> {safe_prod} ({safe_plan}) — ₹{price}')
                lines.append(f'<tg-emoji emoji-id="{KEY_EMOJI}">💎</tg-emoji> <code>{safe_key}</code>')
                if safe_android:
                    lines.append(f'📱 Android ID: <code>{safe_android}</code>')
                lines.append("")
            
            lines.append("━━━━━━━━━━━━━━━━━━━━")
            lines.append("</blockquote>")
            
            text = "\n".join(lines)
            
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="history", parse_mode="HTML")

    elif data == "menu_deposit_history":
        # Premium Emoji IDs
        HEADER_EMOJI = "6091170843080007327"   # 💰
        SEP_EMOJI = "6307665627481903641"      # ➖
        TOTAL_EMOJI = "6244678063775289843"    # ⚡
        AMOUNT_EMOJI = "6237742262822901946"   # ⚡
        ID_EMOJI = "5888781182249738113"       # 🆔
        DATE_EMOJI = "5274055917766202507"     # 📅
        UTR_EMOJI = "5310228579009699834"      # 🔑
        USER_EMOJI = "4967667085606912536"     # 👤

        raw_history = db.get_deposit_history(user_id, 10)
        history = [row for row in raw_history if (row[4] if len(row)>4 and row[4] else "completed") == "completed"]
        
        if not history:
            text = f"""<blockquote>
<tg-emoji emoji-id="{HEADER_EMOJI}">💰</tg-emoji> <b>DEPOSIT HISTORY</b>
❌ No successful deposits yet
</blockquote>"""
        else:
            total_deposits = sum(row[1] for row in history)
            
            lines = [
                "<blockquote>",
                f'<tg-emoji emoji-id="{HEADER_EMOJI}">💰</tg-emoji> <b>DEPOSIT HISTORY</b>',
                f'<tg-emoji emoji-id="{SEP_EMOJI}">➖</tg-emoji>' * 12,
                f'<tg-emoji emoji-id="{TOTAL_EMOJI}">⚡</tg-emoji> <b>Total:</b> ₹{total_deposits:.2f}',
                ""
            ]
            
            for row in history:
                order_id = row[0]
                amount = row[1]
                utr = row[2] if row[2] else "N/A"
                sender = row[3] if row[3] else "N/A"
                timestamp = row[5] if len(row) > 5 and row[5] else ""
                date_str = timestamp[:16] if timestamp else "N/A"
                
                lines.append(f'<tg-emoji emoji-id="{AMOUNT_EMOJI}">⚡</tg-emoji> ₹{amount:.2f}')
                lines.append(f'   <tg-emoji emoji-id="{ID_EMOJI}">🆔</tg-emoji> {order_id}')
                lines.append(f'   <tg-emoji emoji-id="{DATE_EMOJI}">📅</tg-emoji> {date_str}')
                lines.append(f'   <tg-emoji emoji-id="{UTR_EMOJI}">🔑</tg-emoji> {utr}')
                lines.append(f'   <tg-emoji emoji-id="{USER_EMOJI}">👤</tg-emoji> {sender}')
                lines.append("")
            
            lines.append(f'<tg-emoji emoji-id="{SEP_EMOJI}">➖</tg-emoji>' * 20)
            lines.append("</blockquote>")
            
            text = "\n".join(lines)
        
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="deposit_history", parse_mode="HTML")

    elif data == "menu_tutorial":
        text = get_text_safe("tutorial", "📚 <b>Tutorial</b>\\n\\nHow to use the bot.")
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="tutorial", parse_mode="HTML")

    elif data == "menu_support":
        text = get_text_safe("support", "💬 <b>Support</b>\\n\\nContact admin for help.")
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="support", parse_mode="HTML")

    elif data == "menu_download":
        text = get_text_safe("download", "📥 <b>Download</b>\\n\\nDownload links coming soon.")
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="download", parse_mode="HTML")

    elif data == "menu_referral":
        # Premium Emoji IDs — Aapki di hui
        STAR_EMOJI = "6242413641052722528"      # ⭐
        MONEY_EMOJI = "6276133811545706331"     # 💸
        LINK_EMOJI = "6100657257605763582"      # 🔗
        USER_EMOJI = "4967667085606912536"      # 👥
        COIN_EMOJI = "6235445786759402354"      # 💰
        MEGAPHONE_EMOJI = "5328175963144466763" # 📢
        
        # Database se real data lo
        total_refs = db.db.users.count_documents({"referred_by": user_id})
        
        pipeline = [
            {"$match": {"referrer_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$bonus_amount"}}}
        ]
        result = list(db.db.referral_earnings.aggregate(pipeline))
        total_earnings = result[0]["total"] if result else 0.0
        
        bot_username = context.bot.username or "TrustedpanelsellerWala_bot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        text = f"""<blockquote>
╭━━━━〔 <tg-emoji emoji-id="{STAR_EMOJI}">⭐</tg-emoji> REFERRAL PROGRAM 〕━━━━╮
                                   
<tg-emoji emoji-id="{MONEY_EMOJI}">💸</tg-emoji> Apne friends ko refer karo aur
   unke har recharge par earning karo!
                                   
<tg-emoji emoji-id="{LINK_EMOJI}">🔗</tg-emoji> <b>Your Referral Link:</b>
<code>{referral_link}</code>
                                   
<tg-emoji emoji-id="{USER_EMOJI}">👥</tg-emoji> <b>Total Referrals:</b> {total_refs}
<tg-emoji emoji-id="{COIN_EMOJI}">💰</tg-emoji> <b>Total Earnings:</b> ₹{total_earnings:.2f}
                                   
<tg-emoji emoji-id="{MEGAPHONE_EMOJI}">📢</tg-emoji> Link share karo • Refer karo • Earn karo!
                                   
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯
</blockquote>"""
        
        keyboard = [[CB("Back to Menu", style="primary", icon=get_button_emoji("back"), callback_data="back_to_menu")]]
        
        await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="referral", parse_mode="HTML")

    elif data == "menu_add_balance":
        COIN_EMOJI = "6089118454302909415"      # 🪙
        MONEY_EMOJI = "6334784630809435068"     # 💰
        BOLT_EMOJI = "6276133811545706331"      # ⚡
        ARROW_EMOJI = "6091231303334633875"     # ➡️
        CASH_EMOJI = "6332078964621712044"      # 💵
        
        context.user_data["kp_amt"] = ""
        
        text = f"""<blockquote>
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="{COIN_EMOJI}">🪙</tg-emoji> <b>ADD FUNDS TO WALLET</b>
━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="{MONEY_EMOJI}">💰</tg-emoji> Choose a quick amount to add
   or type/use a custom one below.

<tg-emoji emoji-id="{BOLT_EMOJI}">⚡</tg-emoji> Predefined amounts are faster to process!

━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="{ARROW_EMOJI}">➡️</tg-emoji> <b>Amount:</b> ₹0 <tg-emoji emoji-id="{CASH_EMOJI}">💵</tg-emoji>
</blockquote>"""
        
        if query.message.photo or query.message.video:
            await query.message.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=get_numeric_keypad(), parse_mode="HTML")
        else:
            await safe_edit(query, text=text, reply_markup=get_numeric_keypad(), parse_mode="HTML")

    elif data.startswith("kp_"):
        action = data.split("kp_")[1]
        current = context.user_data["kp_amt"]

        if action.isdigit():
            if current == "0": current = ""
            current += action
        elif action == "clear":
            current = ""
        elif action == "confirm":
            if not current or not current.isdigit() or int(current) <= 0:
                await query.answer("❌ Please enter a valid amount!", show_alert=True)
                return
            
            original_amount = int(current)
            if original_amount < MIN_AMOUNT:
                await query.answer(f"❌ Minimum amount is ₹{MIN_AMOUNT}", show_alert=True)
                return
            
            EMOJI_ID = "6129812419028982717"
            text = f"""<blockquote>
━━━━━━━━━━━━━━━━━━━━
<b>PAYMENT OPTIONS</b>
━━━━━━━━━━━━━━━━━━━━

PhonePe / GooglePay Payment Available

अगर किसी एक Payment Option से Payment Failed हो,
तो दूसरा Option Select करके Payment करें.

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="{EMOJI_ID}">💳</tg-emoji>
━━━━━━━━━━━━━━━━━━━━
</blockquote>"""
            keyboard = [
                [
                    CB("GooglePay", style="primary", icon=get_button_emoji("googlepay"), callback_data=f"gateway_2_{original_amount}"),
                    CB("PhonePe", style="primary", icon=get_button_emoji("phonepe"), callback_data=f"gateway_1_{original_amount}")
                ],
                [CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="menu_add_balance")]
            ]
            
            await send_screen(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), screen_key="payment", parse_mode="HTML")
            return


        context.user_data["kp_amt"] = current
        display_amt = current if current else "0"
        COIN_EMOJI = "6089118454302909415"      # 🪙
        MONEY_EMOJI = "6334784630809435068"     # 💰
        BOLT_EMOJI = "6276133811545706331"      # ⚡
        ARROW_EMOJI = "6091231303334633875"     # ➡️
        CASH_EMOJI = "6332078964621712044"      # 💵
        
        text = f"""<blockquote>
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="{COIN_EMOJI}">🪙</tg-emoji> <b>ADD FUNDS TO WALLET</b>
━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="{MONEY_EMOJI}">💰</tg-emoji> Choose a quick amount to add
   or type/use a custom one below.

<tg-emoji emoji-id="{BOLT_EMOJI}">⚡</tg-emoji> Predefined amounts are faster to process!

━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="{ARROW_EMOJI}">➡️</tg-emoji> <b>Amount:</b> ₹{display_amt} <tg-emoji emoji-id="{CASH_EMOJI}">💵</tg-emoji>
</blockquote>"""
        try:
            await safe_edit(query, text=text, reply_markup=get_numeric_keypad(), parse_mode="HTML")
        except:
            pass
    elif data.startswith("gateway_"):
        parts = data.split("_")
        gateway = parts[1]
        original_amount = int(parts[2])
        
        order_prefix = "ADD1_" if gateway == "1" else "ADD2_"
        order_id = f"{order_prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
        customer_name = query.from_user.full_name or f"User{user_id}"

        logger.info(f"👤 User {user_id} ({customer_name}) requested ₹{original_amount} top-up → order {order_id}")
        await query.answer("⏳ Creating your payment link...")
        payment_url, upi_url, err = await asyncio.to_thread(create_karanpay_order, original_amount, order_id, customer_name)
        if not payment_url:
            logger.error(f"❌ KaranPay order creation failed for user {user_id}: {err}")
            await query.answer(
                "❌ Payment order create nahi ho paaya. Error: " + str(err),
                show_alert=True
            )
            return

        expiry_time = (datetime.now() + timedelta(minutes=5)).strftime("%d-%m-%Y %H:%M:%S")

        db.create_order(order_id, user_id, original_amount)

        text_msg = f"""
<tg-emoji emoji-id="6215156189454409086">💰</tg-emoji> <b>Amount: ₹{original_amount:.2f}</b>
<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji> <b>Order ID: <code>{order_id}</code></b>
⏰ <b>Expires: {expiry_time}</b>

📊 <b>Scan the QR or tap "Pay Now" to open the secure payment page.</b>

⚠️ <b>Important:</b> Pay exact amount <b>₹{original_amount:.2f}</b>
"""
        keyboard = [
            [CB("Verify Payment", style="success", icon=get_button_emoji("confirm"), callback_data=f"verify_{order_id}")],
            [CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="menu_add_balance")]
        ]

        try:
            qr_img = generate_qr_image(upi_url)
        except Exception as e:
            logger.error(f"QR image generation failed: {e}")
            qr_img = None

        try:
            if qr_img:
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=qr_img, caption=text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text=text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send payment message: {e}")
            await query.answer("❌ Message bhej nahi paya, dobara try karo.", show_alert=True)
            return

        try:
            await query.message.delete()
        except Exception:
            pass
        return

    elif data.startswith("verify_"):
        order_id = data.split("verify_")[1]
        order = db.get_order(order_id)
    
        if not order:
            await query.answer("❌ Order not found!", show_alert=True)
            return
    
        if order[3] == "completed":
            await query.answer("✅ Already verified!", show_alert=True)
            msg = f'<tg-emoji emoji-id="6235234890980269200">✅</tg-emoji> <b>Already Verified!</b>\\n₹{order[2]} added to your wallet.'
            try:
                await query.message.edit_caption(caption=msg, parse_mode="HTML")
            except:
                try:
                    await query.message.edit_text(text=msg, parse_mode="HTML")
                except:
                    pass
            return

        await query.answer("⏳ Checking payment...")

        result = await asyncio.to_thread(check_karanpay_status, order_id)
        if result:
            user_id_o, amount_o = order[1], order[2]
            utr = result.get("utr", "N/A")
            paid_amount = result.get("amount", amount_o)
            sender = result.get("customer_name", "Unknown")
            if db.complete_order_atomic(order_id, utr, sender):
                db.update_balance(user_id_o, paid_amount)
                db.add_deposit_history(user_id_o, order_id, paid_amount, utr, sender)
                notify_admin_deposit(user_id_o, order_id, paid_amount, utr, sender)
            msg = (f'<tg-emoji emoji-id="6235234890980269200">✅</tg-emoji> <b>Payment Verified!</b>\\n'
                   f'₹{paid_amount} added to your wallet.\\n'
                   f'<tg-emoji emoji-id="6034969813032374911">🧾</tg-emoji> UTR: <code>{utr}</code>')
            try:
                await query.message.edit_caption(caption=msg, parse_mode="HTML")
            except:
                try:
                    await query.message.edit_text(text=msg, parse_mode="HTML")
                except:
                    pass
            return

        msg = f"""
<tg-emoji emoji-id="6070873970100409600">⭐</tg-emoji> <b>PAYMENT VERIFICATION</b>
━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji> <b>Order:</b> <code>{order_id}</code>
<tg-emoji emoji-id="6215156189454409086">💰</tg-emoji> <b>Amount:</b> ₹{order[2]:.2f}
━━━━━━━━━━━━━━━━━━
📱 Please wait 10-15 seconds...
Payment will be auto-detected!
"""
        try:
            await query.message.edit_caption(caption=msg, parse_mode="HTML")
        except:
            try:
                await query.message.edit_text(text=msg, parse_mode="HTML")
            except:
                pass
        asyncio.create_task(
            check_payment_later(context, query.message.chat_id, query.message.message_id, order_id)
        )



    elif data.startswith("admin_"):
        if str(user_id) != str(ADMIN_ID):
            await query.answer("❌ You are not authorized!", show_alert=True)
            return

        if data == "admin_panel":
            text = "🛠 <b>ADMIN PANEL</b>\n\nChoose an action below:"
            await safe_edit(query, text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")

        elif data == "admin_export_users":
            if str(user_id) != str(ADMIN_ID):
                return
            all_users = list(db.db.users.find({}, {"_id": 0})) 
            if not all_users:
                await query.message.reply_text("❌ No users found.")
                return
            json_data = json.dumps(all_users, indent=4)
            file_io = io.BytesIO(json_data.encode("utf-8"))
            file_io.name = "export_users.json"
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_io,
                caption="✅ <b>Exported user data.</b>\n\n⚠️ <b>Clear ALL users?</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [CB("Yes, Clear Database", style="danger", icon=get_button_emoji("clear"), callback_data="admin_clear_users_confirm")],
                    [CB("Cancel", style="primary", icon=get_button_emoji("cancel"), callback_data="admin_panel")]
                ])
            )
            return
        
        elif data == "admin_clear_users_confirm":
            if str(user_id) != str(ADMIN_ID):
                return
            deleted = db.db.users.delete_many({}).deleted_count
            await query.message.reply_text(f"✅ <b>Deleted {deleted} users.</b>", parse_mode="HTML")
            await send_screen(query, "Database cleared.", get_admin_panel_keyboard(), "admin_panel")
            return

        elif data == "admin_colors":
            buttons = [
                "Product Store", "My Profile", "Add Balance", "Order History", 
                "Deposit History", "Tutorial", "Support", "Download Hack", 
                "Referral", "Verify Payment", "Check Again", "Back to Menu", 
                "Back", "Main Menu", "Cancel", "❌ Cancel", "BACK", "Confirm", "Clear", "Transfer Balance"
            ]
            rows = []
            for i in range(0, len(buttons), 2):
                row = []
                for btn in buttons[i:i+2]:
                    c_style = db.get_setting(f"color_{btn}") or "primary"
                    row.append(CB(f"{btn} ({c_style})", style=c_style, callback_data=f"admin_color_{btn}"))
                rows.append(row)
            rows.append([CB("Clear Colors", style="danger", icon=get_button_emoji("clear"), callback_data="admin_clear_colors")])
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "🎨 <b>Select a button to change its color:</b>\n(Clicking it cycles through colors)", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data == "admin_clear_colors":
            buttons = [
                "Product Store", "My Profile", "Add Balance", "Order History", 
                "Deposit History", "Tutorial", "Support", "Download Hack", 
                "Referral", "Verify Payment", "Check Again", "Back to Menu", 
                "Back", "Main Menu", "Cancel", "❌ Cancel", "BACK", "Confirm", "Clear", "Transfer Balance"
            ]
            for btn in buttons:
                db.delete_setting(f"color_{btn}")
            await query.answer("✅ Colors reset!", show_alert=True)
            # Re-render
            rows = []
            for i in range(0, len(buttons), 2):
                row = []
                for btn in buttons[i:i+2]:
                    c_style = db.get_setting(f"color_{btn}") or "primary"
                    row.append(CB(f"{btn} ({c_style})", style=c_style, callback_data=f"admin_color_{btn}"))
                rows.append(row)
            rows.append([CB("Clear Colors", style="danger", icon=get_button_emoji("clear"), callback_data="admin_clear_colors")])
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "🎨 <b>Select a button to change its color:</b>\n(Clicking it cycles through colors)", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data.startswith("admin_color_"):
            btn_name = data.split("admin_color_")[1]
            styles = ["primary", "success", "danger"]
            current_style = db.get_setting(f"color_{btn_name}") or "primary"
            if current_style in styles:
                next_index = (styles.index(current_style) + 1) % len(styles)
            else:
                next_index = 0
            new_style = styles[next_index]
            db.set_setting(f"color_{btn_name}", new_style)
            
            # Re-render
            buttons = [
                "Product Store", "My Profile", "Add Balance", "Order History", 
                "Deposit History", "Tutorial", "Support", "Download Hack", 
                "Referral", "Verify Payment", "Check Again", "Back to Menu", 
                "Back", "Main Menu", "Cancel", "❌ Cancel", "BACK", "Confirm", "Clear"
            ]
            rows = []
            for i in range(0, len(buttons), 2):
                row = []
                for btn in buttons[i:i+2]:
                    c_style = db.get_setting(f"color_{btn}") or "primary"
                    row.append(CB(f"{btn} ({c_style})", style=c_style, callback_data=f"admin_color_{btn}"))
                rows.append(row)
            rows.append([CB("Clear Colors", style="danger", icon=get_button_emoji("clear"), callback_data="admin_clear_colors")])
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "🎨 <b>Select a button to change its color:</b>\n(Clicking it cycles through colors)", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data == "admin_devices":
            products = db.get_products()
            categories = list(products.keys())
            hidden_cats = db.get_setting("hidden_devices")
            hidden_list = hidden_cats.split(",") if hidden_cats else []
            
            rows = []
            for cat in categories:
                status = "🔴 Hidden" if cat in hidden_list else "🟢 Visible"
                cb = encode_cb("admin_toggledv", cat)
                rows.append([CB(f"{cat} - {status}", style="danger", icon=get_button_emoji("star"), callback_data=cb)])
            
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "📱 <b>Manage Devices Visibility</b>\nClick on a device category to toggle its visibility in the Product Store:", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data.startswith("admin_toggledv" + SEP):
            cat = decode_cb(data)[1]
            hidden_cats = db.get_setting("hidden_devices")
            hidden_list = hidden_cats.split(",") if hidden_cats else []
            
            if cat in hidden_list:
                hidden_list.remove(cat)
            else:
                hidden_list.append(cat)
                
            db.set_setting("hidden_devices", ",".join(hidden_list))
            
            # Re-render
            products = db.get_products()
            categories = list(products.keys())
            rows = []
            for c in categories:
                status = "🔴 Hidden" if c in hidden_list else "🟢 Visible"
                cb = encode_cb("admin_toggledv", c)
                rows.append([CB(f"{c} - {status}", style="danger", icon=get_button_emoji("star"), callback_data=cb)])
            
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "📱 <b>Manage Devices Visibility</b>\nClick on a device category to toggle its visibility in the Product Store:", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data == "admin_texts":
            context.user_data["awaiting_text_key"] = None
            rows = []
            for k, v in EDITABLE_TEXTS.items():
                rows.append([CB(f"Edit {v} Text", style="primary", icon=get_button_emoji("tutorial"), callback_data=f"admin_edittext_{k}")])
            for cat in db.get_products().keys():
                rows.append([CB(f"Edit Category: {cat}", style="primary", icon=get_button_emoji("tutorial"), callback_data=f"admin_edittext_cat_{cat}")])
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "📝 <b>Select a screen text to edit:</b>", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data.startswith("admin_edittext_"):
            key = data.split("admin_edittext_")[1]
            context.user_data["awaiting_text_key"] = key
            
            if key.startswith("cat_"):
                name = f"Category: {key.replace('cat_', '')}"
            else:
                name = EDITABLE_TEXTS.get(key, key)
                
            keyboard = [
                [CB("Remove Caption (Clear)", style="danger", icon=get_button_emoji("clear"), callback_data=f"admin_cleartxt_{key}")],
                [CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="admin_texts")]
            ]
            await safe_edit(
                query, 
                f"📝 <b>Send the new text for {name}</b>\n\n(You can use HTML tags like &lt;b&gt;, &lt;i&gt; and emojis).\nType /cancel to abort.", 
                InlineKeyboardMarkup(keyboard), 
                parse_mode="HTML"
            )

        elif data.startswith("admin_cleartxt_"):
            key = data.split("admin_cleartxt_")[1]
            db.delete_setting(f"text_{key}")
            context.user_data["awaiting_text_key"] = None
            await query.answer("✅ Caption Removed / Reset to default!", show_alert=True)
            # Re-render admin_texts
            rows = []
            for k, v in EDITABLE_TEXTS.items():
                rows.append([CB(f"Edit {v} Text", style="primary", icon=get_button_emoji("tutorial"), callback_data=f"admin_edittext_{k}")])
            for cat in db.get_products().keys():
                rows.append([CB(f"Edit Category: {cat}", style="primary", icon=get_button_emoji("tutorial"), callback_data=f"admin_edittext_cat_{cat}")])
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "📝 <b>Select a screen text to edit:</b>", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data == "admin_emojis":
            context.user_data["awaiting_emoji_key"] = None
            rows = []
            keys = list(BUTTON_EMOJIS.keys())
            
            # dynamically add all product names
            for cat, prods in db.get_products().items():
                for p in prods.keys():
                    keys.append(f"prod_{p}")

            # display in chunks of 2
            for i in range(0, len(keys), 2):
                row = []
                for k in keys[i:i+2]:
                    btn_text = k.replace("prod_", "Product: ").capitalize()
                    emoji = get_button_emoji(k)
                    if not emoji: emoji = get_button_emoji("star")
                    row.append(CB(btn_text, style="primary", icon=emoji, callback_data=f"admin_editemoji_{k}"))
                rows.append(row)
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "✨ <b>Select an Emoji to edit:</b>", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data.startswith("admin_editemoji_"):
            key = data.split("admin_editemoji_")[1]
            context.user_data["awaiting_emoji_key"] = key
            display_name = key.replace("prod_", "Product: ").capitalize()
            keyboard = [
                [CB("Remove Emoji (Clear)", style="danger", icon=get_button_emoji("clear"), callback_data=f"admin_clearemoji_{key}")],
                [CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="admin_emojis")]
            ]
            await safe_edit(
                query, 
                f"✨ <b>Send the new Premium Emoji for '{display_name}'</b>\n\n(You can just send any premium emoji directly here, I will extract the ID!)\nType /cancel to abort.", 
                InlineKeyboardMarkup(keyboard), 
                parse_mode="HTML"
            )

        elif data.startswith("admin_clearemoji_"):
            key = data.split("admin_clearemoji_")[1]
            db.delete_setting(f"emoji_{key}")
            context.user_data["awaiting_emoji_key"] = None
            await query.answer("✅ Emoji Removed / Reset to default!", show_alert=True)
            # Re-render admin_emojis
            rows = []
            keys = list(BUTTON_EMOJIS.keys())
            for cat, prods in db.get_products().items():
                for p in prods.keys():
                    keys.append(f"prod_{p}")
            for i in range(0, len(keys), 2):
                row = []
                for k in keys[i:i+2]:
                    btn_text = k.replace("prod_", "Product: ").capitalize()
                    emoji = get_button_emoji(k)
                    if not emoji: emoji = get_button_emoji("star")
                    row.append(CB(btn_text, style="primary", icon=emoji, callback_data=f"admin_editemoji_{k}"))
                rows.append(row)
            rows.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, "✨ <b>Select an Emoji to edit:</b>", InlineKeyboardMarkup(rows), parse_mode="HTML")

        elif data == "admin_maintenance_menu":
            current = db.get_setting("maintenance_mode")
            status_text = "🟢 ON" if current == "1" else "🔴 OFF"
            toggle_text = "Turn OFF" if current == "1" else "Turn ON"
            
            keyboard = [
                [CB(f"Status: {status_text} (Click to {toggle_text})", style="primary", icon=get_button_emoji("star"), callback_data="admin_maintenance")],
                [CB("Change Maintenance Message", style="primary", icon=get_button_emoji("tutorial"), callback_data="admin_edittext_maintenance_msg")],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]
            ]
            
            text = "🛠 <b>MAINTENANCE MODE</b>\n\nWhen Maintenance Mode is ON, normal users will see the Maintenance Message instead of the bot menus. Admins can still use the bot normally."
            await safe_edit(query, text, InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_maintenance":
            current = db.get_setting("maintenance_mode")
            new_status = "0" if current == "1" else "1"
            db.set_setting("maintenance_mode", new_status)
            status_text = "🟢 ON" if new_status == "1" else "🔴 OFF"
            toggle_text = "Turn OFF" if new_status == "1" else "Turn ON"
            
            keyboard = [
                [CB(f"Status: {status_text} (Click to {toggle_text})", style="primary", icon=get_button_emoji("star"), callback_data="admin_maintenance")],
                [CB("Change Maintenance Message", style="primary", icon=get_button_emoji("tutorial"), callback_data="admin_edittext_maintenance_msg")],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]
            ]
            await query.answer(f"✅ Maintenance Mode is now {'ON' if new_status == '1' else 'OFF'}!", show_alert=True)
            text = "🛠 <b>MAINTENANCE MODE</b>\n\nWhen Maintenance Mode is ON, normal users will see the Maintenance Message instead of the bot menus. Admins can still use the bot normally."
            await safe_edit(query, text, InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_broadcast":
            context.user_data["awaiting_broadcast"] = True
            text = (
                "📢 <b>Broadcast Mode ON</b>\n\n"
                "Ab jo bhi message bhejoge (text, photo, video, voice, audio, document, sticker — kuch bhi) "
                "wo sabhi users ko bhej diya jaayega.\n\n"
                "Cancel karne ke liye /cancel bhejo."
            )
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_addproduct":
            context.user_data["awaiting_addproduct"] = True
            text = (
                "➕ <b>ADD PRODUCT</b>\n\n"
                "Reply is format mein ek hi message mein:\n"
                "<code>CATEGORY | NAME | PRODUCT_ID | PLAN | PRICE | ANDROID_ID</code>\n\n"
                "Example:\n"
                "<code>ANDROID NON ROOT | BALA MOD PRO | 133 | 1 Day | 150 | 0b9b969bc2e7997b</code>\n\n"
                "(ANDROID_ID optional hai)\n\n"
                "Cancel karne ke liye /cancel bhejo."
            )
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_removeproduct":
            products = db.get_all_products_flat()
            context.user_data["rm_products"] = products
            if not products:
                text = "📦 <b>Koi product nahi hai.</b>"
                keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            else:
                text = "🗑 <b>REMOVE PRODUCT</b>\n\nJis product ko delete karna hai use dabao:"
                keyboard = []
                for i, (category, name, plan_count) in enumerate(products):
                    label = f"{name} ({category}) — {plan_count} plan(s)"
                    cb = encode_cb("admin_rmprod_select", i)
                    keyboard.append([CB(label, style="danger", icon=get_button_emoji("remove"), callback_data=cb)])
                keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_rmprod_select" + SEP):
            parts = decode_cb(data)
            idx = int(parts[1])
            products = context.user_data.get("rm_products", [])
            if idx >= len(products):
                await query.answer("❌ List purani ho gayi, dobara kholo.", show_alert=True)
                return
            category, name, plan_count = products[idx]
            text = (
                f"⚠️ <b>Confirm Delete</b>\n\n"
                f"📦 <b>Product:</b> {name}\n"
                f"📂 <b>Category:</b> {category}\n"
                f"⏳ <b>Plans:</b> {plan_count}\n\n"
                f"Yeh product aur iske saare plans permanently delete ho jaayenge. Pakka?"
            )
            keyboard = [
                [CB("Yes, Delete", style="danger", icon=get_button_emoji("confirm"), callback_data=encode_cb("admin_rmprod_confirm", idx)),
                 CB("Cancel", style="primary", icon=get_button_emoji("cancel"), callback_data="admin_removeproduct")]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_rmprod_confirm" + SEP):
            parts = decode_cb(data)
            idx = int(parts[1])
            products = context.user_data.get("rm_products", [])
            if idx >= len(products):
                await query.answer("❌ List purani ho gayi, dobara kholo.", show_alert=True)
                return
            category, name, plan_count = products[idx]
            deleted = db.delete_product(category, name)
            if deleted:
                text = f"✅ <b>Deleted!</b>\n\n📦 {name} ({category}) ke {deleted} plan(s) remove ho gaye."
            else:
                text = "❌ Product nahi mila (shayad pehle hi delete ho chuka hai)."
            keyboard = [[CB("Back to Admin Panel", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_voicelink":
            products = db.get_all_products_flat()
            context.user_data["voicelink_products"] = products
            if not products:
                text = "📦 <b>Koi product nahi hai.</b>"
                keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            else:
                text = "🔊🔗 <b>MANAGE VOICE / LINK</b>\n\nJis product ka Voice/Link set karna hai use chuno:"
                keyboard = []
                for i, (category, name, plan_count) in enumerate(products):
                    label = f"{name} ({category})"
                    cb = encode_cb("admin_vlprod_select", i)
                    keyboard.append([CB(label, style="primary", icon=get_button_emoji("star"), callback_data=cb)])
                keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_vlprod_select" + SEP):
            parts = decode_cb(data)
            idx = int(parts[1])
            products = context.user_data.get("voicelink_products", [])
            if idx >= len(products):
                await query.answer("❌ Error: Invalid selection.", show_alert=True)
                return
            category, name, _ = products[idx]
            cat_products = db.db.products.find({"category": category, "name": name})
            first_plan = None
            for p in cat_products:
                first_plan = p
                break
            
            if not first_plan:
                await query.answer("❌ Error: Product not found.", show_alert=True)
                return
                
            product_id = first_plan.get("product_id")
            context.user_data["vl_product_id"] = product_id
            
            text = f"🔊🔗 <b>Manage Extras</b>\n\n<b>Product:</b> {name} ({category})\n\nKya set karna chahte ho?"
            keyboard = [
                [CB("Set Voice", style="primary", icon=get_button_emoji("add"), callback_data=f"admin_setvl_voice"),
                 CB("View", style="primary", icon=get_button_emoji("star"), callback_data=f"admin_viewvl_voice"),
                 CB("Remove", style="danger", icon=get_button_emoji("remove"), callback_data=f"admin_rmvl_voice")],
                [CB("Set Link", style="primary", icon=get_button_emoji("add"), callback_data=f"admin_setvl_link"),
                 CB("View", style="primary", icon=get_button_emoji("star"), callback_data=f"admin_viewvl_link"),
                 CB("Remove", style="danger", icon=get_button_emoji("remove"), callback_data=f"admin_rmvl_link")],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_voicelink")]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_setvl_voice":
            product_id = context.user_data.get("vl_product_id")
            if not product_id: return
            context.user_data["awaiting_product_voice"] = product_id
            text = "🔊 <b>Ab ek Voice ya Audio message bhejo</b> is product ke liye.\n\nCancel karne ke liye /cancel bhejo."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_voicelink")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_setvl_link":
            product_id = context.user_data.get("vl_product_id")
            if not product_id: return
            context.user_data["awaiting_product_link"] = product_id
            text = "🔗 <b>Ab ek Link (URL) bhejo</b> is product ke liye.\n\nCancel karne ke liye /cancel bhejo."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_voicelink")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_viewvl_voice":
            product_id = context.user_data.get("vl_product_id")
            if not product_id: return
            prod = db.db.products.find_one({"product_id": product_id})
            if prod and prod.get("voice_file_id"):
                await query.answer("Sending voice...")
                await context.bot.send_voice(chat_id=user_id, voice=prod["voice_file_id"])
            else:
                await query.answer("❌ No voice set for this product.", show_alert=True)
                
        elif data == "admin_rmvl_voice":
            product_id = context.user_data.get("vl_product_id")
            if not product_id: return
            db.set_product_voice(product_id, None)
            
            keyboard = [
                [CB("Set Voice", style="primary", icon=get_button_emoji("add"), callback_data="admin_setvl_voice"),
                 CB("View", style="primary", icon=get_button_emoji("star"), callback_data="admin_viewvl_voice"),
                 CB("Remove", style="danger", icon=get_button_emoji("remove"), callback_data="admin_rmvl_voice")],
                [CB("Set Link", style="primary", icon=get_button_emoji("add"), callback_data="admin_setvl_link"),
                 CB("View", style="primary", icon=get_button_emoji("star"), callback_data="admin_viewvl_link"),
                 CB("Remove", style="danger", icon=get_button_emoji("remove"), callback_data="admin_rmvl_link")],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_voicelink")]
            ]
            await safe_edit(query, text="✅ <b>Voice has been successfully REMOVED!</b>\n\nYou can set a new one or go back.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_viewvl_link":
            product_id = context.user_data.get("vl_product_id")
            if not product_id: return
            prod = db.db.products.find_one({"product_id": product_id})
            if prod and prod.get("product_link"):
                await query.answer("Sending link...")
                await context.bot.send_message(chat_id=user_id, text=f"🔗 <b>Link for Product:</b>\n{prod['product_link']}", parse_mode="HTML")
            else:
                await query.answer("❌ No link set for this product.", show_alert=True)

        elif data == "admin_rmvl_link":
            product_id = context.user_data.get("vl_product_id")
            if not product_id: return
            db.set_product_link(product_id, None)
            
            keyboard = [
                [CB("Set Voice", style="primary", icon=get_button_emoji("add"), callback_data="admin_setvl_voice"),
                 CB("View", style="primary", icon=get_button_emoji("star"), callback_data="admin_viewvl_voice"),
                 CB("Remove", style="danger", icon=get_button_emoji("remove"), callback_data="admin_rmvl_voice")],
                [CB("Set Link", style="primary", icon=get_button_emoji("add"), callback_data="admin_setvl_link"),
                 CB("View", style="primary", icon=get_button_emoji("star"), callback_data="admin_viewvl_link"),
                 CB("Remove", style="danger", icon=get_button_emoji("remove"), callback_data="admin_rmvl_link")],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_voicelink")]
            ]
            await safe_edit(query, text="✅ <b>Link has been successfully REMOVED!</b>\n\nYou can set a new one or go back.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_changeprice":
            products = db.get_all_products_flat()
            context.user_data["price_products"] = products
            if not products:
                text = "📦 <b>Koi product nahi hai.</b>"
                keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            else:
                text = "💰 <b>CHANGE PRICE</b>\n\nJis product ka price change karna hai use chuno:"
                keyboard = []
                for i, (category, name, plan_count) in enumerate(products):
                    label = f"{name} ({category}) — {plan_count} plan(s)"
                    cb = encode_cb("admin_priceprod_select", i)
                    keyboard.append([CB(label, style="primary", icon=get_button_emoji("star"), callback_data=cb)])
                keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
                await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_priceprod_select" + SEP):
            parts = decode_cb(data)
            idx = int(parts[1])
            products = context.user_data.get("price_products", [])
            if idx >= len(products):
                await query.answer("❌ List purani ho gayi, dobara kholo.", show_alert=True)
                return
            category, name, plan_count = products[idx]
            all_products = db.get_products()
            plans = all_products.get(category, {}).get(name, {}).get("plans", {})
            plan_ids = all_products.get(category, {}).get(name, {}).get("plan_ids", {})

            if not plans:
                await query.answer("❌ Is product ke plans nahi mile.", show_alert=True)
                return

            text = f"💰 <b>{name}</b> ({category})\n\nJis plan ka price change karna hai use chuno:"
            keyboard = []
            for plan_name, price in plans.items():
                plan_row_id = plan_ids.get(plan_name)
                label = f"{plan_name} — ₹{price:.0f}"
                keyboard.append([CB(label, style="primary", icon=get_button_emoji("add_balance"), callback_data=f"admin_priceplan_{plan_row_id}")])
            keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_changeprice")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_priceplan_"):
            plan_row_id = int(data.replace("admin_priceplan_", ""))
            plan = db.get_plan_by_id(plan_row_id)
            if not plan:
                await query.answer("❌ Plan not found.", show_alert=True)
                return
            context.user_data["awaiting_newprice_id"] = plan_row_id
            text = (
                f"💰 <b>Change Price</b>\n\n"
                f"📦 <b>Product:</b> {plan['name']}\n"
                f"⏳ <b>Plan:</b> {plan['plan']}\n"
                f"💵 <b>Current Price:</b> ₹{plan['price']:.2f}\n\n"
                f"Naya price type karo (sirf number, jaise 150):\n\n"
                f"Cancel karne ke liye /cancel bhejo."
            )
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_changeprice")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_welcomemedia":
            media_type, _ = db.get_welcome_media()
            status = {"photo": "📷 Photo set hai", "video": "🎥 Video set hai"}.get(media_type, "❌ Kuch set nahi hai (sirf text)")
            text = (
                "🖼 <b>WELCOME MEDIA</b>\n\n"
                "Jab koi user /start karega ya Main Menu pe wapas aayega, "
                "text ke saath ye photo/video dikhega.\n\n"
                f"<b>Current status:</b> {status}"
            )
            await safe_edit(query, text=text, reply_markup=get_welcome_media_keyboard(media_type), parse_mode="HTML")

        elif data == "admin_setwelcomephoto":
            context.user_data["awaiting_welcome_photo"] = True
            text = "📷 <b>Ab ek photo bhejo</b> jo welcome message mein use hogi.\n\nCancel karne ke liye /cancel bhejo."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_welcomemedia")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_setwelcomevideo":
            context.user_data["awaiting_welcome_video"] = True
            text = "🎥 <b>Ab ek video bhejo</b> jo welcome message mein use hogi.\n\nCancel karne ke liye /cancel bhejo."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_welcomemedia")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_removewelcomemedia":
            db.clear_welcome_media()
            text = "✅ <b>Welcome media hata di gayi.</b>\n\nAb welcome message sirf text mein aayega."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_welcomemedia")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_menumedia":
            text = (
                "🖼 <b>MENU MEDIA</b>\n\n"
                "In mein se kisi bhi screen ke liye photo/video set kar sakte ho — jab bhi user "
                "us button pe jaayega, text ke saath ye media dikhegi.\n\nEk screen chuno:"
            )
            keyboard = []
            for key, label in SCREEN_LABELS.items():
                media_type, _ = db.get_screen_media(key)
                status = "✅" if media_type else "▫️"
                keyboard.append([CB(f"{status} {label}", style="primary", icon=get_button_emoji("star"), callback_data=f"admin_screenmedia_{key}")])
            keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_screenmedia_"):
            screen_key = data.replace("admin_screenmedia_", "")
            label = SCREEN_LABELS.get(screen_key, screen_key)
            media_type, _ = db.get_screen_media(screen_key)
            status = {"photo": "📷 Photo set hai", "video": "🎥 Video set hai"}.get(media_type, "❌ Koi media set nahi hai")
            text = f"🖼 <b>{label}</b>\n\nCurrent status: {status}"
            keyboard = [
                [CB("Set Photo", style="primary", icon=get_button_emoji("add"), callback_data=f"admin_setscreenphoto_{screen_key}")],
                [CB("Set Video", style="primary", icon=get_button_emoji("add"), callback_data=f"admin_setscreenvideo_{screen_key}")],
            ]
            if media_type:
                keyboard.append([CB("Remove Media", style="danger", icon=get_button_emoji("remove"), callback_data=f"admin_removescreenmedia_{screen_key}")])
            keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_menumedia")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_setscreenphoto_"):
            screen_key = data.replace("admin_setscreenphoto_", "")
            context.user_data["awaiting_screen_photo"] = screen_key
            label = SCREEN_LABELS.get(screen_key, screen_key)
            text = f"📷 <b>Ab ek photo bhejo</b> jo <b>{label}</b> screen ke liye use hogi.\n\nCancel karne ke liye /cancel bhejo."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=f"admin_screenmedia_{screen_key}")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_setscreenvideo_"):
            screen_key = data.replace("admin_setscreenvideo_", "")
            context.user_data["awaiting_screen_video"] = screen_key
            context.user_data["awaiting_text_key"] = screen_key
            context.user_data["awaiting_emoji_key"] = screen_key
            label = SCREEN_LABELS.get(screen_key, screen_key)
            text = f"🎥 <b>Ab ek video bhejo</b> jo <b>{label}</b> screen ke liye use hogi.\n\nCancel karne ke liye /cancel bhejo."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=f"admin_screenmedia_{screen_key}")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_removescreenmedia_"):
            screen_key = data.replace("admin_removescreenmedia_", "")
            db.clear_screen_media(screen_key)
            label = SCREEN_LABELS.get(screen_key, screen_key)
            text = f"✅ <b>{label}</b> ki media hata di gayi."
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_menumedia")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_addbalance":
            context.user_data["awaiting_addbalance"] = True
            text = (
                "💰 <b>ADD BALANCE TO USER</b>\n\n"
                "Reply is format mein:\n"
                "<code>USER_ID AMOUNT</code>\n\n"
                "Example:\n"
                "<code>8373276191 500</code>\n\n"
                "Cancel karne ke liye /cancel bhejo."
            )
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_removebalance":
            context.user_data["awaiting_removebalance"] = True
            text = (
                "💸 <b>REMOVE BALANCE FROM USER</b>\n\n"
                "Reply is format mein:\n"
                "<code>USER_ID AMOUNT</code>\n\n"
                "Example:\n"
                "<code>8373276191 500</code>\n\n"
                "Cancel karne ke liye /cancel bhejo."
            )
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data == "admin_stats":
            stats = db.get_stats()
            text = f"""
    <tg-emoji emoji-id="6073308817125282940">📊</tg-emoji> <b>BOT STATISTICS</b>
    ━━━━━━━━━━━━━━━━━━
    <tg-emoji emoji-id="5301276827782755360">👥</tg-emoji> <b>Total Users:</b> {stats[0]}
    <tg-emoji emoji-id="6033106828018062225">💰</tg-emoji> <b>Total Wallet Balance:</b> ₹{stats[1]:.2f}
    <tg-emoji emoji-id="6294257044526469584">📋</tg-emoji> <b>Total Orders:</b> {stats[2]}
    <tg-emoji emoji-id="6033106828018062225">💰</tg-emoji> <b>Total Deposited:</b> ₹{stats[3]:.2f}
    ━━━━━━━━━━━━━━━━━━
    """
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_users":
            recent = db.get_recent_users(limit=25)
            total = len(db.get_all_user_ids())
            if recent:
                lines = [f"• <code>{uid}</code> — @{uname or 'N/A'} — ₹{bal:.2f}" for uid, uname, bal in recent]
                preview = "\n".join(lines)
            else:
                preview = "(No users yet)"
            text = (
                f'<tg-emoji emoji-id="5301276827782755360">👥</tg-emoji> <b>ALL USERS (Total: {total})</b>\n'
                "━━━━━━━━━━━━━━━━━━\n"
                f"{preview}\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "<i>Showing most recent 25 users.</i>"
            )
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_resellers":
            await query.answer("🚧 Manage Resellers is currently under construction. Coming soon!", show_alert=True)

        elif data == "admin_manage_captions":
            text = "📝 <b>MANAGE CAPTIONS</b>\n\nChoose what you want to customize:"
            keyboard = [
                [CB("📁 Category Captions", style="primary", icon="", callback_data="admin_list_cat_captions")],
                [CB("🛒 Product Captions", style="primary", icon="", callback_data="admin_list_prod_captions")],
                [CB("Back to Admin Panel", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_list_cat_captions":
            cat_order_str = db.get_setting("category_order")
            all_cats = list(db.get_products().keys())
            if not cat_order_str:
                order_list = all_cats
            else:
                order_list = [c.strip() for c in cat_order_str.split(",") if c.strip()]
                for c in all_cats:
                    if c not in order_list:
                        order_list.append(c)
            
            text = "📝 <b>CATEGORY CAPTIONS</b>\n\nSelect a category to change its caption:"
            keyboard = []
            for c in order_list:
                keyboard.append([CB(f"📁 {c}", style="primary", icon="", callback_data=encode_cb("admin_edit_cap", "cat", c))])
            keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_manage_captions")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_list_prod_captions":
            prods_flat = db.get_all_products_flat()
            text = "📝 <b>PRODUCT CAPTIONS</b>\n\nSelect a product to change its caption:"
            keyboard = []
            for p in prods_flat:
                keyboard.append([CB(f"🛒 {p[1]}", style="primary", icon="", callback_data=encode_cb("admin_edit_cap", "prod", p[1]))])
            keyboard.append([CB("Back", style="danger", icon=get_button_emoji("back"), callback_data="admin_manage_captions")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_edit_cap" + SEP):
            parts = decode_cb(data)
            cap_type = parts[1] # 'cat' or 'prod'
            name = parts[2]
            key = f"{cap_type}_{name}"
            
            if cap_type == "cat":
                default_text = f"<b>📁 Category: {name}</b>\n\nSelect a product to purchase:"
            else:
                default_text = f"<b>🛒 Product: {name}</b>\n\nChoose expiration pack period below:"
                
            current_text = get_text_safe(key, default_text)
            
            text = f"📝 <b>EDITING CAPTION</b>\n\n<b>Type:</b> {cap_type.upper()}\n<b>Name:</b> {name}\n\n<b>Current Caption:</b>\n<blockquote>{current_text}</blockquote>\n\nClick 'Change' to set a new caption, or 'Reset' to restore the default."
            
            keyboard = [
                [CB("Change Text", style="primary", icon="", callback_data=encode_cb("admin_change_cap", key))],
                [CB("Reset to Default", style="danger", icon="", callback_data=encode_cb("admin_reset_cap", key))],
                [CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=f"admin_list_{cap_type}_captions")]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_change_cap" + SEP):
            key = decode_cb(data)[1]
            context.user_data["awaiting_custom_text"] = key
            
            text = f"✏️ <b>Send me the new text for <code>{key}</code>!</b>\n\nYou can use HTML tags like <code>&lt;b&gt;bold&lt;/b&gt;</code>.\n\nType /cancel to abort."
            keyboard = [[CB("Cancel", style="danger", icon=get_button_emoji("cancel"), callback_data="admin_manage_captions")]]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_reset_cap" + SEP):
            key = decode_cb(data)[1]
            db.set_setting(key, "") 
            await query.answer(f"Reset {key} to default!", show_alert=True)
            
            cap_type = key.split("_", 1)[0]
            keyboard = [[CB("Back", style="danger", icon=get_button_emoji("back"), callback_data=f"admin_list_{cap_type}_captions")]]
            await safe_edit(query, text=f"✅ <b>Successfully reset {key}!</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_reorder_store":
            cat_order_str = db.get_setting("category_order")
            if not cat_order_str:
                order_list = list(db.get_products().keys())
            else:
                order_list = [c.strip() for c in cat_order_str.split(",") if c.strip()]
                all_cats = list(db.get_products().keys())
                for c in all_cats:
                    if c not in order_list:
                        order_list.append(c)
                
            text = "🔄 <b>REORDER STORE</b>\n\nClick ⬆️ or ⬇️ to move Categories. Click on a Category name to reorder its Products."
            keyboard = []
            for i, c in enumerate(order_list):
                row = [
                    CB(f"📁 {c}", style="primary", icon="", callback_data=encode_cb("admin_reorder_catprod", c)),
                    CB("⬆️", style="primary", icon="", callback_data=encode_cb("admin_reorder_cat_up", i)),
                    CB("⬇️", style="primary", icon="", callback_data=encode_cb("admin_reorder_cat_down", i))
                ]
                keyboard.append(row)
            keyboard.append([CB("Back to Admin Panel", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_reorder_cat_"):
            parts = decode_cb(data)
            action = parts[0]
            idx = int(parts[1])
            
            cat_order_str = db.get_setting("category_order")
            if not cat_order_str:
                order_list = list(db.get_products().keys())
            else:
                order_list = [c.strip() for c in cat_order_str.split(",") if c.strip()]
                all_cats = list(db.get_products().keys())
                for c in all_cats:
                    if c not in order_list:
                        order_list.append(c)
                        
            if action == "admin_reorder_cat_up" and idx > 0:
                order_list[idx], order_list[idx-1] = order_list[idx-1], order_list[idx]
            elif action == "admin_reorder_cat_down" and idx < len(order_list) - 1:
                order_list[idx], order_list[idx+1] = order_list[idx+1], order_list[idx]
            
            db.set_setting("category_order", ",".join(order_list))
            
            text = "🔄 <b>REORDER STORE</b>\n\nClick ⬆️ or ⬇️ to move Categories. Click on a Category name to reorder its Products."
            keyboard = []
            for i, c in enumerate(order_list):
                row = [
                    CB(f"📁 {c}", style="primary", icon="", callback_data=encode_cb("admin_reorder_catprod", c)),
                    CB("⬆️", style="primary", icon="", callback_data=encode_cb("admin_reorder_cat_up", i)),
                    CB("⬇️", style="primary", icon="", callback_data=encode_cb("admin_reorder_cat_down", i))
                ]
                keyboard.append(row)
            keyboard.append([CB("Back to Admin Panel", style="danger", icon=get_button_emoji("back"), callback_data="admin_panel")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_reorder_catprod" + SEP):
            parts = decode_cb(data)
            cat_name = parts[1]
            prods = list(db.db.products.find({"category": cat_name}).sort([("order", 1), ("name", 1)]))
            
            for i, p in enumerate(prods):
                if "order" not in p:
                    db.db.products.update_one({"_id": p["_id"]}, {"$set": {"order": i}})
                    p["order"] = i
            
            text = f"🔄 <b>REORDER PRODUCTS</b>\n\nCategory: <b>{cat_name}</b>\n\nClick ⬆️ or ⬇️ to change product position."
            keyboard = []
            for i, p in enumerate(prods):
                row = [
                    CB(p["name"], style="primary", icon="", callback_data="ignore"),
                    CB("⬆️", style="primary", icon="", callback_data=encode_cb("admin_reorder_prod_up", cat_name, i)),
                    CB("⬇️", style="primary", icon="", callback_data=encode_cb("admin_reorder_prod_down", cat_name, i))
                ]
                keyboard.append(row)
            keyboard.append([CB("Back to Categories", style="danger", icon=get_button_emoji("back"), callback_data="admin_reorder_store")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("admin_reorder_prod_"):
            parts = decode_cb(data)
            action = parts[0]
            cat_name = parts[1]
            idx = int(parts[2])
            
            prods = list(db.db.products.find({"category": cat_name}).sort([("order", 1), ("name", 1)]))
            for i, p in enumerate(prods):
                if "order" not in p:
                    db.db.products.update_one({"_id": p["_id"]}, {"$set": {"order": i}})
                    p["order"] = i
            
            if action == "admin_reorder_prod_up" and idx > 0:
                p1 = prods[idx]
                p2 = prods[idx-1]
                db.db.products.update_one({"_id": p1["_id"]}, {"$set": {"order": idx-1}})
                db.db.products.update_one({"_id": p2["_id"]}, {"$set": {"order": idx}})
                prods[idx], prods[idx-1] = prods[idx-1], prods[idx]
            elif action == "admin_reorder_prod_down" and idx < len(prods) - 1:
                p1 = prods[idx]
                p2 = prods[idx+1]
                db.db.products.update_one({"_id": p1["_id"]}, {"$set": {"order": idx+1}})
                db.db.products.update_one({"_id": p2["_id"]}, {"$set": {"order": idx}})
                prods[idx], prods[idx+1] = prods[idx+1], prods[idx]
            
            text = f"🔄 <b>REORDER PRODUCTS</b>\n\nCategory: <b>{cat_name}</b>\n\nClick ⬆️ or ⬇️ to change product position."
            keyboard = []
            for i, p in enumerate(prods):
                row = [
                    CB(p["name"], style="primary", icon="", callback_data="ignore"),
                    CB("⬆️", style="primary", icon="", callback_data=encode_cb("admin_reorder_prod_up", cat_name, i)),
                    CB("⬇️", style="primary", icon="", callback_data=encode_cb("admin_reorder_prod_down", cat_name, i))
                ]
                keyboard.append(row)
            keyboard.append([CB("Back to Categories", style="danger", icon=get_button_emoji("back"), callback_data="admin_reorder_store")])
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_welcome_reaction":
            status = db.get_setting("welcome_reaction_enabled")
            if status is None: status = "1"
            status_text = "🟢 ON" if status == "1" else "🔴 OFF"
            context.user_data["awaiting_welcome_reaction"] = True
            text = "🌟 <b>SET WELCOME REACTION</b>\n\nSend a standard emoji (like 🦄, 🔥) or a Premium Emoji to set as the reaction for /start.\n\nType /cancel to abort."
            keyboard = [
                [CB(f"Status: {status_text}", style="primary", icon="", callback_data="admin_toggle_reaction")],
                [CB("Clear Reaction", style="danger", icon=get_button_emoji("clear"), callback_data="admin_clear_reaction")]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
        elif data == "admin_toggle_reaction":
            status = db.get_setting("welcome_reaction_enabled")
            if status is None: status = "1"
            new_status = "0" if status == "1" else "1"
            db.set_setting("welcome_reaction_enabled", new_status)
            
            status_text = "🟢 ON" if new_status == "1" else "🔴 OFF"
            text = "🌟 <b>SET WELCOME REACTION</b>\n\nSend a standard emoji (like 🦄, 🔥) or a Premium Emoji to set as the reaction for /start.\n\nType /cancel to abort."
            keyboard = [
                [CB(f"Status: {status_text}", style="primary", icon="", callback_data="admin_toggle_reaction")],
                [CB("Clear Reaction", style="danger", icon=get_button_emoji("clear"), callback_data="admin_clear_reaction")]
            ]
            await safe_edit(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "admin_clear_reaction":
            db.set_setting("welcome_reaction", "")
            context.user_data["awaiting_welcome_reaction"] = False
            await query.answer("Welcome reaction cleared!", show_alert=True)
            text = "🛠 <b>ADMIN PANEL</b>\n\nChoose an action below:"
            await safe_edit(query, text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")

        else:
            logger.warning(f"Unknown admin callback: {data}")
            await query.answer("Unknown action.", show_alert=True)

    else:
        logger.warning(f"Unknown callback: {data}")
        await query.answer("Unknown action.", show_alert=True)




import telegram.error

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, telegram.error.BadRequest) and "parse entities" in str(context.error).lower():
        if hasattr(update, "effective_chat") and update.effective_chat:
            error_msg = "\u274c <b>HTML Formatting Error!</b>\n\nA custom text has invalid HTML. Please fix it in Admin Panel (Manage Texts)."
            try:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send error notice: {e}")

async def main():
    banner = r"""
╔══════════════════════════════════════════════╗
║   KARANPAY WALLET BOT — STARTING UP            ║
╚══════════════════════════════════════════════╝
"""
    try:
        import sys
        sys.stdout.buffer.write(banner.encode('utf-8') + b'\n')
    except Exception:
        pass
    logger.info("Bot boot sequence initiated...")
    logger.info(f"Receiver UPI      : {RECEIVER_UPI}")
    logger.info(f"PhonePe Key (1)      : {KARANPAY_KEY_1}")
    logger.info(f"GooglePay Key (2)   : {KARANPAY_KEY_2}")
    logger.info(f"Min Add Amount    : Rs.{MIN_AMOUNT}")
    logger.info("Buttons           : Premium Emojis Only")
    logger.info("Auto-Verify       : KaranPay check-status polling (every 10s)")

    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
    )

    app = Application.builder().token(TOKEN).request(request).build()
    app.add_error_handler(global_error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addproduct", add_product))
    app.add_handler(CommandHandler("broadcast", broadcast_start))
    app.add_handler(CommandHandler("cancel", broadcast_cancel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.User(ADMIN_ID) & ~filters.COMMAND, handle_admin_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), handle_user_message))


    monitor = KaranPayMonitor(db, app.bot)
    monitor.start()

    logger.info("Bot is now LIVE and polling for updates!")

    # Start dummy web server for Render health checks
    async def health_check(request):
        return web.Response(text="Bot is running!")
    
    webapp = web.Application()
    webapp.router.add_get('/', health_check)
    runner = web.AppRunner(webapp)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy web server started on port {port}")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())