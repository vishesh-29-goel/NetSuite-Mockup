from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import re

app = FastAPI(title="Faire NetSuite SuiteTalk Mock API", version="mock-v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Embedded data — real P3.26 values
# ---------------------------------------------------------------------------

PIVOT_DATA = [
    {"vendor": "CDW Direct", "department": "200 Corporate", "jan_2026": -0.01, "feb_2026": 0.00, "mar_2026": 11223.66, "mom_variance": -11223.66},
    {"vendor": "CDW Direct", "department": "235 Information Technology", "jan_2026": 21633.20, "feb_2026": 11223.66, "mar_2026": 0.00, "mom_variance": 11223.66},
    {"vendor": "CDW Direct", "department": "430 Data Science", "jan_2026": 8469.47, "feb_2026": 8469.43, "mar_2026": 0.00, "mom_variance": 8469.43},
    {"vendor": "Charm", "department": "500 Growth - Brand Partnerships", "jan_2026": 5500.00, "feb_2026": 5500.00, "mar_2026": 0.00, "mom_variance": 5500.00},
    {"vendor": "Charm", "department": "570 GTM Operations", "jan_2026": 575.34, "feb_2026": 0.00, "mar_2026": 5500.00, "mom_variance": -5500.00},
    {"vendor": "Experian", "department": "300 Risk", "jan_2026": 0.00, "feb_2026": 0.00, "mar_2026": 11850.00, "mom_variance": -11850.00},
    {"vendor": "Experian", "department": "430 Data Science", "jan_2026": 32787.50, "feb_2026": 29193.62, "mar_2026": 69597.86, "mom_variance": -40404.24},
    {"vendor": "Middesk, Inc.", "department": "300 Risk", "jan_2026": 6805.35, "feb_2026": 4564.61, "mar_2026": 0.00, "mom_variance": 4564.61},
    {"vendor": "Navan", "department": "240 People Operations", "jan_2026": 6187.15, "feb_2026": 4726.01, "mar_2026": 0.00, "mom_variance": 4726.01},
    {"vendor": "Onix Networking Corp", "department": "200 Corporate", "jan_2026": 28273.18, "feb_2026": 0.00, "mar_2026": 0.00, "mom_variance": 0.00},
    {"vendor": "Onix Networking Corp", "department": "235 Information Technology", "jan_2026": 0.00, "feb_2026": 28721.65, "mar_2026": 28601.13, "mom_variance": 120.52},
    {"vendor": "Plaid Inc.", "department": "400 Engineering", "jan_2026": 51950.45, "feb_2026": 53549.78, "mar_2026": 0.00, "mom_variance": 53549.78},
    {"vendor": "Smartly.Io Solutions Inc", "department": "520 Growth - Marketing", "jan_2026": 42943.70, "feb_2026": 12500.00, "mar_2026": 0.00, "mom_variance": 12500.00},
]

TRANSACTIONS = [
    # Experian / 430 Data Science / Mar 2026
    {"vendor": "Experian", "department": "430 Data Science", "period": "Mar 2026", "account": "65100", "transaction_type": "Bill", "journal_number": "6000244561", "memo": "BIS ONLINE-MAR-2026", "amount": 27729.00, "zip_bill_link": "https://faire.ziphq.com/invoice-detail/0eddb76d-597a-8380-8760-0082abfdd8ea", "je_support_link": None, "asset_memo": None, "entity": "Experian"},
    {"vendor": "Experian", "department": "430 Data Science", "period": "Mar 2026", "account": "65100", "transaction_type": "Bill", "journal_number": "6000263190", "memo": "BIS ONLINE-MAR-2026", "amount": 34431.36, "zip_bill_link": "https://faire.ziphq.com/invoice-detail/0f12828a-441a-8780-8760-0082ab4ea8f4", "je_support_link": None, "asset_memo": None, "entity": "Experian"},
    {"vendor": "Experian", "department": "430 Data Science", "period": "Mar 2026", "account": "65100", "transaction_type": "Journal", "journal_number": "JE2176667", "memo": None, "amount": 7437.50, "zip_bill_link": None, "je_support_link": None, "asset_memo": "AS9719 | Journal# JE2173845 | Invoice #6000157012 is a one year contract starting in Aug 2025 per DRI Ting Neo", "entity": "- No Entity -"},
    # Experian / 300 Risk / Mar 2026
    {"vendor": "Experian", "department": "300 Risk", "period": "Mar 2026", "account": "65100", "transaction_type": "Journal", "journal_number": "JE2176670", "memo": None, "amount": 11850.00, "zip_bill_link": None, "je_support_link": None, "asset_memo": "AS9490 | VendBill# 6000052365 | BIS ONLINE-APR-2025 for Premier Profile Reports (PPR)", "entity": "- No Entity -"},
    # Plaid / 400 Engineering
    {"vendor": "Plaid Inc.", "department": "400 Engineering", "period": "Mar 2026", "account": "65100", "transaction_type": None, "journal_number": None, "memo": "No transactions posted in March 2026", "amount": 0.00, "zip_bill_link": None, "je_support_link": None, "asset_memo": None, "entity": None},
    {"vendor": "Plaid Inc.", "department": "400 Engineering", "period": "Feb 2026", "account": "65100", "transaction_type": "Bill", "journal_number": "6000218942", "memo": "Plaid API Usage - February 2026", "amount": 53549.78, "zip_bill_link": "https://faire.ziphq.com/invoice-detail/mock-plaid-feb", "je_support_link": None, "asset_memo": None, "entity": "Plaid Inc."},
    # Navan / 240 People Ops
    {"vendor": "Navan", "department": "240 People Operations", "period": "Mar 2026", "account": "65100", "transaction_type": None, "journal_number": None, "memo": "No transactions posted in March 2026", "amount": 0.00, "zip_bill_link": None, "je_support_link": None, "asset_memo": None, "entity": None},
    {"vendor": "Navan", "department": "240 People Operations", "period": "Feb 2026", "account": "65100", "transaction_type": "Bill", "journal_number": "INV3298488", "memo": "Navan Travel Management - March 2026", "amount": 4726.01, "zip_bill_link": None, "je_support_link": None, "asset_memo": None, "entity": "Navan"},
    # CDW / 235 IT / Mar 2026
    {"vendor": "CDW Direct", "department": "235 Information Technology", "period": "Mar 2026", "account": "65100", "transaction_type": None, "journal_number": None, "memo": "No transactions posted in March 2026", "amount": 0.00, "zip_bill_link": None, "je_support_link": None, "asset_memo": None, "entity": None},
    {"vendor": "CDW Direct", "department": "200 Corporate", "period": "Mar 2026", "account": "65100", "transaction_type": "Bill", "journal_number": "6000251847", "memo": "CDW Software Licenses - Mar 2026", "amount": 11223.66, "zip_bill_link": "https://faire.ziphq.com/invoice-detail/mock-cdw-mar", "je_support_link": None, "asset_memo": None, "entity": "CDW Direct"},
]

ACCOUNTS = [
    {"id": "65100", "accountNumber": "65100", "accountName": "Computer Software", "type": "Expense", "balance": 0.00},
    {"id": "20161", "accountNumber": "20161", "accountName": "Accrued Computer Software", "type": "OtherCurrentLiability", "balance": 0.00},
]

VENDORS = [
    {"id": "v001", "entityId": "CDW Direct", "email": "billing@cdw.com", "category": "Software"},
    {"id": "v002", "entityId": "Charm", "email": "billing@charm.io", "category": "Software"},
    {"id": "v003", "entityId": "Experian", "email": "ar@experian.com", "category": "Data"},
    {"id": "v004", "entityId": "Middesk, Inc.", "email": "billing@middesk.com", "category": "Software"},
    {"id": "v005", "entityId": "Navan", "email": "billing@navan.com", "category": "Travel"},
    {"id": "v006", "entityId": "Onix Networking Corp", "email": "billing@onix.com", "category": "IT Services"},
    {"id": "v007", "entityId": "Plaid Inc.", "email": "billing@plaid.com", "category": "API Services"},
    {"id": "v008", "entityId": "Smartly.Io Solutions Inc", "email": "billing@smartly.io", "category": "Marketing"},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tx_to_suiteql_item(tx: dict) -> dict:
    return {
        "account": tx["account"],
        "accountName": "Computer Software",
        "vendor": tx["vendor"],
        "department": tx["department"],
        "period": tx["period"],
        "transactionType": tx.get("transaction_type"),
        "journalNumber": tx.get("journal_number"),
        "memo": tx.get("memo"),
        "amount": tx["amount"],
        "zipBillLink": tx.get("zip_bill_link"),
        "jeSupportLink": tx.get("je_support_link"),
        "assetMemo": tx.get("asset_memo"),
        "entity": tx.get("entity"),
    }


def suiteql_response(items: list) -> dict:
    return {
        "totalResults": len(items),
        "offset": 0,
        "count": len(items),
        "hasMore": False,
        "items": items,
    }


def filter_transactions(query: str) -> list:
    """Filter TRANSACTIONS based on hints found in the SQL query string."""
    results = list(TRANSACTIONS)

    # Vendor filter — match known vendor names explicitly to avoid greedy capture issues
    known_vendors = [t["vendor"] for t in TRANSACTIONS]
    matched_vendor = None
    for v in known_vendors:
        if v.lower() in query.lower():
            matched_vendor = v
            break
    if matched_vendor:
        results = [t for t in results if t["vendor"].lower() == matched_vendor.lower()]

    # Department filter — match known departments explicitly
    known_depts = list({t["department"] for t in TRANSACTIONS})
    for dept in known_depts:
        if dept.lower() in query.lower():
            results = [t for t in results if t["department"].lower() == dept.lower()]
            break

    # Period filter — e.g. "Mar 2026" or "Feb 2026"
    period_match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d\d", query, re.IGNORECASE)
    if period_match:
        period_hint = period_match.group(0).strip()
        month = period_hint[:3].capitalize()
        year = period_hint[-4:]
        normalised = f"{month} {year}"
        results = [t for t in results if t["period"] == normalised]

    return results


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SuiteQLRequest(BaseModel):
    q: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "instance": "faire-wholesale", "version": "mock-v1"}


@app.post("/auth/token")
def auth_token():
    return {
        "access_token": "mock_token_faire_wholesale",
        "token_type": "bearer",
        "expires_in": 3600,
    }


@app.post("/query/v1/suiteql")
def suiteql(body: SuiteQLRequest):
    q = body.q

    # Journal entry detail
    if "journalentry" in q.lower():
        items = [tx_to_suiteql_item(t) for t in TRANSACTIONS if t.get("transaction_type") == "Journal"]
        return suiteql_response(items)

    # Pivot / summary data
    if "pivot" in q.lower() or "summary" in q.lower():
        return suiteql_response(PIVOT_DATA)

    # Vendor lookup via SuiteQL
    if "vendor_id" in q.lower() or "from vendor" in q.lower():
        return suiteql_response([{"id": v["id"], "entityId": v["entityId"]} for v in VENDORS])

    # Transaction queries — covers TB Detail (65100/20161/Computer Software),
    # vendor-specific drills, period filters, and the general fallback.
    # Always apply filter_transactions so vendor+period combinations work correctly.
    filtered = filter_transactions(q)
    items = [tx_to_suiteql_item(t) for t in filtered]
    return suiteql_response(items)


@app.get("/record/v1/account")
def get_accounts():
    return {
        "totalResults": len(ACCOUNTS),
        "offset": 0,
        "count": len(ACCOUNTS),
        "hasMore": False,
        "items": ACCOUNTS,
    }


@app.get("/record/v1/transaction")
def get_transactions(
    vendor: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
):
    results = list(TRANSACTIONS)
    if vendor:
        results = [t for t in results if vendor.lower() in t["vendor"].lower()]
    if department:
        results = [t for t in results if department.lower() in t["department"].lower()]
    if period:
        results = [t for t in results if t["period"].lower() == period.lower()]
    if account:
        results = [t for t in results if t["account"] == account]

    items = [tx_to_suiteql_item(t) for t in results]
    return {
        "totalResults": len(items),
        "offset": 0,
        "count": len(items),
        "hasMore": False,
        "items": items,
    }


@app.get("/record/v1/vendor")
def get_vendors(q: Optional[str] = Query(None)):
    results = VENDORS
    if q:
        results = [v for v in VENDORS if q.lower() in v["entityId"].lower()]
    return {
        "totalResults": len(results),
        "offset": 0,
        "count": len(results),
        "hasMore": False,
        "items": results,
    }
