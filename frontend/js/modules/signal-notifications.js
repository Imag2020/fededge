/**
 * Signal Notifications Module
 * Handles real-time signal notifications that appear on any page
 */

export class SignalNotifications {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.currentSignal = null;
        this.autoCloseTimeout = null;
        this.isModalVisible = false;
    }

    /**
     * Initialize signal notifications
     */
    async init() {
        console.log('[SignalNotifications] Initializing...');

        // Load the modal HTML into the page
        await this.loadModalHTML();

        // Setup global functions
        this.setupGlobalFunctions();

        // Update counters initially
        this.updateSignalCounters();

        // Update counters every 30 seconds
        setInterval(() => {
            this.updateSignalCounters();
        }, 30000);

        console.log('[SignalNotifications] ✓ Initialized');
    }

    /**
     * Load modal HTML into the page
     */
    async loadModalHTML() {
        try {
            const response = await fetch('/frontend/components/signal-notification-modal.html');
            const html = await response.text();

            // Inject modal at the end of body
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            document.body.appendChild(tempDiv.firstElementChild);

            console.log('[SignalNotifications] ✓ Modal HTML loaded');
        } catch (error) {
            console.error('[SignalNotifications] Failed to load modal HTML:', error);
        }
    }

    /**
     * Setup global functions (called from modal HTML)
     */
    setupGlobalFunctions() {
        window.closeSignalNotification = () => this.closeNotification();
        window.viewSignalDetails = () => this.viewSignalDetails();
    }

    /**
     * Show notification for a new signal
     */
    showSignalNotification(signal) {
        console.log('[SignalNotifications] Showing notification for:', signal.ticker);

        this.currentSignal = signal;
        const modal = document.getElementById('signal-notification-modal');

        if (!modal) {
            console.error('[SignalNotifications] Modal element not found');
            return;
        }

        // Update modal content
        this.updateModalContent(signal);

        // Show modal
        modal.style.display = 'block';
        this.isModalVisible = true;

        // Start auto-close timer (10 seconds)
        this.startAutoCloseTimer();

        // Play notification sound (optional)
        this.playNotificationSound();

        // Update counters
        this.updateSignalCounters();
    }

    /**
     * Update modal content with signal data
     */
    updateModalContent(signal) {
        // Update timestamp
        const timestampEl = document.getElementById('signal-modal-timestamp');
        if (timestampEl) {
            timestampEl.textContent = this.formatTimestamp(signal.timestamp);
        }

        // Update symbol
        const symbolEl = document.getElementById('signal-modal-symbol');
        if (symbolEl) {
            symbolEl.textContent = signal.ticker || signal.symbol;
        }

        // Update action badge
        const actionBadge = document.getElementById('signal-modal-action-badge');
        if (actionBadge) {
            const action = signal.action || (signal.side === 'LONG' ? 'BUY' : 'SELL');
            actionBadge.textContent = action;

            if (action === 'BUY') {
                actionBadge.style.background = 'linear-gradient(135deg, #10b981, #059669)';
            } else {
                actionBadge.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            }
        }

        // Update price levels
        const entryEl = document.getElementById('signal-modal-entry');
        const tpEl = document.getElementById('signal-modal-tp');
        const slEl = document.getElementById('signal-modal-sl');

        if (entryEl) entryEl.textContent = this.formatPrice(signal.entry_price || signal.entry);
        if (tpEl) tpEl.textContent = this.formatPrice(signal.target_price || signal.tp);
        if (slEl) slEl.textContent = this.formatPrice(signal.stop_loss || signal.sl);

        // Update confidence
        const confidenceEl = document.getElementById('signal-modal-confidence');
        if (confidenceEl) {
            const confidence = signal.confidence || 50;
            confidenceEl.textContent = `${Math.round(confidence)}%`;
        }

        // Update RSI
        const rsiEl = document.getElementById('signal-modal-rsi');
        if (rsiEl) {
            rsiEl.textContent = signal.rsi ? signal.rsi.toFixed(1) : '--';
        }

        // Update reasoning
        const reasoningEl = document.getElementById('signal-modal-reasoning');
        if (reasoningEl) {
            reasoningEl.textContent = signal.reasoning ||
                `${signal.event || 'GOLDEN'} CROSS detected. RSI: ${signal.rsi?.toFixed(1) || '--'}, ATR: ${signal.atr_pct?.toFixed(2) || '--'}%`;
        }
    }

    /**
     * Start auto-close timer
     */
    startAutoCloseTimer() {
        // Clear existing timer
        if (this.autoCloseTimeout) {
            clearTimeout(this.autoCloseTimeout);
        }

        // Reset progress bar
        const progressBar = document.getElementById('signal-modal-progress');
        if (progressBar) {
            progressBar.style.transition = 'none';
            progressBar.style.width = '100%';

            // Trigger animation
            setTimeout(() => {
                progressBar.style.transition = 'width 10s linear';
                progressBar.style.width = '0%';
            }, 50);
        }

        // Auto-close after 10 seconds
        this.autoCloseTimeout = setTimeout(() => {
            this.closeNotification();
        }, 10000);
    }

    /**
     * Close notification
     */
    closeNotification() {
        const modal = document.getElementById('signal-notification-modal');
        if (modal) {
            // Add slide-out animation
            modal.style.animation = 'slideOutRight 0.5s ease-in';

            setTimeout(() => {
                modal.style.display = 'none';
                modal.style.animation = 'slideInRight 0.5s ease-out';
                this.isModalVisible = false;
            }, 500);
        }

        // Clear timeout
        if (this.autoCloseTimeout) {
            clearTimeout(this.autoCloseTimeout);
            this.autoCloseTimeout = null;
        }
    }

    /**
     * View signal details (navigate to bots page)
     */
    viewSignalDetails() {
        this.closeNotification();

        // Navigate to bots page
        if (this.fedEdgeAI && this.fedEdgeAI.switchToPage) {
            this.fedEdgeAI.switchToPage('bots');
        }
    }

    /**
     * Update signal counters in dashboard
     */
    async updateSignalCounters() {
        try {
            // Fetch signals count
            const signalsResponse = await fetch('/api/signals?limit=50');
            const signalsData = await signalsResponse.json();

            const activeSignalsCount = signalsData.signals?.length || 0;

            // Fetch trading stats for open trades
            const statsResponse = await fetch('/api/trading-stats');
            const statsData = await statsResponse.json();

            const openTradesCount = statsData.stats?.open_trades || 0;

            // Update counters
            const activeSignalsEl = document.getElementById('active-signals-count');
            const openTradesEl = document.getElementById('open-trades-count');

            if (activeSignalsEl) {
                activeSignalsEl.textContent = activeSignalsCount;
            }

            if (openTradesEl) {
                openTradesEl.textContent = openTradesCount;
            }

            console.log(`[SignalNotifications] Updated counters: ${activeSignalsCount} signals, ${openTradesCount} open trades`);
        } catch (error) {
            console.error('[SignalNotifications] Error updating counters:', error);
        }
    }

    /**
     * Play notification sound
     */
    playNotificationSound() {
        try {
            // Create a simple beep sound using Web Audio API
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (error) {
            console.warn('[SignalNotifications] Could not play sound:', error);
        }
    }

    /**
     * Format timestamp
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Just now';

        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);

        if (diffSecs < 60) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;

        return date.toLocaleTimeString();
    }

    /**
     * Format price
     */
    formatPrice(price) {
        if (!price) return '--';

        const num = parseFloat(price);
        if (num >= 1) {
            return num.toFixed(2);
        } else if (num >= 0.01) {
            return num.toFixed(4);
        } else {
            return num.toFixed(8);
        }
    }

    /**
     * Handle new signal from WebSocket
     */
    handleNewSignal(signal) {
        console.log('[SignalNotifications] New signal received:', signal);

        // Show notification
        this.showSignalNotification(signal);

        // Update counters
        this.updateSignalCounters();
    }
}
