/**
 * Trading Manager Module
 * Handles trading operations, simulations, and trade history
 */

import { UIUtils } from './ui-utils.js';

export class TradingManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.simulations = [];
        this.currentTrades = [];
    }

    /**
     * Setup trading bot interface
     */
    setupTradingBotInterface() {
        console.log('[TradingManager] Setting up trading bot interface...');

        // Load simulations on init
        this.loadSimulations();

        // Refresh simulations every 30 seconds
        setInterval(() => {
            this.loadSimulations();
        }, 30000);

        // Setup button event listeners FIRST (need to be ready for user interaction)
        // Use setTimeout to ensure DOM is ready
        setTimeout(() => {
            this.setupBotButtons();
            console.log('[TradingManager] Bot buttons setup complete');
        }, 100);

        // Update bot status and stats
        setTimeout(() => {
            this.updateBotStatus();
            console.log('[TradingManager] Initial bot status update complete');
        }, 500);

        setInterval(() => {
            this.updateBotStatus();
        }, 10000); // Every 10 seconds

        // Load signals for bots page
        if (document.getElementById('bot-signals-list')) {
            console.log('[TradingManager] Bots page detected, loading signals...');
            setTimeout(() => {
                this.fedEdgeAI.signalsManager.loadAISignals();
            }, 300);

            // Refresh signals every 30 seconds
            setInterval(() => {
                this.fedEdgeAI.signalsManager.loadAISignals();
            }, 30000);
        }
    }

    /**
     * Setup bot button event listeners
     */
    setupBotButtons() {
        console.log('[TradingManager] Setting up bot button listeners...');

        // Start/Stop button
        const startStopBtn = document.getElementById('bot-start-stop-btn');
        if (startStopBtn) {
            console.log('[TradingManager] ✓ Start/Stop button found');
            startStopBtn.addEventListener('click', async () => {
                console.log('[TradingManager] Start/Stop button clicked');
                await this.toggleBot();
            });
        } else {
            console.warn('[TradingManager] ✗ Start/Stop button NOT found');
        }

        // Manual scan button
        const scanBtn = document.getElementById('trading-bot-scan-btn');
        if (scanBtn) {
            console.log('[TradingManager] ✓ Scan button found');
            scanBtn.addEventListener('click', async () => {
                console.log('[TradingManager] Scan button clicked');
                await this.manualScan();
            });
        } else {
            console.warn('[TradingManager] ✗ Scan button NOT found');
        }

        // Config button
        const configBtn = document.getElementById('bot-config-btn');
        if (configBtn) {
            console.log('[TradingManager] ✓ Config button found');
            configBtn.addEventListener('click', () => {
                console.log('[TradingManager] Config button clicked');
                this.showBotConfigModal();
            });
        } else {
            console.warn('[TradingManager] ✗ Config button NOT found');
        }

        // Modal close buttons
        const closeModalBtn = document.getElementById('close-bot-config-modal');
        const closeFooterBtn = document.getElementById('close-bot-config-footer-btn');

        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => {
                this.closeBotConfigModal();
            });
        }

        if (closeFooterBtn) {
            closeFooterBtn.addEventListener('click', () => {
                this.closeBotConfigModal();
            });
        }

        // Preset buttons
        const presetScalpBtn = document.getElementById('preset-scalp-btn');
        const presetDayBtn = document.getElementById('preset-day-btn');
        const presetSwingBtn = document.getElementById('preset-swing-btn');
        const presetResetBtn = document.getElementById('preset-reset-btn');

        if (presetScalpBtn) {
            presetScalpBtn.addEventListener('click', () => this.applyPreset('scalp'));
        }

        if (presetDayBtn) {
            presetDayBtn.addEventListener('click', () => this.applyPreset('day'));
        }

        if (presetSwingBtn) {
            presetSwingBtn.addEventListener('click', () => this.applyPreset('swing'));
        }

        if (presetResetBtn) {
            presetResetBtn.addEventListener('click', () => this.resetBotConfig());
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-bot-config-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadBotConfig();
            });
        }
    }

    /**
     * Toggle bot start/stop
     */
    async toggleBot() {
        try {
            const statusResponse = await fetch('/api/trading-bot/status');
            const statusData = await statusResponse.json();

            const endpoint = statusData.is_running ? '/api/trading-bot/stop' : '/api/trading-bot/start';
            const response = await fetch(endpoint, { method: 'POST' });

            if (response.ok) {
                const data = await response.json();
                UIUtils.showNotification(data.message || 'Bot status changed', 'success');

                // Update button immediately
                const startStopBtn = document.getElementById('bot-start-stop-btn');
                if (startStopBtn) {
                    const newIsRunning = !statusData.is_running;
                    if (newIsRunning) {
                        startStopBtn.innerHTML = '⏸️ Stop';
                        startStopBtn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                    } else {
                        startStopBtn.innerHTML = '▶️ Start';
                        startStopBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                    }
                }

                this.updateBotStatus(); // Refresh status
            } else {
                throw new Error('Failed to toggle bot');
            }
        } catch (error) {
            console.error('Error toggling bot:', error);
            UIUtils.showNotification('Failed to toggle bot', 'error');
        }
    }

    /**
     * Manual scan
     */
    async manualScan() {
        try {
            UIUtils.showNotification('Starting manual scan...', 'info');

            const response = await fetch('/api/trading-bot/scan', { method: 'POST' });

            if (response.ok) {
                const data = await response.json();

                if (data.success) {
                    const count = data.count || 0;
                    UIUtils.showNotification(
                        count > 0 ? `${count} signal${count > 1 ? 's' : ''} detected!` : 'No signals found',
                        count > 0 ? 'success' : 'info'
                    );

                    // Refresh signals and stats
                    this.fedEdgeAI.signalsManager.loadAISignals();
                    this.updateBotStatus();
                } else {
                    UIUtils.showNotification(data.message || 'Scan failed', 'error');
                }
            } else {
                throw new Error('Failed to scan');
            }
        } catch (error) {
            console.error('Error during manual scan:', error);
            UIUtils.showNotification('Failed to scan', 'error');
        }
    }

    /**
     * Show bot config modal
     */
    showBotConfigModal() {
        console.log('[TradingManager] Opening config modal...');

        // Find the modal in the currently active page only
        const activePage = document.querySelector('.content-page.active');
        const modal = activePage ? activePage.querySelector('#bot-config-modal') : null;

        if (modal) {
            console.log('[TradingManager] ✓ Modal found in active page, opening...');

            // Force modal to be visible on TOP of everything
            modal.style.display = 'flex';
            modal.style.position = 'fixed';
            modal.style.top = '0';
            modal.style.left = '0';
            modal.style.width = '100%';
            modal.style.height = '100%';
            modal.style.zIndex = '999999';  // Super high z-index
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
            modal.style.alignItems = 'center';
            modal.style.justifyContent = 'center';
            modal.style.background = 'rgba(0, 0, 0, 0.8)';

            // Ensure modal content is also visible
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.position = 'relative';
                modalContent.style.zIndex = '1000000';
            }

            this.loadBotConfig();
        } else {
            console.error('[TradingManager] ✗ Modal bot-config-modal NOT FOUND in active page');
            UIUtils.showNotification('Config modal not found', 'error');
        }
    }

    /**
     * Close bot config modal
     */
    closeBotConfigModal() {
        // Find the modal in the currently active page only
        const activePage = document.querySelector('.content-page.active');
        const modal = activePage ? activePage.querySelector('#bot-config-modal') : null;

        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Load bot config into modal
     */
    async loadBotConfig() {
        try {
            console.log('[TradingManager] Loading bot config...');
            const response = await fetch('/api/bot-config');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('[TradingManager] ✓ Config loaded');

            // Find the config display in the currently active page
            const activePage = document.querySelector('.content-page.active');
            const configDisplay = activePage ? activePage.querySelector('#current-bot-config') : null;

            if (configDisplay) {
                // Display formatted JSON
                configDisplay.textContent = JSON.stringify(data.config, null, 2);
                console.log('[TradingManager] ✓ Config displayed');
            } else {
                console.warn('[TradingManager] ✗ current-bot-config element not found in active page');
            }
        } catch (error) {
            console.error('[TradingManager] Error loading bot config:', error);

            // Find the config display in the currently active page
            const activePage = document.querySelector('.content-page.active');
            const configDisplay = activePage ? activePage.querySelector('#current-bot-config') : null;

            if (configDisplay) {
                configDisplay.textContent = 'Error loading configuration: ' + error.message;
            }
        }
    }

    /**
     * Apply a preset configuration
     */
    async applyPreset(presetName) {
        try {
            UIUtils.showNotification(`Applying ${presetName} preset...`, 'info');

            const response = await fetch(`/api/bot-config/preset/${presetName}`, {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                UIUtils.showNotification(`${presetName} preset applied!`, 'success');

                // Reload config display
                this.loadBotConfig();

                // Refresh bot status
                this.updateBotStatus();
            } else {
                throw new Error('Failed to apply preset');
            }
        } catch (error) {
            console.error('Error applying preset:', error);
            UIUtils.showNotification('Failed to apply preset', 'error');
        }
    }

    /**
     * Reset bot configuration
     */
    async resetBotConfig() {
        try {
            if (!confirm('Reset bot configuration to default values?')) {
                return;
            }

            UIUtils.showNotification('Resetting configuration...', 'info');

            const response = await fetch('/api/bot-config/reset', {
                method: 'POST'
            });

            if (response.ok) {
                UIUtils.showNotification('Configuration reset!', 'success');
                this.loadBotConfig();
                this.updateBotStatus();
            } else {
                throw new Error('Failed to reset config');
            }
        } catch (error) {
            console.error('Error resetting config:', error);
            UIUtils.showNotification('Failed to reset configuration', 'error');
        }
    }

    /**
     * Update bot status and trading stats
     */
    async updateBotStatus() {
        try {
            console.log('[TradingManager] Updating bot status...');

            // Fetch bot status
            const statusResponse = await fetch('/api/trading-bot/status');
            if (!statusResponse.ok) {
                console.error('[TradingManager] Failed to fetch bot status:', statusResponse.status);
                return;
            }

            const statusData = await statusResponse.json();
            console.log('[TradingManager] Bot status:', statusData.is_running ? 'RUNNING' : 'STOPPED');

            const statusText = document.getElementById('bot-status-text');
            const statusIndicator = document.getElementById('bot-status-indicator');
            const startStopBtn = document.getElementById('bot-start-stop-btn');

            if (statusText && statusIndicator) {
                if (statusData.is_running) {
                    statusText.textContent = 'Bot actif';
                    statusIndicator.style.background = '#10b981';

                    // Update button label
                    if (startStopBtn) {
                        startStopBtn.innerHTML = '⏸️ Stop';
                        startStopBtn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                    }
                } else {
                    statusText.textContent = 'Bot arrêté';
                    statusIndicator.style.background = '#ef4444';

                    // Update button label
                    if (startStopBtn) {
                        startStopBtn.innerHTML = '▶️ Start';
                        startStopBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                    }
                }
            } else {
                console.warn('[TradingManager] Status elements not found');
            }

            // Fetch trading stats
            const statsResponse = await fetch('/api/trading-stats');
            if (!statsResponse.ok) {
                console.error('[TradingManager] Failed to fetch stats:', statsResponse.status);
                return;
            }

            const statsData = await statsResponse.json();
            console.log('[TradingManager] Trading stats:', statsData);

            if (statsData.success && statsData.stats) {
                this.renderTradingStats(statsData.stats);
            } else {
                console.error('[TradingManager] Invalid stats data:', statsData);
            }
        } catch (error) {
            console.error('[TradingManager] Error updating bot status:', error);
        }
    }

    /**
     * Render trading stats
     */
    renderTradingStats(stats) {
        console.log('[TradingManager] Rendering trading stats:', stats);

        // Update winrate mini display
        const winrateMini = document.getElementById('bot-winrate-mini');
        if (winrateMini) {
            winrateMini.textContent = `WR: ${stats.winrate_pct.toFixed(1)}%`;
            console.log('[TradingManager] ✓ Updated winrate:', winrateMini.textContent);
        } else {
            console.warn('[TradingManager] ✗ bot-winrate-mini element not found');
        }

        // Update signals info
        const signalsInfo = document.getElementById('signals-info');
        if (signalsInfo) {
            const total = stats.total || 0;
            signalsInfo.textContent = `${total} signal${total !== 1 ? 's' : ''}`;
            console.log('[TradingManager] ✓ Updated signals info:', signalsInfo.textContent);
        } else {
            console.warn('[TradingManager] ✗ signals-info element not found');
        }

        // Update trading stats content
        const statsContent = document.getElementById('trading-stats-content');
        if (statsContent) {
            statsContent.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                    <div>
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Total Trades</div>
                        <div style="color: #fff; font-size: 20px; font-weight: 700;">${stats.total}</div>
                    </div>
                    <div>
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Win Rate</div>
                        <div style="color: ${stats.winrate_pct >= 50 ? '#10b981' : '#ef4444'}; font-size: 20px; font-weight: 700;">
                            ${stats.winrate_pct.toFixed(1)}%
                        </div>
                    </div>
                    <div>
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Wins</div>
                        <div style="color: #10b981; font-size: 18px; font-weight: 600;">${stats.wins}</div>
                    </div>
                    <div>
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Losses</div>
                        <div style="color: #ef4444; font-size: 18px; font-weight: 600;">${stats.losses}</div>
                    </div>
                    <div>
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Open Trades</div>
                        <div style="color: #fbbf24; font-size: 18px; font-weight: 600;">${stats.open_trades}</div>
                    </div>
                    <div>
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Expired</div>
                        <div style="color: #6b7280; font-size: 18px; font-weight: 600;">${stats.expired}</div>
                    </div>
                </div>
            `;
        }

        // Update recent trades table
        const tradesTable = document.getElementById('recent-trades-table');
        if (tradesTable && stats.recent_trades && stats.recent_trades.length > 0) {
            tradesTable.innerHTML = `
                <table style="width: 100%; font-size: 11px; color: #d1d5db;">
                    <thead style="background: rgba(255, 255, 255, 0.05);">
                        <tr>
                            <th style="padding: 8px; text-align: left; color: #9ca3af;">Symbol</th>
                            <th style="padding: 8px; text-align: left; color: #9ca3af;">Side</th>
                            <th style="padding: 8px; text-align: right; color: #9ca3af;">Entry</th>
                            <th style="padding: 8px; text-align: right; color: #9ca3af;">TP/SL</th>
                            <th style="padding: 8px; text-align: center; color: #9ca3af;">Result</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${stats.recent_trades.slice(0, 10).map(trade => `
                            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                                <td style="padding: 8px; font-weight: 600;">${trade.symbol}</td>
                                <td style="padding: 8px;">
                                    <span style="
                                        padding: 2px 6px;
                                        border-radius: 4px;
                                        background: ${trade.side === 'LONG' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'};
                                        color: ${trade.side === 'LONG' ? '#10b981' : '#ef4444'};
                                        font-size: 10px;
                                    ">${trade.side}</span>
                                </td>
                                <td style="padding: 8px; text-align: right;">${parseFloat(trade.entry).toFixed(6)}</td>
                                <td style="padding: 8px; text-align: right; font-size: 10px; color: #9ca3af;">
                                    ${parseFloat(trade.tp).toFixed(6)} / ${parseFloat(trade.sl).toFixed(6)}
                                </td>
                                <td style="padding: 8px; text-align: center;">
                                    ${trade.close_reason === 'TP' ?
                                        '<span style="color: #10b981; font-weight: 600;">✓ WIN</span>' :
                                        trade.close_reason === 'SL' ?
                                        '<span style="color: #ef4444; font-weight: 600;">✗ LOSS</span>' :
                                        trade.close_reason === 'EXPIRED' ?
                                        '<span style="color: #6b7280; font-weight: 600;">⏱ EXP</span>' :
                                        '<span style="color: #fbbf24; font-weight: 600;">⚡ OPEN</span>'
                                    }
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else if (tradesTable) {
            tradesTable.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px; font-size: 12px;">
                    Aucun trade récent
                </div>
            `;
        }

        // Update config display
        const configDisplay = document.getElementById('bot-config-display');
        if (configDisplay && stats.config) {
            const config = stats.config;
            configDisplay.innerHTML = `
                <div>
                    <div style="color: #9ca3af; margin-bottom: 4px;">Scan Interval</div>
                    <div style="color: #fff; font-weight: 600;">${config.scan_seconds}s</div>
                </div>
                <div>
                    <div style="color: #9ca3af; margin-bottom: 4px;">Timeframe</div>
                    <div style="color: #fff; font-weight: 600;">${config.kline_interval}</div>
                </div>
                <div>
                    <div style="color: #9ca3af; margin-bottom: 4px;">Min Volume</div>
                    <div style="color: #fff; font-weight: 600;">$${(config.min_24h_usd / 1000).toFixed(0)}k</div>
                </div>
                <div>
                    <div style="color: #9ca3af; margin-bottom: 4px;">Quote</div>
                    <div style="color: #fff; font-weight: 600;">${config.quote_whitelist.join(', ') || 'All'}</div>
                </div>
                <div>
                    <div style="color: #9ca3af; margin-bottom: 4px;">Paper Trading</div>
                    <div style="color: ${config.paper_trading ? '#10b981' : '#ef4444'}; font-weight: 600;">
                        ${config.paper_trading ? '✓ ON' : '✗ OFF'}
                    </div>
                </div>
                <div>
                    <div style="color: #9ca3af; margin-bottom: 4px;">Realtime TP/SL</div>
                    <div style="color: ${config.realtime_tpsl ? '#10b981' : '#6b7280'}; font-weight: 600;">
                        ${config.realtime_tpsl ? '✓ ON' : '○ OFF'}
                    </div>
                </div>
            `;
        }
    }

    /**
     * Load simulations from API
     */
    async loadSimulations() {
        try {
            const response = await fetch('/api/simulations');
            if (!response.ok) throw new Error('Failed to fetch simulations');

            const data = await response.json();

            // Backend returns {status: "success", simulations: [...]}
            if (data.status === 'success') {
                this.simulations = data.simulations || [];
            } else {
                this.simulations = [];
            }

            console.log(`Loaded ${this.simulations.length} simulations`);
            this.renderSimulations();
        } catch (error) {
            console.error('Error loading simulations:', error);
            UIUtils.showNotification('Failed to load simulations', 'error');
        }
    }

    /**
     * Render simulations list
     */
    renderSimulations() {
        const simulationsContainer = document.getElementById('simulations-list');
        const countElement = document.getElementById('simulations-count');

        // Always update Settings page (regardless of whether simulations page is visible)
        this.renderSimulationsInSettings();

        if (!simulationsContainer) return;

        // Update count
        if (countElement) {
            const activeCount = this.simulations.filter(s => s.is_active).length;
            countElement.textContent = `${this.simulations.length} simulation${this.simulations.length !== 1 ? 's' : ''} (${activeCount} active)`;
        }

        if (!this.simulations || this.simulations.length === 0) {
            simulationsContainer.innerHTML = `
                <div style="text-align: center; color: #6b7280; padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
                    <div>No trading bots yet. Create your first bot!</div>
                </div>
            `;
            if (countElement) {
                countElement.textContent = '0 simulations';
            }
            return;
        }

        simulationsContainer.innerHTML = this.simulations.map(sim => `
            <div class="simulation-card" style="
                background: white;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                border-left: 4px solid ${sim.is_running ? '#10b981' : '#6b7280'};
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <div>
                        <div style="font-weight: 700; font-size: 16px; color: #1f2937; margin-bottom: 4px;">
                            ${UIUtils.escapeHtml(sim.name || 'Unnamed Bot')}
                        </div>
                        <div style="font-size: 12px; color: #6b7280;">
                            Wallet: ${UIUtils.escapeHtml(sim.wallet_name || 'default')}
                        </div>
                    </div>
                    <div style="
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                        background: ${sim.is_active ? '#10b981' : '#6b7280'};
                        color: white;
                    ">
                        ${sim.is_active ? 'Active' : 'Inactive'}
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 12px;">
                    <div>
                        <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">Strategy</div>
                        <div style="font-size: 14px; font-weight: 600; color: #1f2937;">
                            ${UIUtils.escapeHtml(sim.strategy || 'default')}
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">Frequency</div>
                        <div style="font-size: 14px; font-weight: 600; color: #1f2937;">
                            ${sim.frequency_minutes || 0} min
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">Total Runs</div>
                        <div style="font-size: 14px; font-weight: 600; color: #1f2937;">
                            ${sim.total_runs || 0}
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">Success Rate</div>
                        <div style="font-size: 14px; font-weight: 600; color: #1f2937;">
                            ${(sim.success_rate || 0).toFixed(1)}%
                        </div>
                    </div>
                </div>

                <div style="display: flex; gap: 8px;">
                    <button onclick="window.toggleSimulation(${sim.id})" style="
                        flex: 1;
                        padding: 8px;
                        background: ${sim.is_active ? '#ef4444' : '#10b981'};
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                        font-size: 12px;
                    ">
                        ${sim.is_active ? 'Stop' : 'Start'}
                    </button>
                    <button onclick="window.showTradesHistory('${sim.wallet_name}')" style="
                        flex: 1;
                        padding: 8px;
                        background: #3b82f6;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                        font-size: 12px;
                    ">
                        History
                    </button>
                    <button onclick="window.deleteSimulation(${sim.id})" style="
                        padding: 8px 12px;
                        background: #ef4444;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                        font-size: 12px;
                    ">
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render simulations in Settings page
     */
    renderSimulationsInSettings() {
        const settingsContainer = document.getElementById('trading-simulations-list');

        if (!settingsContainer) return;

        if (!this.simulations || this.simulations.length === 0) {
            settingsContainer.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px;">
                    No trading simulations configured
                </div>
            `;
            return;
        }

        settingsContainer.innerHTML = this.simulations.map(sim => `
            <div style="
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-left: 4px solid ${sim.is_running ? '#10b981' : '#6b7280'};
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div>
                        <div style="color: #fff; font-weight: 600; font-size: 14px; margin-bottom: 4px;">
                            ${UIUtils.escapeHtml(sim.name || 'Unnamed Bot')}
                        </div>
                        <div style="color: #9ca3af; font-size: 12px;">
                            ${UIUtils.escapeHtml(sim.wallet_name || 'default')} • ${sim.strategy || 'default'}
                        </div>
                    </div>
                    <div style="
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 600;
                        background: ${sim.is_running ? '#10b981' : '#6b7280'};
                        color: white;
                    ">
                        ${sim.is_running ? 'Running' : 'Stopped'}
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 12px;">
                    <div>
                        <span style="color: #9ca3af;">Frequency:</span>
                        <span style="color: #fff; margin-left: 4px;">${sim.frequency_minutes || 0}min</span>
                    </div>
                    <div>
                        <span style="color: #9ca3af;">Runs:</span>
                        <span style="color: #fff; margin-left: 4px;">${sim.total_runs || 0}</span>
                    </div>
                    <div>
                        <span style="color: #9ca3af;">Success:</span>
                        <span style="color: #fff; margin-left: 4px;">${(sim.success_rate || 0).toFixed(1)}%</span>
                    </div>
                </div>
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <button onclick="window.toggleSimulation(${sim.id})" style="
                        flex: 1;
                        padding: 6px;
                        background: ${sim.is_active ? '#ef4444' : '#10b981'};
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 11px;
                        font-weight: 600;
                    ">
                        ${sim.is_active ? 'Stop' : 'Start'}
                    </button>
                    <button onclick="window.deleteSimulation(${sim.id})" style="
                        padding: 6px 10px;
                        background: #ef4444;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 11px;
                        font-weight: 600;
                    ">
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Toggle simulation (start/stop)
     */
    async toggleSimulation(simulationId) {
        try {
            const response = await fetch(`/api/simulations/${simulationId}/toggle`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to toggle simulation');

            const data = await response.json();
            UIUtils.showNotification(data.message || 'Simulation toggled', 'success');

            // Reload simulations
            this.loadSimulations();
        } catch (error) {
            console.error('Error toggling simulation:', error);
            UIUtils.showNotification('Failed to toggle simulation', 'error');
        }
    }

    /**
     * Delete simulation
     */
    async deleteSimulation(simulationId) {
        if (!confirm('Are you sure you want to delete this simulation?')) return;

        try {
            const response = await fetch(`/api/simulations/${simulationId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete simulation');

            UIUtils.showNotification('Simulation deleted', 'success');

            // Reload simulations
            this.loadSimulations();
        } catch (error) {
            console.error('Error deleting simulation:', error);
            UIUtils.showNotification('Failed to delete simulation', 'error');
        }
    }

    /**
     * Show trades history
     */
    async showTradesHistory(walletName = 'default') {
        try {
            // Utiliser l'endpoint existant /wallets/{wallet_name}/transactions
            const response = await fetch(`/api/wallets/${encodeURIComponent(walletName)}/transactions`);
            if (!response.ok) throw new Error('Failed to fetch trades');

            const data = await response.json();

            // Adapter le format des transactions pour le format attendu
            const adaptedTrades = (data.transactions || []).map(tx => ({
                id: tx.id,
                timestamp: tx.timestamp,
                ticker: tx.asset_symbol,
                action: tx.type,  // BUY or SELL
                amount: parseFloat(tx.quantity),
                price: parseFloat(tx.price_at_time),
                total: parseFloat(tx.quantity) * parseFloat(tx.price_at_time),
                fee: parseFloat(tx.fee || 0),
                reasoning: tx.reasoning || tx.notes || 'No reasoning available'
            }));

            // Adapter le format de réponse pour handleTradesHistory
            const adaptedData = {
                payload: {
                    wallet_name: data.wallet_name || walletName,
                    trades: adaptedTrades,
                    count: adaptedTrades.length
                }
            };

            this.handleTradesHistory(adaptedData);
        } catch (error) {
            console.error('Error loading trades:', error);
            UIUtils.showNotification('Failed to load trades history', 'error');
        }
    }

    /**
     * Handle trades history
     */
    handleTradesHistory(data) {
        const payload = data.payload || {};
        const trades = payload.trades || [];

        console.log(`Loaded ${trades.length} trades`);
        console.log('Trades data:', trades);

        // Open trades modal
        try {
            this.displayTradesModal(trades, payload.wallet_name);
            console.log('Modal displayed successfully');
        } catch (error) {
            console.error('Error displaying modal:', error);
            UIUtils.showNotification('Failed to display trades modal', 'error');
        }
    }

    /**
     * Display trades modal
     */
    displayTradesModal(trades, walletName) {
        console.log('Creating modal for', trades.length, 'trades');

        try {
            const tradesTable = this.renderTradesTable(trades);
            console.log('Trades table rendered');

            const modal = UIUtils.createModal(`
                <div style="max-width: 800px;">
                    <h2 style="margin-bottom: 16px; color: #1f2937;">
                        Trade History: ${UIUtils.escapeHtml(walletName || 'default')}
                    </h2>
                    <div id="trades-container" style="max-height: 500px; overflow-y: auto;">
                        ${tradesTable}
                    </div>
                    <button onclick="this.closest('.modal-overlay').remove()" style="
                        margin-top: 16px;
                        padding: 8px 16px;
                        background: #3b82f6;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                    ">
                        Close
                    </button>
                </div>
            `);

            console.log('Modal created:', modal);
            document.body.appendChild(modal);
            console.log('Modal appended to body');
        } catch (error) {
            console.error('Error in displayTradesModal:', error);
            throw error;
        }
    }

    /**
     * Render trades table
     */
    renderTradesTable(trades) {
        console.log('renderTradesTable called with', trades.length, 'trades');

        if (!trades || trades.length === 0) {
            return `
                <div style="text-align: center; color: #6b7280; padding: 40px;">
                    No trades found
                </div>
            `;
        }

        try {
            const rows = trades.map((trade, index) => {
                console.log(`Rendering trade ${index}:`, trade);

                // Safe values with defaults
                const timestamp = trade.timestamp || trade.created_at || '';
                const ticker = trade.ticker || trade.asset_symbol || 'N/A';
                const action = (trade.action || trade.type || 'N/A').toUpperCase();
                const amount = parseFloat(trade.amount || trade.quantity || 0);
                const price = parseFloat(trade.price || trade.price_at_time || 0);
                const total = trade.total || (amount * price);

                return `
                    <tr style="border-bottom: 1px solid #e5e7eb;">
                        <td style="padding: 12px; font-size: 12px; color: #6b7280;">
                            ${UIUtils.formatTimestamp(timestamp)}
                        </td>
                        <td style="padding: 12px; font-weight: 600; color: #1f2937;">
                            ${UIUtils.escapeHtml(ticker)}
                        </td>
                        <td style="padding: 12px;">
                            <span style="
                                padding: 4px 8px;
                                border-radius: 6px;
                                font-size: 11px;
                                font-weight: 600;
                                background: ${action === 'BUY' ? '#10b981' : '#ef4444'};
                                color: white;
                            ">
                                ${action}
                            </span>
                        </td>
                        <td style="padding: 12px; text-align: right; font-weight: 600; color: #1f2937;">
                            ${amount.toFixed(6)}
                        </td>
                        <td style="padding: 12px; text-align: right; color: #6b7280;">
                            ${UIUtils.formatPrice(price)}
                        </td>
                        <td style="padding: 12px; text-align: right; font-weight: 600; color: #1f2937;">
                            ${UIUtils.formatPrice(total)}
                        </td>
                    </tr>
                `;
            });

            const table = `
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 12px; text-align: left; font-size: 12px; color: #6b7280;">Date</th>
                            <th style="padding: 12px; text-align: left; font-size: 12px; color: #6b7280;">Ticker</th>
                            <th style="padding: 12px; text-align: left; font-size: 12px; color: #6b7280;">Action</th>
                            <th style="padding: 12px; text-align: right; font-size: 12px; color: #6b7280;">Amount</th>
                            <th style="padding: 12px; text-align: right; font-size: 12px; color: #6b7280;">Price</th>
                            <th style="padding: 12px; text-align: right; font-size: 12px; color: #6b7280;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.join('')}
                    </tbody>
                </table>
            `;

            console.log('Table rendered successfully');
            return table;
        } catch (error) {
            console.error('Error rendering trades table:', error);
            return `<div style="color: red; padding: 20px;">Error rendering trades: ${error.message}</div>`;
        }
    }

    /**
     * Show modal to create new simulation
     */
    async showCreateSimulationModal() {
        try {
            // Fetch available wallets
            const walletsResponse = await fetch('/api/wallets');
            if (!walletsResponse.ok) throw new Error('Failed to fetch wallets');
            const walletsData = await walletsResponse.json();
            const wallets = walletsData.wallets || [];

            if (wallets.length === 0) {
                UIUtils.showNotification('Please create a wallet first', 'warning');
                return;
            }

            const walletsOptions = wallets.map(w =>
                `<option value="${w.id}">${UIUtils.escapeHtml(w.name)}</option>`
            ).join('');

            const modal = UIUtils.createModal(`
                <div style="max-width: 500px;">
                    <h2 style="margin-bottom: 20px; color: #1f2937;">Create New Simulation</h2>

                    <form id="create-simulation-form" style="display: flex; flex-direction: column; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Name</label>
                            <input type="text" id="sim-name" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " placeholder="My Trading Bot" />
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Wallet</label>
                            <select id="sim-wallet" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                                background: white;
                            ">
                                ${walletsOptions}
                            </select>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Strategy</label>
                            <select id="sim-strategy" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                                background: white;
                            ">
                                <option value="scalp">Scalp (Short-term)</option>
                                <option value="swing">Swing (Medium-term)</option>
                                <option value="hold">Hold (Long-term)</option>
                            </select>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Frequency</label>
                            <select id="sim-frequency" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                                background: white;
                            ">
                                <option value="5">Every 5 minutes</option>
                                <option value="15" selected>Every 15 minutes</option>
                                <option value="30">Every 30 minutes</option>
                                <option value="60">Every 1 hour</option>
                                <option value="240">Every 4 hours</option>
                                <option value="1440">Every 24 hours</option>
                            </select>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Description (optional)</label>
                            <textarea id="sim-description" rows="3" style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                                resize: vertical;
                            " placeholder="Describe your trading strategy..."></textarea>
                        </div>

                        <div style="display: flex; gap: 12px; margin-top: 8px;">
                            <button type="button" onclick="this.closest('.modal-overlay').remove()" style="
                                flex: 1;
                                padding: 10px;
                                background: #6b7280;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">Cancel</button>
                            <button type="submit" style="
                                flex: 1;
                                padding: 10px;
                                background: linear-gradient(135deg, #10b981, #059669);
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">Create Simulation</button>
                        </div>
                    </form>
                </div>
            `, { maxWidth: '500px' });

            document.body.appendChild(modal);

            // Handle form submission
            document.getElementById('create-simulation-form').addEventListener('submit', async (e) => {
                e.preventDefault();

                const simulationData = {
                    name: document.getElementById('sim-name').value,
                    wallet_id: parseInt(document.getElementById('sim-wallet').value),
                    strategy: document.getElementById('sim-strategy').value,
                    frequency_minutes: parseInt(document.getElementById('sim-frequency').value),
                    description: document.getElementById('sim-description').value || ''
                };

                try {
                    const response = await fetch('/api/simulations', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(simulationData)
                    });

                    if (!response.ok) throw new Error('Failed to create simulation');

                    const result = await response.json();

                    if (result.status === 'success') {
                        UIUtils.showNotification('Simulation created successfully', 'success');
                        modal.remove();
                        this.loadSimulations();
                    } else {
                        throw new Error(result.message || 'Failed to create simulation');
                    }
                } catch (error) {
                    console.error('Error creating simulation:', error);
                    UIUtils.showNotification('Failed to create simulation: ' + error.message, 'error');
                }
            });

        } catch (error) {
            console.error('Error showing create simulation modal:', error);
            UIUtils.showNotification('Failed to load wallets', 'error');
        }
    }

    /**
     * Handle trade executed from WebSocket
     */
    handleTradeExecuted(data) {
        const payload = data.payload || {};
        const trade = payload.trade || payload;

        console.log('Trade executed:', trade);

        UIUtils.showNotification(
            `${trade.action} ${trade.amount} ${trade.ticker} @ ${UIUtils.formatPrice(trade.price)}`,
            'success'
        );

        // Reload simulations to update stats
        this.loadSimulations();
    }

    /**
     * Handle trading decision from WebSocket
     */
    handleTradingDecision(data) {
        const payload = data.payload || {};

        console.log('Trading decision:', payload);

        // Update dashboard with decision info if needed
    }
}
