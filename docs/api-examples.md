# PMRI Global API Examples

The PMRI Global API is a RESTful service built with FastAPI. It handles routing, ML inference, and portfolio management.

## Authentication

First, log in to get a JWT token.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "retail@example.com", "password": "password"}'
  
# Extract the "access_token" from the response
```

## 1. Create a Portfolio

```bash
curl -X POST http://localhost:8000/portfolios \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "My Global Tech Portfolio"}'
```

## 2. Upload Holdings via CSV

Use a CSV file with columns: `symbol,exchange,quantity`

```bash
curl -X POST http://localhost:8000/portfolios/<PORTFOLIO_ID>/upload \
  -H 'Authorization: Bearer <TOKEN>' \
  -F 'file=@portfolio.csv'
```

## 3. Get an Insurance Quote

The engine will evaluate the portfolio against the ML model and apply tier-specific underwriting limits.

```bash
curl -X POST http://localhost:8000/quotes \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
    "portfolio_id": "<PORTFOLIO_ID>",
    "term": "WEEKLY",
    "notional_inr": 500000
  }'
```

## 4. Bind Policy (Purchase)

If the quote is `eligible: true`, you can purchase it.

```bash
curl -X POST http://localhost:8000/policies \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"quote_id": "<QUOTE_ID>"}'
```

## 5. View Ledger Transactions

View the premium deduction.

```bash
curl -X GET http://localhost:8000/ledger?policy_id=<POLICY_ID> \
  -H 'Authorization: Bearer <TOKEN>'
```

## 6. Trigger Admin Settlement

Manually trigger the settlement engine (Admin only).

```bash
curl -X POST http://localhost:8000/settlements/run \
  -H 'Authorization: Bearer <ADMIN_TOKEN>'
```
