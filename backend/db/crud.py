from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any, Tuple
import datetime
from decimal import Decimal
from .models import (
    Asset,
    Wallet,
    WalletHolding,
    WalletTransaction,
    TransactionType,
    WorldState,
    NewsArticle,
    Simulation,
    # Nouveau RAG
    RagDocument,
    RagChunk,
    RagTrace,
    # Copilot / FedEdge
    CopilotAgent,
    CopilotMission,
    CopilotStateKV,
    CopilotEvent,
    TeachingExample,
    UserFact,
    UserNote,
    CopilotConsciousSnapshot,
)

from ..dot_memory import DoTGraph  

DOT_MEMORY_KEY_TEMPLATE = "agent_v2:{agent_id}:dot_memory"


def get_dot_memory(db: Session, agent_id: str) -> DoTGraph:
    """
    Récupère le DoTGraph pour un agent donné depuis CopilotStateKV.
    Si absent, retourne un graph vide.
    """
    key = DOT_MEMORY_KEY_TEMPLATE.format(agent_id=agent_id)
    row = db.query(CopilotStateKV).filter(CopilotStateKV.key == key).first()
    if row and row.value_json:
        try:
            return DoTGraph.from_dict(row.value_json)
        except Exception:
            # si la structure a changé ou est cassée, repartir sur un nouveau graph
            return DoTGraph()
    return DoTGraph()


def save_dot_memory(db: Session, agent_id: str, graph: DoTGraph) -> None:
    """
    Sauvegarde le DoTGraph d'un agent dans CopilotStateKV.
    """
    key = DOT_MEMORY_KEY_TEMPLATE.format(agent_id=agent_id)
    data = graph.to_dict()
    row = db.query(CopilotStateKV).filter(CopilotStateKV.key == key).first()
    now = datetime.datetime.utcnow()
    if row is None:
        row = CopilotStateKV(key=key, value_json=data, updated_at=now)
        db.add(row)
    else:
        row.value_json = data
        row.updated_at = now
    db.commit()



# ============== Asset CRUD ==============

