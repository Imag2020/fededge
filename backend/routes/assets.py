"""
Asset Management Routes
Handles all asset-related endpoints including search, analytics, and management
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import json
from pathlib import Path
from datetime import datetime, timedelta

from ..db.models import SessionLocal, Asset
from ..db import crud
from ..analytics.asset_stats import analyze_asset, get_asset_summary_for_llm, asset_analyzer

router = APIRouter(tags=["assets"])


@router.get("/assets")
async def get_supported_assets():
    """Retourne la liste des assets supportés avec prix actuels"""
    from ..utils.asset_helpers import get_supported_assets_list

    try:
        assets = get_supported_assets_list()

        # Charger les prix actuels depuis le cache
        prices_cache_file = Path("data/prices_cache.json")
        current_prices = {}

        if prices_cache_file.exists():
            try:
                with open(prices_cache_file, 'r') as f:
                    cache_data = json.load(f)
                    current_prices = cache_data.get('prices', {})
            except:
                pass

        # Mettre à jour les prix des assets avec les prix actuels
        for asset in assets:
            asset_id = asset.get('id')
            if asset_id and asset_id in current_prices:
                price_data = current_prices[asset_id]
                asset['current_price'] = price_data.get('usd', asset.get('current_price'))
                asset['price_change_24h'] = price_data.get('usd_24h_change', asset.get('price_change_24h'))
                asset['market_cap'] = price_data.get('usd_market_cap', asset.get('market_cap'))

        return {
            "success": True,
            "total": len(assets),
            "assets": assets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération assets: {str(e)}")


@router.get("/assets/dropdown")
async def get_assets_for_dropdown():
    """Retourne les assets formatés pour un dropdown"""
    from ..utils.asset_helpers import get_assets_for_dropdown
    try:
        dropdown_assets = get_assets_for_dropdown()
        return {
            "success": True,
            "total": len(dropdown_assets),
            "options": dropdown_assets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération dropdown: {str(e)}")


@router.get("/assets/search")
async def search_assets(q: str = "", limit: int = 20):
    """Recherche des assets par nom ou symbole"""
    from ..utils.asset_helpers import search_assets
    try:
        if not q or len(q) < 2:
            return {"success": True, "results": [], "query": q}

        results = search_assets(q, limit)
        return {
            "success": True,
            "query": q,
            "total": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche: {str(e)}")


@router.post("/assets")
async def add_new_asset(asset_data: dict):
    """Ajouter un nouvel asset à la base de données"""
    from sqlalchemy.orm import sessionmaker

    db = SessionLocal()
    try:
        # Validation des données requises
        required_fields = ['id', 'name', 'symbol', 'coingecko_id']
        for field in required_fields:
            if field not in asset_data:
                return {"status": "error", "message": f"Champ requis manquant: {field}"}

        # Vérifier si l'asset existe déjà
        existing_asset = db.query(Asset).filter(Asset.id == asset_data['id']).first()
        if existing_asset:
            return {"status": "error", "message": f"Asset {asset_data['id']} existe déjà"}

        # Créer le nouvel asset
        new_asset = Asset(
            id=asset_data['id'],
            name=asset_data['name'],
            symbol=asset_data['symbol'].upper(),
            coingecko_id=asset_data['coingecko_id'],
            binance_symbol=asset_data.get('binance_symbol'),
            logo_url=asset_data.get('logo_url', ''),
            description=asset_data.get('description', '')
        )

        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)

        return {
            "status": "success",
            "message": f"Asset {new_asset.name} ({new_asset.symbol}) ajouté avec succès",
            "asset": {
                "id": new_asset.id,
                "name": new_asset.name,
                "symbol": new_asset.symbol,
                "coingecko_id": new_asset.coingecko_id
            }
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.get("/supported-assets")
async def get_supported_assets_list():
    """Récupérer la liste des cryptos supportées"""
    db = SessionLocal()
    try:
        assets = crud.get_all_assets(db)
        assets_data = [
            {
                "symbol": asset.symbol,
                "name": asset.name,
                "id": asset.id
            }
            for asset in assets
        ]
        return {"status": "success", "assets": assets_data}
    except Exception as e:
        return {"status": "error", "message": str(e), "assets": []}
    finally:
        db.close()


@router.get("/assets/{asset_id}/analysis")
async def get_asset_analysis(asset_id: str, days: int = 1):
    """Get comprehensive asset analysis with statistics"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

        # Temporary fallback analysis while fixing the main analyzer
        try:
            analysis = analyze_asset(asset_id, days)
            if 'error' not in analysis:
                return {"status": "success", "analysis": analysis}
        except Exception:
            pass  # Fall through to fallback

        # Fallback basic analysis
        fallback_analysis = {
            "asset_id": asset_id,
            "period_days": days,
            "stats": {
                "price_change_24h": 0.0,
                "volume_24h": 0.0,
                "market_cap": 0.0,
                "volatility": 0.0
            },
            "analysis_timestamp": datetime.now().isoformat(),
            "note": "Fallback analysis - full analytics temporarily unavailable"
        }

        return {"status": "success", "analysis": fallback_analysis}

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/assets/{asset_id}/chart-data")
async def get_asset_chart_data(asset_id: str, days: int = 1):
    """Get raw chart data for frontend visualization"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

        # Try to get real chart data
        try:
            chart_data = asset_analyzer.get_asset_market_chart(asset_id, days)
            if chart_data:
                # Format data for Chart.js
                formatted_data = {
                    "labels": [],
                    "prices": [],
                    "volumes": [],
                    "market_caps": []
                }

                if 'prices' in chart_data:
                    for timestamp, price in chart_data['prices']:
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        formatted_data["labels"].append(dt.isoformat())
                        formatted_data["prices"].append(price)

                if 'total_volumes' in chart_data:
                    formatted_data["volumes"] = [volume for _, volume in chart_data['total_volumes']]

                if 'market_caps' in chart_data:
                    formatted_data["market_caps"] = [mcap for _, mcap in chart_data['market_caps']]

                return {"status": "success", "chart_data": formatted_data, "raw_data": chart_data}
        except Exception:
            pass  # Fall through to fallback

        # Fallback empty chart data
        now = datetime.now()
        fallback_data = {
            "labels": [(now - timedelta(hours=i)).isoformat() for i in range(24, 0, -1)],
            "prices": [0.0] * 24,
            "volumes": [0.0] * 24,
            "market_caps": [0.0] * 24
        }

        return {"status": "success", "chart_data": fallback_data, "note": "Fallback data - real charts temporarily unavailable"}

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/assets/{asset_id}/llm-summary")
async def get_asset_llm_summary(asset_id: str, days: int = 1):
    """Get LLM-ready text summary of asset analysis"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

        # Try to get real LLM summary
        try:
            summary = get_asset_summary_for_llm(asset_id, days)
            if not summary.startswith("Analysis Error:") and not summary.startswith("Formatting Error:"):
                return {"status": "success", "summary": summary}
        except Exception:
            pass  # Fall through to fallback

        # Fallback basic summary
        fallback_summary = f"""Asset Analysis Summary for {asset_id.upper()}

Period: {days} day(s)
Status: Basic analysis available

Current market data shows {asset_id} is actively traded.
Full analytics are temporarily unavailable due to system maintenance.

Note: This is a fallback summary while the full analysis system is being restored."""

        return {"status": "success", "summary": fallback_summary, "note": "Fallback summary - full analytics temporarily unavailable"}

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
