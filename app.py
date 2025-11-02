

# app.py - GiftPool Bot: Group Gift & Secret Santa Web Assistant
# Features: PayPal (auto), Budget in €, PAYMENT SIMULATOR (for demo)
# No manual intervention | Live dashboard | Gmail | Render-ready

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
import yagmail
import random
import threading
import schedule
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# === LOAD ENV ===
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# === CONFIG ===
PAYPAL_CLIENT_ID = os.getenv('vPAYPAL_CLIENT_ID')      # From PayPal Developer
PAYPAL_SECRET = os.getenv('vPAYPAL_SECRET')            # From PayPal Developer
PAYPAL_BASE = os.getenv('vPAYPAL_BASE')      # .paypal.com for live
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')

# In-memory DB
groups = {}

# === EMAIL SETUP ===
try:
    email_sender = yagmail.SMTP(
        user=EMAIL_USER,
        password=EMAIL_PASS,
        host='smtp.gmail.com',
        port=587,
        smtp_starttls=True,
        smtp_ssl=False,
        smtp_skip_login=False
    )
    print("Gmail SMTP connected")
except Exception as e:
    print(f"SMTP Error: {e}")
    email_sender = None

def send_email(to, subject, body):
    if email_sender:
        try:
            email_sender.send(to=to, subject=subject, contents=body)
        except Exception as e:
            print(f"Email failed: {e}")

# === PAYPAL TOKEN ===
def get_paypal_token():
    url = f"{PAYPAL_BASE}/v1/oauth2/token"
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    headers = {'Accept': 'application/json'}
    data = {'grant_type': 'client_credentials'}
    r = requests.post(url, auth=auth, headers=headers, data=data, timeout=10)
    return r.json().get('access_token') if r.status_code == 200 else None

# === CREATE PAYPAL ORDER ===
def create_paypal_order(amount, name, group_id, email):
    token = get_paypal_token()
    if not token: return {'id': None, 'approve_url': '#'}
    
    url = f"{PAYPAL_BASE}/v2/checkout/orders"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "EUR", "value": str(amount)},
            "description": f"Gift - {name}",
            "custom_id": f"{group_id}|{email}"
        }],
        "application_context": {
            "return_url": url_for('paypal_return', _external=True),
            "cancel_url": url_for('paypal_cancel', _external=True),
            "brand_name": "GiftPool",
            "user_action": "PAY_NOW"
        }
    }
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 201:
        data = r.json()
        approve = [l['href'] for l in data['links'] if l['rel'] == 'approve'][0]
        return {'id': data['id'], 'approve_url': approve}
    return {'id': None, 'approve_url': '#'}

# === CAPTURE PAYMENT ===
def capture_paypal_order(order_id):
    token = get_paypal_token()
    if not token: return False
    url = f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    r = requests.post(url, headers=headers)
    return r.status_code == 201 and r.json().get('status') == 'COMPLETED'

# === HOME ===
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mode = request.form['mode']
        recipient = request.form.get('recipient', '').strip()
        emails_input = request.form['emails']
        budget = int(request.form.get('budget', 30))

        emails = [e.strip() for e in emails_input.split(',') if e.strip()]
        if len(emails) < 2:
            flash("At least 2 participants required.")
            return redirect(url_for('index'))

        group_id = f"{mode}_{int(time.time())}"
        ideas = [f"Headphones (~{budget}€)", f"Book (~{budget//2}€)"]

        # === FORMATEAR EUROS ===
        budget_formatted = f"{budget}€"

        groups[group_id] = {
            'id': group_id, 'mode': mode, 'recipient': recipient,
            'budget': budget, 'budget_formatted': budget_formatted,
            'emails': emails,
            'names': [e.split('@')[0].capitalize() for e in emails],
            'ideas': ideas, 'votes': {0: 0, 1: 0},
            'payments': {}, 'created': datetime.now().strftime('%b %d, %H:%M')
        }

        # === PAYPAL LINKS ===
        for email in emails:
            name = email.split('@')[0].capitalize()
            order = create_paypal_order(budget, name, group_id, email)

            groups[group_id]['payments'][email] = {
                'name': name,
                'paypal_order_id': order['id'],
                'paypal_link': order['approve_url'],
                'paid': False
            }

            # === EMAIL CON EUROS ===
            body = f"""
            <h2>Gift for <strong>{recipient}</strong></h2>
            <p>Your share: <strong>{budget_formatted}</strong></p>
            <p><a href="{order['approve_url']}" 
               style="background:#0070ba;color:white;padding:12px 20px;text-decoration:none;border-radius:8px;font-weight:bold;">
               Pay {budget_formatted} with PayPal
            </a></p>
            <p><small>Payment will be confirmed <strong>automatically</strong>.</small></p>
            <hr>
            <p>Live dashboard: <a href="{url_for('view_group', group_id=group_id, _external=True)}">View</a></p>
            """
            send_email(email, f"Gift for {recipient} - Pay {budget_formatted}", body)

        flash(f"Group created! Share: {url_for('view_group', group_id=group_id, _external=True)}")
        return redirect(url_for('view_group', group_id=group_id))

    return render_template('index.html')

# === PAYPAL RETURN ===
@app.route('/paypal-return')
def paypal_return():
    flash("Processing PayPal payment...")
    return redirect(url_for('index'))

@app.route('/paypal-cancel')
def paypal_cancel():
    flash("Payment cancelled.")
    return redirect(url_for('index'))

# === WEBHOOK: AUTO CONFIRM ===
@app.route('/webhook/paypal', methods=['POST'])
def paypal_webhook():
    payload = request.get_json()
    if payload.get('event_type') == 'CHECKOUT.ORDER.APPROVED':
        order_id = payload['resource']['id']
        for gid, g in groups.items():
            for email, p in g['payments'].items():
                if p.get('paypal_order_id') == order_id:
                    if capture_paypal_order(order_id):
                        p['paid'] = True
                        name = p['name']
                        for e in g['emails']:
                            send_email(e, "Payment confirmed!", f"<strong>{name}</strong> paid {g['budget_formatted']}!")
                    return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'ignored'}), 200

# === SIMULADOR DE PAGOS (para pruebas) ===
@app.route('/simulate-payment', methods=['POST'])
def simulate_payment():
    group_id = request.form['group_id']
    email = request.form['email']
    if group_id in groups and email in groups[group_id]['payments']:
        groups[group_id]['payments'][email]['paid'] = True
        name = groups[group_id]['payments'][email]['name']
        for e in groups[group_id]['emails']:
            send_email(e, "Payment simulated!", f"<strong>{name}</strong> paid {groups[group_id]['budget_formatted']} (demo).")
        flash(f"Simulated payment for {name}")
    return redirect(url_for('view_group', group_id=group_id))

# === DASHBOARD ===
@app.route('/group/<group_id>')
def view_group(group_id):
    group = groups.get(group_id)
    if not group:
        flash("Group not found.")
        return redirect(url_for('index'))
    return render_template('grupo.html', group=group)

# === REMINDERS ===
def send_reminders():
    for gid, g in list(groups.items()):
        if g['mode'] == 'giftpool':
            for email, p in g['payments'].items():
                if not p['paid']:
                    send_email(email, "Reminder", f"Please pay {g['budget_formatted']} for {g['recipient']}.")

schedule.every().day.at("09:00").do(send_reminders)
threading.Thread(target=lambda: [schedule.run_pending(), time.sleep(60)], daemon=True).start()

# === RUN ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)