def create_asset(db: Session, asset_id: str, name: str, symbol: str, 
                coingecko_id: str = None, binance_symbol: str = None,
                logo_url: str = None, description: str = None) -> Asset:
    """Create a new asset"""
    asset = Asset(
        id=asset_id,
        name=name,
        symbol=symbol.upper(),
        coingecko_id=coingecko_id or asset_id,
        binance_symbol=binance_symbol or symbol.upper(),
        logo_url=logo_url,
        description=description
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

def get_asset(db: Session, asset_id: str) -> Optional[Asset]:
    """Get asset by ID"""
    return db.query(Asset).filter(Asset.id == asset_id).first()

def get_asset_by_symbol(db: Session, symbol: str) -> Optional[Asset]:
    """Get asset by symbol"""
    return db.query(Asset).filter(Asset.symbol == symbol.upper()).first()

def get_all_assets(db: Session) -> List[Asset]:
    """Get all assets"""
    return db.query(Asset).order_by(Asset.symbol).all()

def search_assets(db: Session, query: str) -> List[Asset]:
    """Search assets by name or symbol"""
    search_term = f"%{query.upper()}%"
    return db.query(Asset).filter(
        or_(
            Asset.name.ilike(search_term),
            Asset.symbol.ilike(search_term)
        )
    ).order_by(Asset.symbol).all()

# ============== Wallet CRUD ==============

def create_wallet(db: Session, name: str, initial_budget: float = 0.0, user_id: int = None) -> Wallet:
    """Create a new wallet"""
    wallet = Wallet(
        name=name,
        user_id=user_id,
        initial_budget_usd=Decimal(str(initial_budget)),
        total_value_usd=Decimal('0')
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet

def get_wallet(db: Session, wallet_id: int) -> Optional[Wallet]:
    """Get wallet by ID"""
    return db.query(Wallet).filter(Wallet.id == wallet_id).first()

def get_wallet_by_name(db: Session, name: str) -> Optional[Wallet]:
    """Get wallet by name (case-insensitive)"""
    return db.query(Wallet).filter(Wallet.name.ilike(name)).first()

def get_user_wallets(db: Session, user_id: int = None) -> List[Wallet]:
    """Get all wallets for a user (or all wallets if user_id is None)"""
    query = db.query(Wallet)
    if user_id is not None:
        query = query.filter(Wallet.user_id == user_id)
    return query.order_by(Wallet.created_at.desc()).all()

def update_wallet(db: Session, wallet_id: int, **kwargs) -> Optional[Wallet]:
    """Update wallet"""
    wallet = get_wallet(db, wallet_id)
    if wallet:
        for key, value in kwargs.items():
            if hasattr(wallet, key):
                setattr(wallet, key, value)
        wallet.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(wallet)
    return wallet

def delete_wallet(db: Session, wallet_id: int) -> bool:
    """Delete a wallet and all its holdings and transactions"""
    wallet = get_wallet(db, wallet_id)
    if not wallet:
        return False
    
    # Delete all associated holdings
    db.query(WalletHolding).filter(WalletHolding.wallet_id == wallet_id).delete()
    
    # Delete all associated transactions
    db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet_id).delete()
    
    # Delete the wallet
    db.delete(wallet)
    db.commit()
    return True

# ============== Wallet Holdings CRUD ==============

def create_or_update_holding(db: Session, wallet_id: int, asset_id: str, 
                           quantity: Decimal, price: Decimal) -> WalletHolding:
    """Create or update a wallet holding"""
    holding = get_holding(db, wallet_id, asset_id)
    
    if holding:
        # Update existing holding with weighted average price
        old_total_value = holding.quantity * holding.average_buy_price
        new_total_value = quantity * price
        total_quantity = holding.quantity + quantity
        
        if total_quantity > 0:
            holding.average_buy_price = (old_total_value + new_total_value) / total_quantity
        holding.quantity = total_quantity
        holding.updated_at = datetime.datetime.utcnow()
    else:
        # Create new holding
        holding = WalletHolding(
            wallet_id=wallet_id,
            asset_id=asset_id,
            quantity=quantity,
            average_buy_price=price
        )
        db.add(holding)
    
    db.commit()
    db.refresh(holding)
    return holding

def get_wallet_holdings(db: Session, wallet_id: int) -> List[WalletHolding]:
    """Get all holdings for a wallet"""
    return db.query(WalletHolding).filter(
        WalletHolding.wallet_id == wallet_id
    ).filter(WalletHolding.quantity > 0).all()

def get_holding(db: Session, wallet_id: int, asset_id: str) -> Optional[WalletHolding]:
    """Get specific holding"""
    return db.query(WalletHolding).filter(
        and_(
            WalletHolding.wallet_id == wallet_id,
            WalletHolding.asset_id == asset_id
        )
    ).first()

def update_holding_quantity(db: Session, wallet_id: int, asset_id: str, 
                          new_quantity: Decimal) -> Optional[WalletHolding]:
    """Update holding quantity"""
    holding = get_holding(db, wallet_id, asset_id)
    if holding:
        holding.quantity = new_quantity
        holding.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(holding)
    return holding

def get_holding_by_id(db: Session, holding_id: int) -> Optional[WalletHolding]:
    """Get holding by ID"""
    return db.query(WalletHolding).filter(WalletHolding.id == holding_id).first()

def update_holding(db: Session, holding_id: int, **kwargs) -> Optional[WalletHolding]:
    """Update holding with given fields"""
    holding = get_holding_by_id(db, holding_id)
    if not holding:
        return None
    
    for key, value in kwargs.items():
        if hasattr(holding, key):
            setattr(holding, key, value)
    
    holding.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(holding)
    return holding

def delete_holding(db: Session, holding_id: int) -> bool:
    """Delete a holding"""
    holding = get_holding_by_id(db, holding_id)
    if not holding:
        return False
    
    db.delete(holding)
    db.commit()
    return True

def calculate_wallet_value(db: Session, wallet_id: int, 
                         current_prices: Dict[str, Decimal] = None) -> Dict[str, Any]:
    """Calculate total wallet value using current market prices"""
    holdings = get_wallet_holdings(db, wallet_id)
    
    total_value = Decimal('0')
    holdings_detail = []
    
    for holding in holdings:
        # Récupérer l'asset pour obtenir le coingecko_id
        asset = get_asset(db, holding.asset_id)
        coingecko_id = asset.coingecko_id if asset else holding.asset_id
        
        # Récupérer le prix actuel ou utiliser le prix d'achat moyen
        if current_prices and coingecko_id in current_prices:
            current_price = Decimal(str(current_prices[coingecko_id]['usd']))
        elif holding.average_buy_price and holding.average_buy_price > 0:
            current_price = holding.average_buy_price
        else:
            # Si pas de prix d'achat ET pas de prix actuel, essayer de récupérer depuis l'API
            try:
                from ..collectors.price_collector import fetch_crypto_prices
                fresh_prices = fetch_crypto_prices()
                if fresh_prices and coingecko_id in fresh_prices:
                    current_price = Decimal(str(fresh_prices[coingecko_id]['usd']))
                else:
                    current_price = Decimal('0')  # Fallback
            except:
                current_price = Decimal('0')  # Fallback en cas d'erreur
        
        holding_value = holding.quantity * current_price
        cost_basis = holding.quantity * (holding.average_buy_price or current_price)
        pnl = holding_value - cost_basis
        pnl_percentage = (pnl / cost_basis * 100) if cost_basis > 0 else Decimal('0')
        
        holdings_detail.append({
            "asset_id": holding.asset_id,
            "quantity": holding.quantity,
            "average_buy_price": holding.average_buy_price,
            "current_price": current_price,
            "current_value": holding_value,
            "cost_basis": cost_basis,
            "pnl": pnl,
            "pnl_percentage": pnl_percentage
        })
        
        total_value += holding_value
    
    return {
        "total_value": total_value,
        "holdings_count": len(holdings),
        "holdings": holdings_detail
    }

# ============== Wallet Transactions CRUD ==============

def create_transaction(db: Session, wallet_id: int, asset_id: str,
                      transaction_type: TransactionType, quantity: Decimal,
                      price_at_time: Decimal, fee: Decimal = Decimal('0'),
                      notes: str = None) -> WalletTransaction:
    """Create a new wallet transaction and update holdings"""
    
    # Create transaction record
    transaction = WalletTransaction(
        wallet_id=wallet_id,
        asset_id=asset_id,
        type=transaction_type,
        amount=quantity,
        price_at_time=price_at_time,
        total_value=quantity * price_at_time,
        fees=fee,
        reasoning=notes
    )
    db.add(transaction)
    
    # Update holdings based on transaction type
    if transaction_type == TransactionType.BUY:
        # Add to holdings
        create_or_update_holding(db, wallet_id, asset_id, quantity, price_at_time)
    elif transaction_type == TransactionType.SELL:
        # Reduce holdings
        holding = get_holding(db, wallet_id, asset_id)
        if holding:
            new_quantity = holding.quantity - quantity
            update_holding_quantity(db, wallet_id, asset_id, max(new_quantity, Decimal('0')))
    # For TRANSFER, we might need additional logic depending on requirements
    
    db.commit()
    db.refresh(transaction)
    return transaction

def get_wallet_transactions(db: Session, wallet_id: int, 
                          limit: int = None, offset: int = 0) -> List[WalletTransaction]:
    """Get wallet transaction history"""
    query = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id == wallet_id
    ).order_by(WalletTransaction.timestamp.desc())
    
    if limit:
        query = query.limit(limit).offset(offset)
    
    return query.all()

def get_asset_transactions(db: Session, wallet_id: int, asset_id: str) -> List[WalletTransaction]:
    """Get transaction history for specific asset"""
    return db.query(WalletTransaction).filter(
        and_(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.asset_id == asset_id
        )
    ).order_by(WalletTransaction.timestamp.desc()).all()

def get_transactions_by_type(db: Session, wallet_id: int, 
                           transaction_type: TransactionType) -> List[WalletTransaction]:
    """Get transactions by type"""
    return db.query(WalletTransaction).filter(
        and_(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.type == transaction_type
        )
    ).order_by(WalletTransaction.timestamp.desc()).all()

