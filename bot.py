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
import datetime
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "8519590900:AAHbABvAjuIGHI8GD7hlFk8eeL6ZVF2kab8")
DEFAULT_OTP_DOCTOR_KEY = os.getenv("OTPDOCTOR_API_KEY", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "8282846997").strip()
PORT = int(os.getenv("PORT", "10000"))

OTP_DOCTOR_BASE = "https://www.otpdoctor.in/stubs/handler_api.php"
OTP_DOCTOR_WEB_TOKEN = "6874841e41592b17f19761540921b8b4d200920078bff7d9cc8d843d7c32"

# ─── Crowstack Signup APIs (Primary OTP Send & Verify) ────────────────────────
CROWSTACK_BASE = "https://meesho.crowstack.tech/api/signup"
CROWSTACK_ACCOUNT_BASE = "https://meesho.crowstack.tech/api/account"

CROWSTACK_PROFILES = {
    "new": {
        "id": "new",
        "name": "New Session (Nikit #8912242607 - Edge)",
        "user_id": "8912242607",
        "user_name": "Nikit",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0",
        "sec_ch_ua": '"Chromium";v="154", "Microsoft Edge";v="154", "Not A(Brand";v="99"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "x_tg_init_data": "query_id=AAGvBzYTBAAAAK8HNhMzhhua&user=%7B%22id%22%3A8912242607%2C%22first_name%22%3A%22Nikit%22%2C%22last_name%22%3A%22%22%2C%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FCzB6ff0QnWjL-1jduLteUDGtPQ_2cw5UV_KgdSt69fDwah01TLx2_AIcKiFqxJey.svg%22%7D&auth_date=1792225371&signature=7N1pVOo4ORLfWrSjOstQ9w7PP1232y5QsLLIIoq_GyHgz6pHUtFU09aGRbzyvD0-EFpZnq0Dqqd91mzWmm7wDg&hash=a6e0369cfc2c519da67f296a91175b7b0176fcee1ee0020f5a9b75e7bbbe671c",
    },
    "main": {
        "id": "main",
        "name": "Main Session (Marin #8282846997 - Chrome)",
        "user_id": "8282846997",
        "user_name": "Marin",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "x_tg_init_data": "query_id=AAEVN7JtAwAAABU3sm1QtPuH&user=%7B%22id%22%3A8282846997%2C%22first_name%22%3A%22Marin%22%2C%22last_name%22%3A%22%22%2C%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FCd3jfjEFdjJYBiKIo4WzzZvJU53Lb8Cy84uyXS3KREOS1owG9u4WgR40VQwx0oOR.svg%22%7D&auth_date=1792224917&signature=eRDMjVmN_R9XOOhTlKwewowZSSmMGSPW_ti1xCVmRIDHmOhjX-xBvDBoW1XF9SqUWShBcgYWq8jT9FosBejgAA&hash=0aea774ef60eefe6140ba64514f74d44c10e045924f6e542957b06251e5e2f9f",
    },
    "session3": {
        "id": "session3",
        "name": "Session 3 (MarinKitagwa123 #8691393716)",
        "user_id": "8691393716",
        "user_name": "MarinKitagwa123",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="154", "Not A(Brand";v="99"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "x_tg_init_data": (
            "query_id=AAG0JAwGBAAAALQkDAaIYRD3&user=%7B%22id%22%3A8691393716%2C%22first_name%22%3A%22Don%27t%20AskForName%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22MarinKitagwa123%22%2C%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2Frc-kUBgyN1MQtwHbuKioRqG34P_3qD42UFR_ZHoG7kesBta9Ld6rEWz6JBI8i7GI.svg%22%7D"
            "&auth_date=1792126601&signature=AjSMEJVRu2roa8YIGHjbI62oiQtd9GHaSSV6J0buvBA526Al2K5il95Bzat0Yhf8YS2euHx3tJlna4FsBHTQBg"
            "&hash=74368c5a6457536400e6404378aa34c98e06665d10f032eb3993cab45d6acf6a"
        ),
    },
}

# ─── Speedz Checker (tubesave.in v2.0.0) Multi-Key Pool & Load Balancer ──────
SPEEDZ_BASE_URL = "https://tubesave.in/api/v1"
DEFAULT_SPEEDZ_KEY = os.getenv("SPEEDZ_API_KEY", "AK_CAlD5Tt-jLsQOX_Jq0t70jtQ57yEOmfY").strip()
SPEEDZ_LAST_USED = {}  # {api_key: timestamp}
SPEEDZ_LOCK = asyncio.Lock()
SAVED_SPEEDZ_KEYS_FILE = "saved_speedz_keys.json"


