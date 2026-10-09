# Tractor & Equipment Booking System

A Flask + SQLite college mini project for booking tractors and agricultural equipment.

## Features
- Farmer registration/login
- Equipment listing and details
- Date-based booking
- Booking conflict check
- My Bookings
- Cancel pending booking
- Admin dashboard
- Approve/reject bookings
- Add/delete equipment
- SQLite database created automatically

## Run in Termux / Windows
```bash
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

## Admin login
Email: admin@gmail.com
Password: admin123


## New Features Added

### 1. Chatbot Assistant
A floating AgriBook chatbot is available on every page. It answers common questions about:
- Equipment and rent
- Booking process
- Payments
- Cancellation
- Admin functions

It is implemented locally, so no AI API key is required.

### 2. Payment Gateway
Razorpay Checkout integration has been added.
- Set `RAZORPAY_KEY_ID` as an environment variable to enable Razorpay checkout.
- Use Razorpay **Test Mode** keys for a college demonstration.
- If no key is configured, the project provides a clearly labelled demo-payment flow.

Example (Windows PowerShell):
```powershell
$env:RAZORPAY_KEY_ID="your_test_key_id"
python app.py
```

Example (Linux/macOS/Termux):
```bash
export RAZORPAY_KEY_ID="your_test_key_id"
python app.py
```

> For production payments, server-side Razorpay signature verification should be added before treating a payment as final. This college-project version records the successful checkout/payment callback for demonstration.