def calculate_wallet_pnl(db: Session, wallet_id: int, 
                          current_prices: Dict[str, Decimal] = None) -> Dict[str, Any]:
    """Calculate profit/loss for wallet using FIFO method"""
    transactions = get_wallet_transactions(db, wallet_id)
    holdings = get_wallet_holdings(db, wallet_id)
    
    total_invested = Decimal('0')
    total_current_value = Decimal('0')
    realized_pnl = Decimal('0')
    
    # Calculate realized P&L from completed buy/sell pairs
    asset_positions = {}
    
    for tx in reversed(transactions):  # Process in chronological order
        asset_id = tx.asset_id
        if asset_id not in asset_positions:
            asset_positions[asset_id] = []
        
        if tx.type == TransactionType.BUY:
            asset_positions[asset_id].append({
                'quantity': tx.amount,
                'price': tx.price_at_time,
                'timestamp': tx.timestamp
            })
        elif tx.type == TransactionType.SELL:
            # Calculate realized P&L using FIFO
            remaining_to_sell = tx.amount
            sell_price = tx.price_at_time
            
            while remaining_to_sell > 0 and asset_positions[asset_id]:
                buy_position = asset_positions[asset_id][0]
                
                if buy_position['quantity'] <= remaining_to_sell:
                    # Fully close this buy position
                    quantity_sold = buy_position['quantity']
                    realized_pnl += quantity_sold * (sell_price - buy_position['price'])
                    remaining_to_sell -= quantity_sold
                    asset_positions[asset_id].pop(0)
                else:
                    # Partially close this buy position
                    quantity_sold = remaining_to_sell
                    realized_pnl += quantity_sold * (sell_price - buy_position['price'])
                    buy_position['quantity'] -= quantity_sold
                    remaining_to_sell = Decimal('0')
    
    # Calculate unrealized P&L from current holdings
    for holding in holdings:
        cost_basis = holding.quantity * holding.average_buy_price
        total_invested += cost_basis
        
        current_price = (current_prices.get(holding.asset_id, holding.average_buy_price)
                        if current_prices else holding.average_buy_price)
        current_value = holding.quantity * current_price
        total_current_value += current_value
    
    unrealized_pnl = total_current_value - total_invested
    total_pnl = realized_pnl + unrealized_pnl
    
    return {
        "total_invested": total_invested,
        "current_value": total_current_value,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "total_pnl_percentage": (total_pnl / total_invested * 100) if total_invested > 0 else Decimal('0')
    }

# ============== Analytics and Reporting ==============

def get_wallet_performance_summary(db: Session, wallet_id: int, 
                                 days: int = 30) -> Dict[str, Any]:
    """Get wallet performance summary for specified period"""
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    # Get transactions in period
    recent_transactions = db.query(WalletTransaction).filter(
        and_(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.timestamp >= cutoff_date
        )
    ).all()
    
    # Calculate metrics
    total_buy_volume = sum(
        tx.amount * tx.price_at_time 
        for tx in recent_transactions 
        if tx.type == TransactionType.BUY
    )
    
    total_sell_volume = sum(
        tx.amount * tx.price_at_time 
        for tx in recent_transactions 
        if tx.type == TransactionType.SELL
    )
    
    transaction_count = len(recent_transactions)
    unique_assets = len(set(tx.asset_id for tx in recent_transactions))
    
    return {
        "period_days": days,
        "transaction_count": transaction_count,
        "unique_assets_traded": unique_assets,
        "total_buy_volume": total_buy_volume,
        "total_sell_volume": total_sell_volume,
        "net_flow": total_buy_volume - total_sell_volume
    }

def get_asset_allocation(db: Session, wallet_id: int, 
                       current_prices: Dict[str, Decimal] = None) -> List[Dict[str, Any]]:
    """Get asset allocation breakdown for wallet"""
    holdings = get_wallet_holdings(db, wallet_id)
    wallet_value = calculate_wallet_value(db, wallet_id, current_prices)
    total_value = wallet_value["total_value"]
    
    allocation = []
    for holding in holdings:
        current_price = (current_prices.get(holding.asset_id, holding.average_buy_price)
                        if current_prices else holding.average_buy_price)
        
        holding_value = holding.quantity * current_price
        percentage = (holding_value / total_value * 100) if total_value > 0 else Decimal('0')
        
        allocation.append({
            "asset_id": holding.asset_id,
            "quantity": holding.quantity,
            "value": holding_value,
            "percentage": percentage,
            "average_buy_price": holding.average_buy_price,
            "current_price": current_price
        })
    
    # Sort by value descending
    return sorted(allocation, key=lambda x: x["value"], reverse=True)

# ============== Initialization and Utilities ==============

def init_default_assets(db: Session):
    """Initialize database with cryptocurrency assets from CoinGecko top 250"""
    existing_count = db.query(Asset).count()
    
    if existing_count > 50:  # Si on a déjà beaucoup d'assets, pas besoin de re-initialiser
        print(f"ℹ️  Database already contains {existing_count} assets - skipping initialization")
        return
    
    try:
        # Utiliser le registre crypto pour obtenir les top 250
        from ..utils.crypto_registry import get_crypto_registry
        
        print("🔄 Récupération des top 250 cryptos depuis CoinGecko...")
        registry = get_crypto_registry()
        registry_data = registry.get_registry()
        
        if registry_data and 'assets' in registry_data:
            assets_added = 0
            for asset_data in registry_data['assets']:
                # Vérifier si l'asset existe déjà
                existing_asset = db.query(Asset).filter(Asset.id == asset_data['id']).first()
                if not existing_asset:
                    asset = Asset(
                        id=asset_data["id"],
                        name=asset_data["name"],
                        symbol=asset_data["symbol"],
                        coingecko_id=asset_data["id"],
                        binance_symbol=asset_data.get("symbol", asset_data["symbol"]),  # Utiliser symbol par défaut
                        logo_url=asset_data.get("image"),
                        description=f"Market cap rank: {asset_data.get('market_cap_rank', 'N/A')}"
                    )
                    db.add(asset)
                    assets_added += 1
            
            if assets_added > 0:
                db.commit()
                print(f"✅ Initialized {assets_added} assets from CoinGecko top 250")
            else:
                print("ℹ️  All assets already exist in database")
        else:
            print("⚠️  Registre crypto vide, initialisation des assets essentiels...")
            init_essential_assets_fallback(db)
            
    except Exception as e:
        print(f"❌ Erreur récupération assets CoinGecko: {e}")
        print("⚠️  Fallback vers les assets essentiels...")
        init_essential_assets_fallback(db)

