"""routers/portfolios.py — Portfolios router with CSV upload and holdings management."""
from __future__ import annotations
import csv
import io
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.org import OrgMember
from app.models.portfolio import Portfolio, Holding
from app.schemas.portfolio import PortfolioCreate, PortfolioResponse, HoldingInput, HoldingResponse, CsvUploadResult

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


async def _check_org_access(org_id: str, current_user: User, db: AsyncSession):
    if not current_user.is_admin:
        m = (await db.execute(select(OrgMember).where(OrgMember.org_id == uuid.UUID(org_id), OrgMember.user_id == current_user.id))).scalar_one_or_none()
        if not m:
            raise HTTPException(403, detail="Access denied to this organisation context.")


from sqlalchemy.orm import selectinload

async def _get_portfolio(portfolio_id: str, current_user: User, db: AsyncSession) -> Portfolio:
    p = (await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .where(Portfolio.id == uuid.UUID(portfolio_id))
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(404, detail="Portfolio not found.")
    if p.org_id:
        await _check_org_access(str(p.org_id), current_user, db)
    elif p.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, detail="Access denied.")
    return p


@router.post("", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(req: PortfolioCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if req.org_id:
        await _check_org_access(req.org_id, current_user, db)
    p = Portfolio(name=req.name, user_id=current_user.id, org_id=uuid.UUID(req.org_id) if req.org_id else None)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return PortfolioResponse(
        id=str(p.id), name=p.name, user_id=str(p.user_id),
        org_id=str(p.org_id) if p.org_id else None,
        created_at=p.created_at.isoformat(),
        holdings=[],
    )


@router.get("", response_model=List[PortfolioResponse])
async def list_portfolios(org_id: str = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if org_id:
        await _check_org_access(org_id, current_user, db)
        q = select(Portfolio).where(Portfolio.org_id == uuid.UUID(org_id))
    else:
        q = select(Portfolio).where(Portfolio.user_id == current_user.id, Portfolio.org_id.is_(None))
    
    portfolios = (await db.execute(q)).scalars().all()
    result = []
    for p in portfolios:
        if p.status == "ARCHIVED":
            continue
        h_q = await db.execute(select(Holding).where(Holding.portfolio_id == p.id))
        holdings = h_q.scalars().all()
        result.append(PortfolioResponse(
            id=p.id, name=p.name, user_id=p.user_id, org_id=p.org_id,
            created_at=p.created_at,
            status=p.status,
            holdings=[HoldingResponse.model_validate(h) for h in holdings]
        ))
    return result


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(portfolio_id: str, req: PortfolioUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = await _get_portfolio(portfolio_id, current_user, db)
    if req.name is not None:
        p.name = req.name
    if req.status is not None:
        p.status = req.status.upper()
    await db.commit()
    await db.refresh(p)
    return PortfolioResponse.model_validate(p)


@router.delete("/{portfolio_id}", status_code=204)
async def delete_portfolio(portfolio_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = await _get_portfolio(portfolio_id, current_user, db)
    # Check if has active policies
    from app.models.quote import Quote
    from app.models.policy import Policy
    active_pol = (await db.execute(select(Policy).where(Policy.portfolio_id == p.id, Policy.status == "ACTIVE"))).scalar()
    if active_pol:
        raise HTTPException(400, detail="Cannot delete portfolio with active insurance policies. Archive it instead.")
    
    await db.delete(p)
    await db.commit()
    return None


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = await _get_portfolio(portfolio_id, current_user, db)
    # Holdings are already loaded via selectinload in _get_portfolio
    return PortfolioResponse.model_validate(p)


@router.post("/{portfolio_id}/holdings", response_model=PortfolioResponse)
async def add_holding(portfolio_id: str, h: HoldingInput, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
    from symbols import validate_and_normalize

    p = await _get_portfolio(portfolio_id, current_user, db)
    sym, exc, err = validate_and_normalize(h.symbol, h.exchange)
    if err:
        raise HTTPException(400, detail=err)

    # Upsert logic
    existing = (await db.execute(select(Holding).where(Holding.portfolio_id == p.id, Holding.symbol == f"{sym}.{exc}"))).scalar_one_or_none()
    if existing:
        existing.quantity += h.quantity
    else:
        db.add(Holding(portfolio_id=p.id, symbol=f"{sym}.{exc}", exchange=exc, quantity=h.quantity))
    
    await db.commit()
    # Refresh to pick up new holdings (selectinload should be used if we re-fetch)
    p = await _get_portfolio(portfolio_id, current_user, db)
    return PortfolioResponse.model_validate(p)


@router.post("/{portfolio_id}/upload", response_model=CsvUploadResult)
async def upload_csv(portfolio_id: str, file: UploadFile = File(...), replace: bool = False, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Upload a CSV with headers: symbol, exchange, quantity."""
    p = await _get_portfolio(portfolio_id, current_user, db)
    
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
    from symbols import validate_and_normalize

    content = await file.read()
    
    # Try multiple encodings
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(400, detail="Could not decode CSV file. Please save as UTF-8.")

    # Detect format: Google Sheets exports each row as a single quoted string,
    # e.g.: "symbol,exchange,quantity"  (the whole line is one quoted field)
    # vs standard CSV:  symbol,exchange,quantity  (no outer quotes)
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Check if lines are whole-line quoted (Google Sheets style)
    whole_line_quoted = all(
        l.startswith('"') and l.endswith('"') and l.count('"') == 2
        for l in raw_lines if l
    )
    
    if whole_line_quoted:
        # Each line is a quoted string containing the CSV row — strip outer quotes and re-parse
        cleaned_lines = [l[1:-1] for l in raw_lines]
        csv_text = "\n".join(cleaned_lines)
    else:
        # Standard CSV — pass through as-is
        csv_text = "\n".join(raw_lines)
    
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
    except Exception:
        raise HTTPException(400, detail="Invalid CSV format.")

    if replace:
        await db.execute(Holding.__table__.delete().where(Holding.portfolio_id == p.id))

    accepted, rejected = [], []
    holdings_dict = {}

    for row in reader:
        # Normalize keys (strip whitespace, lowercase)
        # Handle cases where k might be None or row has extra values
        row = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        
        raw_sym = row.get("symbol", "").strip()
        exc = row.get("exchange", "NSE").strip()
        qty_str = str(row.get("quantity", "0")).strip()
        
        try:
            qty = float(qty_str)
            if qty <= 0: raise ValueError()
        except ValueError:
            rejected.append({"row": row, "reason": "Invalid or negative quantity"})
            continue

        sym, canonical_exc, err = validate_and_normalize(raw_sym, exc)
        if err:
            rejected.append({"row": row, "reason": err})
            continue

        key = f"{sym}.{canonical_exc}"
        holdings_dict[key] = holdings_dict.get(key, 0.0) + qty
        accepted.append(HoldingInput(symbol=sym, exchange=canonical_exc, quantity=qty))

    for key, qty in holdings_dict.items():
        sym, exc = key.split(".")
        db.add(Holding(portfolio_id=p.id, symbol=key, exchange=exc, quantity=qty))
        
    await db.commit()
    
    return CsvUploadResult(
        accepted=accepted,
        rejected=rejected,
        message=f"Processed {len(accepted) + len(rejected)} rows. {len(accepted)} accepted."
    )
