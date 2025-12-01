/**
 * Debug script to force reload all data on bots page
 * Paste this in browser console (F12) to force refresh everything
 */

console.log('🔧 DEBUG RELOAD SCRIPT');

// Force reload bot status
async function forceReloadBotStatus() {
    console.log('📊 Reloading bot status...');
    try {
        const response = await fetch('/api/trading-bot/status');
        const data = await response.json();
        console.log('✅ Bot Status:', data);
        return data;
    } catch (error) {
        console.error('❌ Bot Status Error:', error);
    }
}

// Force reload trading stats
async function forceReloadStats() {
    console.log('📈 Reloading trading stats...');
    try {
        const response = await fetch('/api/trading-stats');
        const data = await response.json();
        console.log('✅ Trading Stats:', data);

        // Manually update DOM
        if (data.success && data.stats) {
            const winrateMini = document.getElementById('bot-winrate-mini');
            if (winrateMini) {
                winrateMini.textContent = `WR: ${data.stats.winrate_pct.toFixed(1)}%`;
                console.log('✅ Updated winrate display');
            }

            const signalsInfo = document.getElementById('signals-info');
            if (signalsInfo) {
                signalsInfo.textContent = `${data.stats.total} signal${data.stats.total !== 1 ? 's' : ''}`;
                console.log('✅ Updated signals info');
            }
        }
        return data;
    } catch (error) {
        console.error('❌ Trading Stats Error:', error);
    }
}

// Force reload signals
async function forceReloadSignals() {
    console.log('🎯 Reloading signals...');
    try {
        const response = await fetch('/api/signals?limit=20');
        const data = await response.json();
        console.log('✅ Signals:', data);

        // Manually render signals in bot page
        const botSignalsList = document.getElementById('bot-signals-list');
        if (botSignalsList && data.signals) {
            if (data.signals.length === 0) {
                botSignalsList.innerHTML = `
                    <div style="text-align: center; color: #9ca3af; padding: 20px; font-size: 12px;">
                        Aucun signal actif
                    </div>
                `;
            } else {
                botSignalsList.innerHTML = data.signals.map(signal => `
                    <div style="
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 6px;
                        padding: 10px;
                        margin-bottom: 8px;
                        border-left: 3px solid ${signal.action === 'BUY' ? '#10b981' : '#ef4444'};
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                <span style="
                                    background: ${signal.action === 'BUY' ? '#10b981' : '#ef4444'};
                                    color: white;
                                    padding: 2px 8px;
                                    border-radius: 4px;
                                    font-size: 10px;
                                    font-weight: 600;
                                ">${signal.action}</span>
                                <span style="color: #fff; font-weight: 600; font-size: 13px;">${signal.ticker}</span>
                            </div>
                            <div style="font-size: 10px; color: #9ca3af;">
                                Entry: ${signal.entry_price.toFixed(6)} |
                                TP: <span style="color: #10b981;">${signal.target_price.toFixed(6)}</span> |
                                SL: <span style="color: #ef4444;">${signal.stop_loss.toFixed(6)}</span>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="
                                width: 32px;
                                height: 32px;
                                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                color: white;
                                font-size: 11px;
                                font-weight: 700;
                            ">${Math.round(signal.confidence || 0)}</div>
                        </div>
                    </div>
                `).join('');
            }
            console.log('✅ Updated signals display');
        }
        return data;
    } catch (error) {
        console.error('❌ Signals Error:', error);
    }
}

// Test button click handlers
function testButtons() {
    console.log('🔘 Testing button handlers...');

    const scanBtn = document.getElementById('trading-bot-scan-btn');
    const configBtn = document.getElementById('bot-config-btn');
    const startStopBtn = document.getElementById('bot-start-stop-btn');

    console.log('Scan button:', scanBtn ? '✅ Found' : '❌ Not found');
    console.log('Config button:', configBtn ? '✅ Found' : '❌ Not found');
    console.log('Start/Stop button:', startStopBtn ? '✅ Found' : '❌ Not found');

    if (scanBtn) {
        console.log('Scan button has', scanBtn.onclick ? 'onclick' : 'no onclick');
        console.log('Scan button listeners:', getEventListeners(scanBtn));
    }
}

// Run all reloads
async function forceReloadAll() {
    console.log('🚀 FORCE RELOAD ALL DATA');
    await forceReloadBotStatus();
    await forceReloadStats();
    await forceReloadSignals();
    testButtons();
    console.log('✅ RELOAD COMPLETE');
}

// Auto-run
console.log('💡 Run forceReloadAll() to reload all data');
console.log('💡 Run testButtons() to check button handlers');

// Expose to window
window.forceReloadAll = forceReloadAll;
window.forceReloadBotStatus = forceReloadBotStatus;
window.forceReloadStats = forceReloadStats;
window.forceReloadSignals = forceReloadSignals;
window.testButtons = testButtons;
