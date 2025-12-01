"""
Wallet Management Routes
Handles all wallet and holding-related endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
import io
import csv

from ..db.models import SessionLocal
from ..db import crud

router = APIRouter(tags=["wallets"])


# Pydantic models
class WalletCreate(BaseModel):
    name: str
    initial_budget: Optional[float] = 0.0
    user_id: Optional[int] = None


class WalletUpdate(BaseModel):
    name: Optional[str] = None
    initial_budget: Optional[float] = None
    user_id: Optional[int] = None


class HoldingCreate(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: Optional[float] = None


class HoldingUpdate(BaseModel):
    quantity: Optional[float] = None
    avg_buy_price: Optional[float] = None


# Wallet endpoints
@router.get("/wallets")
async def get_wallets(calculate_values: bool = False):
    """Récupérer tous les portefeuilles (avec valeurs optionnelles pour vitesse)"""
    db = SessionLocal()
    try:
        wallets = crud.get_user_wallets(db)

        wallets_data = []
        for wallet in wallets:
            if calculate_values:
                # Récupérer la valeur actuelle du wallet (plus lent)
                wallet_value = crud.calculate_wallet_value(db, wallet.id)
                current_value = float(wallet_value["total_value"])
                holdings_count = wallet_value["holdings_count"]
            else:
                # Calcul rapide juste du nombre de holdings
                holdings_count = len(crud.get_wallet_holdings(db, wallet.id))
                current_value = 0.0  # Sera calculé côté front avec les prix en cache

            wallets_data.append({
                "id": wallet.id,
                "name": wallet.name,
                "user_id": wallet.user_id,
                "current_value": current_value,
                "created_at": wallet.created_at.isoformat(),
                "updated_at": wallet.updated_at.isoformat(),
                "holdings_count": holdings_count,
                "initial_budget": float(wallet.initial_budget_usd) if hasattr(wallet, 'initial_budget_usd') and wallet.initial_budget_usd else 0.0
            })

        return {"status": "success", "wallets": wallets_data}
    except Exception as e:
        return {"status": "error", "message": str(e), "wallets": []}
    finally:
        db.close()


@router.post("/wallets")
async def create_wallet(wallet_data: WalletCreate):
    """Créer un nouveau portefeuille"""
    db = SessionLocal()
    try:
        # Vérifier si un portefeuille avec ce nom existe déjà
        existing = crud.get_wallet_by_name(db, wallet_data.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Un portefeuille nommé '{wallet_data.name}' existe déjà")

        # Créer le nouveau portefeuille
        wallet = crud.create_wallet(
            db=db,
            name=wallet_data.name,
            initial_budget=wallet_data.initial_budget,
            user_id=wallet_data.user_id
        )

        # Récupérer la valeur du wallet pour la réponse
        wallet_value = crud.calculate_wallet_value(db, wallet.id)

        wallet_response = {
            "id": wallet.id,
            "name": wallet.name,
            "user_id": wallet.user_id,
            "current_value": float(wallet_value["total_value"]),
            "created_at": wallet.created_at.isoformat(),
            "updated_at": wallet.updated_at.isoformat(),
            "holdings_count": wallet_value["holdings_count"]
        }

        return {"status": "success", "message": "Portefeuille créé avec succès", "wallet": wallet_response}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.get("/wallets/{wallet_id}")
async def get_wallet(wallet_id: int, calculate_value: bool = False):
    """Récupérer un portefeuille spécifique (avec calcul valeur optionnel)"""
    db = SessionLocal()
    try:
        wallet = crud.get_wallet(db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Portefeuille non trouvé")

        if calculate_value:
            # Récupérer la valeur actuelle du wallet (plus lent)
            wallet_value = crud.calculate_wallet_value(db, wallet.id)
            current_value = float(wallet_value["total_value"])
            holdings_count = wallet_value["holdings_count"]
        else:
            # Calcul rapide juste du nombre de holdings
            holdings_count = len(crud.get_wallet_holdings(db, wallet.id))
            current_value = float(wallet.initial_budget_usd) if wallet.initial_budget_usd else 0.0

        wallet_data = {
            "id": wallet.id,
            "name": wallet.name,
            "user_id": wallet.user_id,
            "initial_budget_usdt": float(wallet.initial_budget_usd) if wallet.initial_budget_usd else 0.0,
            "current_value": current_value,
            "created_at": wallet.created_at.isoformat(),
            "updated_at": wallet.updated_at.isoformat(),
            "holdings_count": holdings_count
        }

        return {"status": "success", "wallet": wallet_data}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.put("/wallets/{wallet_id}")
async def update_wallet(wallet_id: int, wallet_data: WalletUpdate):
    """Mettre à jour un portefeuille"""
    db = SessionLocal()
    try:
        wallet = crud.get_wallet(db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Portefeuille non trouvé")

        # Vérifier si le nouveau nom existe déjà (si fourni)
        if wallet_data.name and wallet_data.name != wallet.name:
            existing = crud.get_wallet_by_name(db, wallet_data.name)
            if existing:
                raise HTTPException(status_code=400, detail=f"Un portefeuille nommé '{wallet_data.name}' existe déjà")

        # Mettre à jour les champs fournis
        update_data = {}
        if wallet_data.name:
            update_data["name"] = wallet_data.name
        if wallet_data.initial_budget is not None:
            update_data["initial_budget_usd"] = Decimal(str(wallet_data.initial_budget))

        updated_wallet = crud.update_wallet(db, wallet_id, **update_data)

        # Récupérer la valeur actuelle du wallet
        wallet_value = crud.calculate_wallet_value(db, updated_wallet.id)

        wallet_response = {
            "id": updated_wallet.id,
            "name": updated_wallet.name,
            "user_id": updated_wallet.user_id,
            "current_value": float(wallet_value["total_value"]),
            "created_at": updated_wallet.created_at.isoformat(),
            "updated_at": updated_wallet.updated_at.isoformat(),
            "holdings_count": wallet_value["holdings_count"]
        }

        return {"status": "success", "message": "Portefeuille mis à jour avec succès", "wallet": wallet_response}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.delete("/wallets/{wallet_id}")
async def delete_wallet(wallet_id: int):
    """Supprimer un portefeuille"""
    db = SessionLocal()
    try:
        wallet = crud.get_wallet(db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Portefeuille non trouvé")

        # Vérifier si c'est le portefeuille par défaut
        if wallet.name == "default":
            raise HTTPException(status_code=400, detail="Impossible de supprimer le portefeuille par défaut")

        # Supprimer le portefeuille
        crud.delete_wallet(db, wallet_id)

        return {"status": "success", "message": f"Portefeuille '{wallet.name}' supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


# Holdings endpoints
@router.get("/wallets/{wallet_id}/holdings")
async def get_wallet_holdings(wallet_id: int):
    """Récupérer tous les holdings d'un portefeuille avec prix actuels"""
    db = SessionLocal()
    try:
        wallet = crud.get_wallet(db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Portefeuille non trouvé")

        holdings = crud.get_wallet_holdings(db, wallet_id)
        holdings_data = []

        # Récupérer les prix actuels depuis CoinGecko
        try:
            from ..collectors.price_collector import fetch_crypto_prices
            current_prices = fetch_crypto_prices()
        except Exception as e:
            print(f"⚠️ Erreur récupération prix CoinGecko: {e}")
            current_prices = {}

        for holding in holdings:
            asset = crud.get_asset(db, holding.asset_id)
            if not asset:
                continue

            # Récupérer le prix actuel
            coingecko_id = asset.coingecko_id or asset.id
            if current_prices and coingecko_id in current_prices:
                current_price = float(current_prices[coingecko_id]['usd'])
            elif holding.average_buy_price and holding.average_buy_price > 0:
                current_price = float(holding.average_buy_price)
            else:
                current_price = 0.0

            quantity = float(holding.quantity)
            avg_buy_price = float(holding.average_buy_price) if holding.average_buy_price else current_price
            current_value = quantity * current_price
            total_invested = quantity * avg_buy_price
            pnl = current_value - total_invested
            pnl_percent = (pnl / total_invested * 100) if total_invested > 0 else 0

            holdings_data.append({
                "id": holding.id,
                "symbol": asset.symbol,
                "quantity": quantity,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price,
                "current_value": current_value,
                "total_invested": total_invested,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "allocation_percent": 0  # À calculer avec la valeur totale du portefeuille
            })

        # Calculer les allocations
        total_value = sum(h["current_value"] for h in holdings_data)
        for holding in holdings_data:
            holding["allocation_percent"] = (holding["current_value"] / total_value * 100) if total_value > 0 else 0

        return {"status": "success", "holdings": holdings_data}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e), "holdings": []}
    finally:
        db.close()


