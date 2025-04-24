from flask import Flask, render_template, request, redirect
import requests
import uuid

app = Flask(__name__)

CHAPA_SECRET_KEY = "CHASECK_TEST-t9dxI0uLk5jWSly5yUQIn5gkJFgJAPH6"  # Replace with your Chapa secret key

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/pay', methods=['POST'])
def pay():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    amount = request.form['amount']

    tx_ref = str(uuid.uuid4())  # unique transaction ID

    payment_data = {
        "amount": amount,
        "currency": "ETB",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "callback_url": f"http://localhost:5000/callback/{tx_ref}",
        "return_url": "http://localhost:5000/success",
        "customization": {
            "title": "QuickMart",
            "description": "Product payment on QuickMart"
        }
    }

    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
    }

    response = requests.post("https://api.chapa.co/v1/transaction/initialize", json=payment_data, headers=headers)
    res = response.json()

    if res['status'] == 'success':
        return redirect(res['data']['checkout_url'])
    else:
        return f"Error: {res['message']}"

@app.route('/success')
def success():
    return "✅ Payment Successful! Thank you."

@app.route('/callback/<tx_ref>')
def callback(tx_ref):
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
    }

    verify_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    response = requests.get(verify_url, headers=headers)
    result = response.json()

    if result['status'] == 'success' and result['data']['status'] == 'success':
        return redirect('/success')
    else:
        return "❌ Payment failed or not verified."

if __name__ == '__main__':
    app.run(debug=True)