def init_essential_assets_fallback(db: Session):
    """Fallback pour initialiser quelques assets essentiels en cas d'erreur"""
    essential_assets = [
        {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"},
        {"id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
        {"id": "tether", "name": "Tether", "symbol": "USDT"},
        {"id": "usd-coin", "name": "USD Coin", "symbol": "USDC"},
    ]
    
    for asset_data in essential_assets:
        existing = db.query(Asset).filter(Asset.id == asset_data["id"]).first()
        if not existing:
            asset = Asset(
                id=asset_data["id"],
                name=asset_data["name"],
                symbol=asset_data["symbol"],
                coingecko_id=asset_data["id"],
                binance_symbol=asset_data["symbol"]
            )
            db.add(asset)
    
    db.commit()
    print(f"✅ Initialized {len(essential_assets)} essential assets (fallback)")

def init_default_wallet_and_simulation(db: Session):
    """Initialize default wallet with USDC holding and default scalp simulation"""
    # Vérifier si un wallet par défaut existe déjà
    default_wallet = get_wallet_by_name(db, "default")

    if default_wallet:
        print(f"ℹ️  Default wallet already exists (ID: {default_wallet.id})")
    else:
        # Créer le wallet par défaut
        default_wallet = create_wallet(
            db=db,
            name="default",
            initial_budget=1000.0,
            user_id=None
        )
        print(f"✅ Created default wallet (ID: {default_wallet.id})")

    # Vérifier si l'asset USDC existe, sinon le créer
    usdc_asset = get_asset(db, "usd-coin")
    if not usdc_asset:
        usdc_asset = create_asset(
            db=db,
            asset_id="usd-coin",
            name="USD Coin",
            symbol="USDC",
            coingecko_id="usd-coin",
            binance_symbol="USDC",
            description="Stablecoin pegged to USD"
        )
        print("✅ Created USDC asset")

    # Vérifier si le holding USDC existe déjà
    usdc_holding = get_holding(db, default_wallet.id, "usd-coin")

    if not usdc_holding:
        # Créer le holding USDC de 1000 USDC
        usdc_holding = create_or_update_holding(
            db=db,
            wallet_id=default_wallet.id,
            asset_id="usd-coin",
            quantity=Decimal('1000'),
            price=Decimal('1.0')  # USDC = 1 USD
        )
        print(f"✅ Added 1000 USDC to default wallet")
    else:
        print(f"ℹ️  USDC holding already exists ({usdc_holding.quantity} USDC)")

    # Vérifier si une simulation par défaut existe déjà
    default_simulation = db.query(Simulation).filter(
        Simulation.name == "Default Scalp Strategy"
    ).first()

    if not default_simulation:
        # Créer la simulation par défaut (scalp toutes les 15 minutes)
        default_simulation = create_simulation(
            db=db,
            name="Default Scalp Strategy",
            wallet_id=default_wallet.id,
            strategy="scalp",  # Stratégie de scalping
            frequency_minutes=15,  # Toutes les 15 minutes
            description="Default scalp simulation running every 15 minutes"
        )
        print(f"✅ Created default scalp simulation (ID: {default_simulation.id})")
    else:
        print(f"ℹ️  Default simulation already exists (ID: {default_simulation.id})")

    return {
        "wallet": default_wallet,
        "usdc_holding": usdc_holding,
        "simulation": default_simulation
    }

def cleanup_old_transactions(db: Session, days_to_keep: int = 365):
    """Clean up old transactions to save space"""
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_to_keep)

    deleted_count = db.query(WalletTransaction).filter(
        WalletTransaction.timestamp < cutoff_date
    ).delete()

    db.commit()
    print(f"🧹 Cleaned up {deleted_count} old transactions")

# ============== Complete Wallet Report ==============

def generate_wallet_report(db: Session, wallet_id: int, 
                         current_prices: Dict[str, Decimal] = None) -> Dict[str, Any]:
    """Generate comprehensive wallet report"""
    wallet = get_wallet(db, wallet_id)
    if not wallet:
        return None
    
    # Basic wallet info
    wallet_value = calculate_wallet_value(db, wallet_id, current_prices)
    pnl_data = calculate_wallet_pnl(db, wallet_id, current_prices)
    performance_summary = get_wallet_performance_summary(db, wallet_id)
    asset_allocation = get_asset_allocation(db, wallet_id, current_prices)
    recent_transactions = get_wallet_transactions(db, wallet_id, limit=10)
    
    return {
        "wallet": {
            "id": wallet.id,
            "name": wallet.name,
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at
        },
        "wallet_value": {
            "total_value": wallet_value["total_value"],
            "holdings_count": wallet_value["holdings_count"]
        },
        "performance": {
            "total_invested": pnl_data["total_invested"],
            "current_value": pnl_data["current_value"],
            "total_pnl": pnl_data["total_pnl"],
            "total_pnl_percentage": pnl_data["total_pnl_percentage"],
            "realized_pnl": pnl_data["realized_pnl"],
            "unrealized_pnl": pnl_data["unrealized_pnl"]
        },
        "recent_activity": performance_summary,
        "asset_allocation": asset_allocation,
        "recent_transactions": [
            {
                "timestamp": tx.timestamp,
                "asset_id": tx.asset_id,
                "type": tx.type.value,
                "quantity": tx.amount,
                "price": tx.price_at_time,
                "fee": tx.fees,
                "tx_hash": tx.tx_hash
            }
            for tx in recent_transactions
        ]
    }


# ============== World Context CRUD ==============

def get_world_context(db: Session) -> Optional[WorldState]:
    """Récupérer le contexte mondial actuel (ligne unique)"""
    return db.query(WorldState).filter(WorldState.id == 1).first()


def create_or_update_world_context(
    db: Session, 
    world_summary: str, 
    sentiment_score: float = None, 
    key_themes: List[str] = None
) -> WorldState:
    """Créer/MAJ le contexte mondial (toujours id=1), met à jour 'timestamp' pour refléter la fraicheur."""
    world_context = db.query(WorldState).filter(WorldState.id == 1).first()
    now = datetime.datetime.utcnow()

    if world_context:
        world_context.summary = world_summary
        world_context.sentiment_score = sentiment_score
        world_context.key_events = key_themes or []
        world_context.timestamp = now            # ✅ important
    else:
        world_context = WorldState(
            id=1,
            summary=world_summary,
            sentiment_score=sentiment_score,
            key_events=key_themes or [],
            timestamp=now                        # ✅ important
        )
        db.add(world_context)

    db.commit()
    db.refresh(world_context)
    return world_context
    

def get_world_context_for_llm(db: Session) -> str:
    """Récupérer le contexte mondial formaté pour le LLM"""
    world_context = get_world_context(db)
    
    if not world_context:
        return "Aucun contexte mondial disponible"
    
    # Formater pour le LLM
    context_text = f"CONTEXTE MONDIAL (mise à jour: {world_context.timestamp.strftime('%Y-%m-%d %H:%M')}):\n"
    context_text += f"{world_context.summary}\n"
    
    if world_context.sentiment_score is not None:
        sentiment_desc = "positif" if world_context.sentiment_score > 0.1 else "négatif" if world_context.sentiment_score < -0.1 else "neutre"
        context_text += f"Sentiment global: {sentiment_desc} ({world_context.sentiment_score:.2f})\n"
    
    if world_context.key_events:
        context_text += f"Thèmes clés: {', '.join(world_context.key_events)}"
    
    return context_text

def get_market_context_for_llm(db: Session) -> str:
    """Récupérer le contexte de marché formaté pour le LLM"""
    # Pour l'instant, utiliser les données de marché les plus récentes ou un format simple
    # TODO: Implémenter une vraie table MarketState si nécessaire
    try:
        from .models import MarketState
        market_context = db.query(MarketState).order_by(MarketState.timestamp.desc()).first()
        
        if market_context:
            context_text = f"CONTEXTE MARCHÉ (mise à jour: {market_context.timestamp.strftime('%Y-%m-%d %H:%M')}):\n"
            if market_context.total_market_cap:
                context_text += f"Capitalisation totale: ${market_context.total_market_cap/1e12:.1f}T\n"
            if market_context.btc_dominance:
                context_text += f"Dominance BTC: {market_context.btc_dominance:.1f}%\n"
            if market_context.fear_greed_index:
                context_text += f"Index Fear & Greed: {market_context.fear_greed_index}/100\n"
            return context_text
        else:
            # Fallback: générer un contexte basé sur les données de prix récentes
            return "Marchés crypto en consolidation, sentiment mixte, volatilité modérée"
    except:
        return "Marchés crypto en consolidation, sentiment mixte, volatilité modérée"

# ============== News Articles CRUD ==============

def create_news_article(
    db: Session,
    title: str,
    content: str,
    source: str,
    url: str = None,
    author: str = None,
    published_date: datetime.datetime = None,
    category: str = None,
    sentiment_score: float = None,
    relevance_score: float = None,
    keywords: List[str] = None,
    mentioned_assets: List[str] = None,
    summary: str = None
) -> NewsArticle:
    """Créer un nouvel article de news avec gestion des doublons"""
    
    # Vérification finale de doublon au niveau CRUD (sécurité supplémentaire)
    if url:
        existing = get_news_article_by_url(db, url)
        if existing:
            print(f"⚠️ Article avec URL déjà existant: {url}")
            return existing
    
    article = NewsArticle(
        title=title,
        content=content,
        source=source,
        url=url,
        author=author,
        published_at=published_date or datetime.datetime.utcnow(),
        sentiment_score=sentiment_score,
        relevance_score=relevance_score,
        crypto_mentions=mentioned_assets or [],
        summary=summary,
        keywords=keywords or [],
        mentioned_assets=mentioned_assets or [],
        category=category
    )
    
    try:
        db.add(article)
        db.commit()
        db.refresh(article)

        # Extract data BEFORE any potential async operations to avoid SQLite thread issues
        article_id = article.id
        article_title = article.title
        article_content = article.content
        article_summary = article.summary or ""

        # NOTE: Embedding generation is now caller's responsibility to avoid thread issues
        # Caller should call _trigger_embedding_generation_safe() after closing their session
        # Example:
        #   article = crud.create_news_article(db, ...)
        #   db.close()
        #   crud._trigger_embedding_generation_safe(article.id, article.title, ...)

        return article
    except Exception as e:
        # Rollback en cas d'erreur
        db.rollback()
        # Si c'est une erreur de contrainte d'unicité, essayer de récupérer l'article existant
        if "UNIQUE constraint" in str(e) and url:
            existing = get_news_article_by_url(db, url)
            if existing:
                print(f"⚠️ Doublon détecté, retour de l'article existant: {url}")
                return existing
        # Sinon, re-lancer l'erreur
        raise e

def get_news_article(db: Session, article_id: int) -> Optional[NewsArticle]:
    """Récupérer un article par ID"""
    return db.query(NewsArticle).filter(NewsArticle.id == article_id).first()

def get_news_article_by_url(db: Session, url: str) -> Optional[NewsArticle]:
    """Récupérer un article par URL (pour éviter les doublons)"""
    return db.query(NewsArticle).filter(NewsArticle.url == url).first()

def get_recent_news_articles(
    db: Session, 
    limit: int = 50, 
    hours_back: int = 24,
    source: str = None,
    category: str = None,
    min_relevance: float = None,
    only_active: bool = True
) -> List[NewsArticle]:
    """Récupérer les articles récents avec filtres"""
    
    query = db.query(NewsArticle)

    # EXCLUDE knowledge documents (RAG uploads) from news
    query = query.filter(NewsArticle.category != 'knowledge')

    # Filtre par date
    since_date = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    query = query.filter(NewsArticle.scraped_date >= since_date)

    # Filtres optionnels
    if source:
        query = query.filter(NewsArticle.source == source)
    
    if category:
        query = query.filter(NewsArticle.category == category)
    
    if min_relevance is not None:
        query = query.filter(NewsArticle.relevance_score >= min_relevance)
    
    if only_active:
        query = query.filter(NewsArticle.is_active == True)
    
    return query.order_by(NewsArticle.published_at.desc()).limit(limit).all()

def get_unprocessed_news_articles(db: Session, limit: int = 20) -> List[NewsArticle]:
    """Récupérer les articles non encore traités par l'IA"""
    return db.query(NewsArticle).filter(
        NewsArticle.is_processed == False,
        NewsArticle.category != 'knowledge',
        NewsArticle.is_active == True
    ).order_by(NewsArticle.scraped_date.asc()).limit(limit).all()

def mark_article_processed(
    db: Session, 
    article_id: int, 
    summary: str = None,
    sentiment_score: float = None,
    relevance_score: float = None,
    keywords: List[str] = None,
    mentioned_assets: List[str] = None,
    category: str = None
) -> Optional[NewsArticle]:
    """Marquer un article comme traité et mettre à jour ses métadonnées"""
    
    article = get_news_article(db, article_id)
    if not article:
        return None
    
    article.is_processed = True
    
    if summary is not None:
        article.summary = summary
    if sentiment_score is not None:
        article.sentiment_score = sentiment_score
    if relevance_score is not None:
        article.relevance_score = relevance_score
    if keywords is not None:
        article.keywords = keywords
    if mentioned_assets is not None:
        article.mentioned_assets = mentioned_assets
    if category is not None:
        article.category = category
    
    db.commit()
    db.refresh(article)
    return article

def mark_article_embedded(
    db: Session, 
    article_id: int, 
    embedding_model: str
) -> Optional[NewsArticle]:
    """Marquer un article comme vectorisé pour RAG"""
    
    article = get_news_article(db, article_id)
    if not article:
        return None
    
    article.embedding_generated = True
    article.embedding_model = embedding_model
    article.embedding_date = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(article)
    return article

def get_articles_for_world_context_generation(
    db: Session, 
    hours_back: int = 12, 
    min_relevance: float = 0.5,
    limit: int = 30
) -> List[NewsArticle]:
    """Récupérer les articles pertinents pour générer le contexte mondial"""
    
    since_date = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    
    return db.query(NewsArticle).filter(
        NewsArticle.is_processed == True,
        NewsArticle.is_active == True,
        NewsArticle.scraped_date >= since_date,
        NewsArticle.relevance_score >= min_relevance
    ).order_by(
        NewsArticle.relevance_score.desc(),
        NewsArticle.published_at.desc()
    ).limit(limit).all()

def cleanup_old_news_articles(db: Session, days_to_keep: int = 30) -> int:
    """Nettoyer les anciens articles (marquer comme inactifs)"""
    
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_to_keep)
    
    updated_count = db.query(NewsArticle).filter(
        NewsArticle.scraped_date < cutoff_date,
        NewsArticle.is_active == True
    ).update({"is_active": False})
    
    db.commit()
    return updated_count