@router.post("/wallets/{wallet_id}/holdings")
async def add_wallet_holding(wallet_id: int, holding_data: HoldingCreate):
    """Ajouter un holding à un portefeuille"""
    db = SessionLocal()
    try:
        wallet = crud.get_wallet(db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Portefeuille non trouvé")

        # Récupérer ou créer l'asset
        asset = crud.get_asset_by_symbol(db, holding_data.symbol.upper())
        if not asset:
            raise HTTPException(status_code=400, detail=f"Asset '{holding_data.symbol}' non trouvé")

        # Vérifier s'il existe déjà un holding pour cet asset
        existing_holding = crud.get_holding(db, wallet_id, asset.id)
        if existing_holding:
            raise HTTPException(status_code=400, detail=f"Un holding pour {holding_data.symbol} existe déjà")

        # Récupérer le prix actuel si avg_buy_price n'est pas fourni
        current_price = holding_data.avg_buy_price or 0

        # Créer le holding
        holding = crud.create_or_update_holding(
            db=db,
            wallet_id=wallet_id,
            asset_id=asset.id,
            quantity=Decimal(str(holding_data.quantity)),
            price=Decimal(str(current_price))
        )

        return {"status": "success", "message": f"Holding {holding_data.symbol} ajouté avec succès", "holding_id": holding.id}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.put("/holdings/{holding_id}")
async def update_holding(holding_id: int, holding_data: HoldingUpdate):
    """Mettre à jour un holding"""
    db = SessionLocal()
    try:
        holding = crud.get_holding_by_id(db, holding_id)
        if not holding:
            raise HTTPException(status_code=404, detail="Holding non trouvé")

        # Mettre à jour les champs fournis
        update_data = {}
        if holding_data.quantity is not None:
            update_data["quantity"] = Decimal(str(holding_data.quantity))
        if holding_data.avg_buy_price is not None:
            update_data["average_buy_price"] = Decimal(str(holding_data.avg_buy_price))

        if update_data:
            crud.update_holding(db, holding_id, **update_data)
        return {"status": "success", "message": "Holding mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.delete("/holdings/{holding_id}")
async def delete_holding(holding_id: int):
    """Supprimer un holding"""
    db = SessionLocal()
    try:
        holding = crud.get_holding_by_id(db, holding_id)
        if not holding:
            raise HTTPException(status_code=404, detail="Holding non trouvé")

        asset = crud.get_asset(db, holding.asset_id)
        symbol = asset.symbol if asset else str(holding.asset_id)
        crud.delete_holding(db, holding_id)

        return {"status": "success", "message": f"Holding {symbol} supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


# Transaction endpoints
@router.get("/wallets/{wallet_name}/transactions")
async def get_wallet_transactions_by_name(wallet_name: str):
    """Récupérer toutes les transactions d'un wallet par nom"""
    db = SessionLocal()
    try:
        # Récupérer le wallet par nom
        wallet = crud.get_wallet_by_name(db, wallet_name)
        if not wallet:
            # Créer le wallet s'il n'existe pas
            wallet = crud.create_wallet(db, name=wallet_name)

        # Récupérer toutes les transactions
        transactions = crud.get_wallet_transactions(db, wallet.id)

        # Formater les transactions pour le frontend
        transactions_data = []
        for tx in transactions:
            asset = crud.get_asset(db, tx.asset_id)

            # Utiliser le reasoning si disponible
            reasoning = tx.reasoning if tx.reasoning else "Pas de reasoning disponible pour ce trade"

            transaction_info = {
                "id": tx.id,
                "timestamp": tx.timestamp.isoformat(),
                "type": tx.type.value.upper(),
                "asset_symbol": asset.symbol if asset else str(tx.asset_id),
                "asset_name": asset.name if asset else str(tx.asset_id),
                "quantity": str(tx.amount),
                "price_at_time": str(tx.price_at_time),
                "fee": str(tx.fees) if tx.fees else "0",
                "notes": reasoning,
                "reasoning": reasoning
            }
            transactions_data.append(transaction_info)

        return {
            "status": "success",
            "wallet_name": wallet_name,
            "wallet_id": wallet.id,
            "transactions": transactions_data,
            "count": len(transactions_data)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.get("/wallets/{wallet_name}/transactions/export")
async def export_wallet_transactions_csv(wallet_name: str):
    """Exporter toutes les transactions d'un wallet en CSV"""
    db = SessionLocal()
    try:
        wallet = crud.get_wallet_by_name(db, wallet_name)
        if not wallet:
            wallet = crud.create_wallet(db, name=wallet_name)

        transactions = crud.get_wallet_transactions(db, wallet.id)

        # Créer le CSV en mémoire
        output = io.StringIO()
        writer = csv.writer(output)

        # En-têtes
        writer.writerow(["ID", "Date", "Type", "Asset", "Symbol", "Quantity", "Price", "Fee", "Total Value", "Reasoning"])

        # Données
        for tx in sorted(transactions, key=lambda x: x.timestamp, reverse=True):
            asset = crud.get_asset(db, tx.asset_id)
            total_value = float(tx.amount) * float(tx.price_at_time)

            writer.writerow([
                tx.id,
                tx.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                tx.type.value.upper(),
                asset.name if asset else tx.asset_id,
                asset.symbol if asset else tx.asset_id,
                f"{float(tx.amount):.8f}",
                f"{float(tx.price_at_time):.2f}",
                f"{float(tx.fees) if tx.fees else 0:.8f}",
                f"{total_value:.2f}",
                tx.reasoning if tx.reasoning else "N/A"
            ])

        # Préparer la réponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=trades_{wallet_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
