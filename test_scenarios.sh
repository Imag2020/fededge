#!/bin/bash
# Test différents scénarios de signaux synthétiques

echo "🧪 TEST SCÉNARIOS - Génération signaux synthétiques"
echo "=================================================="
echo ""

echo "Choisissez un scénario:"
echo "  1) extreme_fear - RSI oversold partout (bullish)"
echo "  2) bullish      - Tendance haussière (golden cross, breakouts)"
echo "  3) bearish      - Tendance baissière (death cross, breakdowns)"
echo "  4) mixed        - Mix de signaux bullish/bearish"
echo ""

read -p "Scénario (1-4): " choice

case $choice in
  1)
    scenario="extreme_fear"
    ;;
  2)
    scenario="bullish"
    ;;
  3)
    scenario="bearish"
    ;;
  4)
    scenario="mixed"
    ;;
  *)
    echo "❌ Choix invalide"
    exit 1
    ;;
esac

echo ""
echo "📡 Génération signaux scénario: $scenario"
echo "----------------------------------------------"

curl -s -X POST http://localhost:8000/api/trading-bot/scan \
  -H "Content-Type: application/json" \
  -d "{\"use_synthetic\": true, \"scenario\": \"$scenario\"}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'✅ {d.get(\"count\", 0)} signaux générés')
print(f'   Scénario: {d.get(\"scenario\", \"?\")}')
if d.get('signals'):
    for s in d['signals']:
        side = s.get('action', s.get('side', '?'))
        emoji = '🟢' if side == 'BUY' else '🔴'
        print(f'   {emoji} {s.get(\"symbol\")} {s.get(\"event\")} (conf: {s.get(\"confidence\", 0):.0f}%)')
"

echo ""
echo "✅ FAIT!"
echo ""
echo "Rechargez la page frontend ou attendez le prochain cycle (~2min)"
echo "Vous devriez voir les signaux dans 'Global Consciousness'"