def get_news_articles_stats(db: Session) -> Dict[str, Any]:
    """Obtenir les statistiques des articles de news"""
    
    total_articles = db.query(NewsArticle).count()
    active_articles = db.query(NewsArticle).filter(NewsArticle.is_active == True).count()
    processed_articles = db.query(NewsArticle).filter(NewsArticle.is_processed == True).count()
    embedded_articles = db.query(NewsArticle).filter(NewsArticle.embedding_generated == True).count()
    
    # Articles par source
    sources_stats = db.query(
        NewsArticle.source, 
        func.count(NewsArticle.id).label('count')
    ).filter(NewsArticle.is_active == True).group_by(NewsArticle.source).all()
    
    # Articles récents (24h)
    recent_cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    recent_articles = db.query(NewsArticle).filter(
        NewsArticle.scraped_date >= recent_cutoff,
        NewsArticle.is_active == True
    ).count()
    
    return {
        "total_articles": total_articles,
        "active_articles": active_articles,
        "processed_articles": processed_articles,
        "embedded_articles": embedded_articles,
        "recent_24h": recent_articles,
        "processing_rate": (processed_articles / active_articles * 100) if active_articles > 0 else 0,
        "embedding_rate": (embedded_articles / processed_articles * 100) if processed_articles > 0 else 0,
        "sources": [{"source": source, "count": count} for source, count in sources_stats]
    }

