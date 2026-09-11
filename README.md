# Meesho Multi-Server Hunter & JSON Store Bot 🚀

Standalone Telegram Bot with Multi-Server Support, Automated JSON Store, Live Staged Simulation, Admin-Exclusive Delivery Control, and 2-Way Live Support.

---

## 🌟 Key Features

### 🛍️ Automated Meesho JSON Store (Buyer Interface)
- **Instant QR Invoices**: Real-time UPI QR generation with order IDs, customizable prices, and payee details.
- **12-Digit UTR Verification**: Automated payment submission and admin notification.
- **Realistic Staged Live Progress Simulation**:
  - `[▓▓░░░░░░░░] 20% (Searching)` — Searching fresh unregistered number on fast servers...
  - `[▓▓▓▓▓░░░░░] 50% (OTP Sent)` — Allocated Mobile `+91 98765-XXXXX` & SMS dispatched.
  - `[▓▓▓▓▓▓▓▓░░] 85% (Logging in)` — SMS OTP 6-digit verified & generating session tokens.
  - `[▓▓▓▓▓▓▓▓▓▓] 100% (Complete)` — Account created successfully! Admin final quality check.
- **My Orders & History**: `/orders` command to view past orders and statuses.
- **2-Way Always-On Support**: Buyer can send queries directly to Admin via `💬 Contact Admin`.

### 👑 Admin Master Controls
- **Admin-Exclusive Delivery Control**: Mined account files and JSON tokens go **strictly to Admin (`8282846997`)** first. Admin chooses to:
  - `[📤 Send This Mined JSON to Buyer]`
  - `[📁 Upload Custom File / JSON to Buyer]` (`/deliver <order_id>`)
- **Direct Messaging & Reply**: `/msg <user_id> <reply>` to reply directly to buyers through the bot.
- **Broadcast Announcements**: `/broadcast <message>` to notify all buyers and registered users instantly.
- **Store Settings**: `/setprice <amount>` and `/setupi <upi_id> [name]`.

### ⚙️ Multi-Server Hunter Controls
- **🔑 Custom API Key**: Set your own OTP Doctor API key via `/setkey <api_key>`.
- **⚙️ Server Selection**: Select up to 2 servers simultaneously (e.g. Server 5841, 19826, or custom server IDs).
- **📝 Custom JSON Template**: `/setjson` to configure your custom export schema or use `/convertjson` to reform arbitrary JSON into your required template.

---

## 🚀 Quick Start
```bash
cd multi-hunter
pip install -r requirements.txt
python bot.py
```
