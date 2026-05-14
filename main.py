import secrets
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Query, Depends, Header, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

app = FastAPI(title="Faire NetSuite SuiteTalk Mock API", version="mock-v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# OAuth 2.0 TBA — in-memory token store
# ---------------------------------------------------------------------------

ACTIVE_TOKENS: dict[str, datetime] = {}  # token -> expires_at

MOCK_CLIENT_ID = "faire_netsuite_client"
MOCK_CLIENT_SECRET = "faire_netsuite_secret"


def verify_token(authorization: str = Header(default=None)):
    """FastAPI dependency — validates Bearer token on protected endpoints."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "error_description": "Missing or malformed Authorization header"},
        )
    token = authorization.split(" ", 1)[1]
    expires_at = ACTIVE_TOKENS.get(token)
    if expires_at is None or datetime.utcnow() > expires_at:
        # Clean up expired token if present
        ACTIVE_TOKENS.pop(token, None)
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "error_description": "Token not found or expired"},
        )
    # Opportunistic cleanup of other expired tokens
    expired = [t for t, exp in list(ACTIVE_TOKENS.items()) if datetime.utcnow() > exp]
    for t in expired:
        ACTIVE_TOKENS.pop(t, None)
    return token


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

    # Vendor filter
    known_vendors = [t["vendor"] for t in TRANSACTIONS]
    matched_vendor = None
    for v in known_vendors:
        if v.lower() in query.lower():
            matched_vendor = v
            break
    if matched_vendor:
        results = [t for t in results if t["vendor"].lower() == matched_vendor.lower()]

    # Department filter
    known_depts = list({t["department"] for t in TRANSACTIONS})
    for dept in known_depts:
        if dept.lower() in query.lower():
            results = [t for t in results if t["department"].lower() == dept.lower()]
            break

    # Period filter
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
    # Count currently active (non-expired) tokens
    now = datetime.utcnow()
    active_count = sum(1 for exp in ACTIVE_TOKENS.values() if now <= exp)
    return {
        "status": "ok",
        "instance": "faire-wholesale",
        "version": "mock-v1",
        "auth": "oauth2_tba",
        "active_tokens": active_count,
    }


@app.post("/auth/token")
async def auth_token(
    grant_type: str = Form(default=None),
    client_id: str = Form(default=None),
    client_secret: str = Form(default=None),
):
    """
    OAuth 2.0 client_credentials token endpoint.
    Accepts form-encoded body (application/x-www-form-urlencoded), exactly
    as NetSuite SuiteTalk REST API does.
    """
    if client_id != MOCK_CLIENT_ID or client_secret != MOCK_CLIENT_SECRET:
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_client", "error_description": "Invalid client credentials"},
        )
    token = f"netsuite_{secrets.token_hex(16)}"
    expires_at = datetime.utcnow() + timedelta(seconds=3600)
    ACTIVE_TOKENS[token] = expires_at
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "rest_webservices",
    }


@app.get("/auth/introspect")
def auth_introspect(authorization: str = Header(default=None)):
    """
    Token introspection — does NOT require auth itself.
    Returns active=true/false with metadata.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return {"active": False}
    token = authorization.split(" ", 1)[1]
    expires_at = ACTIVE_TOKENS.get(token)
    if expires_at is None or datetime.utcnow() > expires_at:
        return {"active": False}
    return {
        "active": True,
        "client_id": MOCK_CLIENT_ID,
        "exp": int(expires_at.timestamp()),
        "scope": "rest_webservices",
    }


@app.post("/query/v1/suiteql")
def suiteql(body: SuiteQLRequest, token: str = Depends(verify_token)):
    q = body.q

    if "journalentry" in q.lower():
        items = [tx_to_suiteql_item(t) for t in TRANSACTIONS if t.get("transaction_type") == "Journal"]
        return suiteql_response(items)

    if "pivot" in q.lower() or "summary" in q.lower():
        return suiteql_response(PIVOT_DATA)

    if "vendor_id" in q.lower() or "from vendor" in q.lower():
        return suiteql_response([{"id": v["id"], "entityId": v["entityId"]} for v in VENDORS])

    filtered = filter_transactions(q)
    items = [tx_to_suiteql_item(t) for t in filtered]
    return suiteql_response(items)


@app.get("/record/v1/account")
def get_accounts(token: str = Depends(verify_token)):
    return {
        "totalResults": len(ACCOUNTS),
        "offset": 0,
        "count": len(ACCOUNTS),
        "hasMore": False,
        "items": ACCOUNTS,
    }


@app.get("/record/v1/transaction")
def get_transactions(
    token: str = Depends(verify_token),
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
def get_vendors(token: str = Depends(verify_token), q: Optional[str] = Query(None)):
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



# ---------------------------------------------------------------------------
# Database helpers — Supabase/Postgres for GL data
# ---------------------------------------------------------------------------

import os as _os
import psycopg2 as _psycopg2
import psycopg2.extras as _extras


def _get_db():
    """Return a psycopg2 connection using DATABASE_URL env var."""
    url = _os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return _psycopg2.connect(url)


def _db_rows_to_gl(rows):
    """Convert DB rows (RealDictRow) to the GL report shape."""
    result = []
    for r in rows:
        result.append({
            "financial_row": r["account"],
            "entity": r["entity"],
            "vendor": r["vendor"],
            "department": r["department"],
            "memo": r["memo"],
            "transaction_type": r["transaction_type"],
            "document_number": r["document_number"],
            "asset_memo": r["asset_memo"],
            "zip_bill_link": r["zip_bill_link"],
            "je_support_link": r["journal_entry_support"],
            "jan_2026": float(r["jan_2026"] or 0),
            "feb_2026": float(r["feb_2026"] or 0),
            "mar_2026": float(r["mar_2026"] or 0),
            "total": float(r["total"] or 0),
        })
    return result


REPORT_META = {
    "reportId": "gl-report-65100-q1-2026",
    "reportName": "TB Detail — Computer Software (65100) — Q1 2026",
    "subsidiary": "Faire Wholesale, Inc.",
    "accounts": "65100 - Computer Software",
    "periods": "Jan 2026, Feb 2026, Mar 2026",
    "createdAt": "2026-04-01T09:14:32Z",
    "source": "netsuite_gl_transactions",
}


# ---------------------------------------------------------------------------
# Saved Exports — GL Report  (reads from Postgres)
# ---------------------------------------------------------------------------

@app.get("/saved-exports/gl-report")
def get_gl_report(
    vendor: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
):
    """
    Returns the TB Detail GL report as JSON, queried from the agent-managed DB.
    Mimics a NetSuite Saved Export / SuiteQL response.
    Filterable by vendor, department, account, or period (Jan-2026 / Feb-2026 / Mar-2026).
    No auth required — mimics NetSuite Saved Exports public link behaviour.
    """
    conn = _get_db()
    try:
        cur = conn.cursor(cursor_factory=_extras.RealDictCursor)
        query = "SELECT * FROM netsuite_gl_transactions WHERE 1=1"
        params = []
        if vendor:
            query += " AND LOWER(vendor) LIKE %s"
            params.append(f"%{vendor.lower()}%")
        if department:
            query += " AND LOWER(department) LIKE %s"
            params.append(f"%{department.lower()}%")
        if account:
            query += " AND LOWER(account) LIKE %s"
            params.append(f"%{account.lower()}%")
        if period:
            col_map = {"jan": "jan_2026", "feb": "feb_2026", "mar": "mar_2026"}
            for k, col in col_map.items():
                if k in period.lower():
                    query += f" AND {col} != 0"
                    break
        query += " ORDER BY ABS(total) DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    results = _db_rows_to_gl(rows)
    meta = dict(REPORT_META)
    meta["rowCount"] = len(results)
    meta["filters"] = {"vendor": vendor, "department": department, "account": account, "period": period}
    return {"meta": meta, "totalRows": len(results), "rows": results}


@app.get("/saved-exports/gl-report/csv")
def download_gl_report_csv(
    vendor: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
):
    """
    Streams the GL report as a CSV download, sourced from the DB.
    Used by the skill to ingest the report programmatically.
    """
    import io
    import csv as _csv
    from fastapi.responses import StreamingResponse

    conn = _get_db()
    try:
        cur = conn.cursor(cursor_factory=_extras.RealDictCursor)
        query = "SELECT * FROM netsuite_gl_transactions WHERE 1=1"
        params = []
        if vendor:
            query += " AND LOWER(vendor) LIKE %s"
            params.append(f"%{vendor.lower()}%")
        if department:
            query += " AND LOWER(department) LIKE %s"
            params.append(f"%{department.lower()}%")
        query += " ORDER BY ABS(total) DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    buf = io.StringIO()
    fieldnames = ["account","entity","vendor","department","memo","transaction_type",
                  "document_number","asset_memo","zip_bill_link","journal_entry_support",
                  "jan_2026","feb_2026","mar_2026","total","period"]
    writer = _csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r[k] for k in fieldnames if k in r})

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=NetSuite_GL_65100_Q1_2026.csv"},
    )