# ============== SIMULATION CRUD ==============

def create_simulation(
    db: Session,
    name: str,
    wallet_id: int,
    strategy: str,
    frequency_minutes: int,
    description: str = None
) -> Simulation:
    """Créer une nouvelle simulation avec next_run_at correctement initialisé"""
    from datetime import datetime, timedelta
    
    # Calculer la prochaine exécution (maintenant + fréquence)
    next_run_at = datetime.utcnow() + timedelta(minutes=frequency_minutes)
    
    simulation = Simulation(
        name=name,
        description=description,
        wallet_id=wallet_id,
        strategy=strategy,
        frequency_minutes=frequency_minutes,
        next_run_at=next_run_at  # Initialiser correctement next_run_at
    )
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    return simulation

def get_simulation(db: Session, simulation_id: int) -> Optional[Simulation]:
    """Récupérer une simulation par ID"""
    return db.query(Simulation).filter(Simulation.id == simulation_id).first()

def get_simulation_by_name(db: Session, name: str) -> Optional[Simulation]:
    """Récupérer une simulation par nom"""
    return db.query(Simulation).filter(Simulation.name == name).first()

def get_simulations(db: Session, active_only: bool = False) -> List[Simulation]:
    """Récupérer toutes les simulations"""
    query = db.query(Simulation)
    if active_only:
        query = query.filter(Simulation.is_active == True)
    return query.order_by(Simulation.created_at.desc()).all()

def get_simulations_for_wallet(db: Session, wallet_id: int, active_only: bool = False) -> List[Simulation]:
    """Récupérer les simulations d'un wallet spécifique"""
    query = db.query(Simulation).filter(Simulation.wallet_id == wallet_id)
    if active_only:
        query = query.filter(Simulation.is_active == True)
    return query.order_by(Simulation.created_at.desc()).all()

def update_simulation(
    db: Session,
    simulation_id: int,
    name: str = None,
    description: str = None,
    strategy: str = None,
    frequency_minutes: int = None,
    is_active: bool = None,
    is_running: bool = None
) -> Optional[Simulation]:
    """Mettre à jour une simulation"""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        return None
    
    if name is not None:
        simulation.name = name
    if description is not None:
        simulation.description = description
    if strategy is not None:
        simulation.strategy = strategy
    if frequency_minutes is not None:
        simulation.frequency_minutes = frequency_minutes
    if is_active is not None:
        simulation.is_active = is_active
    if is_running is not None:
        simulation.is_running = is_running
    
    db.commit()
    db.refresh(simulation)
    return simulation

def delete_simulation(db: Session, simulation_id: int) -> bool:
    """Supprimer une simulation"""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        return False
    
    db.delete(simulation)
    db.commit()
    return True

def update_simulation_stats(
    db: Session,
    simulation_id: int,
    last_run_at: datetime.datetime = None,
    next_run_at: datetime.datetime = None,
    success: bool = True,
    error: str = None
) -> Optional[Simulation]:
    """Mettre à jour les statistiques d'une simulation après exécution"""
    from datetime import datetime, timedelta
    
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        return None
    
    if last_run_at:
        simulation.last_run_at = last_run_at
    
    # S'assurer que next_run_at est toujours défini correctement
    if next_run_at:
        simulation.next_run_at = next_run_at
    else:
        # Calculer automatiquement la prochaine exécution si non fournie
        simulation.next_run_at = datetime.utcnow() + timedelta(minutes=simulation.frequency_minutes)
    
    simulation.total_runs += 1
    
    if success:
        simulation.successful_runs += 1
        simulation.last_error = None
    else:
        simulation.failed_runs += 1
        if error:
            simulation.last_error = error
    
    db.commit()
    db.refresh(simulation)
    return simulation

def get_active_simulations_to_run(db: Session) -> List[Simulation]:
    """Récupérer les simulations actives prêtes à être exécutées"""
    current_time = datetime.datetime.utcnow()
    return db.query(Simulation).filter(
        Simulation.is_active == True,
        # Retirer is_running == True pour permettre aux simulations de redémarrer
        or_(
            Simulation.next_run_at.is_(None),
            Simulation.next_run_at <= current_time
        )
    ).all()

def set_simulation_running(db: Session, simulation_id: int, is_running: bool) -> bool:
    """Marquer une simulation comme en cours d'exécution ou non"""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        return False
    
    simulation.is_running = is_running
    db.commit()
    return True


    # ============== RAG HELPERS (NOUVEAU SYSTÈME) ==============

