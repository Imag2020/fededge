#!/bin/bash
# Test rapide API Phase 1

echo "🧪 TEST PHASE 1 - Génération signaux synthétiques"
echo "=================================================="
echo ""

echo "1️⃣ Générer 5 signaux EXTREME FEAR (oversold partout)"
echo "------------------------------------------------------"
curl -X POST http://localhost:5000/trading-bot/scan \
  -H "Content-Type: application/json" \
  -d '{"use_synthetic": true, "scenario": "extreme_fear"}' \
  2>/dev/null | python3 -m json.tool

echo ""
echo ""
echo "⏳ Attendre 3 secondes pour que la conscience se mette à jour..."
sleep 3

echo ""
echo "2️⃣ Vérifier les signaux disponibles"
echo "------------------------------------------------------"
curl http://localhost:5000/bot-signals 2>/dev/null | python3 -m json.tool | head -50

echo ""
echo ""
echo "✅ FAIT! Maintenant vérifiez le frontend:"
echo "   - Vous devriez voir des signaux 📡"
echo "   - Des opportunités 💡 (DCA entry sur BTC/ETH/SOL)"
echo "   - Des risques ⚠️ (extreme_fear)"
echo ""
echo "Si la conscience ne se met pas à jour automatiquement,"
echo "attendez le prochain cycle (~2 min) ou rechargez la page."
