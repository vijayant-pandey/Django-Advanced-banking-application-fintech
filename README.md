# Django Advanced Banking Application (FinTech)

A core-banking simulation built with Django. It models customer accounts, multi-currency wallets, deposits and withdrawals, and inter-account transfers over Indian payment rails (NEFT, RTGS, IMPS, UPI) plus cross-currency FX transfers. Around that sit the back-office controls a bank needs: maker-checker approval, AML alerts, fee and GST accounting, an immutable audit log, a Chart.js operations dashboard, and regulatory-style reports exported as CSV, PDF and Excel.

## Features

### Customer side
- **Registration and login.** Signing up creates a `Customer` profile and a savings `BankAccount` with an auto-generated account number. The account starts inactive until an admin approves it.
- **Customer dashboard.** Shows account details and the balance of every currency wallet.
- **Deposit and withdraw** in any active currency wallet.
- **Fund transfers** to another account over NEFT, RTGS, IMPS, UPI, Internal or FX.
- **Statement / passbook** and **transfer history** pages.

### Payment rails and rules
| Channel | Behaviour |
|---|---|
| **INTERNAL** | Settles immediately after approval. |
| **NEFT** | Queued and settled in batches, only inside the NEFT window (09:00–19:00 IST). |
| **RTGS** | Minimum ₹2,00,000, flat ₹25 fee. |
| **IMPS** | Instant, with slab-based fees (₹2.50 / ₹5 / ₹10 and up). |
| **UPI** | Creates a UPI *intent* that expires after 3 minutes. Confirmed by an admin or by the PSP webhook. |
| **FX** | Required for any non-INR transfer. The rate is locked for a time window, then approved (or re-quoted) before settlement. |

All transfers are blocked if they would exceed the daily transfer limit. A double-settlement guard stops a transfer from being settled twice.

### Multi-currency and FX
- `Currency`, `Wallet` (one per currency per account) and `FXRate` models.
- FX conversion with a spread. The spread is booked as FX income in `TransactionFee`.
- `FXRateLock` stores a locked rate with an expiry, plus admin actions to approve or re-quote.
- Every transaction stores its INR-equivalent value for reporting.

### Compliance and risk
- **AML alerts**, raised automatically for:
  - daily volume ≥ ₹10,00,000 (`DAILY_LIMIT`)
  - rapid transactions within 10 minutes (`RAPID_TX`)
  - FX activity ≥ ₹5,00,000 (`SUSPICIOUS_FX`)
- **GST ledger.** 18% GST is calculated on fees, with a monthly GSTR-3B style summary.
- **Audit log.** Login, logout, create, update, transfer and reversal actions are recorded with user and IP address. Admins can't delete logs.
- **Maker-checker.** Transfers are approved or rejected by staff in the admin panel.

### Admin operations dashboard (Chart.js)
At `/transactions/dashboard/admin/` (staff only):

| Chart | Type |
|---|---|
| FX income by currency (plus today's and this month's totals) | Bar |
| AML alerts by type | Pie |
| AML alerts: resolved vs pending | Doughnut |
| Currency exposure (wallet balances by currency) | Bar |
| Daily transaction volume (INR) | Line |
| Deposit vs withdraw breakdown | Pie |
| Transaction volume by currency (INR) | Bar |
| GST collection (monthly) | Line |
| FX income vs GST (monthly trend) | Line |

### Reports and exports (Django admin actions)
Select records in the admin panel and choose an action from the **Action** dropdown:

| Admin section | Reports | Formats |
|---|---|---|
| Transactions | RBI daily report, management summary | CSV, PDF, Excel / PDF |
| AML alerts | AML alerts report, resolve selected alerts | CSV, PDF, Excel |
| Transaction fees | FX income report | CSV, PDF, Excel |
| GST ledger | GST report, monthly GST (GSTR-3B), FX + GST compliance | CSV, PDF, Excel |
| Transfer requests | Approve & execute, reject, approve/reject UPI intent, approve/re-quote FX rate | — |

## Tech stack
- Python 3.13, Django 6.0
- Django REST Framework (with user throttling)
- SQLite (development)
- Chart.js (admin dashboard)
- ReportLab (PDF), openpyxl (Excel)
- python-dotenv (environment variables)

## Project structure
```
core/            Project settings and root URL configuration
authentication/  Register, login, logout, login/logout audit signals
customers/       Customer model and customer dashboard
accounts/        BankAccount, Currency, Wallet, FXRate, FixedDeposit, FX engine
transactions/    Transactions, transfers, settlement engine, AML, fees, GST,
                 admin dashboard, exports, reports, UPI webhook
audit/           AuditLog model and helpers
```

## URLs

Base URL when running locally: `http://127.0.0.1:8000`

| URL | Who | Description |
|---|---|---|
| `/auth/register/` | Public | Create a customer account |
| `/auth/login/` | Public | Log in |
| `/auth/logout/` | Logged-in user | Log out |
| `/dashboard/` | Logged-in user | Customer dashboard (account and wallets) |
| `/transactions/deposit/` | Logged-in user | Deposit money |
| `/transactions/withdraw/` | Logged-in user | Withdraw money |
| `/transactions/transfer/` | Logged-in user | Transfer money (choose channel and currency) |
| `/transactions/statement/` | Logged-in user | Account statement / passbook |
| `/transactions/transfers/history/` | Logged-in user | Transfer history |
| `/transactions/dashboard/admin/` | Staff | Operations dashboard with charts |
| `/transactions/webhooks/upi/` | PSP (POST) | UPI payment status webhook |
| `/admin/` | Staff | Django admin: approvals, AML, reports and exports |

After login, users are sent to `/dashboard/`. After logout, they're sent back to `/auth/login/`.

### UPI webhook
`POST /transactions/webhooks/upi/` simulates a payment service provider confirming a UPI payment.

- Header: `X-PSP-SIGNATURE`, the HMAC-SHA256 of the raw request body
- Body: JSON with the transfer reference and `"status": "SUCCESS"` or `"FAILED"`
- Returns `403` for a bad signature, `404` if the transfer is unknown, `409` if the UPI intent has expired

## Getting started

### 1. Clone and create a virtual environment
```bash
git clone https://github.com/vijayant-pandey/Django-Advanced-banking-application-fintech.git
cd Django-Advanced-banking-application-fintech
python -m venv venv
```

Activate it:
```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file
In the project root:
```
SECRET_KEY=your-django-secret-key
```
You can generate a key with:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Set up the database and an admin user
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 5. Initial data
1. Log in at `/admin/` and add currencies under **Accounts → Currencies** (at least `INR`, plus e.g. `USD`, `EUR`) and some **FX rates**.
2. Register a customer at `/auth/register/`.
3. In the admin panel, activate the new **Bank account**.
4. Create INR wallets for existing accounts:
   ```bash
   python manage.py create_inr_wallets
   ```

## Management commands

| Command | What it does |
|---|---|
| `python manage.py create_inr_wallets` | Creates an INR wallet for every bank account that doesn't have one |
| `python manage.py credit_monthly_interest` | Credits monthly interest to savings accounts |
| `python manage.py settle_neft_batch` | Settles pending NEFT transfers (only inside the NEFT window) |
| `python manage.py expire_upi_intents` | Marks UPI intents past their expiry time as expired |
| `python manage.py generate_monthly_gst` | Generates the monthly GST (GSTR-3B) summary |

In a real deployment these would run on a schedule (cron or a task queue).

## Notes
- This is a learning / portfolio project that simulates banking workflows. It isn't connected to any real payment network.
- `DEBUG` is on and SQLite is used. Both need changing for production.
