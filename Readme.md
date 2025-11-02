# GiftPool Bot – Group Gift & Secret Santa Web Assistant

**A fully automated web bot** that organizes **group gifts** and **Secret Santa** with **zero manual intervention**.

---

## Features

| Feature | Description |
|--------|-------------|
| **100% Automatic Payments** | PayPal integration with **webhook** → detects payments instantly |
| **Budget in Euros** | Clean format: `30€` everywhere |
| **Live Dashboard** | Real-time status: who paid, who didn't |
| **Email Automation** | Gmail SMTP sends personalized links and reminders |
| **Payment Simulator** | Test payments with one click (for demo) |
| **No Manual Confirmation** | PayPal handles everything |
| **Deployed on Render** | Free, public URL: `https://giftpool.onrender.com` |

---

## How It Works (Bot Flow)

1. **User creates a group** → fills form (recipient, emails, budget)
2. **Bot generates PayPal links** for each participant
3. **Emails sent automatically** with:
   - Personalized message
   - PayPal button (`Pay 30€`)
   - Live dashboard link
4. **User clicks PayPal** → pays with Sandbox (test mode)
5. **PayPal webhook fires** → bot **captures payment**
6. **Bot updates dashboard** → marks as **Paid**
7. **Bot emails everyone**: "Ana has paid!"
8. **Daily reminders** to unpaid users

**No human intervention needed.**

---

## Technologies

- **Python / Flask** – Web framework
- **PayPal API (v2)** – Payments + Webhooks
- **Gmail SMTP** – Email automation
- **Render.com** – Free hosting
- **PayPal Sandbox** – Test environment (no real money)


**Try it now:**  
[https://giftpool.onrender.com](https://giftpool.onrender.com)

> Use test card: `4032 0382 0382 0382`  
> PayPal Sandbox buyer: `buyer@example.com` / `paypal`

---

## Project Structure
giftpool/
├── app.py                  # Main bot logic
├── templates/
│   ├── index.html          # Create group form
│   └── grupo.html          # Live dashboard
├── requirements.txt        # Dependencies
├── Procfile                # Render deploy
├── .env.example            # Environment variables
└── README.md               # This file


---


### 1. Clone & Install
```bash
git clone https://github.com/javieer005/giftpool
cd giftpool
pip install -r requirements.txt