# ---------------------------------------------------------------------------
# Transaction Drill-Down — line items behind a vendor/account balance
# ---------------------------------------------------------------------------

@app.get("/record/v1/transaction-lines")
def get_transaction_lines(
    vendor: str = Query(..., description="Vendor name (partial match OK)"),
    account: Optional[str] = Query(None, description="GL account filter e.g. '65100'"),
    department: Optional[str] = Query(None, description="Department filter"),
    period: Optional[str] = Query(None, description="Period filter e.g. 'Mar-2026'"),
    document_number: Optional[str] = Query(None, description="Filter by specific doc number"),
    token: str = Depends(verify_token),
):
    """
    Returns individual transaction line items that make up a vendor's GL balance.
    This is the drill-down endpoint — equivalent to NetSuite's transaction detail view.
    The agent calls this after spotting a large/unusual balance in the GL report
    to understand WHAT makes up the number (e.g. the $69K Experian Mar-2026 balance).
    """
    conn = _get_db()
    try:
        cur = conn.cursor(cursor_factory=_extras.RealDictCursor)
        query = """
            SELECT id, parent_document_number, vendor, account, department,
                   line_date, description, invoice_number, quantity,
                   unit_price, amount, period_month, transaction_type, memo
            FROM netsuite_transaction_line_items
            WHERE LOWER(vendor) LIKE %s
        """
        params = [f"%{vendor.lower()}%"]

        if account:
            query += " AND LOWER(account) LIKE %s"
            params.append(f"%{account.lower()}%")
        if department:
            query += " AND LOWER(department) LIKE %s"
            params.append(f"%{department.lower()}%")
        if period:
            query += " AND LOWER(period_month) LIKE %s"
            params.append(f"%{period.lower()}%")
        if document_number:
            query += " AND (LOWER(parent_document_number) LIKE %s OR LOWER(invoice_number) LIKE %s)"
            params.extend([f"%{document_number.lower()}%", f"%{document_number.lower()}%"])

        query += " ORDER BY line_date, amount DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    items = []
    total_amount = 0.0
    for r in rows:
        amt = float(r["amount"] or 0)
        total_amount += amt
        items.append({
            "id": r["id"],
            "documentNumber": r["parent_document_number"],
            "invoiceNumber": r["invoice_number"],
            "vendor": r["vendor"],
            "account": r["account"],
            "department": r["department"],
            "date": str(r["line_date"]),
            "description": r["description"],
            "quantity": float(r["quantity"] or 1),
            "unitPrice": float(r["unit_price"] or amt),
            "amount": amt,
            "periodMonth": r["period_month"],
            "transactionType": r["transaction_type"],
            "memo": r["memo"],
        })

    return {
        "query": {
            "vendor": vendor,
            "account": account,
            "department": department,
            "period": period,
            "documentNumber": document_number,
        },
        "totalRows": len(items),
        "netAmount": round(total_amount, 2),
        "currency": "USD",
        "items": items,
    }
