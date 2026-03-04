"""scripts/seed.py — Generate sample users, orgs, and portfolios for the PMRI demo."""
import asyncio
import sys
import os
from pathlib import Path

# Provide access to backend app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.user import User
from app.models.org import Org, OrgMember
from app.models.portfolio import Portfolio, Holding

settings = get_settings()

async def ensure_db_tables():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        import app.models  # trigger registration
        await conn.run_sync(Base.metadata.create_all)
    return engine

async def seed():
    engine = await ensure_db_tables()
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)
    
    async with AsyncSessionLocal() as db:
        print("Seeding DB...")
        
        # 1. Retail User
        retail = User(email="retail@example.com", hashed_password=hash_password("password"), tier="RETAIL")
        db.add(retail)
        
        # 2. Institutional Org + Owner + Member
        inst_owner = User(email="admin@fund.com", hashed_password=hash_password("password"), tier="INSTITUTIONAL_BASIC", is_admin=True)
        inst_trader = User(email="trader@fund.com", hashed_password=hash_password("password"), tier="INSTITUTIONAL_BASIC")
        db.add_all([inst_owner, inst_trader])
        await db.flush()
        
        org = Org(name="Global Macro Fund", tier="INSTITUTIONAL_BASIC")
        db.add(org)
        await db.flush()
        
        db.add(OrgMember(org_id=org.id, user_id=inst_owner.id, role="OWNER"))
        db.add(OrgMember(org_id=org.id, user_id=inst_trader.id, role="MEMBER"))
        
        # 3. Portfolios
        p1 = Portfolio(user_id=retail.id, name="My Retirement (Indian Equities)")
        db.add(p1)
        await db.flush()
        db.add_all([
            Holding(portfolio_id=p1.id, symbol="RELIANCE.NSE", exchange="NSE", quantity=50),
            Holding(portfolio_id=p1.id, symbol="TCS.NSE", exchange="NSE", quantity=20),
            Holding(portfolio_id=p1.id, symbol="HDFCBANK.NSE", exchange="NSE", quantity=100)
        ])
        
        p2 = Portfolio(user_id=inst_owner.id, org_id=org.id, name="Global Tech Alpha")
        db.add(p2)
        await db.flush()
        db.add_all([
            Holding(portfolio_id=p2.id, symbol="AAPL.NASDAQ", exchange="NASDAQ", quantity=1000),
            Holding(portfolio_id=p2.id, symbol="MSFT.NASDAQ", exchange="NASDAQ", quantity=500),
            Holding(portfolio_id=p2.id, symbol="GOOGL.NASDAQ", exchange="NASDAQ", quantity=800),
            Holding(portfolio_id=p2.id, symbol="INFY.NSE", exchange="NSE", quantity=5000)
        ])

        await db.commit()
        print("✅ DB Seeded with Retail and Institutional global portfolios.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
