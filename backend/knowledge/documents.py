"""Curated JazzCash knowledge documents for RAG retrieval."""

from __future__ import annotations

KNOWLEDGE_DOCUMENTS = [
    {
        "id": "kb-wallet",
        "title": "JazzCash Wallet",
        "category": "wallet",
        "route": "/home",
        "keywords": ["wallet", "balance", "valiit", "account", "paisa", "money"],
        "content": (
            "JazzCash Wallet lets you store, send, and receive money digitally. "
            "Check your balance on the Home screen. Demo user Fahem has a mock wallet. "
            "Never share your MPIN or OTP. This assistant cannot move money — it only guides."
        ),
    },
    {
        "id": "kb-send-money",
        "title": "Send Money / Money Transfer",
        "category": "transfer",
        "route": "/send-money",
        "keywords": ["send money", "transfer", "bhejo", "bhejna", "paisa bhejo", "remittance"],
        "content": (
            "Send Money is under Send Money in the app. You can transfer to JazzCash numbers, "
            "bank accounts, or via Raast. Fees: wallet-to-wallet free (demo); bank transfer "
            "Rs. 15–50 (demo). The AI assistant guides you but NEVER executes transfers."
        ),
    },
    {
        "id": "kb-bank-transfer",
        "title": "Bank Transfer",
        "category": "transfer",
        "route": "/send-money",
        "keywords": ["bank", "bank transfer", "iban", "account number", "hbl", "ubl", "mcb"],
        "content": (
            "Bank transfers are available via Send Money → Bank Transfer. Enter IBAN or account "
            "details carefully. Confirm recipient name before submitting. Demo fees apply. "
            "AI will not execute bank transfers."
        ),
    },
    {
        "id": "kb-raast",
        "title": "What is Raast?",
        "category": "faq",
        "route": "/send-money",
        "keywords": ["raast", "راست", "instant transfer", "fast payment"],
        "content": (
            "Raast is Pakistan's instant payment system by the State Bank of Pakistan. "
            "It enables fast, low-cost account-to-account transfers using Raast ID or account "
            "number, available 24/7. In JazzCash, open Send Money and choose Raast. "
            "Demo: free Raast transfers for eligible users."
        ),
    },
    {
        "id": "kb-bills",
        "title": "Bill Payments",
        "category": "payments",
        "route": "/bills",
        "keywords": [
            "bill",
            "electricity",
            "gas",
            "water",
            "lesco",
            "kesc",
            "ssgc",
            "sngpl",
            "utility",
            "bijli",
            "بل",
        ],
        "content": (
            "Pay utility bills via Bill Payment: electricity (LESCO, K-Electric), gas (SSGC, SNGPL), "
            "water, internet, and more. Enter consumer number, review amount, confirm with MPIN. "
            "Bill payments are usually free (demo). Navigate to /bills."
        ),
    },
    {
        "id": "kb-passport",
        "title": "Passport Fee Payment",
        "category": "government",
        "route": "/bills",
        "keywords": ["passport", "passport fee", "dgip", "government", "nadra"],
        "content": (
            "Passport fees can be paid under Government Payments / Bill Payment. Select Passport "
            "Fee, enter required details from DGIP, and pay from your wallet. This is guidance only — "
            "no real government payment is executed in this demo."
        ),
    },
    {
        "id": "kb-recharge",
        "title": "Mobile Recharge",
        "category": "payments",
        "route": "/mobile-recharge",
        "keywords": ["recharge", "topup", "load", "mobile", "jazz", "telenor", "ufone", "zong"],
        "content": (
            "Mobile Recharge lets you top up prepaid numbers for Jazz and other networks. "
            "Open Mobile Recharge, enter number and amount, confirm. Usually free (demo). Route: /mobile-recharge."
        ),
    },
    {
        "id": "kb-mtag",
        "title": "M-Tag Recharge",
        "category": "payments",
        "route": "/services",
        "keywords": ["m-tag", "mtag", "motorway", "toll"],
        "content": (
            "M-Tag is used for motorway toll payments. Recharge your M-Tag from Services → M-Tag. "
            "Enter tag ID and amount. Demo only — no real toll recharge."
        ),
    },
    {
        "id": "kb-savings",
        "title": "Savings Options",
        "category": "products",
        "route": "/savings",
        "keywords": ["saving", "savings", "bachat", "profit", "save", "بچت"],
        "content": (
            "JazzCash savings options (demo): Save As You Go (auto-save with up to 10% p.a. demo), "
            "and JazzCash Savings Account with competitive daily profit. Open /savings to explore. "
            "Returns shown are demo figures only."
        ),
    },
    {
        "id": "kb-loans",
        "title": "Loans / Ready Cash",
        "category": "products",
        "route": "/loans",
        "keywords": [
            "loan",
            "ready cash",
            "qarz",
            "credit",
            "borrow",
            "repay",
            "repayment",
            "installment",
            "late fee",
            "payment plan",
            "قرضہ",
            "قسط",
        ],
        "content": (
            "Ready Cash / JazzCash loans: short-term digital credit based on KYC, wallet history, "
            "and recent transactions (demo only — no real disbursement).\n\n"
            "PROACTIVE REPAYMENT JOURNEY MANAGEMENT (CX 4.0 demo):\n"
            "- Home shows a Loan payment plan card with status (On Track / Due Soon / Due Today / Behind / Paid Off), "
            "next installment, progress, and outstanding balance.\n"
            "- Assistant can: explain charges, compare illustrative repayment plans "
            "(Faster payoff, Balanced, Lower payments), prepare catch-up or next-installment repayment "
            "(user must approve), and set reminder preferences (3 days before / 1 day before / due date).\n"
            "- If Behind: overdue days + illustrative late charge are explained; catch-up = installment + late fee.\n"
            "- Values in APP CONTEXT ready_cash_loan are the live demo state — use them when answering.\n"
            "- Always guide via suggested_action route /loans. Never pretend a real repayment executed."
        ),
    },
    {
        "id": "kb-insurance",
        "title": "Insurance",
        "category": "products",
        "route": "/insurance",
        "keywords": ["insurance", "health", "device protect", "cover", "انشورنس"],
        "content": (
            "JazzCash offers Health Cover and Device Protect insurance plans with affordable "
            "monthly premiums (demo). Browse /insurance. No real policy is purchased in this demo."
        ),
    },
    {
        "id": "kb-investments",
        "title": "Investments",
        "category": "products",
        "route": "/services",
        "keywords": ["invest", "investment", "mutual fund", "stocks"],
        "content": (
            "Investment products may be available under Services depending on eligibility. "
            "Demo content only — not investment advice. Always read risk disclosures."
        ),
    },
    {
        "id": "kb-cards",
        "title": "JazzCash Card",
        "category": "products",
        "route": "/services",
        "keywords": ["card", "debit", "visa", "virtual card"],
        "content": (
            "JazzCash Card links to your wallet for online and POS payments. Virtual and physical "
            "options may be available. Manage cards under Services. Demo only."
        ),
    },
    {
        "id": "kb-qr",
        "title": "QR Payments",
        "category": "payments",
        "route": "/services",
        "keywords": ["qr", "scan", "merchant", "pay at shop"],
        "content": (
            "Pay merchants by scanning JazzCash QR codes. Open QR Pay, scan, confirm amount. "
            "Double rewards offers may apply on QR payments (see Offers)."
        ),
    },
    {
        "id": "kb-rewards",
        "title": "Rewards & Cashback",
        "category": "offers",
        "route": "/offers",
        "keywords": ["reward", "cashback", "points", "offer", "discount", "انعام"],
        "content": (
            "Earn JazzCash Rewards and cashback on eligible transactions. Current demo offers "
            "include 5% cashback on bill payments, free Raast transfers, and 2x QR rewards. "
            "See /offers."
        ),
    },
    {
        "id": "kb-offers",
        "title": "Current Offers",
        "category": "offers",
        "route": "/offers",
        "keywords": ["offer", "promo", "deal", "cashback offer"],
        "content": (
            "Demo offers: (1) 5% cashback on electricity & gas bills up to Rs. 200, (2) Free Raast "
            "transfers, (3) Double rewards on QR, (4) Bonus savings profit. Validities are demo dates."
        ),
    },
    {
        "id": "kb-security",
        "title": "Security & Account Safety",
        "category": "security",
        "route": "/support",
        "keywords": ["security", "pin", "mpin", "otp", "fraud", "scam", "hack"],
        "content": (
            "Never share MPIN, OTP, or CNIC with anyone including support callers. JazzCash will "
            "not ask for your MPIN. Enable biometric login. Report fraud via Support. "
            "This AI never asks for MPIN or executes transactions."
        ),
    },
    {
        "id": "kb-account",
        "title": "Account Management",
        "category": "account",
        "route": "/home",
        "keywords": ["profile", "account", "kyc", "limit", "upgrade", "cnic"],
        "content": (
            "Manage profile, KYC level, and limits from account settings. Higher KYC levels unlock "
            "higher transaction limits. Demo user: Fahem, Level 1."
        ),
    },
    {
        "id": "kb-transactions",
        "title": "Transaction History & Status",
        "category": "transactions",
        "route": "/transactions",
        "keywords": [
            "transaction",
            "history",
            "pending",
            "failed",
            "status",
            "receipt",
            "txn",
            "ٹرانزیکشن",
        ],
        "content": (
            "View transaction history under Transactions (/transactions). Statuses: Completed "
            "(successful), Pending (in process — wait or check later), Failed (not completed — "
            "amount usually reversed; check failure reason). Demo includes a pending Raast transfer "
            "and a failed SSGC bill."
        ),
    },
    {
        "id": "kb-pending",
        "title": "Pending Transaction Meaning",
        "category": "transactions",
        "route": "/transactions",
        "keywords": ["pending", "processing", "in process", "waiting"],
        "content": (
            "A Pending transaction means the payment is still being processed by JazzCash or the "
            "receiving bank/network. Wait a few minutes and refresh. If it stays pending too long, "
            "contact Support with the transaction ID. Do not retry immediately with the same details "
            "to avoid duplicates."
        ),
    },
    {
        "id": "kb-failed",
        "title": "Failed Payment Troubleshooting",
        "category": "troubleshooting",
        "route": "/support",
        "keywords": [
            "fail",
            "failed",
            "failure",
            "error",
            "nahi hui",
            "cancel",
            "insufficient",
        ],
        "content": (
            "If a payment fails: (1) Check wallet balance, (2) Verify consumer/account number, "
            "(3) Check network connectivity, (4) Review failure reason in transaction details, "
            "(5) Retry later or contact Support. Demo failed TXN-982336 SSGC bill: insufficient balance. "
            "Amount is typically not deducted on failure; if deducted, it is reversed."
        ),
    },
    {
        "id": "kb-support",
        "title": "Customer Support",
        "category": "support",
        "route": "/support",
        "keywords": ["support", "complaint", "help", "helpline", "complaint register"],
        "content": (
            "Register complaints via in-app Support (/support) or JazzCash helpline. Keep transaction "
            "ID ready. Demo ticket SUP-4401 exists for failed SSGC payment. AI can guide but cannot "
            "open real tickets against production systems."
        ),
    },
    {
        "id": "kb-fees",
        "title": "Fees and Charges",
        "category": "fees",
        "route": "/services",
        "keywords": ["fee", "charge", "charges", "cost", "kitni", "pricing"],
        "content": (
            "Demo fee guide: Wallet-to-wallet free; Raast free up to limit; Bank transfer Rs. 15–50; "
            "Bill payment usually free; Mobile recharge free; ATM cash-out Rs. 30–50. "
            "Actual fees may differ in production JazzCash."
        ),
    },
    {
        "id": "kb-navigation-home",
        "title": "App Navigation — Home",
        "category": "navigation",
        "route": "/home",
        "keywords": ["home", "where", "kahan", "open", "section", "menu"],
        "content": (
            "Home shows balance, AI ask bar, popular services, and shortcuts. Bottom nav: "
            "Home, AI, Services, Transactions, More."
        ),
    },
    {
        "id": "kb-ai-limits",
        "title": "AI Assistant Capabilities & Limits",
        "category": "faq",
        "route": "/ai",
        "keywords": ["ai", "assistant", "can you send", "execute", "transfer kar do"],
        "content": (
            "JazzCash AI helps you discover services, understand fees, troubleshoot, and navigate. "
            "It does NOT execute financial transactions. If asked to send money, it refuses execution "
            "and offers to guide you to Send Money instead."
        ),
    },
]
