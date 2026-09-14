#!/usr/bin/env python3
"""
Meesho Multi-Server Hunter & Account Creator Bot
=================================================
Key Features:
  1. Custom API Key per user (/setkey or '🔑 Set API Key')
  2. Select up to 2 servers simultaneously (/servers or '⚙️ Select Servers')
  3. Continuous Dual-Server Hunting:
     - Alternates buying between selected servers
     - Checks registration via Web Checker API
     - Auto-cancels registered numbers for refund
     - If fresh: sends OTP via Crowstack API, auto-fetches SMS from OTP Doctor,
       verifies login, and exports account JSON directly to Telegram!
  4. Manual Number Check ('📱 Check My Number'):
     - Checks registration status
     - If registered: prompts option to send OTP anyway
     - If fresh: sends OTP, verifies, and exports JSON
  5. Per-user settings saved persistently in user_configs.json
"""

import os
import sys
import time
import re
import json
import uuid
import random
import secrets
import base64
import io
import urllib.parse
import qrcode
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import httpx
from dotenv import load_dotenv

# Cryptography for fallback Meesho login
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Windows console encoding fix
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── Load Environment ─────────────────────────────────────────────────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8519590900:AAG8kn_xe0obnB1cvEId-CzTjR7GFSMYrtU")
DEFAULT_OTP_DOCTOR_KEY = os.getenv("OTPDOCTOR_API_KEY", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "8282846997").strip()
PORT = int(os.getenv("PORT", "10000"))

OTP_DOCTOR_BASE = "https://www.otpdoctor.in/stubs/handler_api.php"
OTP_DOCTOR_WEB_TOKEN = "6874841e41592b17f19761540921b8b4d200920078bff7d9cc8d843d7c32"

# ─── Crowstack Signup APIs (Primary OTP Send & Verify) ────────────────────────
CROWSTACK_BASE = "https://meesho.crowstack.tech/api/signup"
CROWSTACK_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://meesho.crowstack.tech",
    "Referer": "https://meesho.crowstack.tech/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "X-Tg-Init-Data": (
        "query_id=AAEVN7JtAwAAABU3sm2aUBhR&user=%7B%22id%22%3A8282846997%2C"
        "%22first_name%22%3A%22Marin%22%2C%22last_name%22%3A%22%22%2C"
        "%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C"
        "%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C"
        "%2FCd3jfjEFdjJYBiKIo4WzzZvJU53Lb8Cy84uyXS3KREOS1owG9u4WgR40VQwx0oOR.svg%22%7D"
        "&auth_date=1788610401&signature=k4mneTgLJIWH33XG-nBIs8kE-cNIsE70RKNacz3NZc80zbLpoq0BRRoTuEDZNCMX6Dy1p48Kxu6Jw_CajHMRAw"
        "&hash=54fb10c6a40b2b5fd9002abcc44d5871328080319f4f168796a053e7599ffcf5"
    ),
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

# User Referral Program Link
REFERRAL_LINK = "https://app.meesho.com/2yoV/r99th0qd?via=9qx7y4&from=referral_program"

# ─── Hidenfree APIs (Secondary Signup & Offer API) ───────────────────────────
HIDENFREE_BASE = "https://meeshoji.hidenfree.com/api"
HIDENFREE_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://meeshoji.hidenfree.com",
    "priority": "u=1, i",
    "referer": "https://meeshoji.hidenfree.com/",
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-fetch-storage-access": "active",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "x-session-token": "xhtB-VXF6ovxbGtzcH4rG2jIcRfRwZDYqbexKi9xSIM",
    "x-telegram-init-data": (
        "query_id=AAEVN7JtAwAAABU3sm1dbv1t&user=%7B%22id%22%3A8282846997%2C"
        "%22first_name%22%3A%22Marin%22%2C%22last_name%22%3A%22%22%2C"
        "%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C"
        "%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C"
        "%2FCd3jfjEFdjJYBiKIo4WzzZvJU53Lb8Cy84uyXS3KREOS1owG9u4WgR40VQwx0oOR.svg%22%7D"
        "&auth_date=1788664785&signature=pR7gnaXuO8XjW0Tl2YsNmyDNte-gOqIMH03dUvxjj0MKu1X1WD_lPjyHk6UIFocuWAt1WgDzaW1XuUsc4AlGCw"
        "&hash=133f05679fb179deec52c5ceddd68aa5dee2239825048bdeacb3f2a05fdf04fe"
    ),
}

# ─── GemixAI APIs (3rd Fallback Signup & Offer Reroll API) ────────────────────
GEMIXAI_BASE = "https://manish.gemixai.shop/meesho/api"
GEMIXAI_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://manish.gemixai.shop",
    "Pragma": "no-cache",
    "Referer": "https://manish.gemixai.shop/meesho/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Storage-Access": "active",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "X-User-Id": "u_xct9k1vmti8kavd",
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

# ─── Web Registration Checker APIs ────────────────────────────────────────────
CHECKER_PRIMARY = "https://pricetrackerpro.fojadomain.fun/api/check"
CHECKER_FALLBACK = "https://promeesho.eu.cc/api/check"

CHECKER_HEADERS_1 = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://pricetrackerpro.fojadomain.fun",
    "referer": "https://pricetrackerpro.fojadomain.fun/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "x-token": "8282846997.68a9acd4037ffb4c",
}

CHECKER_HEADERS_2 = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://promeesho.eu.cc",
    "referer": "https://promeesho.eu.cc/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "x-token": "8282846997.023e330b21f757ae",
}

# ─── Fallback Direct Meesho / OTPLESS Constants ────────────────────────────────
MEESHO_API_BASE = "https://prod.meeshoapi.com/api"
MEESHO_AUTH = "32c4d8137cn9eb493a1921f203173080"
MEESHO_RSA_PUBKEY_B64 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAslmrLKGRzVnAtii3o89yI33FXZoRfBJ"
    "V89PaCTp9Mxu7FgAaAOtaOnB2xWGG2a6Rz6zRzKPilRdAsm5oBW8mm8Uzvt7mbf7c7pjfBrjNdnKji"
    "/9/zM3fpjh364/GwG3OpyYngD49i09ySljA7Elh97Pp+QJH2z25Xv2eRSHJPizgQ8TE1bJkP9fd9J"
    "cfpGFyeEJX1bUIbgRlfED2TpJKGeaEfZ9no5+i/rgCaIRO9t86UqgeVJyCyJLnUkrU/ARPj9q/Aij"
    "JV9kvyPT137UQLO+Cl6nZYOglqGcPnRbGiW6WM7imkSxR2XBn6N4ojf49nJOwnN826hkdH5JaPJ1p"
    "AQIDAQAB"
)
OTPLESS_APP_ID = "XN07RN1IQC548C9YK5I4"
OTPLESS_PACKAGE = "com.meesho.supply"
OTPLESS_LOGIN_URI = "otpless.xn07rn1iqc548c9yk5i4://otpless"
OTPLESS_OTP_HASH = "oBcOM6bXKNc"
OTPLESS_APP_SIG = "oBcOM6bXKNcqouiPFcR1ur60Z6myTuVIDNSNWuKOlzU"
OTPLESS_UA = "okhttp/4.9.0"
OTPLESS_ORIGIN = "https://otpless.com"

DEVICE_INFO_OTPLESS = {
    "platform": "android",
    "vendor": "motorola",
    "browser": "",
    "connection": "",
    "language": "en-IN",
    "cookieEnabled": "",
    "screenWidth": 1080,
    "screenHeight": 2225,
    "userAgent": "Dalvik/2.1.0 (Linux; U; Android 12; moto g(60) Build/S2RI32.32-20-9-9-2) otplesssdk",
    "timezoneOffset": 330,
    "cpuArchitecture": "aarch64",
}
KEY_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()-_=+"

# ─── Default Known Meesho Servers ─────────────────────────────────────────────
KNOWN_SERVERS = {
    "5841": {"id": "5841", "name": "Server 5841 Ind8", "price": "₹12"},
    
    
    "19826": {"id": "19826", "name": "Server 19826MeeshoIn-9", "price": "₹9"},

}

USER_CONFIGS_FILE = "user_configs.json"
STORE_SETTINGS_FILE = "store_settings.json"
ORDERS_DB_FILE = "orders_db.json"
ACTIVE_TASKS = {}

DEFAULT_STORE_SETTINGS = {
    "meesho_price": int(os.getenv("MEESHO_PRICE", "99")),
    "upi_id": os.getenv("UPI_ID", "paytmqr28100505010115i3puxb4eoa@paytm").strip(),
    "upi_name": os.getenv("UPI_NAME", "Meesho JSON Store").strip(),
    "admin_username": os.getenv("ADMIN_USERNAME", "shivamthakur01").strip().lstrip("@"),
    "support_text": os.getenv("SUPPORT_TEXT", "Admin se baat karne ke liye yahan contact karein: @shivamthakur01"),
    "referral_link": os.getenv("REFERRAL_LINK", "https://app.meesho.com/2yoV/r99th0qd?via=9qx7y4&from=referral_program").strip(),
}


