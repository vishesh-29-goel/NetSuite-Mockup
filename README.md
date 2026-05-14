# NetSuite Mock API — Faire Wholesale Demo

Mock of the NetSuite SuiteTalk REST API serving real P3.26 (March 2026) accrual data for the Faire demo.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/token` | Mock OAuth token |
| POST | `/query/v1/suiteql` | SuiteQL queries (main data endpoint) |
| GET | `/record/v1/account` | Account list (65100, 20161) |
| GET | `/record/v1/transaction` | Transaction detail (vendor/dept/period filters) |
| GET | `/record/v1/vendor` | Vendor search |
| GET | `/health` | Health check |

## SuiteQL Usage

```bash
# Get all Computer Software transactions
curl -X POST {BASE_URL}/query/v1/suiteql \
  -H 'Content-Type: application/json' \
  -d '{"q": "SELECT * FROM transaction WHERE account = 65100"}'

# Drill into specific vendor + period
curl -X POST {BASE_URL}/query/v1/suiteql \
  -H 'Content-Type: application/json' \
  -d '{"q": "SELECT * FROM transaction WHERE vendor = Experian AND period = Mar 2026"}'
```

## Deploying to production
When Faire IT clearance comes through, change `NETSUITE_BASE_URL` in the skill to point at the real SuiteTalk endpoint. No other code changes needed.
