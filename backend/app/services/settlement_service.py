"""services/settlement_service.py — Service that handles policy maturity evaluation and payoff computation."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.policy import Policy, Settlement, LedgerTransaction
from app.services.market_service import market_service
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)


async def run_settlements(db: AsyncSession, term: Optional[str] = None) -> Dict:
    """Find ACTIVE policies that should mature, compute payoffs, update ledgers, and mark SETTLED."""
    now = datetime.now(timezone.utc)
    
    # 1. Select ACTIVE policies, optionally filtered by term, where end_date has passed
    q = select(Policy).where(Policy.status == "ACTIVE", Policy.end_date <= now)
    if term:
        q = q.where(Policy.term == term.upper())
        
    policies = (await db.execute(q)).scalars().all()
    if not policies:
        return {"term": term, "policies_checked": 0, "policies_settled": 0, "errors": 0, "details": []}

    details = []
    settled = 0
    errors = 0

    for p in policies:
        try:
            # 2. Get ending snapshot of portfolio value
            end_val = 0.0
            for symbol, start_data in p.portfolio_snapshot.items():
                qty = start_data["qty"]
                try:
                    price = market_service.get_current_price(symbol)
                except ValueError:
                    price = start_data["price"] # Fallback if missing
                end_val += (price * qty)

            # 3. Compute Payoff
            res = ml_service.compute_settlement(
                notional=p.notional_inr,
                start_idx=p.start_portfolio_value,
                end_idx=end_val,
                loss_threshold=p.loss_threshold,
                profit_threshold=p.profit_threshold,
                coverage_rate=p.coverage_rate,
                profit_share_rate=p.profit_share_rate,
                max_payout=p.max_payout_inr
            )
            
            # 4. Save Settlement record
            s = Settlement(
                policy_id=p.id,
                end_portfolio_value=end_val,
                portfolio_return_pct=res["portfolio_return"],
                payout_inr=res["payout_inr"],
                surplus_inr=res["surplus_inr"],
                outcome=res["outcome"]
            )
            db.add(s)
            
            # 5. Ledger entries based on outcome
            if res["payout_inr"] > 0:
                tx_payout = LedgerTransaction(
                    policy_id=p.id,
                    tx_type="PAYOUT",
                    amount_inr=-res["payout_inr"],
                    description=f"Market drop {res['portfolio_return']*100:.2f}% < {p.loss_threshold*100:.2f}%."
                )
                db.add(tx_payout)
                
            if res["surplus_inr"] > 0:
                tx_surplus = LedgerTransaction(
                    policy_id=p.id,
                    tx_type="SURPLUS_SHARE",
                    amount_inr=res["surplus_inr"],
                    description=f"Market gain {res['portfolio_return']*100:.2f}% > {p.profit_threshold*100:.1f}%."
                )
                db.add(tx_surplus)

            # 6. Mark Policy SETTLED
            p.status = "SETTLED"
            await db.flush()
            settled += 1
            details.append({"policy_id": str(p.id), "outcome": res["outcome"], "return": res["portfolio_return"]})
            
        except Exception as e:
            logger.error("Error settling policy %s: %s", p.id, e, exc_info=True)
            errors += 1
            details.append({"policy_id": str(p.id), "error": str(e)})

    await db.commit()
    
    return {
        "term": term,
        "policies_checked": len(policies),
        "policies_settled": settled,
        "errors": errors,
        "details": details
    }