def load_saved_speedz_keys_global() -> list[str]:
    keys = []
    if os.path.exists(SAVED_SPEEDZ_KEYS_FILE):
        try:
            with open(SAVED_SPEEDZ_KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    keys.extend([k.strip() for k in data if isinstance(k, str) and len(k.strip()) >= 15])
        except Exception:
            pass
    return keys


def save_saved_speedz_keys_global(keys: list[str]):
    try:
        with open(SAVED_SPEEDZ_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
    except Exception as e:
        print(f"[SavedSpeedzKeys Save Error] {e}")


def get_speedz_keys_pool(chat_id: int | str = None) -> list[str]:
    """Retrieves all Speedz Checker API keys for load balancing."""
    pool = []
    if chat_id:
        cfg = get_user_config(chat_id)
        u_keys = cfg.get("speedz_keys", [])
        if isinstance(u_keys, list):
            pool.extend([k.strip() for k in u_keys if k and isinstance(k, str) and len(k.strip()) >= 15])

    # Merge persistent global saved speedz keys
    for gk in load_saved_speedz_keys_global():
        if gk not in pool:
            pool.append(gk)

    if DEFAULT_SPEEDZ_KEY and DEFAULT_SPEEDZ_KEY not in pool:
        pool.append(DEFAULT_SPEEDZ_KEY)

    # Filter uniques while preserving order
    seen = set()
    res = []
    for k in pool:
        if k not in seen:
            seen.add(k)
            res.append(k)
    return res


def build_speedz_settings_message_and_markup(chat_id: int | str = None) -> tuple[str, dict]:
    sp_keys = get_speedz_keys_pool(chat_id)
    total_keys = len(sp_keys)
    capacity_min = total_keys * 12
    lines = [
        "⚡ <b>SPEEDZ CHECKER KEYS & LOAD BALANCER</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🔑 <b>Active Keys in Pool:</b> <b>{total_keys} Keys</b>",
        f"🚀 <b>Check Capacity:</b> ~<b>{capacity_min} checks/minute</b> (1 req/5s per key)",
        f"🛡️ <b>Rate Limit Bypass:</b> <code>Active (Round-Robin Auto-Rotation)</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for s_idx, s_k in enumerate(sp_keys, start=1):
        masked_s = s_k[:8] + "..." + s_k[-6:] if len(s_k) > 14 else s_k
        last_u = SPEEDZ_LAST_USED.get(s_k, 0.0)
        time_ago = f"{int(time.time() - last_u)}s ago" if last_u > 0 else "Ready"
        lines.append(f"{s_idx}. <code>{masked_s}</code> (Status: {time_ago})")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("👇 <i>Niche button se ek sath multiple keys add karein ya file export karein:</i>")

    markup = {
        "inline_keyboard": [
            [
                {"text": "➕ Add Speedz Keys (Bulk)", "callback_data": "add_speedz_prompt"},
                {"text": "📥 Export Speedz Keys (.txt)", "callback_data": "export_speedz_keys"},
            ],
            [
                {"text": "🗑️ Clear Custom Keys", "callback_data": "clear_speedz_prompt"},
                {"text": "🔙 Back to Store Settings", "callback_data": "open_settings_menu"},
            ]
        ]
    }
    return "\n".join(lines), markup


async def handle_export_speedz_keys(client: httpx.AsyncClient, target_chat_id: int | str):
    sp_keys = get_speedz_keys_pool(target_chat_id)
    if not sp_keys:
        await send_tg_message(client, target_chat_id, "⚠️ Koi Speedz keys configured nahi hain!")
        return
    txt_content = "\n".join(sp_keys)
    await send_tg_document(
        client,
        target_chat_id,
        filename=f"speedz_keys_backup_{len(sp_keys)}_keys.txt",
        content=txt_content,
        caption=(
            f"⚡ <b>Speedz Checker Keys Backup:</b> <code>{len(sp_keys)}</code> keys exported.\n"
            f"📊 <b>Total Capacity:</b> ~<code>{len(sp_keys) * 12}</code> checks/minute\n"
            f"<i>(Direct backup file saved across server restarts)</i>"
        ),
    )


async def get_next_available_speedz_key(chat_id: int | str = None) -> tuple[str | None, float]:
    """
    Selects the best available Speedz API key with least cooldown or lowest last-used timestamp.
    Returns (api_key, wait_seconds). If wait_seconds <= 0, key is ready immediately.
    """
    async with SPEEDZ_LOCK:
        keys = get_speedz_keys_pool(chat_id)
        if not keys:
            return None, 0.0

        now = time.time()
        # Find any key that passed 5.0s cooldown
        for k in keys:
            last = SPEEDZ_LAST_USED.get(k, 0.0)
            if now - last >= 5.0:
                SPEEDZ_LAST_USED[k] = now
                return k, 0.0

        # If all keys currently in 5s cooldown, pick the one with lowest wait time
        best_k = min(keys, key=lambda x: SPEEDZ_LAST_USED.get(x, 0.0))
        wait_s = max(0.0, 5.0 - (now - SPEEDZ_LAST_USED.get(best_k, 0.0)))
        SPEEDZ_LAST_USED[best_k] = now + wait_s
        return best_k, wait_s


def get_crowstack_profile_key(chat_id: int | str = None) -> str:
    if chat_id:
        cfg = get_user_config(chat_id)
        return cfg.get("crowstack_profile", "new")
    return "new"


def get_crowstack_headers(chat_id: int | str = None) -> dict:
    prof_key = get_crowstack_profile_key(chat_id)
    cfg = get_user_config(chat_id) if chat_id else {}
    prof = CROWSTACK_PROFILES.get(prof_key, CROWSTACK_PROFILES["new"])
    init_data = cfg.get("crowstack_custom_init_data") if (prof_key == "custom" and cfg.get("crowstack_custom_init_data")) else prof["x_tg_init_data"]

    return {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://meesho.crowstack.tech",
        "Pragma": "no-cache",
        "Referer": "https://meesho.crowstack.tech/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Storage-Access": "active",
        "User-Agent": prof["user_agent"],
        "X-Tg-Init-Data": init_data,
        "sec-ch-ua": prof["sec_ch_ua"],
        "sec-ch-ua-mobile": prof["sec_ch_ua_mobile"],
        "sec-ch-ua-platform": prof["sec_ch_ua_platform"],
    }


# Backwards compatibility alias
CROWSTACK_HEADERS = get_crowstack_headers()

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

# ─── Cupponhub APIs (New Primary Signup / Check API) ─────────────────────────
CUPPONHUB_BASE = "https://cupponhub.shop/meesho/api"
CUPPONHUB_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://cupponhub.shop",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://cupponhub.shop/meesho/",
    "sec-ch-ua": '"Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-fetch-storage-access": "active",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "x-tg-init-data": (
        "query_id=AAEVN7JtAwAAABU3sm3gVF_u&user=%7B%22id%22%3A8282846997%2C"
        "%22first_name%22%3A%22Marin%22%2C%22last_name%22%3A%22%22%2C"
        "%22username%22%3A%22MarinKitagwa12%22%2C%22language_code%22%3A%22en%22%2C"
        "%22allows_write_to_pm%22%3Atrue%2C"
        "%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C"
        "%2FCd3jfjEFdjJYBiKIo4WzzZvJU53Lb8Cy84uyXS3KREOS1owG9u4WgR40VQwx0oOR.svg%22%7D"
        "&auth_date=1790004685&signature=1OCyjJ069TjCyH3uzCGGtMD3_Si8ciNELX2DhGRjiNSMCS6_IDf63rhFe6MC3ZPuyEDjQ9TPW7F70nuE1bMADw"
        "&hash=20f2817adf3381cb9d3cac0b825f0941e660e0d9551d354bcead591cd706cb50"
    ),
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
    "meesho_price": int(os.getenv("MEESHO_PRICE", "20")),
    "referral_price": int(os.getenv("REFERRAL_PRICE", "25")),
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
        default_keys = [DEFAULT_OTP_DOCTOR_KEY] if DEFAULT_OTP_DOCTOR_KEY else []
        configs[cid] = {
            "api_key": DEFAULT_OTP_DOCTOR_KEY,
            "api_keys": default_keys,
            "selected_servers": ["5841"],
            "custom_servers": {},
        }
        save_all_configs(configs)
    return configs[cid]


def update_user_config(chat_id: int | str, updates: dict):
    configs = load_all_configs()
    cid = str(chat_id)
    default_keys = [DEFAULT_OTP_DOCTOR_KEY] if DEFAULT_OTP_DOCTOR_KEY else []
    cur = configs.get(cid, {
        "api_key": DEFAULT_OTP_DOCTOR_KEY,
        "api_keys": default_keys,
        "selected_servers": ["5841"],
        "custom_servers": {},
    })
    cur.update(updates)
    configs[cid] = cur
    save_all_configs(configs)


SAVED_KEYS_FILE = "saved_keys.json"


def load_saved_keys_global() -> list[str]:
    keys = []
    if os.path.exists(SAVED_KEYS_FILE):
        try:
            with open(SAVED_KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    keys.extend([k.strip() for k in data if isinstance(k, str) and len(k.strip()) >= 8])
        except Exception:
            pass

    env_keys = os.getenv("OTPDOCTOR_API_KEYS", "")
    if env_keys:
        for k in re.split(r"[\s,\n]+", env_keys):
            clean = k.strip()
            if len(clean) >= 8 and clean not in keys:
                keys.append(clean)

    if DEFAULT_OTP_DOCTOR_KEY and DEFAULT_OTP_DOCTOR_KEY not in keys:
        keys.append(DEFAULT_OTP_DOCTOR_KEY)
    return keys


def save_saved_keys_global(keys: list[str]):
    try:
        with open(SAVED_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
    except Exception as e:
        print(f"[SavedKeys Save Error] {e}")


# ─── Multi-Key Management Helpers ─────────────────────────────────────────────
def get_user_api_keys(chat_id: int | str = None) -> list[str]:
    keys = []
    if chat_id:
        cfg = get_user_config(chat_id)
        user_keys = cfg.get("api_keys")
        if isinstance(user_keys, list) and len(user_keys) > 0:
            keys.extend([k.strip() for k in user_keys if isinstance(k, str) and len(k.strip()) >= 8])
        single = (cfg.get("api_key") or "").strip()
        if single and len(single) >= 8 and single not in keys:
            keys.append(single)

    # Merge with persistent global saved keys
    global_keys = load_saved_keys_global()
    for gk in global_keys:
        if gk not in keys:
            keys.append(gk)

    return keys


def add_user_api_key(chat_id: int | str, new_key: str) -> list[str]:
    keys = list(get_user_api_keys(chat_id))
    cleaned = new_key.strip()
    if cleaned and cleaned not in keys:
        keys.append(cleaned)
    primary = keys[0] if keys else ""
    update_user_config(chat_id, {"api_keys": keys, "api_key": primary})
    save_saved_keys_global(keys)
    return keys


def add_user_api_keys_bulk(chat_id: int | str, new_keys: list[str]) -> list[str]:
    keys = list(get_user_api_keys(chat_id))
    added = []
    for raw in new_keys:
        cleaned = raw.strip()
        if len(cleaned) >= 8 and cleaned not in keys:
            keys.append(cleaned)
            added.append(cleaned)
    primary = keys[0] if keys else ""
    update_user_config(chat_id, {"api_keys": keys, "api_key": primary})
    save_saved_keys_global(keys)
    return added


def remove_user_api_key(chat_id: int | str, target: int | str) -> list[str]:
    keys = list(get_user_api_keys(chat_id))
    if isinstance(target, int):
        if 0 <= target < len(keys):
            keys.pop(target)
    elif isinstance(target, str):
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(keys):
                keys.pop(idx)
        elif target in keys:
            keys.remove(target)
    primary = keys[0] if keys else ""
    update_user_config(chat_id, {"api_keys": keys, "api_key": primary})
    save_saved_keys_global(keys)
    return keys


def clear_user_api_keys(chat_id: int | str):
    update_user_config(chat_id, {"api_keys": [], "api_key": ""})
    save_saved_keys_global([])


# ─── Persistent Created Accounts Summary & History ────────────────────────────
ACCOUNTS_LOCK = asyncio.Lock()
ACCOUNTS_HISTORY_FILE = "accounts_history.json"
ACCOUNTS_SUMMARY_TXT = os.path.join("accounts", "created_accounts_summary.txt")

FAILED_ACCOUNTS_LOCK = asyncio.Lock()
FAILED_ACCOUNTS_FILE = "failed_accounts_history.json"
FAILED_ACCOUNTS_TXT = os.path.join("accounts", "failed_accounts_summary.txt")

TRANSACTIONS_LOCK = asyncio.Lock()
TRANSACTIONS_HISTORY_FILE = "transactions_history.json"
TRANSACTIONS_LOG_TXT = os.path.join("accounts", "transactions_log.txt")


def load_failed_accounts_history() -> list:
    if os.path.exists(FAILED_ACCOUNTS_FILE):
        try:
            with open(FAILED_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_failed_accounts_history(history: list):
    try:
        with open(FAILED_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Failed Accounts History Save Error] {e}")


async def record_failed_account(phone: str, worker_id: int, server: str, key_preview: str, reason: str):
    async with FAILED_ACCOUNTS_LOCK:
        history = load_failed_accounts_history()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": len(history) + 1,
            "phone": phone,
            "worker_id": worker_id,
            "server": str(server),
            "key_preview": key_preview,
            "reason": reason,
            "failed_at": now_str,
            "timestamp": time.time(),
        }
        history.append(entry)
        save_failed_accounts_history(history)


def load_accounts_history() -> list:
    if os.path.exists(ACCOUNTS_HISTORY_FILE):
        try:
            with open(ACCOUNTS_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_accounts_history(history: list):
    try:
        with open(ACCOUNTS_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Accounts History Save Error] {e}")


def load_transactions_history() -> list:
    if os.path.exists(TRANSACTIONS_HISTORY_FILE):
        try:
            with open(TRANSACTIONS_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_transactions_history(history: list):
    try:
        with open(TRANSACTIONS_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Transactions History Save Error] {e}")


def regenerate_transactions_log_txt():
    try:
        os.makedirs("accounts", exist_ok=True)
        history = load_transactions_history()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "==========================================================================================================",
            "                            MEESHO BOT - TRANSACTION & ACTIVITY AUDIT LOG",
            "==========================================================================================================",
            f"Log Generated At : {now_str}",
            f"Total Transactions Logged: {len(history)}",
            "----------------------------------------------------------------------------------------------------------",
            f"{'#':<4} | {'Event / Action':<24} | {'Mobile Number':<14} | {'Worker':<12} | {'Server':<8} | {'Wallet Bal':<12} | {'Timestamp':<20}",
            "----------------------------------------------------------------------------------------------------------",
        ]
        for item in history:
            idx = item.get("id", 1)
            event = item.get("event", "")
            phone = item.get("phone", "N/A")
            worker = f"Worker #{item.get('worker_id', 1)}" if item.get('worker_id') else "System"
            server = str(item.get("server", "-"))
            bal = str(item.get("balance", "-"))
            dt = item.get("created_at", "")
            lines.append(f"{idx:<4} | {event:<24} | +91{phone:<11} | {worker:<12} | {server:<8} | ₹{bal:<11} | {dt:<20}")
        lines.append("==========================================================================================================")
        with open(TRANSACTIONS_LOG_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[Regenerate Transactions Log Error] {e}")


async def record_transaction(event: str, phone: str, worker_id: int, server: str, balance: str, details: str = ""):
    async with TRANSACTIONS_LOCK:
        history = load_transactions_history()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": len(history) + 1,
            "event": event,
            "phone": phone,
            "worker_id": worker_id,
            "server": str(server),
            "balance": str(balance),
            "details": details,
            "created_at": now_str,
            "timestamp": time.time(),
        }
        history.append(entry)
        save_transactions_history(history)
        regenerate_transactions_log_txt()


def regenerate_accounts_summary_txt():
    try:
        os.makedirs("accounts", exist_ok=True)
        history = load_accounts_history()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "================================================================================",
            "                   MEESHO BOT - CREATED ACCOUNTS SUMMARY REPORT",
            "================================================================================",
            f"Report Generated At : {now_str}",
            f"Total Accounts Logged: {len(history)}",
            "--------------------------------------------------------------------------------",
            f"{'#':<4} | {'Mobile Number':<14} | {'User ID':<18} | {'Server':<8} | {'Worker':<12} | {'Date & Time':<20}",
            "--------------------------------------------------------------------------------",
        ]
        for item in history:
            idx = item.get("id", 1)
            phone = item.get("phone", "")
            uid = item.get("user_id", "")
            srv = item.get("server", "")
            w_label = f"Worker #{item.get('worker_id', 1)}"
            dt = item.get("created_at", "")
            lines.append(f"{idx:<4} | +91{phone:<11} | {str(uid):<18} | {str(srv):<8} | {w_label:<12} | {dt:<20}")
        lines.append("================================================================================")
        with open(ACCOUNTS_SUMMARY_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[Regenerate Summary Error] {e}")


def regenerate_all_summary_reports() -> list[str]:
    """Regenerates master summary, transaction log, and per-worker account files."""
    generated_files = []
    regenerate_accounts_summary_txt()
    regenerate_transactions_log_txt()
    if os.path.exists(ACCOUNTS_SUMMARY_TXT):
        generated_files.append(ACCOUNTS_SUMMARY_TXT)
    if os.path.exists(TRANSACTIONS_LOG_TXT):
        generated_files.append(TRANSACTIONS_LOG_TXT)

    try:
        os.makedirs("accounts", exist_ok=True)
        history = load_accounts_history()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        worker_groups = {}
        for item in history:
            w_id = item.get("worker_id", 1)
            worker_groups.setdefault(w_id, []).append(item)

        for w_id, w_items in worker_groups.items():
            w_file = os.path.join("accounts", f"worker_{w_id}_accounts_summary.txt")
            lines = [
                "================================================================================",
                f"             MEESHO BOT - WORKER #{w_id} CREATED ACCOUNTS SUMMARY",
                "================================================================================",
                f"Report Generated At : {now_str}",
                f"Worker Identification: Worker #{w_id}",
                f"Total Accounts Created by this Worker: {len(w_items)}",
                "--------------------------------------------------------------------------------",
                f"{'#':<4} | {'Mobile Number':<14} | {'User ID':<18} | {'Server':<8} | {'Date & Time':<20}",
                "--------------------------------------------------------------------------------",
            ]
            for i, it in enumerate(w_items, start=1):
                phone = it.get("phone", "")
                uid = it.get("user_id", "")
                srv = it.get("server", "")
                dt = it.get("created_at", "")
                lines.append(f"{i:<4} | +91{phone:<11} | {str(uid):<18} | {str(srv):<8} | {dt:<20}")
            lines.append("================================================================================")
            with open(w_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            generated_files.append(w_file)
    except Exception as e:
        print(f"[Per-Worker Summary Error] {e}")

    return generated_files


async def record_created_account(phone: str, user_id: str, server: str, worker_id: int, key_preview: str, file_path: str):
    async with ACCOUNTS_LOCK:
        history = load_accounts_history()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": len(history) + 1,
            "phone": phone,
            "user_id": str(user_id),
            "server": str(server),
            "worker_id": worker_id,
            "key_preview": key_preview,
            "created_at": now_str,
            "timestamp": time.time(),
            "file_path": file_path,
        }
        history.append(entry)
        save_accounts_history(history)
        regenerate_all_summary_reports()


def get_day_wise_breakdown() -> list[tuple[str, int]]:
    """Returns list of (YYYY-MM-DD, count) tuples sorted descending by date."""
    history = load_accounts_history()
    day_counts = {}
    for item in history:
        dt_str = str(item.get("created_at", ""))[:10]
        if dt_str and len(dt_str) == 10:
            day_counts[dt_str] = day_counts.get(dt_str, 0) + 1
    sorted_days = sorted(day_counts.keys(), reverse=True)
    return [(d, day_counts[d]) for d in sorted_days]


def reset_session_stats(chat_id: int | str):
    """Resets in-memory live hunting counters for the specified chat/session."""
    cid = int(chat_id) if str(chat_id).isdigit() else chat_id
    state = ACTIVE_TASKS.get(cid) or ACTIVE_TASKS.get(str(chat_id))
    if state:
        state["attempts"] = 0
        state["accounts_created"] = 0
        state["registered_count"] = 0
        state["failed_creations"] = 0
        state["start_time"] = time.time()
        worker_states = state.get("worker_states", {})
        for w_st in worker_states.values():
            w_st["attempts"] = 0
            w_st["accounts"] = 0
            w_st["registered"] = 0
            w_st["failed"] = 0


async def reset_today_accounts() -> int:
    """Removes created and failed account records for today from persistent history."""
    deleted_count = 0
    async with ACCOUNTS_LOCK:
        history = load_accounts_history()
        today_prefix = time.strftime("%Y-%m-%d")
        remaining = [x for x in history if not str(x.get("created_at", "")).startswith(today_prefix)]
        deleted_count = len(history) - len(remaining)
        for idx, it in enumerate(remaining, start=1):
            it["id"] = idx
        save_accounts_history(remaining)
        regenerate_all_summary_reports()
    async with FAILED_ACCOUNTS_LOCK:
        f_history = load_failed_accounts_history()
        today_prefix = time.strftime("%Y-%m-%d")
        f_remaining = [x for x in f_history if not str(x.get("failed_at", "")).startswith(today_prefix)]
        save_failed_accounts_history(f_remaining)
    return deleted_count


async def reset_all_accounts_history() -> int:
    """Clears all-time created and failed account records and regenerates report files."""
    deleted_count = 0
    async with ACCOUNTS_LOCK:
        history = load_accounts_history()
        deleted_count = len(history)
        save_accounts_history([])
        regenerate_all_summary_reports()
    async with FAILED_ACCOUNTS_LOCK:
        save_failed_accounts_history([])
    return deleted_count


def generate_accounts_summary_text() -> str:
    history = load_accounts_history()
    tx_history = load_transactions_history()
    failed_history = load_failed_accounts_history()
    total = len(history)
    total_failed = len(failed_history)
    today_prefix = time.strftime("%Y-%m-%d")
    today_count = sum(1 for x in history if str(x.get("created_at", "")).startswith(today_prefix))
    today_failed = sum(1 for x in failed_history if str(x.get("failed_at", "")).startswith(today_prefix))

    # Day-wise breakdown
    day_breakdown = get_day_wise_breakdown()
    day_lines = []
    for d, cnt in day_breakdown[:7]:
        label = f"📅 Today ({d})" if d == today_prefix else f"📆 {d}"
        day_lines.append(f"• <b>{label}:</b> <b>{cnt}</b> accounts")
    if not day_lines:
        day_lines.append(f"• <b>📅 Today ({today_prefix}):</b> 0 accounts")
    day_history_str = "\n".join(day_lines)

    server_counts = {}
    worker_counts = {}
    for x in history:
        s = str(x.get("server", "Unknown"))
        server_counts[s] = server_counts.get(s, 0) + 1
        w = f"Worker #{x.get('worker_id', 1)}"
        worker_counts[w] = worker_counts.get(w, 0) + 1

    srv_breakdown = ", ".join(f"Server {s}: {cnt}" for s, cnt in server_counts.items()) if server_counts else "None"
    worker_breakdown = ", ".join(f"{w}: {cnt}" for w, cnt in worker_counts.items()) if worker_counts else "None"

    recent = history[-5:]
    recent_lines = []
    if recent:
        for it in reversed(recent):
            recent_lines.append(
                f"• <code>+91{it.get('phone')}</code> | UID: <code>{it.get('user_id')}</code> | Srv: <code>{it.get('server')}</code> | W#{it.get('worker_id')} (<i>{it.get('created_at', '')[-8:]}</i>)"
            )
    recent_text = "\n".join(recent_lines) if recent_lines else "<i>No accounts created yet.</i>"

    # Recent failed accounts snippet
    recent_failed = failed_history[-4:]
    recent_failed_lines = []
    if recent_failed:
        for f_it in reversed(recent_failed):
            recent_failed_lines.append(
                f"• <code>+91{f_it.get('phone')}</code> | W#{f_it.get('worker_id')} (Key: {f_it.get('key_preview', 'N/A')}) | Reason: <code>{str(f_it.get('reason', ''))[:30]}</code> (<i>{str(f_it.get('failed_at', ''))[-8:]}</i>)"
            )
    recent_failed_text = "\n".join(recent_failed_lines) if recent_failed_lines else "<i>No failed account creation recorded.</i>"

    # Recent transactions snippet
    recent_tx = tx_history[-4:]
    recent_tx_lines = []
    if recent_tx:
        for t in reversed(recent_tx):
            recent_tx_lines.append(
                f"• <code>{t.get('event')}</code> | +91{t.get('phone', 'N/A')} | W#{t.get('worker_id', 1)} | Bal: ₹{t.get('balance')} (<i>{t.get('created_at', '')[-8:]}</i>)"
            )
    recent_tx_text = "\n".join(recent_tx_lines) if recent_tx_lines else "<i>No transactions logged yet.</i>"

    summary_msg = (
        f"📋 <b>MEESHO MASTER SUMMARY & AUDIT REPORT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total Accounts Created:</b> <b>{total}</b>\n"
        f"❌ <b>Total Failed Creations:</b> <b>{total_failed}</b>\n"
        f"📅 <b>Created Today ({today_prefix}):</b> <b>{today_count}</b> (❌ Failed: <b>{today_failed}</b>)\n\n"
        f"🗓️ <b>Day-Wise History:</b>\n{day_history_str}\n\n"
        f"🏷️ <b>Server Breakdown:</b> {srv_breakdown}\n"
        f"⚡ <b>Worker Breakdown:</b> {worker_breakdown}\n\n"
        f"🕒 <b>Latest Created Accounts:</b>\n{recent_text}\n\n"
        f"⚠️ <b>Recent Failed Creations:</b>\n{recent_failed_text}\n\n"
        f"💳 <b>Recent Wallet / Number Activity:</b>\n{recent_tx_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 <i>Niche detailed <b>Master Summary</b>, <b>Per-Worker Summary</b>, aur <b>Transaction Log</b> files attach ki gayi hain.</i>"
    )
    return summary_msg



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
    return int(load_store_settings().get("meesho_price", 20))


def update_store_price(new_price: int):
    st = load_store_settings()
    st["meesho_price"] = int(new_price)
    save_store_settings(st)


def get_store_referral_price() -> int:
    return int(load_store_settings().get("referral_price", 25))


def update_store_referral_price(new_price: int):
    st = load_store_settings()
    st["referral_price"] = int(new_price)
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

    for attempt in range(4):
        try:
            r = await client.post(url, json=payload, timeout=15)
            data = r.json()
            if r.status_code == 429:
                wait_sec = data.get("parameters", {}).get("retry_after", 3)
                print(f"[TG 429 FloodWait] Telegram requested wait of {wait_sec}s. Backing off (attempt #{attempt + 1})...")
                await asyncio.sleep(wait_sec + 0.5)
                continue
            elif r.status_code == 400 and "can't parse entities" in (data.get("description") or "").lower():
                # HTML entity error fallback: send plain text
                plain_payload = dict(payload)
                plain_payload.pop("parse_mode", None)
                r_plain = await client.post(url, json=plain_payload, timeout=15)
                return r_plain.json()
            return data
        except Exception as e:
            if attempt < 3:
                await asyncio.sleep(1.0)
            else:
                print(f"[TG Error] send_tg_message: {e}")
                return None
    return None


async def send_tg_document(client: httpx.AsyncClient, chat_id: int | str, filename: str, content: str | bytes, caption: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    if isinstance(content, str):
        content = content.encode("utf-8")
    files = {"document": (filename, content, "application/json")}
    data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}

    for attempt in range(4):
        try:
            r = await client.post(url, data=data, files=files, timeout=25.0)
            res_data = r.json()
            if r.status_code == 429:
                wait_sec = res_data.get("parameters", {}).get("retry_after", 3)
                print(f"[TG 429 FloodWait Document] Sleeping {wait_sec}s before retrying document delivery...")
                await asyncio.sleep(wait_sec + 0.5)
                continue
            elif r.status_code == 400 and "can't parse entities" in (res_data.get("description") or "").lower():
                plain_data = dict(data)
                plain_data.pop("parse_mode", None)
                r_plain = await client.post(url, data=plain_data, files=files, timeout=25.0)
                return r_plain.json()
            return res_data
        except Exception as e:
            if attempt < 3:
                await asyncio.sleep(1.0)
            else:
                print(f"[TG Error] send_tg_document: {e}")
                return None
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
BALANCE_CACHE = {}  # {api_key: {"balance": str, "time": float}}


async def otpd_balance(client: httpx.AsyncClient, api_key: str, force_refresh: bool = False) -> str:
    now = time.time()
    cached = BALANCE_CACHE.get(api_key)
    # Return cached balance if fetched within last 8 seconds to avoid OTP Doctor IP rate limits
    if not force_refresh and cached and (now - cached.get("time", 0)) < 8.0:
        return cached["balance"]

    for attempt in range(2):
        try:
            r = await client.get(OTP_DOCTOR_BASE, params={"action": "getBalance", "api_key": api_key}, timeout=10)
            t = r.text.strip()
            if t.startswith("ACCESS_BALANCE:"):
                val = t.split(":")[1]
                BALANCE_CACHE[api_key] = {"balance": val, "time": time.time()}
                return val
            elif "RATE_LIMIT" in t or "TOO_MANY_REQUESTS" in t:
                if cached and cached.get("balance"):
                    return cached["balance"]
                await asyncio.sleep(0.8)
                continue
            elif t.replace(".", "", 1).isdigit():
                BALANCE_CACHE[api_key] = {"balance": t, "time": time.time()}
                return t
            return t
        except Exception as e:
            if cached and cached.get("balance"):
                return cached["balance"]
            return f"Error ({e})"

    if cached and cached.get("balance"):
        return cached["balance"]
    return "0.00"


def parse_balance_float(val: any) -> float:
    try:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).replace("ACCESS_BALANCE:", "").strip()
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if m:
            return float(m.group(0))
        return 0.0
    except Exception:
        return 0.0


async def fetch_all_key_balances(client: httpx.AsyncClient, keys: list[str], max_concurrency: int = 25) -> dict[str, str]:
    """Fetches balances for hundreds of keys concurrently using Semaphore without rate-limit delay."""
    sem = asyncio.Semaphore(max_concurrency)

    async def _fetch(k):
        async with sem:
            bal = await otpd_balance(client, k)
            return k, bal

    results = await asyncio.gather(*[_fetch(k) for k in keys], return_exceptions=True)
    res_map = {}
    for item in results:
        if isinstance(item, tuple) and len(item) == 2:
            res_map[item[0]] = str(item[1])
    return res_map


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


async def otpd_cancel_attempt(client: httpx.AsyncClient, api_key: str, act_id: str) -> tuple[bool, str]:
    # 1. Try standard Handler API
    try:
        r = await client.get(
            OTP_DOCTOR_BASE,
            params={"action": "setStatus", "api_key": api_key, "id": act_id, "status": "8"},
            timeout=10,
        )
        t = r.text.strip()
        if "ACCESS_CANCEL" in t or "CANCEL" in t:
            return True, f"Handler: {t}"
    except Exception as e:
        pass

    # 2. Try Web Cancel API
    try:
        r2 = await client.get(
            "https://www.otpdoctor.in/api/service/cancelNumberq.php",
            params={"token": OTP_DOCTOR_WEB_TOKEN, "id": act_id},
            headers={"user-agent": CHECKER_HEADERS_1["user-agent"]},
            timeout=10,
        )
        data = r2.json()
        st_code = data.get("status")
        msg = data.get("message", "")
        if st_code == 200 or "refunded" in msg.lower() or "cancelled" in msg.lower():
            return True, f"Web API: {msg} (Bal: {data.get('new_balance', '')})"
        return False, f"Status {st_code}: {msg}"
    except Exception as e:
        return False, str(e)


async def schedule_delayed_cancel(
    client: httpx.AsyncClient,
    api_key: str,
    act_id: str,
    phone: str = "",
    initial_delay: int = 180,
    state: dict = None,
    w_state: dict = None,
):
    """
    Automatic Cancel & Refund Manager:
    1. Waits initial_delay (default 3 minutes / 180s) so server lock window expires.
    2. Sends cancel request to OTP Doctor.
    3. If not cancelled yet (e.g. status 600 / timer active), retries every 1 minute (60s)
       until successfully cancelled & refunded.
    4. Automatically updates pending_cancels count in real-time.
    """
    if state is not None:
        state["pending_cancels"] = state.get("pending_cancels", 0) + 1
    if w_state is not None:
        w_state["pending_cancels"] = w_state.get("pending_cancels", 0) + 1
    try:
        if initial_delay > 0:
            print(f"[{time.strftime('%H:%M:%S')}] [AutoCancel] ⏳ Number +91{phone} (ID: {act_id}) queued for cancellation in {initial_delay}s (3 min)...")
            await asyncio.sleep(initial_delay)

        attempt = 0
        while True:
            attempt += 1
            print(f"[{time.strftime('%H:%M:%S')}] [AutoCancel] 🔄 Cancel Attempt #{attempt} for +91{phone} (ID: {act_id})...")
            success, res_info = await otpd_cancel_attempt(client, api_key, act_id)
            if success:
                print(f"[{time.strftime('%H:%M:%S')}] [AutoCancel] ✅ Number +91{phone} (ID: {act_id}) successfully cancelled & refunded! ({res_info})")
                try:
                    cur_bal = await otpd_balance(client, api_key)
                    await record_transaction("REFUND_CONFIRMED", phone, 0, "-", cur_bal, res_info)
                except Exception:
                    pass
                break

            print(f"[{time.strftime('%H:%M:%S')}] [AutoCancel] ⚠️ Cancel rejected for +91{phone} (ID: {act_id}): {res_info}. Retrying in 60s (1 min)...")
            await asyncio.sleep(60)

    except asyncio.CancelledError:
        await otpd_cancel_attempt(client, api_key, act_id)
    except Exception as e:
        print(f"[AutoCancel Error] +91{phone} (ID: {act_id}): {e}")
    finally:
        if state is not None:
            state["pending_cancels"] = max(0, state.get("pending_cancels", 1) - 1)
        if w_state is not None:
            w_state["pending_cancels"] = max(0, w_state.get("pending_cancels", 1) - 1)


async def otpd_cancel(
    client: httpx.AsyncClient,
    api_key: str,
    act_id: str,
    phone: str = "",
    initial_delay: int = 180,
    state: dict = None,
    w_state: dict = None,
) -> bool:
    asyncio.create_task(
        schedule_delayed_cancel(
            client,
            api_key,
            act_id,
            phone=phone,
            initial_delay=initial_delay,
            state=state,
            w_state=w_state,
        )
    )
    return True


async def otpd_buy_multi_server_race(client: httpx.AsyncClient, api_key: str, servers: list[str]) -> dict:
    """Races multiple servers concurrently in parallel. The fastest server to return a number wins!
    Any trailing numbers received from other servers in the same race are immediately cancelled/refunded."""
    if not servers:
        return {"ok": False, "error": "No servers configured"}
    if len(servers) == 1:
        return await otpd_buy(client, api_key, servers[0])

    tasks = [asyncio.create_task(otpd_buy(client, api_key, str(s))) for s in servers]
    winner = None
    extra_bought = []
    errors = []

    for fut in asyncio.as_completed(tasks):
        try:
            res = await fut
            if res.get("ok"):
                if winner is None:
                    winner = res
                else:
                    extra_bought.append(res)
            else:
                errors.append(res.get("error", "Unknown error"))
        except Exception as e:
            errors.append(str(e))

    # Cancel any extra numbers bought in the race right away with 0s delay for instant refund
    if extra_bought:
        for extra in extra_bought:
            extra_id = extra.get("id")
            extra_phone = extra.get("phone", "")
            if extra_id:
                asyncio.create_task(otpd_cancel(client, api_key, extra_id, phone=extra_phone, initial_delay=0))

    if winner:
        return winner

    combined_err = " | ".join(set(errors)) if errors else "NO_NUMBERS"
    return {"ok": False, "error": combined_err, "server_id": servers[0] if servers else "unknown"}


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


# ─── Cupponhub Core API Functions ─────────────────────────────────────────────
async def cupponhub_check_phone(client: httpx.AsyncClient, phone: str) -> dict:
    """Checks registration on Meesho via Cupponhub phone/check endpoint."""
    try:
        resp = await client.post(
            f"{CUPPONHUB_BASE}/phone/check",
            headers=CUPPONHUB_HEADERS,
            json={"mobile": phone},
            timeout=10,
        )
        if resp.status_code == 200:
            d = resp.json() or {}
            st = str(d.get("status", "")).lower()
            if st == "old":
                return {"ok": True, "registered": True, "fresh": False, "source": "cupponhub", "message": d.get("message", "")}
            elif st in ("new", "fresh", "unregistered", "ok") or (st and st != "old"):
                return {"ok": True, "registered": False, "fresh": True, "source": "cupponhub"}
    except Exception as e:
        print(f"[Cupponhub Phone Check Error] {e}")
    return {"ok": False, "registered": None, "fresh": None, "error": "Cupponhub check failed"}


async def cupponhub_send_otp(client: httpx.AsyncClient, phone: str, tier: int = 200, chat_id: int | str = None) -> dict:
    """Dispatches Meesho OTP via Cupponhub login/check API with configurable discount tier."""
    try:
        payload = {"mobile": str(phone), "tier": int(tier)}
        resp = await client.post(
            f"{CUPPONHUB_BASE}/login/check",
            headers=CUPPONHUB_HEADERS,
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json() or {}
            status = data.get("status", "")
            if status == "otp_sent":
                sess_id = data.get("session_id") or f"8282846997_{phone}"
                return {
                    "ok": True,
                    "method": "cupponhub",
                    "session_id": sess_id,
                    "bucket": data.get("bucket", tier),
                    "tier": tier,
                    "session": {
                        "method": "cupponhub",
                        "phone": phone,
                        "session_id": sess_id,
                        "tier": tier,
                        "chat_id": chat_id,
                    },
                }
            else:
                err_msg = data.get("message") or data.get("error") or str(data)
                return {"ok": False, "error": f"Cupponhub: {err_msg}"}
        else:
            return {"ok": False, "error": f"Cupponhub HTTP {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "error": f"Cupponhub exception: {e}"}


async def cupponhub_verify_otp(client: httpx.AsyncClient, session_id: str, otp: str, phone: str = "") -> dict:
    """Verifies Meesho OTP via Cupponhub login/verify API."""
    try:
        payload = {"session_id": str(session_id), "otp": str(otp)}
        resp = await client.post(
            f"{CUPPONHUB_BASE}/login/verify",
            headers=CUPPONHUB_HEADERS,
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json() or {}
            if data.get("status") == "success":
                uid = data.get("user_id") or data.get("account_id")
                return {
                    "ok": True,
                    "user_id": str(uid),
                    "phone": str(data.get("mobile") or phone),
                    "account": data,
                    "bucket": data.get("bucket", 0),
                    "is_new": data.get("new", True),
                }
            else:
                err = data.get("message") or data.get("error") or str(data)
                return {"ok": False, "error": f"Cupponhub verify: {err}"}
        else:
            return {"ok": False, "error": f"Cupponhub verify HTTP {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "error": f"Cupponhub verify exception: {e}"}


# ─── Web Registration Checker (Speedz Checker Multi-Key + Crowstack Fallback) ──
async def check_meesho_reg(client: httpx.AsyncClient, phone: str, chat_id: int | str = None) -> dict:
    clean_num = clean_phone(phone)

    # 1. Primary Engine: Speedz Checker API with Multi-Key Round-Robin & Rate Limit Bypass
    try:
        sp_key, wait_time = await get_next_available_speedz_key(chat_id)
        if sp_key:
            if wait_time > 0 and wait_time <= 2.5:
                await asyncio.sleep(wait_time)
            
            headers = {"X-API-Key": sp_key, "Content-Type": "application/json"}
            sp_res = await client.post(
                f"{SPEEDZ_BASE_URL}/check",
                headers=headers,
                json={"service": "meesho", "number": clean_num},
                timeout=9,
            )
            if sp_res.status_code == 200:
                data = sp_res.json() or {}
                if data.get("success") and "is_registered" in data:
                    is_reg = bool(data["is_registered"])
                    return {
                        "registered": is_reg,
                        "fresh": not is_reg,
                        "ok": True,
                        "error": None,
                        "source": f"speedz ({sp_key[:8]}...)",
                    }
            elif sp_res.status_code == 429:
                print(f"[Speedz Rate Limit Hit on key {sp_key[:8]}...]")
    except Exception as e:
        print(f"[Speedz Checker Exception]: {e}")

    # 2. Secondary Engine: Crowstack Registration Status Check (Active & Ultra-Accurate)
    try:
        for prof_k in ("new", "main", "session3"):
            p_inf = CROWSTACK_PROFILES.get(prof_k)
            if not p_inf:
                continue
            cs_headers = {
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Origin": "https://meesho.crowstack.tech",
                "Referer": "https://meesho.crowstack.tech/",
                "User-Agent": p_inf["user_agent"],
                "X-Tg-Init-Data": p_inf["x_tg_init_data"],
            }
            cs_payload = {
                "phone": clean_num,
                "ref_link": REFERRAL_LINK,
                "force": True
            }
            r_cs = await client.post(
                f"{CROWSTACK_BASE}/send-otp",
                headers=cs_headers,
                json=cs_payload,
                timeout=10,
            )
            if r_cs.status_code == 200:
                d_cs = r_cs.json() or {}
                if d_cs.get("ok") and "registered" in d_cs:
                    is_reg = bool(d_cs["registered"])
                    return {
                        "registered": is_reg,
                        "fresh": not is_reg,
                        "ok": True,
                        "error": None,
                        "source": f"crowstack ({prof_k})",
                    }
    except Exception as e:
        print(f"[Crowstack Checker Exception]: {e}")

    # ── Legacy Checkers (Preserved & Commented as requested) ──
    # # 1. Cupponhub phone check endpoint
    # try:
    #     cup_chk = await cupponhub_check_phone(client, phone)
    #     if cup_chk.get("ok"):
    #         return {
    #             "registered": cup_chk.get("registered", False),
    #             "fresh": cup_chk.get("fresh", False),
    #             "ok": True,
    #             "error": None,
    #             "source": "cupponhub",
    #         }
    # except Exception as e:
    #     print(f"[Checker Cupponhub Exception]: {e}")
    #
    # # 2. Standard Web Checker APIs (PriceTrackerPro / ProMeesho)
    # payload = {"number": phone}
    # for url, hdr in [(CHECKER_PRIMARY, CHECKER_HEADERS_1), (CHECKER_FALLBACK, CHECKER_HEADERS_2)]:
    #     try:
    #         r = await client.post(url, json=payload, headers=hdr, timeout=10)
    #         if r.status_code == 200:
    #             d = r.json()
    #             if d.get("ok") and d.get("results"):
    #                 res = d["results"][0]
    #                 return {"registered": res.get("registered", False), "fresh": res.get("fresh", False), "ok": True, "error": None}
    #     except Exception:
    #         continue
    #
    # # 3. Hidenfree check-phone API
    # try:
    #     r_hf = await client.post(f"{HIDENFREE_BASE}/login/check-phone", headers=HIDENFREE_HEADERS, json={"phone": phone}, timeout=10)
    #     if r_hf.status_code == 200:
    #         d_hf = r_hf.json()
    #         if d_hf.get("ok"):
    #             is_reg = bool(d_hf.get("registered", False))
    #             return {"registered": is_reg, "fresh": not is_reg, "ok": True, "error": None}
    # except Exception:
    #     pass

    return {"registered": None, "fresh": None, "ok": False, "error": "All checkers (Speedz & Crowstack) failed"}


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


async def crowstack_export_file(client: httpx.AsyncClient, chat_id: int | str = None) -> dict:
    """Calls Crowstack export_file API to fetch full account and session export."""
    try:
        headers = get_crowstack_headers(chat_id)
        resp = await client.post(
            f"{CROWSTACK_ACCOUNT_BASE}/export_file",
            headers=headers,
            json={},
            timeout=15,
        )
        if resp.status_code == 200:
            try:
                data = resp.json() or {}
                return {"ok": True, "data": data}
            except Exception:
                return {"ok": True, "text": resp.text}
        return {"ok": False, "status": resp.status_code, "text": resp.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


PENDING_OTP_FALLBACK_DECISIONS = {}  # {phone: asyncio.Future()}


async def request_otp_fallback_decision(client: httpx.AsyncClient, chat_id: int | str, phone: str, worker_id: int = 1, server: str = "") -> str:
    """
    Asks user via Telegram when both Crowstack Rem & Marin fail.
    Waits 25 seconds for inline response. If timeout or rejected, returns 'cancel' to auto-cancel number for refund.
    """
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    PENDING_OTP_FALLBACK_DECISIONS[phone] = fut

    w_tag = f"Worker #{worker_id}" if worker_id else "Worker"
    s_tag = f"Server {server}" if server else "Server"
    msg_text = (
        f"⚠️ <b>CROWSTACK SESSIONS FAILOVER!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Mobile:</b> <code>+91{phone}</code> ({w_tag} | {s_tag})\n"
        f"❌ <b>Rem (#8912242607) & Marin (#8282846997) Dono Fail Ho Gaye!</b>\n\n"
        f"👉 <b>Kya action lena hai?</b>\n"
        f"• <b>GemixAI:</b> ₹200 OFF reroll karke OTP send karein.\n"
        f"• <b>Cancel Number:</b> Number refund ke liye turant cancel karein.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <i>Agar 25 sec mein response nahi aaya to number auto-cancel ho jayega.</i>"
    )
    kb = {
        "inline_keyboard": [
            [
                {"text": "🟢 Use GemixAI (₹200 OFF)", "callback_data": f"fb_gemix_{phone}"},
                {"text": "❌ Cancel Number (Refund)", "callback_data": f"fb_cancel_{phone}"},
            ]
        ]
    }
    await send_tg_message(client, chat_id, msg_text, reply_markup=kb)

    try:
        decision = await asyncio.wait_for(fut, timeout=25.0)
        return decision
    except asyncio.TimeoutError:
        print(f"[FallbackDecision] ⏰ 25s Timeout reached for {phone}. Auto-cancelling for refund...")
        await send_tg_message(
            client,
            chat_id,
            f"⏰ <b>Decision Timeout (25s):</b> <code>+91{phone}</code> par response nahi mila. Number auto-cancel kiya jaa raha hai refund ke liye.",
        )
        return "cancel"
    finally:
        PENDING_OTP_FALLBACK_DECISIONS.pop(phone, None)


async def _send_gemixai_otp_flow(client: httpx.AsyncClient, phone: str, dev: dict, chat_id: int | str = None) -> dict:
    """Executes GemixAI OTP send with ₹200 OFF offer reroll."""
    try:
        print(f"[GemixAI] Executing GemixAI API for +91{phone} (rerolling for ₹200 OFF)...")
        offer_bucket = 0
        for rr_try in range(1, 25):
            try:
                rr_resp = await client.post(f"{GEMIXAI_BASE}/reroll", headers=GEMIXAI_HEADERS, timeout=8)
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
            await asyncio.sleep(0.3)

        if not offer_bucket:
            offer_bucket = 200

        if chat_id:
            await send_tg_message(
                client,
                chat_id,
                f"🎯 <b>GemixAI: ₹{offer_bucket} OFF Offer Mil Gaya!</b>\n📤 Ab <code>+91{phone}</code> par OTP bhej rahe hain...",
            )

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
                        "chat_id": chat_id,
                    },
                }
            else:
                return {"ok": False, "error": f"GemixAI rejected: {otp_data}"}
    except Exception as e:
        return {"ok": False, "error": f"GemixAI error: {str(e)}"}
    return {"ok": False, "error": "GemixAI flow failed"}


async def send_meesho_otp(client: httpx.AsyncClient, phone: str, dev: dict, chat_id: int | str = None, worker_id: int = 1, server: str = "") -> dict:
    """Dispatches OTP using selected Engine: Cupponhub, Crowstack (Rem/Marin), GemixAI, Hidenfree, or Auto-Failover."""
    cfg = get_user_config(chat_id) if chat_id else {}
    engine = cfg.get("api_engine", "crowstack")
    tier = int(cfg.get("cupponhub_tier", 200))
    cur_ref = get_referral_link()

    # ── 1. Cupponhub Direct Engine ──
    if engine == "cupponhub":
        cup_res = await cupponhub_send_otp(client, phone, tier=tier, chat_id=chat_id)
        if cup_res.get("ok"):
            print(f"[{time.strftime('%H:%M:%S')}] [Cupponhub] ✅ OTP sent via Cupponhub (Tier: ₹{tier}) to +91{phone}!")
            return cup_res
        else:
            print(f"[Cupponhub failed for +91{phone}]: {cup_res.get('error')}")
            return cup_res

    # ── 2. GemixAI Direct Engine ──
    if engine == "gemixai":
        return await _send_gemixai_otp_flow(client, phone, dev, chat_id)

    # ── 3. Hidenfree Direct Engine ──
    if engine == "hidenfree":
        try:
            hf_res = await client.post(f"{HIDENFREE_BASE}/login/send-otp", headers=HIDENFREE_HEADERS, json={"phone": phone, "referral_link": cur_ref}, timeout=15)
            if hf_res.status_code == 200:
                hf_data = hf_res.json() or {}
                if hf_data.get("ok"):
                    return {
                        "ok": True,
                        "method": "hidenfree",
                        "registered": False,
                        "bucket": hf_data.get("offer_bucket", 200),
                        "session": {"method": "hidenfree", "phone": phone, "instance_id": dev["instance_id"], "chat_id": chat_id},
                    }
        except Exception as e:
            print(f"[Hidenfree send-otp error]: {e}")
        return {"ok": False, "error": "Hidenfree send-otp failed"}

    # ── 4. Auto-Failover: Cupponhub ➔ Crowstack ➔ GemixAI ──
    if engine == "auto":
        cup_res = await cupponhub_send_otp(client, phone, tier=tier, chat_id=chat_id)
        if cup_res.get("ok"):
            print(f"[{time.strftime('%H:%M:%S')}] [Auto-Failover] ✅ OTP sent via Cupponhub (Tier: ₹{tier}) to +91{phone}!")
            return cup_res
        print(f"[Auto-Failover] Cupponhub failed ({cup_res.get('error')}). Auto-falling back to Crowstack...")

    # ── Crowstack (Rem & Marin session failover) ──
    cur_prof = get_crowstack_profile_key(chat_id)
    profiles_to_try = [cur_prof]
    if cur_prof == "new":
        profiles_to_try.append("main")
    elif cur_prof == "main":
        profiles_to_try.append("new")
    else:
        profiles_to_try.extend(["new", "main"])

    crowstack_errors = []
    for prof_key in profiles_to_try:
        try:
            p_info = CROWSTACK_PROFILES.get(prof_key, CROWSTACK_PROFILES["new"])
            prof_name = p_info["name"]
            print(f"[{time.strftime('%H:%M:%S')}] [Crowstack] Trying {prof_name} for +91{phone}...")

            headers = get_crowstack_headers(chat_id)
            headers["User-Agent"] = p_info["user_agent"]
            headers["X-Tg-Init-Data"] = p_info["x_tg_init_data"]
            headers["sec-ch-ua"] = p_info["sec_ch_ua"]
            headers["sec-ch-ua-platform"] = p_info.get("sec_ch_ua_platform", '"Windows"')

            payload = {"phone": phone, "ref_link": cur_ref, "force": True}
            resp = await client.post(
                f"{CROWSTACK_BASE}/send-otp",
                headers=headers,
                json=payload,
                timeout=25,
            )
            raw_text = resp.text.strip()
            data = None
            try:
                data = resp.json()
            except Exception:
                pass

            if resp.status_code == 200 and data and data.get("ok"):
                print(f"[{time.strftime('%H:%M:%S')}] [Crowstack] ✅ OTP sent successfully using {prof_name}!")
                return {
                    "ok": True,
                    "method": "crowstack",
                    "profile": prof_key,
                    "registered": data.get("registered"),
                    "bucket": data.get("bucket"),
                    "session": {
                        "method": "crowstack",
                        "profile": prof_key,
                        "phone": phone,
                        "instance_id": dev["instance_id"],
                        "chat_id": chat_id,
                    },
                }
            else:
                err_msg = (data.get("error") or data.get("message") or raw_text) if data else raw_text
                crowstack_errors.append(f"{prof_name}: {err_msg} (HTTP {resp.status_code})")
                print(f"[Crowstack {prof_name} rejected]: {err_msg}")
                if chat_id:
                    err_preview = raw_text[:800] if raw_text else f"HTTP {resp.status_code}"
                    await send_tg_message(
                        client,
                        chat_id,
                        f"⚠️ <b>[Crowstack Response] send-otp REJECTED!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📊 <b>HTTP Status:</b> <code>{resp.status_code}</code>\n"
                        f"👤 <b>Session:</b> <code>{prof_name}</code>\n"
                        f"❌ <b>Server Response:</b>\n<pre><code>{err_preview}</code></pre>",
                    )
        except Exception as e:
            crowstack_errors.append(f"{prof_name}: {e}")
            print(f"[Crowstack {prof_key} error]: {e}")
            if chat_id:
                await send_tg_message(
                    client,
                    chat_id,
                    f"🚨 <b>[Crowstack Network Exception]</b>\n"
                    f"👤 <b>Session:</b> <code>{prof_name}</code>\n"
                    f"⚠️ <code>{e}</code>",
                )

    print(f"[Crowstack Failover] All Crowstack sessions failed for +91{phone}: {crowstack_errors}")
    if chat_id:
        await send_tg_message(
            client,
            chat_id,
            f"❌ <b>[Crowstack Failover] All Sessions Failed for +91{phone}!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Session Errors:</b>\n<code>{chr(10).join(crowstack_errors)}</code>",
        )

    if chat_id and engine == "auto":
        user_choice = await request_otp_fallback_decision(client, chat_id, phone, worker_id, server)
        if user_choice != "gemix":
            return {"ok": False, "error": f"Crowstack Rem & Marin failed ({'; '.join(crowstack_errors)}) & user chose to cancel."}
        return await _send_gemixai_otp_flow(client, phone, dev, chat_id)

    return {"ok": False, "error": f"All OTP dispatch methods failed ({'; '.join(crowstack_errors)})"}


async def verify_meesho_otp(client: httpx.AsyncClient, phone: str, otp: str, session: dict, dev: dict, chat_id: int | str = None) -> dict:
    """Verifies OTP via Cupponhub, Crowstack (Rem/Marin auto-failover), Hidenfree, GemixAI, or fallback to OTPLESS."""
    method = session.get("method")
    cid = chat_id or session.get("chat_id")

    # Method 1: Cupponhub
    if method == "cupponhub":
        sess_id = session.get("session_id") or f"8282846997_{phone}"
        return await cupponhub_verify_otp(client, sess_id, otp, phone=phone)

    # Method 2: Crowstack
    if method == "crowstack":
        prof_key = session.get("profile", get_crowstack_profile_key(cid))
        # Ensure all 3 sessions are attempted in order
        profiles_to_try = [prof_key]
        for candidate in ("new", "main", "session3"):
            if candidate not in profiles_to_try:
                profiles_to_try.append(candidate)

        for p_k in profiles_to_try:
            try:
                p_info = CROWSTACK_PROFILES.get(p_k, CROWSTACK_PROFILES["new"])
                prof_name = p_info["name"]
                headers = get_crowstack_headers(cid)
                headers["User-Agent"] = p_info["user_agent"]
                headers["X-Tg-Init-Data"] = p_info["x_tg_init_data"]
                headers["sec-ch-ua"] = p_info["sec_ch_ua"]
                headers["sec-ch-ua-platform"] = p_info.get("sec_ch_ua_platform", '"Windows"')

                payload = {"otp": otp}
                print(f"[{time.strftime('%H:%M:%S')}] [Crowstack] Verifying OTP {otp} for +91{phone} via {prof_name}...")
                resp = await client.post(
                    f"{CROWSTACK_BASE}/verify",
                    headers=headers,
                    json=payload,
                    timeout=25,
                )
                raw_text = resp.text.strip()
                data = None
                try:
                    data = resp.json()
                except Exception:
                    pass

                if resp.status_code == 200 and data and data.get("ok"):
                    acc = data.get("account", {})
                    print(f"[{time.strftime('%H:%M:%S')}] [Crowstack] ✅ Verify SUCCESS via {prof_name} for +91{phone}!")

                    # Call Crowstack Export File API right after account creation
                    try:
                        exp_res = await crowstack_export_file(client, cid)
                        if exp_res.get("ok"):
                            exp_data = exp_res.get("data")
                            if isinstance(exp_data, dict):
                                for k, v in exp_data.items():
                                    if k not in acc or not acc[k]:
                                        acc[k] = v
                        else:
                            if cid:
                                await send_tg_message(client, cid, f"⚠️ <b>[Crowstack Response] export_file non-200:</b>\n<code>{exp_res}</code>")
                    except Exception as exp_e:
                        print(f"[Crowstack export_file error]: {exp_e}")
                        if cid:
                            await send_tg_message(client, cid, f"⚠️ <b>[Crowstack export_file exception]:</b> <code>{exp_e}</code>")

                    xo = acc.get("xo", "")
                    ox = acc.get("ox", "")
                    return {
                        "ok": True,
                        "user_id": acc.get("user_id"),
                        "phone": acc.get("mobile", phone),
                        "account": acc,
                        "xo": xo,
                        "ox": ox,
                        "bucket": acc.get("offer_bucket") or acc.get("bucket"),
                        "is_new": True,
                    }
                else:
                    err = (data.get("error") or data.get("message") or raw_text) if data else raw_text
                    print(f"[Crowstack verify rejected with {p_k}]: {err}")
                    if cid:
                        err_preview = raw_text[:800] if raw_text else f"HTTP {resp.status_code}"
                        await send_tg_message(
                            client,
                            cid,
                            f"❌ <b>[Crowstack Response] verify REJECTED!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📊 <b>HTTP Status:</b> <code>{resp.status_code}</code>\n"
                            f"👤 <b>Session:</b> <code>{prof_name}</code>\n"
                            f"⚠️ <b>Server Response:</b>\n<pre><code>{err_preview}</code></pre>",
                        )
            except Exception as e:
                print(f"[Crowstack verify error with {p_k}]: {e}")
                if cid:
                    await send_tg_message(client, cid, f"🚨 <b>[Crowstack Verify Exception]:</b> <code>{e}</code>")

        if cid:
            await send_tg_message(client, cid, f"❌ <b>[Crowstack Verify] All 3 sessions (Rem, Marin & Marin123) failed for +91{phone}!</b>")
        return {"ok": False, "error": "Crowstack verify failed across all 3 sessions.", "fail_type": "crowstack_verify"}

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
KNOWN_MENU_BUTTONS = {
    "🚀 Start Hunt",
    "📱 Check My Number",
    "⚙️ Select Servers",
    "🔑 Manage Keys",
    "🔑 Set API Key",
    "📋 Accounts Summary",
    "📊 Stats",
    "📝 Set JSON Format",
    "🔄 Convert JSON",
    "⚙️ Store Settings",
    "👥 Paid Users / Orders",
    "📢 Broadcast",
    "📦 View Orders",
    "💰 Balance",
    "🛑 Stop Hunt",
    "👤 Switch Identity",
    "👤 API Session",
    "🔗 Set Referral",
    "💰 Set JSON Price",
    "➕ Add Custom Server",
    "🛍️ Buy Meesho JSON",
    "📦 My Orders",
    "💬 Contact Admin",
    "ℹ️ How It Works",
    "❌ Cancel",
    "🔙 Back to Menu",
}

ADMIN_MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🚀 Start Hunt"}, {"text": "📱 Check My Number"}],
        [{"text": "⚙️ Select Servers"}, {"text": "🔑 Manage Keys"}],
        [{"text": "📋 Accounts Summary"}, {"text": "📊 Stats"}],
        [{"text": "📝 Set JSON Format"}, {"text": "🔄 Convert JSON"}],
        [{"text": "⚙️ Store Settings"}, {"text": "👥 Paid Users / Orders"}],
        [{"text": "📢 Broadcast"}, {"text": "💰 Balance"}, {"text": "🛑 Stop Hunt"}],
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


# ─── Admin Paid Users Queue & Order Delivery Helpers ──────────────────────────
def build_paid_orders_view_message_and_markup() -> tuple[str, dict]:
    all_ords = load_orders()
    if not all_ords:
        return "ℹ️ Koi orders nahi mile.", {"inline_keyboard": []}

    pending_appr = [o for o in all_ords.values() if o.get("status") == "PENDING_APPROVAL"]
    paid_approved = [o for o in all_ords.values() if o.get("status") in ("PAID_APPROVED", "PROCESSING", "READY_FOR_DELIVERY")]
    completed = [o for o in all_ords.values() if o.get("status") == "COMPLETED"]

    lines = [
        "👥 <b>MEESHO PAID USERS & ORDER QUEUE</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    kb_rows = []

    if paid_approved:
        lines.append(f"🟢 <b>PAID & READY FOR DELIVERY ({len(paid_approved)}):</b>")
        for o in sorted(paid_approved, key=lambda x: x.get("created_at", 0), reverse=True)[:10]:
            oid = o.get("id")
            uid = o.get("user_id")
            uname = o.get("username") or o.get("first_name") or uid
            ref_tag = " (Custom Link)" if o.get("custom_referral_link") else ""
            lines.append(
                f"• <b>#{oid}</b> | User: <code>{uid}</code> (@{uname})\n"
                f"  Amt: ₹{o.get('amount')}{ref_tag} | UTR: <code>{o.get('utr') or 'N/A'}</code>\n"
                f"  Status: <b>{o.get('status')}</b>"
                + (f"\n  🔗 Refer: <code>{o.get('custom_referral_link')}</code>" if o.get("custom_referral_link") else "")
            )
            btn_label = f"📤 Deliver to @{uname} (#{oid})"[:36]
            kb_rows.append([{"text": btn_label, "callback_data": f"deliver_custom_{oid}"}])
        lines.append("┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈")

    if pending_appr:
        lines.append(f"🟡 <b>UTR SUBMITTED (PENDING APPROVAL) ({len(pending_appr)}):</b>")
        for o in sorted(pending_appr, key=lambda x: x.get("created_at", 0), reverse=True)[:5]:
            oid = o.get("id")
            uid = o.get("user_id")
            uname = o.get("username") or uid
            lines.append(
                f"• <b>#{oid}</b> | @{uname} | ₹{o.get('amount')} | UTR: <code>{o.get('utr')}</code>"
            )
            kb_rows.append([
                {"text": f"✅ Approve #{oid}", "callback_data": f"approve_ord_{oid}"},
                {"text": f"📁 Deliver #{oid}", "callback_data": f"deliver_custom_{oid}"},
            ])
        lines.append("┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈")

    if completed:
        lines.append(f"✅ <b>RECENT DELIVERIES ({len(completed)} total):</b>")
        for o in sorted(completed, key=lambda x: x.get("delivered_at", 0), reverse=True)[:4]:
            lines.append(f"• <b>#{o.get('id')}</b> | +91{o.get('delivered_phone') or 'N/A'} | ₹{o.get('amount')} | Done ✅")

    if not pending_appr and not paid_approved and not completed:
        lines.append("ℹ️ Abhi koi active paid orders nahi hain.")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("👉 <i>Kisi bhi user ko JSON deliver karne ke liye unke naam ke button par click karein ya command <code>/deliver &lt;order_id&gt;</code> use karein.</i>")

    kb_rows.append([{"text": "🔄 Refresh List", "callback_data": "view_paid_users"}])
    return "\n".join(lines), {"inline_keyboard": kb_rows}


async def deliver_json_with_simulation(
    client: httpx.AsyncClient,
    buyer_id: str,
    order_id: str,
    content: str,
    file_bytes: bytes | None = None,
    filename: str = "meesho_account.json",
    phone_hint: str = None,
    admin_notify_id: str | int | None = None,
):
    try:
        phone = phone_hint
        if not phone and content:
            m = re.search(r'"(?:phone|mobile|phoneNumber|number)"\s*:\s*"?(?:91)?([6-9]\d{9})"?', content)
            if m:
                phone = m.group(1)
        if not phone:
            m = re.search(r'\b[6-9]\d{9}\b', content or "")
            if m:
                phone = m.group(0)
        if not phone:
            phone = str(random.randint(6200000000, 9999999999))

        masked_phone = f"{phone[:3]}XXXX{phone[-3:]}"

        # ── Step 1: Searching Fresh Number Simulation ──
        await send_tg_message(
            client,
            buyer_id,
            f"🔍 <b>[Step 1/4] Fresh Unregistered Number Search Shuru...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
            f"⚡ Server 5841 par 100% fresh unregistered Indian number scan ho raha hai...\n"
            f"⏳ <b>Status:</b> <code>[▓▓░░░░░░░░] 25% (Searching)</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        )
        await asyncio.sleep(2.5)

        # ── Step 2: Fresh Number Found & OTP Sent Simulation ──
        await send_tg_message(
            client,
            buyer_id,
            f"📱 <b>[Step 2/4] Fresh Unregistered Number Mil Gaya!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📞 <b>Allocated Mobile:</b> <code>+91 {masked_phone}</code>\n"
            f"📩 Official Meesho OTP dispatch kar diya gaya hai (Max wait: 2 mins)...\n"
            f"⏳ <b>Status:</b> <code>[▓▓▓▓▓░░░░░] 55% (OTP Sent)</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        )
        await asyncio.sleep(2.5)

        # ── Step 3: OTP Verified & Extracting Tokens Simulation ──
        await send_tg_message(
            client,
            buyer_id,
            f"⚡ <b>[Step 3/4] OTP Verify Ho Gaya & Session Generate Ho Raha Hai!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐 <b>Verification:</b> <code>6-Digit OTP Verified ✅</code>\n"
            f"⚙️ Meesho session tokens, cookies & xo/ox keys extract ho rahe hain...\n"
            f"⏳ <b>Status:</b> <code>[▓▓▓▓▓▓▓▓░░] 85% (Extracting Tokens)</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        )
        await asyncio.sleep(2.0)

        # ── Step 4: JSON Generation Complete Simulation ──
        await send_tg_message(
            client,
            buyer_id,
            f"✨ <b>[Step 4/4] Meesho Account JSON Ban Gya!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎉 <b>Account JSON Ban Kar Ready Hai!</b>\n"
            f"📁 Packaging ready-to-use <code>.json</code> file...\n"
            f"⏳ <b>Status:</b> <code>[▓▓▓▓▓▓▓▓▓▓] 100% (Complete)</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        )
        await asyncio.sleep(1.2)

        # ── Step 5: Final Delivery Message & File Attachment ──
        buyer_msg = (
            f"🎉 <b>AAPKA MEESHO JSON ORDER READY HAI!</b>\n\n"
            f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
            f"📱 <b>Mobile:</b> <code>+91 {masked_phone}</code>\n"
            f"⚡ <b>Status:</b> 100% Verified & Delivered!\n\n"
            f"📋 <b>Account JSON Data:</b>\n"
            f"<pre><code>{content[:3000]}</code></pre>\n\n"
            f"👇 Niche di gayi <code>.json</code> file download karke use karein. Thank you for shopping with us!"
        )
        await send_tg_message(client, buyer_id, buyer_msg, reply_markup=USER_MAIN_MENU_KEYBOARD)

        if file_bytes:
            await send_tg_document(
                client,
                buyer_id,
                filename=filename or f"meesho_{phone}.json",
                content=file_bytes,
                caption=f"✅ Meesho Account JSON (+91{masked_phone})",
            )
        else:
            await send_tg_document(
                client,
                buyer_id,
                filename=filename or f"meesho_{phone}.json",
                content=content,
                caption=f"✅ Meesho Account JSON (+91{masked_phone})",
            )

        if admin_notify_id:
            await send_tg_message(
                client,
                admin_notify_id,
                f"🎉 <b>ORDER #{order_id} DELIVERED SUCCESSFULLY!</b>\n\n"
                f"👤 <b>Buyer:</b> <code>{buyer_id}</code>\n"
                f"📱 <b>Phone:</b> <code>+91{phone}</code>\n"
                f"✨ User ko staged simulation ke sath JSON file successfully deliver ho gayi!",
                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
            )
    except Exception as e:
        print(f"[Simulation Delivery Error] {e}")


# ─── User Tracking Registry & Invoice Generator ───────────────────────────────
ALL_USERS_FILE = "all_users.json"


def register_user_activity(user_id: int | str, username: str = "", first_name: str = ""):
    if not user_id:
        return
    try:
        users = {}
        if os.path.exists(ALL_USERS_FILE):
            try:
                with open(ALL_USERS_FILE, "r", encoding="utf-8") as f:
                    users = json.load(f)
            except Exception:
                users = {}
        uid = str(user_id)
        existing = users.get(uid, {})
        users[uid] = {
            "user_id": uid,
            "username": username or existing.get("username", ""),
            "first_name": first_name or existing.get("first_name", ""),
            "last_seen": time.time(),
        }
        with open(ALL_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[RegisterUser Error] {e}")


def get_all_broadcast_recipients() -> set:
    recipients = set()
    if os.path.exists(ALL_USERS_FILE):
        try:
            with open(ALL_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid in data.keys():
                    recipients.add(str(uid))
        except Exception:
            pass

    all_cfgs = load_all_configs()
    for cid in all_cfgs.keys():
        recipients.add(str(cid))

    all_ords = load_orders()
    for o in all_ords.values():
        if o.get("user_id"):
            recipients.add(str(o["user_id"]))

    if str(ADMIN_CHAT_ID) in recipients:
        recipients.remove(str(ADMIN_CHAT_ID))
    return recipients


async def create_and_send_buyer_invoice(
    client: httpx.AsyncClient,
    chat_id: int | str,
    user_id: int | str,
    username: str,
    first_name: str,
    order_type: str,
    quantity: int,
    unit_price: int,
    custom_referral_link: str | None = None,
):
    total_amount = quantity * unit_price
    order_id = f"ORD{int(time.time()) % 1000000:06d}"
    store_st = load_store_settings()
    upi_id = store_st.get("upi_id", "paytmqr28100505010115i3puxb4eoa@paytm")
    upi_name = store_st.get("upi_name", "Meesho Store")

    new_order = {
        "id": order_id,
        "user_id": str(user_id),
        "username": username,
        "first_name": first_name,
        "amount": total_amount,
        "quantity": quantity,
        "unit_price": unit_price,
        "order_type": order_type,
        "custom_referral_link": custom_referral_link,
        "status": "AWAITING_PAYMENT",
        "created_at": time.time(),
        "utr": None,
    }
    save_order(new_order)
    st = ACTIVE_TASKS.setdefault(chat_id, {})
    st["awaiting_utr_order"] = order_id
    st["manual_step"] = None

    qr_bytes = generate_upi_qr_bytes(upi_id, upi_name, total_amount, order_id)
    ref_line = f"🔗 <b>Attached Refer Link:</b>\n<code>{custom_referral_link}</code>\n" if custom_referral_link else ""
    invoice_caption = (
        f"🧾 <b>MEESHO JSON OFFICIAL INVOICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
        f"📦 <b>Type:</b> {order_type}\n"
        f"🔢 <b>Quantity:</b> <b>{quantity} Account(s)</b> (@ ₹{unit_price}/acc)\n"
        f"{ref_line}"
        f"💵 <b>Total Payable:</b> <b>₹{total_amount}</b>\n"
        f"👤 <b>Payee Name:</b> {upi_name}\n"
        f"📲 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>PAYMENT STEPS:</b>\n"
        f"1️⃣ Upar diye gaye QR Code ko Paytm / PhonePe / GPay se scan karein.\n"
        f"2️⃣ <b>₹{total_amount}</b> ka exact payment karein.\n"
        f"3️⃣ Payment ke baad <b>12-digit UTR / Ref Number</b> copy karein.\n"
        f"4️⃣ Niche <b>Submit UTR</b> button dabakar ya seedhe yahan UTR likhkar bhejein.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Admin payment verify karte hi fresh accounts process hona shuru ho jayenge!</i>"
    )
    qr_inline_kb = {
        "inline_keyboard": [
            [{"text": "💳 Submit UTR / Ref No", "callback_data": f"submit_utr_{order_id}"}],
            [{"text": "❌ Cancel Order", "callback_data": f"cancel_ord_{order_id}"}],
        ]
    }
    await send_tg_photo(client, chat_id, qr_bytes, caption=invoice_caption, reply_markup=qr_inline_kb)


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
        srv_desc = ", ".join(f"Server {s}" for s in servers)
        print(f"[OrderDelivery] Attempt #{attempt} for Order {order_id} racing servers [{srv_desc}]...")

        res = await otpd_buy_multi_server_race(client, api_key, servers)
        if not res.get("ok"):
            print(f"[OrderDelivery] Buy failed on [{srv_desc}]: {res.get('error')}")
            await asyncio.sleep(3)
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
            await asyncio.sleep(0.3)

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


# ─── Multi-Key UI Helpers ─────────────────────────────────────────────────────
async def build_keys_view_message_and_markup(client: httpx.AsyncClient, chat_id: int | str):
    keys = get_user_api_keys(chat_id)
    lines = [
        "🔑 <b>OTP DOCTOR MULTI-KEY MANAGEMENT</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Aap ek se zyada (multiple) API keys add kar sakte hain.\nHar key ka <b>alag worker parallel chalega (1-2s speed)</b> bina kisi collision ke!\n",
    ]
    if not keys:
        lines.append("❌ <b>Koi API Key add nahi hai.</b>\nNiche <b>➕ Add New Key</b> par click karein.")
    else:
        bal_map = await fetch_all_key_balances(client, keys, max_concurrency=30)
        total_bal = 0.0
        for b in bal_map.values():
            try:
                total_bal += float(b)
            except ValueError:
                pass

        lines.append(f"⚡ <b>Total Configured Keys:</b> <code>{len(keys)} Keys</code> (Parallel Workers)")
        lines.append(f"💵 <b>Total Combined Wallet:</b> <b>₹{total_bal:.2f}</b>\n")

        disp_limit = 8
        for idx, k in enumerate(keys[:disp_limit], start=1):
            bal = bal_map.get(k, "0.00")
            masked = k[:4] + "..." + k[-4:] if len(k) >= 8 else k
            lines.append(f"• <b>Key #{idx}:</b> <code>{masked}</code> | Balance: <b>₹{bal}</b> (<code>Worker #{idx}</code>)")

        if len(keys) > disp_limit:
            remaining = len(keys) - disp_limit
            lines.append(f"\n<i>... aur {remaining} active keys configured hain.</i>")
            lines.append("📁 <i>Sabhi keys export/backup ke liye <code>/backupkeys</code> bhejein.</i>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("👇 <i>Niche button dabakar actions choose karein:</i>")

    inline_kb = {
        "inline_keyboard": [
            [
                {"text": "➕ Add New Key", "callback_data": "add_key_prompt"},
                {"text": "🗑️ Delete Key", "callback_data": "del_key_prompt"},
            ],
            [
                {"text": "🔄 Refresh Balances", "callback_data": "refresh_keys"},
                {"text": "📁 Backup Keys (.txt)", "callback_data": "backup_keys_action"},
            ],
            [
                {"text": "🧹 Clear All Keys", "callback_data": "clear_keys_prompt"},
            ]
        ]
    }
    return "\n".join(lines), inline_kb


async def build_stats_view_message_and_markup(client: httpx.AsyncClient, chat_id: int | str, state: dict = None) -> tuple[str, dict]:
    cfg = get_user_config(chat_id)
    keys = get_user_api_keys(chat_id)
    sel_servers = cfg.get("selected_servers", ["5841"])
    server_names = ", ".join(f"Server {s}" for s in sel_servers)

    history = load_accounts_history()
    failed_history = load_failed_accounts_history()
    total_all_time = len(history)
    all_time_failed = len(failed_history)
    today_prefix = time.strftime("%Y-%m-%d")
    today_count = sum(1 for x in history if str(x.get("created_at", "")).startswith(today_prefix))
    today_failed = sum(1 for x in failed_history if str(x.get("failed_at", "")).startswith(today_prefix))

    # Day-wise aggregate
    day_counts = {}
    for item in history:
        dt_str = str(item.get("created_at", ""))[:10]
        if dt_str and len(dt_str) == 10:
            day_counts[dt_str] = day_counts.get(dt_str, 0) + 1

    sorted_days = sorted(day_counts.keys(), reverse=True)
    day_lines = []
    for d in sorted_days[:5]:
        label = f"📅 Today ({d})" if d == today_prefix else f"📆 {d}"
        day_lines.append(f"• <b>{label}:</b> <b>{day_counts[d]}</b> accounts")
    if not day_lines:
        day_lines.append(f"• <b>📅 Today ({today_prefix}):</b> 0 accounts")
    day_history_str = "\n".join(day_lines)

    cid = int(chat_id) if str(chat_id).isdigit() else chat_id
    if state is None:
        state = ACTIVE_TASKS.get(cid) or ACTIVE_TASKS.get(str(chat_id)) or {}

    balances_dict = await fetch_all_key_balances(client, keys, max_concurrency=25)
    total_bal = sum(parse_balance_float(v) for v in balances_dict.values())

    is_running = state.get("hunting", False)

    # Compile per-key performance & stats
    key_stats = []
    for idx, k in enumerate(keys, start=1):
        masked = k[:4] + "..." + k[-4:] if len(k) >= 8 else k
        bal = parse_balance_float(balances_dict.get(k, "0.00"))
        w_st = state.get("worker_states", {}).get(idx, {}) if is_running else {}
        session_created = w_st.get("accounts", 0)
        session_failed = w_st.get("failed", 0)
        session_att = w_st.get("attempts", 0)
        c_rej = w_st.get("crowstack_rejects", 0)
        t_fail = w_st.get("timeout_fails", 0)
        p_cancels = w_st.get("pending_cancels", 0)
        w_status = w_st.get("status", "Running" if is_running else "Idle")

        all_created = sum(1 for x in history if x.get("key_preview") == masked or (x.get("worker_id") == idx and not x.get("key_preview")))
        all_failed = sum(1 for x in failed_history if x.get("key_preview") == masked or (x.get("worker_id") == idx and not x.get("key_preview")))
        today_created = sum(1 for x in history if (x.get("key_preview") == masked or (x.get("worker_id") == idx and not x.get("key_preview"))) and str(x.get("created_at", "")).startswith(today_prefix))

        key_stats.append({
            "idx": idx,
            "key": k,
            "masked": masked,
            "balance": bal,
            "session_created": session_created,
            "session_failed": session_failed,
            "session_att": session_att,
            "crowstack_rejects": c_rej,
            "timeout_fails": t_fail,
            "pending_cancels": p_cancels,
            "all_created": all_created,
            "all_failed": all_failed,
            "today_created": today_created,
            "status": w_status,
        })

    # Find Top Performing API Key (Ranked by accounts created)
    if is_running:
        sorted_keys = sorted(key_stats, key=lambda x: (x["session_created"], x["today_created"], x["all_created"], x["balance"]), reverse=True)
    else:
        sorted_keys = sorted(key_stats, key=lambda x: (x["today_created"], x["all_created"], x["balance"]), reverse=True)

    top_key = sorted_keys[0] if sorted_keys else None
    top_recommendation = ""
    if top_key:
        active_cnt = top_key["session_created"] if is_running else top_key["today_created"]
        total_cnt = top_key["all_created"]
        fail_cnt = top_key["session_failed"] if is_running else top_key["all_failed"]
        t_bal = top_key["balance"]
        if active_cnt > 0 or total_cnt > 0:
            if t_bal < 20.0:
                bal_alert = f"⚠️ <b>LOW BALANCE ALERT:</b> Is key se sabse zyada accounts ban rahe hain, lekin balance sirf <b>₹{t_bal:.2f}</b> bacha hai! Jaldi balance add karein taaki hunting ruke na."
            elif t_bal < 40.0:
                bal_alert = f"ℹ️ <b>Balance Moderate:</b> ₹{t_bal:.2f} available. Top-up add kar sakte hain."
            else:
                bal_alert = f"✅ <b>Balance Healthy:</b> ₹{t_bal:.2f} available."

            period_label = f"Session: {active_cnt} Created" if is_running else f"Today: {active_cnt} Created"
            top_recommendation = (
                f"🏆 <b>SABSE ZYADA ACCOUNTS BANE WALI KEY:</b>\n"
                f"👑 <b>Key #{top_key['idx']} (<code>{top_key['masked']}</code>)</b>\n"
                f"📈 <b>Stats:</b> {period_label} | Total: {total_cnt} | Failed: {fail_cnt}\n"
                f"💰 <b>Current Balance:</b> <b>₹{t_bal:.2f}</b>\n"
                f"{bal_alert}\n\n"
            )

    if is_running:
        runtime_mins = int((time.time() - state.get("start_time", time.time())) // 60)
        worker_lines = []
        max_disp = min(12, len(key_stats))
        for it in key_stats[:max_disp]:
            idx = it["idx"]
            masked = it["masked"]
            bal = it["balance"]
            s_c = it["session_created"]
            c_rej = it["crowstack_rejects"]
            t_fail = it["timeout_fails"]
            p_cancels = it["pending_cancels"]
            st_text = it["status"]
            bal_tag = " ⚠️ Low Bal" if bal < 20.0 else ""
            rank_badge = "👑 " if top_key and top_key["idx"] == idx and (s_c > 0 or it["all_created"] > 0) else ""
            worker_lines.append(
                f"• {rank_badge}<b>Worker #{idx} ({masked}):</b> <code>{st_text}</code>\n"
                f"   └ <b>{s_c}</b> Created | <b>{c_rej}</b> Crowstack Reject | <b>{t_fail}</b> Timeout Fail | <b>{p_cancels}</b> In Line for Cancel | Bal: <b>₹{bal:.2f}</b>{bal_tag}"
            )
        if len(key_stats) > max_disp:
            worker_lines.append(f"• <i>... aur {len(key_stats) - max_disp} more workers active</i>")
        w_details = "\n".join(worker_lines) if worker_lines else "<i>No active workers</i>"

        target_limit = state.get("target_limit", 0)
        budget_block = ""
        if target_limit > 0:
            created_so_far = state.get("accounts_created", 0)
            remaining_accs = max(0, target_limit - created_so_far)
            est_cost_rem = remaining_accs * 12.0
            est_cost_total = target_limit * 12.0
            buf_val = total_bal - est_cost_rem
            buf_str = f"+₹{buf_val:.2f} ✅ (Balance Sufficient)" if buf_val >= 0 else f"-₹{abs(buf_val):.2f} ⚠️ (Deficit)"
            budget_block = (
                f"🎯 <b>Target & Budget Progress:</b>\n"
                f"• Progress: <b>{created_so_far}/{target_limit} Accounts</b> ({remaining_accs} remaining)\n"
                f"• Estimated Cost: <b>~₹{est_cost_rem:.2f}</b> (Total: ~₹{est_cost_total:.2f} @ ₹12/acc)\n"
                f"• Safe Buffer: <b>{buf_str}</b>\n\n"
            )

        consec_rej = state.get("consecutive_crowstack_rejects", 0)
        consec_str = f" ⚠️ (Consecutive: {consec_rej}/3 - Auto-Stop on 3)" if consec_rej > 0 else ""

        stats_text = (
            f"📊 <b>LIVE MULTI-KEY HUNTING STATS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>Status:</b> 🟢 Running ({len(keys)} Parallel Workers)\n"
            f"⏱️ <b>Uptime:</b> {runtime_mins} minutes\n"
            f"🏷️ <b>Active Servers:</b> <code>{server_names}</code>\n\n"
            f"{budget_block}"
            f"📅 <b>DAY-WISE CREATED ACCOUNTS:</b>\n"
            f"{day_history_str}\n"
            f"📊 <b>Total All-Time:</b> <b>{total_all_time} Created</b> (❌ {all_time_failed} Failed)\n"
            f"📅 <b>Today's Total:</b> <b>{today_count} Created</b> (❌ {today_failed} Failed)\n\n"
            f"🔄 <b>Session Attempts:</b> {state.get('attempts', 0)}\n"
            f"❌ <b>Registered Numbers Cancelled:</b> {state.get('registered_count', 0)}\n"
            f"🎉 <b>Session Accounts Created:</b> <b>{state.get('accounts_created', 0)}</b>\n"
            f"⚠️ <b>Session Account Creation Failed:</b> <b>{state.get('failed_creations', 0)}</b>\n"
            f"   ├── ⏰ <b>SMS Timeout (2m):</b> <b>{state.get('failed_sms_timeout', 0)}</b>\n"
            f"   ├── 🦅 <b>Crowstack Verify Rejected:</b> <b>{state.get('failed_crowstack_verify', 0)}</b>{consec_str}\n"
            f"   └── 🔄 <b>In Line for Cancel (Queue):</b> <b>{state.get('pending_cancels', 0)}</b>\n"
            f"💵 <b>Total Pool Wallet:</b> <b>₹{total_bal:.2f}</b>\n\n"
            f"{top_recommendation}"
            f"⚡ <b>Per-Worker Performance & Breakdown:</b>\n{w_details}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 <i>Niche button dabakar live refresh ya counter reset karein:</i>"
        )
    else:
        key_balances = []
        max_disp = min(12, len(key_stats))
        for it in key_stats[:max_disp]:
            idx = it["idx"]
            masked = it["masked"]
            bal = it["balance"]
            a_c = it["all_created"]
            a_f = it["all_failed"]
            bal_tag = " ⚠️ Low Bal" if bal < 20.0 else ""
            rank_badge = "👑 " if top_key and top_key["idx"] == idx and a_c > 0 else ""
            key_balances.append(
                f"• {rank_badge}<b>Key #{idx} ({masked}):</b> ₹{bal:.2f} | Created: <b>{a_c}</b> | Failed: <b>{a_f}</b>{bal_tag}"
            )
        if len(key_stats) > max_disp:
            key_balances.append(f"• <i>... aur {len(key_stats) - max_disp} more keys configured</i>")
        k_bal_str = "\n".join(key_balances) if key_balances else "<i>No keys configured</i>"

        cfg_limit = int(cfg.get("target_limit", 0))
        budget_block_idle = ""
        if cfg_limit > 0:
            est_cost = cfg_limit * 12.0
            buf_val = total_bal - est_cost
            buf_str = f"+₹{buf_val:.2f} ✅ (Balance Sufficient)" if buf_val >= 0 else f"-₹{abs(buf_val):.2f} ⚠️ (Deficit)"
            budget_block_idle = (
                f"🎯 <b>Configured Target Limit:</b> <b>{cfg_limit} Accounts</b>\n"
                f"💰 <b>Estimated Budget:</b> ~₹{est_cost:.2f} (@ ₹12/acc) | Buffer: <b>{buf_str}</b>\n\n"
            )

        stats_text = (
            f"📊 <b>BOT MASTER STATS & DAY-WISE REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>Status:</b> ⚪ Idle (Not running)\n"
            f"🔑 <b>Configured Keys:</b> <b>{len(keys)} Keys</b>\n"
            f"🏷️ <b>Configured Servers:</b> <code>{server_names}</code>\n\n"
            f"{budget_block_idle}"
            f"📅 <b>DAY-WISE CREATED ACCOUNTS:</b>\n"
            f"{day_history_str}\n"
            f"📊 <b>Total All-Time:</b> <b>{total_all_time} Created</b> (❌ {all_time_failed} Failed)\n"
            f"📅 <b>Today's Total:</b> <b>{today_count} Created</b> (❌ {today_failed} Failed)\n\n"
            f"🔄 <b>Last Session Attempts:</b> {state.get('attempts', 0) if state else 0}\n"
            f"🎉 <b>Last Session Created:</b> {state.get('accounts_created', 0) if state else 0}\n"
            f"⚠️ <b>Last Session Failed:</b> {state.get('failed_creations', 0) if state else 0}\n\n"
            f"{top_recommendation}"
            f"💰 <b>Key Performance & Balances:</b>\n{k_bal_str}\n"
            f"💵 <b>Total Combined Wallet:</b> <b>₹{total_bal:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 <i>Niche button dabakar live refresh ya counter reset karein:</i>"
        )

    stats_kb = {
        "inline_keyboard": [
            [
                {"text": "🔄 Refresh Live Stats", "callback_data": "refresh_stats_view"},
                {"text": "⚡ Reset Session Stats", "callback_data": "reset_session_action"},
            ],
            [
                {"text": "📅 Reset Today's Count", "callback_data": "reset_today_action"},
                {"text": "🗑️ Reset All History", "callback_data": "reset_history_prompt"},
            ]
        ]
    }
    return stats_text, stats_kb


def build_identity_settings_message_and_markup(chat_id: int | str):
    cfg = get_user_config(chat_id)
    cur_prof = cfg.get("crowstack_profile", "new")
    prof_info = CROWSTACK_PROFILES.get(cur_prof, CROWSTACK_PROFILES["new"])

    lines = [
        "👤 <b>CROWSTACK API IDENTITY & SESSION MANAGER</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⚡ <b>Active Session:</b> <code>{prof_info['name']}</code>",
        f"🆔 <b>Account ID:</b> <code>{prof_info.get('user_id', 'N/A')} ({prof_info.get('user_name', 'N/A')})</code>",
        f"🌐 <b>Client UA:</b> <code>{prof_info.get('user_agent', '').split(' ')[-1]}</code>\n",
        "💡 <i>Jab aap session profile switch karte hain, sabhi Crowstack requests (send-otp, verify, export_file) usi identity aur header token se execute hoti hain.</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "👇 <b>Choose Active Crowstack Session Profile:</b>",
    ]

    btn_new = "✅ " if cur_prof == "new" else ""
    btn_main = "✅ " if cur_prof == "main" else ""
    btn_cust = "✅ " if cur_prof == "custom" else ""

    kb = {
        "inline_keyboard": [
            [
                {"text": f"{btn_new}✨ New Rem Session (#8912242607 - Edge)", "callback_data": "set_profile_new"},
            ],
            [
                {"text": f"{btn_main}🔷 Main Marin Session (#8282846997 - Chrome)", "callback_data": "set_profile_main"},
            ],
            [
                {"text": f"{btn_cust}✏️ Set Custom X-Tg-Init-Data", "callback_data": "set_profile_custom"},
            ],
            [
                {"text": "🔙 Back to Store Settings", "callback_data": "open_settings_menu"},
            ]
        ]
    }
    return "\n".join(lines), kb


async def compute_target_limit_budget_message(client: httpx.AsyncClient, chat_id: int | str, lim_val: int) -> str:
    """Calculates live OTP Doctor wallet balance vs target limit cost (@ ₹12/account) and returns formatted budget insight."""
    keys = get_user_api_keys(chat_id)
    balances = await fetch_all_key_balances(client, keys)
    total_bal = sum(parse_balance_float(v) for v in balances.values())

    if lim_val <= 0:
        return (
            "♾️ <b>Target Limit: Unlimited (Continuous Hunt Mode)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Current Total Wallet:</b> <b>₹{total_bal:.2f}</b>\n"
            "<i>Bot bina kisi limit ke continuous hunting karta rahega jab tak stop na karein.</i>"
        )

    est_cost = lim_val * 12.0
    buffer_val = total_bal - est_cost

    if buffer_val >= 0:
        return (
            f"🎯 <b>Target Limit: {lim_val} Accounts Set!</b>\n\n"
            f"💰 <b>Smart Auto-Budget & Wallet Management:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Target Accounts:</b> <code>{lim_val}</code>\n"
            f"• <b>Estimated Cost (@ ₹12/acc):</b> <b>~₹{est_cost:.2f}</b>\n"
            f"• <b>Live Total Wallet:</b> <b>₹{total_bal:.2f}</b>\n"
            f"• <b>Safe Remaining Buffer:</b> <b>+₹{buffer_val:.2f}</b> ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Balance is Sufficient!</b> {lim_val} accounts safe tarike se ban jayenge aur target hit hote hi bot automatically hunting stop kar dega."
        )
    else:
        return (
            f"🎯 <b>Target Limit: {lim_val} Accounts Set!</b>\n\n"
            f"💰 <b>Smart Auto-Budget & Wallet Management:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Target Accounts:</b> <code>{lim_val}</code>\n"
            f"• <b>Estimated Cost (@ ₹12/acc):</b> <b>~₹{est_cost:.2f}</b>\n"
            f"• <b>Live Total Wallet:</b> <b>₹{total_bal:.2f}</b>\n"
            f"• <b>Deficit / Shortfall:</b> <b>-₹{abs(buffer_val):.2f}</b> ⚠️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Wallet Warning:</b> Total {lim_val} accounts ke liye lagbhag ₹{est_cost:.2f} lagenge, lekin abhi wallet me sirf ₹{total_bal:.2f} available hai. Beech me hunting rukne se bachne ke liye ₹{abs(buffer_val):.2f} top-up kar lein."
        )


def build_engine_and_target_settings_message_and_markup(chat_id: int | str):
    """Builds the API Engine, Tier & Target Limit configuration menu."""
    cfg = get_user_config(chat_id)
    cur_engine = cfg.get("api_engine", "crowstack")
    cur_tier = int(cfg.get("cupponhub_tier", 200))
    cur_limit = int(cfg.get("target_limit", 0))

    engine_names = {
        "cupponhub": f"🛍️ Cupponhub (Tier: ₹{cur_tier} OFF)",
        "crowstack": "🦅 Crowstack (Rem/Marin Failover)",
        "gemixai": "⚡ GemixAI (₹200 Reroll)",
        "hidenfree": "📦 Hidenfree",
        "auto": f"🔄 Auto-Failover (Cupponhub ₹{cur_tier} ➔ Crowstack ➔ GemixAI)",
    }
    cur_engine_label = engine_names.get(cur_engine, cur_engine)
    limit_label = f"🎯 <b>Max {cur_limit} Accounts (Auto-Stop)</b>" if cur_limit > 0 else "♾️ <b>Unlimited (Continuous Hunt)</b>"

    lines = [
        "⚡ <b>MEESHO BOT — API ENGINE & TARGET CONFIG</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⚙️ <b>Active Account Creator Engine:</b>\n👉 <code>{cur_engine_label}</code>\n",
        f"🏷️ <b>Cupponhub Offer Tier:</b> <b>₹{cur_tier} OFF</b>",
        f"🎯 <b>Configured Target Limit:</b> {limit_label}\n",
        "💡 <i>Aap choose kar sakte hain:</i>\n"
        "• <b>API Engine:</b> Cupponhub, Crowstack, GemixAI ya Auto-Failover\n"
        "• <b>Tier:</b> ₹200 OFF ya ₹180 OFF\n"
        "• <b>Target Limit:</b> Kitne accounts banakar bot auto-stop kare (in-flight accounts finish karke safe exit)\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "👇 <b>Niche diye gaye buttons se turant customize karein:</b>",
    ]

    b_cup = "✅ " if cur_engine == "cupponhub" else ""
    b_crow = "✅ " if cur_engine == "crowstack" else ""
    b_gem = "✅ " if cur_engine == "gemixai" else ""
    b_hid = "✅ " if cur_engine == "hidenfree" else ""
    b_auto = "✅ " if cur_engine == "auto" else ""

    b_t200 = "✅ " if cur_tier == 200 else ""
    b_t180 = "✅ " if cur_tier == 180 else ""

    kb = {
        "inline_keyboard": [
            [
                {"text": f"{b_cup}🛍️ Cupponhub API", "callback_data": "set_engine_cupponhub"},
                {"text": f"{b_crow}🦅 Crowstack API", "callback_data": "set_engine_crowstack"},
            ],
            [
                {"text": f"{b_gem}⚡ GemixAI API", "callback_data": "set_engine_gemixai"},
                {"text": f"{b_hid}📦 Hidenfree", "callback_data": "set_engine_hidenfree"},
            ],
            [
                {"text": f"{b_auto}🔄 Auto-Failover (Smart)", "callback_data": "set_engine_auto"},
            ],
            [
                {"text": f"{b_t200}🎁 Tier: ₹200 OFF", "callback_data": "set_tier_200"},
                {"text": f"{b_t180}🎁 Tier: ₹180 OFF", "callback_data": "set_tier_180"},
            ],
            [
                {"text": f"🎯 Target Limit: {cur_limit if cur_limit > 0 else 'Unlimited'}", "callback_data": "set_limit_prompt"},
                {"text": "🚀 Launch Hunt", "callback_data": "launch_hunt_action"},
            ],
            [
                {"text": "🔙 Back to Store Settings", "callback_data": "open_settings_menu"},
            ]
        ]
    }
    return "\n".join(lines), kb


# ─── Multi-Key Concurrent Worker Engine ───────────────────────────────────────
async def run_single_key_worker(
    client: httpx.AsyncClient,
    chat_id: int | str,
    worker_id: int,
    api_key: str,
    servers: list,
    state: dict,
):
    key_preview = api_key[:4] + "..." + api_key[-4:] if len(api_key) >= 8 else api_key
    w_state = state["worker_states"][worker_id]
    w_state["status"] = "Running"
    server_idx = (worker_id - 1) % len(servers)

    print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] Started with Key: {key_preview} on servers: {servers}")

    while state.get("hunting") and not state.get("stop_flag"):
        # Check target limit before buying a new number
        target_limit = state.get("target_limit", 0)
        if target_limit > 0 and state.get("accounts_created", 0) >= target_limit:
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] 🎯 Target limit of {target_limit} reached! Worker not buying new numbers.")
            break

        w_state["attempts"] += 1
        state["attempts"] += 1
        att_num = w_state["attempts"]
        srv_desc = ", ".join(f"Server {s}" for s in servers)
        if len(servers) > 1:
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] Attempt #{att_num}: ⚡ Racing [{srv_desc}] concurrently (Key {key_preview})...")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] Attempt #{att_num}: Buying number from Server {servers[0]} (Key {key_preview})...")

        res = await otpd_buy_multi_server_race(client, api_key, servers)
        current_server = res.get("server_id", servers[0])

        if not res.get("ok"):
            err = res.get("error", "Unknown error")
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] Buy error on [{srv_desc}]: {err}")

            if "NO_BALANCE" in err:
                w_state["status"] = "Waiting Refund"
                print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ⏳ Low balance ({srv_desc}, Key {key_preview}). Waiting for background cancel refund...")
                refund_done = False
                for _ in range(5):
                    if state.get("stop_flag") or not state.get("hunting"):
                        break
                    await asyncio.sleep(60)
                    new_bal = await otpd_balance(client, api_key)
                    try:
                        if float(new_bal) >= 9.0:
                            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ✅ Refund received! New Balance: ₹{new_bal}. Resuming hunt silently...")
                            w_state["status"] = "Running"
                            refund_done = True
                            break
                    except ValueError:
                        pass
                if not refund_done:
                    w_state["status"] = "Paused (No Balance)"
                    await send_tg_message(
                        client,
                        chat_id,
                        f"❌ <b>Worker #{worker_id} Paused!</b> Key <code>{key_preview}</code> balance insufficient (>5 min wait). Baaki workers chalte rahenge.",
                    )
                    break
                continue

            if "NO_NUMBERS" in err or "TRY_AGAIN" in err:
                await asyncio.sleep(1.0)
                continue

            await asyncio.sleep(1.2)
            continue

        act_id = res["id"]
        phone = res["phone"]
        w_state["active_id"] = act_id
        cur_bal = await otpd_balance(client, api_key)
        await record_transaction("NUMBER_BOUGHT", phone, worker_id, current_server, cur_bal, f"Key: {key_preview} (Race Win)")
        print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ⚡ Server {current_server} won! Got number: {phone} (ID: {act_id}, Bal: ₹{cur_bal}) — checking registration...")

        chk = await check_meesho_reg(client, phone, chat_id=chat_id)
        if not chk.get("ok"):
            await asyncio.sleep(1.0)
            chk = await check_meesho_reg(client, phone, chat_id=chat_id)

        if not chk.get("ok"):
            err_detail = chk.get("error", "Both checker endpoints down")
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] 🚨 Checker failed: {err_detail}. Queued cancel for {phone}...")
            cur_bal = await otpd_balance(client, api_key)
            w_state["balance"] = parse_balance_float(cur_bal)
            await record_transaction("CHECKER_FAIL_CANCEL", phone, worker_id, current_server, cur_bal, err_detail)
            await otpd_cancel(client, api_key, act_id, phone=phone, initial_delay=180, state=state, w_state=w_state)
            w_state["active_id"] = None
            await asyncio.sleep(1.0)
            continue

        is_reg = chk.get("registered")

        # ── Registered (Old User) → 3 min delayed cancel with 1 min retry, worker continues hunting! ──
        if is_reg is True:
            w_state["registered"] += 1
            state["registered_count"] += 1
            cur_bal = await otpd_balance(client, api_key)
            w_state["balance"] = parse_balance_float(cur_bal)
            await record_transaction("NUMBER_CANCEL_QUEUED", phone, worker_id, current_server, cur_bal, "Registered/Old User")
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] Number {phone} is REGISTERED. Queued 3-min cancel with 1-min retry...")
            await otpd_cancel(client, api_key, act_id, phone=phone, initial_delay=180, state=state, w_state=w_state)
            w_state["active_id"] = None
            await asyncio.sleep(1.0)
            continue

        # ── FRESH / UNREGISTERED NUMBER FOUND! ──
        print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] 🎉 FRESH NUMBER FOUND: {phone} (Server: {current_server}) — Starting OTP login...")

        fresh_alert_msg = (
            f"🎉 <b>FRESH UNREGISTERED NUMBER FOUND!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>Mobile:</b> <code>+91{phone}</code>\n"
            f"⚡ <b>Worker:</b> <code>Worker #{worker_id}</code> (Key: <code>{key_preview}</code>)\n"
            f"🏷️ <b>Server:</b> <code>Server {current_server}</code>\n"
            f"📩 <b>Action:</b> Meesho Official OTP bheja jaa raha hai (Max wait: 2 mins)..."
        )
        await send_tg_message(client, chat_id, fresh_alert_msg)

        dev = mk_device()
        otp_res = await send_meesho_otp(client, phone, dev, chat_id=chat_id, worker_id=worker_id, server=current_server)
        if not otp_res.get("ok"):
            err_str = otp_res.get("error", "Failed")
            w_state["failed"] = w_state.get("failed", 0) + 1
            state["failed_creations"] = state.get("failed_creations", 0) + 1
            await record_failed_account(phone, worker_id, current_server, key_preview, f"OTP Send Failed: {err_str}")
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ❌ OTP send failed: {err_str}. Queued cancel for refund...")
            cur_bal = await otpd_balance(client, api_key)
            w_state["balance"] = parse_balance_float(cur_bal)
            await record_transaction("OTP_SEND_FAIL_CANCEL", phone, worker_id, current_server, cur_bal, err_str)
            await send_tg_message(
                client,
                chat_id,
                f"❌ <b>[Account Creation Failed — OTP Dispatch]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>Mobile:</b> <code>+91{phone}</code> (Worker #{worker_id} | Key: <code>{key_preview}</code>)\n"
                f"⚠️ <b>Reason:</b> <code>{err_str}</code>\n"
                f"📊 <b>Worker #{worker_id}:</b> {w_state.get('accounts', 0)} Created | {w_state.get('crowstack_rejects', 0)} Crowstack Reject | {w_state.get('timeout_fails', 0)} Timeout Fail | Bal: ₹{cur_bal}\n"
                f"📊 <b>Total Failed in Session:</b> <b>{state.get('failed_creations', 0)}</b>\n"
                f"🔄 Number cancel & refund queued.",
            )
            await otpd_cancel(client, api_key, act_id, phone=phone, initial_delay=0, state=state, w_state=w_state)
            w_state["active_id"] = None
            await asyncio.sleep(1.0)
            continue

        session_dict = otp_res["session"]
        print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ⏳ OTP sent to {phone}! Waiting for SMS (max 2 mins)...")

        # Poll OTP Doctor for incoming SMS (Max 2 minutes = 120 seconds)
        otp_code = None
        sms_text = ""
        start_wait = time.time()

        while (time.time() - start_wait) < 120:
            if state.get("stop_flag") or not state.get("hunting"):
                await otpd_cancel(client, api_key, act_id, phone=phone, initial_delay=0, state=state, w_state=w_state)
                w_state["active_id"] = None
                return

            sms_res = await otpd_get_sms(client, api_key, act_id)
            if sms_res.get("ok"):
                sms_text = sms_res.get("sms", "")
                digits = re.findall(r"\b\d{4,6}\b", sms_text)
                if digits:
                    otp_code = digits[0]
                    print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] 🔑 Extracted OTP: {otp_code}")
                    await send_tg_message(
                        client,
                        chat_id,
                        f"🔑 <b>[OTP Doctor SMS Aaya!]</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 <b>Mobile:</b> <code>+91{phone}</code> (Worker #{worker_id})\n"
                        f"🔢 <b>OTP:</b> <code>{otp_code}</code>\n"
                        f"📩 <b>SMS:</b> <code>{sms_text}</code>\n"
                        f"⚡ <i>Ab Crowstack login verify call ki jaa rahi hai...</i>",
                    )
                    break
            await asyncio.sleep(0.3)

        if not otp_code:
            w_state["failed"] = w_state.get("failed", 0) + 1
            w_state["timeout_fails"] = w_state.get("timeout_fails", 0) + 1
            state["failed_creations"] = state.get("failed_creations", 0) + 1
            state["failed_sms_timeout"] = state.get("failed_sms_timeout", 0) + 1
            await record_failed_account(phone, worker_id, current_server, key_preview, "SMS Timeout (2 Mins Elapsed)")
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ⏰ SMS Timeout for {phone} (2 mins elapsed). Sending cancel request...")
            cur_bal = await otpd_balance(client, api_key)
            w_state["balance"] = parse_balance_float(cur_bal)
            await record_transaction("SMS_TIMEOUT_CANCEL", phone, worker_id, current_server, cur_bal, "2-min Timeout")
            await send_tg_message(
                client,
                chat_id,
                f"⏰ <b>[Account Creation Failed — SMS Timeout]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>Mobile:</b> <code>+91{phone}</code> (Worker #{worker_id} | Key: <code>{key_preview}</code>)\n"
                f"⚠️ <b>Reason:</b> OTP Doctor se 2 min me SMS nahi aaya.\n"
                f"📊 <b>Worker #{worker_id}:</b> {w_state.get('accounts', 0)} Created | {w_state.get('crowstack_rejects', 0)} Crowstack Reject | {w_state.get('timeout_fails', 0)} Timeout Fail | Bal: ₹{cur_bal}\n"
                f"📊 <b>Session Failures:</b> Total: <b>{state.get('failed_creations', 0)}</b> | ⏰ SMS Timeout: <b>{state.get('failed_sms_timeout', 0)}</b>\n"
                f"🔄 Number cancel & refund queued.",
            )
            await otpd_cancel(client, api_key, act_id, phone=phone, initial_delay=0, state=state, w_state=w_state)
            w_state["active_id"] = None
            await asyncio.sleep(1.0)
            continue

        # Verify OTP & Login to Meesho (Complete in-flight account even if target reached)
        print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] 🔐 Verifying OTP {otp_code} for {phone}...")
        login_res = await verify_meesho_otp(client, phone, otp_code, session_dict, dev, chat_id=chat_id)

        if login_res.get("ok"):
            # Reset consecutive Crowstack reject counter on successful account creation
            state["consecutive_crowstack_rejects"] = 0
            w_state["accounts"] += 1
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

            # Record in Master Account Summary File, Audit Log & DB
            cur_bal = await otpd_balance(client, api_key)
            w_state["balance"] = parse_balance_float(cur_bal)
            await record_transaction("ACCOUNT_CREATED", phone, worker_id, current_server, cur_bal, f"UID: {user_id}")
            await record_created_account(phone, user_id, current_server, worker_id, key_preview, fname)

            # Calculate today's index & stats
            history = load_accounts_history()
            today_prefix = time.strftime("%Y-%m-%d")
            today_count = sum(1 for x in history if x.get("created_at", "").startswith(today_prefix))

            def ordinal(n):
                if 11 <= (n % 100) <= 13:
                    return f"{n}th"
                return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

            today_ordinal = ordinal(today_count)
            lifetime_total = len(history)

            # Sync to TelegramBotSell Store Stock
            sync_res = sync_to_sell_store(account_data, phone)
            store_tag = f"\n🛒 <b>Auto-Stocked in Sell Bot:</b> ✅ Live (Total Stock: {sync_res.get('stock', 1)})" if sync_res.get("ok") else ""

            target_limit = state.get("target_limit", 0)
            target_info = f" | 🎯 Target: <b>{state['accounts_created']}/{target_limit}</b>" if target_limit > 0 else ""

            # Key balance & performance insight
            key_bal_f = parse_balance_float(cur_bal)
            key_acc_cnt = w_state.get("accounts", 0)
            key_fail_cnt = w_state.get("failed", 0)
            if key_bal_f < 20.0:
                key_bal_alert = f"\n⚠️ <b>Key Balance Alert:</b> ₹{key_bal_f:.2f} bacha hai! (Is key se accounts ban rahe hain, please top up karein!)"
            else:
                key_bal_alert = f"\n💳 <b>Key Balance:</b> ₹{key_bal_f:.2f}"

            account_msg = (
                f"✨━━━━━━━━━━━━━━━━━━━━━━━━━✨\n"
                f"🎉 <b>MEESHO ACCOUNT CREATED SUCCESSFULLY!</b>\n"
                f"🏆 <b>Aaj Ka {today_ordinal} Fresh Account!</b> (Date: <code>{today_prefix}</code>)\n"
                f"✨━━━━━━━━━━━━━━━━━━━━━━━━━✨\n\n"
                f"📱 <b>Mobile Number:</b> <code>+91 {phone}</code>\n"
                f"👤 <b>Meesho User ID:</b> <code>{user_id}</code>\n"
                f"⚡ <b>Mined By:</b> <code>Worker #{worker_id}</code> (Key: <code>{key_preview}</code>)\n"
                f"🔑 <b>Key Performance:</b> <b>{key_acc_cnt} Created</b> | {key_fail_cnt} Failed{key_bal_alert}\n"
                f"🏷️ <b>Server:</b> <code>Server {current_server}</code>\n"
                f"📊 <b>Stats:</b> Today's: <b>#{today_count}</b> | Lifetime: <b>#{lifetime_total}</b>{target_info}{store_tag}\n"
                f"✨━━━━━━━━━━━━━━━━━━━━━━━━━✨\n"
                f"📁 <i>Official JSON file <code>meesho_{phone}.json</code> niche attach ki gayi hai.</i>"
            )
            await send_tg_message(client, chat_id, account_msg)

            await send_tg_document(
                client,
                chat_id,
                filename=f"meesho_{phone}.json",
                content=json_str,
                caption=f"✅ Meesho Account (+91{phone}) — Aaj Ka #{today_count} Account | Worker #{worker_id}",
            )

            # Check if target reached
            if target_limit > 0 and state.get("accounts_created", 0) >= target_limit:
                state["target_reached"] = True
                print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] 🎯 Target limit ({target_limit}) reached! Signalling safe exit.")

            w_state["active_id"] = None
        else:
            err_msg = login_res.get("error", "Login failed")
            w_state["failed"] = w_state.get("failed", 0) + 1
            w_state["crowstack_rejects"] = w_state.get("crowstack_rejects", 0) + 1
            state["failed_creations"] = state.get("failed_creations", 0) + 1
            state["failed_crowstack_verify"] = state.get("failed_crowstack_verify", 0) + 1
            state["consecutive_crowstack_rejects"] = state.get("consecutive_crowstack_rejects", 0) + 1
            consec = state["consecutive_crowstack_rejects"]

            await record_failed_account(phone, worker_id, current_server, key_preview, f"Crowstack Verify Rejected: {err_msg}")
            print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] ❌ Crowstack verify failed: {err_msg} (Consecutive: {consec}/3). Queued cancel...")
            cur_bal = await otpd_balance(client, api_key)
            w_state["balance"] = parse_balance_float(cur_bal)
            await record_transaction("LOGIN_FAILED_CANCEL", phone, worker_id, current_server, cur_bal, err_msg)
            await send_tg_message(
                client,
                chat_id,
                f"❌ <b>[Account Creation Failed — Crowstack Verify Rejected]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>Mobile:</b> <code>+91{phone}</code> (Worker #{worker_id} | Key: <code>{key_preview}</code>)\n"
                f"⚠️ <b>Reason:</b> <code>{err_msg}</code>\n"
                f"📊 <b>Worker #{worker_id}:</b> {w_state.get('accounts', 0)} Created | {w_state.get('crowstack_rejects', 0)} Crowstack Reject | {w_state.get('timeout_fails', 0)} Timeout Fail | Bal: ₹{cur_bal}\n"
                f"📊 <b>Session Failures:</b> Total: <b>{state.get('failed_creations', 0)}</b> | 🦅 Verify Rejected: <b>{state.get('failed_crowstack_verify', 0)}</b>\n"
                f"⚠️ <b>Consecutive Rejects:</b> <b>{consec}/3</b>\n"
                f"🔄 Number cancel & refund queued.",
            )
            await otpd_cancel(client, api_key, act_id, phone=phone, initial_delay=0, state=state, w_state=w_state)
            w_state["active_id"] = None

            # Auto-Stop Trigger if 3 consecutive Crowstack rejections occur
            if consec >= 3:
                print(f"[{time.strftime('%H:%M:%S')}] 🛑 [SAFETY TRIGGER] Crowstack verify rejected {consec} times consecutively! Stopping hunt...")
                state["stop_flag"] = True
                state["hunting"] = False
                safety_alert = (
                    "🛑 <b>AUTOMATIC SAFETY STOP TRIGGERED!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ <b>Crowstack Verify lagatar {consec} baar REJECT ho gaya!</b>\n"
                    "💸 OTP Doctor balance aur numbers waste hone se bachane ke liye bot ne hunting turant <b>STOP</b> kar di hai.\n\n"
                    "🔍 <b>Likely Reason:</b>\n"
                    "• Crowstack session expire ho gaya ya token invalid ho gaya hai\n"
                    "• Crowstack server verification requests block kar raha hai\n\n"
                    "👉 <i>Kripya <code>/profiles</code> se session update karein ya naya session token paste karke dobara /hunt chalayein.</i>"
                )
                await send_tg_message(client, chat_id, safety_alert, reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                break

        await asyncio.sleep(1.0)

    # Clean up on worker exit
    act_id = w_state.get("active_id")
    if act_id:
        await otpd_cancel(client, api_key, act_id, initial_delay=0, state=state, w_state=w_state)
        w_state["active_id"] = None
    w_state["status"] = "Stopped"
    print(f"[{time.strftime('%H:%M:%S')}] [Worker #{worker_id}] Exited cleanly.")


# ─── Dual Server Multi-Key Hunter Task ────────────────────────────────────────
async def run_multi_hunter_task(client: httpx.AsyncClient, chat_id: int | str, target_limit: int = None):
    state = ACTIVE_TASKS.get(chat_id)
    if not state or not state["hunting"]:
        return

    keys = get_user_api_keys(chat_id)
    if not keys:
        state["hunting"] = False
        await send_tg_message(
            client,
            chat_id,
            "⚠️ <b>OTP Doctor API Key Required!</b>\n\n"
            "Aapne abhi tak koi API Key add nahi kiya hai.\n"
            "👉 Kripya <b>🔑 Manage Keys</b> button dabayein ya <code>/addkey &lt;your_key&gt;</code> bhejein.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    cfg = get_user_config(chat_id)
    servers = cfg.get("selected_servers", ["5841"])
    if not servers:
        servers = ["5841"]
        update_user_config(chat_id, {"selected_servers": servers})

    servers = servers[:5]
    server_names = ", ".join(f"Server {s}" for s in servers)
    server_mode_tag = " ⚡ (Parallel Fast Race Mode)" if len(servers) > 1 else ""

    if target_limit is None:
        target_limit = int(cfg.get("target_limit", 0))

    state["target_limit"] = target_limit
    state["target_reached"] = False
    state["attempts"] = 0
    state["registered_count"] = 0
    state["accounts_created"] = 0
    state["failed_creations"] = 0
    state["failed_sms_timeout"] = 0
    state["failed_crowstack_verify"] = 0
    state["consecutive_crowstack_rejects"] = 0
    state["pending_cancels"] = 0
    state["start_time"] = time.time()
    state["worker_states"] = {}
    state["stop_flag"] = False

    engine = cfg.get("api_engine", "crowstack")
    tier = int(cfg.get("cupponhub_tier", 200))
    engine_names = {
        "cupponhub": f"🛍️ Cupponhub (Tier: ₹{tier} OFF)",
        "crowstack": "🦅 Crowstack (Rem/Marin Failover)",
        "gemixai": "⚡ GemixAI (₹200 Reroll)",
        "hidenfree": "📦 Hidenfree",
        "auto": f"🔄 Auto-Failover (Cupponhub ₹{tier} ➔ Crowstack ➔ GemixAI)",
    }
    engine_label = engine_names.get(engine, engine)

    # Parallel balance fetch for fast instant startup (even with 300+ keys)
    bal_map = await fetch_all_key_balances(client, keys, max_concurrency=30)
    key_lines = []
    total_bal = 0.0
    for idx, key in enumerate(keys, start=1):
        bal = bal_map.get(key, "0.00")
        try:
            total_bal += float(bal)
        except ValueError:
            pass
        masked = key[:4] + "..." + key[-4:] if len(key) >= 8 else key
        if idx <= 6:
            key_lines.append(f"• <b>Worker #{idx}:</b> <code>{masked}</code> (₹{bal})")
        state["worker_states"][idx] = {
            "active_id": None,
            "attempts": 0,
            "accounts": 0,
            "registered": 0,
            "failed": 0,
            "timeout_fails": 0,
            "crowstack_rejects": 0,
            "pending_cancels": 0,
            "status": "Starting",
            "key_preview": masked,
            "api_key": key,
            "balance": parse_balance_float(bal),
        }

    if target_limit > 0:
        est_cost = target_limit * 12.0
        buffer_val = total_bal - est_cost
        buf_tag = f"+₹{buffer_val:.2f} ✅ (Balance Sufficient)" if buffer_val >= 0 else f"-₹{abs(buffer_val):.2f} ⚠️ (Deficit/Shortfall)"
        limit_label = (
            f"🎯 <b>Target Limit:</b> <b>{target_limit} Accounts (Auto-Stop)</b>\n"
            f"💰 <b>Smart Budget:</b> Est. ~₹{est_cost:.2f} (@ ₹12/acc) | Buffer: <b>{buf_tag}</b>\n"
        )
    else:
        limit_label = "🎯 <b>Target Limit:</b> ♾️ Continuous Unlimited\n"

    if len(keys) > 6:
        key_lines.append(f"<i>... aur {len(keys)-6} workers background me ready hain.</i>")

    keys_str = "\n".join(key_lines)
    await send_tg_message(
        client,
        chat_id,
        f"🎯 <b>Multi-Key Concurrent Hunting Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Creator Engine:</b> <code>{engine_label}</code>\n"
        f"{limit_label}"
        f"⚡ <b>Active Concurrent Workers:</b> <b>{len(keys)} Parallel Workers</b>\n"
        f"💵 <b>Total Combined Wallet:</b> <b>₹{total_bal:.2f}</b>\n"
        f"🏷️ <b>Selected Servers:</b> <code>{server_names}</code>{server_mode_tag}\n\n"
        f"🔑 <b>Configured API Keys:</b>\n{keys_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>📊 Live stats: <b>/stats</b> | 📋 Summary: <b>/summary</b> | 🛑 Stop: <b>/stop</b></i>",
    )

    worker_tasks = []
    for idx, key in enumerate(keys, start=1):
        t = asyncio.create_task(
            run_single_key_worker(client, chat_id, idx, key, servers, state)
        )
        worker_tasks.append(t)
        if idx % 10 == 0:
            await asyncio.sleep(0.05)

    # Wait for all workers to finish
    if worker_tasks:
        await asyncio.gather(*worker_tasks, return_exceptions=True)

    state["hunting"] = False
    state["active_id"] = None
    total_time_mins = int((time.time() - state.get("start_time", time.time())) // 60)

    # Final summary of workers
    final_bal_map = await fetch_all_key_balances(client, keys, max_concurrency=30)
    final_worker_lines = []
    for idx, key in enumerate(keys[:8], start=1):
        w_st = state["worker_states"].get(idx, {})
        w_bal = final_bal_map.get(key, "0.00")
        final_worker_lines.append(
            f"• <b>Worker #{idx} ({w_st.get('key_preview', '')}):</b> {w_st.get('attempts', 0)} att | {w_st.get('accounts', 0)} created | {w_st.get('failed', 0)} failed | Bal: ₹{w_bal}"
        )
    if len(keys) > 8:
        final_worker_lines.append(f"<i>... aur {len(keys)-8} workers ki detail report /summary me dekhein.</i>")
    w_summary = "\n".join(final_worker_lines)

    if state.get("target_reached"):
        banner_title = f"🎯 <b>TARGET LIMIT REACHED ({state.get('accounts_created', 0)} / {target_limit})!</b>"
        banner_sub = f"🎉 <b>Target ke anusaar {state.get('accounts_created', 0)} accounts successfully create ho gaye aur bot safely stop ho gaya.</b>\n"
    else:
        banner_title = "🏁 <b>Hunting Session Stopped!</b>"
        banner_sub = ""

    await send_tg_message(
        client,
        chat_id,
        f"{banner_title}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{banner_sub}"
        f"⏱️ <b>Total Runtime:</b> {total_time_mins} minutes\n"
        f"🔄 <b>Total Combined Attempts:</b> {state.get('attempts', 0)}\n"
        f"❌ <b>Registered Cancelled:</b> {state.get('registered_count', 0)}\n"
        f"🎉 <b>Total Accounts Created:</b> <b>{state.get('accounts_created', 0)}</b>\n"
        f"⚠️ <b>Total Failed Creations:</b> <b>{state.get('failed_creations', 0)}</b>\n\n"
        f"📊 <b>Per-Worker Performance:</b>\n{w_summary}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Summary report dekhne ke liye <b>/summary</b> dabayein.\nDobara chalane ke liye <b>🚀 Start Hunt</b>.</i>",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


# ─── Manual Number Check & Login Handlers ─────────────────────────────────────
async def handle_manual_number_check(client: httpx.AsyncClient, chat_id: int | str, state: dict, phone: str):
    phone = clean_phone(phone)
    if len(phone) != 10 or phone[0] not in "6789":
        await send_tg_message(client, chat_id, "❌ Kripya valid 10-digit Indian mobile number bhejein (jaise: <code>9876543210</code>).")
        return

    await send_tg_message(client, chat_id, f"🔍 Checking <code>+91{phone}</code> on Meesho...")
    chk = await check_meesho_reg(client, phone, chat_id=chat_id)
    if not chk["ok"]:
        await asyncio.sleep(1)
        chk = await check_meesho_reg(client, phone, chat_id=chat_id)

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

        # Calculate today's index & stats
        history = load_accounts_history()
        today_prefix = time.strftime("%Y-%m-%d")
        today_count = sum(1 for x in history if x.get("created_at", "").startswith(today_prefix))

        def ordinal(n):
            if 11 <= (n % 100) <= 13:
                return f"{n}th"
            return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

        today_ordinal = ordinal(today_count)
        lifetime_total = len(history)

        account_msg = (
            f"✨━━━━━━━━━━━━━━━━━━━━━━━━━✨\n"
            f"🎉 <b>MEESHO ACCOUNT CREATED SUCCESSFULLY!</b>\n"
            f"🏆 <b>Aaj Ka {today_ordinal} Fresh Account!</b> (Date: <code>{today_prefix}</code>)\n"
            f"✨━━━━━━━━━━━━━━━━━━━━━━━━━✨\n\n"
            f"📱 <b>Mobile Number:</b> <code>+91 {phone}</code>\n"
            f"👤 <b>Meesho User ID:</b> <code>{user_id}</code>\n"
            f"🏷️ <b>Account Type:</b> {'Old User (Existing)' if is_reg else 'Fresh Unregistered'}{store_tag}\n"
            f"📊 <b>Stats:</b> Today's: <b>#{today_count}</b> | Lifetime Total: <b>#{lifetime_total}</b>\n"
            f"✨━━━━━━━━━━━━━━━━━━━━━━━━━✨\n"
            f"📁 <i>Official JSON file <code>meesho_{phone}.json</code> niche attach ki gayi hai.</i>"
        )
        await send_tg_message(client, chat_id, account_msg, reply_markup=MAIN_MENU_KEYBOARD)

        await send_tg_document(
            client,
            chat_id,
            filename=f"meesho_{phone}.json",
            content=json_str,
            caption=f"✅ Meesho Account (+91{phone}) — Aaj Ka #{today_count} JSON",
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
    print(f"[{time.strftime('%H:%M:%S')}] 🤖 Multi-Server Meesho Bot Started! (@BotFather verified)", flush=True)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            del_res = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
                json={"drop_pending_updates": False},
                timeout=10,
            )
            print(f"[{time.strftime('%H:%M:%S')}] [Telegram Webhook] Deleted: {del_res.json()}", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [Telegram Webhook Warning] {e}", flush=True)

        offset = 0

        while True:
            try:
                r = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                    json={
                        "offset": offset,
                        "timeout": 10,
                        "allowed_updates": ["message", "callback_query"],
                    },
                    timeout=20.0,
                )
                if r.status_code != 200:
                    print(f"[{time.strftime('%H:%M:%S')}] [TG Polling Warning] HTTP {r.status_code}: {r.text[:200]}", flush=True)
                    await asyncio.sleep(2)
                    continue

                data = r.json()
                if not data.get("ok"):
                    print(f"[{time.strftime('%H:%M:%S')}] [TG getUpdates Error] {data.get('description')}", flush=True)
                    await asyncio.sleep(3)
                    continue

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
                        register_user_activity(cb_user_id, cb_from.get("username", ""), cb_from.get("first_name", ""))
                        print(f"[{time.strftime('%H:%M:%S')}] [TG Callback] user={cb_user_id} data={cb_data}", flush=True)

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

                            ord_item["status"] = "PAID_APPROVED"
                            ord_item["approved_at"] = time.time()
                            save_order(ord_item)

                            buyer_id = str(ord_item.get("user_id"))
                            await answer_tg_callback(client, cb_id, f"✅ Order #{order_id} Payment Verified!")
                            await send_tg_message(
                                client,
                                buyer_id,
                                f"✅ <b>PAYMENT VERIFIED BY ADMIN!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
                                f"⚡ <b>Status:</b> <code>Payment Verified — Start Making Account!</code>\n\n"
                                f"🔍 <i>Hamara automated server fresh number search aur session generation initiate kar raha hai...</i>\n"
                                f"⏳ <i>Kripya thoda intezaar karein, jaise hi JSON generate hoga aapko deliver ho jayega!</i>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━",
                                reply_markup=USER_MAIN_MENU_KEYBOARD,
                            )
                            admin_paid_kb = {
                                "inline_keyboard": [
                                    [{"text": f"📤 Deliver JSON to User", "callback_data": f"deliver_custom_{order_id}"}],
                                    [{"text": f"🚀 Launch Auto-Hunt for #{order_id}", "callback_data": f"hunt_ord_{order_id}"}],
                                    [{"text": f"👥 View All Paid Users", "callback_data": "view_paid_users"}]
                                ]
                            }
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"✅ <b>Order #{order_id} Payment Verified!</b>\n\n"
                                f"👤 <b>Buyer:</b> <code>{buyer_id}</code> (@{ord_item.get('username') or 'N/A'})\n"
                                f"💰 <b>Amount:</b> ₹{ord_item.get('amount')}\n"
                                f"📦 <b>Type:</b> {ord_item.get('order_type', 'Standard')}\n\n"
                                f"👉 User ko notification chali gayi hai: <i>'Payment verified, start making account'</i>.\n"
                                f"Aap niche button se user ko JSON deliver kar sakte hain ya auto-hunt shuru kar sakte hain.",
                                reply_markup=admin_paid_kb,
                            )
                            continue

                        # ── Admin Launch Auto-Hunt for Order Callback ──
                        elif cb_data.startswith("hunt_ord_"):
                            order_id = cb_data.replace("hunt_ord_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id, f"🚀 Auto-Hunt started for #{order_id}!")
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

                        # ── Admin Deliver Mined JSON to Buyer Callback (with Realistic Simulation) ──
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

                            await answer_tg_callback(client, cb_id, f"🚀 Delivering to #{order_id} with realistic simulation...")
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🚀 <b>Delivery Started for Order #{order_id}!</b>\n\nUser <code>{buyer_id}</code> ko realistic progress updates ke sath JSON deliver kiya jaa raha hai...",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                            asyncio.create_task(
                                deliver_json_with_simulation(
                                    client,
                                    buyer_id,
                                    order_id,
                                    content=mined_json,
                                    filename=f"meesho_{mined_phone}.json",
                                    phone_hint=mined_phone,
                                    admin_notify_id=cb_chat_id,
                                )
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

                        # ── Admin View Paid Users Queue Callback ──
                        elif cb_data == "view_paid_users":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id, "🔄 Updating orders...")
                            text_view, kb_view = build_paid_orders_view_message_and_markup()
                            await send_tg_message(client, cb_chat_id, text_view, reply_markup=kb_view)
                            continue

                        # ── Buyer Choose Account Type: Standard (₹20) ──
                        elif cb_data == "order_type_standard":
                            std_price = get_store_price()
                            await answer_tg_callback(client, cb_id)
                            qty_prompt = (
                                f"⚡ <b>STANDARD FRESH MEESHO ACCOUNTS</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"Kripya accounts ki quantity select karein:\n\n"
                                f"📌 <b>Order Limits:</b>\n"
                                f"• <b>Minimum Order:</b> 1 Account\n"
                                f"• <b>Maximum Limit:</b> 20 Accounts / Order\n"
                                f"• <b>Price:</b> ₹{std_price} / Account (OTP Number)\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👇 <i>Quantity choose karein ya custom number likhein:</i>"
                            )
                            qty_kb = {
                                "inline_keyboard": [
                                    [
                                        {"text": f"1 Acc (₹{1 * std_price})", "callback_data": "std_qty_1"},
                                        {"text": f"2 Accs (₹{2 * std_price})", "callback_data": "std_qty_2"},
                                        {"text": f"5 Accs (₹{5 * std_price})", "callback_data": "std_qty_5"},
                                    ],
                                    [
                                        {"text": f"10 Accs (₹{10 * std_price})", "callback_data": "std_qty_10"},
                                        {"text": f"20 Accs (₹{20 * std_price})", "callback_data": "std_qty_20"},
                                    ],
                                    [
                                        {"text": "✏️ Enter Custom Quantity (1-20)", "callback_data": "std_qty_custom"},
                                    ],
                                    [
                                        {"text": "❌ Cancel", "callback_data": "cancel_buy_selection"},
                                    ]
                                ]
                            }
                            await send_tg_message(client, cb_chat_id, qty_prompt, reply_markup=qty_kb)
                            continue

                        # ── Standard Account Quantity Selected (Buttons) ──
                        elif cb_data.startswith("std_qty_"):
                            std_price = get_store_price()
                            q_param = cb_data.replace("std_qty_", "").strip()
                            if q_param == "custom":
                                st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                                st["manual_step"] = "awaiting_std_custom_qty"
                                await answer_tg_callback(client, cb_id)
                                cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                                await send_tg_message(
                                    client,
                                    cb_chat_id,
                                    f"🔢 <b>Standard Account Quantity Bhejein:</b>\n\n"
                                    f"Kitne accounts generate karwane hain? Number likhkar bhejein:\n"
                                    f"• <b>Allowed Range:</b> 1 se 20 accounts\n"
                                    f"• <b>Price:</b> ₹{std_price} / Account\n"
                                    f"<i>(Jaise: <code>3</code> ya <code>7</code> ya <code>12</code>)</i>",
                                    reply_markup=cancel_markup,
                                )
                                continue
                            elif q_param.isdigit():
                                qty = int(q_param)
                                qty = max(1, min(20, qty))
                                await answer_tg_callback(client, cb_id, f"{qty} accounts selected!")
                                await create_and_send_buyer_invoice(
                                    client,
                                    cb_chat_id,
                                    cb_user_id,
                                    cb_from.get("username", ""),
                                    cb_from.get("first_name", "User"),
                                    "Standard Fresh",
                                    qty,
                                    std_price,
                                    custom_referral_link=None,
                                )
                                continue

                        # ── Buyer Choose Account Type: Custom Referral (₹25) ──
                        elif cb_data == "order_type_custom":
                            ref_price = get_store_referral_price()
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_buyer_custom_ref"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🔗 <b>APNA MEESHO REFERRAL LINK BHEJEIN:</b>\n\n"
                                f"Aapne <b>Custom Referral Account (₹{ref_price}/acc)</b> chuna hai.\n\n"
                                f"⚠️ <b>Important Rules:</b>\n"
                                f"• Apna link use karne par <b>Minimum 5 Accounts</b> lene honge.\n"
                                f"• Maximum limit <b>20 Accounts</b> per order hai.\n\n"
                                f"👉 <i>Apna official Meesho referral link yahan paste karke bhejein:</i>\n"
                                f"<i>(Jaise: <code>https://app.meesho.com/2yoV/...</code>)</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        # ── Custom Referral Account Quantity Selected (Buttons) ──
                        elif cb_data.startswith("cust_qty_"):
                            ref_price = get_store_referral_price()
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            saved_ref = st.get("temp_custom_ref_link")
                            if not saved_ref:
                                await answer_tg_callback(client, cb_id, "⚠️ Referral link missing! Please try again.", show_alert=True)
                                continue

                            q_param = cb_data.replace("cust_qty_", "").strip()
                            if q_param == "custom":
                                st["manual_step"] = "awaiting_cust_custom_qty"
                                await answer_tg_callback(client, cb_id)
                                cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                                await send_tg_message(
                                    client,
                                    cb_chat_id,
                                    f"🔢 <b>Custom Referral Quantity Bhejein:</b>\n\n"
                                    f"Kitne accounts generate karwane hain? Number likhkar bhejein:\n"
                                    f"• <b>Minimum:</b> 5 Accounts\n"
                                    f"• <b>Maximum:</b> 20 Accounts\n"
                                    f"• <b>Price:</b> ₹{ref_price} / Account\n"
                                    f"<i>(Jaise: <code>5</code>, <code>8</code>, <code>12</code>, <code>20</code>)</i>",
                                    reply_markup=cancel_markup,
                                )
                                continue
                            elif q_param.isdigit():
                                qty = int(q_param)
                                qty = max(5, min(20, qty))
                                await answer_tg_callback(client, cb_id, f"{qty} accounts selected!")
                                await create_and_send_buyer_invoice(
                                    client,
                                    cb_chat_id,
                                    cb_user_id,
                                    cb_from.get("username", ""),
                                    cb_from.get("first_name", "User"),
                                    "Custom Referral",
                                    qty,
                                    ref_price,
                                    custom_referral_link=saved_ref,
                                )
                                continue

                        # ── Buyer Cancel Account Type Selection ──
                        elif cb_data == "cancel_buy_selection":
                            await answer_tg_callback(client, cb_id, "Cancelled.")
                            await send_tg_message(client, cb_chat_id, "❌ Selection cancel kar di gayi.", reply_markup=USER_MAIN_MENU_KEYBOARD)
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

                        elif cb_data == "add_key_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_add_key"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                "➕ <b>Naya OTP Doctor API Key bhejein:</b>\n\n<i>(OTP Doctor dashboard se copy karke yahan paste karein. Yeh key parallel worker ke roop mein add ho jayegi)</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        elif cb_data == "del_key_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            keys = get_user_api_keys(cb_chat_id)
                            if not keys:
                                await answer_tg_callback(client, cb_id, "⚠️ Koi key configured nahi hai!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_del_key"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            key_list_str = "\n".join(f"• <b>Key #{i}:</b> <code>{k[:4]}...{k[-4:]}</code>" for i, k in enumerate(keys, start=1))
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🗑️ <b>Delete API Key:</b>\n\n{key_list_str}\n\n👉 <i>Delete karne ke liye Key Number bhejein (jaise: <code>1</code> ya <code>2</code>) ya command <code>/delkey 1</code> bhejein.</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        elif cb_data == "refresh_keys":
                            await answer_tg_callback(client, cb_id, "🔄 Updating balances...")
                            keys_text, keys_kb = await build_keys_view_message_and_markup(client, cb_chat_id)
                            await send_tg_message(client, cb_chat_id, keys_text, reply_markup=keys_kb)
                            continue

                        elif cb_data == "clear_keys_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            clear_user_api_keys(cb_chat_id)
                            await answer_tg_callback(client, cb_id, "🧹 Sabhi keys clear ho gayi!")
                            keys_text, keys_kb = await build_keys_view_message_and_markup(client, cb_chat_id)
                            await send_tg_message(client, cb_chat_id, keys_text, reply_markup=keys_kb)
                            continue

                        elif cb_data == "backup_keys_action":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            keys = get_user_api_keys(cb_chat_id)
                            if not keys:
                                await answer_tg_callback(client, cb_id, "⚠️ Koi keys configured nahi hain!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id, "📥 Backup file ban rahi hai...")
                            txt_content = "\n".join(keys)
                            await send_tg_document(
                                client,
                                cb_chat_id,
                                filename=f"otpdoctor_keys_backup_{len(keys)}_keys.txt",
                                content=txt_content,
                                caption=f"🔐 <b>OTP Doctor Keys Backup:</b> <code>{len(keys)}</code> API keys exported.\n<i>(Direct backup file saved across server restarts)</i>",
                            )
                            continue

                        # ── Day-Wise & Stats Reset Callbacks ──
                        elif cb_data == "refresh_stats_view":
                            await answer_tg_callback(client, cb_id, "🔄 Updating Live Stats...")
                            st = ACTIVE_TASKS.get(cb_chat_id, {})
                            stats_text, stats_kb = await build_stats_view_message_and_markup(client, cb_chat_id, st)
                            await send_tg_message(client, cb_chat_id, stats_text, reply_markup=stats_kb)
                            continue

                        elif cb_data == "reset_session_action":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            reset_session_stats(cb_chat_id)
                            await answer_tg_callback(client, cb_id, "⚡ Active Session Stats Reset!")
                            st = ACTIVE_TASKS.get(cb_chat_id, {})
                            stats_text, stats_kb = await build_stats_view_message_and_markup(client, cb_chat_id, st)
                            await send_tg_message(client, cb_chat_id, f"✅ <b>Active Session Counters Reset!</b>\n\n{stats_text}", reply_markup=stats_kb)
                            continue

                        elif cb_data == "reset_today_action":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            del_c = await reset_today_accounts()
                            await answer_tg_callback(client, cb_id, f"📅 Today's {del_c} accounts reset!")
                            st = ACTIVE_TASKS.get(cb_chat_id, {})
                            stats_text, stats_kb = await build_stats_view_message_and_markup(client, cb_chat_id, st)
                            await send_tg_message(client, cb_chat_id, f"📅 <b>Today's accounts reset!</b> ({del_c} records cleared)\n\n{stats_text}", reply_markup=stats_kb)
                            continue

                        elif cb_data == "reset_history_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id)
                            confirm_kb = {
                                "inline_keyboard": [
                                    [
                                        {"text": "⚠️ Yes, Delete All History", "callback_data": "confirm_reset_history_action"},
                                        {"text": "❌ Cancel", "callback_data": "cancel_reset_history"},
                                    ]
                                ]
                            }
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                "⚠️ <b>CONFIRM ALL-TIME HISTORY RESET:</b>\n\nKya aap sach mein <b>sab accounts ki history delete</b> karna chahte hain?\nYeh action irreversible hai.",
                                reply_markup=confirm_kb,
                            )
                            continue

                        elif cb_data == "confirm_reset_history_action":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            del_all = await reset_all_accounts_history()
                            await answer_tg_callback(client, cb_id, f"🗑️ All {del_all} accounts deleted!")
                            st = ACTIVE_TASKS.get(cb_chat_id, {})
                            stats_text, stats_kb = await build_stats_view_message_and_markup(client, cb_chat_id, st)
                            await send_tg_message(client, cb_chat_id, f"🗑️ <b>All-Time History Cleared!</b> ({del_all} accounts removed)\n\n{stats_text}", reply_markup=stats_kb)
                            continue

                        elif cb_data == "cancel_reset_history":
                            await answer_tg_callback(client, cb_id, "Cancelled.")
                            st = ACTIVE_TASKS.get(cb_chat_id, {})
                            stats_text, stats_kb = await build_stats_view_message_and_markup(client, cb_chat_id, st)
                            await send_tg_message(client, cb_chat_id, stats_text, reply_markup=stats_kb)
                            continue

                        # ── Crowstack Failover User Choice Callbacks ──
                        elif cb_data.startswith("fb_gemix_"):
                            phone = cb_data.replace("fb_gemix_", "").strip()
                            fut = PENDING_OTP_FALLBACK_DECISIONS.get(phone)
                            if fut and not fut.done():
                                fut.set_result("gemix")
                            await answer_tg_callback(client, cb_id, "🟢 GemixAI Fallback Chosen!")
                            await send_tg_message(client, cb_chat_id, f"🟢 <b>GemixAI (₹200 OFF):</b> <code>+91{phone}</code> par ₹200 OFF reroll karke OTP send kiya jaa raha hai...")
                            continue

                        elif cb_data.startswith("fb_cancel_"):
                            phone = cb_data.replace("fb_cancel_", "").strip()
                            fut = PENDING_OTP_FALLBACK_DECISIONS.get(phone)
                            if fut and not fut.done():
                                fut.set_result("cancel")
                            await answer_tg_callback(client, cb_id, "❌ Number Cancelled (Refunded)")
                            await send_tg_message(client, cb_chat_id, f"❌ <b>Cancelled:</b> <code>+91{phone}</code> refund ke liye cancel kar diya gaya.")
                            continue

                        # ── Crowstack Identity & Session Profile Callbacks ──
                        elif cb_data == "open_identity_menu":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id)
                            id_text, id_kb = build_identity_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(client, cb_chat_id, id_text, reply_markup=id_kb)
                            continue

                        elif cb_data == "open_settings_menu":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id)
                            cur_ref = get_referral_link()
                            cur_p = get_store_price()
                            cur_upi = get_store_upi_id()
                            cur_name = get_store_upi_name()
                            prof_key = get_crowstack_profile_key(cb_chat_id)
                            prof_name = CROWSTACK_PROFILES.get(prof_key, CROWSTACK_PROFILES["new"])["name"]
                            cfg = get_user_config(cb_chat_id)
                            cur_eng = cfg.get("api_engine", "crowstack")
                            cur_tier = int(cfg.get("cupponhub_tier", 200))
                            cur_lim = int(cfg.get("target_limit", 0))
                            lim_str = f"{cur_lim} Accs" if cur_lim > 0 else "Unlimited"

                            settings_text = (
                                f"⚙️ <b>MEESHO STORE & BOT SETTINGS</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"⚡ <b>Creator Engine:</b> <code>{cur_eng.upper()} (₹{cur_tier} OFF)</code>\n"
                                f"🎯 <b>Target Limit:</b> <b>{lim_str}</b>\n"
                                f"👤 <b>Crowstack Session:</b> <code>{prof_name}</code>\n"
                                f"💰 <b>Meesho JSON Price:</b> <b>₹{cur_p}</b>\n"
                                f"📲 <b>UPI ID:</b> <code>{cur_upi}</code> (<b>{cur_name}</b>)\n"
                                f"🔗 <b>Referral Link:</b>\n<code>{cur_ref}</code>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👇 <i>Niche button dabakar koi bhi setting turant update karein:</i>"
                            )
                            settings_kb = {
                                "inline_keyboard": [
                                    [
                                        {"text": "⚡ API Engine & Target Limit", "callback_data": "open_engine_menu"},
                                    ],
                                    [
                                        {"text": "👤 Crowstack Session / Identity", "callback_data": "open_identity_menu"},
                                    ],
                                    [
                                        {"text": "⚡ Speedz Keys & Load Balancer", "callback_data": "open_speedz_menu"},
                                    ],
                                    [
                                        {"text": "➕ Add Speedz Keys (Bulk)", "callback_data": "add_speedz_prompt"},
                                        {"text": "📥 Export Speedz (.txt)", "callback_data": "export_speedz_keys"},
                                    ],
                                    [
                                        {"text": "🔗 Change Referral Link", "callback_data": "set_ref_link"},
                                    ],
                                    [
                                        {"text": "💳 Change UPI ID / Name", "callback_data": "set_upi_id"},
                                        {"text": "💰 Change Price", "callback_data": "set_price"},
                                    ]
                                ]
                            }
                            await send_tg_message(client, cb_chat_id, settings_text, reply_markup=settings_kb)
                            continue

                        elif cb_data == "open_speedz_menu":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id)
                            sp_text, sp_kb = build_speedz_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(client, cb_chat_id, sp_text, reply_markup=sp_kb)
                            continue

                        elif cb_data == "add_speedz_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_speedz_bulk"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                "⚡ <b>Speedz Checker API Keys Bhejein:</b>\n\n"
                                "👉 <i>Ek sath multiple keys paste kar sakte hain (space, comma, newline ya .txt file bhej sakte hain).\n"
                                "Example: <code>AK_xxx AK_yyy AK_zzz</code></i>\n\n"
                                "⚡ <i>Sabhi keys automatic round-robin load balancer pool me add ho jayengi!</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        elif cb_data == "export_speedz_keys":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id, "📥 Exporting Speedz Keys...")
                            await handle_export_speedz_keys(client, cb_chat_id)
                            continue

                        elif cb_data == "clear_speedz_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            update_user_config(cb_chat_id, {"speedz_keys": []})
                            save_saved_speedz_keys_global([])
                            await answer_tg_callback(client, cb_id, "🗑️ Custom Speedz keys cleared!")
                            sp_text, sp_kb = build_speedz_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(client, cb_chat_id, f"🗑️ <b>Custom Speedz Keys Cleared!</b>\n\n{sp_text}", reply_markup=sp_kb)
                            continue

                        elif cb_data == "open_engine_menu":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id)
                            eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(client, cb_chat_id, eng_text, reply_markup=eng_kb)
                            continue

                        elif cb_data.startswith("set_engine_"):
                            eng_choice = cb_data.replace("set_engine_", "").strip()
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            update_user_config(cb_chat_id, {"api_engine": eng_choice})
                            await answer_tg_callback(client, cb_id, f"✅ Engine set to {eng_choice.upper()}!")
                            eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(client, cb_chat_id, eng_text, reply_markup=eng_kb)
                            continue

                        elif cb_data.startswith("set_tier_"):
                            tier_choice = int(cb_data.replace("set_tier_", "").strip())
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            update_user_config(cb_chat_id, {"cupponhub_tier": tier_choice})
                            await answer_tg_callback(client, cb_id, f"✅ Cupponhub Tier: ₹{tier_choice} OFF!")
                            eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(client, cb_chat_id, eng_text, reply_markup=eng_kb)
                            continue

                        elif cb_data == "set_limit_prompt":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_target_limit"
                            await answer_tg_callback(client, cb_id)
                            keys_cb = get_user_api_keys(cb_chat_id)
                            bals_cb = await fetch_all_key_balances(client, keys_cb)
                            tot_bal_cb = sum(parse_balance_float(v) for v in bals_cb.values())
                            possible_cb = int(tot_bal_cb // 12) if tot_bal_cb >= 12 else 0
                            cur_lim = int(get_user_config(cb_chat_id).get("target_limit", 0))
                            cur_lim_str = f"{cur_lim} Accounts" if cur_lim > 0 else "Unlimited"

                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🎯 <b>Target Account Limit & Auto-Budgeting:</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"• <b>Current Target:</b> <code>{cur_lim_str}</code>\n"
                                f"• <b>Live Total Wallet:</b> <b>₹{tot_bal_cb:.2f}</b>\n"
                                f"• <b>Max Feasible (@ ₹12/acc):</b> <b>~{possible_cb} Accounts</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"Kitne accounts banakar bot ko auto-stop karna hai?\n"
                                f"👉 Number type karke bhejein (jaise: <code>70</code> ya <code>3</code> ya <code>0</code> for unlimited):\n\n"
                                f"<i>(Note: In-flight ban rahe accounts safe finish hoke stop honge)</i>",
                                reply_markup=cancel_markup,
                            )
                            continue

                        elif cb_data == "launch_hunt_action":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {"hunting": False, "active_id": None, "stop_flag": False})
                            if st.get("hunting"):
                                await answer_tg_callback(client, cb_id, "⚠️ Hunting already running!", show_alert=True)
                                continue
                            await answer_tg_callback(client, cb_id, "🚀 Launching Hunt...")
                            cfg_cb = get_user_config(cb_chat_id)
                            sel_servers = cfg_cb.get("selected_servers", ["5841"])
                            if not sel_servers:
                                sel_servers = ["5841"]
                                update_user_config(cb_chat_id, {"selected_servers": sel_servers})
                            st["hunting"] = True
                            st["active_id"] = None
                            st["stop_flag"] = False
                            asyncio.create_task(run_multi_hunter_task(client, cb_chat_id))
                            continue

                        elif cb_data == "set_profile_new":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            update_user_config(cb_chat_id, {"crowstack_profile": "new"})
                            await answer_tg_callback(client, cb_id, "✅ Switched to New Rem Session!")
                            id_text, id_kb = build_identity_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🎉 <b>Crowstack Session Successfully Switched!</b>\n\nAb se sabhi OTP requests aur <code>export_file</code> calls <b>Rem (#8912242607)</b> profile aur Edge headers ke sath execute hongi.\n\n{id_text}",
                                reply_markup=id_kb,
                            )
                            continue

                        elif cb_data == "set_profile_main":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            update_user_config(cb_chat_id, {"crowstack_profile": "main"})
                            await answer_tg_callback(client, cb_id, "✅ Switched to Main Marin Session!")
                            id_text, id_kb = build_identity_settings_message_and_markup(cb_chat_id)
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                f"🎉 <b>Crowstack Session Successfully Switched!</b>\n\nAb se sabhi OTP requests aur <code>export_file</code> calls <b>Marin (#8282846997)</b> main profile aur Chrome headers ke sath execute hongi.\n\n{id_text}",
                                reply_markup=id_kb,
                            )
                            continue

                        elif cb_data == "set_profile_custom":
                            if not is_admin(cb_user_id):
                                await answer_tg_callback(client, cb_id, "⛔ Admin access required!", show_alert=True)
                                continue
                            st = ACTIVE_TASKS.setdefault(cb_chat_id, {})
                            st["manual_step"] = "awaiting_custom_init_data"
                            await answer_tg_callback(client, cb_id)
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                cb_chat_id,
                                "✏️ <b>Custom Telegram X-Tg-Init-Data Token Bhejein:</b>\n\n<i>(Apna custom <code>query_id=...&user=...&hash=...</code> token string yahan paste karein)</i>",
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
                    register_user_activity(chat_id, username, first_name)
                    print(f"[{time.strftime('%H:%M:%S')}] [TG Message] chat_id={chat_id} ({first_name} @{username}) text={repr(text)}", flush=True)

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

                    # Auto-clear stuck manual_step if any standard menu button or command is clicked
                    if text in KNOWN_MENU_BUTTONS or (text.startswith("/") and not (state.get("manual_step") == "confirm_otp" and text in ("/yes", "/no"))):
                        state["manual_step"] = None
                        state["awaiting_utr_order"] = None
                        state["awaiting_custom_delivery_order"] = None
                        state["awaiting_admin_reply_user"] = None

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

                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"🚀 <b>Delivery Initiated for Order #{target_ord_id}!</b>\n\n"
                                    f"👤 <b>Buyer:</b> <code>{buyer_id}</code>\n"
                                    f"Bot user ko staged number finding & JSON creation progress dikhakar file deliver karega...",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )

                                asyncio.create_task(
                                    deliver_json_with_simulation(
                                        client,
                                        buyer_id,
                                        target_ord_id,
                                        content=content,
                                        file_bytes=file_bytes,
                                        filename=filename,
                                        admin_notify_id=chat_id,
                                    )
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
                                    ref_info = f"\n🔗 <b>Buyer's Refer Link:</b>\n<code>{order.get('custom_referral_link')}</code>" if order.get('custom_referral_link') else ""
                                    admin_alert = (
                                        f"🚨 <b>NEW MEESHO JSON PAYMENT RECEIVED!</b>\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"🆔 <b>Order ID:</b> <code>#{order['id']}</code>\n"
                                        f"👤 <b>Buyer:</b> {first_name} (@{username} | ID: <code>{chat_id}</code>)\n"
                                        f"📦 <b>Account Type:</b> {order.get('order_type', 'Standard Fresh')}{ref_info}\n"
                                        f"💰 <b>Amount:</b> ₹{order['amount']}\n"
                                        f"🔢 <b>UTR / Ref:</b> <code>{extracted_utr}</code>\n"
                                        f"📅 <b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"👇 <b>Select Action:</b>"
                                    )
                                    admin_inline_kb = {
                                        "inline_keyboard": [
                                            [
                                                {"text": "✅ Verify Payment", "callback_data": f"approve_ord_{order['id']}"},
                                                {"text": "📁 Deliver JSON", "callback_data": f"deliver_custom_{order['id']}"},
                                            ],
                                            [
                                                {"text": "🚀 Verify & Auto-Hunt", "callback_data": f"hunt_ord_{order['id']}"},
                                                {"text": "💬 Message Buyer", "callback_data": f"reply_user_{chat_id}"},
                                            ],
                                            [
                                                {"text": "❌ Reject Order", "callback_data": f"reject_ord_{order['id']}"},
                                            ]
                                        ]
                                    }
                                    await send_tg_message(client, ADMIN_CHAT_ID, admin_alert, reply_markup=admin_inline_kb)
                                continue

                        # ── Buyer /start or /help ──
                        if text.startswith("/start") or text.startswith("/help"):
                            std_p = get_store_price()
                            ref_p = get_store_referral_price()
                            welcome_text = (
                                f"🛍️ <b>WELCOME TO MEESHO JSON STORE & GENERATOR</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"⚡ <b>100% Fresh • Unregistered • High-Speed JSON Maker</b>\n\n"
                                f"💎 <b>Account Pricing:</b>\n"
                                f"• 📱 <b>Standard Fresh Account:</b> <code>₹{std_p} / Account</code> (OTP Number Cost)\n"
                                f"• 🔗 <b>Apna Meesho Referral Link:</b> <code>₹{ref_p} / Account</code> (Custom Refer Processing)\n\n"
                                f"📌 <b>Kaise Kaam Karta Hai?</b>\n"
                                f"1️⃣ Niche <b>🛍️ Buy Meesho JSON</b> par click karein.\n"
                                f"2️⃣ Account type choose karein (Standard ₹{std_p} ya Apna Refer Link ₹{ref_p}).\n"
                                f"3️⃣ QR code scan karke UPI payment karein aur 12-digit UTR submit karein.\n"
                                f"4️⃣ Admin payment verify karenge aur turant fresh number hunt start ho jayega.\n"
                                f"5️⃣ Number find hote hi OTP verify hokar ready-to-use <code>.json</code> file deliver ho jayegi!\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👇 <i>Niche diye gaye button se shuru karein:</i>"
                            )
                            await send_tg_message(client, chat_id, welcome_text, reply_markup=USER_MAIN_MENU_KEYBOARD)
                            continue

                        # ── Buyer Step: Submitting Custom Referral Link ──
                        elif state.get("manual_step") == "awaiting_buyer_custom_ref":
                            buyer_ref = text.strip()
                            if buyer_ref.startswith("http://") or buyer_ref.startswith("https://") or "meesho.com" in buyer_ref:
                                state["manual_step"] = None
                                state["temp_custom_ref_link"] = buyer_ref
                                ref_p = get_store_referral_price()

                                qty_prompt = (
                                    f"🔗 <b>MEESHO REFERRAL LINK SAVED!</b>\n"
                                    f"<code>{buyer_ref}</code>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"Ab kitne accounts generate karwane hain choose karein:\n\n"
                                    f"📌 <b>Custom Referral Rules:</b>\n"
                                    f"• <b>Minimum Order:</b> <b>5 Accounts</b> (Mandatory)\n"
                                    f"• <b>Maximum Limit:</b> <b>20 Accounts</b> / Order\n"
                                    f"• <b>Price:</b> <b>₹{ref_p} / Account</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👇 <i>Quantity choose karein ya custom number likhein:</i>"
                                )
                                qty_kb = {
                                    "inline_keyboard": [
                                        [
                                            {"text": f"5 Accs (₹{5 * ref_p})", "callback_data": "cust_qty_5"},
                                            {"text": f"10 Accs (₹{10 * ref_p})", "callback_data": "cust_qty_10"},
                                        ],
                                        [
                                            {"text": f"15 Accs (₹{15 * ref_p})", "callback_data": "cust_qty_15"},
                                            {"text": f"20 Accs (₹{20 * ref_p})", "callback_data": "cust_qty_20"},
                                        ],
                                        [
                                            {"text": "✏️ Enter Custom Quantity (5-20)", "callback_data": "cust_qty_custom"},
                                        ],
                                        [
                                            {"text": "❌ Cancel", "callback_data": "cancel_buy_selection"},
                                        ]
                                    ]
                                }
                                await send_tg_message(client, chat_id, qty_prompt, reply_markup=qty_kb)
                                continue
                            else:
                                await send_tg_message(client, chat_id, "❌ Kripya valid Meesho URL bhejein (jaise: <code>https://app.meesho.com/...</code> ya <code>/cancel</code> bhejein).")
                                continue

                        # ── Buyer Step: Submitting Custom Standard Quantity ──
                        elif state.get("manual_step") == "awaiting_std_custom_qty":
                            std_p = get_store_price()
                            if text.isdigit():
                                qty = int(text)
                                if 1 <= qty <= 20:
                                    state["manual_step"] = None
                                    await create_and_send_buyer_invoice(
                                        client,
                                        chat_id,
                                        chat_id,
                                        username,
                                        first_name,
                                        "Standard Fresh",
                                        qty,
                                        std_p,
                                        custom_referral_link=None,
                                    )
                                    continue
                                else:
                                    await send_tg_message(
                                        client,
                                        chat_id,
                                        f"⚠️ <b>Invalid Quantity:</b> Standard accounts ke liye <b>Minimum 1</b> aur <b>Maximum 20</b> accounts allow hain.\n👉 Kripya 1 se 20 ke beech number bhejein:",
                                    )
                                    continue
                            else:
                                await send_tg_message(client, chat_id, "❌ Kripya valid number bhejein (jaise: <code>3</code> ya <code>7</code> ya <code>12</code>) ya <code>/cancel</code> karein.")
                                continue

                        # ── Buyer Step: Submitting Custom Referral Quantity ──
                        elif state.get("manual_step") == "awaiting_cust_custom_qty":
                            ref_p = get_store_referral_price()
                            saved_ref = state.get("temp_custom_ref_link")
                            if text.isdigit():
                                qty = int(text)
                                if 5 <= qty <= 20:
                                    state["manual_step"] = None
                                    await create_and_send_buyer_invoice(
                                        client,
                                        chat_id,
                                        chat_id,
                                        username,
                                        first_name,
                                        "Custom Referral",
                                        qty,
                                        ref_p,
                                        custom_referral_link=saved_ref,
                                    )
                                    continue
                                else:
                                    await send_tg_message(
                                        client,
                                        chat_id,
                                        f"⚠️ <b>Quantity Restriction:</b> Custom referral link use karne par <b>Minimum 5</b> aur <b>Maximum 20</b> accounts zaroori hain!\n👉 Kripya 5 se 20 ke beech number bhejein:",
                                    )
                                    continue
                            else:
                                await send_tg_message(client, chat_id, "❌ Kripya valid number bhejein (jaise: <code>5</code>, <code>8</code>, <code>15</code>) ya <code>/cancel</code> karein.")
                                continue

                        # ── Buyer Buy Meesho JSON ──
                        elif text in ("🛍️ Buy Meesho JSON", "/buy", "buy", "Buy"):
                            std_p = get_store_price()
                            ref_p = get_store_referral_price()

                            buy_prompt = (
                                f"🛍️ <b>MEESHO FRESH JSON GENERATOR</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"Kripya account generation type select karein:\n\n"
                                f"1️⃣ <b>Standard Fresh Account — ₹{std_p}</b>\n"
                                f"• 100% Unregistered Indian OTP Number\n"
                                f"• Ready-to-use Meesho Session JSON\n\n"
                                f"2️⃣ <b>Custom Referral Account — ₹{ref_p}</b>\n"
                                f"• <b>Aapka apna Meesho referral link</b> use hoga\n"
                                f"• Referral cash & discounts directly aapke account mein add honge\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👇 <i>Niche diye gaye button par click karein:</i>"
                            )
                            buy_kb = {
                                "inline_keyboard": [
                                    [
                                        {"text": f"⚡ 1. Standard Account (₹{std_p})", "callback_data": "order_type_standard"},
                                    ],
                                    [
                                        {"text": f"🔗 2. Apna Referral Link (₹{ref_p})", "callback_data": "order_type_custom"},
                                    ],
                                    [
                                        {"text": "❌ Cancel", "callback_data": "cancel_buy_selection"},
                                    ]
                                ]
                            }
                            await send_tg_message(client, chat_id, buy_prompt, reply_markup=buy_kb)
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
                        prof_key = get_crowstack_profile_key(chat_id)
                        prof_name = CROWSTACK_PROFILES.get(prof_key, CROWSTACK_PROFILES["new"])["name"]

                        settings_text = (
                            f"⚙️ <b>MEESHO STORE & BOT SETTINGS</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 <b>Active Crowstack Session:</b> <code>{prof_name}</code>\n"
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
                                    {"text": "⚡ API Engine & Target Limit", "callback_data": "open_engine_menu"},
                                ],
                                [
                                    {"text": "👤 Crowstack Session / Identity", "callback_data": "open_identity_menu"},
                                ],
                                [
                                    {"text": "⚡ Speedz Keys & Load Balancer", "callback_data": "open_speedz_menu"},
                                ],
                                [
                                    {"text": "➕ Add Speedz Keys (Bulk)", "callback_data": "add_speedz_prompt"},
                                    {"text": "📥 Export Speedz (.txt)", "callback_data": "export_speedz_keys"},
                                ],
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

                    # ── 👤 Crowstack Session / Identity (/identity, /profile, /session) ──
                    elif text in ("👤 Switch Identity", "👤 API Session", "/identity", "/profile", "/session", "/identities"):
                        id_text, id_kb = build_identity_settings_message_and_markup(chat_id)
                        await send_tg_message(client, chat_id, id_text, reply_markup=id_kb)

                    elif text.startswith("/setprofile"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and parts[1].strip().lower() in ("new", "main", "rem", "marin"):
                            choice = "new" if parts[1].strip().lower() in ("new", "rem") else "main"
                            update_user_config(chat_id, {"crowstack_profile": choice})
                            id_text, id_kb = build_identity_settings_message_and_markup(chat_id)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Crowstack Session Switched to {choice.upper()}!</b>\n\n{id_text}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Usage: <code>/setprofile new</code> ya <code>/setprofile main</code>")

                    elif text.startswith("/setinitdata"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and "query_id" in parts[1] and "hash" in parts[1]:
                            raw_init = parts[1].strip()
                            update_user_config(chat_id, {"crowstack_profile": "custom", "crowstack_custom_init_data": raw_init})
                            id_text, id_kb = build_identity_settings_message_and_markup(chat_id)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Custom Telegram X-Tg-Init-Data Successfully Saved!</b>\n\n{id_text}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            state["manual_step"] = "awaiting_custom_init_data"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "✏️ <b>Custom Telegram X-Tg-Init-Data Token Bhejein:</b>\n\n<i>(Apna custom <code>query_id=...&user=...&hash=...</code> token string yahan paste karein)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_custom_init_data":
                        raw_init = text.strip()
                        if "query_id" in raw_init or "hash" in raw_init or "user" in raw_init:
                            update_user_config(chat_id, {"crowstack_profile": "custom", "crowstack_custom_init_data": raw_init})
                            state["manual_step"] = None
                            id_text, id_kb = build_identity_settings_message_and_markup(chat_id)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Custom Telegram Session Token Saved!</b>\n\n{id_text}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(client, chat_id, "❌ Invalid token format! Token mein <code>query_id</code>, <code>user</code> ya <code>hash</code> hona chahiye.")

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

                    # ── 📢 Broadcast Announcement (/broadcast <message> or '📢 Broadcast') ──
                    elif text.startswith("/broadcast") or text == "📢 Broadcast":
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and len(parts[1].strip()) > 0:
                            bcast_text = parts[1].strip()
                            recipients = get_all_broadcast_recipients()

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
                            state["manual_step"] = "awaiting_broadcast_message"
                            recipients = get_all_broadcast_recipients()
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                f"📢 <b>BROADCAST TO EVERY USER:</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👥 <b>Total Target Users:</b> <code>{len(recipients)}</code> users\n\n"
                                f"👉 <i>Jo announcement message sabhi users ko bhejna hai, yahan type karke bhejein:</i>\n\n"
                                f"<i>(Text, formatting, links sabhi automatically deliver honge)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_broadcast_message":
                        bcast_text = text.strip()
                        state["manual_step"] = None
                        recipients = get_all_broadcast_recipients()

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

                    # ── 👥 Paid Users / Orders (Admin) ──
                    elif text in ("👥 Paid Users / Orders", "📦 View Orders", "/orders", "/allorders", "/paidusers"):
                        text_view, kb_view = build_paid_orders_view_message_and_markup()
                        await send_tg_message(client, chat_id, text_view, reply_markup=kb_view)
                        continue

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

                    # ── 🔑 Multi-Key Management (/keys, /addkey, /addkeys, /delkey, /clearkeys, /backupkeys) ──
                    elif text in ("🔑 Manage Keys", "🔑 Set API Key", "/keys", "/managekeys"):
                        keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                        await send_tg_message(client, chat_id, keys_text, reply_markup=keys_kb)

                    # ── Bulk Add Keys (/addkeys <key1> <key2> ... or /bulkkeys) ──
                    elif text.startswith("/addkeys") or text.startswith("/bulkkeys") or text.startswith("/importkeys"):
                        raw_payload = text.split(maxsplit=1)
                        if len(raw_payload) == 2 and len(raw_payload[1].strip()) >= 8:
                            raw_keys = re.findall(r"[a-zA-Z0-9_\-]{8,128}", raw_payload[1])
                            if raw_keys:
                                added = add_user_api_keys_bulk(chat_id, raw_keys)
                                all_keys = get_user_api_keys(chat_id)
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"🎉 <b>Bulk Keys Import Complete!</b>\n\n"
                                    f"✅ <b>Added / Updated:</b> {added} keys\n"
                                    f"⚡ <b>Total Active Workers:</b> {len(all_keys)} keys\n\n"
                                    f"<i>Keys persistent JSON & memory pool mein save ho gayi hain.</i>",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            else:
                                await send_tg_message(client, chat_id, "❌ Valid API keys nahi mili format mein.")
                        else:
                            state["manual_step"] = "awaiting_bulk_keys"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "📥 <b>Bulk OTP Doctor API Keys Import:</b>\n\n"
                                "Aap apni sabhi keys (1 se lekar 500+ tak) yahan text mein paste karein (newline, space ya comma separated) ya direct <code>.txt</code> file upload karein.\n\n"
                                "Bot sabhi valid keys auto-detect karke parallel worker pool mein add kar dega.",
                                reply_markup=cancel_markup,
                            )

                    # ── Single Add Key (/addkey <key>) ──
                    elif text.startswith("/addkey"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and len(parts[1].strip()) >= 8:
                            cand_key = parts[1].strip()
                            # Check if multiple keys passed into /addkey
                            extracted = re.findall(r"[a-zA-Z0-9_\-]{8,128}", cand_key)
                            if len(extracted) > 1:
                                added = add_user_api_keys_bulk(chat_id, extracted)
                                keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"🎉 <b>Bulk Keys Added!</b> ({added} keys)\n\n{keys_text}",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            else:
                                test_bal = await otpd_balance(client, cand_key)
                                if "ACCESS_BALANCE" in test_bal or test_bal.replace(".", "", 1).isdigit():
                                    add_user_api_key(chat_id, cand_key)
                                    keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                                    await send_tg_message(
                                        client,
                                        chat_id,
                                        f"✅ <b>Naya API Key Successfully Add ho gaya!</b>\n💰 <b>Key Balance:</b> ₹{test_bal}\n\n{keys_text}",
                                        reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                    )
                                else:
                                    await send_tg_message(
                                        client,
                                        chat_id,
                                        f"❌ <b>Invalid API Key!</b> OTP Doctor error: <code>{test_bal}</code>\nKripya sahi key bhejein.",
                                        reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                    )
                        else:
                            state["manual_step"] = "awaiting_add_key"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "➕ <b>Naya OTP Doctor API Key bhejein:</b>\n<i>(OTP Doctor dashboard se copy karke yahan paste karein)</i>",
                                reply_markup=cancel_markup,
                            )

                    # ── Backup Keys (/backupkeys, /exportkeys) ──
                    elif text in ("/backupkeys", "/exportkeys", "📥 Backup Keys"):
                        keys = get_user_api_keys(chat_id)
                        if not keys:
                            await send_tg_message(client, chat_id, "⚠️ Koi keys configured nahi hain!", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            txt_content = "\n".join(keys)
                            await send_tg_document(
                                client,
                                chat_id,
                                filename=f"otpdoctor_keys_backup_{len(keys)}_keys.txt",
                                content=txt_content,
                                caption=f"🔐 <b>OTP Doctor Keys Backup:</b> <code>{len(keys)}</code> API keys exported.\n<i>(Direct backup file saved across server restarts)</i>",
                            )

                    elif text.startswith("/delkey"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2:
                            target = parts[1].strip()
                            remove_user_api_key(chat_id, target)
                            keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🗑️ <b>Key Successfully Removed!</b>\n\n{keys_text}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Usage: <code>/delkey &lt;key_number_or_string&gt;</code> (jaise: <code>/delkey 1</code>)")

                    elif text in ("/clearkeys", "/clearallkeys"):
                        clear_user_api_keys(chat_id)
                        await send_tg_message(
                            client,
                            chat_id,
                            "🧹 <b>Sabhi API Keys Clear kar di gayi hain!</b> Nayi key add karne ke liye <b>🔑 Manage Keys</b> dabayein.",
                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                        )

                    elif text.startswith("/setkey"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and len(parts[1].strip()) >= 8:
                            new_key = parts[1].strip()
                            extracted = re.findall(r"[a-zA-Z0-9_\-]{8,128}", new_key)
                            if len(extracted) > 1:
                                added = add_user_api_keys_bulk(chat_id, extracted)
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"✅ <b>Bulk API Keys Saved!</b> ({added} keys active)",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            else:
                                test_bal = await otpd_balance(client, new_key)
                                if "ACCESS_BALANCE" in test_bal or test_bal.replace(".", "", 1).isdigit():
                                    add_user_api_key(chat_id, new_key)
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
                            state["manual_step"] = "awaiting_add_key"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "🔑 <b>Apna OTP Doctor API Key bhejein:</b>\n<i>(OTP Doctor dashboard se copy karke yahan paste karein)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") in ("awaiting_add_key", "awaiting_bulk_keys"):
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
                                print(f"[Keys File Import Error] {e}")

                        cand_keys = re.findall(r"[a-zA-Z0-9_\-]{8,128}", content)
                        if len(cand_keys) > 1:
                            added = add_user_api_keys_bulk(chat_id, cand_keys)
                            state["manual_step"] = None
                            keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎉 <b>Bulk Keys Verified & Imported!</b>\n⚡ <b>Added:</b> {added} Keys\n\n{keys_text}",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        elif len(cand_keys) == 1:
                            candidate_key = cand_keys[0]
                            test_bal = await otpd_balance(client, candidate_key)
                            if "ACCESS_BALANCE" in test_bal or test_bal.replace(".", "", 1).isdigit():
                                add_user_api_key(chat_id, candidate_key)
                                state["manual_step"] = None
                                keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"🎉 <b>API Key Verified & Saved!</b>\n💰 <b>Wallet Balance:</b> ₹{test_bal}\n\n{keys_text}",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            else:
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"❌ <b>API Key Invalid!</b> Error: <code>{test_bal}</code>\nDobara sahi key bhejein ya /cancel karein.",
                                )
                        else:
                            await send_tg_message(client, chat_id, "❌ Koi valid API keys detect nahi hui. Kripya valid key string paste karein.")

                    # Auto-detect uploaded .txt document for API Keys import if sent directly
                    elif msg.get("document") and msg["document"].get("file_name", "").endswith(".txt") and not state.get("hunting"):
                        doc = msg.get("document")
                        try:
                            f_res = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": doc["file_id"]}, timeout=10)
                            if f_res.status_code == 200:
                                f_path = f_res.json().get("result", {}).get("file_path")
                                if f_path:
                                    dl_res = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_path}", timeout=20)
                                    file_content = dl_res.text
                                    extracted_keys = re.findall(r"[a-zA-Z0-9_\-]{8,128}", file_content)
                                    if extracted_keys:
                                        added = add_user_api_keys_bulk(chat_id, extracted_keys)
                                        keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                                        await send_tg_message(
                                            client,
                                            chat_id,
                                            f"📄 <b>Keys Text File Auto-Imported!</b>\n\n"
                                            f"📥 <b>File:</b> <code>{doc.get('file_name')}</code>\n"
                                            f"✅ <b>Loaded:</b> {added} keys\n\n{keys_text}",
                                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                        )
                        except Exception as doc_e:
                            print(f"[Txt Doc Import Error] {doc_e}")

                    elif state.get("manual_step") == "awaiting_del_key":
                        del_target = text.strip()
                        remove_user_api_key(chat_id, del_target)
                        state["manual_step"] = None
                        keys_text, keys_kb = await build_keys_view_message_and_markup(client, chat_id)
                        await send_tg_message(
                            client,
                            chat_id,
                            f"🗑️ <b>API Key Successfully Deleted!</b>\n\n{keys_text}",
                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                        )

                    # ── 📋 Accounts Summary & History Report (/summary, /accounts) ──
                    elif text in ("📋 Accounts Summary", "/summary", "/accounts", "/report"):
                        generated_files = regenerate_all_summary_reports()
                        sum_text = generate_accounts_summary_text()
                        await send_tg_message(client, chat_id, sum_text, reply_markup=ADMIN_MAIN_MENU_KEYBOARD)

                        for fpath in generated_files:
                            if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                                try:
                                    fname = os.path.basename(fpath)
                                    with open(fpath, "r", encoding="utf-8") as f:
                                        txt_content = f.read()
                                    if "worker_" in fname:
                                        w_num = fname.split("_")[1]
                                        cap = f"⚡ <b>Worker #{w_num} Created Accounts Report</b>"
                                    elif "transactions" in fname:
                                        cap = "💳 <b>Wallet & Transactions Audit Log</b>"
                                    else:
                                        cap = "📋 <b>Meesho Master Accounts Summary Report</b>"
                                    await send_tg_document(
                                        client,
                                        chat_id,
                                        filename=fname,
                                        content=txt_content,
                                        caption=cap,
                                    )
                                    await asyncio.sleep(0.3)
                                except Exception as e:
                                    print(f"[Send Summary File Error] {fpath}: {e}")

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

                    # ── 🔍 Speedz Checker Keys Management (/speedzkeys, /addspeedz, /exportspeedz, /clearspeedz) ──
                    elif state.get("manual_step") == "awaiting_speedz_bulk":
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
                                print(f"[Speedz File Import Error] {e}")

                        new_keys = re.findall(r"[a-zA-Z0-9_\-]{15,100}", content)
                        state["manual_step"] = None
                        if new_keys:
                            cur_keys = cfg.get("speedz_keys", [])
                            if not isinstance(cur_keys, list):
                                cur_keys = []
                            added_c = 0
                            for nk in new_keys:
                                if nk not in cur_keys and nk != DEFAULT_SPEEDZ_KEY:
                                    cur_keys.append(nk)
                                    added_c += 1
                            update_user_config(chat_id, {"speedz_keys": cur_keys})
                            save_saved_speedz_keys_global(cur_keys)
                            total_now = len(get_speedz_keys_pool(chat_id))
                            await send_tg_message(
                                client,
                                chat_id,
                                f"✅ <b>{added_c} Speedz API Key(s) Successfully Added!</b>\n"
                                f"📊 <b>Total Pool:</b> {total_now} Keys (~{total_now * 12} checks/min)\n"
                                f"⚡ Round-Robin Auto-Rotation enabled across all keys!",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                        else:
                            await send_tg_message(
                                client,
                                chat_id,
                                "❌ Koi valid Speedz API Key nahi mili. Format jaise: <code>AK_xxx</code>",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )

                    elif text.startswith("/exportspeedz") or text.startswith("/exportspeedzkeys") or text.lower() in ("export spedzapi", "export speedzapi", "⚡ export speedz keys", "export speedz"):
                        await handle_export_speedz_keys(client, chat_id)

                    elif text.startswith("/speedzkeys") or text == "🔍 Speedz Keys" or text == "⚡ Speedz Keys":
                        sp_text, sp_kb = build_speedz_settings_message_and_markup(chat_id)
                        await send_tg_message(client, chat_id, sp_text, reply_markup=sp_kb)

                    elif text.startswith("/addspeedz"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2 and parts[1].strip():
                            new_keys = re.findall(r"[a-zA-Z0-9_\-]{15,100}", parts[1])
                            if new_keys:
                                cur_keys = cfg.get("speedz_keys", [])
                                if not isinstance(cur_keys, list):
                                    cur_keys = []
                                added_c = 0
                                for nk in new_keys:
                                    if nk not in cur_keys and nk != DEFAULT_SPEEDZ_KEY:
                                        cur_keys.append(nk)
                                        added_c += 1
                                update_user_config(chat_id, {"speedz_keys": cur_keys})
                                save_saved_speedz_keys_global(cur_keys)
                                total_now = len(get_speedz_keys_pool(chat_id))
                                await send_tg_message(
                                    client,
                                    chat_id,
                                    f"✅ <b>{added_c} Speedz API Key(s) Successfully Added!</b>\n"
                                    f"📊 <b>Total Pool:</b> {total_now} Keys (~{total_now * 12} checks/min)\n"
                                    f"⚡ Round-Robin Load Balancing enabled!",
                                    reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                                )
                            else:
                                await send_tg_message(client, chat_id, "❌ Valid API Key format detect nahi hua. Jaise: <code>/addspeedz AK_xxx</code>")
                        else:
                            state["manual_step"] = "awaiting_speedz_bulk"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            await send_tg_message(
                                client,
                                chat_id,
                                "⚡ <b>Speedz Checker API Keys Bhejein:</b>\n\n"
                                "👉 <i>Ek sath multiple keys paste karein ya .txt file bhej sakte hain.\n"
                                "Example: <code>AK_xxx AK_yyy AK_zzz</code></i>",
                                reply_markup=cancel_markup,
                            )

                    elif text == "/clearspeedz":
                        update_user_config(chat_id, {"speedz_keys": []})
                        save_saved_speedz_keys_global([])
                        await send_tg_message(
                            client,
                            chat_id,
                            f"🗑️ <b>Custom Speedz Keys Cleared!</b>\nAb default server key use hogi (Total: {len(get_speedz_keys_pool(chat_id))} key).",
                            reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                        )

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

                    # ── ⚡ Creator Engine Menu & Commands ──
                    elif text in ("⚡ Creator Engine", "⚡ API Engine", "/engine", "/engines", "/setengine"):
                        eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(chat_id)
                        await send_tg_message(client, chat_id, eng_text, reply_markup=eng_kb)

                    elif text.startswith("/setengine ") or text.startswith("/engine "):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2:
                            val = parts[1].strip().lower()
                            if val in ("cupponhub", "crowstack", "gemixai", "hidenfree", "auto"):
                                update_user_config(chat_id, {"api_engine": val})
                                eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(chat_id)
                                await send_tg_message(client, chat_id, f"✅ <b>API Engine set to {val.upper()}!</b>\n\n{eng_text}", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                            else:
                                await send_tg_message(client, chat_id, "⚠️ Options: <code>cupponhub</code>, <code>crowstack</code>, <code>gemixai</code>, <code>hidenfree</code>, <code>auto</code>")

                    # ── 🎁 Tier Selection (/settier 200, /settier 180, /tier) ──
                    elif text.startswith("/settier") or text.startswith("/tier"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] in ("200", "180"):
                            t_val = int(parts[1])
                            update_user_config(chat_id, {"cupponhub_tier": t_val})
                            eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(chat_id)
                            await send_tg_message(client, chat_id, f"✅ <b>Cupponhub Tier set to ₹{t_val} OFF!</b>\n\n{eng_text}", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            await send_tg_message(client, chat_id, "⚠️ Usage: <code>/settier 200</code> ya <code>/settier 180</code>")

                    # ── 🎯 Target Limit Commands (/setlimit <n>, /limit <n>, /target <n>) ──
                    elif text.startswith("/setlimit") or text.startswith("/limit") or text.startswith("/target") or text in ("🎯 Target Limit", "🎯 Set Target"):
                        parts = text.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            lim_val = int(parts[1])
                            update_user_config(chat_id, {"target_limit": lim_val})
                            state["target_limit"] = lim_val
                            budget_msg = await compute_target_limit_budget_message(client, chat_id, lim_val)
                            eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(chat_id)
                            await send_tg_message(client, chat_id, f"{budget_msg}\n\n{eng_text}", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            state["manual_step"] = "awaiting_target_limit"
                            cancel_markup = {"keyboard": [[{"text": "❌ Cancel"}]], "resize_keyboard": True}
                            keys_m = get_user_api_keys(chat_id)
                            bals_m = await fetch_all_key_balances(client, keys_m)
                            tot_bal_m = sum(parse_balance_float(v) for v in bals_m.values())
                            possible_m = int(tot_bal_m // 12) if tot_bal_m >= 12 else 0
                            cur_lim = int(cfg.get("target_limit", 0))
                            cur_lim_str = f"{cur_lim} Accounts" if cur_lim > 0 else "Unlimited"

                            await send_tg_message(
                                client,
                                chat_id,
                                f"🎯 <b>Target Account Limit & Auto-Budgeting:</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"• <b>Current Target:</b> <code>{cur_lim_str}</code>\n"
                                f"• <b>Live Total Wallet:</b> <b>₹{tot_bal_m:.2f}</b>\n"
                                f"• <b>Max Feasible (@ ₹12/acc):</b> <b>~{possible_m} Accounts</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"Kitne accounts banakar bot ko stop hona chahiye?\n"
                                f"👉 Number type karke bhejein (jaise: <code>70</code> ya <code>3</code> ya <code>0</code> for unlimited):\n\n"
                                f"<i>(In-flight ban rahe accounts safe finish hoke stop honge)</i>",
                                reply_markup=cancel_markup,
                            )

                    elif state.get("manual_step") == "awaiting_target_limit":
                        clean_val = text.strip()
                        if clean_val.isdigit():
                            lim_val = int(clean_val)
                            update_user_config(chat_id, {"target_limit": lim_val})
                            state["target_limit"] = lim_val
                            state["manual_step"] = None
                            budget_msg = await compute_target_limit_budget_message(client, chat_id, lim_val)
                            eng_text, eng_kb = build_engine_and_target_settings_message_and_markup(chat_id)
                            await send_tg_message(client, chat_id, f"{budget_msg}\n\n{eng_text}", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            await send_tg_message(client, chat_id, "❌ Kripya valid number bhejein (jaise: <code>3</code> ya <code>0</code> for unlimited).")

                    # ── 🚀 Start Hunt ──
                    elif text.startswith("/hunt") or text == "🚀 Start Hunt":
                        parts = text.split()
                        hunt_limit = None
                        if len(parts) >= 2 and parts[1].isdigit():
                            hunt_limit = int(parts[1])
                            update_user_config(chat_id, {"target_limit": hunt_limit})
                            state["target_limit"] = hunt_limit

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
                            asyncio.create_task(run_multi_hunter_task(client, chat_id, target_limit=hunt_limit))

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

                    # ── 📊 Stats & Day-Wise Breakdown ──
                    elif text.startswith("/stats") or text == "📊 Stats":
                        stats_text, stats_kb = await build_stats_view_message_and_markup(client, chat_id, state)
                        await send_tg_message(client, chat_id, stats_text, reply_markup=stats_kb)

                    # ── ⚡ Reset Session Counters (/resetstats, /resetsession) ──
                    elif text in ("/resetstats", "/resetsession"):
                        reset_session_stats(chat_id)
                        stats_text, stats_kb = await build_stats_view_message_and_markup(client, chat_id, state)
                        await send_tg_message(client, chat_id, f"⚡ <b>Session Stats Reset Successfully!</b>\n\n{stats_text}", reply_markup=stats_kb)

                    # ── 📅 Reset Today's Created Accounts (/resetday, /resettoday) ──
                    elif text in ("/resetday", "/resettoday"):
                        del_c = await reset_today_accounts()
                        stats_text, stats_kb = await build_stats_view_message_and_markup(client, chat_id, state)
                        await send_tg_message(client, chat_id, f"📅 <b>Today's accounts reset!</b> ({del_c} records cleared)\n\n{stats_text}", reply_markup=stats_kb)

                    # ── 🗑️ Reset All-Time History (/resethistory, /clearhistory) ──
                    elif text in ("/resethistory", "/clearhistory"):
                        confirm_kb = {
                            "inline_keyboard": [
                                [
                                    {"text": "⚠️ Yes, Delete All History", "callback_data": "confirm_reset_history_action"},
                                    {"text": "❌ Cancel", "callback_data": "cancel_reset_history"},
                                ]
                            ]
                        }
                        await send_tg_message(
                            client,
                            chat_id,
                            "⚠️ <b>CONFIRM ALL-TIME HISTORY RESET:</b>\n\nKya aap sach mein <b>sab accounts ki history delete</b> karna chahte hain?\nYeh action irreversible hai.",
                            reply_markup=confirm_kb,
                        )

                    # ── 💰 Balance (High Speed Parallel Polling) ──
                    elif text.startswith("/balance") or text == "💰 Balance":
                        keys = get_user_api_keys(chat_id)
                        if not keys:
                            await send_tg_message(
                                client,
                                chat_id,
                                "⚠️ <b>API Key Set Nahi Hai!</b>\nKripya pehle <b>🔑 Manage Keys</b> button dabayein ya <code>/addkey &lt;your_key&gt;</code> bhejein.",
                                reply_markup=ADMIN_MAIN_MENU_KEYBOARD,
                            )
                            continue

                        await send_tg_message(client, chat_id, f"⚡ <i>Fetching balances for {len(keys)} keys in parallel...</i>")
                        balances_dict = await fetch_all_key_balances(client, keys, max_concurrency=25)
                        total_bal = sum(parse_balance_float(v) for v in balances_dict.values())
                        
                        lines = [
                            f"💰 <b>OTP DOCTOR BALANCES ({len(keys)} KEYS):</b>",
                            "━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ]
                        max_disp = min(12, len(keys))
                        for idx in range(1, max_disp + 1):
                            key = keys[idx - 1]
                            bal = parse_balance_float(balances_dict.get(key, "0.00"))
                            masked = key[:4] + "..." + key[-4:] if len(key) >= 8 else key
                            lines.append(f"• <b>Key #{idx}</b> (<code>{masked}</code>): <b>₹{bal:.2f}</b> (<code>Worker #{idx}</code>)")
                        if len(keys) > max_disp:
                            lines.append(f"• <i>... and {len(keys) - max_disp} more keys in active pool</i>")
                        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
                        lines.append(f"💵 <b>Total Combined Balance:</b> <b>₹{total_bal:.2f}</b>")
                        lines.append(f"🔐 Full keys export ke liye <code>/backupkeys</code> bhejein.")
                        await send_tg_message(client, chat_id, "\n".join(lines))

                    # ── 🛑 Stop Hunt ──
                    elif text.startswith("/stop") or text == "🛑 Stop Hunt":
                        if state.get("hunting"):
                            state["stop_flag"] = True
                            state["hunting"] = False
                            # Cancel all active worker numbers across keys
                            worker_states = state.get("worker_states", {})
                            for w_idx, w_st in worker_states.items():
                                act_id = w_st.get("active_id")
                                w_key = w_st.get("api_key")
                                if act_id and w_key:
                                    print(f"[Stop] Worker #{w_idx} cancelling active number {act_id}...")
                                    await otpd_cancel(client, w_key, act_id)
                                    w_st["active_id"] = None
                            await send_tg_message(client, chat_id, "🛑 <b>Sabhi Hunter Workers Stop kar diye gaye hain.</b>", reply_markup=ADMIN_MAIN_MENU_KEYBOARD)
                        else:
                            await send_tg_message(client, chat_id, "ℹ️ Koi active hunt nahi chal rahi hai.")

            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] [Polling Exception] {type(e).__name__}: {e}", flush=True)
                await asyncio.sleep(2)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    asyncio.run(bot_loop())


if __name__ == "__main__":
    main()
