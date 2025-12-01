/**
 * UI Utilities Module
 * Provides utility functions for formatting, notifications, and common UI operations
 */

export class UIUtils {
    /**
     * Show a notification to the user
     * @param {string} message - The message to display
     * @param {string} type - Type of notification: 'info', 'success', 'warning', 'error'
     * @param {number} duration - Duration in milliseconds (default: 3000)
     */
    static showNotification(message, type = 'info', duration = 3000) {
        const notificationContainer = document.getElementById('notification-container') || this.createNotificationContainer();

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            padding: 12px 20px;
            margin-bottom: 10px;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease-out;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        `;

        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌'
        };

        const colors = {
            info: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
            success: 'linear-gradient(135deg, #10b981, #059669)',
            warning: 'linear-gradient(135deg, #f59e0b, #d97706)',
            error: 'linear-gradient(135deg, #ef4444, #dc2626)'
        };

        notification.style.background = colors[type] || colors.info;
        notification.innerHTML = `
            <span style="font-size: 18px;">${icons[type] || icons.info}</span>
            <span>${this.escapeHtml(message)}</span>
        `;

        notificationContainer.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    /**
     * Create notification container if it doesn't exist
     */
    static createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(container);

        // Add animations
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(400px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        return container;
    }

    /**
     * Format price with appropriate decimals
     * @param {number} price - The price to format
     * @returns {string} Formatted price
     */
    static formatPrice(price) {
        if (!price || isNaN(price)) return '$0.00';

        if (price < 0.01) {
            return `$${price.toFixed(6)}`;
        } else if (price < 1) {
            return `$${price.toFixed(4)}`;
        } else if (price < 100) {
            return `$${price.toFixed(2)}`;
        } else {
            return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    }

    /**
     * Format market cap
     * @param {number} marketCap - The market cap value
     * @returns {string} Formatted market cap
     */
    static formatMarketCap(marketCap) {
        if (!marketCap || isNaN(marketCap)) return '$0';

        if (marketCap >= 1e12) {
            return `$${(marketCap / 1e12).toFixed(2)}T`;
        } else if (marketCap >= 1e9) {
            return `$${(marketCap / 1e9).toFixed(2)}B`;
        } else if (marketCap >= 1e6) {
            return `$${(marketCap / 1e6).toFixed(2)}M`;
        } else if (marketCap >= 1e3) {
            return `$${(marketCap / 1e3).toFixed(2)}K`;
        } else {
            return `$${marketCap.toFixed(2)}`;
        }
    }

    /**
     * Format percentage
     * @param {number} value - The percentage value
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted percentage
     */
    static formatPercentage(value, decimals = 2) {
        if (!value || isNaN(value)) return '0.00%';
        return `${value.toFixed(decimals)}%`;
    }

    /**
     * Get color based on value (positive = green, negative = red)
     * @param {number} value - The value to check
     * @returns {string} Color code
     */
    static getValueColor(value) {
        if (value > 0) return '#10b981';
        if (value < 0) return '#ef4444';
        return '#6b7280';
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    static escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Convert frequency string to minutes
     * @param {string} freqStr - Frequency string (e.g., "5m", "1h", "1d")
     * @returns {number} Minutes
     */
    static convertFrequencyToMinutes(freqStr) {
        if (!freqStr) return 5;

        const match = freqStr.match(/^(\d+)([mhd])$/);
        if (!match) return 5;

        const value = parseInt(match[1]);
        const unit = match[2];

        switch(unit) {
            case 'm': return value;
            case 'h': return value * 60;
            case 'd': return value * 60 * 24;
            default: return 5;
        }
    }

    /**
     * Format timestamp to readable date
     * @param {string|number} timestamp - Timestamp to format
     * @returns {string} Formatted date
     */
    static formatTimestamp(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Get cryptocurrency symbol/emoji
     * @param {string} cryptoId - Crypto ID
     * @returns {string} Symbol
     */
    static getCryptoSymbol(cryptoId) {
        const symbols = {
            'bitcoin': '₿',
            'ethereum': 'Ξ',
            'tether': '₮',
            'binancecoin': 'Ƀ',
            'ripple': 'Ʀ',
            'cardano': '₳',
            'solana': '◎',
            'polkadot': '●',
            'dogecoin': 'Ð',
            'usd-coin': '$'
        };
        return symbols[cryptoId] || '◆';
    }

    /**
     * Get Coingecko ID from ticker
     * @param {string} ticker - Ticker symbol
     * @returns {string} Coingecko ID
     */
    static getCoingeckoId(ticker) {
        if (!ticker) return null;

        const mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDT': 'tether',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'SOL': 'solana',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'USDC': 'usd-coin',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'ATOM': 'cosmos'
        };

        return mapping[ticker.toUpperCase()] || null;
    }

    /**
     * Show loading spinner in element
     * @param {HTMLElement} element - Element to show spinner in
     * @param {string} message - Loading message
     */
    static showLoading(element, message = 'Loading...') {
        if (!element) return;

        element.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                color: #6b7280;
            ">
                <div style="
                    width: 40px;
                    height: 40px;
                    border: 4px solid #e5e7eb;
                    border-top-color: #3b82f6;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                "></div>
                <p style="margin-top: 16px; font-size: 14px;">${this.escapeHtml(message)}</p>
            </div>
        `;

        // Add spin animation if not already added
        if (!document.getElementById('spinner-styles')) {
            const style = document.createElement('style');
            style.id = 'spinner-styles';
            style.textContent = `
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Show error message in element
     * @param {HTMLElement} element - Element to show error in
     * @param {string} message - Error message
     */
    static showError(element, message = 'An error occurred') {
        if (!element) return;

        element.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                color: #ef4444;
            ">
                <span style="font-size: 48px;">⚠️</span>
                <p style="margin-top: 16px; font-size: 14px; text-align: center;">${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    /**
     * Debounce function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Create a modal overlay
     * @param {string} content - HTML content for modal
     * @param {Object} options - Modal options
     * @returns {HTMLElement} Modal element
     */
    static createModal(content, options = {}) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            background: rgba(0, 0, 0, 0.7) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            z-index: 99999 !important;
            visibility: visible !important;
            opacity: 1 !important;
        `;

        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.style.cssText = `
            display: block !important;
            background: white !important;
            border-radius: 12px;
            padding: ${options.padding || '24px'};
            width: ${options.width || '90%'};
            max-width: ${options.maxWidth || '600px'};
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            position: relative !important;
            z-index: 100000 !important;
            visibility: visible !important;
            opacity: 1 !important;
        `;
        modalContent.innerHTML = content;

        console.log('[UIUtils] Modal content created:', modalContent);

        modal.appendChild(modalContent);

        console.log('[UIUtils] Modal structure complete, overlay:', modal);

        // Close on overlay click
        if (options.closeOnOverlay !== false) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    console.log('[UIUtils] Closing modal');
                    modal.remove();
                }
            });
        }

        // Comprehensive debugging after appending to DOM
        setTimeout(() => {
            console.log('[UIUtils] === MODAL DEBUG INFO ===');
            console.log('[UIUtils] Modal in DOM:', document.body.contains(modal));
            console.log('[UIUtils] Modal-content in DOM:', document.body.contains(modalContent));

            // Check dimensions
            const modalRect = modal.getBoundingClientRect();
            const contentRect = modalContent.getBoundingClientRect();
            console.log('[UIUtils] Modal dimensions:', {
                width: modalRect.width,
                height: modalRect.height,
                top: modalRect.top,
                left: modalRect.left
            });
            console.log('[UIUtils] Modal-content dimensions:', {
                width: contentRect.width,
                height: contentRect.height,
                top: contentRect.top,
                left: contentRect.left
            });

            // Check computed styles
            const modalComputed = window.getComputedStyle(modal);
            const contentComputed = window.getComputedStyle(modalContent);
            console.log('[UIUtils] Modal computed display:', modalComputed.display);
            console.log('[UIUtils] Modal computed visibility:', modalComputed.visibility);
            console.log('[UIUtils] Modal computed opacity:', modalComputed.opacity);
            console.log('[UIUtils] Modal computed z-index:', modalComputed.zIndex);
            console.log('[UIUtils] Modal-content computed display:', contentComputed.display);
            console.log('[UIUtils] Modal-content computed visibility:', contentComputed.visibility);
            console.log('[UIUtils] Modal-content computed opacity:', contentComputed.opacity);

            // Check if there are any elements with higher z-index
            const allElements = document.querySelectorAll('*');
            let maxZIndex = 0;
            allElements.forEach(el => {
                const z = parseInt(window.getComputedStyle(el).zIndex);
                if (!isNaN(z) && z > maxZIndex) {
                    maxZIndex = z;
                    if (z > 99999) {
                        console.log('[UIUtils] Found element with higher z-index:', z, el);
                    }
                }
            });
            console.log('[UIUtils] Max z-index in page:', maxZIndex);
            console.log('[UIUtils] === END DEBUG INFO ===');
        }, 100);

        // Add modal to DOM
        document.body.appendChild(modal);
        console.log('[UIUtils] Modal appended to body');

        // Setup close buttons
        setTimeout(() => {
            const closeButtons = modal.querySelectorAll('.close-modal');
            closeButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    console.log('[UIUtils] Close button clicked');
                    modal.remove();
                });
            });
            console.log(`[UIUtils] Setup ${closeButtons.length} close button(s)`);
        }, 50);

        return modal;
    }
}
