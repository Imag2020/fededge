/**
 * Rag Manager Module
 * Handles wallet operations, holdings, and performance tracking
 */

import { UIUtils } from './ui-utils.js';

export class WalletManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.currentPrices = {};
        this.tradesCountOverride = {};
        this.selectedWalletId = null;
        this.selectedWalletName = 'Main Wallet';
    }

    /**
     * Setup wallet interface event listeners
     */
    setupWalletInterface() {
        console.log('Setting up wallet interface...');

        // Add wallet button
        const addWalletBtn = document.getElementById('add-wallet-btn');
        if (addWalletBtn) {
            addWalletBtn.addEventListener('click', () => this.showNewWalletForm());
            console.log('✅ Add wallet button handler attached');
        } else {
            console.warn('⚠️ Add wallet button not found');
        }

        // Cancel wallet form button
        const cancelWalletBtn = document.getElementById('cancel-wallet-form');
        if (cancelWalletBtn) {
            cancelWalletBtn.addEventListener('click', () => this.hideWalletForm());
        }

        // Wallet form submission
        const walletForm = document.getElementById('wallet-form-element');
        if (walletForm) {
            walletForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitWalletForm();
            });
        }

        // Add holding button
        const addHoldingBtn = document.getElementById('add-holding-btn');
        if (addHoldingBtn) {
            addHoldingBtn.addEventListener('click', () => this.showAddHoldingForm());
        }

        // Cancel holding form button
        const cancelHoldingBtn = document.getElementById('cancel-holding-form');
        if (cancelHoldingBtn) {
            cancelHoldingBtn.addEventListener('click', () => this.hideAddHoldingForm());
        }

        // Holding form submission
        const holdingForm = document.getElementById('holding-form-element');
        if (holdingForm) {
            holdingForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitHoldingForm();
            });
        }

        // Delete wallet button
        const deleteWalletBtn = document.getElementById('delete-wallet-btn');
        if (deleteWalletBtn) {
            deleteWalletBtn.addEventListener('click', () => this.deleteWallet());
        }

        console.log('✅ Wallet interface setup complete');
    }

    /**
     * Show new wallet form
     */
    showNewWalletForm() {
        this.selectedWalletId = null;
        const placeholder = document.getElementById('wallet-form-placeholder');
        const form = document.getElementById('wallet-form');
        const title = document.getElementById('wallet-form-title');
        const deleteBtn = document.getElementById('delete-wallet-btn');

        if (placeholder) placeholder.style.display = 'none';
        if (form) form.style.display = 'block';
        if (title) title.textContent = 'New Wallet';
        if (deleteBtn) deleteBtn.style.display = 'none';

        // Reset form
        const nameInput = document.getElementById('wallet-name');
        const budgetInput = document.getElementById('wallet-initial-budget-input');
        if (nameInput) nameInput.value = '';
        if (budgetInput) budgetInput.value = '10000';
    }

    /**
     * Hide wallet form
     */
    hideWalletForm() {
        const placeholder = document.getElementById('wallet-form-placeholder');
        const form = document.getElementById('wallet-form');

        if (placeholder) placeholder.style.display = 'flex';
        if (form) form.style.display = 'none';
    }

    /**
     * Submit wallet form
     */
    async submitWalletForm() {
        const nameInput = document.getElementById('wallet-name');
        const budgetInput = document.getElementById('wallet-initial-budget-input');

        if (!nameInput || !budgetInput) return;

        const name = nameInput.value.trim();
        const budget = parseFloat(budgetInput.value);

        if (!name) {
            UIUtils.showNotification('Please enter a wallet name', 'error');
            return;
        }

        if (isNaN(budget) || budget < 0) {
            UIUtils.showNotification('Budget must be a positive number', 'error');
            return;
        }

        try {
            let response;

            // Check if we're creating a new wallet or editing an existing one
            if (this.selectedWalletId) {
                // Update existing wallet
                response = await fetch(`/api/wallets/${this.selectedWalletId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        balance: budget
                    })
                });

                if (!response.ok) throw new Error('Failed to update wallet');
                UIUtils.showNotification('Wallet updated successfully!', 'success');
            } else {
                // Create new wallet
                if (budget < 100) {
                    UIUtils.showNotification('Initial budget must be at least $100', 'error');
                    return;
                }

                response = await fetch('/api/wallets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        initial_balance: budget
                    })
                });

                if (!response.ok) throw new Error('Failed to create wallet');
                UIUtils.showNotification('Wallet created successfully!', 'success');
            }

            this.hideWalletForm();
            await this.loadWalletsData();
        } catch (error) {
            console.error('Error saving wallet:', error);
            UIUtils.showNotification('Failed to save wallet', 'error');
        }
    }

    /**
     * Show add holding form
     */
    showAddHoldingForm() {
        if (!this.selectedWalletId) {
            UIUtils.showNotification('Please select a wallet first', 'warning');
            return;
        }

        const form = document.getElementById('add-holding-form');
        if (form) form.style.display = 'block';

        // Load available cryptos
        this.loadAvailableCryptos();
    }

    /**
     * Hide add holding form
     */
    hideAddHoldingForm() {
        const form = document.getElementById('add-holding-form');
        if (form) form.style.display = 'none';
    }

    /**
     * Load available cryptos for holding dropdown
     */
    async loadAvailableCryptos() {
        try {
            const response = await fetch('/api/assets');
            if (!response.ok) throw new Error('Failed to fetch assets');

            const data = await response.json();
            const assets = data.assets || [];

            const select = document.getElementById('holding-symbol');
            if (!select) return;

            select.innerHTML = '<option value="">Sélectionner une crypto...</option>' +
                assets.slice(0, 50).map(asset =>
                    `<option value="${asset.symbol}">${asset.symbol.toUpperCase()} - ${asset.name}</option>`
                ).join('');
        } catch (error) {
            console.error('Error loading cryptos:', error);
        }
    }

    /**
     * Submit holding form
     */
    async submitHoldingForm() {
        if (!this.selectedWalletId) {
            UIUtils.showNotification('No wallet selected', 'error');
            return;
        }

        const symbolInput = document.getElementById('holding-symbol');
        const quantityInput = document.getElementById('holding-quantity');
        const avgPriceInput = document.getElementById('holding-avg-price');

        if (!symbolInput || !quantityInput) return;

        const symbol = symbolInput.value;
        const quantity = parseFloat(quantityInput.value);
        const avgPrice = avgPriceInput && avgPriceInput.value ? parseFloat(avgPriceInput.value) : null;

        if (!symbol) {
            UIUtils.showNotification('Please select a crypto', 'error');
            return;
        }

        if (isNaN(quantity) || quantity <= 0) {
            UIUtils.showNotification('Please enter a valid quantity', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/wallets/${this.selectedWalletId}/holdings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    quantity: quantity,
                    avg_buy_price: avgPrice
                })
            });

            if (!response.ok) throw new Error('Failed to add holding');

            UIUtils.showNotification('Holding added successfully!', 'success');
            this.hideAddHoldingForm();

            // Reset form
            if (symbolInput) symbolInput.value = '';
            if (quantityInput) quantityInput.value = '';
            if (avgPriceInput) avgPriceInput.value = '';

            // Reload wallet data
            await this.loadWalletsData();
        } catch (error) {
            console.error('Error adding holding:', error);
            UIUtils.showNotification('Failed to add holding', 'error');
        }
    }

    /**
     * Delete wallet
     */
    async deleteWallet() {
        if (!this.selectedWalletId) return;

        if (!confirm(`Are you sure you want to delete "${this.selectedWalletName}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/wallets/${this.selectedWalletId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete wallet');

            UIUtils.showNotification('Wallet deleted successfully!', 'success');
            this.selectedWalletId = null;
            this.selectedWalletName = '';
            this.hideWalletForm();
            await this.loadWalletsData();
        } catch (error) {
            console.error('Error deleting wallet:', error);
            UIUtils.showNotification('Failed to delete wallet', 'error');
        }
    }

    /**
     * Handle price update from WebSocket
     */
    handlePriceUpdate(data) {
        const prices = data.payload || {};

        // Store current prices
        Object.assign(this.currentPrices, prices);

        // Update price displays
        this.updatePriceDisplays(prices);

        // Update wallet with current prices
        this.updateWalletWithCurrentPrices();

        // Update market cap visualization
        this.fedEdgeAI.dashboardManager?.updateMarketCapVisualization(prices);
    }

    /**
     * Update price displays in UI
     */
    updatePriceDisplays(prices) {
        // Update individual price elements
        Object.entries(prices).forEach(([cryptoId, data]) => {
            const priceElement = document.getElementById(`price-${cryptoId}`);
            if (priceElement) {
                priceElement.innerHTML = this.createPriceElementHTML(cryptoId, data);
            }
        });

        // Update crypto prices container
        this.updateCryptoPricesContainer(prices);
    }

    /**
     * Update crypto prices container
     */
    updateCryptoPricesContainer(prices) {
        const container = document.getElementById('crypto-prices');
        if (!container) return;

        // Get top 10 by market cap
        const sortedPrices = Object.entries(prices)
            .filter(([id, data]) => data.market_cap > 0)
            .sort((a, b) => b[1].market_cap - a[1].market_cap)
            .slice(0, 10);

        if (sortedPrices.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: #6b7280; padding: 20px;">
                    Loading prices...
                </div>
            `;
            return;
        }

        container.innerHTML = sortedPrices.map(([cryptoId, data]) => {
            const symbol = UIUtils.getCryptoSymbol(cryptoId);
            const change = data.usd_24h_change || 0;
            const changeColor = change > 0 ? '#10b981' : change < 0 ? '#ef4444' : '#6b7280';

            return `
                <div style="
                    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
                    border-radius: 8px;
                    padding: 12px;
                    border-left: 3px solid #6366f1;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
                        <span style="font-size: 20px;">${symbol}</span>
                        <div>
                            <div style="font-weight: 600; color: #1f2937; font-size: 13px;">
                                ${cryptoId.toUpperCase().replace(/-/g, ' ')}
                            </div>
                            <div style="font-size: 11px; color: #6b7280;">
                                ${UIUtils.formatMarketCap(data.market_cap)}
                            </div>
                        </div>
                    </div>
                    <div style="text-align: right; display: flex; align-items: center; gap: 12px;">
                        <div>
                            <div style="font-weight: 600; color: #fff; font-size: 14px;">
                                ${UIUtils.formatPrice(data.usd)}
                            </div>
                            <div style="font-size: 12px; color: ${changeColor}; font-weight: 600;">
                                ${change > 0 ? '↑' : change < 0 ? '↓' : '→'} ${UIUtils.formatPercentage(Math.abs(change))}
                            </div>
                        </div>
                        <button onclick="window.fedEdgeAI?.showAssetStatsForSymbol('${cryptoId}')" style="
                            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                            border: none;
                            border-radius: 6px;
                            padding: 6px 10px;
                            color: white;
                            font-size: 11px;
                            cursor: pointer;
                            font-weight: 600;
                            white-space: nowrap;
                        " title="View chart and stats">
                            📊 Chart
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Update last update time
        const updateTime = document.getElementById('prices-last-update');
        if (updateTime) {
            updateTime.textContent = new Date().toLocaleTimeString();
        }
    }

    /**
     * Create price element HTML
     */
    createPriceElementHTML(crypto, data) {
        const symbol = UIUtils.getCryptoSymbol(crypto);
        const price = data.usd || 0;
        const change = data.usd_24h_change || 0;
        const changeColor = UIUtils.getValueColor(change);

        return `
            <div style="
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
                border-radius: 8px;
                padding: 12px;
                border-left: 3px solid #6366f1;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 20px;">${symbol}</span>
                    <span style="font-weight: 600; color: #1f2937;">${crypto.toUpperCase()}</span>
                </div>
                <div style="font-size: 18px; font-weight: 700; color: #1f2937; margin-bottom: 4px;">
                    ${UIUtils.formatPrice(price)}
                </div>
                <div style="font-size: 12px; color: ${changeColor}; font-weight: 600;">
                    ${change > 0 ? '↑' : change < 0 ? '↓' : '→'} ${UIUtils.formatPercentage(change)}
                </div>
            </div>
        `;
    }

    /**
     * Handle wallet update from WebSocket
     */
    handleWalletUpdate(data) {
        const payload = data.payload || {};
        const holdings = payload.holdings || [];

        this.updateWalletHoldings(holdings);
        UIUtils.showNotification('Wallet updated', 'success');
    }

    /**
     * Update wallet holdings display
     */
    updateWalletHoldings(holdings) {
        const walletHoldingsDiv = document.getElementById('wallet-holdings');
        if (!walletHoldingsDiv) return;

        if (!holdings || holdings.length === 0) {
            walletHoldingsDiv.innerHTML = `
                <div style="text-align: center; color: #6b7280; padding: 20px;">
                    No holdings yet. Execute trades to see them here.
                </div>
            `;
            return;
        }

        let totalValue = 0;
        const holdingsHTML = holdings.map(holding => {
            const coingeckoId = UIUtils.getCoingeckoId(holding.ticker);
            const currentPrice = coingeckoId ? (this.currentPrices[coingeckoId]?.usd || 0) : 0;
            const value = holding.amount * currentPrice;
            totalValue += value;

            return `
                <div style="
                    background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(5, 150, 105, 0.05));
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 8px;
                    border-left: 3px solid #10b981;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">
                                ${UIUtils.escapeHtml(holding.ticker)}
                            </div>
                            <div style="font-size: 12px; color: #6b7280;">
                                ${holding.amount.toFixed(6)} units
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 600; color: #1f2937;">
                                ${UIUtils.formatPrice(value)}
                            </div>
                            <div style="font-size: 12px; color: #6b7280;">
                                @ ${UIUtils.formatPrice(currentPrice)}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        walletHoldingsDiv.innerHTML = `
            <div style="
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 16px;
                color: white;
            ">
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 4px;">Total Portfolio Value</div>
                <div style="font-size: 24px; font-weight: 700;">${UIUtils.formatPrice(totalValue)}</div>
            </div>
            ${holdingsHTML}
        `;
    }

    /**
     * Update wallet with current prices
     */
    updateWalletWithCurrentPrices() {
        // Get current holdings and recalculate with latest prices
        const walletHoldingsDiv = document.getElementById('wallet-holdings');
        if (walletHoldingsDiv) {
            // This will be triggered after price updates
            // The actual holdings data will be fetched from the backend
        }
    }

    /**
     * Handle wallet performance update
     */
    handleWalletPerformance(data) {
        const payload = data.payload || {};
        const wallets = payload.wallets || [];

        // Find best and worst performers
        if (wallets.length > 0) {
            const sorted = [...wallets].sort((a, b) => b.pnl_percentage - a.pnl_percentage);
            const best = sorted[0];
            const worst = sorted[sorted.length - 1];

            this.updatePerformerDisplay('best-performer', best, true);
            this.updatePerformerDisplay('worst-performer', worst, false);
        }
    }

    /**
     * Update performer display
     */
    updatePerformerDisplay(elementId, performer, isBest) {
        const element = document.getElementById(elementId);
        if (!element || !performer) return;

        const color = isBest ? '#10b981' : '#ef4444';
        const icon = isBest ? '🏆' : '📉';

        element.innerHTML = `
            <div style="
                background: linear-gradient(135deg, ${color}22, ${color}11);
                border-radius: 8px;
                padding: 12px;
                border-left: 3px solid ${color};
            ">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 24px;">${icon}</span>
                    <div>
                        <div style="font-weight: 600; color: #1f2937;">
                            ${UIUtils.escapeHtml(performer.wallet_name)}
                        </div>
                        <div style="font-size: 12px; color: #6b7280;">
                            ${performer.trades_count || 0} trades
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 12px; color: #6b7280;">P&L</div>
                        <div style="font-size: 18px; font-weight: 700; color: ${color};">
                            ${UIUtils.formatPercentage(performer.pnl_percentage)}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 12px; color: #6b7280;">Value</div>
                        <div style="font-size: 14px; font-weight: 600; color: #1f2937;">
                            ${UIUtils.formatPrice(performer.current_value)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Load wallets data
     */
    async loadWalletsData() {
        try {
            const response = await fetch('/api/wallets');
            if (!response.ok) throw new Error('Failed to fetch wallets');

            const data = await response.json();
            const wallets = data.wallets || [];
            this.renderWalletsList(wallets);
        } catch (error) {
            console.error('Error loading wallets:', error);
            UIUtils.showNotification('Failed to load wallets', 'error');
        }
    }

    /**
     * Render wallets list
     */
    renderWalletsList(wallets) {
        const walletsContainer = document.getElementById('wallets-list');
        if (!walletsContainer) return;

        if (!wallets || wallets.length === 0) {
            walletsContainer.innerHTML = `
                <div style="text-align: center; color: #6b7280; padding: 20px;">
                    No wallets found. Create your first wallet!
                </div>
            `;
            return;
        }

        walletsContainer.innerHTML = wallets.map(wallet => `
            <div class="wallet-item" onclick="window.fedEdgeAI.walletManager.selectWallet(${wallet.id}, '${UIUtils.escapeHtml(wallet.name)}')" style="
                background: white;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                cursor: pointer;
                border: 2px solid ${wallet.id === this.selectedWalletId ? '#3b82f6' : '#e5e7eb'};
                transition: all 0.2s;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">
                            ${UIUtils.escapeHtml(wallet.name || 'Unnamed Wallet')}
                        </div>
                        <div style="font-size: 12px; color: #6b7280;">
                            ID: ${wallet.id}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 14px; font-weight: 600; color: #1f2937;">
                            ${UIUtils.formatPrice(wallet.balance || 0)}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Select wallet
     */
    async selectWallet(walletId, walletName) {
        this.selectedWalletId = walletId;
        this.selectedWalletName = walletName;

        console.log(`Selected wallet: ${walletName} (ID: ${walletId})`);

        // Show wallet edit form
        await this.showWalletEditForm(walletId, walletName);

        // Load and display wallet holdings
        await this.loadWalletHoldings(walletId);

        // Reload wallet list to update selection highlighting
        this.loadWalletsData();
    }

    /**
     * Show wallet edit form
     */
    async showWalletEditForm(walletId, walletName) {
        const placeholder = document.getElementById('wallet-form-placeholder');
        const form = document.getElementById('wallet-form');
        const title = document.getElementById('wallet-form-title');
        const deleteBtn = document.getElementById('delete-wallet-btn');
        const nameInput = document.getElementById('wallet-name');
        const budgetInput = document.getElementById('wallet-initial-budget-input');

        if (placeholder) placeholder.style.display = 'none';
        if (form) form.style.display = 'block';
        if (title) title.textContent = `Edit: ${walletName}`;
        if (deleteBtn) deleteBtn.style.display = 'inline-block';

        // Fetch wallet details
        try {
            const response = await fetch(`/api/wallets/${walletId}`);
            if (!response.ok) throw new Error('Failed to fetch wallet details');

            const wallet = await response.json();

            if (nameInput) nameInput.value = wallet.name || walletName;
            if (budgetInput) budgetInput.value = wallet.balance || wallet.initial_balance || 0;
        } catch (error) {
            console.error('Error loading wallet details:', error);
            if (nameInput) nameInput.value = walletName;
        }
    }

    /**
     * Load wallet holdings
     */
    async loadWalletHoldings(walletId) {
        const placeholder = document.getElementById('holdings-placeholder');
        const list = document.getElementById('holdings-list');
        const summary = document.getElementById('holdings-summary');
        const addButton = document.getElementById('add-holding-btn');

        try {
            const response = await fetch(`/api/wallets/${walletId}/holdings`);
            if (!response.ok) throw new Error('Failed to fetch holdings');

            const data = await response.json();
            const holdings = data.holdings || [];

            if (placeholder) placeholder.style.display = 'none';
            if (addButton) addButton.style.display = 'inline-block';

            if (!holdings || holdings.length === 0) {
                if (list) {
                    list.style.display = 'block';
                    list.innerHTML = `
                        <div style="text-align: center; color: #9ca3af; padding: 20px;">
                            No holdings yet. Click "+ Add" to add crypto.
                        </div>
                    `;
                }
                if (summary) summary.style.display = 'none';
                return;
            }

            if (list) {
                list.style.display = 'block';
                list.innerHTML = holdings.map(holding => {
                    const pnl = holding.pnl || 0;
                    const pnlPercent = holding.pnl_percent || 0;
                    const pnlColor = pnl >= 0 ? '#10b981' : '#ef4444';

                    return `
                        <div style="
                            background: rgba(255, 255, 255, 0.05);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 6px;
                            padding: 12px;
                            margin-bottom: 8px;
                        ">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <div style="font-weight: 600; color: #fff; font-size: 14px;">
                                    ${(holding.symbol || holding.crypto_id || 'N/A').toUpperCase()}
                                </div>
                                <div style="font-size: 12px; color: ${pnlColor}; font-weight: 600;">
                                    ${pnl >= 0 ? '+' : ''}${UIUtils.formatPrice(pnl)} (${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
                                <div>
                                    <span style="color: #9ca3af;">Qty:</span>
                                    <span style="color: #fff;">${(holding.quantity || 0).toFixed(8)}</span>
                                </div>
                                <div>
                                    <span style="color: #9ca3af;">Avg:</span>
                                    <span style="color: #fff;">${UIUtils.formatPrice(holding.avg_buy_price || 0)}</span>
                                </div>
                                <div>
                                    <span style="color: #9ca3af;">Current:</span>
                                    <span style="color: #fff;">${UIUtils.formatPrice(holding.current_price || 0)}</span>
                                </div>
                                <div>
                                    <span style="color: #9ca3af;">Value:</span>
                                    <span style="color: #fff;">${UIUtils.formatPrice(holding.current_value || 0)}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Calculate totals from backend data
            let totalPnl = 0;
            let totalCost = 0;
            holdings.forEach(holding => {
                totalPnl += (holding.pnl || 0);
                totalCost += (holding.total_invested || 0);
            });

            const totalRoi = totalCost > 0 ? (totalPnl / totalCost * 100) : 0;
            const pnlColor = totalPnl >= 0 ? '#10b981' : '#ef4444';

            if (summary) {
                summary.style.display = 'block';
                const pnlElement = summary.querySelector('#total-pnl');
                const roiElement = summary.querySelector('#total-roi');
                if (pnlElement) {
                    pnlElement.textContent = `${totalPnl >= 0 ? '+' : ''}${UIUtils.formatPrice(totalPnl)}`;
                    pnlElement.style.color = pnlColor;
                }
                if (roiElement) {
                    roiElement.textContent = `${totalRoi >= 0 ? '+' : ''}${totalRoi.toFixed(2)}%`;
                    roiElement.style.color = pnlColor;
                }
            }

        } catch (error) {
            console.error('Error loading holdings:', error);
            if (list) {
                list.style.display = 'block';
                list.innerHTML = `
                    <div style="text-align: center; color: #ef4444; padding: 20px;">
                        Failed to load holdings
                    </div>
                `;
            }
        }
    }

    /**
     * Create new wallet
     */
    async createNewWallet() {
        const walletName = prompt('Enter wallet name:');
        if (!walletName) return;

        const initialBalance = prompt('Enter initial balance:', '10000');
        if (!initialBalance) return;

        try {
            const response = await fetch('/api/wallets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: walletName,
                    initial_balance: parseFloat(initialBalance)
                })
            });

            if (!response.ok) throw new Error('Failed to create wallet');

            const wallet = await response.json();
            UIUtils.showNotification('Wallet created successfully', 'success');

            // Reload wallets
            this.loadWalletsData();
        } catch (error) {
            console.error('Error creating wallet:', error);
            UIUtils.showNotification('Failed to create wallet', 'error');
        }
    }
}
