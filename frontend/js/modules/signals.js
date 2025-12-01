/**
 * Signals Manager Module
 * Handles AI trading signals, pagination, and display
 */

import { UIUtils } from './ui-utils.js';

export class SignalsManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.signals = [];
        this.currentPage = 0;
        this.signalsPerPage = 4;
    }

    /**
     * Setup signal pagination
     */
    setupSignalPagination() {
        // Pagination buttons will be created dynamically
    }

    /**
     * Load AI signals from API
     */
    async loadAISignals() {
        try {
            const response = await fetch('/api/signals?limit=20');
            if (!response.ok) throw new Error('Failed to fetch signals');

            const data = await response.json();
            this.signals = data.signals || [];

            console.log(`Loaded ${this.signals.length} signals`);
            this.renderSignals();
            this.updateAISignalsSummary();
        } catch (error) {
            console.error('Error loading signals:', error);
            this.showSignalsError();
        }
    }

    /**
     * Update AI signals summary panel
     */
    updateAISignalsSummary() {
        const summaryElement = document.getElementById('ai-signals-summary');
        const scoreElement = document.getElementById('ai-signals-score');
        const updatedElement = document.getElementById('ai-signals-updated');

        if (!summaryElement) return;

        if (this.signals.length === 0) {
            summaryElement.innerHTML = 'No active trading signals. The AI is monitoring markets and will generate signals when opportunities are detected.';
            if (scoreElement) scoreElement.textContent = 'N/A';
            if (updatedElement) updatedElement.textContent = new Date().toLocaleTimeString();
            return;
        }

        // Calculate summary stats
        const buySignals = this.signals.filter(s => s.action === 'BUY').length;
        const sellSignals = this.signals.filter(s => s.action === 'SELL').length;
        const avgConfidence = this.signals.reduce((sum, s) => sum + (s.confidence || 0), 0) / this.signals.length;

        summaryElement.innerHTML = `
            <strong>${this.signals.length}</strong> active signals detected:
            <span style="color: #10b981;">${buySignals} BUY</span>,
            <span style="color: #ef4444;">${sellSignals} SELL</span>.
            Average confidence: <strong>${avgConfidence.toFixed(1)}%</strong>
        `;

        if (scoreElement) {
            scoreElement.textContent = avgConfidence.toFixed(0);
        }

        if (updatedElement) {
            updatedElement.textContent = new Date().toLocaleTimeString();
        }
    }

    /**
     * Render signals for bots page (compact list)
     */
    renderBotsPageSignals(container) {
        if (!this.signals || this.signals.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px; font-size: 12px;">
                    Aucun signal actif
                </div>
            `;
            return;
        }

        container.innerHTML = this.signals.map(signal => `
            <div style="
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 8px;
                border-left: 3px solid ${this.getActionColor(signal.action)};
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span style="
                            background: ${this.getActionColor(signal.action)};
                            color: white;
                            padding: 2px 8px;
                            border-radius: 4px;
                            font-size: 10px;
                            font-weight: 600;
                        ">${signal.action}</span>
                        <span style="color: #fff; font-weight: 600; font-size: 13px;">${UIUtils.escapeHtml(signal.ticker)}</span>
                    </div>
                    <div style="font-size: 10px; color: #9ca3af;">
                        Entry: ${UIUtils.formatPrice(signal.entry_price)} |
                        TP: <span style="color: #10b981;">${UIUtils.formatPrice(signal.target_price)}</span> |
                        SL: <span style="color: #ef4444;">${UIUtils.formatPrice(signal.stop_loss)}</span>
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

    /**
     * Handle new signal from WebSocket
     */
    handleNewSignal(data) {
        const signal = data.payload || {};

        // Add to beginning of signals array
        this.signals.unshift(signal);

        // Keep only last 20 signals
        if (this.signals.length > 20) {
            this.signals = this.signals.slice(0, 20);
        }

        // Render signals
        this.renderSignals();

        // Show notification
        UIUtils.showNotification(`New ${signal.action} signal for ${signal.ticker}`, 'info');
    }

    /**
     * Render signals
     */
    renderSignals() {
        // Check if we're on the bots page (compact layout)
        const botSignalsList = document.getElementById('bot-signals-list');
        if (botSignalsList) {
            this.renderBotsPageSignals(botSignalsList);
            return;
        }

        // Dashboard page (grid layout)
        const signalsGrid = document.getElementById('signals-container');
        if (!signalsGrid) {
            console.warn('signals-container element not found');
            return;
        }

        if (!this.signals || this.signals.length === 0) {
            signalsGrid.innerHTML = `
                <div style="
                    grid-column: 1 / -1;
                    text-align: center;
                    color: #6b7280;
                    padding: 40px;
                ">
                    <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                    <div>No signals available yet. They will appear here when generated.</div>
                </div>
            `;
            return;
        }

        // Calculate pagination
        const totalPages = Math.ceil(this.signals.length / this.signalsPerPage);
        const startIdx = this.currentPage * this.signalsPerPage;
        const endIdx = startIdx + this.signalsPerPage;
        const pageSignals = this.signals.slice(startIdx, endIdx);

        // Render signals
        signalsGrid.innerHTML = pageSignals.map((signal, index) => {
            const size = index === 0 ? 'large' : 'small';
            return this.createSignalElement(signal, size);
        }).join('');

        // Add pagination
        if (totalPages > 1) {
            const paginationHTML = this.createPaginationElement(totalPages);
            signalsGrid.innerHTML += paginationHTML;
        }
    }

    /**
     * Create signal element
     */
    createSignalElement(signal, size = 'small') {
        const isLarge = size === 'large';
        const actionColor = this.getActionColor(signal.action);

        return `
            <div class="signal-card ${size}" onclick="window.fedEdgeAI.signalsManager.openSignalModal(${JSON.stringify(signal).replace(/"/g, '&quot;')})" style="
                background: linear-gradient(135deg, ${actionColor}22, ${actionColor}11);
                border-radius: 12px;
                padding: ${isLarge ? '20px' : '16px'};
                cursor: pointer;
                border-left: 4px solid ${actionColor};
                transition: all 0.2s;
                ${isLarge ? 'grid-column: span 2; grid-row: span 2;' : ''}
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <div>
                        <div style="
                            display: inline-block;
                            background: ${actionColor};
                            color: white;
                            padding: 4px 12px;
                            border-radius: 12px;
                            font-size: ${isLarge ? '14px' : '12px'};
                            font-weight: 600;
                            margin-bottom: 8px;
                        ">
                            ${signal.action || 'HOLD'}
                        </div>
                        <div style="font-size: ${isLarge ? '24px' : '18px'}; font-weight: 700; color: #ffffff;">
                            ${UIUtils.escapeHtml(signal.ticker || 'N/A')}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: ${isLarge ? '20px' : '16px'}; font-weight: 700; color: #1f2937;">
                            ${UIUtils.formatPrice(signal.entry_price || 0)}
                        </div>
                        <div style="font-size: ${isLarge ? '14px' : '12px'}; color: #6b7280;">
                            Entry
                        </div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: ${isLarge ? '12px' : '8px'}; margin-bottom: ${isLarge ? '12px' : '8px'};">
                    <div>
                        <div style="font-size: ${isLarge ? '12px' : '10px'}; color: #6b7280; margin-bottom: 4px;">Target</div>
                        <div style="font-size: ${isLarge ? '16px' : '14px'}; font-weight: 600; color: #10b981;">
                            ${UIUtils.formatPrice(signal.target_price || 0)}
                        </div>
                    </div>
                    <div>
                        <div style="font-size: ${isLarge ? '12px' : '10px'}; color: #6b7280; margin-bottom: 4px;">Stop Loss</div>
                        <div style="font-size: ${isLarge ? '16px' : '14px'}; font-weight: 600; color: #ef4444;">
                            ${UIUtils.formatPrice(signal.stop_loss || 0)}
                        </div>
                    </div>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: ${isLarge ? '12px' : '8px'}; padding-top: ${isLarge ? '12px' : '8px'}; border-top: 1px solid rgba(0, 0, 0, 0.1);">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <div style="
                            width: ${isLarge ? '32px' : '24px'};
                            height: ${isLarge ? '32px' : '24px'};
                            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-size: ${isLarge ? '14px' : '12px'};
                            font-weight: 700;
                        ">
                            ${Math.round(signal.confidence || 0)}
                        </div>
                        <div>
                            <div style="font-size: ${isLarge ? '12px' : '10px'}; color: #6b7280;">Confidence</div>
                            <div style="font-size: ${isLarge ? '14px' : '12px'}; font-weight: 600; color: #1f2937;">
                                ${UIUtils.formatPercentage(signal.confidence || 0)}
                            </div>
                        </div>
                    </div>
                    <div style="font-size: ${isLarge ? '12px' : '10px'}; color: #6b7280;">
                        ${UIUtils.formatTimestamp(signal.timestamp || signal.created_at)}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get action color
     */
    getActionColor(action) {
        const colors = {
            'BUY': '#10b981',
            'SELL': '#ef4444',
            'HOLD': '#6b7280'
        };
        return colors[action?.toUpperCase()] || colors.HOLD;
    }

    /**
     * Create pagination element
     */
    createPaginationElement(totalPages) {
        return `
            <div style="
                grid-column: 1 / -1;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 12px;
                padding: 16px;
            ">
                <button class="pagination-btn" ${this.currentPage === 0 ? 'disabled' : ''} onclick="window.fedEdgeAI.signalsManager.prevPage()" style="
                    padding: 8px 16px;
                    background: ${this.currentPage === 0 ? '#e5e7eb' : '#3b82f6'};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: ${this.currentPage === 0 ? 'not-allowed' : 'pointer'};
                    font-weight: 600;
                ">
                    Previous
                </button>
                <span style="color: #6b7280; font-size: 14px;">
                    Page ${this.currentPage + 1} of ${totalPages}
                </span>
                <button class="pagination-btn" ${this.currentPage >= totalPages - 1 ? 'disabled' : ''} onclick="window.fedEdgeAI.signalsManager.nextPage()" style="
                    padding: 8px 16px;
                    background: ${this.currentPage >= totalPages - 1 ? '#e5e7eb' : '#3b82f6'};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: ${this.currentPage >= totalPages - 1 ? 'not-allowed' : 'pointer'};
                    font-weight: 600;
                ">
                    Next
                </button>
            </div>
        `;
    }

    /**
     * Navigate to previous page
     */
    prevPage() {
        if (this.currentPage > 0) {
            this.currentPage--;
            this.renderSignals();
        }
    }

    /**
     * Navigate to next page
     */
    nextPage() {
        const totalPages = Math.ceil(this.signals.length / this.signalsPerPage);
        if (this.currentPage < totalPages - 1) {
            this.currentPage++;
            this.renderSignals();
        }
    }

    /**
     * Open signal modal with details
     */
    openSignalModal(signal) {
        // This will be implemented in the modals module
        console.log('Opening signal modal:', signal);
        UIUtils.showNotification('Signal details modal - Coming soon', 'info');
    }

    /**
     * Show signals error
     */
    showSignalsError() {
        const signalsGrid = document.getElementById('signals-container');
        if (!signalsGrid) return;

        UIUtils.showError(signalsGrid, 'Failed to load signals');
    }
}
