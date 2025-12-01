/**
 * WebSocket Manager Module
 * Handles WebSocket connection, reconnection, and message routing
 */

import { UIUtils } from './ui-utils.js';

export class WebSocketManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.socket = null;
        this.clientId = 'client_' + Math.random().toString(36).substr(2, 9);
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.customHandlers = []; // Initialize custom handlers array
    }

    /**
     * Setup WebSocket connection
     */
    connect() {
        if (this.isConnecting || (this.socket && this.socket.readyState === WebSocket.OPEN)) {
            console.log('WebSocket already connecting or connected');
            return;
        }

        this.isConnecting = true;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.clientId}`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = async () => {
                console.log('✅ WebSocket connected successfully');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);

                // Get client's public IP before notifying backend
                console.log(`Client ID: ${this.clientId}`);
                let clientPublicIp = null;

                try {
                    console.log('🌐 Fetching client public IP...');
                    const ipResponse = await fetch('https://api.ipify.org?format=json', { timeout: 3000 });
                    if (ipResponse.ok) {
                        const ipData = await ipResponse.json();
                        clientPublicIp = ipData.ip;
                        console.log(`✅ Client public IP: ${clientPublicIp}`);
                    }
                } catch (error) {
                    console.warn('⚠️ Could not fetch client public IP:', error);
                }

                // Notify backend that client is connected with IP
                this.send({
                    type: 'client_connected',
                    client_id: this.clientId,
                    client_public_ip: clientPublicIp
                });
                console.log(`📤 Sent client_connected message to backend (IP: ${clientPublicIp || 'unknown'})`);
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnecting = false;
            };

            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnecting = false;
                this.updateConnectionStatus(false);

                // Attempt to reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.attemptReconnect();
                }
            };

        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.isConnecting = false;
            this.attemptReconnect();
        }
    }

    /**
     * Attempt to reconnect to WebSocket
     */
    attemptReconnect() {
        this.reconnectAttempts++;
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    /**
     * Update connection status in UI
     */
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
            statusElement.style.color = connected ? '#10b981' : '#ef4444';
        }
    }

    /**
     * Send message through WebSocket
     */
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
            return true;
        } else {
            console.warn('WebSocket not connected, cannot send message');
            return false;
        }
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(data) {
        console.log('WebSocket message received:', data.type);

        switch(data.type) {
            case 'chat_response':
                this.fedEdgeAI.chatManager?.handleChatResponse(data);
                break;

            case 'chat_token':
                this.fedEdgeAI.chatManager?.handleChatToken(data);
                break;

            case 'chat_stream_end':
                this.fedEdgeAI.chatManager?.handleChatStreamEnd(data);
                break;

            case 'conversation_cleared':
                this.fedEdgeAI.chatManager?.handleConversationCleared(data);
                break;

            case 'new_signal':
                this.fedEdgeAI.signalsManager?.handleNewSignal(data);
                break;

            case 'stats_update':
                this.fedEdgeAI.dashboardManager?.handleStatsUpdate(data);
                break;

            case 'price_update':
                this.fedEdgeAI.walletManager?.handlePriceUpdate(data);
                break;

            case 'trade_executed':
                this.fedEdgeAI.tradingManager?.handleTradeExecuted(data);
                break;

            case 'wallet_update':
                this.fedEdgeAI.walletManager?.handleWalletUpdate(data);
                break;

            case 'wallet_performance':
                this.fedEdgeAI.walletManager?.handleWalletPerformance(data);
                break;

            case 'trading_decision':
                this.fedEdgeAI.tradingManager?.handleTradingDecision(data);
                break;

            case 'market_alert':
                this.fedEdgeAI.dashboardManager?.handleMarketAlert(data);
                break;

            case 'analysis_error':
                this.handleAnalysisError(data);
                break;

            case 'debug_log':
                this.handleDebugLog(data);
                break;

            case 'debug_session_summary':
                this.handleDebugSessionSummary(data);
                break;

            case 'new_article':
                this.fedEdgeAI.dashboardManager?.handleNewArticle(data);
                break;

            case 'news_update':
                this.fedEdgeAI.dashboardManager?.handleNewsUpdate(data);
                break;

            case 'trades_history':
                this.fedEdgeAI.tradingManager?.handleTradesHistory(data);
                break;

            case 'agent_state_update':
                this.fedEdgeAI.dashboardManager?.handleAgentStateUpdate(data);
                break;

            case 'new_signal':
            case 'trading_signal':
                // Handle new trading signal notification
                console.log('🎯 New trading signal received:', data);
                this.fedEdgeAI.signalNotifications?.handleNewSignal(data.payload || data);
                this.fedEdgeAI.signalsManager?.handleNewSignal(data);
                break;

            default:
                // Try custom handlers first
                if (this.customHandlers && this.customHandlers.length > 0) {
                    console.log(`🔧 Trying ${this.customHandlers.length} custom handlers for message type: ${data.type}`);
                    let handled = false;
                    for (const handler of this.customHandlers) {
                        try {
                            if (handler(data)) {
                                console.log('✅ Message handled by custom handler');
                                handled = true;
                                break;
                            }
                        } catch (error) {
                            console.error('❌ Custom handler error:', error);
                        }
                    }
                    if (handled) break;
                } else {
                    console.log('⚠️ No custom handlers registered for message type:', data.type);
                }

                console.log('Unknown message type:', data.type);
        }
    }

    /**
     * Handle analysis error
     */
    handleAnalysisError(data) {
        const payload = data.payload || {};
        UIUtils.showNotification(payload.error || 'Analysis error occurred', 'error');
    }

    /**
     * Handle debug log
     */
    handleDebugLog(data) {
        const payload = data.payload || {};
        console.log('Debug log:', payload);

        // Add to debug console if available
        const debugConsole = document.getElementById('debug-logs-content');
        if (debugConsole && payload.message) {
            const logEntry = document.createElement('div');
            logEntry.className = 'debug-log-entry';
            logEntry.style.cssText = `
                padding: 8px;
                margin-bottom: 4px;
                border-left: 3px solid #3b82f6;
                background: #f3f4f6;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            `;
            logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${payload.message}`;
            debugConsole.appendChild(logEntry);
            debugConsole.scrollTop = debugConsole.scrollHeight;
        }
    }

    /**
     * Handle debug session summary
     */
    handleDebugSessionSummary(data) {
        const payload = data.payload || {};
        console.log('Debug session summary:', payload);
    }

    /**
     * Close WebSocket connection
     */
    close() {
        if (this.socket) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
            this.socket.close();
            this.socket = null;
        }
    }
}