def get_or_create_rag_document(
    db: Session,
    *,
    title: str,
    url: Optional[str] = None,
    domain: Optional[str] = None,
    file_path: Optional[str] = None,
) -> RagDocument:
    """
    Récupère un RagDocument par URL s'il existe, sinon le crée.
    """
    if url:
        existing = db.query(RagDocument).filter(RagDocument.url == url).first()
        if existing:
            return existing

    doc = RagDocument(
        title=title,
        url=url,
        domain=domain,
        file_path=file_path,
        downloaded_at=datetime.datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def add_rag_chunk(
    db: Session,
    *,
    doc_id: int,
    content: str,
    embedding_bytes: bytes,
    page_number: Optional[int] = None,
    chunk_index: int = 0,
    domain: Optional[str] = None,
) -> RagChunk:
    """
    Ajoute un chunk lié à un RagDocument.
    embedding_bytes = vecteur numpy.float32.tobytes()
    """
    chunk = RagChunk(
        doc_id=doc_id,
        content=content,
        embedding=embedding_bytes,
        page_number=page_number,
        chunk_index=chunk_index,
        domain=domain,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def get_rag_document(db: Session, doc_id: int) -> Optional[RagDocument]:
    """Récupère un RagDocument par ID."""
    return db.query(RagDocument).filter(RagDocument.id == doc_id).first()


def get_rag_document_by_url(db: Session, url: str) -> Optional[RagDocument]:
    """Récupère un RagDocument par URL."""
    return db.query(RagDocument).filter(RagDocument.url == url).first()


def get_rag_chunks_by_domain(
    db: Session,
    *,
    domain: Optional[str] = None,
) -> List[RagChunk]:
    """
    Retourne tous les chunks pour un domaine donné (ou tous si domain=None).
    Attention : potentiellement volumineux.
    """
    q = db.query(RagChunk)
    if domain:
        q = q.filter(RagChunk.domain == domain)
    return q.all()


def search_rag_chunks(
    db: Session,
    *,
    query_embedding: "np.ndarray",
    domain: Optional[str] = None,
    top_k: int = 5,
) -> List[Tuple[RagChunk, float]]:
    """
    Recherche par similarité cosine dans les chunks RAG.

    Args:
        db: Session SQLAlchemy
        query_embedding: Vecteur numpy de la query (doit être normalisé)
        domain: Filtre optionnel par domaine
        top_k: Nombre de résultats à retourner

    Returns:
        Liste de tuples (chunk, similarité) triée par similarité décroissante
    """
    import numpy as np

    # Récupérer les chunks (avec filtre domaine optionnel)
    q = db.query(RagChunk).filter(RagChunk.embedding.isnot(None))
    if domain:
        q = q.filter(RagChunk.domain == domain)

    chunks = q.all()

    if not chunks:
        return []

    # Calculer les similarités
    results = []
    query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

    for chunk in chunks:
        # Désérialiser l'embedding (stocké en BLOB)
        try:
            chunk_emb = np.frombuffer(chunk.embedding, dtype=np.float32)
            chunk_norm = chunk_emb / (np.linalg.norm(chunk_emb) + 1e-8)

            # Similarité cosine
            similarity = float(np.dot(query_norm, chunk_norm))
            results.append((chunk, similarity))
        except Exception as e:
            # Skip chunks avec embeddings corrompus
            continue

    # Trier par similarité décroissante et retourner top_k
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def create_rag_trace(
    db: Session,
    *,
    question: str,
    chunk_ids: List[int],
    model: str,
    latency_ms: int,
    answer_preview: str,
    full_answer: str,
    sources: List[Dict[str, Any]],
) -> RagTrace:
    """
    Log d'une requête RAG.
    sources = [{ "title": ..., "url": ..., "chunk": ... }, ...]
    """
    trace = RagTrace(
        timestamp=datetime.datetime.utcnow(),
        question=question,
        chunk_ids=chunk_ids,
        model=model,
        latency_ms=latency_ms,
        answer_preview=answer_preview,
        full_answer=full_answer,
        sources=sources,
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace


# ============== COPILOT / FEDEDGE HELPERS ==============

# ---- CopilotAgent & CopilotMission ----

def get_copilot_agent(db: Session, agent_id: str) -> Optional[CopilotAgent]:
    return db.query(CopilotAgent).filter(CopilotAgent.id == agent_id).first()


def get_or_create_copilot_agent(
    db: Session,
    *,
    agent_id: str,
    name: str,
    role: str,
    mission: str,
    profile_json: Dict[str, Any],
) -> CopilotAgent:
    agent = get_copilot_agent(db, agent_id)
    if agent:
        return agent

    agent = CopilotAgent(
        id=agent_id,
        name=name,
        role=role,
        mission=mission,
        profile_json=profile_json,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def create_copilot_mission(
    db: Session,
    *,
    agent_id: str,
    name: str,
    description: str,
    kind: str,
    priority: int = 5,
    status: str = "active",
    schedule_cron: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> CopilotMission:
    mission = CopilotMission(
        agent_id=agent_id,
        name=name,
        description=description,
        kind=kind,
        status=status,
        priority=priority,
        schedule_cron=schedule_cron,
        config=config or {},
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def list_active_missions(
    db: Session,
    *,
    agent_id: Optional[str] = None,
) -> List[CopilotMission]:
    q = db.query(CopilotMission).filter(CopilotMission.status == "active")
    if agent_id:
        q = q.filter(CopilotMission.agent_id == agent_id)
    return q.order_by(CopilotMission.priority.asc()).all()


def update_mission_run_times(
    db: Session,
    mission_id: int,
    *,
    last_run_ts: Optional[datetime.datetime] = None,
    next_run_ts: Optional[datetime.datetime] = None,
) -> None:
    mission = db.query(CopilotMission).filter(CopilotMission.id == mission_id).first()
    if not mission:
        return
    if last_run_ts:
        mission.last_run_ts = last_run_ts
    if next_run_ts:
        mission.next_run_ts = next_run_ts
    db.commit()


# ---- CopilotStateKV ----

def get_copilot_state(db: Session, key: str) -> Optional[Dict[str, Any]]:
    row = db.query(CopilotStateKV).filter(CopilotStateKV.key == key).first()
    return row.value_json if row else None


def set_copilot_state(db: Session, key: str, value: Dict[str, Any]) -> CopilotStateKV:
    row = db.query(CopilotStateKV).filter(CopilotStateKV.key == key).first()
    now = datetime.datetime.utcnow()
    if row is None:
        row = CopilotStateKV(
            key=key,
            value_json=value,
            updated_at=now,
        )
        db.add(row)
    else:
        row.value_json = value
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


# ---- CopilotEvent ----

def log_copilot_event(
    db: Session,
    *,
    event_id: str,
    topic: str,
    type: str,
    source: str,
    payload: Dict[str, Any],
) -> CopilotEvent:
    evt = CopilotEvent(
        id=event_id,
        ts=datetime.datetime.utcnow(),
        topic=topic,
        type=type,
        source=source,
        payload=payload,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def get_recent_copilot_events(
    db: Session,
    *,
    topic: Optional[str] = None,
    limit: int = 100,
) -> List[CopilotEvent]:
    q = db.query(CopilotEvent).order_by(CopilotEvent.ts.desc())
    if topic:
        q = q.filter(CopilotEvent.topic == topic)
    return q.limit(limit).all()


# ---- TeachingExample ----

def create_teaching_example(
    db: Session,
    *,
    source_type: str,
    source_id: Optional[str],
    level: str,
    input_text: str,
    target_text: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TeachingExample:
    ex = TeachingExample(
        source_type=source_type,
        source_id=source_id,
        level=level,
        input_text=input_text,
        target_text=target_text,
        tags_json=tags or [],
        metadata_json=metadata or {},
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


def list_teaching_examples(
    db: Session,
    *,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
) -> List[TeachingExample]:
    q = db.query(TeachingExample).order_by(TeachingExample.created_at.desc())
    if level:
        q = q.filter(TeachingExample.level == level)
    if tag:
        q = q.filter(func.json_extract(TeachingExample.tags_json, "$") != None)
        # Filtrage simple: tag in tags_json (SQLite JSON: on peut raffiner plus tard)
    return q.limit(limit).all()


def mark_teaching_example_used(db: Session, example_id: int) -> None:
    ex = db.query(TeachingExample).filter(TeachingExample.id == example_id).first()
    if not ex:
        return
    ex.used_for_train = True
    ex.updated_at = datetime.datetime.utcnow()
    db.commit()


# ---- UserFact & UserNote ----

def upsert_user_fact(
    db: Session,
    *,
    user_id: int,
    key: str,
    value: Dict[str, Any],
) -> UserFact:
    fact = (
        db.query(UserFact)
        .filter(UserFact.user_id == user_id, UserFact.key == key)
        .first()
    )
    now = datetime.datetime.utcnow()
    if fact is None:
        fact = UserFact(
            user_id=user_id,
            key=key,
            value_json=value,
            created_at=now,
            updated_at=now,
        )
        db.add(fact)
    else:
        fact.value_json = value
        fact.updated_at = now
    db.commit()
    db.refresh(fact)
    return fact


def get_user_facts(db: Session, user_id: int) -> List[UserFact]:
    return db.query(UserFact).filter(UserFact.user_id == user_id).all()


def create_user_note(
    db: Session,
    *,
    user_id: int,
    note_text: str,
    tags: Optional[List[str]] = None,
    source_event_id: Optional[str] = None,
    wallet_id: Optional[int] = None,
    ticker: Optional[str] = None,
    is_pinned: bool = False,
) -> UserNote:
    note = UserNote(
        user_id=user_id,
        ts=datetime.datetime.utcnow(),
        source_event_id=source_event_id,
        note_text=note_text,
        tags_json=tags or [],
        is_pinned=is_pinned,
        wallet_id=wallet_id,
        ticker=ticker,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_recent_user_notes(
    db: Session,
    *,
    user_id: int,
    limit: int = 50,
) -> List[UserNote]:
    return (
        db.query(UserNote)
        .filter(UserNote.user_id == user_id)
        .order_by(UserNote.ts.desc())
        .limit(limit)
        .all()
    )


# ======================================================================
# CopilotConsciousSnapshot – CRUD
# ======================================================================

def create_conscious_snapshot(
    db: Session,
    *,
    agent_id: str,
    context: dict,
    vital_signals: Optional[dict] = None,   # ou List[dict] si tu préfères
    summary: Optional[str] = None,
    source_event_id: Optional[str] = None,
) -> CopilotConsciousSnapshot:
    """
    Crée un nouveau snapshot de conscience pour un agent donné.

    - agent_id : identifiant logique de l'agent ("fededge_core", "fededge_teacher", ...)
    - context  : JSON complet de l'état de conscience (market, wallets, sims, missions, ...)
    - vital_signals : éventuels signaux vitaux (opportunité trading, crash, annonces FED...)
    - summary : résumé textuel du snapshot (optionnel, pour UI ou debug)
    - source_event_id : id d'un CopilotEvent qui a déclenché ce snapshot (optionnel)
    """
    obj = CopilotConsciousSnapshot(
        agent_id=agent_id,
        context_json=context,
        vital_signals_json=vital_signals,
        summary_text=summary,
        source_event_id=source_event_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_latest_conscious_snapshot(
    db: Session,
    agent_id: str,
) -> Optional[CopilotConsciousSnapshot]:
    """
    Retourne le dernier snapshot de conscience (état courant) pour un agent.

    Si aucun snapshot n'existe, retourne None.
    """
    return (
        db.query(CopilotConsciousSnapshot)
        .filter(CopilotConsciousSnapshot.agent_id == agent_id)
        .order_by(CopilotConsciousSnapshot.ts.desc())
        .first()
    )


def list_conscious_snapshots(
    db: Session,
    agent_id: str,
    *,
    limit: int = 100,
    since: Optional[datetime.datetime] = None,
) -> List[CopilotConsciousSnapshot]:
    """
    Liste les snapshots de conscience d'un agent, triés du plus récent au plus ancien.

    - limit : nombre max de snapshots à retourner.
    - since : si renseigné, ne retourne que les snapshots avec ts >= since.
    """
    q = (
        db.query(CopilotConsciousSnapshot)
        .filter(CopilotConsciousSnapshot.agent_id == agent_id)
    )
    if since is not None:
        q = q.filter(CopilotConsciousSnapshot.ts >= since)

    return (
        q.order_by(CopilotConsciousSnapshot.ts.desc())
        .limit(limit)
        .all()
    )


def prune_conscious_snapshots_before(
    db: Session,
    agent_id: str,
    before: datetime.datetime,
) -> int:
    """
    Supprime les snapshots de conscience STRICTEMENT antérieurs à 'before'
    pour un agent donné. Retourne le nombre de lignes supprimées.

    Utile pour faire du nettoyage si tu gardes un historique très long
    mais que tu veux purger au-delà d'une certaine fenêtre temporelle.
    """
    q = db.query(CopilotConsciousSnapshot).filter(
        CopilotConsciousSnapshot.agent_id == agent_id,
        CopilotConsciousSnapshot.ts < before,
    )
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return deleted

