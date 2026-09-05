# Meesho Multi-Server Hunter Bot 🚀

Standalone Telegram Bot with Multi-Server Support & Custom OTP Doctor API Key.

## Features
- **🔑 Custom API Key**: Har user apna khud ka OTP Doctor API key set kar sakta hai via `/setkey <api_key>` ya `🔑 Set API Key` button. Key verify hokar `user_configs.json` me persistently save hoti hai.
- **⚙️ Server Selection (Max 2 Servers)**: Up to 2 servers ek sath select karke hunting run kar sakte hain (jaise Server 5841, 2795, 2831, 3012 ya apna custom server ID).
- **🔄 Dual-Server Hunting**:
  - Dono servers me round-robin alternating number buy karta hai.
  - Agar ek server par `NO_NUMBERS` aata hai to turant dusre server ko check karta hai.
  - Web checker se check karta hai: Old/Registered number milte hi turant cancel for refund.
  - Fresh number milte hi Crowstack API se OTP bhejta hai.
  - OTP Doctor se SMS auto-read karke login verify karta hai.
  - Account JSON generate karke Telegram message aur `.json` file ke roop me bhejta hai.
- **📱 Check My Number**:
  - Apna number check karein.
  - Agar number already Registered (Old User) hai, tab bhi option milta hai ki kya phir bhi OTP bhejna hai.
  - Yes karne par OTP bhejkar login complete karta hai.

## Quick Start
```bash
cd multi-hunter
pip install -r requirements.txt
python bot.py
```