# ─── Persistent User Settings Storage ─────────────────────────────────────────
def load_all_configs() -> dict:
    if os.path.exists(USER_CONFIGS_FILE):
        try:
            with open(USER_CONFIGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_all_configs(configs: dict):
    try:
        with open(USER_CONFIGS_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config Save Error] {e}")


def get_user_config(chat_id: int | str) -> dict:
    configs = load_all_configs()
    cid = str(chat_id)
    if cid not in configs:
        configs[cid] = {
            "api_key": DEFAULT_OTP_DOCTOR_KEY,
            "selected_servers": ["5841"],
            "custom_servers": {},
        }
        save_all_configs(configs)
    return configs[cid]


def update_user_config(chat_id: int | str, updates: dict):
    configs = load_all_configs()
    cid = str(chat_id)
    cur = configs.get(cid, {
        "api_key": DEFAULT_OTP_DOCTOR_KEY,
        "selected_servers": ["5841"],
        "custom_servers": {},
    })
    cur.update(updates)
    configs[cid] = cur
    save_all_configs(configs)


# ─── Persistent Store & Order Storage ─────────────────────────────────────────
def load_store_settings() -> dict:
    settings = dict(DEFAULT_STORE_SETTINGS)
    if os.path.exists(STORE_SETTINGS_FILE):
        try:
            with open(STORE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except Exception:
            pass
    return settings


def save_store_settings(settings: dict):
    try:
        with open(STORE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[StoreSettings Save Error] {e}")


def get_store_price() -> int:
    return int(load_store_settings().get("meesho_price", 99))


def update_store_price(new_price: int):
    st = load_store_settings()
    st["meesho_price"] = int(new_price)
    save_store_settings(st)


def get_referral_link() -> str:
    st = load_store_settings()
    return (st.get("referral_link") or REFERRAL_LINK).strip()


def update_referral_link(new_link: str):
    st = load_store_settings()
    st["referral_link"] = new_link.strip()
    save_store_settings(st)


def get_store_upi_id() -> str:
    st = load_store_settings()
    return st.get("upi_id", "paytmqr28100505010115i3puxb4eoa@paytm").strip()


def get_store_upi_name() -> str:
    st = load_store_settings()
    return st.get("upi_name", "Meesho JSON Store").strip()


def update_store_upi(new_upi_id: str, new_name: str = None):
    st = load_store_settings()
    st["upi_id"] = new_upi_id.strip()
    if new_name:
        st["upi_name"] = new_name.strip()
    save_store_settings(st)


def load_orders() -> dict:
    if os.path.exists(ORDERS_DB_FILE):
        try:
            with open(ORDERS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_order(order: dict):
    orders = load_orders()
    orders[str(order["id"])] = order
    try:
        with open(ORDERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Orders Save Error] {e}")


def get_order(order_id: str) -> dict | None:
    orders = load_orders()
    return orders.get(str(order_id))


def get_user_orders(user_id: int | str) -> list:
    orders = load_orders()
    uid = str(user_id)
    return [ord for ord in orders.values() if str(ord.get("user_id")) == uid]


def is_admin(chat_id: int | str) -> bool:
    cid = str(chat_id).strip()
    admin_ids = [ADMIN_CHAT_ID] if ADMIN_CHAT_ID else []
    extra_admins = [x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    admin_ids.extend(extra_admins)
    return cid in admin_ids


def generate_upi_qr_bytes(upi_id: str, upi_name: str, amount: float | int, order_id: str) -> bytes:
    upi_url = f"upi://pay?pa={upi_id}&pn={urllib.parse.quote(upi_name)}&am={amount}&cu=INR&tn={urllib.parse.quote(f'Order {order_id}')}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio.getvalue()


# ─── Health Server for Render / Cloud ─────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"Meesho Multi-Server Hunter Bot"}')

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def log_message(self, format, *args):
        pass


def start_health_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        print(f"[Health Server] Listening on port {PORT}...")
        server.serve_forever()
    except Exception as e:
        print(f"[Health Server Error] {e}")


# ─── Helper Functions ─────────────────────────────────────────────────────────
def clean_phone(raw: str) -> str:
    d = re.sub(r"\D", "", str(raw))
    if len(d) == 12 and d.startswith("91"):
        return d[2:]
    return d[-10:] if len(d) >= 10 else d


def parse_wait_time(msg: str) -> int:
    total = 0
    m = re.search(r"(\d+)\s*minute", msg)
    if m:
        total += int(m.group(1)) * 60
    s = re.search(r"(\d+)\s*second", msg)
    if s:
        total += int(s.group(1))
    return total if total > 0 else 120


def _ts_id():
    return f"{uuid.uuid4()}-{int(time.time() * 1000)}"


def gen_key() -> str:
    return "".join(secrets.choice(KEY_CHARSET) for _ in range(16))


def aes_gcm_encrypt(plaintext: bytes, key: str) -> str:
    iv = os.urandom(12)
    ct = AESGCM(key[:16].encode("utf-8")).encrypt(iv, plaintext, None)
    return base64.b64encode(iv + ct).decode("ascii")


def rsa_encrypt(data: str) -> str:
    pub = serialization.load_der_public_key(base64.b64decode(MEESHO_RSA_PUBKEY_B64))
    return base64.b64encode(pub.encrypt(data.encode("utf-8"), rsa_padding.PKCS1v15())).decode("ascii")


def mk_device():
    return {
        "brand": "motorola",
        "manufacturer": "motorola",
        "model": "moto g(60)",
        "os_version": "12",
        "gaid": str(uuid.uuid4()),
        "android_id": uuid.uuid4().hex[:16],
        "instance_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "user_agent": "Dalvik/2.1.0 (Linux; U; Android 12; moto g(60) Build/) Cronet/137.0.7100.61",
    }


# ─── Telegram Bot API Helpers ─────────────────────────────────────────────────
async def send_tg_message(client: httpx.AsyncClient, chat_id: int | str, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = await client.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[TG Error] send_tg_message: {e}")
        return None


async def send_tg_document(client: httpx.AsyncClient, chat_id: int | str, filename: str, content: str | bytes, caption: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    if isinstance(content, str):
        content = content.encode("utf-8")
    files = {"document": (filename, content, "application/json")}
    data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
    try:
        r = await client.post(url, data=data, files=files, timeout=25.0)
        return r.json()
    except Exception as e:
        print(f"[TG Error] send_tg_document: {e}")
        return None


async def send_tg_photo(client: httpx.AsyncClient, chat_id: int | str, photo_bytes: bytes, caption: str = "", reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("qrcode.png", photo_bytes, "image/png")}
    data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
    try:
        r = await client.post(url, data=data, files=files, timeout=25.0)
        return r.json()
    except Exception as e:
        print(f"[TG Error] send_tg_photo: {e}")
        return None


async def answer_tg_callback(client: httpx.AsyncClient, callback_query_id: str, text: str = None, show_alert: bool = False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        payload["text"] = text
    try:
        r = await client.post(url, json=payload, timeout=10.0)
        return r.json()
    except Exception as e:
        print(f"[TG Error] answer_tg_callback: {e}")
        return None


# ─── OTP Doctor API Helpers ───────────────────────────────────────────────────
async def otpd_balance(client: httpx.AsyncClient, api_key: str) -> str:
    try:
        r = await client.get(OTP_DOCTOR_BASE, params={"action": "getBalance", "api_key": api_key}, timeout=10)
        t = r.text.strip()
        return t.split(":")[1] if t.startswith("ACCESS_BALANCE:") else t
    except Exception as e:
        return f"Error ({e})"


async def otpd_buy(client: httpx.AsyncClient, api_key: str, svc_id: str) -> dict:
    try:
        r = await client.get(OTP_DOCTOR_BASE, params={"action": "getNumber", "api_key": api_key, "service": svc_id}, timeout=15)
        t = r.text.strip()
        if t.startswith("ACCESS_NUMBER:"):
            parts = t.split(":")
            return {"ok": True, "id": parts[1], "phone": clean_phone(parts[2]), "raw": parts[2], "server_id": svc_id}
        return {"ok": False, "error": t, "server_id": svc_id}
    except Exception as e:
        return {"ok": False, "error": str(e), "server_id": svc_id}


async def otpd_cancel(client: httpx.AsyncClient, api_key: str, act_id: str) -> bool:
    for _ in range(5):
        try:
            r = await client.get(OTP_DOCTOR_BASE, params={"action": "setStatus", "api_key": api_key, "id": act_id, "status": "8"}, timeout=10)
            t = r.text.strip()
            if "CANCEL" in t or "ACCESS" in t:
                return True
        except Exception:
            pass

        try:
            r2 = await client.get(
                "https://www.otpdoctor.in/api/service/cancelNumberq.php",
                params={"token": OTP_DOCTOR_WEB_TOKEN, "id": act_id},
                headers={"user-agent": CHECKER_HEADERS_1["user-agent"]},
                timeout=10,
            )
            data = r2.json()
            if data.get("status") == 200:
                return True
            if data.get("status") == 600:
                wait_sec = parse_wait_time(data.get("message", ""))
                await asyncio.sleep(wait_sec + 2)
                continue
        except Exception:
            pass

        await asyncio.sleep(3)
    return False


async def otpd_get_sms(client: httpx.AsyncClient, api_key: str, act_id: str) -> dict:
    try:
        r = await client.get(OTP_DOCTOR_BASE, params={"action": "getStatus", "api_key": api_key, "id": act_id}, timeout=10)
        t = r.text.strip()
        if t.startswith("STATUS_OK:"):
            return {"ok": True, "sms": t.split(":", 1)[1]}
        elif t == "STATUS_WAIT_CODE":
            return {"ok": False, "waiting": True}
        else:
            return {"ok": False, "waiting": False, "error": t}
    except Exception as e:
        return {"ok": False, "waiting": False, "error": str(e)}


# ─── Web Registration Checker ─────────────────────────────────────────────────
async def check_meesho_reg(client: httpx.AsyncClient, phone: str) -> dict:
    payload = {"number": phone}
    last_err = ""
    for url, hdr in [(CHECKER_PRIMARY, CHECKER_HEADERS_1), (CHECKER_FALLBACK, CHECKER_HEADERS_2)]:
        try:
            r = await client.post(url, json=payload, headers=hdr, timeout=10)
            if r.status_code == 200:
                d = r.json()
                if d.get("ok") and d.get("results"):
                    res = d["results"][0]
                    return {
                        "registered": res.get("registered", False),
                        "fresh": res.get("fresh", False),
                        "ok": True,
                        "error": None,
                    }
                elif d.get("error") or d.get("message"):
                    last_err = d.get("error") or d.get("message")
            else:
                last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
            continue

    # 2. Third Fallback: Hidenfree check-phone API
    try:
        r_hf = await client.post(f"{HIDENFREE_BASE}/login/check-phone", headers=HIDENFREE_HEADERS, json={"phone": phone}, timeout=10)
        if r_hf.status_code == 200:
            d_hf = r_hf.json()
            if d_hf.get("ok"):
                is_reg = bool(d_hf.get("registered", False))
                return {
                    "registered": is_reg,
                    "fresh": not is_reg,
                    "ok": True,
                    "error": None,
                }
    except Exception as e:
        last_err = str(e)

    return {"registered": None, "fresh": None, "ok": False, "error": last_err or "All checker endpoints unreachable"}


# ─── Send OTP & Verify (Crowstack + Fallback) ──────────────────────────────────
async def send_meesho_otpless_fallback(client: httpx.AsyncClient, phone: str, dev: dict) -> dict:
    ts_id, in_id = _ts_id(), _ts_id()
    hdr = {"user-agent": OTPLESS_UA}
    try:
        st_resp = await client.get(
            "https://user-auth.otpless.app/v2/state",
            params={
                "origin": OTPLESS_ORIGIN, "version": "V3", "tsId": ts_id, "inId": in_id,
                "isHeadless": "true", "platform": "android", "isLoginPage": "false",
                "packageName": OTPLESS_PACKAGE, "package": OTPLESS_PACKAGE,
                "appId": OTPLESS_APP_ID, "loginUri": OTPLESS_LOGIN_URI,
                "deviceInfo": json.dumps(DEVICE_INFO_OTPLESS),
            },
            headers=hdr,
            timeout=15,
        )
        state = (st_resp.json() or {}).get("state")
        if not state:
            return {"ok": False, "error": "State failed from OTPLESS"}

        app_info = {
            "platform": "android", "manufacturer": dev["manufacturer"],
            "androidVersion": dev["os_version"], "packageName": OTPLESS_PACKAGE,
            "model": dev["model"], "appSignature": OTPLESS_APP_SIG,
            "hasTelegram": "true", "hasWhatsapp": "false", "sdkVersion": "1.3.3",
            "inId": in_id, "tsId": ts_id,
            "isSilentAuthSupported": "true", "isWebAuthnSupported": "true",
            "isCellularDataEnabled": "false",
            "secureDetail": {"simDetail": {"currentTransportType": "WiFi", "isSimInserted": "false"}},
        }
        intent_body = {
            "selectedCountryCode": "+91", "mobile": f"91{phone}",
            "silentAuthEnabled": False, "hasWhatsapp": "false", "deliveryChannel": "SMS",
            "metadata": json.dumps({
                "appInfo": json.dumps(app_info),
                "deviceInfo": json.dumps(DEVICE_INFO_OTPLESS),
                "deviceIdInfo": json.dumps({"androidId": dev["android_id"], "gaid": dev["gaid"]}),
            }),
            "triggerWebauthn": False,
            "clientMetaData": json.dumps({"tid": secrets.token_urlsafe(12)[:16]}),
            "origin": OTPLESS_ORIGIN, "version": "V4",
            "tsId": ts_id, "inId": in_id,
            "deviceInfo": json.dumps(DEVICE_INFO_OTPLESS),
            "loginUri": OTPLESS_LOGIN_URI, "appId": OTPLESS_APP_ID,
            "isHeadless": True, "packageName": OTPLESS_PACKAGE, "package": OTPLESS_PACKAGE,
            "otpHash": OTPLESS_OTP_HASH, "platform": "HEADLESS",
        }

        ir = await client.post(
            f"https://user-auth.otpless.app/v3/lp/user/transaction/intent/{state}",
            headers={**hdr, "content-type": "application/json; charset=utf-8"},
            json=intent_body,
            timeout=15,
        )
        data = ir.json() or {}
        leap = data.get("quantumLeap") or {}
        if not leap.get("uid") or not leap.get("channelAuthToken"):
            return {"ok": False, "error": f"OTP intent rejected: {json.dumps(data)[:150]}"}

        return {
            "ok": True,
            "session": {
                "method": "otpless",
                "state": state, "uid": leap["uid"], "token": leap["channelAuthToken"],
                "as_id": leap.get("asId", ""), "ts_id": ts_id, "in_id": in_id,
                "instance_id": dev["instance_id"],
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def verify_meesho_otpless_fallback(client: httpx.AsyncClient, phone: str, otp: str, session: dict, dev: dict) -> dict:
    otp_headers = {"user-agent": OTPLESS_UA, "content-type": "application/json; charset=utf-8"}
    otp_body = {
        "selectedCountryCode": "91", "mobile": phone, "otp": otp, "value": f"91{phone}",
        "isOTPAutoRead": "false", "uid": session["uid"], "token": session["token"], "asId": session["as_id"],
        "origin": OTPLESS_ORIGIN, "version": "V4", "tsId": session["ts_id"], "inId": session["in_id"],
        "deviceInfo": json.dumps(DEVICE_INFO_OTPLESS, separators=(",", ":")),
        "loginUri": OTPLESS_LOGIN_URI, "appId": OTPLESS_APP_ID,
        "isHeadless": True, "packageName": OTPLESS_PACKAGE, "package": OTPLESS_PACKAGE,
        "otpHash": OTPLESS_OTP_HASH, "platform": "HEADLESS",
    }
    try:
        vr = await client.post(
            f"https://user-auth.otpless.app/v3/lp/user/transaction/otp/{session['state']}",
            headers=otp_headers, json=otp_body, timeout=15,
        )
        data = vr.json() or {}
        ot = data.get("oneTap") or {}
        token = ot.get("token")
        id_token = (ot.get("merchantUserInfo") or {}).get("idToken")
        if not token or not id_token:
            status = (data.get("authDetail") or {}).get("status", "FAILED")
            return {"ok": False, "error": f"OTP verification failed ({status})."}

        key = gen_key()
        login_body = {
            "login_type": "otpless",
            "otpless": {
                "token": token,
                "id_token": aes_gcm_encrypt(id_token.encode("utf-8"), key),
                "aes_key_encrypted": rsa_encrypt(key),
                "version": "v2",
            },
            "ga_id": dev["gaid"],
        }
        anon_hdr = {
            "authorization": MEESHO_AUTH, "app-version": "29.1", "app-version-code": "860",
            "instance-id": dev["instance_id"], "country-iso": "in",
            "application-id": "com.meesho.supply", "app-session-id": dev["session_id"],
            "app-sdk-version": "34", "app-client-id": "android", "xo": "",
            "meesho-user-context": "anonymous", "content-type": "application/json; charset=UTF-8",
            "user-agent": dev["user_agent"],
        }
        lr = await client.post(f"{MEESHO_API_BASE}/2.0/user/login", headers=anon_hdr, json=login_body, timeout=15)
        if lr.status_code != 200:
            return {"ok": False, "error": f"Login HTTP {lr.status_code}: {lr.text[:150]}"}

        ld = lr.json() or {}
        user = ld.get("user") or {}
        xoox = ld.get("xoox") or {}
        xo = xoox.get("xo") or ""
        ox = xoox.get("ox") or ""
        if not xo:
            return {"ok": False, "error": "Login failed: No xo received."}

        return {
            "ok": True,
            "user_id": user.get("user_id"),
            "phone": user.get("phone"),
            "xo": xo,
            "ox": ox,
            "is_new": bool(user.get("new")),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def send_meesho_otp(client: httpx.AsyncClient, phone: str, dev: dict, chat_id: int | str = None) -> dict:
    """Dispatches OTP using Crowstack API (primary) -> Hidenfree API -> GemixAI API (with ₹200 reroll) -> direct OTPLESS."""
    # 1. Primary: Crowstack API (with dynamic user referral link)
    try:
        cur_ref = get_referral_link()
        payload = {"phone": phone, "ref_link": cur_ref, "force": True}
        resp = await client.post(
            f"{CROWSTACK_BASE}/send-otp",
            headers=CROWSTACK_HEADERS,
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json() or {}
            if data.get("ok"):
                return {
                    "ok": True,
                    "method": "crowstack",
                    "registered": data.get("registered"),
                    "bucket": data.get("bucket"),
                    "session": {
                        "method": "crowstack",
                        "phone": phone,
                        "instance_id": dev["instance_id"],
                    },
                }
            else:
                print(f"[Crowstack send-otp rejected]: {data}")
    except Exception as e:
        print(f"[Crowstack send-otp warning]: {e}")

    # 2. Secondary Fallback: Hidenfree API (with offer hunt)
    try:
        print(f"[Fallback] Crowstack unavailable, trying Hidenfree API for +91{phone}...")
        try:
            await client.post(f"{HIDENFREE_BASE}/offer/hunt", headers=HIDENFREE_HEADERS, json={"target": 200}, timeout=8)
        except Exception:
            pass

        chk_resp = await client.post(f"{HIDENFREE_BASE}/login/check-phone", headers=HIDENFREE_HEADERS, json={"phone": phone}, timeout=10)
        chk_data = chk_resp.json() if chk_resp.status_code == 200 else {}

        req_resp = await client.post(f"{HIDENFREE_BASE}/login/request-otp", headers=HIDENFREE_HEADERS, json={"phone": phone}, timeout=15)
        if req_resp.status_code == 200:
            data = req_resp.json() or {}
            if data.get("ok"):
                return {
                    "ok": True,
                    "method": "hidenfree",
                    "registered": data.get("registered", chk_data.get("registered")),
                    "bucket": chk_data.get("offer_bucket") or 200,
                    "session": {
                        "method": "hidenfree",
                        "phone": phone,
                        "instance_id": dev["instance_id"],
                    },
                }
            else:
                print(f"[Hidenfree request-otp rejected]: {data}")
    except Exception as e:
        print(f"[Hidenfree request-otp error]: {e}")

    # 3. Tertiary Fallback: GemixAI API (with Reroll until ₹200 OFF is found)
    try:
        print(f"[Fallback] Hidenfree unavailable, trying GemixAI API for +91{phone} (rerolling for ₹200 OFF)...")
        offer_bucket = 0
        for rr_try in range(1, 31):
            try:
                rr_resp = await client.post(f"{GEMIXAI_BASE}/reroll", headers=GEMIXAI_HEADERS, timeout=10)
                if rr_resp.status_code == 200:
                    rr_data = rr_resp.json() or {}
                    offer = rr_data.get("offer") or {}
                    b = offer.get("bucket") or offer.get("max_offer_value") or 0
                    if b >= 200:
                        offer_bucket = b
                        print(f"[GemixAI] Found ₹{offer_bucket} OFF offer on try #{rr_try}!")
                        break
            except Exception:
                pass
            await asyncio.sleep(0.4)

        if not offer_bucket:
            offer_bucket = 200

        if chat_id:
            await send_tg_message(
                client,
                chat_id,
                f"🎯 <b>GemixAI: ₹{offer_bucket} OFF Offer Mil Gaya!</b>\n📤 Ab <code>+91{phone}</code> par OTP bhej rahe hain...",
            )

        # Send OTP via GemixAI
        otp_payload = {"phone": phone}
        otp_resp = await client.post(
            f"{GEMIXAI_BASE}/auth/otp",
            headers=GEMIXAI_HEADERS,
            json=otp_payload,
            timeout=15,
        )
        if otp_resp.status_code == 200:
            otp_data = otp_resp.json() or {}
            if otp_data.get("success"):
                return {
                    "ok": True,
                    "method": "gemixai",
                    "registered": False,
                    "bucket": offer_bucket,
                    "session": {
                        "method": "gemixai",
                        "phone": phone,
                        "bucket": offer_bucket,
                        "instance_id": dev["instance_id"],
                    },
                }
            else:
                print(f"[GemixAI send-otp rejected]: {otp_data}")
    except Exception as e:
        print(f"[GemixAI send-otp error]: {e}")

    # 4. Quaternary Fallback: Direct OTPLESS
    return await send_meesho_otpless_fallback(client, phone, dev)


async def verify_meesho_otp(client: httpx.AsyncClient, phone: str, otp: str, session: dict, dev: dict) -> dict:
    """Verifies OTP via Crowstack, Hidenfree, GemixAI, or fallback to OTPLESS."""
    # Method 1: Crowstack
    if session.get("method") == "crowstack":
        try:
            payload = {"otp": otp}
            resp = await client.post(
                f"{CROWSTACK_BASE}/verify",
                headers=CROWSTACK_HEADERS,
                json=payload,
                timeout=15,
            )
            data = resp.json() if resp.status_code == 200 else {}
            if data.get("ok"):
                acc = data.get("account", {})
                return {
                    "ok": True,
                    "user_id": acc.get("user_id"),
                    "phone": acc.get("mobile", phone),
                    "account": acc,
                    "bucket": acc.get("offer_bucket") or acc.get("bucket"),
                    "is_new": True,
                }
            err = data.get("error") or data.get("message") or "Verification failed"
            return {"ok": False, "error": f"Crowstack: {err}"}
        except Exception as e:
            return {"ok": False, "error": f"Crowstack verify error: {str(e)}"}

    # Method 2: Hidenfree
    if session.get("method") == "hidenfree":
        try:
            payload = {"otp": otp}
            resp = await client.post(
                f"{HIDENFREE_BASE}/login/verify",
                headers=HIDENFREE_HEADERS,
                json=payload,
                timeout=15,
            )
            data = resp.json() if resp.status_code == 200 else {}
            if data.get("ok"):
                return {
                    "ok": True,
                    "user_id": str(data.get("user_id", "")),
                    "phone": phone,
                    "account": data,
                    "bucket": data.get("offer_bucket") or 200,
                    "is_new": data.get("is_new_user", True),
                }
            err = data.get("error") or data.get("message") or "Verification failed"
            return {"ok": False, "error": f"Hidenfree: {err}"}
        except Exception as e:
            return {"ok": False, "error": f"Hidenfree verify error: {str(e)}"}

    # Method 3: GemixAI
    if session.get("method") == "gemixai":
        try:
            payload = {"phone": phone, "otp": otp, "name": ""}
            resp = await client.post(
                f"{GEMIXAI_BASE}/auth/verify",
                headers=GEMIXAI_HEADERS,
                json=payload,
                timeout=15,
            )
            data = resp.json() if resp.status_code == 200 else {}
            if data.get("success"):
                exp_acc = {}
                try:
                    exp_resp = await client.get(
                        f"{GEMIXAI_BASE}/account/export",
                        headers=GEMIXAI_HEADERS,
                        params={"phone": phone},
                        timeout=10,
                    )
                    if exp_resp.status_code == 200:
                        exp_data = exp_resp.json() or {}
                        if exp_data.get("success"):
                            exp_acc = exp_data.get("export") or {}
                except Exception:
                    pass

                user_id = str(exp_acc.get("user_id") or data.get("user_id") or "")
                xo = exp_acc.get("xo", "")
                ox = exp_acc.get("ox", "")
                return {
                    "ok": True,
                    "user_id": user_id,
                    "phone": phone,
                    "account": {**data, **exp_acc},
                    "xo": xo,
                    "ox": ox,
                    "bucket": session.get("bucket", 200),
                    "is_new": True,
                }
            err = data.get("error") or data.get("message") or "Verification failed"
            return {"ok": False, "error": f"GemixAI: {err}"}
        except Exception as e:
            return {"ok": False, "error": f"GemixAI verify error: {str(e)}"}

    return await verify_meesho_otpless_fallback(client, phone, otp, session, dev)


# ─── JSON Template System ─────────────────────────────────────────────────────
DEFAULT_JSON_TEMPLATE = {
    "mobile": "7500808645",
    "user_id": 593576538,
    "phone": "+917500808645",
    "xo": "",
    "ox": "",
    "instance_id": "",
    "gaid": "",
    "identity": {
        "instance_id": "",
        "gaid": "",
        "android_id": "5ada076fd13b1deb",
        "media_id": "7e243fcf5491daa686dff23e8d724500e9bcbb52b18599fc0dd4a5da311ad921",
        "app_session_id": "7354f6d9-a1c4-437f-a776-f191b44ec8cb",
        "make": "Google",
        "model": "Pixel 8a",
        "build": "CP2A.260605.012",
        "android": "15",
        "dalvik_ua": "Dalvik/2.1.0 (Linux; U; Android 15; Pixel 8a Build/CP2A.260605.012) otplesssdk",
        "connection_type": "MOBILE",
        "carrier": "airtel",
        "screen_width": 1080,
        "screen_height": 2400,
        "screen_dpi": 420,
        "fcm_token": "tvBlQdCyAfe:APA91bHEpgWTdLgB1vaiLkHexQ9M0vpKkfkOxZAkDaz6h9ps7WRUyzpB64QLeOzYWKXHopJ8Yx2unXOq2xYZDJg3iQihPd0RwP5RzZMJZpCnHc00vh35aN44UBReqddaYWMIakeVJoFy",
        "xff": "103.51.251.146",
        "anon_xo": "eyJ0eXBlIjoiY29tcG9zaXRlIn0=.eyJqd3QiOiJleUpoYkdjaU9pSklVekkxTmlJc0ltaDBkSEJ6T2k4dmJXVmxjMmh2TG1OdmJTOXBjMjlmWTI5MWJuUnllVjlqYjJSbElqb2lTVTRpTENKb2RIUndjem92TDIxbFpYTm9ieTVqYjIwdmRtVnljMmx2YmlJNklqRWlMQ0owZVhBaU9pSktWMVFpZlEuZXlKbGVIQWlPakU1TkRZeE1qWXlNalFzSW1oMGRIQnpPaTh2YldWbGMyaHZMbU52YlM5aGJtOXVlVzF2ZFhOZmRYTmxjbDlwWkNJNklqSTNORFEwTXpRd0xXWTVOV1V0TkRSbVppMDROVGhpTFdObE9XRTNaVEJtTURZNU55SXNJbWgwZEhCek9pOHZiV1ZsYzJodkxtTnZiUzlwYm5OMFlXNWpaVjlwWkNJNkltRTNZekExTURFeU9EQTRPR1kzTWpFMk5HUXdZelF5WVRFMU1UZGxaV1JoSWl3aWFXRjBJam94TnpnNE5EUTJNakkwZlEuNWtxb01SVmNDRm85eFVWSVc5bnRXcnhLbWJLcmNjSzVoT3JXaVRtaHdLYyIsInhvIjoiIn0=",
        "_referral_done": True,
        "gender": "Male",
        "age_group": "0-18"
    }
}


def format_account_json(template: dict | None, phone: str, user_id: any, xo: str, ox: str, dev: dict) -> dict:
    import copy
    tmpl = copy.deepcopy(template) if template and isinstance(template, dict) else copy.deepcopy(DEFAULT_JSON_TEMPLATE)

    uid_val = user_id
    try:
        if str(user_id).isdigit():
            uid_val = int(user_id)
    except Exception:
        pass

    inst_id = dev.get("instance_id") or str(uuid.uuid4())
    gaid = dev.get("gaid") or str(uuid.uuid4())

    if "mobile" in tmpl:
        tmpl["mobile"] = str(phone)
    else:
        tmpl["mobile"] = str(phone)

    if "phone" in tmpl:
        tmpl["phone"] = f"+91{phone}"

    if "user_id" in tmpl:
        tmpl["user_id"] = uid_val
    else:
        tmpl["user_id"] = uid_val

    if "xo" in tmpl:
        tmpl["xo"] = xo
    else:
        tmpl["xo"] = xo

    if "ox" in tmpl:
        tmpl["ox"] = ox
    else:
        tmpl["ox"] = ox

    if "instance_id" in tmpl:
        tmpl["instance_id"] = inst_id
    if "gaid" in tmpl:
        tmpl["gaid"] = gaid

    if "identity" in tmpl and isinstance(tmpl["identity"], dict):
        ident = tmpl["identity"]
        ident["instance_id"] = inst_id
        ident["gaid"] = gaid
        if dev.get("android_id"):
            ident["android_id"] = dev["android_id"]
        if dev.get("session_id"):
            ident["app_session_id"] = dev["session_id"]
    elif "identity" not in tmpl:
        tmpl["identity"] = {
            "instance_id": inst_id,
            "gaid": gaid,
            "android_id": dev.get("android_id", ""),
            "app_session_id": dev.get("session_id", ""),
        }

    return tmpl


def extract_json_credentials(data: dict) -> dict:
    """Extracts phone, user_id, xo, ox, instance_id, gaid from any arbitrary Meesho JSON structure."""
    res = {
        "phone": "",
        "user_id": "",
        "xo": "",
        "ox": "",
        "instance_id": "",
        "gaid": "",
        "android_id": "",
        "app_session_id": "",
    }

    def search_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_low = str(k).lower().replace("_", "").replace("-", "")
                if not res["phone"] and k_low in ("mobile", "phone", "phonenumber", "number", "mobileno"):
                    if isinstance(v, (str, int)):
                        cleaned = clean_phone(str(v))
                        if len(cleaned) == 10:
                            res["phone"] = cleaned
                if not res["user_id"] and k_low in ("userid", "uid", "id", "merchantuserid"):
                    if isinstance(v, (str, int)) and str(v).isdigit() and len(str(v)) >= 4:
                        res["user_id"] = str(v)
                if not res["xo"] and k_low in ("xo", "token", "xotoken", "jwt"):
                    if isinstance(v, str) and len(v) > 20:
                        res["xo"] = v
                if not res["ox"] and k_low in ("ox", "refreshtoken", "oxtoken"):
                    if isinstance(v, str) and len(v) > 10:
                        res["ox"] = v
                if not res["instance_id"] and k_low in ("instanceid", "instance"):
                    if isinstance(v, str) and len(v) >= 16:
                        res["instance_id"] = v
                if not res["gaid"] and k_low in ("gaid", "adid", "googleadid"):
                    if isinstance(v, str) and len(v) >= 16:
                        res["gaid"] = v
                if not res["android_id"] and k_low in ("androidid", "aid"):
                    if isinstance(v, str) and len(v) >= 10:
                        res["android_id"] = v
                if not res["app_session_id"] and k_low in ("appsessionid", "sessionid"):
                    if isinstance(v, str) and len(v) >= 16:
                        res["app_session_id"] = v

                if isinstance(v, (dict, list)):
                    search_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                search_keys(item)

    search_keys(data)
    return res


def sync_to_sell_store(account_data: dict, phone: str) -> dict:
    """
    Automatically syncs newly mined Meesho account JSON to TelegramBotSell's stock pool:
    1. Writes to MongoDB collection 'products' (if MONGO_URI is set)
    2. Writes to local 'data/store.json'
    """
    possible_paths = [
        os.getenv("TELEGRAM_SELL_STORE_PATH", ""),
        r"D:\TelegramBotSell\data\store.json",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "TelegramBotSell", "data", "store.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "TelegramBotSell", "data", "store.json")),
        os.path.abspath(os.path.join(os.getcwd(), "..", "TelegramBotSell", "data", "store.json")),
    ]

    store_path = None
    for p in possible_paths:
        if p and os.path.exists(p):
            store_path = p
            break

    # Check MongoDB URI directly or from env
    mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://karankathayat2005_db_user:k4snumCsazWYdemd@telegramsellingbotdb.b5zxeml.mongodb.net/?appName=TelegramSellingBotDb").strip()
    mongo_dbname = os.getenv("MONGO_DB_NAME", "telegram_store").strip()

    json_item_str = json.dumps(account_data, indent=2, ensure_ascii=False) if isinstance(account_data, dict) else str(account_data)
    total_stock = 1

    # 1. MongoDB Direct Sync (if configured)
    if mongo_uri:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)
            db = client[mongo_dbname]
            
            # Find Meesho product
            prod = db.products.find_one({"categoryId": "cat_1788793927977", "type": "stock_pool"})
            if not prod:
                prod = db.products.find_one({"type": "stock_pool", "name": {"$regex": "meesho", "$options": "i"}})

            if prod:
                items = prod.get("stockItems", [])
                if not any(f'"mobile": "{phone}"' in it or f'"{phone}"' in it for it in items):
                    db.products.update_one(
                        {"_id": prod["_id"]},
                        {"$push": {"stockItems": json_item_str}}
                    )
                    total_stock = len(items) + 1
                    print(f"[SellStoreSync] 🍃 MongoDB Synced: Account +91{phone} added to collection 'products'.")
                else:
                    total_stock = len(items)
            else:
                new_prod = {
                    "id": "prod_1788793928009",
                    "categoryId": "cat_1788793927977",
                    "name": "Meesho Fresh Account JSON",
                    "description": "⚡ 100% Fresh Unregistered Meesho Account with Session Tokens & Device ID. Instant automated delivery upon payment.",
                    "price": 99,
                    "type": "stock_pool",
                    "stockItems": [json_item_str],
                    "fileId": None,
                    "fileName": None,
                    "staticContent": None,
                    "isUnlimited": False,
                    "isActive": True,
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                db.products.insert_one(new_prod)
                print(f"[SellStoreSync] 🍃 MongoDB Created product & added Account +91{phone}.")
        except Exception as mongo_err:
            print(f"[SellStoreSync] ⚠️ MongoDB sync warning (falling back to JSON file): {mongo_err}")

    # 2. Local JSON File Sync
    if not store_path:
        return {"ok": True, "stock": total_stock}

    try:
        with open(store_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "categories" not in data or not isinstance(data["categories"], list):
            data["categories"] = []
        if "products" not in data or not isinstance(data["products"], list):
            data["products"] = []

        meesho_cat = None
        for cat in data["categories"]:
            if "meesho" in cat.get("name", "").lower() or cat.get("id") == "cat_1788793927977":
                meesho_cat = cat
                break

        if not meesho_cat:
            meesho_cat = {
                "id": "cat_1788793927977",
                "name": "🛍️ Meesho Fresh JSONs",
                "description": "Freshly mined & verified Meesho Accounts with Token/Session for instant login",
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            data["categories"].append(meesho_cat)

        meesho_prod = None
        for prod in data["products"]:
            if prod.get("categoryId") == meesho_cat["id"] and prod.get("type") == "stock_pool":
                meesho_prod = prod
                break

        if not meesho_prod:
            meesho_prod = {
                "id": "prod_1788793928009",
                "categoryId": meesho_cat["id"],
                "name": "Meesho Fresh Account JSON",
                "description": "⚡ 100% Fresh Unregistered Meesho Account with Session Tokens & Device ID. Instant automated delivery upon payment.",
                "price": 99,
                "type": "stock_pool",
                "stockItems": [],
                "fileId": None,
                "fileName": None,
                "staticContent": None,
                "isUnlimited": False,
                "isActive": True,
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            data["products"].append(meesho_prod)

        if "stockItems" not in meesho_prod or not isinstance(meesho_prod["stockItems"], list):
            meesho_prod["stockItems"] = []

        if not any(f'"mobile": "{phone}"' in item or f'"{phone}"' in item for item in meesho_prod["stockItems"]):
            meesho_prod["stockItems"].append(json_item_str)

            tmp_file = store_path + f".tmp.{os.getpid()}"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, store_path)

            stock_count = len(meesho_prod["stockItems"])
            print(f"[SellStoreSync] ✅ Successfully added Meesho JSON (+91{phone}) to TelegramBotSell stock! (Total Stock: {stock_count})")
            return {"ok": True, "stock": stock_count, "store_path": store_path}
        else:
            stock_count = len(meesho_prod["stockItems"])
            return {"ok": True, "stock": stock_count, "store_path": store_path}

    except Exception as e:
        print(f"[SellStoreSync] ⚠️ Error syncing to TelegramBotSell store: {e}")
        return {"ok": True, "stock": total_stock}


# ─── Keyboards ────────────────────────────────────────────────────────────────
ADMIN_MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🚀 Start Hunt"}, {"text": "📱 Check My Number"}],
        [{"text": "⚙️ Select Servers"}, {"text": "🔑 Set API Key"}],
        [{"text": "📝 Set JSON Format"}, {"text": "🔄 Convert JSON"}],
        [{"text": "⚙️ Store Settings"}, {"text": "📦 View Orders"}],
        [{"text": "📊 Stats"}, {"text": "💰 Balance"}],
        [{"text": "🛑 Stop Hunt"}],
    ],
    "resize_keyboard": True,
}

USER_MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🛍️ Buy Meesho JSON"}],
        [{"text": "📦 My Orders"}, {"text": "💬 Contact Admin"}],
        [{"text": "ℹ️ How It Works"}],
    ],
    "resize_keyboard": True,
}

MAIN_MENU_KEYBOARD = ADMIN_MAIN_MENU_KEYBOARD


# ─── Automated Order Mining & Admin Delivery Task ─────────────────────────────
async def mine_and_deliver_order(client: httpx.AsyncClient, order_id: str):
    order = get_order(order_id)
    if not order:
        print(f"[OrderDelivery] ❌ Order {order_id} not found in DB.")
        return

    buyer_id = str(order.get("user_id"))
    order["status"] = "PROCESSING"
    save_order(order)

    # 1. Initial Live Update to Buyer
    await send_tg_message(
        client,
        buyer_id,
        f"⚡ <b>MEESHO ACCOUNT GENERATION INITIATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
        f"⏳ <b>Status:</b> <code>[▓▓░░░░░░░░] 20% (Searching)</code>\n\n"
        f"🔍 <i>Searching fresh unregistered number on fast servers...</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
    )

    admin_cfg = get_user_config(ADMIN_CHAT_ID)
    api_key = (admin_cfg.get("api_key") or DEFAULT_OTP_DOCTOR_KEY).strip()
    servers = admin_cfg.get("selected_servers", ["5841"])
    if not servers:
        servers = ["5841"]

    delivered_phone = None
    account_json_str = None
    max_attempts = 8

    for attempt in range(1, max_attempts + 1):
        srv = servers[(attempt - 1) % len(servers)]
        print(f"[OrderDelivery] Attempt #{attempt} for Order {order_id} on Server {srv}...")

        res = await otpd_buy(client, api_key, srv)
        if not res.get("ok"):
            print(f"[OrderDelivery] Buy failed on {srv}: {res.get('error')}")
            await asyncio.sleep(4)
            continue

        act_id = res["id"]
        phone = res["phone"]

        chk = await check_meesho_reg(client, phone)
        if not chk.get("ok"):
            await asyncio.sleep(2)
            chk = await check_meesho_reg(client, phone)

        if chk.get("registered") is True or not chk.get("ok"):
            print(f"[OrderDelivery] Phone {phone} is registered or check failed. Cancelling...")
            await otpd_cancel(client, api_key, act_id)
            await asyncio.sleep(4)
            continue

        # 2. Buyer Live Progress: Fresh number found & OTP dispatched
        masked_num = f"{phone[:3]}XXXX{phone[-3:]}"
        await send_tg_message(
            client,
            buyer_id,
            f"📱 <b>FRESH NUMBER ACQUIRED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📞 <b>Allocated Mobile:</b> <code>+91 {masked_num}</code>\n"
            f"⏳ <b>Status:</b> <code>[▓▓▓▓▓░░░░░] 50% (OTP Sent)</code>\n\n"
            f"📩 <i>Sending official Meesho Login OTP via SMS...</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        )

        dev = mk_device()
        otp_res = await send_meesho_otp(client, phone, dev, chat_id=ADMIN_CHAT_ID)
        if not otp_res.get("ok"):
            print(f"[OrderDelivery] OTP send failed: {otp_res.get('error')}. Cancelling...")
            await otpd_cancel(client, api_key, act_id)
            await asyncio.sleep(4)
            continue

        session_dict = otp_res["session"]
        start_wait = time.time()
        otp_code = None

        while (time.time() - start_wait) < 150:
            sms_res = await otpd_get_sms(client, api_key, act_id)
            if sms_res.get("ok"):
                sms_text = sms_res.get("sms", "")
                digits = re.findall(r"\b\d{4,6}\b", sms_text)
                if digits:
                    otp_code = digits[0]
                    # 3. Buyer Live Progress: OTP received & logging in
                    await send_tg_message(
                        client,
                        buyer_id,
                        f"🔑 <b>SMS OTP RECEIVED & VERIFIED!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔐 <b>Verification:</b> <code>OTP 6-Digit Verified ✅</code>\n"
                        f"⏳ <b>Status:</b> <code>[▓▓▓▓▓▓▓▓░░] 85% (Logging in)</code>\n\n"
                        f"⚙️ <i>Generating Meesho session tokens & auth cookies...</i>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
                    )
                    break
            await asyncio.sleep(3)

        if not otp_code:
            print(f"[OrderDelivery] SMS timeout for {phone}. Cancelling...")
            await otpd_cancel(client, api_key, act_id)
            await asyncio.sleep(4)
            continue

        login_res = await verify_meesho_otp(client, phone, otp_code, session_dict, dev)
        if login_res.get("ok"):
            user_id = login_res.get("user_id")
            xo = login_res.get("xo") or ""
            ox = login_res.get("ox") or ""
            tmpl = admin_cfg.get("json_template")
            account_data = format_account_json(tmpl, phone, user_id, xo, ox, dev)

            os.makedirs("accounts", exist_ok=True)
            fname = f"accounts/account_{phone}.json"
            account_json_str = json.dumps(account_data, indent=2, ensure_ascii=False)
            with open(fname, "w", encoding="utf-8") as f:
                f.write(account_json_str)

            delivered_phone = phone
            break
        else:
            print(f"[OrderDelivery] Meesho login failed for {phone}: {login_res.get('error')}")
            await otpd_cancel(client, api_key, act_id)
            await asyncio.sleep(4)

    if delivered_phone and account_json_str:
        order["status"] = "READY_FOR_DELIVERY"
        order["mined_phone"] = delivered_phone
        order["mined_json"] = account_json_str
        order["mined_at"] = time.time()
        save_order(order)

        # 4. Buyer Notification: Account created successfully, waiting for admin delivery
        masked_final = f"{delivered_phone[:3]}XXXX{delivered_phone[-3:]}"
        user_created_msg = (
            f"🎉 <b>MEESHO ACCOUNT CREATED SUCCESSFULLY! ✅</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
            f"📱 <b>Account Mobile:</b> <code>+91 {masked_final}</code>\n"
            f"⏳ <b>Status:</b> <code>[▓▓▓▓▓▓▓▓▓▓] 100% (Complete)</code>\n\n"
            f"🛡️ <b>Admin final quality check kar rahe hain.</b>\n"
            f"📦 Aapka complete JSON file order thodi der mein isi chat mein deliver ho jayega.\n"
            f"⏳ <i>Please wait a few moments!</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await send_tg_message(client, buyer_id, user_created_msg, reply_markup=USER_MAIN_MENU_KEYBOARD)

        # 5. Send Mined Account DIRECTLY TO ADMIN with Delivery Actions
        if ADMIN_CHAT_ID:
            admin_delivery_msg = (
                f"🔔 <b>MEESHO ACCOUNT MINED & READY FOR DELIVERY!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
                f"👤 <b>Buyer:</b> {order.get('first_name', 'User')} (@{order.get('username') or 'N/A'} | ID: <code>{buyer_id}</code>)\n"
                f"📱 <b>Mined Phone:</b> <code>+91{delivered_phone}</code>\n"
                f"💰 <b>Amount:</b> ₹{order.get('amount')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>Mined JSON Data:</b>\n"
                f"<pre><code>{account_json_str[:3000]}</code></pre>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👉 <b>Choose Delivery Action:</b>\n"
                f"• <b>Send This JSON:</b> Yahi mined account buyer ko deliver karein.\n"
                f"• <b>Custom JSON / File:</b> Apni koi dusri JSON file ya text bhejein (/deliver {order_id})."
            )
            admin_delivery_kb = {
                "inline_keyboard": [
                    [
                        {"text": "📤 Send This Mined JSON to Buyer", "callback_data": f"send_mined_{order_id}"},
                    ],
                    [
                        {"text": "📁 Upload Custom File / JSON to Buyer", "callback_data": f"deliver_custom_{order_id}"},
                    ],
                    [
                        {"text": "💬 Message Buyer Directly", "callback_data": f"reply_user_{buyer_id}"},
                    ]
                ]
            }
            await send_tg_message(client, ADMIN_CHAT_ID, admin_delivery_msg, reply_markup=admin_delivery_kb)
            await send_tg_document(
                client,
                ADMIN_CHAT_ID,
                filename=f"order_{order_id}_{delivered_phone}.json",
                content=account_json_str,
                caption=f"📁 Mined Account for Order #{order_id} (+91{delivered_phone})",
            )
    else:
        order["status"] = "FAILED"
        save_order(order)
        await send_tg_message(
            client,
            buyer_id,
            f"⚠️ <b>Order Processing Update</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Order <code>#{order_id}</code> ke liye auto-generation mein thodi deri ho rahi hai. Admin jald hi aapse contact karenge.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=USER_MAIN_MENU_KEYBOARD,
        )
        if ADMIN_CHAT_ID:
            await send_tg_message(
                client,
                ADMIN_CHAT_ID,
                f"⚠️ <b>ORDER AUTO-HUNT FAILED!</b>\n\n"
                f"Order <code>#{order_id}</code> (User: <code>{buyer_id}</code>) hunt nahi ho paya.\n"
                f"Kripya OTP Doctor balance / servers check karein ya <code>/deliver {order_id}</code> se manually custom JSON send karein.",
                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
            )


def build_server_selection_keyboard(selected_servers: list, all_known: dict):
    buttons = []
    row = []
    for sid, sinfo in all_known.items():
        is_sel = sid in selected_servers
        icon = "✅" if is_sel else "⬜"
        label = f"{icon} {sinfo['name']} ({sinfo.get('price', '')})"
        row.append({"text": f"/toggle_{sid}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{"text": "➕ Add Custom Server"}, {"text": "🔙 Back to Menu"}])
    return {"keyboard": buttons, "resize_keyboard": True}


# ─── Dual Server Hunter Task ──────────────────────────────────────────────────
async def run_multi_hunter_task(client: httpx.AsyncClient, chat_id: int | str):
    state = ACTIVE_TASKS.get(chat_id)
    if not state or not state["hunting"]:
        return

    cfg = get_user_config(chat_id)
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        state["hunting"] = False
        await send_tg_message(
            client,
            chat_id,
            "⚠️ <b>OTP Doctor API Key Required!</b>\n\n"
            "Aapne abhi tak apna OTP Doctor API Key set nahi kiya hai.\n"
            "👉 Kripya <b>🔑 Set API Key</b> button dabayein ya <code>/setkey &lt;your_key&gt;</code> bhejein.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    servers = cfg.get("selected_servers", ["5841"])
    if not servers:
        servers = ["5841"]
        update_user_config(chat_id, {"selected_servers": servers})

    # Limit to max 2 servers
    servers = servers[:2]

    bal = await otpd_balance(client, api_key)
    server_names = ", ".join(f"Server {s}" for s in servers)
    await send_tg_message(
        client,
        chat_id,
        f"🎯 <b>Multi-Server Hunting Started!</b>\n\n"
        f"🏷️ <b>Active Servers (Max 2):</b> <code>{server_names}</code>\n"
        f"🔄 <b>Mode:</b> Dual-Server Alternating Buy → Web Check → Auto-Cancel Old → Crowstack OTP Send → Auto SMS → Export JSON!\n"
        f"💰 <b>Wallet Balance:</b> ₹{bal}\n\n"
        f"<i>Current stats ke liye <b>/stats</b> dabayein.\nRokne ke liye <b>/stop</b> dabayein.</i>",
    )

    state["attempts"] = 0
    state["registered_count"] = 0
    state["accounts_created"] = 0
    state["start_time"] = time.time()
    state["last_summary_time"] = time.time()
    server_idx = 0

    while state.get("hunting") and not state.get("stop_flag"):
        # Select server in round-robin fashion
        current_server = servers[server_idx % len(servers)]
        server_idx += 1

        state["attempts"] += 1
        att_num = state["attempts"]
        print(f"[{time.strftime('%H:%M:%S')}] Attempt #{att_num}: Buying number from Server {current_server}...")

        res = await otpd_buy(client, api_key, current_server)

        if not res["ok"]:
            err = res.get("error", "Unknown error")
            print(f"[{time.strftime('%H:%M:%S')}] Server {current_server} Buy error: {err}")

            if "NO_BALANCE" in err:
                await send_tg_message(
                    client,
                    chat_id,
                    f"⚠️ <b>Balance Kam Hai!</b> (Server {current_server})\nCancel refund aane ka wait kar rahe hain (har 2 min mein recheck)...",
                )
                refund_done = False
                for _ in range(5):
                    if state.get("stop_flag"):
                        break
                    await asyncio.sleep(120)
                    new_bal = await otpd_balance(client, api_key)
                    try:
                        if float(new_bal) >= 10.0:
                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>Refund aa gaya!</b> Naya Balance: ₹{new_bal}\nHunting continue kar rahe hain...",
                            )
                            refund_done = True
                            break
                    except ValueError:
                        pass
                if not refund_done:
                    await send_tg_message(
                        client,
                        chat_id,
                        f"❌ <b>Balance insufficient!</b> Current Balance: ₹{await otpd_balance(client, api_key)}\nKripya recharge karein ya /stop karein.",
                    )
                    break
                continue

            if "NO_NUMBERS" in err or "TRY_AGAIN" in err:
                await asyncio.sleep(1.2)
                continue

            await asyncio.sleep(1.5)
            continue

        act_id = res["id"]
        phone = res["phone"]
        state["active_id"] = act_id
        print(f"[{time.strftime('%H:%M:%S')}] Got number: {phone} (ID: {act_id}, Server: {current_server}) — checking registration...")

        chk = await check_meesho_reg(client, phone)
        if not chk["ok"]:
            await asyncio.sleep(1.0)
            chk = await check_meesho_reg(client, phone)

        # 🚨 Both registration checker APIs failed / down!
        if not chk["ok"]:
            err_detail = chk.get("error", "Both checker endpoints down")
            print(f"[{time.strftime('%H:%M:%S')}] 🚨 Web Checker APIs failed: {err_detail}. Alerting user...")
            await otpd_cancel(client, api_key, act_id)
            state["active_id"] = None
            await send_tg_message(
                client,
                chat_id,
                f"🚨 <b>ALERT: Web Registration Checker Down!</b>\n\n"
                f"⚠️ Dono checker APIs (Primary & Fallback) respond nahi kar rahi hain:\n"
                f"<code>Error: {err_detail}</code>\n\n"
                f"🛡️ Aapka balance safe rakhne ke liye number <code>+91{phone}</code> cancel kar diya gaya hai taaki koi loss na ho.\n\n"
                f"Hunting temporarily pause kar di gayi hai. Checker live hone par dobara <b>🚀 Start Hunt</b> karein.",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            state["hunting"] = False
            break

        is_reg = chk.get("registered")

        # ── Registered (Old User) → Silently cancel, wait for refund ──
        if is_reg is True:
            state["registered_count"] += 1
            print(f"[{time.strftime('%H:%M:%S')}] Number {phone} is REGISTERED. Cancelling Server {current_server}...")
            await otpd_cancel(client, api_key, act_id)
            state["active_id"] = None
            await asyncio.sleep(1.0)  # Fast turnaround 1s
            continue

        # ── FRESH / UNREGISTERED NUMBER FOUND! ──
        print(f"[{time.strftime('%H:%M:%S')}] 🎉 FRESH NUMBER FOUND: {phone} (ID: {act_id}, Server: {current_server})")
        await send_tg_message(
            client,
            chat_id,
            f"🎉 <b>FRESH MEESHO NUMBER MILA!</b>\n\n"
            f"📱 <b>Mobile Number:</b> <code>+91{phone}</code>\n"
            f"🏷️ <b>Server:</b> <code>{current_server}</code>\n"
            f"🆔 <b>Activation ID:</b> <code>{act_id}</code>\n\n"
            f"📤 <b>Meesho OTP send kiya ja raha hai...</b>",
        )

        dev = mk_device()
        otp_res = await send_meesho_otp(client, phone, dev, chat_id=chat_id)
        if not otp_res.get("ok"):
            err_str = otp_res.get("error", "Failed")
            await send_tg_message(client, chat_id, f"❌ OTP send failed: <code>{err_str}</code>\nCancelling number for refund...")
            await otpd_cancel(client, api_key, act_id)
            state["active_id"] = None
            await asyncio.sleep(1.5)
            continue

        session_dict = otp_res["session"]
        await send_tg_message(client, chat_id, f"⏳ <b>OTP sent! Server {current_server} par SMS ka wait kar rahe hain (max 3 min)...</b>")

        # ── Step 3: Poll OTP Doctor for incoming SMS ──
        otp_code = None
        sms_text = ""
        start_wait = time.time()

        while (time.time() - start_wait) < 180:
            if state.get("stop_flag"):
                await otpd_cancel(client, api_key, act_id)
                state["active_id"] = None
                return

            sms_res = await otpd_get_sms(client, api_key, act_id)
            if sms_res.get("ok"):
                sms_text = sms_res.get("sms", "")
                digits = re.findall(r"\b\d{4,6}\b", sms_text)
                if digits:
                    otp_code = digits[0]
                    print(f"[{time.strftime('%H:%M:%S')}] 🔑 Extracted OTP: {otp_code}")
                    break
            await asyncio.sleep(3)

        if not otp_code:
            await send_tg_message(
                client,
                chat_id,
                f"⏰ <b>SMS Timeout!</b> OTP nahi aaya.\nNumber <code>{act_id}</code> cancel karke refund le rahe hain...\n⏳ Naye numbers dhoondhna continue rahega!",
            )
            await otpd_cancel(client, api_key, act_id)
            state["active_id"] = None
            await asyncio.sleep(1.5)
            continue

        # ── Step 4: Verify OTP & Login to Meesho ──
        await send_tg_message(
            client,
            chat_id,
            f"📩 <b>SMS Aaya:</b> <code>{sms_text}</code>\n"
            f"🔑 <b>OTP:</b> <code>{otp_code}</code>\n"
            f"🔐 <b>Meesho account login ho raha hai...</b>",
        )

        login_res = await verify_meesho_otp(client, phone, otp_code, session_dict, dev)

        if login_res.get("ok"):
            state["accounts_created"] += 1
            user_id = login_res.get("user_id")

            xo = login_res.get("xo") or ""
            ox = login_res.get("ox") or ""
            cfg = get_user_config(chat_id)
            user_tmpl = cfg.get("json_template")

            account_data = format_account_json(user_tmpl, phone, user_id, xo, ox, dev)

            os.makedirs("accounts", exist_ok=True)
            fname = f"accounts/account_{phone}.json"
            json_str = json.dumps(account_data, indent=2, ensure_ascii=False)
            with open(fname, "w", encoding="utf-8") as f:
                f.write(json_str)

            # 🛒 Auto-Sync to TelegramBotSell Store Stock
            sync_res = sync_to_sell_store(account_data, phone)
            store_tag = f"\n🛒 <b>Auto-Stocked in Sell Bot:</b> ✅ Live (Total Stock: {sync_res.get('stock', 1)})" if sync_res.get("ok") else ""

            account_msg = (
                f"🎉 <b>MEESHO ACCOUNT SUCCESSFULLY CREATED!</b>\n\n"
                f"📱 <b>Mobile:</b> <code>+91{phone}</code>\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
                f"🏷️ <b>Server:</b> <code>{current_server}</code>{store_tag}\n\n"
                f"📋 <b>Account JSON:</b>\n"
                f"<pre><code>{json_str}</code></pre>"
            )
            await send_tg_message(client, chat_id, account_msg)

            await send_tg_document(
                client,
                chat_id,
                filename=f"meesho_{phone}.json",
                content=json_str,
                caption=f"✅ Meesho Account: +91{phone} (Server {current_server})",
            )

            state["active_id"] = None
        else:
            err_msg = login_res.get("error", "Login failed")
            await send_tg_message(client, chat_id, f"❌ Meesho login failed: <code>{err_msg}</code>\nCancelling number...")
            await otpd_cancel(client, api_key, act_id)
            state["active_id"] = None

        await asyncio.sleep(8)

    state["hunting"] = False
    state["active_id"] = None
    final_bal = await otpd_balance(client, api_key)
    total_time_mins = int((time.time() - state.get("start_time", time.time())) // 60)
    await send_tg_message(
        client,
        chat_id,
        f"🏁 <b>Hunting Session Stopped!</b>\n\n"
        f"⏱️ <b>Total Runtime:</b> {total_time_mins} minutes\n"
        f"🔄 <b>Total Attempts:</b> {state.get('attempts', 0)}\n"
        f"❌ <b>Registered (Cancelled):</b> {state.get('registered_count', 0)}\n"
        f"🎉 <b>Accounts Created:</b> {state.get('accounts_created', 0)}\n"
        f"💰 <b>Final Balance:</b> ₹{final_bal}\n\n"
        f"Dobara chalane ke liye <b>🚀 Start Hunt</b> dabayein.",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


# ─── Manual Number Check & Login Handlers ─────────────────────────────────────
async def handle_manual_number_check(client: httpx.AsyncClient, chat_id: int | str, state: dict, phone: str):
    phone = clean_phone(phone)
    if len(phone) != 10 or phone[0] not in "6789":
        await send_tg_message(client, chat_id, "❌ Kripya valid 10-digit Indian mobile number bhejein (jaise: <code>9876543210</code>).")
        return

    await send_tg_message(client, chat_id, f"🔍 Checking <code>+91{phone}</code> on Meesho...")
    chk = await check_meesho_reg(client, phone)
    if not chk["ok"]:
        await asyncio.sleep(1)
        chk = await check_meesho_reg(client, phone)

    if not chk["ok"]:
        err_detail = chk.get("error", "Both checker endpoints unreachable")
        await send_tg_message(
            client,
            chat_id,
            f"🚨 <b>ALERT: Web Registration Checker Down!</b>\n\n"
            f"⚠️ Dono checker APIs kaam nahi kar rahi hain:\n"
            f"<code>Error: {err_detail}</code>\n\n"
            f"Is vajah se number verify nahi ho sakta. Kripya thodi der baad try karein.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    confirm_markup = {
        "keyboard": [
            [{"text": "✅ Yes, Send OTP"}, {"text": "❌ Cancel"}],
        ],
        "resize_keyboard": True,
    }

    if chk.get("registered") is True:
        state["manual_step"] = "confirm_otp"
        state["manual_phone"] = phone
        state["is_registered"] = True
        await send_tg_message(
            client,
            chat_id,
            f"⚠️ <code>+91{phone}</code> <b>REGISTERED (Old User)</b> hai!\n\n"
            f"Is number par Meesho ka account pehle se bana hua hai.\n"
            f"👉 Kya aap <b>phir bhi OTP bhej kar login karna chahte hain</b>?",
            reply_markup=confirm_markup,
        )
    else:
        state["manual_step"] = "confirm_otp"
        state["manual_phone"] = phone
        state["is_registered"] = False
        await send_tg_message(
            client,
            chat_id,
            f"✅ <code>+91{phone}</code> <b>FRESH (Unregistered)</b> hai! 🎉\n\n"
            f"Kya is number ke liye OTP bhejna hai?",
            reply_markup=confirm_markup,
        )


async def handle_manual_send_otp(client: httpx.AsyncClient, chat_id: int | str, state: dict):
    phone = state.get("manual_phone")
    if not phone:
        state["manual_step"] = None
        await send_tg_message(client, chat_id, "⚠️ Koi number select nahi hai. 📱 Check My Number par click karein.", reply_markup=MAIN_MENU_KEYBOARD)
        return

    dev = mk_device()
    await send_tg_message(client, chat_id, f"📤 <b>Meesho OTP send kiya ja raha hai (+91{phone})...</b>")

    otp_res = await send_meesho_otp(client, phone, dev, chat_id=chat_id)
    if not otp_res.get("ok"):
        state["manual_step"] = None
        err_str = otp_res.get("error", "Failed")
        await send_tg_message(client, chat_id, f"❌ OTP send failed: <code>{err_str}</code>", reply_markup=MAIN_MENU_KEYBOARD)
        return

    state["manual_step"] = "awaiting_otp"
    state["manual_session"] = otp_res["session"]
    state["manual_dev"] = dev

    cancel_markup = {
        "keyboard": [
            [{"text": "❌ Cancel"}],
        ],
        "resize_keyboard": True,
    }
    await send_tg_message(
        client,
        chat_id,
        f"📩 <b>OTP Sent to +91{phone}!</b>\n\n"
        f"👉 Aapke phone par 6-digit OTP aaya hoga.\n"
        f"Yahan OTP likhkar bhejein (jaise: <code>123456</code>):",
        reply_markup=cancel_markup,
    )


async def handle_manual_verify_otp(client: httpx.AsyncClient, chat_id: int | str, state: dict, otp_code: str):
    phone = state.get("manual_phone")
    session_dict = state.get("manual_session")
    dev = state.get("manual_dev")

    if not phone or not session_dict or not dev:
        state["manual_step"] = None
        await send_tg_message(client, chat_id, "⚠️ Session expire ho gaya. Kripya dobara try karein.", reply_markup=MAIN_MENU_KEYBOARD)
        return

    await send_tg_message(client, chat_id, f"🔐 <b>Verifying OTP {otp_code} & Logging into Meesho...</b>")
    login_res = await verify_meesho_otp(client, phone, otp_code, session_dict, dev)

    if login_res.get("ok"):
        is_reg = state.get("is_registered", False)
        state["manual_step"] = None
        state["manual_phone"] = None
        user_id = login_res.get("user_id")

        xo = login_res.get("xo") or ""
        ox = login_res.get("ox") or ""
        cfg = get_user_config(chat_id)
        user_tmpl = cfg.get("json_template")

        account_data = format_account_json(user_tmpl, phone, user_id, xo, ox, dev)

        os.makedirs("accounts", exist_ok=True)
        fname = f"accounts/account_{phone}.json"
        json_str = json.dumps(account_data, indent=2, ensure_ascii=False)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(json_str)

        # 🛒 Auto-Sync to TelegramBotSell Store Stock
        sync_res = sync_to_sell_store(account_data, phone)
        store_tag = f"\n🛒 <b>Auto-Stocked in Sell Bot:</b> ✅ Live (Total Stock: {sync_res.get('stock', 1)})" if sync_res.get("ok") else ""

        account_msg = (
            f"🎉 <b>MEESHO ACCOUNT SUCCESSFULLY CREATED!</b>\n\n"
            f"📱 <b>Mobile:</b> <code>+91{phone}</code>\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"🏷️ <b>Type:</b> {'Old User' if is_reg else 'Fresh User'}{store_tag}\n\n"
            f"📋 <b>Account JSON:</b>\n"
            f"<pre><code>{json_str}</code></pre>"
        )
        await send_tg_message(client, chat_id, account_msg, reply_markup=MAIN_MENU_KEYBOARD)

        await send_tg_document(
            client,
            chat_id,
            filename=f"meesho_{phone}.json",
            content=json_str,
            caption=f"✅ Meesho Account: +91{phone}",
        )
    else:
        err_msg = login_res.get("error", "Login failed")
        await send_tg_message(client, chat_id, f"❌ <b>OTP Wrong ya Expired:</b> <code>{err_msg}</code>\n\nDobara OTP daalein ya cancel karne ke liye /cancel bhejein.")


async def convert_and_send_json(client: httpx.AsyncClient, chat_id: int | str, content: str):
    cfg = get_user_config(chat_id)
    user_tmpl = cfg.get("json_template")
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
            target_item = parsed[0]
        elif isinstance(parsed, dict):
            target_item = parsed
        else:
            raise ValueError("JSON must contain an object")

        extracted = extract_json_credentials(target_item)
        phone = extracted["phone"] or "0000000000"
        user_id = extracted["user_id"] or "0"
        xo = extracted["xo"] or ""
        ox = extracted["ox"] or ""

        dev = mk_device()
        if extracted.get("instance_id"):
            dev["instance_id"] = extracted["instance_id"]
        if extracted.get("gaid"):
            dev["gaid"] = extracted["gaid"]
        if extracted.get("android_id"):
            dev["android_id"] = extracted["android_id"]
        if extracted.get("app_session_id"):
            dev["session_id"] = extracted["app_session_id"]

        formatted = format_account_json(user_tmpl, phone, user_id, xo, ox, dev)
        json_str = json.dumps(formatted, indent=2, ensure_ascii=False)

        await send_tg_message(
            client,
            chat_id,
            f"🎉 <b>JSON Successfully Converted & Formatted!</b>\n\n"
            f"📱 <b>Mobile:</b> <code>+91{phone}</code>\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n\n"
            f"📋 <b>New Formatted JSON:</b>\n"
            f"<pre><code>{json_str}</code></pre>",
            reply_markup=MAIN_MENU_KEYBOARD,
        )

        await send_tg_document(
            client,
            chat_id,
            filename=f"converted_{phone}.json",
            content=json_str,
            caption=f"✅ Converted Meesho Account: +91{phone}",
        )
    except Exception as e:
        await send_tg_message(
            client,
            chat_id,
            f"❌ <b>JSON Conversion Failed:</b> <code>{str(e)}</code>\n\nKripya valid Meesho JSON bhejein.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )


# ─── Telegram Bot Polling Loop (Dual-Mode: User Store & Admin Hunter) ─────────
async def bot_loop():
    print("🤖 Multi-Server Meesho Bot Started! (@BotFather verified)")
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
                json={"drop_pending_updates": True},
                timeout=10,
            )
        except Exception:
            pass

        offset = 0

        while True:
            try:
                r = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                    json={
                        "offset": offset,
                        "timeout": 25,
                        "allowed_updates": ["message", "callback_query"],
                    },
                    timeout=35.0,
                )
                data = r.json()
                updates = data.get("result", [])

                for u in updates:
                    offset = u["update_id"] + 1

                    # ══════════════════════════════════════════════════════════
                    # 1. HANDLE CALLBACK QUERIES (Buttons)
                    # ══════════════════════════════════════════════════════════
                    cb = u.get("callback_query")
                    if cb:
                        cb_id = cb.get("id")
                        cb_from = cb.get("from", {})
                        cb_user_id = cb_from.get("id")
                        cb_data = cb.get("data", "")
                        cb_msg = cb.get("message")
                        cb_chat_id = cb_msg["chat"]["id"] if cb_msg else cb_user_id

                        # ── Admin Approve Order Callback ──
                        if cb_data.startswith("approve_ord_"):
                            order_id = cb_data.replace("approve_ord_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue

                            ord_item = get_order(order_id)
                            if not ord_item:
                                await answer_tg_callback(client, cb_id, f"❌ Order {order_id} not found!", show_alert=True)
                                continue

                            if ord_item.get("status") in ("COMPLETED", "PROCESSING"):
                                await answer_tg_callback(client, cb_id, f"⚠️ Order already {ord_item.get('status')}!", show_alert=True)
                                continue

                            await answer_tg_callback(client, cb_id, f"✅ Order {order_id} Approved! Auto-hunt started.")
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🚀 <b>Order Approved!</b> Starting on-demand auto-hunt for Order <code>{order_id}</code>...",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                            asyncio.create_task(mine_and_deliver_order(client, order_id))
                            continue

                        # ── Admin Reject Order Callback ──
                        elif cb_data.startswith("reject_ord_"):
                            order_id = cb_data.replace("reject_ord_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue

                            ord_item = get_order(order_id)
                            if ord_item:
                                ord_item["status"] = "REJECTED"
                                ord_item["rejected_at"] = time.time()
                                save_order(ord_item)
                                buyer_id = ord_item.get("user_id")
                                if buyer_id:
                                    await send_tg_message(
                                        client,
                                        buyer_id,
                                        f"❌ <b>Order Update:</b> Aapka Order <code>{order_id}</code> reject kar diya gaya hai (Payment not verified).\nKripya support se sampark karein.",
                                        reply_markup=USER_MAIN_MENU_KEYBOARD,
                                    )

                            await answer_tg_callback(client, cb_id, f"❌ Order {order_id} Rejected.")
                            await send_tg_message(client, cb_chat_id, f"❌ Order <code>{order_id}</code> mark as REJECTED.")
                            continue

                        # ── Admin Deliver Mined JSON to Buyer Callback ──
                        elif cb_data.startswith("send_mined_"):
                            order_id = cb_data.replace("send_mined_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue

                            ord_item = get_order(order_id)
                            if not ord_item:
                                await answer_tg_callback(client, cb_id, "❌ Order not found!", show_alert=True)
                                continue

                            buyer_id = str(ord_item.get("user_id"))
                            mined_json = ord_item.get("mined_json") or "{}"
                            mined_phone = ord_item.get("mined_phone") or "0000000000"

                            ord_item["status"] = "COMPLETED"
                            ord_item["delivered_phone"] = mined_phone
                            ord_item["delivered_at"] = time.time()
                            save_order(ord_item)

                            buyer_msg = (
                                f"🎉 <b>AAPKA MEESHO JSON ORDER READY HAI!</b>\n\n"
                                f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
                                f"📱 <b>Mobile:</b> <code>+91{mined_phone}</code>\n"
                                f"⚡ <b>Status:</b> 100% Verified & Delivered!\n\n"
                                f"📋 <b>Account JSON:</b>\n"
                                f"<pre><code>{mined_json}</code></pre>\n\n"
                                f"👇 Niche di gayi <code>.json</code> file download karke use karein. Thank you for shopping with us!"
                            )
                            await send_tg_message(client, buyer_id, buyer_msg, reply_markup=USER_MAIN_MENU_KEYBOARD)
                            await send_tg_document(
                                client,
                                buyer_id,
                                filename=f"meesho_{mined_phone}.json",
                                content=mined_json,
                                caption=f"✅ Meesho Account JSON (+91{mined_phone})",
                            )

                            await answer_tg_callback(client, cb_id, f"✅ Order {order_id} delivered to buyer!")
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"✅ Order <code>{order_id}</code> (Mined account +91{mined_phone}) successfully delivered to User <code>{buyer_id}</code>!",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                            continue

                        # ── Admin Deliver Custom File / JSON to Buyer Callback ──
                        elif cb_data.startswith("deliver_custom_"):
                            order_id = cb_data.replace("deliver_custom_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue

                            ord_item = get_order(order_id)
                            if not ord_item:
                                await answer_tg_callback(client, cb_id, "❌ Order not found!", show_alert=True)
                                continue

                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["awaiting_custom_delivery_order"] = order_id
                            await answer_tg_callback(client, cb_id, f"Custom delivery active for #{order_id}")
                            cancel_kb = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"📤 <b>CUSTOM FILE / JSON DELIVERY MODE:</b>\n\n"
                                f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
                                f"👤 <b>Buyer ID:</b> <code>{ord_item.get('user_id')}</code>\n\n"
                                f"👉 Ab aap is user ke liye jo <b>.json file upload karenge</b> ya <b>JSON text message</b> paste karenge, woh seedha buyer ke pass official order delivery ban kar chali jayegi!",
                                reply_markup=cancel_kb,
                            )
                            continue

                        # ── Admin Direct Reply to User Callback ──
                        elif cb_data.startswith("reply_user_"):
                            target_uid = cb_data.replace("reply_user_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue

                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["awaiting_admin_reply_user"] = target_uid
                            await answer_tg_callback(client, cb_id, f"Replying to User {target_uid}")
                            cancel_kb = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"💬 <b>Direct Message to User <code>{target_uid}</code>:</b>\n\n"
                                f"Apna message type karke bhejein. Bot is user ko seedha support message deliver karega.",
                                reply_markup=cancel_kb,
                            )
                            continue

                        # ── Buyer Submit UTR Callback ──
                        elif cb_data.startswith("submit_utr_"):
                            order_id = cb_data.replace("submit_utr_", "").strip()
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["awaiting_utr_order"] = order_id
                            await answer_tg_callback(client, cb_id, "Please enter your 12-digit UTR number.")
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"💳 <b>Order #{order_id} — Submit UTR:</b>\n\n"
                                f"Apne payment receipt ka <b>12-digit UTR / Ref Number</b> yahan type karke bhejein:\n<i>(Jaise: <code>428910293849</code>)</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        # ── Buyer Cancel Order Callback ──
                        elif cb_data.startswith("cancel_ord_"):
                            order_id = cb_data.replace("cancel_ord_", "").strip()
                            ord_item = get_order(order_id)
                            if ord_item and ord_item.get("status") == "AWAITING_PAYMENT":
                                ord_item["status"] = "CANCELLED"
                                save_order(ord_item)
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["awaiting_utr_order"] = None
                            await answer_tg_callback(client, cb_id, "Order cancelled.")
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"❌ Order <code>{order_id}</code> cancel ho gaya.",
                                reply_markup=USER_MAIN_MENU_KEYBOARD,
                            )
                            continue

                        # ── Admin Store Settings Callbacks ──
                        elif cb_data == "set_ref_link":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_referral_link"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            cur_ref = get_referral_link()
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🔗 <b>Meesho Referral Program Link Set Karein:</b>\n\n"
                                f"<b>Current Link:</b>\n<code>{cur_ref}</code>\n\n"
                                f"👉 <i>Apna naya Meesho referral link yahan type/paste karke bhejein:</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        elif cb_data == "set_upi_id":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_upi"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            cur_upi = get_store_upi_id()
                            cur_name = get_store_upi_name()
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"💳 <b>Store UPI Details Set Karein:</b>\n\n"
                                f"• <b>Current UPI ID:</b> <code>{cur_upi}</code>\n"
                                f"• <b>Current Payee Name:</b> {cur_name}\n\n"
                                f"👉 <i>Apna naya UPI ID aur Name bhejein:\nFormat: <code>your-upi@paytm Payee Name</code></i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        elif cb_data == "set_price":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_price"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            cur_p = get_store_price()
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"💰 <b>Meesho JSON Price Set Karein:</b>\n\n"
                                f"• <b>Current Price:</b> ₹{cur_p} / Account\n\n"
                                f"👉 <i>Naya numeric price bhejein (jaise: <code>99</code> ya <code>149</code>):</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        else:
                            await answer_tg_callback(client, cb_id)
                            continue

                    # ══════════════════════════════════════════════════════════
                    # 2. HANDLE TELEGRAM MESSAGES
                    # ══════════════════════════════════════════════════════════
                    msg = u.get("message")
                    if not msg:
                        continue

                    chat_id = msg["chat"]["id"]
                    from_user = msg.get("from", {})
                    first_name = from_user.get("first_name", "User")
                    username = from_user.get("username", "")
                    text = (msg.get("text") or "").strip()

                    state = ACTIVE_TASKS.setdefault(chat_id, {"hunting": False, "active_id": None, "stop_flag": False})
                    cfg = get_user_config(chat_id)
                    all_servers = {**KNOWN_SERVERS, **cfg.get("custom_servers", {})}
                    admin_flag = is_admin(chat_id)
                    store_settings = load_store_settings()
                    current_price = get_store_price()

                    # ── Common: Cancel / Back to Menu ──
                    if text in ("/cancel", "❌ Cancel", "cancel", "🔙 Back to Menu"):
                        state["manual_step"] = None
                        state["manual_phone"] = None
                        state["awaiting_utr_order"] = None
                        state["awaiting_custom_delivery_order"] = None
                        state["awaiting_admin_reply_user"] = None
                        state["in_support"] = None
                        menu_kb = ADMIN_MAIN_MENU_KEYBOARD if admin_flag else USER_MAIN_MENU_KEYBOARD
                        await send_tg_message(client, chat_id, "✅ Main menu par aa gaye.", reply_markup=menu_kb)
                        continue

                    # ══════════════════════════════════════════════════════════
                    # 👑 ADMIN CUSTOM DELIVERY & DIRECT MESSAGING HANDLERS
                    # ══════════════════════════════════════════════════════════
                    if admin_flag:
                        # ── Admin Delivering Custom File / JSON to User ──
                        if state.get("awaiting_custom_delivery_order") or (msg.get("document") and state.get("awaiting_custom_delivery_order")):
                            target_ord_id = state.get("awaiting_custom_delivery_order")
                            ord_item = get_order(target_ord_id)
                            if ord_item:
                                buyer_id = str(ord_item.get("user_id"))
                                doc = msg.get("document")
                                content = text
                                file_bytes = None
                                filename = "meesho_account.json"
                                if doc and doc.get("file_id"):
                                    try:
                                        f_res = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": doc["file_id"]}, timeout=10)
                                        if f_res.status_code == 200:
                                            f_path = f_res.json().get("result", {}).get("file_path")
                                            if f_path:
                                                dl_res = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_path}", timeout=20)
                                                file_bytes = dl_res.content
                                                content = dl_res.text
                                                filename = doc.get("file_name", "meesho_account.json")
                                    except Exception as e:
                                        print(f"[AdminDocDL Error] {e}")

                                ord_item["status"] = "COMPLETED"
                                ord_item["custom_delivered"] = True
                                ord_item["delivered_at"] = time.time()
                                save_order(ord_item)
                                state["awaiting_custom_delivery_order"] = None

                                buyer_msg = (
                                    f"🎉 <b>AAPKA MEESHO JSON ORDER READY HAI!</b>\n\n"
                                    f"🆔 <b>Order ID:</b> <code>{target_ord_id}</code>\n"
                                    f"⚡ <b>Status:</b> 100% Verified & Delivered!\n\n"
                                    f"📋 <b>Account Details:</b>\n"
                                    f"<pre><code>{content[:3000]}</code></pre>\n\n"
                                    f"👇 Niche di gayi <code>.json</code> file download karke use karein. Thank you for shopping with us!"
                                )
                                await send_tg_message(client, buyer_id, buyer_msg, reply_markup=USER_MAIN_MENU_KEYBOARD)
                                if file_bytes:
                                    await send_tg_document(client, buyer_id, filename=filename, content=file_bytes, caption=f"✅ Meesho Account JSON ({filename})")
                                else:
                                    await send_tg_document(client, buyer_id, filename=f"order_{target_ord_id}.json", content=content, caption=f"✅ Meesho Account JSON (Order #{target_ord_id})")

                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"🎉 <b>CUSTOM FILE SUCCESSFULLY DELIVERED!</b>\n\n"
                                    f"🆔 <b>Order ID:</b> <code>{target_ord_id}</code>\n"
                                    f"👤 <b>Buyer ID:</b> <code>{buyer_id}</code>\n"
                                    f"Status: <b>COMPLETED</b>",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                                continue

                        # ── Admin Direct Replying to User Message ──
                        if state.get("awaiting_admin_reply_user"):
                            target_uid = str(state.get("awaiting_admin_reply_user"))
                            state["awaiting_admin_reply_user"] = None
                            user_recv_msg = (
                                f"💬 <b>Support Message from Admin:</b>\n\n"
                                f"{text}"
                            )
                            await send_tg_message(client, target_uid, user_recv_msg, reply_markup=USER_MAIN_MENU_KEYBOARD)
                            await send_tg_message(client, chat_id, f"✅ Message sent to User <code>{target_uid}</code>!", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                            continue

                    # ══════════════════════════════════════════════════════════
                    # 🛍️ BUYER / NORMAL USER INTERFACE (Non-Admin)
                    # ══════════════════════════════════════════════════════════
                    if not admin_flag:
                        # ── Detect UTR Submission ──
                        extracted_utr = None
                        if re.match(r"^\d{10,16}$", text):
                            extracted_utr = text
                        elif state.get("awaiting_utr_order") and re.search(r"\d{10,16}", text):
                            m = re.search(r"\d{10,16}", text)
                            if m:
                                extracted_utr = m.group(0)

                        if extracted_utr:
                            # Match order
                            target_order_id = state.get("awaiting_utr_order")
                            order = None
                            if target_order_id:
                                order = get_order(target_order_id)
                            if not order:
                                user_ords = get_user_orders(chat_id)
                                pending = [o for o in user_ords if o.get("status") == "AWAITING_PAYMENT"]
                                if pending:
                                    order = sorted(pending, key=lambda x: x.get("created_at", 0), reverse=True)[0]

                            if order:
                                order["utr"] = extracted_utr
                                order["status"] = "PENDING_APPROVAL"
                                order["submitted_at"] = time.time()
                                save_order(order)
                                state["awaiting_utr_order"] = None

                                # Confirm to buyer
                                user_confirm = (
                                    f"✅ <b>PAYMENT UTR SUBMITTED!</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🆔 <b>Order ID:</b> <code>#{order['id']}</code>\n"
                                    f"💰 <b>Amount:</b> ₹{order['amount']}\n"
                                    f"🔢 <b>Submitted UTR:</b> <code>{extracted_utr}</code>\n"
                                    f"⏳ <b>Status:</b> <code>Admin Verification Pending</code>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"⚡ <i>Payment verify hote hi aapka fresh account process hona shuru ho jayega!</i>"
                                )
                                await send_tg_message(client, chat_id, user_confirm, reply_markup=USER_MAIN_MENU_KEYBOARD)

                                # Alert Admin
                                if ADMIN_CHAT_ID:
                                    admin_alert = (
                                        f"🚨 <b>NEW MEESHO JSON PAYMENT RECEIVED!</b>\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"🆔 <b>Order ID:</b> <code>#{order['id']}</code>\n"
                                        f"👤 <b>Buyer:</b> {first_name} (@{username} | ID: <code>{chat_id}</code>)\n"
                                        f"💰 <b>Amount:</b> ₹{order['amount']}\n"
                                        f"🔢 <b>UTR / Ref:</b> <code>{extracted_utr}</code>\n"
                                        f"📅 <b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"👇 <b>Select Action:</b>"
                                    )
                                    admin_inline_kb = {
                                        "inline_keyboard": [
                                            [
                                                {"text": "✅ Approve & Start Hunt", "callback_data": f"approve_ord_{order['id']}"},
                                                {"text": "📁 Deliver Custom JSON", "callback_data": f"deliver_custom_{order['id']}"},
                                            ],
                                            [
                                                {"text": "💬 Message Buyer", "callback_data": f"reply_user_{chat_id}"},
                                                {"text": "❌ Reject", "callback_data": f"reject_ord_{order['id']}"},
                                            ]
                                        ]
                                    }
                                    await send_tg_message(client, ADMIN_CHAT_ID, admin_alert, reply_markup=admin_inline_kb)
                                continue

                        # ── Buyer /start or /help ──
                        if text.startswith("/start") or text.startswith("/help"):
                            welcome_text = (
                                f"🛍️ <b>WELCOME TO MEESHO JSON STORE</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"⚡ <b>100% Fresh • Unregistered • High-Speed Delivery</b>\n\n"
                                f"💎 <b>Instant Premium Meesho Accounts:</b>\n"
                                f"• <b>Live Price:</b> <code>₹{current_price} / Account</code>\n"
                                f"• <b>Account Type:</b> 100% Fresh Unregistered OTP Login\n"
                                f"• <b>Format:</b> Clean & Ready-to-use <code>.json</code> File\n"
                                f"• <b>Delivery:</b> Direct File Download in Telegram\n\n"
                                f"👇 <i>Niche diye gaye menu se <b>🛍️ Buy Meesho JSON</b> dabayein!</i>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━"
                            )
                            await send_tg_message(client, chat_id, welcome_text, reply_markup=USER_MAIN_MENU_KEYBOARD)
                            continue

                        # ── Buyer Buy Meesho JSON ──
                        elif text in ("🛍️ Buy Meesho JSON", "/buy", "buy", "Buy"):
                            order_id = f"ORD{int(time.time()) % 1000000:06d}"
                            upi_id = store_settings.get("upi_id", "paytmqr28100505010115i3puxb4eoa@paytm")
                            upi_name = store_settings.get("upi_name", "Meesho Store")

                            new_order = {
                                "id": order_id,
                                "user_id": str(chat_id),
                                "username": username,
                                "first_name": first_name,
                                "amount": current_price,
                                "status": "AWAITING_PAYMENT",
                                "created_at": time.time(),
                                "utr": None,
                            }
                            save_order(new_order)
                            state["awaiting_utr_order"] = order_id

                            qr_bytes = generate_upi_qr_bytes(upi_id, upi_name, current_price, order_id)
                            invoice_caption = (
                                f"🧾 <b>MEESHO JSON OFFICIAL INVOICE</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
                                f"💵 <b>Total Payable:</b> <b>₹{current_price}</b>\n"
                                f"👤 <b>Payee Name:</b> {upi_name}\n"
                                f"📲 <b>UPI ID:</b> <code>{upi_id}</code>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"📌 <b>PAYMENT STEPS:</b>\n"
                                f"1️⃣ Upar diye gaye QR Code ko Paytm / PhonePe / GPay se scan karein.\n"
                                f"2️⃣ <b>₹{current_price}</b> ka exact payment karein.\n"
                                f"3️⃣ Payment ke baad <b>12-digit UTR / Ref Number</b> copy karein.\n"
                                f"4️⃣ Niche <b>Submit UTR</b> button dabakar ya seedhe yahan UTR likhkar bhejein.\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━"
                            )
                            qr_inline_kb = {
                                "inline_keyboard": [
                                    [{"text": "💳 Submit UTR / Ref No", "callback_data": f"submit_utr_{order_id}"}],
                                    [{"text": "❌ Cancel Order", "callback_data": f"cancel_ord_{order_id}"}],
                                ]
                            }
                            await send_tg_photo(client, chat_id, qr_bytes, caption=invoice_caption, reply_markup=qr_inline_kb)
                            continue

                        # ── Buyer My Orders ──
                        elif text in ("📦 My Orders", "/orders", "orders"):
                            u_ords = get_user_orders(chat_id)
                            if not u_ords:
                                await send_tg_message(client, chat_id, "ℹ️ Aapka koi order nahi mila. Naya order place karne ke liye <b>🛍️ Buy Meesho JSON</b> dabayein.", reply_markup=USER_MAIN_MENU_KEYBOARD)
                                continue

                            recent = sorted(u_ords, key=lambda x: x.get("created_at", 0), reverse=True)[:5]
                            lines = [
                                "📦 <b>AAPKE RECENT ORDERS</b>",
                                "━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ]
                            for o in recent:
                                st_icon = "🟢" if o.get("status") == "COMPLETED" else "🟡" if o.get("status") in ("PENDING_APPROVAL", "PROCESSING", "READY_FOR_DELIVERY") else "⚪"
                                lines.append(
                                    f"{st_icon} <b>Order #{o.get('id')}</b>\n"
                                    f"• Amount: ₹{o.get('amount')}\n"
                                    f"• Status: <b>{o.get('status')}</b>\n"
                                    f"• UTR: <code>{o.get('utr') or 'Not submitted'}</code>\n"
                                    f"• Delivered: <code>{o.get('delivered_phone') or ('Ready (Awaiting Admin)' if o.get('status') == 'READY_FOR_DELIVERY' else 'Pending')}</code>\n"
                                    f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈"
                                )
                            await send_tg_message(client, chat_id, "\n".join(lines), reply_markup=USER_MAIN_MENU_KEYBOARD)
                            continue

                        # ── Buyer Contact Admin / Support ──
                        elif text in ("💬 Contact Admin", "/support", "contact"):
                            state["in_support"] = True
                            cancel_kb = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            support_prompt = (
                                f"💬 <b>DIRECT ADMIN SUPPORT</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"Aapka jo bhi sawal, order enquiry ya help chahiye, yahan message likhkar bhejein.\n\n"
                                f"📩 <i>Aapka message seedha admin ko forward ho jayega aur admin isi chat me reply karenge.</i>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━"
                            )
                            await send_tg_message(client, chat_id, support_prompt, reply_markup=cancel_kb)
                            continue

                        # ── Buyer Sending Support Message to Admin ──
                        elif state.get("in_support"):
                            state["in_support"] = None
                            if ADMIN_CHAT_ID:
                                admin_user_msg = (
                                    f"📩 <b>SUPPORT MESSAGE FROM USER:</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 <b>From:</b> {first_name} (@{username} | ID: <code>{chat_id}</code>)\n"
                                    f"💭 <b>Message:</b>\n<i>\"{text}\"</i>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👉 <b>Quick Reply:</b> <code>/msg {chat_id} &lt;reply&gt;</code>"
                                )
                                reply_inline_kb = {
                                    "inline_keyboard": [
                                        [{"text": "💬 Reply to User", "callback_data": f"reply_user_{chat_id}"}]
                                    ]
                                }
                                await send_tg_message(client, ADMIN_CHAT_ID, admin_user_msg, reply_markup=reply_inline_kb)

                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>Message Sent to Admin!</b>\n\nAdmin jald hi aapke message ka reply karenge. Thank you!",
                                reply_markup=USER_MAIN_MENU_KEYBOARD,
                            )
                            continue

                        # ── Buyer How It Works ──
                        elif text in ("ℹ️ How It Works", "/about"):
                            guide_text = (
                                f"ℹ️ <b>MEESHO JSON STORE GUIDE</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"1️⃣ <b>Step 1: Place Order</b>\n"
                                f"   Click <b>🛍️ Buy Meesho JSON</b> to generate your invoice & QR.\n\n"
                                f"2️⃣ <b>Step 2: Pay via UPI</b>\n"
                                f"   Scan QR with Paytm/PhonePe/GPay and pay <b>₹{current_price}</b>.\n\n"
                                f"3️⃣ <b>Step 3: Submit UTR</b>\n"
                                f"   Submit 12-digit UTR receipt number here.\n\n"
                                f"4️⃣ <b>Step 4: Automated Account Generation</b>\n"
                                f"   System fresh unregistered number par account create karta hai.\n\n"
                                f"5️⃣ <b>Step 5: Direct File Delivery</b>\n"
                                f"   Aapko ready-to-use <code>.json</code> file isi chat me mil jayegi!\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━"
                            )
                            await send_tg_message(client, chat_id, guide_text, reply_markup=USER_MAIN_MENU_KEYBOARD)
                            continue

                        else:
                            # Forward unhandled user message as support query to Admin
                            if ADMIN_CHAT_ID:
                                admin_user_msg = (
                                    f"📩 <b>MESSAGE FROM USER:</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 <b>User:</b> {first_name} (@{username} | ID: <code>{chat_id}</code>)\n"
                                    f"💭 <i>\"{text}\"</i>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"Reply ke liye: <code>/msg {chat_id} &lt;message&gt;</code>"
                                )
                                reply_inline_kb = {
                                    "inline_keyboard": [
                                        [{"text": "💬 Reply to User", "callback_data": f"reply_user_{chat_id}"}]
                                    ]
                                }
                                await send_tg_message(client, ADMIN_CHAT_ID, admin_user_msg, reply_markup=reply_inline_kb)

                            await send_tg_message(
                                client,
                                chat_id,
                                f"👋 <b>Welcome to Meesho JSON Store!</b>\n\nNiche diye gaye buttons se option choose karein:",
                                reply_markup=USER_MAIN_MENU_KEYBOARD,
                            )
                            continue

                    # ══════════════════════════════════════════════════════════
                    # 👑 ADMIN HUNTER & STORE MANAGEMENT INTERFACE
                    # ══════════════════════════════════════════════════════════
                    # ── Admin /start or /help ──
                    if text.startswith("/start") or text.startswith("/help"):
                        cur_servers = cfg.get("selected_servers", ["5841"])
                        cur_key = (cfg.get("api_key") or "").strip()
                        masked_key = cur_key[:4] + "..." + cur_key[-4:] if len(cur_key) >= 8 else "❌ Not set (Click 🔑 Set API Key)"
                        has_custom_json = "Custom Template Active" if cfg.get("json_template") else "Default Clean Format"
                        menu_text = (
                            f"👑 <b>Meesho Hunter & Store Master Control</b>\n\n"
                            f"⚙️ <b>Current Hunter Settings:</b>\n"
                            f"• <b>Active Servers (Max 2):</b> <code>{', '.join(cur_servers)}</code>\n"
                            f"• <b>OTP Doctor API Key:</b> <code>{masked_key}</code>\n"
                            f"• <b>JSON Format:</b> <code>{has_custom_json}</code>\n\n"
                            f"🛍️ <b>Store Settings:</b>\n"
                            f"• <b>Meesho JSON Price:</b> ₹{current_price}\n"
                            f"• <b>UPI ID:</b> <code>{get_store_upi_id()}</code>\n"
                            f"• <b>Referral Link:</b> <code>{get_referral_link()[:35]}...</code>\n\n"
                            f"📌 <b>Admin Commands:</b>\n"
                            f"• <b>/setreferral &lt;link&gt;</b> — Referral link update karein\n"
                            f"• <b>/setupi &lt;upi_id&gt; [name]</b> — UPI ID & Name change karein\n"
                            f"• <b>/setprice &lt;amount&gt;</b> — Store price change karein\n"
                            f"• <b>/deliver &lt;order_id&gt;</b> — User ko custom JSON file/text deliver karein\n"
                            f"• <b>/msg &lt;user_id&gt; &lt;text&gt;</b> — User ko direct message/reply bhejein\n"
                            f"• <b>/broadcast &lt;message&gt;</b> — Sabhi buyers ko announcement send karein"
                        )
                        await send_tg_message(client, chat_id, menu_text, reply_markup=ADMIN_MAIN_MENU_KEYBOARD)

                    # ── ⚙️ Store Settings Overview (Admin) ──
                    elif text in ("⚙️ Store Settings", "/settings", "/storesettings"):
                        cur_ref = get_referral_link()
                        cur_p = get_store_price()
                        cur_upi = get_store_upi_id()
                        cur_name = get_store_upi_name()

                        settings_text = (
                            f"⚙️ <b>MEESHO STORE & BOT SETTINGS</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"💰 <b>Meesho JSON Price:</b> <b>₹{cur_p}</b>\n"
                            f"📲 <b>UPI ID:</b> <code>{cur_upi}</code>\n"
                            f"👤 <b>Payee Name:</b> <b>{cur_name}</b>\n"
                            f"🔗 <b>Referral Link:</b>\n<code>{cur_ref}</code>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👇 <i>Niche button dabakar koi bhi setting turant update karein:</i>"
                        )
                        settings_kb = {
                            "inline_keyboard": [
                                [
                                    {"text": "🔗 Change Referral Link", "callback_data": "set_ref_link"},
                                ],
                                [
                                    {"text": "💳 Change UPI ID / Name", "callback_data": "set_upi_id"},
                                    {"text": "💰 Change Price", "callback_data": "set_price"},
                                ]
                            ]
                        }
                        await send_tg_message(client, chat_id, settings_text, reply_markup=settings_kb)

                    # ── 🔗 Set Referral Link (/setreferral <link>) ──
                    elif text.startswith("/setreferral") or text.startswith("/setref") or text == "🔗 Set Referral":
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and (parts[1].strip().startswith("http") or "meesho.com" in parts[1]):
                            nl = parts[1].strip()
                            update_referral_link(nl)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>Meesho Referral Program Link Updated!</b>\n\n🔗 <b>New Link:</b>\n<code>{nl}</code>\n\nAb se sabhi naye accounts iss referral link ke sath register honge.",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            state["manual_step"] = "awaiting_referral_link"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            cur_ref = get_referral_link()
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🔗 <b>Meesho Referral Link Bhejein:</b>\n\n<b>Current:</b> <code>{cur_ref}</code>\n\n<i>(Apna naya Meesho referral program link yahan paste karein)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_referral_link":
                        nl = text.strip()
                        if nl.startswith("http://") or nl.startswith("https://") or "meesho.com" in nl:
                            update_referral_link(nl)
                            state["manual_step"] = None
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Referral Program Link Successfully Saved!</b>\n\n🔗 <code>{nl}</code>",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(client, chat_id, "❌ Kripya valid URL bhejein (jaise: <code>https://app.meesho.com/...</code>).")

                    # ── 📤 Deliver Custom File / JSON (/deliver <order_id>) ──
                    elif text.startswith("/deliver") or text.startswith("/sendjson"):
                        parts = text.split()
                        if len(parts) >= 2:
                            oid = parts[1].strip()
                            ord_item = get_order(oid)
                            if ord_item:
                                state["awaiting_custom_delivery_order"] = oid
                                cancel_kb = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"📤 <b>Order #{oid} Custom Delivery Mode:</b>\n\n"
                                    f"👤 <b>Buyer ID:</b> <code>{ord_item.get('user_id')}</code>\n"
                                    f"👉 Ab aap is user ko jo <b>.json file upload karenge</b> ya <b>JSON text</b> bhejna chahte hain, yahan send karein.",
                                    reply_markup=cancel_kb,
                                )
                            else:
                                await send_tg_message(client, chat_id, f"❌ Order {oid} not found.")
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Usage: <code>/deliver &lt;order_id&gt;</code>")

                    # ── 💬 Direct Message / Reply to User (/msg <user_id> <message>) ──
                    elif text.startswith("/msg") or text.startswith("/reply"):
                        parts = text.split(maxsplit=2)
                        if len(parts) >= 3 and parts[1].isdigit():
                            target_uid = parts[1].strip()
                            msg_content = parts[2].strip()
                            user_recv_msg = (
                                f"💬 <b>Support Message from Admin:</b>\n\n"
                                f"{msg_content}"
                            )
                            res = await send_tg_message(client, target_uid, user_recv_msg, reply_markup=USER_MAIN_MENU_KEYBOARD)
                            if res and res.get("ok"):
                                await send_tg_message(client, chat_id, f"✅ Message sent to User <code>{target_uid}</code>!", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                            else:
                                await send_tg_message(client, chat_id, f"❌ Failed to send message to User <code>{target_uid}</code> (User may have blocked the bot).", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Usage: <code>/msg &lt;user_id&gt; &lt;your message&gt;</code>")

                    # ── 📢 Broadcast Announcement (/broadcast <message>) ──
                    elif text.startswith("/broadcast"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and len(parts[1].strip()) > 0:
                            bcast_text = parts[1].strip()
                            all_ords = load_orders()
                            all_cfgs = load_all_configs()
                            recipients = set()
                            for o in all_ords.values():
                                if o.get("user_id"):
                                    recipients.add(str(o["user_id"]))
                            for cid in all_cfgs.keys():
                                recipients.add(str(cid))

                            if str(ADMIN_CHAT_ID) in recipients:
                                recipients.remove(str(ADMIN_CHAT_ID))

                            if not recipients:
                                await send_tg_message(client, chat_id, "ℹ️ Koi registered users nahi mile broadcast ke liye.", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                                continue

                            await send_tg_message(client, chat_id, f"📢 <b>Broadcasting message to {len(recipients)} users...</b>")
                            sent_count = 0
                            fail_count = 0

                            formatted_bcast = (
                                f"📢 <b>OFFICIAL ANNOUNCEMENT:</b>\n\n"
                                f"{bcast_text}"
                            )

                            for uid in recipients:
                                try:
                                    r_b = await send_tg_message(client, uid, formatted_bcast, reply_markup=USER_MAIN_MENU_KEYBOARD)
                                    if r_b and r_b.get("ok"):
                                        sent_count += 1
                                    else:
                                        fail_count += 1
                                    await asyncio.sleep(0.05)
                                except Exception:
                                    fail_count += 1

                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>Broadcast Complete!</b>\n\n"
                                f"📤 <b>Successfully Sent:</b> {sent_count}\n"
                                f"❌ <b>Failed (Blocked):</b> {fail_count}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Usage: <code>/broadcast &lt;announcement message&gt;</code>")

                    # ── 💰 Set JSON Price (Admin) ──
                    elif text.startswith("/setprice") or text == "💰 Set JSON Price":
                        parts = text.split()
                        if len(parts) == 2 and parts[1].isdigit():
                            np = int(parts[1])
                            update_store_price(np)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>Store Price Updated!</b>\nMeesho JSON ka naya price: <b>₹{np}</b>",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            state["manual_step"] = "awaiting_price"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                f"💰 <b>Meesho JSON ka Naya Price Bhejein:</b>\n<i>(Current: ₹{current_price}, jaise: <code>99</code> ya <code>149</code>)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_price":
                        if text.isdigit():
                            np = int(text)
                            update_store_price(np)
                            state["manual_step"] = None
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Price Successfully Updated to ₹{np}!</b>",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(client, chat_id, "❌ Kripya valid numeric amount bhejein (jaise: <code>99</code>).")

                    # ── 📦 View Orders (Admin) ──
                    elif text in ("📦 View Orders", "/orders", "/allorders"):
                        all_ords = load_orders()
                        if not all_ords:
                            await send_tg_message(client, chat_id, "ℹ️ Koi orders nahi mile.", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                            continue

                        sorted_ords = sorted(all_ords.values(), key=lambda x: x.get("created_at", 0), reverse=True)[:8]
                        lines = ["📦 <b>ALL STORE ORDERS:</b>\n"]
                        for o in sorted_ords:
                            st_icon = "🟢" if o.get("status") == "COMPLETED" else "🟡" if o.get("status") in ("PENDING_APPROVAL", "PROCESSING", "READY_FOR_DELIVERY") else "❌" if o.get("status") == "REJECTED" else "⚪"
                            lines.append(
                                f"{st_icon} <b>Order #{o.get('id')}</b> | User: <code>{o.get('user_id')}</code> (@{o.get('username') or 'N/A'})\n"
                                f"• Amount: ₹{o.get('amount')} | Status: <b>{o.get('status')}</b>\n"
                                f"• UTR: <code>{o.get('utr') or 'N/A'}</code> | Deliver: <code>/deliver {o.get('id')}</code>\n"
                            )
                        await send_tg_message(client, chat_id, "\n".join(lines), reply_markup=ADMIN_MAIN_MENU_KEYBOARD)

                    # ── /setupi <upi_id> [name] (Admin) ──
                    elif text.startswith("/setupi"):
                        parts = text.split(maxsplit=2)
                        if len(parts) >= 2:
                            new_upi = parts[1].strip()
                            new_name = parts[2].strip() if len(parts) == 3 else store_settings.get("upi_name", "Meesho Store")
                            update_store_upi(new_upi, new_name)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>UPI Details Updated!</b>\n📲 <b>UPI ID:</b> <code>{new_upi}</code>\n👤 <b>Name:</b> {new_name}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            state["manual_step"] = "awaiting_upi"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                f"💳 <b>Store UPI Details Bhejein:</b>\n<i>(Format: <code>your-upi@paytm Payee Name</code>)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_upi":
                        parts = text.split(maxsplit=1)
                        new_upi = parts[0].strip()
                        new_name = parts[1].strip() if len(parts) > 1 else None
                        update_store_upi(new_upi, new_name)
                        state["manual_step"] = None
                        st = load_store_settings()
                        await send_tg_message(
                            client,
                            chat_id,
                            f"🎉 <b>UPI Details Successfully Updated!</b>\n📲 <b>UPI ID:</b> <code>{st.get('upi_id')}</code>\n👤 <b>Payee Name:</b> {st.get('upi_name')}",
                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                        )

                    # ── /approve <order_id> (Admin) ──
                    elif text.startswith("/approve"):
                        parts = text.split()
                        if len(parts) == 2:
                            oid = parts[1].strip()
                            ord_item = get_order(oid)
                            if ord_item:
                                await send_tg_message(client, chat_id, f"🚀 <b>Approving Order {oid}...</b> Auto-hunt started.")
                                asyncio.create_task(mine_and_deliver_order(client, oid))
                            else:
                                await send_tg_message(client, chat_id, f"❌ Order {oid} not found.")

                    # ── 🔑 Set API Key ──
                    elif text.startswith("/setkey") or text == "🔑 Set API Key":
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and len(parts[1].strip()) >= 10:
                            new_key = parts[1].strip()
                            test_bal = await otpd_balance(client, new_key)
                            if "ACCESS_BALANCE" in test_bal or test_bal.replace(".", "", 1).isdigit():
                                update_user_config(chat_id, {"api_key": new_key})
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"✅ <b>API Key Successfully Saved!</b>\n💰 <b>Wallet Balance:</b> ₹{test_bal}",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            else:
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"❌ <b>Invalid API Key!</b> OTP Doctor ne reject kiya: <code>{test_bal}</code>\nKripya sahi key bhejein.",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                        else:
                            state["manual_step"] = "awaiting_api_key"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "🔑 <b>Apna OTP Doctor API Key bhejein:</b>\n<i>(OTP Doctor dashboard se copy karke yahan paste karein)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_api_key":
                        candidate_key = text.strip()
                        test_bal = await otpd_balance(client, candidate_key)
                        if "ACCESS_BALANCE" in test_bal or test_bal.replace(".", "", 1).isdigit():
                            update_user_config(chat_id, {"api_key": candidate_key})
                            state["manual_step"] = None
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>API Key Verified & Saved!</b>\n💰 <b>Wallet Balance:</b> ₹{test_bal}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(
                                client,
                                chat_id,
                                f"❌ <b>API Key Invalid!</b> Error: <code>{test_bal}</code>\nDobara sahi key bhejein ya /cancel karein.",
                            )

                    # ── 📝 Set JSON Format Template ──
                    elif text.startswith("/setjson") or text == "📝 Set JSON Format":
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and parts[1].strip().startswith("{") and parts[1].strip().endswith("}"):
                            try:
                                parsed = json.loads(parts[1].strip())
                                if not isinstance(parsed, dict):
                                    raise ValueError("JSON must be a key-value object")
                                update_user_config(chat_id, {"json_template": parsed})
                                preview = json.dumps(parsed, indent=2)[:600]
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"✅ <b>Custom JSON Template Successfully Set!</b>\n\nAb se sabhi naye accounts iss template format mein export honge.\n\n<b>Template Preview:</b>\n<pre><code>{preview}</code></pre>",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            except Exception as e:
                                await send_tg_message(client, chat_id, f"❌ <b>Invalid JSON:</b> <code>{e}</code>\nKripya valid JSON bhejein.")
                        else:
                            state["manual_step"] = "awaiting_json_template"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            cur_tmpl = cfg.get("json_template") or DEFAULT_JSON_TEMPLATE
                            cur_preview = json.dumps(cur_tmpl, indent=2)[:400]
                            await send_tg_message(
                                client,
                                chat_id,
                                f"📝 <b>Custom JSON Template Set Karein:</b>\n\n"
                                f"Aap apna custom JSON format text message mein paste karein ya <code>.json</code> file upload karein.\n\n"
                                f"<b>Active Template Preview:</b>\n<pre><code>{cur_preview}...</code></pre>\n\n"
                                f"<i>Commands:</i>\n"
                                f"• <b>/resetjson</b> — Reset to clean default\n"
                                f"• <b>/viewjson</b> — View full active template",
                                reply_markup=cancel_markup,
                            )

                    elif text == "/resetjson":
                        update_user_config(chat_id, {"json_template": None})
                        await send_tg_message(
                            client,
                            chat_id,
                            "🔄 <b>JSON Template Reset to Default!</b> Ab clean default format use hoga.",
                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                        )

                    elif text == "/viewjson":
                        cur_tmpl = cfg.get("json_template") or DEFAULT_JSON_TEMPLATE
                        cur_str = json.dumps(cur_tmpl, indent=2)
                        await send_tg_message(
                            client,
                            chat_id,
                            f"📋 <b>Active JSON Template:</b>\n<pre><code>{cur_str[:3800]}</code></pre>",
                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                        )

                    elif state.get("manual_step") == "awaiting_json_template":
                        content = text
                        doc = msg.get("document")
                        if doc and doc.get("file_id"):
                            try:
                                f_res = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": doc["file_id"]}, timeout=10)
                                if f_res.status_code == 200:
                                    f_path = f_res.json().get("result", {}).get("file_path")
                                    if f_path:
                                        dl_res = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_path}", timeout=20)
                                        content = dl_res.text
                            except Exception as e:
                                print(f"[Doc Download Error] {e}")

                        try:
                            parsed = json.loads(content)
                            if not isinstance(parsed, dict):
                                raise ValueError("JSON must be a key-value dictionary object")
                            update_user_config(chat_id, {"json_template": parsed})
                            state["manual_step"] = None
                            preview = json.dumps(parsed, indent=2)[:600]
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Custom JSON Template Successfully Saved!</b>\n\nAb se sabhi naye accounts iss format mein export honge.\n\n<b>Preview:</b>\n<pre><code>{preview}</code></pre>",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        except Exception as e:
                            await send_tg_message(
                                client,
                                chat_id,
                                f"❌ <b>Invalid JSON Format:</b> <code>{e}</code>\n\nKripya valid JSON paste karein ya /cancel karein.",
                            )

                    # ── 🔄 Convert Arbitrary / Old JSON ──
                    elif text.startswith("/convertjson") or text.startswith("/convert") or text.startswith("/fixjson") or text == "🔄 Convert JSON":
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and parts[1].strip().startswith("{") and parts[1].strip().endswith("}"):
                            await convert_and_send_json(client, chat_id, parts[1].strip())
                        else:
                            state["manual_step"] = "awaiting_convert_json"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "🔄 <b>JSON Converter / Reformatter:</b>\n\n"
                                "Aap apna kisi bhi dusre ya purane format ka Meesho JSON text message mein paste karein ya <code>.json</code> file upload karein.\n\n"
                                "Bot usme se <code>phone</code>, <code>user_id</code>, <code>xo</code>, <code>ox</code>, <code>identity</code> extract karke aapke active JSON template format mein naya JSON file bana dega!",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_convert_json" or (msg.get("document") and msg["document"].get("file_name", "").endswith(".json")):
                        content = text
                        doc = msg.get("document")
                        if doc and doc.get("file_id"):
                            try:
                                f_res = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": doc["file_id"]}, timeout=10)
                                if f_res.status_code == 200:
                                    f_path = f_res.json().get("result", {}).get("file_path")
                                    if f_path:
                                        dl_res = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_path}", timeout=20)
                                        content = dl_res.text
                            except Exception as e:
                                print(f"[Doc Download Error] {e}")

                        state["manual_step"] = None
                        await convert_and_send_json(client, chat_id, content)

                    # ── ⚙️ Select Servers (Max 2) ──
                    elif text.startswith("/servers") or text == "⚙️ Select Servers":
                        sel = cfg.get("selected_servers", ["5841"])
                        text_msg = (
                            f"⚙️ <b>Server Selection (Max 2 Servers):</b>\n\n"
                            f"Currently Selected: <b>{', '.join(sel) if sel else 'None'}</b>\n\n"
                            f"Kisi bhi server par click karke ON/OFF toggle karein.\n"
                            f"<i>(Note: Ek sath maximum 2 servers active reh sakte hain)</i>"
                        )
                        kb = build_server_selection_keyboard(sel, all_servers)
                        await send_tg_message(client, chat_id, text_msg, reply_markup=kb)

                    # Toggle server callback (e.g. /toggle_5841)
                    elif text.startswith("/toggle_"):
                        sid = text.replace("/toggle_", "").strip()
                        sel = list(cfg.get("selected_servers", ["5841"]))
                        if sid in sel:
                            if len(sel) == 1:
                                await send_tg_message(client, chat_id, "⚠️ Kam se kam 1 server select hona zaroori hai!")
                            else:
                                sel.remove(sid)
                                update_user_config(chat_id, {"selected_servers": sel})
                                await send_tg_message(client, chat_id, f"❌ Server {sid} Deselected. Active: {', '.join(sel)}")
                        else:
                            if len(sel) >= 2:
                                await send_tg_message(client, chat_id, f"⚠️ <b>Max 2 Servers Allowed!</b>\nPehle kisi ek active server ko uncheck karein.")
                            else:
                                sel.append(sid)
                                update_user_config(chat_id, {"selected_servers": sel})
                                await send_tg_message(client, chat_id, f"✅ Server {sid} Selected! Active: {', '.join(sel)}")

                        cfg = get_user_config(chat_id)
                        all_servers = {**KNOWN_SERVERS, **cfg.get("custom_servers", {})}
                        kb = build_server_selection_keyboard(cfg.get("selected_servers", []), all_servers)
                        await send_tg_message(client, chat_id, f"Updated Active Servers: <b>{', '.join(cfg.get('selected_servers', []))}</b>", reply_markup=kb)

                    # ── Add Custom Server ID ──
                    elif text == "➕ Add Custom Server" or text.startswith("/addserver"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1].isdigit():
                            sid = parts[1]
                            custom = cfg.get("custom_servers", {})
                            custom[sid] = {"id": sid, "name": f"Server {sid}", "price": "Custom"}
                            update_user_config(chat_id, {"custom_servers": custom})
                            await send_tg_message(client, chat_id, f"✅ Naya Server {sid} add ho gaya! /servers par jakar select kar sakte hain.")
                        else:
                            state["manual_step"] = "awaiting_custom_server"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(client, chat_id, "➕ <b>Custom Server ID bhejein:</b>\n<i>(Jaise: <code>2795</code> ya <code>5841</code>)</i>", reply_markup=cancel_markup)

                    elif state.get("manual_step") == "awaiting_custom_server":
                        sid = text.strip()
                        if sid.isdigit():
                            custom = cfg.get("custom_servers", {})
                            custom[sid] = {"id": sid, "name": f"Server {sid}", "price": "Custom"}
                            update_user_config(chat_id, {"custom_servers": custom})
                            state["manual_step"] = None
                            await send_tg_message(client, chat_id, f"✅ Server <code>{sid}</code> successfully add ho gaya!", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            await send_tg_message(client, chat_id, "❌ Kripya sirf numeric Server ID bhejein (jaise: <code>5841</code>).")

                    # ── 🚀 Start Hunt ──
                    elif text.startswith("/hunt") or text == "🚀 Start Hunt":
                        if state.get("hunting"):
                            await send_tg_message(client, chat_id, "⚠️ Hunting already chal rahi hai! Live stats ke liye <b>/stats</b> dabayein.")
                        else:
                            sel_servers = cfg.get("selected_servers", ["5841"])
                            if not sel_servers:
                                sel_servers = ["5841"]
                                update_user_config(chat_id, {"selected_servers": sel_servers})
                            state["hunting"] = True
                            state["active_id"] = None
                            state["stop_flag"] = False
                            asyncio.create_task(run_multi_hunter_task(client, chat_id))

                    # ── 📱 Check My Number ──
                    elif text.startswith("/check") or text == "📱 Check My Number":
                        parts = text.split()
                        if len(parts) >= 2 and len(clean_phone(parts[1])) == 10:
                            num = clean_phone(parts[1])
                            await handle_manual_number_check(client, chat_id, state, num)
                        else:
                            state["manual_step"] = "awaiting_number"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "📱 <b>Apna 10-digit mobile number bhejein:</b>\n<i>(Jaise: <code>9876543210</code>)</i>",
                                reply_markup=cancel_markup,
                            )

                    # ── Confirm OTP Dispatch (Yes / No) ──
                    elif state.get("manual_step") == "confirm_otp" and text in ("✅ Yes, Send OTP", "yes", "Yes", "/yes"):
                        await handle_manual_send_otp(client, chat_id, state)

                    # ── Awaiting OTP Code ──
                    elif state.get("manual_step") == "awaiting_otp":
                        digits = re.findall(r"\b\d{4,6}\b", text)
                        if digits:
                            await handle_manual_verify_otp(client, chat_id, state, digits[0])
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Kripya valid 4 ya 6-digit OTP code bhejein. Cancel karne ke liye /cancel bhejein.")

                    # ── Number Input ──
                    elif state.get("manual_step") == "awaiting_number" or (len(clean_phone(text)) == 10 and clean_phone(text)[0] in "6789" and not state.get("hunting")):
                        num = clean_phone(text)
                        await handle_manual_number_check(client, chat_id, state, num)

                    # ── 📊 Stats ──
                    elif text.startswith("/stats") or text == "📊 Stats":
                        api_key = (cfg.get("api_key") or "").strip()
                        b = await otpd_balance(client, api_key) if api_key else "Not set"
                        sel_servers = cfg.get("selected_servers", ["5841"])
                        if state and state.get("hunting"):
                            runtime_mins = int((time.time() - state.get("start_time", time.time())) // 60)
                            stats_text = (
                                f"📊 <b>LIVE DUAL-SERVER HUNTING STATS</b>\n\n"
                                f"⚡ <b>Status:</b> 🟢 Running\n"
                                f"⏱️ <b>Uptime:</b> {runtime_mins} minutes\n"
                                f"🏷️ <b>Active Servers:</b> {', '.join(sel_servers)}\n"
                                f"🔄 <b>Total Attempts:</b> {state.get('attempts', 0)}\n"
                                f"❌ <b>Registered (Cancelled):</b> {state.get('registered_count', 0)}\n"
                                f"🎉 <b>Accounts Created:</b> {state.get('accounts_created', 0)}\n"
                                f"💰 <b>Wallet Balance:</b> ₹{b}"
                            )
                        else:
                            stats_text = (
                                f"📊 <b>BOT STATS</b>\n\n"
                                f"⚡ <b>Status:</b> ⚪ Idle (Not running)\n"
                                f"🏷️ <b>Configured Servers:</b> {', '.join(sel_servers)}\n"
                                f"🔄 <b>Last Session Attempts:</b> {state.get('attempts', 0) if state else 0}\n"
                                f"🎉 <b>Accounts Created:</b> {state.get('accounts_created', 0) if state else 0}\n"
                                f"💰 <b>Wallet Balance:</b> ₹{b}\n\n"
                                f"Start karne ke liye <b>🚀 Start Hunt</b> dabayein."
                            )
                        await send_tg_message(client, chat_id, stats_text)

                    # ── 💰 Balance ──
                    elif text.startswith("/balance") or text == "💰 Balance":
                        api_key = (cfg.get("api_key") or "").strip()
                        if not api_key:
                            await send_tg_message(
                                client,
                                chat_id,
                                "⚠️ <b>API Key Set Nahi Hai!</b>\nKripya pehle <b>🔑 Set API Key</b> button dabayein ya <code>/setkey &lt;your_key&gt;</code> bhejein.",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                            continue
                        b = await otpd_balance(client, api_key)
                        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) >= 8 else api_key
                        await send_tg_message(
                            client,
                            chat_id,
                            f"💰 <b>OTP Doctor Balance:</b> ₹{b}\n🔑 <b>Active Key:</b> <code>{masked_key}</code>",
                        )

                    # ── 🛑 Stop Hunt ──
                    elif text.startswith("/stop") or text == "🛑 Stop Hunt":
                        if state.get("hunting"):
                            state["stop_flag"] = True
                            act_id = state.get("active_id")
                            if act_id:
                                api_key = cfg.get("api_key", DEFAULT_OTP_DOCTOR_KEY)
                                await send_tg_message(client, chat_id, f"🛑 Active number <code>{act_id}</code> cancel ho raha hai...")
                                await otpd_cancel(client, api_key, act_id)
                                state["active_id"] = None
                            await send_tg_message(client, chat_id, "🛑 <b>Hunting Stop kar di gayi hai.</b>")
                        else:
                            await send_tg_message(client, chat_id, "ℹ️ Koi active hunt nahi chal rahi hai.")

            except Exception as e:
                print(f"[Polling Exception] {e}")
                await asyncio.sleep(2)


def main():
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    asyncio.run(bot_loop())


if __name__ == "__main__":
    main()
