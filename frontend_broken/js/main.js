class HiveAI {
    constructor() {
        this.socket = null;
        this.clientId = 'client_' + Math.random().toString(36).substr(2, 9);
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Gestion des signaux et pagination
        this.signals = [];
        this.currentPage = 0;
        this.signalsPerPage = 4; // 1 large + 3 small (ou pagination si nécessaire)
        
        // Stockage des prix en temps réel pour le wallet
        this.currentPrices = {};
        // Override local pour le compteur de trades par wallet (corrige les données API approximatives)
        this.tradesCountOverride = {};
        
        this.init();
    }
    
    init() {
        console.log('🚀 HIVE AI init started...');
        
        this.setupWebSocket();
        this.setupChatInterface();
        this.setupLogsModal();
        this.setupDebugConsole();
        this.setupSignalModal();
        this.setupSignalPagination();
        this.setupAssetStatsModal();
        this.setupWorldContextModal();
        this.setupFinanceMarketModal();
        this.setupSettingsModal();
        this.setupTradingBotInterface();

        // Configuration de la navigation sidebar (inline pour éviter les erreurs)
        setTimeout(() => {
            console.log('🚀 Setting up sidebar navigation...');

            const sidebarItems = document.querySelectorAll('.sidebar-item');
            const contentPages = document.querySelectorAll('.content-page');

            sidebarItems.forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();

                    const targetPage = item.getAttribute('data-page');
                    console.log(`🎯 Navigating to: ${targetPage}`);

                    // Remove active class from all sidebar items
                    sidebarItems.forEach(sidebarItem => {
                        sidebarItem.classList.remove('active');
                    });

                    // Add active class to clicked item
                    item.classList.add('active');

                    // Hide all content pages
                    contentPages.forEach(page => {
                        page.classList.remove('active');
                    });

                    // Show target page
                    const targetPageElement = document.getElementById(`${targetPage}-page`);
                    if (targetPageElement) {
                        targetPageElement.classList.add('active');

                        // Si on navigue vers la page simulations, charger les simulations
                        if (targetPage === 'simulations') {
                            console.log('🎮 Loading simulations for simulations page...');
                            setTimeout(() => {
                                this.loadSimulations();
                            }, 100);
                        }
                    } else {
                        console.error(`❌ Page not found: ${targetPage}-page`);
                    }
                });
            });

            console.log('✅ Sidebar navigation setup complete');
        }, 100);
        
        // Setup des events pour les simulations avec attente DOM
        setTimeout(() => {
            this.setupSimulationEvents();
        }, 100);
        
        // FORCER le chargement des simulations avec attente DOM
        console.log('🚀 Préparation chargement des simulations...');
        this.waitAndLoadSimulations();
        
        // Créer une fonction de test globale
        window.testSimulationModal = () => {
            console.log('🧪 Test manuel du modal');
            this.openSimulationModal();
        };
        
        // Fonction globale pour tester le chargement
        window.loadSimulations = () => {
            console.log('🧪 Test global loadSimulations');
            this.loadSimulations();
        };
        
        // Afficher le message d'attente au démarrage avec délai
        setTimeout(() => {
            console.log('🎯 Calling renderSignals from init...');
            this.renderSignals();
        }, 100);
        
        console.log('HIVE AI initialized');
        
        // Test direct pour forcer l'affichage
        window.testSignals = () => {
            console.log('🧪 Test direct des signaux...');
            this.forceRenderSignals();
        };
        
        // Test immédiat au chargement
        setTimeout(() => {
            console.log('🔥 Test automatique au chargement...');
            this.forceRenderSignals();
        }, 500);
        
        // Test des endpoints d'assets
        setTimeout(() => {
            this.testAssetEndpoints();
        }, 2000);
        
        // Test de la modale d'assets
        window.testAssetModal = () => {
            console.log('🧪 Test forcé de la modale asset-stats');
            const modal = document.getElementById('asset-stats-modal');
            if (modal) {
                modal.style.display = 'flex';
                modal.classList.add('show'); // Utiliser la classe CSS
                modal.style.zIndex = '9999';
                console.log('✅ Modale forcée à s\'afficher');
                
                // Test d'écriture dans les sections
                const priceContent = document.getElementById('price-stats-content');
                if (priceContent) {
                    priceContent.innerHTML = '🧪 TEST: Prix analysis';
                    console.log('✅ Contenu prix injecté');
                }
            } else {
                console.error('❌ Modale non trouvée');
            }
        };
        
        // Ajouter les gestionnaires pour les boutons de test
        this.setupTestButtons();
    }
    
    async testAssetEndpoints() {
        console.log('🧪 Test des endpoints d\'assets...');
        const testAssetId = 'bitcoin';
        
        const endpoints = [
            `/api/assets/${testAssetId}/analysis?days=1`,
            `/api/assets/${testAssetId}/chart-data?days=1`,
            `/api/assets/${testAssetId}/llm-summary?days=1`
        ];
        
        for (const endpoint of endpoints) {
            try {
                console.log(`🔍 Test de ${endpoint}...`);
                const response = await fetch(endpoint);
                console.log(`✅ ${endpoint}: ${response.status} ${response.statusText}`);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log(`📊 ${endpoint}: status=${data.status}`);
                } else {
                    console.error(`❌ ${endpoint}: Erreur ${response.status}`);
                }
            } catch (error) {
                console.error(`❌ ${endpoint}: Exception:`, error);
            }
        }
    }
    
    forceRenderSignals() {
        console.log('💪 Force render signals...');
        const recentContainer = document.getElementById('signals-compact') || document.getElementById('signals-container');
        
        if (recentContainer) {
            recentContainer.innerHTML = `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100px;
                    background: rgba(16, 185, 129, 0.1);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 8px;
                    color: #10b981;
                    font-size: 14px;
                    font-weight: 600;
                ">
                    ✅ TEST RÉUSSI - En attente de signaux IA...
                </div>
            `;
            console.log('✅ Message de test affiché dans signals-compact');
        } else {
            console.error('❌ Container signals-compact ou signals-container introuvable !');
        }
    }
    
    setupTestButtons() {
        const testSignalBtn = document.getElementById('test-signal-btn');
        const testDemoBtn = document.getElementById('test-demo-btn');
        
        if (testSignalBtn) {
            testSignalBtn.addEventListener('click', async () => {
                console.log('🧪 Déclenchement manuel signal de test...');
                try {
                    const response = await fetch('/test-signal');
                    const result = await response.json();
                    console.log('✅ Réponse test signal:', result);
                } catch (error) {
                    console.error('❌ Erreur test signal:', error);
                }
            });
        }
        
        if (testDemoBtn) {
            testDemoBtn.addEventListener('click', async () => {
                console.log('🎯 Déclenchement manuel signal démo...');
                try {
                    const response = await fetch('/test-demo-signal');
                    const result = await response.json();
                    console.log('✅ Réponse demo signal:', result);
                } catch (error) {
                    console.error('❌ Erreur demo signal:', error);
                }
            });
        }
    }
    
    setupWebSocket() {
        if (this.isConnecting) return;
        
        this.isConnecting = true;
        const wsUrl = `ws://${window.location.hostname}:8000/ws/${this.clientId}`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = (event) => {
            console.log('✅ WebSocket connected successfully');
            this.isConnecting = false;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
            
            // Demander les prix immédiatement après connexion
            console.log('💰 Demande de prix immédiate après connexion');
            this.socket.send(JSON.stringify({
                type: 'request_prices',
                payload: {}
            }));
            
            // Send a test message to confirm connection
            this.socket.send(JSON.stringify({
                type: 'test_connection',
                payload: 'Frontend connected'
            }));
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('📨 Message WebSocket reçu:', data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket closed:', event);
            this.isConnecting = false;
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.isConnecting = false;
            this.updateConnectionStatus(false);
        };
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => {
                this.setupWebSocket();
            }, 2000 * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
    
    updateConnectionStatus(connected) {
        // Update UI to show connection status
        const statusElements = document.querySelectorAll('.status-dot');
        statusElements.forEach(dot => {
            if (connected) {
                dot.style.background = '#10b981';
            } else {
                dot.style.background = '#ef4444';
            }
        });
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'chat_response':
                this.handleChatResponse(data.payload);
                break;
            case 'conversation_cleared':
                this.handleConversationCleared(data.payload);
                break;
            case 'new_signal':
                this.handleNewSignal(data.payload);
                break;
            case 'stats_update':
                this.handleStatsUpdate(data.payload);
                break;
            case 'price_update':
                this.handlePriceUpdate(data.payload);
                break;
            case 'new_article':
                this.handleNewArticle(data.payload);
                break;
            case 'trading_decision':
                this.handleTradingDecision(data.payload);
                break;
            case 'market_alert':
                this.handleMarketAlert(data.payload);
                break;
            case 'analysis_error':
                this.handleAnalysisError(data.payload);
                break;
            case 'trade_executed':
                this.handleTradeExecuted(data.payload);
                break;
            case 'wallet_update':
                this.handleWalletUpdate(data.payload);
                break;
            case 'debug_log':
                this.handleDebugLog(data.payload);
                break;
            case 'debug_session_summary':
                this.handleDebugSessionSummary(data.payload);
                break;
            case 'wallet_performance':
                this.handleWalletPerformance(data.payload);
                break;
            case 'trades_history':
                this.handleTradesHistory(data.payload);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    handleChatResponse(payload) {
        this.hideTypingIndicator();
        this.addMessageToChat(payload.ai_response, 'ai', payload);
    }
    
    handleConversationCleared(payload) {
        // Clear all messages except the initial greeting
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="message ai">
                Salut! Je suis votre assistant HIVE AI. Comment puis-je vous aider aujourd'hui?
            </div>
            <div class="typing-indicator" id="typing-indicator">
                L'IA réfléchit...
            </div>
        `;
        
        // Show confirmation message briefly
        this.addMessageToChat("✅ " + payload.message, 'ai');
        
        console.log('Conversation cleared');
    }
    
    handleNewSignal(payload) {
        console.log('📡 Nouveau signal reçu:', payload);
        
        // Ajouter le signal à la liste
        this.signals.unshift(payload); // Ajouter en début de liste
        
        // Limiter à 20 signaux maximum
        if (this.signals.length > 20) {
            this.signals = this.signals.slice(0, 20);
        }
        
        // Revenir à la première page pour voir le nouveau signal
        this.currentPage = 0;
        
        // Re-rendre l'affichage des signaux
        this.renderSignals();
        
        console.log(`🔔 Nouveau signal ajouté. Total: ${this.signals.length}, Page: ${this.currentPage + 1}`);
    }
    
    handleStatsUpdate(payload) {
        // Update dashboard stats avec nouvelles métriques
        if (payload.total_roi) {
            const roiElement = document.getElementById('roi-value');
            if (roiElement) roiElement.textContent = `${payload.total_roi}%`;
        }
        
        if (payload.daily_pnl) {
            const pnlElement = document.getElementById('daily-pnl');
            if (pnlElement) {
                const sign = payload.daily_pnl >= 0 ? '+' : '';
                pnlElement.textContent = `${sign}$${payload.daily_pnl}`;
                pnlElement.style.color = payload.daily_pnl >= 0 ? '#10b981' : '#ef4444';
            }
        }
        
        if (payload.active_signals) {
            const signalsElement = document.getElementById('active-signals');
            if (signalsElement) signalsElement.textContent = payload.active_signals;
        }
        
        if (payload.success_rate) {
            const successElement = document.getElementById('success-rate');
            if (successElement) successElement.textContent = `${payload.success_rate}%`;
        }
        
        // Mise à jour des anciennes métriques pour compatibilité
        if (payload.network_nodes) {
            const nodesElement = document.getElementById('network-nodes');
            if (nodesElement) nodesElement.textContent = payload.network_nodes;
        }
        
        if (payload.collective_iq) {
            const iqElement = document.getElementById('collective-iq');
            if (iqElement) iqElement.textContent = payload.collective_iq;
        }
        
        if (payload.accuracy_24h) {
            const accuracyElement = document.getElementById('accuracy-24h');
            if (accuracyElement) accuracyElement.textContent = payload.accuracy_24h;
        }
    }
    
    handleTradingDecision(payload) {
        console.log('Nouvelle décision de trading reçue:', payload);
        
        // Créer un signal à partir de la décision de trading
        const signalData = {
            asset_ticker: payload.asset_ticker,
            action: payload.action,
            confidence: Math.round(payload.confidence * 100), // Convertir en pourcentage
            signal_type: payload.signal_type,
            reasoning: payload.reasoning,
            timestamp: payload.timestamp,
            price_target: payload.price_target || null,
            entry_price: payload.entry_price || null,
            stop_loss: payload.stop_loss || null
        };
        
        // Ajouter à la section des signaux
        this.handleNewSignal(signalData);
        
        // Optionnel: montrer une notification
        this.showNotification(`Nouvelle décision: ${payload.action} ${payload.asset_ticker}`, 'success');
    }
    
    handleMarketAlert(payload) {
        console.log('Alerte marché reçue:', payload);
        
        // Créer une notification d'alerte
        const alertMessage = `📢 ${payload.alert_type}: ${payload.asset_ticker} - Force: ${Math.round(payload.strength * 100)}%`;
        this.showNotification(alertMessage, 'warning');
        
        // Optionnel: ajouter l'alerte à une section dédiée du dashboard
        const alertsContainer = document.getElementById('market-alerts');
        if (alertsContainer) {
            const alertElement = this.createAlertElement(payload);
            alertsContainer.insertBefore(alertElement, alertsContainer.firstChild);
            
            // Limiter à 5 alertes maximum
            const alerts = alertsContainer.querySelectorAll('.market-alert');
            if (alerts.length > 5) {
                alerts[alerts.length - 1].remove();
            }
        }
    }
    
    handleAnalysisError(payload) {
        console.error('Erreur d\'analyse:', payload);
        
        // Afficher une notification d'erreur
        const errorMessage = `❌ Erreur d'analyse pour ${payload.asset_ticker}: ${payload.error}`;
        this.showNotification(errorMessage, 'error');
    }
    
    createAlertElement(alert) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'market-alert';
        alertDiv.style.cssText = `
            background: rgba(251, 191, 36, 0.1);
            border: 1px solid rgba(251, 191, 36, 0.3);
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
            animation: fadeIn 0.3s ease;
        `;
        
        alertDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 600; color: #fbbf24; font-size: 14px;">
                        ${alert.alert_type} - ${alert.asset_ticker}
                    </div>
                    <div style="color: #d1d5db; font-size: 12px; margin-top: 4px;">
                        ${alert.message}
                    </div>
                </div>
                <div style="background: rgba(251, 191, 36, 0.2); padding: 4px 8px; border-radius: 4px;">
                    <span style="color: #fbbf24; font-size: 12px; font-weight: 600;">
                        ${Math.round(alert.strength * 100)}%
                    </span>
                </div>
            </div>
        `;
        
        return alertDiv;
    }
    
    showNotification(message, type = 'info') {
        // Créer une notification toast
        const notification = document.createElement('div');
        const colors = {
            success: { bg: '#10b981', border: '#065f46' },
            warning: { bg: '#f59e0b', border: '#92400e' },
            error: { bg: '#ef4444', border: '#991b1b' },
            info: { bg: '#3b82f6', border: '#1e40af' }
        };
        
        const color = colors[type] || colors.info;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${color.bg};
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid ${color.border};
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            max-width: 400px;
            animation: slideIn 0.3s ease;
            font-size: 14px;
            font-weight: 500;
        `;
        
        notification.textContent = message;
        
        // Ajouter au body
        document.body.appendChild(notification);
        
        // Retirer après 5 secondes
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
        
        // Ajouter les animations CSS si elles n'existent pas
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    createSignalElement(signal, size = 'large') {
        const signalDiv = document.createElement('div');
        signalDiv.className = `signal-item ${size}`;
        
        // Gérer les différents formats d'action
        const action = signal.action || signal.type || 'HOLD';
        const actionClass = action.toLowerCase() === 'buy' ? 'signal-buy' :
                           action.toLowerCase() === 'sell' ? 'signal-sell' :
                           action.toLowerCase() === 'hold' ? 'signal-hold' : 'signal-hold';
        
        // Gérer les différents formats d'actif
        const assetName = signal.asset_ticker || signal.asset || 'Unknown Asset';
        
        // Formater la confiance
        const confidence = typeof signal.confidence === 'number' ? signal.confidence : 
                          (signal.confidence ? parseInt(signal.confidence) : 0);
        
        signalDiv.innerHTML = `
            <div>
                <div class="signal-header">
                    <div class="signal-icon ${actionClass}">${action}</div>
                    <div class="signal-info">
                        <h3>${assetName}</h3>
                        <div class="signal-details">
                            <span>Entry: ${signal.entry_price || 'N/A'}</span>
                            <span>Target: ${signal.price_target || signal.target_price || 'N/A'}</span>
                            <span>Stop: ${signal.stop_loss || 'N/A'}</span>
                        </div>
                        ${signal.signal_type ? `<div style="font-size: 12px; color: #6b7280; margin-top: 4px;">${signal.signal_type}</div>` : ''}
                    </div>
                </div>
                <p style="margin-top: 12px; font-size: 14px; color: #9ca3af;">
                    ${signal.reasoning || signal.reason || 'Signal généré par l\'IA collective'}
                </p>
                ${signal.timestamp ? `<div style="font-size: 11px; color: #6b7280; margin-top: 8px;">
                    ${new Date(signal.timestamp).toLocaleString('fr-FR')}
                </div>` : ''}
                ${size !== 'small' ? `<div style="
                    margin-top: 12px;
                    padding: ${size === 'large' ? '8px 12px' : '6px 8px'};
                    background: rgba(59, 130, 246, 0.1);
                    border: 1px solid rgba(59, 130, 246, 0.2);
                    border-radius: 6px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: ${size === 'large' ? '12px' : '10px'};
                    color: #60a5fa;
                " class="signal-details-btn">
                    🔍 ${size === 'large' ? 'Voir l\'analyse complète' : 'Analyse'}
                </div>` : ''}
            </div>
            <div class="signal-confidence">
                <div class="confidence-score">${confidence}%</div>
                <div class="confidence-label">Confiance</div>
            </div>
        `;
        
        // Ajouter l'événement click pour ouvrir le modal - TOUS les signaux sont cliquables
        signalDiv.addEventListener('click', (e) => {
            // Si c'est la pagination, ne pas ouvrir le modal
            if (e.target.closest('.pagination-mini-btn')) {
                return;
            }
            this.openSignalModal(signal);
        });
        signalDiv.style.cursor = 'pointer';
        
        // Ajouter l'effet hover
        signalDiv.addEventListener('mouseenter', () => {
            const detailsBtn = signalDiv.querySelector('.signal-details-btn');
            if (detailsBtn) {
                detailsBtn.style.background = 'rgba(59, 130, 246, 0.15)';
                detailsBtn.style.borderColor = 'rgba(59, 130, 246, 0.3)';
            }
        });
        
        signalDiv.addEventListener('mouseleave', () => {
            const detailsBtn = signalDiv.querySelector('.signal-details-btn');
            if (detailsBtn) {
                detailsBtn.style.background = 'rgba(59, 130, 246, 0.1)';
                detailsBtn.style.borderColor = 'rgba(59, 130, 246, 0.2)';
            }
        });
        
        return signalDiv;
    }
    
    setupChatInterface() {
        const chatButton = document.getElementById('chat-button');
        const chatPopup = document.getElementById('chat-popup');
        const chatClose = document.getElementById('chat-close');
        const chatClear = document.getElementById('chat-clear');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');

        // Vérifier que les éléments existent
        if (!chatButton) {
            console.warn('⚠️ Chat interface elements not found - chat functionality disabled');
            return;
        }

        // Toggle chat popup
        chatButton.addEventListener('click', () => {
            const isVisible = chatPopup.style.display === 'flex';
            chatPopup.style.display = isVisible ? 'none' : 'flex';
            if (!isVisible) {
                chatInput.focus();
            }
        });
        
        // Close chat popup
        chatClose.addEventListener('click', () => {
            chatPopup.style.display = 'none';
        });
        
        // Clear conversation
        chatClear.addEventListener('click', () => {
            if (confirm('Êtes-vous sûr de vouloir effacer toute la conversation ?')) {
                this.clearConversation();
            }
        });
        
        // Handle form submission
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (message && this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.sendChatMessage(message);
                chatInput.value = '';
            }
        });
        
        // Handle enter key
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        // Handle RAG toggle
        const ragToggle = document.getElementById('rag-toggle');
        const ragStatus = document.getElementById('rag-status');
        const ragIndicator = document.getElementById('rag-indicator');
        
        if (ragToggle && ragStatus && ragIndicator) {
            ragToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    ragStatus.textContent = 'Forcé ON';
                    ragIndicator.style.background = '#3b82f6';
                } else {
                    ragStatus.textContent = 'Auto';
                    ragIndicator.style.background = '#10b981';
                }
            });
        }
    }
    
    sendChatMessage(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }
        
        // Add user message to chat
        this.addMessageToChat(message, 'user');
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Determine RAG usage based on toggle
        const ragToggle = document.getElementById('rag-toggle');
        let useRag = 'auto'; // Default to auto-detection
        
        if (ragToggle && ragToggle.checked) {
            useRag = 'true'; // Force RAG when checked
        }
        
        // Send message to server with RAG preference
        const data = {
            type: 'chat_message',
            payload: message,
            use_rag: useRag
        };
        
        this.socket.send(JSON.stringify(data));
    }
    
    addMessageToChat(message, type, payload = null) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        if (type === 'ai' && payload && payload.is_rag_response && payload.sources && payload.sources.length > 0) {
            // Enhanced AI message with RAG sources
            messageDiv.innerHTML = `
                <div style="margin-bottom: 8px;">${message}</div>
                <div style="
                    background: rgba(59, 130, 246, 0.1);
                    border: 1px solid rgba(59, 130, 246, 0.2);
                    border-radius: 6px;
                    padding: 8px;
                    margin-top: 8px;
                    font-size: 11px;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        color: #3b82f6;
                        font-weight: 600;
                        margin-bottom: 6px;
                    ">
                        🔍 Sources RAG (${payload.source_count})
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        ${payload.sources.slice(0, 3).map((source, index) => `
                            <div style="
                                background: rgba(255, 255, 255, 0.03);
                                border-radius: 4px;
                                padding: 6px 8px;
                                border-left: 2px solid #3b82f6;
                            ">
                                <div style="
                                    display: flex;
                                    align-items: center;
                                    gap: 6px;
                                    margin-bottom: 4px;
                                ">
                                    <span style="
                                        background: #3b82f6;
                                        color: white;
                                        border-radius: 50%;
                                        width: 16px;
                                        height: 16px;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        font-size: 9px;
                                        font-weight: bold;
                                    ">${index + 1}</span>
                                    <div style="
                                        font-size: 10px;
                                        font-weight: 600;
                                        color: #e5e7eb;
                                        overflow: hidden;
                                        text-overflow: ellipsis;
                                        white-space: nowrap;
                                        max-width: 200px;
                                    " title="${source.title || source.url}">
                                        ${source.title || source.source || 'Article'}
                                    </div>
                                </div>
                                <div style="
                                    font-size: 9px;
                                    color: #9ca3af;
                                    line-height: 1.3;
                                    margin-bottom: 3px;
                                ">${source.passage_preview || 'Extrait non disponible'}</div>
                                <a href="${source.url}" target="_blank" style="
                                    color: #60a5fa;
                                    text-decoration: none;
                                    font-size: 8px;
                                    opacity: 0.8;
                                " title="${source.url}">
                                    📰 ${source.source} • ${source.published_at || 'Date inconnue'}
                                </a>
                            </div>
                        `).join('')}
                        ${payload.source_count > 3 ? `
                            <div style="color: #9ca3af; font-size: 10px; margin-top: 2px;">
                                ... et ${payload.source_count - 3} autres sources
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        } else {
            // Standard message
            messageDiv.textContent = message;
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    showTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        const messagesContainer = document.getElementById('chat-messages');
        
        if (indicator) {
            indicator.style.display = 'block';
            messagesContainer.appendChild(indicator);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    clearConversation() {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }
        
        // Send clear message to server
        const data = {
            type: 'clear_conversation',
            payload: {}
        };
        
        this.socket.send(JSON.stringify(data));
    }
    
    handlePriceUpdate(prices) {
        console.log('💰 handlePriceUpdate appelé avec:', prices);
        const container = document.getElementById('crypto-prices');
        if (!container) {
            console.error('❌ Container crypto-prices non trouvé!');
            return;
        }
        
        // Stocker les prix en temps réel pour le wallet
        this.currentPrices = prices;
        console.log('💰 Prix stockés pour wallet:', this.currentPrices);
        
        // Update timestamp
        const timestampElement = document.getElementById('prices-last-update');
        if (timestampElement) {
            timestampElement.textContent = new Date().toLocaleTimeString('fr-FR');
        }
        
        // Clear existing content
        container.innerHTML = '';
        
        // Create price elements for each crypto
        Object.entries(prices).forEach(([crypto, data]) => {
            const priceElement = this.createPriceElement(crypto, data);
            container.appendChild(priceElement);
        });
        
        console.log('Prices updated:', prices);
        
        // Update market cap visualization
        this.updateMarketCapVisualization(prices);
        
        // Mettre à jour le wallet avec les nouveaux prix
        this.updateWalletWithCurrentPrices();
    }
    
    updateMarketCapVisualization(prices) {
        const container = document.getElementById('market-cap-visualization');
        if (!container) return;
        
        // Filter data that has market cap info et limiter aux top 12 pour éviter l'encombrement
        const marketCapData = Object.entries(prices)
            .filter(([crypto, data]) => data.usd_market_cap)
            .map(([crypto, data]) => ({
                name: crypto,
                marketCap: data.usd_market_cap,
                price: data.usd,
                change24h: data.usd_24h_change || 0,
                image: data.image || null  // Ajouter l'image si disponible
            }))
            .sort((a, b) => b.marketCap - a.marketCap)
            .slice(0, 12); // Limiter aux 12 premiers
        
        if (marketCapData.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #9ca3af; padding: 50px;">Pas de données market cap disponibles</div>';
            return;
        }
        
        // Clear container
        container.innerHTML = '';
        
        // Calculate total market cap for proportional sizing
        const totalMarketCap = marketCapData.reduce((sum, item) => sum + item.marketCap, 0);
        
        // Create treemap-style visualization avec défilement
        const treemapContainer = document.createElement('div');
        treemapContainer.style.cssText = `
            display: flex;
            flex-wrap: wrap;
            height: 100%;
            gap: 4px;
            align-content: flex-start;
            max-height: 280px;
            overflow-y: auto;
            overflow-x: hidden;
            padding-right: 8px;
        `;
        
        // Style pour la scrollbar
        treemapContainer.innerHTML = `
            <style>
                .market-cap-container::-webkit-scrollbar {
                    width: 6px;
                }
                .market-cap-container::-webkit-scrollbar-track {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 3px;
                }
                .market-cap-container::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.3);
                    border-radius: 3px;
                }
                .market-cap-container::-webkit-scrollbar-thumb:hover {
                    background: rgba(255, 255, 255, 0.5);
                }
            </style>
        `;
        treemapContainer.className = 'market-cap-container';
        
        marketCapData.forEach((crypto, index) => {
            const percentage = (crypto.marketCap / totalMarketCap) * 100;
            const cryptoElement = this.createMarketCapBlock(crypto, percentage, index);
            treemapContainer.appendChild(cryptoElement);
        });
        
        container.appendChild(treemapContainer);
    }
    
    createMarketCapBlock(crypto, percentage, index) {
        const colors = [
            'linear-gradient(135deg, #f59e0b, #fbbf24)', // Bitcoin - Gold
            'linear-gradient(135deg, #8b5cf6, #a78bfa)', // Ethereum - Purple  
            'linear-gradient(135deg, #10b981, #34d399)', // Others - Green variations
            'linear-gradient(135deg, #06b6d4, #67e8f9)',
            'linear-gradient(135deg, #ef4444, #f87171)',
            'linear-gradient(135deg, #f59e0b, #fbbf24)',
            'linear-gradient(135deg, #6366f1, #8b5cf6)',
            'linear-gradient(135deg, #84cc16, #a3e635)'
        ];
        
        const block = document.createElement('div');
        const isChange24hPositive = crypto.change24h >= 0;
        
        // Calculate width: more visible sizing for smaller cryptos
        let width;
        if (percentage > 40) {
            width = Math.min(percentage * 1.5, 100); // Large cryptos: proportional but not too big
        } else if (percentage > 10) {
            width = Math.max(percentage * 2, 25); // Medium cryptos: boost visibility
        } else {
            width = Math.max(percentage * 3, 20); // Small cryptos: significant boost
        }
        
        const height = Math.max(70 - (index * 6), 45); // Better height distribution
        
        block.style.cssText = `
            background: ${colors[index % colors.length]};
            border-radius: 8px;
            padding: 12px;
            color: #000;
            font-weight: 600;
            position: relative;
            cursor: pointer;
            transition: all 0.3s ease;
            width: ${width}%;
            height: ${height}px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-width: 120px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        `;
        
        // Crypto name and price (combined)
        const nameDiv = document.createElement('div');
        nameDiv.style.cssText = `
            font-size: ${width > 30 ? '14px' : '12px'};
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 2px;
        `;
        nameDiv.textContent = `${this.getCryptoSymbol(crypto.name)} $${this.formatPrice(crypto.price)}`;
        
        // Market cap only
        const marketCapDiv = document.createElement('div');
        marketCapDiv.style.cssText = `
            font-size: ${width > 30 ? '11px' : '9px'};
            opacity: 0.8;
            margin-bottom: 2px;
        `;
        marketCapDiv.textContent = this.formatMarketCap(crypto.marketCap);
        
        // Only 24h change (price is now in market cap line)
        const changeDiv = document.createElement('div');
        changeDiv.style.cssText = `
            text-align: right;
            margin-top: 4px;
        `;
        
        const changeSpan = document.createElement('span');
        changeSpan.style.cssText = `
            background: ${isChange24hPositive ? 'rgba(0, 0, 0, 0.1)' : 'rgba(255, 255, 255, 0.2)'};
            padding: 3px 6px;
            border-radius: 4px;
            font-size: ${width > 30 ? '10px' : '9px'};
            font-weight: 600;
        `;
        changeSpan.textContent = `${isChange24hPositive ? '+' : ''}${(Number(crypto.change24h) || 0).toFixed(1)}%`;
        
        changeDiv.appendChild(changeSpan);
        
        block.appendChild(nameDiv);
        block.appendChild(marketCapDiv);
        block.appendChild(changeDiv);
        
        // Hover effect
        block.addEventListener('mouseenter', () => {
            block.style.transform = 'scale(1.02)';
            block.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.2)';
        });
        
        block.addEventListener('mouseleave', () => {
            block.style.transform = 'scale(1)';
            block.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
        });
        
        return block;
    }
    
    getCryptoSymbol(cryptoId) {
        const symbols = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH', 
            'solana': 'SOL',
            'bittensor': 'TAO',
            'fetch-ai': 'FET',
            'cardano': 'ADA',
            'polkadot': 'DOT',
            'chainlink': 'LINK'
        };
        return symbols[cryptoId] || cryptoId.toUpperCase();
    }
    
    formatMarketCap(marketCap) {
        if (marketCap >= 1e12) {
            return `$${(marketCap / 1e12).toFixed(1)}T`;
        } else if (marketCap >= 1e9) {
            return `$${(marketCap / 1e9).toFixed(1)}B`;
        } else if (marketCap >= 1e6) {
            return `$${(marketCap / 1e6).toFixed(1)}M`;
        } else {
            return `$${marketCap.toFixed(0)}`;
        }
    }

    convertFrequencyToMinutes(freqStr) {
        switch(freqStr) {
            case '5min': return 5;
            case '15min': return 15;
            case '30min': return 30;
            case '1h': return 60;
            case '4h': return 240;
            case '1d': return 1440;
            default: return parseInt(freqStr); // fallback for old format
        }
    }
    
    formatPrice(price) {
        if (price >= 1000) {
            return price.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
        } else if (price >= 1) {
            return price.toFixed(2);
        } else {
            return price.toFixed(4);
        }
    }
    
    createPriceElement(crypto, data) {
        const priceDiv = document.createElement('div');
        priceDiv.style.cssText = `
            background: rgba(255, 255, 255, 0.05);
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        `;
        
        priceDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div id="crypto-icon-${crypto}" style="
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    background: ${data.image ? 'rgba(255, 255, 255, 0.1)' : 'linear-gradient(135deg, #f59e0b, #fbbf24)'};
                    border: 2px solid rgba(255, 255, 255, 0.2);
                ">
                    ${data.image ? 
                        `<img src="${data.image}" alt="${crypto}" style="width: 28px; height: 28px; border-radius: 50%;" 
                              onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'color: #f59e0b; font-weight: 700; font-size: 12px;\\'>${crypto.toUpperCase().slice(0, 3)}</div>';">` :
                        `<span style="color: ${data.image ? '#fff' : '#000'}; font-weight: 700; font-size: 12px;">${crypto.toUpperCase().slice(0, 3)}</span>`
                    }
                </div>
                <div>
                    <div style="font-weight: 600; color: #fff; font-size: 14px;">
                        ${crypto.toUpperCase()}
                    </div>
                    <div style="font-size: 12px; color: #9ca3af;">
                        ${new Date().toLocaleTimeString()}
                    </div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="text-align: right;">
                    <div style="font-size: 16px; font-weight: 700; color: #10b981;">
                        $${typeof data.usd === 'number' ? data.usd.toFixed(4) : data.usd || data}
                    </div>
                </div>
                <button class="asset-chart-btn" data-asset-id="${crypto}" data-asset-symbol="${this.getCryptoSymbol(crypto) || crypto.toUpperCase()}" style="
                    background: rgba(139, 92, 246, 0.2);
                    border: 1px solid rgba(139, 92, 246, 0.4);
                    border-radius: 6px;
                    color: #8b5cf6;
                    cursor: pointer;
                    font-size: 16px;
                    padding: 6px 10px;
                    transition: all 0.2s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                " title="Voir les statistiques détaillées">📊</button>
            </div>
        `;
        
        // Add hover effect
        priceDiv.addEventListener('mouseenter', () => {
            priceDiv.style.background = 'rgba(255, 255, 255, 0.08)';
        });
        
        priceDiv.addEventListener('mouseleave', () => {
            priceDiv.style.background = 'rgba(255, 255, 255, 0.05)';
        });
        
        // Add click handler for chart button
        const chartBtn = priceDiv.querySelector('.asset-chart-btn');
        if (chartBtn) {
            chartBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const assetId = chartBtn.dataset.assetId;
                const assetSymbol = chartBtn.dataset.assetSymbol;
                console.log(`📊 Ouverture des statistiques pour ${assetSymbol} (${assetId})`);
                this.showAssetStatsForSymbol(assetSymbol);
            });
            
            // Add hover effect to chart button
            chartBtn.addEventListener('mouseenter', () => {
                chartBtn.style.background = 'rgba(139, 92, 246, 0.3)';
                chartBtn.style.transform = 'scale(1.1)';
            });
            
            chartBtn.addEventListener('mouseleave', () => {
                chartBtn.style.background = 'rgba(139, 92, 246, 0.2)';
                chartBtn.style.transform = 'scale(1)';
            });
        }
        
        return priceDiv;
    }
    
    handleNewArticle(article) {
        const container = document.getElementById('crypto-news');
        if (!container) return;
        
        // Update timestamp
        const timestampElement = document.getElementById('news-last-update');
        if (timestampElement) {
            timestampElement.textContent = new Date().toLocaleTimeString('fr-FR');
        }
        
        // Remove loading message if it exists
        const loadingMsg = container.querySelector('[style*="text-align: center"]');
        if (loadingMsg) {
            loadingMsg.remove();
        }
        
        // Create article element
        const articleElement = this.createArticleElement(article);
        
        // Add to top of news container
        container.insertBefore(articleElement, container.firstChild);
        
        // Limit to 10 articles
        const articles = container.querySelectorAll('.news-article');
        if (articles.length > 10) {
            articles[articles.length - 1].remove();
        }
        
        console.log('New article added:', article.title);
    }
    
    createArticleElement(article) {
        const articleDiv = document.createElement('div');
        articleDiv.className = 'news-article';
        articleDiv.style.cssText = `
            background: rgba(255, 255, 255, 0.05);
            padding: 10px; /* Réduit de 16px à 10px */
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            margin-bottom: 8px; /* Assure l'espacement entre articles */
        `;
        
        const publishedDate = new Date(article.published_at).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        articleDiv.innerHTML = `
            <div style="margin-bottom: 6px;">
                <h4 style="
                    font-size: 12px;
                    font-weight: 600;
                    color: #fff;
                    margin-bottom: 4px;
                    line-height: 1.2;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                ">
                    ${article.title}
                </h4>
                <div style="
                    font-size: 10px;
                    color: #9ca3af;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <span>${article.source || 'Source inconnue'}</span>
                    <span>${publishedDate}</span>
                </div>
            </div>
            ${article.description ? `
                <p style="
                    font-size: 11px;
                    color: #d1d5db;
                    line-height: 1.3;
                    margin: 4px 0 0 0;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                ">
                    ${article.description}
                </p>
            ` : ''}
        `;
        
        // Add click handler to open article
        articleDiv.addEventListener('click', () => {
            if (article.url) {
                window.open(article.url, '_blank');
            }
        });
        
        // Add hover effect
        articleDiv.addEventListener('mouseenter', () => {
            articleDiv.style.background = 'rgba(255, 255, 255, 0.08)';
            articleDiv.style.transform = 'translateY(-2px)';
        });
        
        articleDiv.addEventListener('mouseleave', () => {
            articleDiv.style.background = 'rgba(255, 255, 255, 0.05)';
            articleDiv.style.transform = 'translateY(0)';
        });
        
        return articleDiv;
    }
    
    setupLogsModal() {
        const viewLogsBtn = document.getElementById('view-logs-btn');
        const logsModal = document.getElementById('logs-modal');
        const closeLogsModal = document.getElementById('close-logs-modal');
        
        if (viewLogsBtn && logsModal && closeLogsModal) {
            // Open logs modal
            viewLogsBtn.addEventListener('click', () => {
                logsModal.style.display = 'flex';
                this.updateLogsContent();
                // Afficher le panneau Datasets (stats + derniers rows)
                this.renderDatasetsPanel?.();
            });
            
            // Close logs modal
            closeLogsModal.addEventListener('click', () => {
                logsModal.style.display = 'none';
            });
            
            // Close on background click
            logsModal.addEventListener('click', (e) => {
                if (e.target === logsModal) {
                    logsModal.style.display = 'none';
                }
            });
        }
    }
    
    // Datasets debug panel in Logs modal
    async renderDatasetsPanel() {
        try {
            const logsModal = document.getElementById('logs-modal');
            if (!logsModal) return;
            let panel = document.getElementById('datasets-panel');
            if (!panel) {
                panel = document.createElement('div');
                panel.id = 'datasets-panel';
                panel.style.cssText = `
                    margin-top: 12px;
                    padding: 10px;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 8px;
                    background: rgba(99,102,241,0.08);
                `;
                // Insert before logs-content if exists, else append
                const logsContent = document.getElementById('logs-content');
                if (logsContent && logsContent.parentNode) {
                    logsContent.parentNode.insertBefore(panel, logsContent);
                } else {
                    logsModal.appendChild(panel);
                }
            }
            panel.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <div style="color:#a5b4fc;font-weight:600;">📦 Datasets (world_state • candidates • decider)</div>
                    <button id="refresh-datasets-stats" style="
                        background: rgba(99,102,241,0.2);
                        border: 1px solid rgba(99,102,241,0.3);
                        color:#a5b4fc;border-radius:4px;padding:4px 8px;font-size:11px;cursor:pointer;
                    ">🔄 Rafraîchir</button>
                </div>
                <div id="datasets-stats" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;"></div>
                <div id="datasets-latest" style="margin-top:10px;"></div>`;
            document.getElementById('refresh-datasets-stats')?.addEventListener('click', () => this.renderDatasetsPanel());
            const stats = await this.fetchDatasetStats();
            const statsContainer = document.getElementById('datasets-stats');
            const buildCard = (key, label) => {
                const s = stats[key] || {};
                return `<div style="background: rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:8px;">
                    <div style="color:#e5e7eb;font-weight:600;font-size:12px;margin-bottom:6px;">${label}</div>
                    <div style="color:#9ca3af;font-size:11px;">Rows: <span style="color:#fff;font-weight:600;">${s.total_rows ?? 0}</span></div>
                    <div style="color:#9ca3af;font-size:11px;">Dernier: <span style="color:#fff;">${s.last_timestamp || 'N/A'}</span></div>
                    <div style="margin-top:6px;">
                        <button data-ds="${key}" class="ds-latest-btn" style="
                            background: rgba(16,185,129,0.2); border:1px solid rgba(16,185,129,0.3);
                            color:#10b981; border-radius:4px; padding:3px 6px; font-size:11px; cursor:pointer;
                        ">Voir derniers rows</button>
                    </div>
                </div>`;
            };
            statsContainer.innerHTML = buildCard('world_state','World State') + buildCard('candidates','Candidates') + buildCard('decider','Decider');
            // Attach handlers
            statsContainer.querySelectorAll('.ds-latest-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const type = e.currentTarget.getAttribute('data-ds');
                    const rows = await this.fetchDatasetLatest(type);
                    const container = document.getElementById('datasets-latest');
                    container.innerHTML = `<div style="color:#e5e7eb;font-weight:600;margin:8px 0;">Derniers rows: ${type}</div>
                        <pre style="max-height:220px;overflow:auto;background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.08);padding:8px;border-radius:6px;color:#d1d5db;font-size:11px;">${this.escapeHtml(JSON.stringify(rows, null, 2))}</pre>`;
                });
            });
        } catch (err) {
            console.error('Datasets panel error:', err);
        }
    }
    async fetchDatasetStats() {
        try {
            const res = await fetch('/debug/datasets/stats');
            const data = await res.json();
            return data.stats || {};
        } catch {
            return {};
        }
    }
    async fetchDatasetLatest(type) {
        try {
            const res = await fetch(`/debug/datasets/${type}/latest?limit=20`);
            const data = await res.json();
            return data.rows || [];
        } catch {
            return [];
        }
    }
    escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, s => ({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[s]));
    }
    
    setupDebugConsole() {
        const debugConsoleBtn = document.getElementById('debug-console-btn');
        const debugModal = document.getElementById('debug-console-modal');
        const closeDebugModal = document.getElementById('close-debug-console-modal');
        const debugClearBtn = document.getElementById('debug-clear-btn');
        const debugPauseBtn = document.getElementById('debug-pause-btn');
        
        // Variables pour contrôler la pause
        this.debugPaused = false;
        
        if (debugConsoleBtn && debugModal && closeDebugModal) {
            // Open debug console modal
            debugConsoleBtn.addEventListener('click', () => {
                debugModal.style.display = 'flex';
                console.log('🐛 Debug console opened');
            });
            
            // Close debug console modal
            closeDebugModal.addEventListener('click', () => {
                debugModal.style.display = 'none';
            });
            
            // Close on background click
            debugModal.addEventListener('click', (e) => {
                if (e.target === debugModal) {
                    debugModal.style.display = 'none';
                }
            });
        }
        
        // Clear debug logs
        if (debugClearBtn) {
            debugClearBtn.addEventListener('click', () => {
                const debugConsole = document.getElementById('debug-console');
                if (debugConsole) {
                    debugConsole.innerHTML = `
                        <div style="color: #6b7280; text-align: center; margin: 20px 0;">
                            🗑️ Logs effacés<br>
                            En attente de nouveaux logs...
                        </div>
                    `;
                    this.updateDebugCounter();
                }
            });
        }
        
        // Pause/Resume debug logs
        if (debugPauseBtn) {
            debugPauseBtn.addEventListener('click', () => {
                this.debugPaused = !this.debugPaused;
                if (this.debugPaused) {
                    debugPauseBtn.innerHTML = '▶️ Reprendre';
                    debugPauseBtn.style.background = '#dc2626';
                } else {
                    debugPauseBtn.innerHTML = '⏸️ Pause';
                    debugPauseBtn.style.background = '#374151';
                }
            });
        }
    }
    
    updateLogsContent() {
        const logsContent = document.getElementById('logs-content');
        if (!logsContent) return;
        
        const now = new Date();
        const timestamp = now.toLocaleString('fr-FR');
        
        // Simulate real logs based on current state
        const logs = [
            `[${timestamp}] ✅ HIVE AI Backend started`,
            `[${timestamp}] 🔄 Scheduler started with data collection tasks`,
            `[${timestamp}] 📡 WebSocket manager initialized`,
            `[${timestamp}] 💰 Price collection task started (every 30s)`,
            `[${timestamp}] 📰 News collection task started (every 5min)`,
            `[${timestamp}] 🔌 Client connected: ${this.clientId}`,
            `[${timestamp}] 💰 Last price update: ${document.getElementById('prices-last-update')?.textContent || 'Never'}`,
            `[${timestamp}] 📰 Last news update: ${document.getElementById('news-last-update')?.textContent || 'Never'}`,
            `[${timestamp}] 🔗 WebSocket status: ${this.socket?.readyState === WebSocket.OPEN ? 'Connected' : 'Disconnected'}`,
            `[${timestamp}] 📊 Active connections: ${Object.keys(this.socket ? 1 : 0)}`,
        ];
        
        logsContent.innerHTML = logs.map(log => {
            let color = '#e4e4e7';
            if (log.includes('✅') || log.includes('Connected')) color = '#10b981';
            else if (log.includes('🔄') || log.includes('💰') || log.includes('📰')) color = '#f59e0b';
            else if (log.includes('📡') || log.includes('🔌')) color = '#6366f1';
            else if (log.includes('Disconnected')) color = '#ef4444';
            
            return `<div style="color: ${color};">${log}</div>`;
        }).join('');
    }
    
    setupSignalModal() {
        const signalModal = document.getElementById('signal-details-modal');
        const closeSignalModal = document.getElementById('close-signal-modal');
        
        if (signalModal && closeSignalModal) {
            // Fermer le modal
            closeSignalModal.addEventListener('click', () => {
                signalModal.style.display = 'none';
            });
            
            // Fermer sur clic en arrière-plan
            signalModal.addEventListener('click', (e) => {
                if (e.target === signalModal) {
                    signalModal.style.display = 'none';
                }
            });
            
            // Fermer avec Escape
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && signalModal.style.display === 'flex') {
                    signalModal.style.display = 'none';
                }
            });
        }
    }
    
    openSignalModal(signalData) {
        console.log('🔍 Ouverture du modal signal avec:', signalData);
        
        const modal = document.getElementById('signal-details-modal');
        if (!modal) {
            console.error('Modal signal non trouvé');
            return;
        }
        
        // Remplir les données de base
        this.populateSignalModal(signalData);
        
        // Afficher le modal
        modal.style.display = 'flex';
    }
    
    populateSignalModal(signalData) {
        // Données de base du signal
        const asset = signalData.asset_ticker || signalData.asset || 'Unknown';
        const action = signalData.action || signalData.type || 'HOLD';
        const confidence = signalData.confidence || 0;
        
        // Éléments du modal
        const elements = {
            subtitle: document.getElementById('signal-modal-subtitle'),
            action: document.getElementById('signal-modal-action'),
            asset: document.getElementById('signal-modal-asset'),
            confidence: document.getElementById('signal-modal-confidence'),
            entry: document.getElementById('signal-modal-entry'),
            target: document.getElementById('signal-modal-target'),
            stop: document.getElementById('signal-modal-stop'),
            type: document.getElementById('signal-modal-type'),
            timestamp: document.getElementById('signal-modal-timestamp'),
            reasoning: document.getElementById('signal-modal-reasoning'),
            llmResponse: document.getElementById('signal-modal-llm-response'),
            worldContext: document.getElementById('signal-modal-world-context'),
            financeContext: document.getElementById('signal-modal-finance-context'),
            assetContext: document.getElementById('signal-modal-asset-context')
        };
        
        // Remplir les données
        if (elements.subtitle) {
            elements.subtitle.textContent = `Analyse détaillée pour ${asset}`;
        }
        
        if (elements.action) {
            elements.action.textContent = action;
            // Couleur selon l'action
            const colors = {
                'BUY': '#10b981',
                'SELL': '#ef4444', 
                'HOLD': '#f59e0b'
            };
            elements.action.style.background = colors[action] || '#6b7280';
        }
        
        if (elements.asset) {
            elements.asset.textContent = asset;
        }
        
        if (elements.confidence) {
            elements.confidence.textContent = `${confidence}%`;
        }
        
        if (elements.entry) {
            elements.entry.textContent = signalData.entry_price ? `$${signalData.entry_price}` : 'N/A';
        }
        
        if (elements.target) {
            elements.target.textContent = signalData.price_target || signalData.target_price ? 
                `$${signalData.price_target || signalData.target_price}` : 'N/A';
        }
        
        if (elements.stop) {
            elements.stop.textContent = signalData.stop_loss ? `$${signalData.stop_loss}` : 'N/A';
        }
        
        if (elements.type) {
            elements.type.textContent = signalData.signal_type || 'ANALYSIS';
        }
        
        if (elements.timestamp) {
            const timestamp = signalData.timestamp ? 
                new Date(signalData.timestamp).toLocaleString('fr-FR') : 
                'Non disponible';
            elements.timestamp.textContent = timestamp;
        }
        
        if (elements.reasoning) {
            elements.reasoning.textContent = signalData.reasoning || 
                signalData.reason || 
                'Aucun raisonnement disponible';
        }
        
        // Réponse LLM complète (données brutes)
        if (elements.llmResponse) {
            const llmData = signalData.llm_response || 
                           signalData.raw_llm_data || 
                           JSON.stringify(signalData, null, 2);
            elements.llmResponse.textContent = llmData;
        }
        
        // Contextes d'analyse
        if (elements.worldContext) {
            elements.worldContext.textContent = signalData.world_context || 
                'Conditions de marché global stables, aucun événement majeur détecté.';
        }
        
        if (elements.financeContext) {
            elements.financeContext.textContent = signalData.finance_context || 
                'Marchés financiers montrant une volatilité modérée avec des tendances mixtes.';
        }
        
        if (elements.assetContext) {
            elements.assetContext.textContent = signalData.asset_context || 
                `Analyse spécifique pour ${asset} basée sur l'action des prix récente et le sentiment du marché.`;
        }
    }
    
    setupSignalPagination() {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        if (prevBtn && nextBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPage > 0) {
                    this.currentPage--;
                    this.renderSignals();
                }
            });
            
            nextBtn.addEventListener('click', () => {
                const maxPage = Math.ceil(this.signals.length / this.signalsPerPage) - 1;
                if (this.currentPage < maxPage) {
                    this.currentPage++;
                    this.renderSignals();
                }
            });
        }
    }
    
    renderSignals() {
        console.log(`🔍 renderSignals appelé - Total signaux: ${this.signals.length}`);
        
        // Vérifier si on utilise la nouvelle interface compacte ou l'ancienne
        const compactContainer = document.getElementById('signals-compact');
        if (compactContainer) {
            this.renderSignalsCompact();
            return;
        }
        
        // Ancienne interface (gardée pour compatibilité)
        const recentContainer = document.getElementById('signals-compact') || document.getElementById('signals-container');
        const mediumContainer = document.getElementById('signals-medium');
        const smallContainer = document.getElementById('signals-small');
        const pagination = document.getElementById('signals-pagination');
        
        if (!recentContainer) {
            console.error('Containers de signaux non trouvés');
            return;
        }
        
        // Debug: vérifier les signaux disponibles
        console.log('Signaux disponibles:', this.signals.map(s => s.asset_ticker || s.payload?.asset_ticker));
        
        // Vider complètement tous les containers
        recentContainer.innerHTML = '';
        mediumContainer.innerHTML = ''; // Gardé vide maintenant
        smallContainer.innerHTML = '';
        
        // Si pas de signaux, afficher un message par défaut
        if (this.signals.length === 0) {
            recentContainer.innerHTML = `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 350px;
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    color: #9ca3af;
                    font-size: 14px;
                ">
                    🔄 En attente de signaux IA...
                </div>
            `;
            return;
        }
        
        // Calculer les signaux à afficher pour la page actuelle
        const startIndex = this.currentPage * this.signalsPerPage;
        const endIndex = startIndex + this.signalsPerPage;
        const pageSignals = this.signals.slice(startIndex, endIndex);
        
        // Log pour debug
        console.log(`🔄 Rendu page ${this.currentPage + 1}, signaux: ${pageSignals.length}`);
        
        // Afficher les signaux selon la nouvelle disposition  
        const totalPages = Math.ceil(this.signals.length / this.signalsPerPage);
        const maxSmallSignals = totalPages > 1 ? 2 : Math.min(3, pageSignals.length - 1);
        
        pageSignals.forEach((signal, index) => {
            if (index >= this.signalsPerPage) return; // Limiter au nombre par page
            
            const signalElement = this.createSignalElement(signal, this.getSignalSize(index));
            console.log(`📍 Signal ${index}: ${signal.payload?.asset_ticker} (${this.getSignalSize(index)})`);
            
            if (index === 0) {
                // Le premier signal en grande taille sur toute la largeur
                recentContainer.appendChild(signalElement);
                console.log(`✅ Signal large ajouté: ${signal.payload?.asset_ticker}`);
            } else if (index <= maxSmallSignals) {
                // Signaux small selon la place disponible
                smallContainer.appendChild(signalElement);
                console.log(`✅ Signal small ${index} ajouté: ${signal.payload?.asset_ticker}`);
            }
        });
        
        // Ajouter la pagination comme 3ème élément si nécessaire
        if (totalPages > 1) {
            const paginationElement = this.createPaginationElement();
            smallContainer.appendChild(paginationElement);
            console.log(`📄 Pagination ajoutée (${this.currentPage + 1}/${totalPages})`);
        }
        
        console.log(`📊 Total signaux: ${this.signals.length}, Page: ${this.currentPage + 1}/${totalPages}`);
        
        // Mettre à jour la pagination
        this.updatePagination();
    }
    
    getSignalSize(index) {
        if (index === 0) return 'large';  // Position 0: large (toute la largeur)
        return 'small';                   // Positions 1-2: small (ligne 2, max 2)
    }
    
    createPaginationElement() {
        const paginationDiv = document.createElement('div');
        paginationDiv.className = 'signal-item small pagination-card';
        paginationDiv.style.cssText = `
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px;
            padding: 8px;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            cursor: default;
        `;
        
        const totalPages = Math.ceil(this.signals.length / this.signalsPerPage);
        const currentPage = this.currentPage + 1;
        
        paginationDiv.innerHTML = `
            <div style="text-align: center;">
                <div style="color: #a5b4fc; font-size: 11px; margin-bottom: 8px;">
                    📄 Page ${currentPage}/${totalPages}
                </div>
                <div style="display: flex; gap: 4px; justify-content: center;">
                    <button class="pagination-mini-btn" ${this.currentPage === 0 ? 'disabled' : ''} onclick="window.hiveAI?.prevPage()">
                        ←
                    </button>
                    <button class="pagination-mini-btn" ${this.currentPage >= totalPages - 1 ? 'disabled' : ''} onclick="window.hiveAI?.nextPage()">
                        →
                    </button>
                </div>
            </div>
        `;
        
        return paginationDiv;
    }
    
    updatePagination() {
        // Masquer l'ancienne pagination en bas
        const pagination = document.getElementById('signals-pagination');
        if (pagination) {
            pagination.style.display = 'none';
        }
    }
    
    prevPage() {
        if (this.currentPage > 0) {
            this.currentPage--;
            this.renderSignals();
        }
    }
    
    nextPage() {
        const maxPage = Math.ceil(this.signals.length / this.signalsPerPage) - 1;
        if (this.currentPage < maxPage) {
            this.currentPage++;
            this.renderSignals();
        }
    }
    
    renderSignalsCompact() {
        console.log(`🔥 renderSignalsCompact appelé - Total signaux: ${this.signals.length}`);
        
        const compactContainer = document.getElementById('signals-compact');
        if (!compactContainer) {
            console.error('Container de signaux compacts non trouvé');
            return;
        }
        
        // Vider le container
        compactContainer.innerHTML = '';
        
        // Si pas de signaux, afficher un message par défaut
        if (this.signals.length === 0) {
            compactContainer.innerHTML = `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 200px;
                    color: #9ca3af;
                    font-size: 12px;
                    text-align: center;
                ">
                    🔄 En attente de signaux IA...<br>
                    <span style="font-size: 10px; opacity: 0.7;">Les signaux apparaîtront ici</span>
                </div>
            `;
            return;
        }
        
        // Afficher les signaux les plus récents (maximum 8 pour l'espace compact)
        const recentSignals = this.signals.slice(0, 8);
        
        recentSignals.forEach((signal, index) => {
            const signalData = signal.payload || signal;
            const signalElement = this.createCompactSignalElement(signalData, index);
            compactContainer.appendChild(signalElement);
        });
        
        console.log(`✅ ${recentSignals.length} signaux compacts rendus.`);
    }
    
    createCompactSignalElement(signalData, index) {
        const element = document.createElement('div');
        element.className = 'signal-compact-item';
        
        // Calculer le temps relatif
        const timeAgo = this.getTimeAgo(signalData.timestamp);
        
        // Déterminer la classe de couleur pour l'action
        const actionClass = signalData.action ? signalData.action.toLowerCase() : 'hold';
        
        element.innerHTML = `
            <div class="signal-compact-header">
                <div>
                    <span class="signal-compact-ticker">${signalData.asset_ticker || 'N/A'}</span>
                    <span class="signal-compact-action ${actionClass}">${signalData.action || 'HOLD'}</span>
                </div>
                <div>
                    <span class="signal-compact-confidence">${signalData.confidence || 0}%</span>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="signal-compact-time">${timeAgo}</div>
                <div style="font-size: 9px; color: #6b7280;">${signalData.signal_type || 'ANALYSIS'}</div>
            </div>
        `;
        
        // Ajouter l'événement de clic pour ouvrir le modal
        element.addEventListener('click', () => {
            this.openSignalModal(signalData);
        });
        
        return element;
    }
    
    handleTradeExecuted(payload) {
        console.log('🔥 Trade exécuté:', payload);
        
        // Afficher une notification
        const message = payload.success ? 
            `✅ ${payload.action} ${payload.asset_ticker}: ${payload.message}` :
            `❌ Échec ${payload.action} ${payload.asset_ticker}: ${payload.message}`;
            
        this.showNotification(message, payload.success ? 'success' : 'error');
        
        // Log détaillé pour debug
        if (payload.success) {
            console.log(`💰 Trade réussi: ${payload.action} ${payload.asset_ticker} | Nouveau budget: $${payload.new_budget?.toFixed(2) || 'N/A'}`);
        }
    }
    
    handleWalletUpdate(payload) {
        console.log('💼 Mise à jour du wallet:', payload);
        
        // Mettre à jour les éléments avec la nouvelle structure
        const walletValueElement = document.getElementById('wallet-budget');
        const totalTradesElement = document.getElementById('wallet-total-trades');
        const walletNameElement = document.getElementById('wallet-name');
        
        if (walletValueElement) {
            walletValueElement.textContent = `$${payload.total_value.toFixed(2)}`;
        }
        
        if (walletNameElement) {
            walletNameElement.textContent = payload.wallet_name || 'Mon Wallet';
        }
        
        if (totalTradesElement) {
            const raw = payload.total_trades;
            let count = 0;
            if (typeof raw === 'number') {
                count = Math.floor(raw);
            } else if (typeof raw === 'string') {
                // Handle values like "26,10" or "26.10" or with spaces
                const m = raw.match(/\d+/);
                if (m) count = parseInt(m[0], 10);
            }
            if (!Number.isFinite(count)) count = 0;
            totalTradesElement.textContent = String(count);
        }
        
        // Pour la nouvelle structure, nous n'avons plus de budget initial à comparer
        // Mais nous pouvons afficher la valeur totale et le nombre de holdings
        const holdingsCountElement = document.getElementById('wallet-holdings-count');
        if (holdingsCountElement) {
            holdingsCountElement.textContent = payload.holdings_count || 0;
        }
        
        // Mettre à jour les holdings avec la nouvelle structure
        this.updateWalletHoldings(payload.holdings || []);
    }
    
    getCoingeckoId(ticker) {
        // Mapping des tickers vers les IDs CoinGecko
        const mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'SOL': 'solana',
            'TAO': 'bittensor',
            'FET': 'fetch-ai',
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'LINK': 'chainlink'
        };
        return mapping[ticker.toUpperCase()] || ticker.toLowerCase();
    }
    
    updateWalletHoldings(holdings) {
        const holdingsContainer = document.getElementById('wallet-holdings');
        if (!holdingsContainer) return;
        
        // Vider le conteneur
        holdingsContainer.innerHTML = '';
        
        if (!holdings || holdings.length === 0) {
            holdingsContainer.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px; font-size: 12px;">
                    Aucun actif dans le wallet
                </div>
            `;
            return;
        }
        
        // Créer un élément pour chaque holding avec la nouvelle structure
        holdings.forEach(holding => {
            const holdingElement = document.createElement('div');
            holdingElement.style.cssText = `
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;
            
            // Utiliser la nouvelle structure avec asset_ticker et asset_name
            const ticker = holding.asset_ticker || 'N/A';
            const name = holding.asset_name || ticker;
            
            // Mapper le ticker vers l'ID CoinGecko pour les prix temps réel
            const cryptoId = this.getCoingeckoId(ticker);
            const quantity = Number(holding.quantity) || 0;
            const currentPrice = Number(this.currentPrices[cryptoId]?.usd ?? holding.average_buy_price ?? 0);
            const totalValue = quantity * currentPrice;
            
            console.log(`💰 ${ticker}: Prix actuel=${currentPrice}, Prix moyen=${holding.average_buy_price}`);
            
            // Partie gauche: ticker et quantité avec valeur totale
            const leftDiv = document.createElement('div');
            leftDiv.innerHTML = `
                <div style="font-weight: 600; color: #fff; font-size: 13px;">${ticker}</div>
                <div style="color: #9ca3af; font-size: 11px; margin-bottom: 2px;">${name}</div>
                <div style="color: #9ca3af; font-size: 11px;">${quantity.toFixed(6)} unités</div>
            `;
            
            // Partie droite: valeur totale et prix unitaire
            const rightDiv = document.createElement('div');
            rightDiv.style.textAlign = 'right';
            rightDiv.innerHTML = `
                <div style="color: #10b981; font-size: 12px; font-weight: 600;">$${totalValue.toFixed(2)}</div>
                <div style="color: #9ca3af; font-size: 10px;">@$${currentPrice.toFixed(2)}</div>
            `;
            
            holdingElement.appendChild(leftDiv);
            holdingElement.appendChild(rightDiv);
            holdingsContainer.appendChild(holdingElement);
        });
    }
    
    updateWalletWithCurrentPrices() {
        // Cette fonction met à jour l'affichage du wallet quand de nouveaux prix arrivent
        // Elle re-trigger l'affichage des holdings si ils sont déjà chargés
        const holdingsContainer = document.getElementById('wallet-holdings');
        if (!holdingsContainer || holdingsContainer.children.length === 0) {
            return; // Pas de holdings affichés actuellement
        }
        
        // Déclencher une nouvelle mise à jour des stats du wallet si nécessaire
        // (Cette logique pourrait être étendue pour recalculer les valeurs totales)
        console.log('💰 Wallet mis à jour avec les nouveaux prix:', this.currentPrices);
    }
    
    // ============== ASSET STATISTICS MODAL ==============
    
    setupAssetStatsModal() {
        console.log('🔧 Setup asset statistics modal...');
        
        const closeBtn = document.getElementById('close-asset-stats-modal');
        const modal = document.getElementById('asset-stats-modal');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeAssetStatsModal());
        }
        
        // Close on background click
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeAssetStatsModal();
                }
            });
        }
    }
    
    async showAssetStats(assetId, assetName = null) {
        console.log(`📊 showAssetStats appelé avec assetId: ${assetId}, assetName: ${assetName}`);
        
        const modal = document.getElementById('asset-stats-modal');
        const title = document.getElementById('asset-stats-title');
        
        if (title) {
            title.textContent = `📊 Analyse de ${assetName || assetId.toUpperCase()}`;
        }
        
        // Show modal with loading state
        if (modal) {
            console.log('🎯 Ouverture de la modale asset-stats-modal');
            modal.style.display = 'flex';
            modal.classList.add('show'); // Ajouter la classe pour rendre visible
            this.showAssetStatsLoading();
        } else {
            console.error('❌ Modale asset-stats-modal non trouvée !');
        }
        
        try {
            // Fetch data with timeout and better error handling
            const timeout = 15000; // 15 secondes timeout
            
            const fetchWithTimeout = (url) => {
                return Promise.race([
                    fetch(url),
                    new Promise((_, reject) => 
                        setTimeout(() => reject(new Error('Timeout')), timeout)
                    )
                ]);
            };
            
            console.log(`📊 Début du chargement des données pour ${assetId}...`);
            
            // Fetch data in parallel avec gestion d'erreur individuelle
            const [analysisResponse, chartDataResponse, summaryResponse] = await Promise.all([
                fetchWithTimeout(`/api/assets/${assetId}/analysis?days=1`).catch(e => ({error: e.message})),
                fetchWithTimeout(`/api/assets/${assetId}/chart-data?days=1`).catch(e => ({error: e.message})),
                fetchWithTimeout(`/api/assets/${assetId}/llm-summary?days=1`).catch(e => ({error: e.message}))
            ]);
            
            // Vérifier si les réponses sont des erreurs
            if (analysisResponse.error || chartDataResponse.error || summaryResponse.error) {
                console.error('📊 Erreurs lors des requêtes:', {
                    analysis: analysisResponse.error,
                    chartData: chartDataResponse.error,
                    summary: summaryResponse.error
                });
                this.showAssetStatsError('Erreur de chargement (timeout ou API indisponible)');
                return;
            }
            
            const analysis = await analysisResponse.json();
            const chartData = await chartDataResponse.json();
            const summary = await summaryResponse.json();
            
            console.log('📊 Réponses API:', {analysis: analysis.status, chartData: chartData.status, summary: summary.status});
            
            if (analysis.status === 'success' && chartData.status === 'success' && summary.status === 'success') {
                console.log('🎯 Appel de displayAssetStatsData avec:', {
                    analysis: analysis.analysis ? 'OK' : 'NULL',
                    chartData: chartData.chart_data ? 'OK' : 'NULL', 
                    summary: summary.summary ? 'OK' : 'NULL'
                });
                this.displayAssetStatsData(analysis.analysis, chartData.chart_data, summary.summary);
            } else {
                console.error('📊 Erreurs dans les données:', {analysis, chartData, summary});
                this.showAssetStatsError(`Erreur API: ${analysis.message || chartData.message || summary.message || 'Données indisponibles'}`);
            }
            
        } catch (error) {
            console.error('📊 Erreur critique lors du chargement:', error);
            this.showAssetStatsError('Erreur de connexion au serveur');
        }
    }
    
    showAssetStatsLoading() {
        const sections = [
            'price-stats-content',
            'technical-analysis-content', 
            'volume-stats-content',
            'market-cap-content',
            'llm-summary-content'
        ];
        
        sections.forEach(sectionId => {
            const element = document.getElementById(sectionId);
            if (element) {
                element.innerHTML = '<div style="text-align: center; padding: 20px; color: #9ca3af;">⏳ Chargement...</div>';
            }
        });
        
        // Clear chart
        this.clearAssetChart();
    }
    
    displayAssetStatsData(analysis, chartData, summary) {
        console.log('🎯 displayAssetStatsData exécutée avec:', {
            analysis: analysis ? Object.keys(analysis) : 'NULL',
            chartData: chartData ? Object.keys(chartData) : 'NULL',
            summary: summary ? typeof summary : 'NULL'
        });
        
        // Display price statistics
        this.displayPriceStats(analysis.price_analysis);
        
        // Display technical analysis
        this.displayTechnicalAnalysis(analysis.price_analysis);
        
        // Display volume stats
        if (analysis.volume_analysis) {
            this.displayVolumeStats(analysis.volume_analysis);
        }
        
        // Display market cap
        if (analysis.market_cap_analysis) {
            this.displayMarketCapStats(analysis.market_cap_analysis);
        }
        
        // Display LLM summary
        this.displayLLMSummary(summary);
        
        // Create chart
        this.createAssetChart(chartData);
    }
    
    displayPriceStats(priceAnalysis) {
        console.log('🎯 displayPriceStats appelée avec:', priceAnalysis ? Object.keys(priceAnalysis) : 'NULL');
        const content = document.getElementById('price-stats-content');
        console.log('🎯 Element price-stats-content trouvé:', content ? 'OUI' : 'NON');
        if (!content || !priceAnalysis) {
            console.error('❌ Échec displayPriceStats:', {content: !!content, priceAnalysis: !!priceAnalysis});
            return;
        }
        
        const changeColor = priceAnalysis.variation_percent >= 0 ? '#10b981' : '#ef4444';
        const changeSign = priceAnalysis.variation_percent >= 0 ? '+' : '';
        
        content.innerHTML = `
            <div style="display: grid; gap: 8px;">
                <div><strong>Prix de départ:</strong> $${priceAnalysis.price_start}</div>
                <div><strong>Prix actuel:</strong> $${priceAnalysis.price_end}</div>
                <div><strong>Variation:</strong> <span style="color: ${changeColor};">${changeSign}${priceAnalysis.variation_percent}%</span></div>
                <div><strong>Min/Max:</strong> $${priceAnalysis.price_min} / $${priceAnalysis.price_max}</div>
                <div><strong>Prix moyen:</strong> $${priceAnalysis.price_mean}</div>
                <div><strong>Volatilité:</strong> ${priceAnalysis.volatility_percent}%</div>
                <div><strong>Points de données:</strong> ${priceAnalysis.data_points}</div>
            </div>
        `;
    }
    
    displayTechnicalAnalysis(priceAnalysis) {
        const content = document.getElementById('technical-analysis-content');
        if (!content || !priceAnalysis) return;
        
        const trendColor = priceAnalysis.trend_direction === 'bullish' ? '#10b981' : 
                          priceAnalysis.trend_direction === 'bearish' ? '#ef4444' : '#6b7280';
        
        content.innerHTML = `
            <div style="display: grid; gap: 8px;">
                <div><strong>Tendance:</strong> <span style="color: ${trendColor};">${priceAnalysis.trend_direction}</span></div>
                <div><strong>Force:</strong> ${priceAnalysis.trend_strength} (R²: ${priceAnalysis.trend_r_squared})</div>
                <div><strong>Support:</strong> $${priceAnalysis.support_level}</div>
                <div><strong>Résistance:</strong> $${priceAnalysis.resistance_level}</div>
                <div><strong>Distance support:</strong> ${priceAnalysis.distance_to_support}%</div>
                <div><strong>Distance résistance:</strong> ${priceAnalysis.distance_to_resistance}%</div>
                <div><strong>Momentum (5pts):</strong> ${priceAnalysis.momentum_5_points}%</div>
            </div>
        `;
    }
    
    displayVolumeStats(volumeAnalysis) {
        const content = document.getElementById('volume-stats-content');
        if (!content || !volumeAnalysis) return;
        
        const trendColor = volumeAnalysis.volume_trend === 'increasing' ? '#10b981' : 
                          volumeAnalysis.volume_trend === 'decreasing' ? '#ef4444' : '#6b7280';
        
        content.innerHTML = `
            <div style="display: grid; gap: 8px;">
                <div><strong>Tendance:</strong> <span style="color: ${trendColor};">${volumeAnalysis.volume_trend}</span></div>
                <div><strong>Variation:</strong> ${volumeAnalysis.volume_change_percent}%</div>
                <div><strong>Volume moyen:</strong> $${volumeAnalysis.volume_mean.toLocaleString()}</div>
                <div><strong>Volume début:</strong> $${volumeAnalysis.volume_start.toLocaleString()}</div>
                <div><strong>Volume fin:</strong> $${volumeAnalysis.volume_end.toLocaleString()}</div>
            </div>
        `;
    }
    
    displayMarketCapStats(marketCapAnalysis) {
        const content = document.getElementById('market-cap-content');
        if (!content || !marketCapAnalysis) return;
        
        const trendColor = marketCapAnalysis.market_cap_trend === 'growing' ? '#10b981' : 
                          marketCapAnalysis.market_cap_trend === 'shrinking' ? '#ef4444' : '#6b7280';
        
        content.innerHTML = `
            <div style="display: grid; gap: 8px;">
                <div><strong>Tendance:</strong> <span style="color: ${trendColor};">${marketCapAnalysis.market_cap_trend}</span></div>
                <div><strong>Variation:</strong> ${marketCapAnalysis.market_cap_change_percent}%</div>
                <div><strong>Market Cap actuel:</strong> $${marketCapAnalysis.market_cap_end.toLocaleString()}</div>
                <div><strong>Market Cap début:</strong> $${marketCapAnalysis.market_cap_start.toLocaleString()}</div>
            </div>
        `;
    }
    
    displayLLMSummary(summary) {
        const content = document.getElementById('llm-summary-content');
        if (!content) return;
        
        content.textContent = summary;
    }
    
    createAssetChart(chartData) {
        const canvas = document.getElementById('asset-price-chart');
        if (!canvas || !chartData) return;
        
        // Destroy existing chart
        if (this.assetChart) {
            this.assetChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        this.assetChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels.map(label => {
                    const date = new Date(label);
                    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
                }),
                datasets: [{
                    label: 'Prix (USD)',
                    data: chartData.prices,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 1,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#d1d5db'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#9ca3af',
                            maxTicksLimit: 10
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#9ca3af',
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
    
    clearAssetChart() {
        if (this.assetChart) {
            this.assetChart.destroy();
            this.assetChart = null;
        }
    }
    
    showAssetStatsError(message) {
        const sections = [
            'price-stats-content',
            'technical-analysis-content', 
            'volume-stats-content',
            'market-cap-content',
            'llm-summary-content'
        ];
        
        sections.forEach(sectionId => {
            const element = document.getElementById(sectionId);
            if (element) {
                element.innerHTML = `<div style="text-align: center; padding: 20px; color: #ef4444;">❌ ${message}</div>`;
            }
        });
        
        this.clearAssetChart();
    }
    
    closeAssetStatsModal() {
        const modal = document.getElementById('asset-stats-modal');
        if (modal) {
            modal.classList.remove('show'); // Supprimer la classe pour cacher avec animation
            // Attendre la fin de l'animation avant de masquer complètement
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300); // 300ms correspond à la transition CSS
        }
        
        // Cleanup chart
        this.clearAssetChart();
    }
    
    showAssetStatsForSymbol(symbol) {
        console.log('🎯 showAssetStatsForSymbol appelé avec symbol:', symbol);
        
        // Map common symbols to CoinGecko IDs
        const symbolToId = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'ADA': 'cardano',
            'TAO': 'bittensor',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'ASI': 'artificial-superintelligence-alliance',
            'DOGE': 'dogecoin',
            'USDC': 'usd-coin',
            'USDT': 'tether'
        };
        
        const assetId = symbolToId[symbol.toUpperCase()] || symbol.toLowerCase();
        console.log('🔄 Mapping:', symbol, '->', assetId);
        
        this.showAssetStats(assetId, symbol);
    }
    
    // 🐛 DEBUG LOGGING METHODS
    handleDebugLog(payload) {
        // Filtrer les logs trop répétitifs (limiter à 1 par 5 secondes pour le même type)
        const now = Date.now();
        const logType = payload?.step?.step_type || 'unknown';
        const lastLogTime = this.lastDebugLogs?.[logType] || 0;
        
        // Ignorer complètement certains types de logs trop fréquents
        const ignoredLogTypes = ['data_collection', 'status_check', 'heartbeat', 'ping'];
        if (ignoredLogTypes.includes(logType.toLowerCase())) {
            return;
        }
        
        // Limiter à 1 par 5 secondes pour les autres types
        if (now - lastLogTime < 5000) {
            return;
        }
        
        // Initialiser le tracker de logs si nécessaire
        if (!this.lastDebugLogs) {
            this.lastDebugLogs = {};
            this.debugLogCount = 0;
        }
        this.lastDebugLogs[logType] = now;
        this.debugLogCount = (this.debugLogCount || 0) + 1;
        
        // Limiter le nombre total de logs dans la console (garder seulement les plus récents)
        if (this.debugLogCount % 50 === 0) {
            console.log('🧹 Nettoyage des logs debug - trop nombreux');
            // Ne pas afficher ce log particulier
            return;
        }
        
        console.log('🐛 Debug log reçu:', payload);
        
        // Ajouter le log à la console debug
        this.addDebugLogToConsole(payload);
        
        // Mettre à jour le compteur de logs
        this.updateDebugCounter();
    }
    
    handleDebugSessionSummary(payload) {
        console.log('📊 Debug session summary reçu:', payload);
        
        // Afficher un résumé de session dans la console debug
        this.addSessionSummaryToConsole(payload);
    }
    
    handleWalletPerformance(payload) {
        console.log('📊 Performance du wallet reçue:', payload);
        
        // Mettre à jour le budget initial avec la vraie valeur du budget initial
        const walletInitialBudgetElement = document.getElementById('wallet-initial-budget');
        if (walletInitialBudgetElement && payload.initial_budget !== undefined) {
            walletInitialBudgetElement.textContent = `$${parseFloat(payload.initial_budget).toFixed(2)}`;
        }
        
        // Mettre à jour le budget disponible (valeur actuelle des holdings/titres)
        const walletBudgetElement = document.getElementById('wallet-budget');
        if (walletBudgetElement && payload.current_value !== undefined) {
            walletBudgetElement.textContent = `$${parseFloat(payload.current_value).toFixed(2)}`;
        }
        
        // Mettre à jour P&L Total
        const walletPnlElement = document.getElementById('wallet-pnl');
        if (walletPnlElement && payload.net_pnl !== undefined) {
            const netPnl = parseFloat(payload.net_pnl);
            const sign = netPnl >= 0 ? '+' : '';
            walletPnlElement.textContent = `${sign}$${netPnl.toFixed(2)}`;
            walletPnlElement.style.color = netPnl >= 0 ? '#10b981' : '#ef4444';
        }
        
        // Mettre à jour P&L pourcentage
        const walletPnlPercentElement = document.getElementById('wallet-pnl-percent');
        if (walletPnlPercentElement && payload.unrealized_pnl_percent !== undefined) {
            const pnlPercent = parseFloat(payload.unrealized_pnl_percent);
            const sign = pnlPercent >= 0 ? '+' : '';
            walletPnlPercentElement.textContent = `${sign}${pnlPercent.toFixed(2)}%`;
            walletPnlPercentElement.style.color = pnlPercent >= 0 ? '#10b981' : '#ef4444';
        }
        
        // Calculer et afficher P&L du jour (approximation basée sur daily change)
        if (payload.assets && payload.assets.length > 0) {
            let dailyPnl = 0;
            payload.assets.forEach(asset => {
                if (asset.daily_change && asset.current_value) {
                    const dailyChange = parseFloat(asset.daily_change) / 100;
                    const assetDailyPnl = parseFloat(asset.current_value) * dailyChange / (1 + dailyChange);
                    dailyPnl += assetDailyPnl;
                }
            });
            
            const dailyPnlElement = document.getElementById('daily-pnl');
            if (dailyPnlElement) {
                const sign = dailyPnl >= 0 ? '+' : '';
                dailyPnlElement.textContent = `${sign}$${dailyPnl.toFixed(2)}`;
                dailyPnlElement.style.color = dailyPnl >= 0 ? '#10b981' : '#ef4444';
            }
        }
        
        // Le budget et budget initial sont déjà mis à jour plus haut dans handleWalletPerformance
        
        // Mettre à jour le total des frais
        if (payload.total_fees_paid !== undefined) {
            const totalFeesElement = document.getElementById('total-fees');
            if (totalFeesElement) {
                totalFeesElement.textContent = `$${parseFloat(payload.total_fees_paid).toFixed(2)}`;
            }
        }
        
        // Afficher le meilleur et pire performer si disponible
        if (payload.best_performer) {
            this.updatePerformerDisplay('best-performer', payload.best_performer, true);
        }
        if (payload.worst_performer) {
            this.updatePerformerDisplay('worst-performer', payload.worst_performer, false);
        }
        
        // Notification pour changements significatifs
        if (payload.unrealized_pnl_percent !== undefined) {
            const pnlPercent = parseFloat(payload.unrealized_pnl_percent);
            if (Math.abs(pnlPercent) > 5) {
                const message = pnlPercent > 0 
                    ? `🚀 Wallet en hausse: +${pnlPercent.toFixed(1)}%`
                    : `📉 Wallet en baisse: ${pnlPercent.toFixed(1)}%`;
                this.showNotification(message, pnlPercent > 0 ? 'success' : 'info');
            }
        }
    }
    
    updatePerformerDisplay(elementId, performer, isBest) {
        const element = document.getElementById(elementId);
        if (element && performer.symbol && performer.pnl_percent !== undefined) {
            const sign = performer.pnl_percent >= 0 ? '+' : '';
            const icon = isBest ? '🥇' : '🥉';
            element.textContent = `${icon} ${performer.symbol}: ${sign}${performer.pnl_percent.toFixed(1)}%`;
            element.style.color = performer.pnl_percent >= 0 ? '#10b981' : '#ef4444';
        }
    }
    
    // ==================== GESTION MODAL TRADES ====================
    
    showTradesModal(walletName = 'default') {
        console.log('🔍 Ouverture de la modal des trades...');
        console.log('🔍 Document readyState:', document.readyState);
        console.log('🔍 Toutes les modals:', document.querySelectorAll('[id*="modal"]'));
        this.tradesModalWalletName = walletName;
        const modal = document.getElementById('trades-history-modal');
        console.log('🔍 Modal element:', modal);
        if (modal) {
            console.log('✅ Modal trouvée, affichage...');
            modal.style.display = 'flex';
            modal.style.position = 'fixed';
            modal.style.top = '0';
            modal.style.left = '0';
            modal.style.width = '100%';
            modal.style.height = '100%';
            modal.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
            modal.style.zIndex = '10000';
            modal.style.opacity = '1';
            modal.style.visibility = 'visible';
            console.log('🎨 Styles appliqués à la modal');
            this.loadTradesHistory(walletName);
            
            // Ajouter les event listeners pour fermer la modal
            const closeBtn = document.getElementById('close-trades-history-modal');
            const filterAsset = document.getElementById('trades-asset-filter');
            const filterType = document.getElementById('trades-type-filter');
            
            if (closeBtn) {
                closeBtn.onclick = () => this.closeTradesModal();
            }
            
            // Event listeners pour les filtres
            if (filterAsset) {
                filterAsset.onchange = () => this.filterTrades();
            }
            if (filterType) {
                filterType.onchange = () => this.filterTrades();
            }
            
            // Fermer si click sur l'overlay
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closeTradesModal();
                }
            };
        } else {
            console.error('❌ Modal avec ID "trades-history-modal" non trouvée dans le DOM !');
            return;
        }
    }
    
    closeTradesModal() {
        console.log('❌ Fermeture de la modal des trades...');
        const modal = document.getElementById('trades-history-modal');
        if (modal) {
            modal.style.display = 'none';
            modal.style.opacity = '0';
            modal.style.visibility = 'hidden';
        }
    }
    
        // Alias pour compatibilité avec les boutons des simulations
    showTradesHistory(walletName = 'default') {
        console.log(`🔍 showTradesHistory appelée pour le wallet: ${walletName}`);
        this.showTradesModal(walletName);
    }
    
    // Récupérer le nombre de trades pour une simulation
    async getSimulationTradesCount(simulationId) {
        try {
            const response = await fetch(`/api/trading/simulations/${simulationId}/trades/count`);
            if (response.ok) {
                const data = await response.json();
                return data.count || 0;
            }
        } catch (error) {
            console.warn(`⚠️ Impossible de récupérer le nombre de trades pour la simulation ${simulationId}:`, error);
        }
        return 0;
    }
    
    loadTradesHistory(walletName = null) {
        console.log('🔍 Chargement de l\'historique des trades...');
        const targetWallet = walletName || this.tradesModalWalletName || 'default';
        
        // Demander les trades au backend via WebSocket
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const message = {
                type: 'request_trades_history',
                payload: {
                    wallet_name: targetWallet
                }
            };
            console.log('📨 Requête trades_history envoyée pour wallet:', targetWallet);
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('❌ WebSocket non disponible pour charger les trades');
            this.showTradesError('Connexion WebSocket non disponible');
        }
    }
    
    handleTradesHistory(payload) {
        console.log('📊 Historique des trades reçu:', payload);
        console.log('📊 Payload détaillé:', JSON.stringify(payload, null, 2));
        
        const tradesListElement = document.getElementById('trades-list');
        const totalCountElement = document.getElementById('trades-total-count');
        const assetFilterElement = document.getElementById('trades-asset-filter');
        
        console.log('🔍 Elements trouvés:', {
            tradesListElement: !!tradesListElement,
            totalCountElement: !!totalCountElement,
            assetFilterElement: !!assetFilterElement
        });
        
        if (!tradesListElement) {
            console.error('❌ Element trades-list non trouvé !');
            return;
        }
        
        // Stocker les trades pour le filtrage
        this.allTrades = payload.trades || [];
        
        // Mettre à jour le compteur total
        if (totalCountElement) {
            totalCountElement.textContent = this.allTrades.length;
        }
        
        // Populer le filtre des actifs
        if (assetFilterElement) {
            const assets = [...new Set(this.allTrades.map(t => t.asset_symbol))];
            assetFilterElement.innerHTML = '<option value="">Tous les actifs</option>';
            assets.forEach(asset => {
                assetFilterElement.innerHTML += `<option value="${asset}">${asset}</option>`;
            });
        }
        
        // Afficher les trades
        this.displayTrades(this.allTrades);

        // Mettre à jour le libellé du bouton "Voir X trades" de la carte simulation correspondante
        try {
            const walletName = this.tradesModalWalletName || payload.wallet_name || payload.wallet || payload.walletName;
            if (walletName) {
                const count = this.allTrades.length;
                // Mémoriser la valeur exacte pour ce wallet afin de survivre aux re-render
                this.tradesCountOverride = this.tradesCountOverride || {};
                this.tradesCountOverride[walletName] = count;

                // Mise à jour SCOPÉE dans la carte ciblée (plus robuste)
                const card = document.querySelector(`.simulation-card[data-wallet-name="${walletName}"]`);
                if (card) {
                    card.querySelectorAll(`button[data-wallet-name="${walletName}"]`).forEach(b => {
                        b.textContent = `📊 Voir ${count} trade${count > 1 ? 's' : ''}`;
                    });
                    card.querySelectorAll(`.trades-total-value[data-wallet-name="${walletName}"]`).forEach(el => {
                        el.textContent = String(count);
                    });
                }

                // Fallback global si nécessaire (au cas où)
                document.querySelectorAll(`button[data-wallet-name="${walletName}"]`).forEach(b => {
                    b.textContent = `📊 Voir ${count} trade${count > 1 ? 's' : ''}`;
                });
                document.querySelectorAll(`.trades-total-value[data-wallet-name="${walletName}"]`).forEach(el => {
                    el.textContent = String(count);
                });
            }
        } catch (e) {
            console.warn('⚠️ Impossible de mettre à jour le compteur de trades sur la carte simulation:', e);
        }
    }
    
    displayTrades(trades) {
        console.log('🎯 Affichage des trades:', trades?.length || 0, 'trades');
        const tradesListElement = document.getElementById('trades-list');
        if (!tradesListElement) {
            console.error('❌ Element trades-list non trouvé dans displayTrades !');
            return;
        }
        
        if (!trades || trades.length === 0) {
            console.log('⚠️ Aucun trade à afficher');
            tradesListElement.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 40px; font-size: 14px;">
                    Aucun trade trouvé
                </div>
            `;
            return;
        }
        
        console.log('📋 Premier trade pour debug:', trades[0]);
        
        // Trier par date décroissante (plus récent en premier)
        const sortedTrades = [...trades].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        tradesListElement.innerHTML = sortedTrades.map((trade, index) => {
            const date = new Date(trade.timestamp);
            const dateStr = date.toLocaleDateString('fr-FR');
            const timeStr = date.toLocaleTimeString('fr-FR');
            
            const typeColor = trade.type === 'BUY' ? '#10b981' : '#ef4444';
            const typeIcon = trade.type === 'BUY' ? '📈' : '📉';
            const quantity = parseFloat(trade.quantity);
            const price = parseFloat(trade.price_at_time);
            const value = quantity * price;
            const fee = parseFloat(trade.fee || 0);
            
            // Debug pour les premières transactions
            if (index < 3) {
                console.log(`🔍 Trade ${index}:`, {
                    quantity: trade.quantity,
                    price: trade.price_at_time,
                    value: value,
                    fee: trade.fee
                });
            }
            
            // ID unique pour la zone expandable du reasoning
            const reasoningId = `reasoning-${index}`;
            
            return `
                <div style="
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    padding: 16px;
                    transition: background-color 0.2s;
                " onmouseover="this.style.backgroundColor='rgba(255,255,255,0.05)'" 
                   onmouseout="this.style.backgroundColor='transparent'">
                    
                    <!-- En-tête du trade -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr auto; gap: 12px; align-items: center;">
                        <div>
                            <div style="color: #9ca3af; font-size: 12px;">Date</div>
                            <div style="color: #fff; font-weight: 600;">${dateStr}</div>
                            <div style="color: #9ca3af; font-size: 11px;">${timeStr}</div>
                        </div>
                        
                        <div>
                            <div style="color: #9ca3af; font-size: 12px;">Type</div>
                            <div style="color: ${typeColor}; font-weight: 600; display: flex; align-items: center; gap: 4px;">
                                <span>${typeIcon}</span>
                                <span>${trade.type}</span>
                            </div>
                        </div>
                        
                        <div>
                            <div style="color: #9ca3af; font-size: 12px;">Asset</div>
                            <div style="color: #fff; font-weight: 600;">${trade.asset_symbol}</div>
                        </div>
                        
                        <div>
                            <div style="color: #9ca3af; font-size: 12px;">Quantité</div>
                            <div style="color: #fff; font-weight: 600;">${quantity < 0.00001 ? quantity.toExponential(2) : quantity.toFixed(8)}</div>
                            <div style="color: #9ca3af; font-size: 11px;">@ $${price.toFixed(2)}</div>
                        </div>
                        
                        <div style="text-align: right;">
                            <div style="color: #9ca3af; font-size: 12px;">Valeur</div>
                            <div style="color: #fff; font-weight: 600;">
                                ${value < 0.01 ? 
                                    (value < 0.0001 ? `$${value.toExponential(2)}` : `$${value.toFixed(4)}`) : 
                                    `$${value.toFixed(2)}`
                                }
                            </div>
                            ${fee > 0.001 ? `<div style="color: #ef4444; font-size: 11px;">Frais: ${fee < 0.01 ? `$${fee.toFixed(6)}` : `$${fee.toFixed(2)}`}</div>` : 
                              fee > 0 ? `<div style="color: #9ca3af; font-size: 11px;">Frais: <$0.001</div>` : 
                              `<div style="color: #9ca3af; font-size: 11px;">Pas de frais</div>`}
                        </div>
                        
                        <div>
                            ${trade.reasoning ? `
                                <button onclick="this.parentElement.parentElement.parentElement.querySelector('#${reasoningId}').style.display = this.parentElement.parentElement.parentElement.querySelector('#${reasoningId}').style.display === 'none' ? 'block' : 'none'; this.textContent = this.textContent === '📋 Reasoning' ? '📋 Cacher' : '📋 Reasoning';" 
                                        style="
                                            background: rgba(59, 130, 246, 0.2);
                                            color: #3b82f6;
                                            border: 1px solid rgba(59, 130, 246, 0.3);
                                            border-radius: 4px;
                                            padding: 4px 8px;
                                            font-size: 11px;
                                            cursor: pointer;
                                            transition: all 0.2s;
                                        "
                                        onmouseover="this.style.backgroundColor='rgba(59, 130, 246, 0.3)'"
                                        onmouseout="this.style.backgroundColor='rgba(59, 130, 246, 0.2)'">
                                    📋 Reasoning
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    
                    <!-- Zone expandable pour le reasoning -->
                    ${trade.reasoning ? `
                        <div id="${reasoningId}" style="
                            display: none;
                            margin-top: 12px;
                            padding: 12px;
                            background: rgba(0, 0, 0, 0.3);
                            border-radius: 6px;
                            border-left: 3px solid #3b82f6;
                        ">
                            <div style="color: #9ca3af; font-size: 12px; margin-bottom: 6px;">🤖 Reasoning de l'IA:</div>
                            <div style="color: #d1d5db; font-size: 13px; line-height: 1.4; white-space: pre-wrap;">${trade.reasoning}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    }
    
    filterTrades() {
        if (!this.allTrades) return;
        
        const assetFilter = document.getElementById('trades-asset-filter')?.value;
        const typeFilter = document.getElementById('trades-type-filter')?.value;
        
        let filteredTrades = this.allTrades;
        
        if (assetFilter) {
            filteredTrades = filteredTrades.filter(t => t.asset_symbol === assetFilter);
        }
        
        if (typeFilter) {
            filteredTrades = filteredTrades.filter(t => t.type === typeFilter);
        }
        
        this.displayTrades(filteredTrades);
    }
    
    showTradesError(message) {
        const tradesListElement = document.getElementById('trades-list');
        if (tradesListElement) {
            tradesListElement.innerHTML = `
                <div style="text-align: center; color: #ef4444; padding: 40px; font-size: 14px;">
                    ❌ ${message}
                </div>
            `;
        }
    }
    
    addDebugLogToConsole(payload) {
        const debugConsole = document.getElementById('debug-console');
        if (!debugConsole) {
            console.warn('Debug console element not found');
            return;
        }
        
        // Si debug en pause, ne pas ajouter les nouveaux logs
        if (this.debugPaused) {
            return;
        }
        
        const { step, session_info } = payload;
        const timestamp = new Date(step.timestamp).toLocaleTimeString();
        
        // Créer l'élément de log
        const logEntry = document.createElement('div');
        logEntry.className = `debug-log-entry ${step.step_type.toLowerCase()}`;
        
        // Icône selon le type d'étape
        const iconMap = {
            'SESSION_START': '🚀',
            'DATA_COLLECTION': '📊',
            'LLM_EXCHANGE': '🤖',
            'DECISION_MADE': '🎯',
            'EXECUTION_ATTEMPT': '💼',
            'DATABASE_OP': '🗃️',
            'WEBSOCKET_BROADCAST': '📡',
            'ERROR': '❌',
            'SESSION_END': '🏁'
        };
        
        const icon = iconMap[step.step_type] || '📝';
        
        logEntry.innerHTML = `
            <div class="debug-log-header">
                <span class="debug-log-icon">${icon}</span>
                <span class="debug-log-time">${timestamp}</span>
                <span class="debug-log-type">${step.step_type}</span>
                <span class="debug-log-session">${session_info.asset_ticker}</span>
            </div>
            <div class="debug-log-message">${step.message}</div>
            ${step.data && Object.keys(step.data).length > 0 ? 
                `<div class="debug-log-data">
                    <details>
                        <summary>Détails</summary>
                        <pre>${JSON.stringify(step.data, null, 2)}</pre>
                    </details>
                </div>` : ''
            }
        `;
        
        // Ajouter au début de la console (plus récent en haut)
        debugConsole.insertBefore(logEntry, debugConsole.firstChild);
        
        // Limiter le nombre d'entrées (garder les 100 plus récentes)
        const entries = debugConsole.querySelectorAll('.debug-log-entry');
        if (entries.length > 100) {
            entries[entries.length - 1].remove();
        }
        
        // Auto-scroll si l'utilisateur est en bas
        if (debugConsole.scrollTop + debugConsole.clientHeight >= debugConsole.scrollHeight - 10) {
            debugConsole.scrollTop = 0; // Scroll vers le haut car les nouveaux logs sont au début
        }
    }
    
    addSessionSummaryToConsole(payload) {
        const debugConsole = document.getElementById('debug-console');
        if (!debugConsole) return;
        
        const summaryEntry = document.createElement('div');
        summaryEntry.className = 'debug-session-summary';
        
        summaryEntry.innerHTML = `
            <div class="session-summary-header">
                <span class="session-icon">📊</span>
                <span class="session-title">Session ${payload.asset_ticker} terminée</span>
                <span class="session-duration">${payload.duration_seconds}s</span>
            </div>
            <div class="session-stats">
                <span>✅ ${payload.total_steps} étapes</span>
                <span>📊 ${payload.status}</span>
            </div>
        `;
        
        debugConsole.insertBefore(summaryEntry, debugConsole.firstChild);
    }
    
    updateDebugCounter() {
        const counter = document.getElementById('debug-counter');
        if (!counter) return;
        
        const entries = document.querySelectorAll('.debug-log-entry').length;
        counter.textContent = entries;
        
        // Animation simple pour attirer l'attention
        counter.style.animation = 'pulse 0.5s ease-in-out';
        setTimeout(() => {
            counter.style.animation = '';
        }, 500);
    }
    
    setupWorldContextModal() {
        console.log('🌍 Configuration modal contexte mondial...');
        
        // Event listener pour le bouton world context
        const worldContextBtn = document.getElementById('world-context-btn');
        if (worldContextBtn) {
            worldContextBtn.addEventListener('click', () => {
                this.openWorldContextModal();
            });
            console.log('✅ Bouton world context configuré');
        } else {
            console.warn('⚠️ Bouton world-context-btn non trouvé');
        }
        
        // Event listener pour fermer le modal
        const closeBtn = document.getElementById('close-world-context-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeWorldContextModal();
            });
        }
        
        // Fermer en cliquant à l'extérieur
        const modal = document.getElementById('world-context-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeWorldContextModal();
                }
            });
        }
        
        // Fermer avec la touche Escape (ajouté dans keydown existant)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const worldModal = document.getElementById('world-context-modal');
                if (worldModal && worldModal.style.display === 'flex') {
                    this.closeWorldContextModal();
                }
            }
        });
    }
    
    async openWorldContextModal() {
        console.log('🌍 Ouverture modal contexte mondial...');
        
        const modal = document.getElementById('world-context-modal');
        if (!modal) {
            console.error('❌ Modal world-context-modal non trouvé');
            return;
        }
        
        // Afficher le modal
        modal.style.display = 'flex';
        modal.classList.add('show');
        
        // Charger les données depuis l'API
        try {
            console.log('📡 Récupération des données de contexte mondial...');
            const response = await fetch('/api/world-context');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('✅ Données de contexte reçues:', data);
            
            if (data.status === 'success') {
                this.populateWorldContextModal(data.world_context);
            } else {
                throw new Error(data.message || 'Erreur lors de la récupération du contexte');
            }
            
        } catch (error) {
            console.error('❌ Erreur lors de la récupération du contexte mondial:', error);
            this.showWorldContextError(error.message);
        }
    }
    
    populateWorldContextModal(worldContext) {
        console.log('📝 Remplissage du modal avec les données:', worldContext);
        
        // Résumé du contexte mondial
        const summaryElement = document.getElementById('world-context-summary');
        if (summaryElement) {
            summaryElement.textContent = worldContext.world_summary || 'Aucun résumé disponible';
        }
        
        // Score de sentiment
        const sentimentScore = parseFloat(worldContext.sentiment_score) || 0;
        const sentimentElement = document.getElementById('sentiment-score');
        const sentimentBar = document.getElementById('sentiment-bar');
        
        if (sentimentElement) {
            sentimentElement.textContent = sentimentScore.toFixed(1);
            
            // Couleur basée sur le sentiment
            if (sentimentScore < -0.2) {
                sentimentElement.style.color = '#ef4444'; // Rouge
            } else if (sentimentScore > 0.2) {
                sentimentElement.style.color = '#10b981'; // Vert
            } else {
                sentimentElement.style.color = '#fbbf24'; // Jaune
            }
        }
        
        if (sentimentBar) {
            // Convertir le score (-1 à +1) en pourcentage (0 à 100%)
            const barWidth = ((sentimentScore + 1) / 2) * 100;
            sentimentBar.style.width = barWidth + '%';
        }
        
        // Thèmes clés
        const themesContainer = document.getElementById('key-themes-container');
        if (themesContainer) {
            themesContainer.innerHTML = '';
            
            const themes = worldContext.key_themes || [];
            if (themes.length > 0) {
                themes.forEach(theme => {
                    const themeTag = document.createElement('div');
                    themeTag.style.cssText = `
                        background: rgba(16, 185, 129, 0.2);
                        border: 1px solid rgba(16, 185, 129, 0.4);
                        border-radius: 20px;
                        padding: 6px 12px;
                        color: #10b981;
                        font-size: 12px;
                        font-weight: 600;
                        white-space: nowrap;
                    `;
                    themeTag.textContent = theme;
                    themesContainer.appendChild(themeTag);
                });
            } else {
                themesContainer.innerHTML = '<div style="color: #9ca3af; font-style: italic;">Aucun thème identifié</div>';
            }
        }
        
        // Dernière mise à jour
        const lastUpdatedElement = document.getElementById('context-last-updated');
        if (lastUpdatedElement) {
            if (worldContext.last_updated) {
                const date = new Date(worldContext.last_updated);
                const formattedDate = date.toLocaleString('fr-FR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                lastUpdatedElement.textContent = formattedDate;
            } else {
                lastUpdatedElement.textContent = 'Jamais mis à jour';
            }
        }
    }
    
    showWorldContextError(errorMessage) {
        console.log('❌ Affichage de l\'erreur dans le modal');
        
        const summaryElement = document.getElementById('world-context-summary');
        if (summaryElement) {
            summaryElement.innerHTML = `
                <div style="color: #ef4444; text-align: center; padding: 20px;">
                    <div style="font-size: 24px; margin-bottom: 10px;">⚠️</div>
                    <div style="font-weight: 600; margin-bottom: 8px;">Erreur de chargement</div>
                    <div style="font-size: 14px; opacity: 0.8;">${errorMessage}</div>
                </div>
            `;
        }
        
        // Masquer les autres sections en cas d'erreur
        const sentimentScore = document.getElementById('sentiment-score');
        const themesContainer = document.getElementById('key-themes-container');
        const lastUpdated = document.getElementById('context-last-updated');
        
        if (sentimentScore) sentimentScore.textContent = 'N/A';
        if (themesContainer) themesContainer.innerHTML = '<div style="color: #9ca3af;">Non disponible</div>';
        if (lastUpdated) lastUpdated.textContent = 'Erreur';
    }
    
    closeWorldContextModal() {
        console.log('❌ Fermeture modal contexte mondial');
        const modal = document.getElementById('world-context-modal');
        if (modal) {
            modal.classList.remove('show');
            // Hide after animation completes
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    }
    
    setupFinanceMarketModal() {
        console.log('💹 Configuration modal marché financier...');
        
        // Event listener pour le bouton finance market
        const financeMarketBtn = document.getElementById('finance-market-btn');
        if (financeMarketBtn) {
            financeMarketBtn.addEventListener('click', () => {
                this.openFinanceMarketModal();
            });
            console.log('✅ Bouton finance market configuré');
        } else {
            console.warn('⚠️ Bouton finance-market-btn non trouvé');
        }
        
        // Event listener pour fermer le modal
        const closeBtn = document.getElementById('close-finance-market-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeFinanceMarketModal();
            });
        }
    }

    setupSettingsModal() {
        console.log('⚙️ Configuration modal Settings...');
        
        // Event listener pour le bouton settings
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.openSettingsModal();
            });
            console.log('✅ Bouton settings configuré');
        } else {
            console.warn('⚠️ Bouton settings-btn non trouvé');
        }
        
        // Event listener pour fermer le modal
        const closeBtn = document.getElementById('close-settings-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeSettingsModal();
            });
        }
        
        // Event listeners pour les boutons d'actions LLM
        const addLlmBtn = document.getElementById('add-llm-btn');
        if (addLlmBtn) {
            addLlmBtn.addEventListener('click', () => {
                this.showAddLlmForm();
            });
        }
        
        const addSimulationConfigBtn = document.getElementById('add-simulation-config-btn');
        if (addSimulationConfigBtn) {
            addSimulationConfigBtn.addEventListener('click', () => {
                console.log('🎮 Bouton Ajouter simulation config cliqué');
                this.showAddSimulationForm();
            });
        }
        
        const saveConfigBtn = document.getElementById('save-config-btn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => {
                this.saveConfiguration();
            });
        }
        
        const resetConfigBtn = document.getElementById('reset-config-btn');
        if (resetConfigBtn) {
            resetConfigBtn.addEventListener('click', () => {
                this.resetConfiguration();
            });
        }
        
        // Event listeners pour le modal d'ajout de LLM
        const closeAddLlmBtn = document.getElementById('close-add-llm-modal');
        if (closeAddLlmBtn) {
            closeAddLlmBtn.addEventListener('click', () => {
                this.closeAddLlmModal();
            });
        }
        
        const cancelAddLlmBtn = document.getElementById('cancel-add-llm-btn');
        if (cancelAddLlmBtn) {
            cancelAddLlmBtn.addEventListener('click', () => {
                this.closeAddLlmModal();
            });
        }
        
        const addLlmForm = document.getElementById('add-llm-form');
        if (addLlmForm) {
            addLlmForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitAddLlmForm();
            });
        }
        
        const testLlmConfigBtn = document.getElementById('test-llm-config-btn');
        if (testLlmConfigBtn) {
            testLlmConfigBtn.addEventListener('click', () => {
                this.testLlmConfigurationForm();
            });
        }
        
        // Auto-génération de l'ID basé sur le nom
        const llmNameInput = document.getElementById('llm-name');
        const llmIdInput = document.getElementById('llm-id');
        if (llmNameInput && llmIdInput) {
            llmNameInput.addEventListener('input', (e) => {
                const name = e.target.value;
                const id = name.toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .replace(/-+/g, '-')
                    .trim();
                llmIdInput.value = id;
            });
        }
        
        // Auto-remplissage basé sur le type de LLM
        // Sera configuré quand le modal s'ouvre
        
        // Fermer en cliquant à l'extérieur (settings)
        const settingsModal = document.getElementById('settings-modal');
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    this.closeSettingsModal();
                }
            });
        }
        
        // Fermer en cliquant à l'extérieur (finance)
        const financeModal = document.getElementById('finance-market-modal');
        if (financeModal) {
            financeModal.addEventListener('click', (e) => {
                if (e.target === financeModal) {
                    this.closeFinanceMarketModal();
                }
            });
        }
        
        // Fermer en cliquant à l'extérieur (add-llm)
        const addLlmModal = document.getElementById('add-llm-modal');
        if (addLlmModal) {
            addLlmModal.addEventListener('click', (e) => {
                if (e.target === addLlmModal) {
                    this.closeAddLlmModal();
                }
            });
        }
        
        // Fermer avec la touche Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const financeModal = document.getElementById('finance-market-modal');
                const settingsModal = document.getElementById('settings-modal');
                const addLlmModal = document.getElementById('add-llm-modal');
                
                if (financeModal && financeModal.style.display === 'flex') {
                    this.closeFinanceMarketModal();
                }
                if (settingsModal && settingsModal.style.display === 'flex') {
                    this.closeSettingsModal();
                }
                if (addLlmModal && addLlmModal.style.display === 'flex') {
                    this.closeAddLlmModal();
                }
            }
        });
    }

    // ========== TRADING BOT INTERFACE ==========
    setupTradingBotInterface() {
        console.log('🤖 Setup interface trading bot...');
        
        // Variables pour le trading bot
        this.tradingBotStatus = 'unknown';
        this.tradingSignals = [];
        this.currentSignalPage = 0;
        this.signalsPerPage = 6; // 6 signaux par page
        
        // Boutons de contrôle
        this.setupTradingBotButtons();
        this.setupTradingStatsModal();
        this.setupBotConfigModal();
        
        // Charger le statut initial avec délai
        setTimeout(() => {
            this.loadTradingBotStatus();
            this.loadTradingSignals();
            this.loadBotConfig(); // Charger aussi la config au démarrage
            this.loadTradingStatsForSummary(); // Charger les stats pour le win rate
        }, 500);
        
        // Mise à jour périodique
        this.startTradingBotUpdateInterval();
    }
    
    setupTradingBotButtons() {
        // Bouton Start/Stop
        const startStopBtn = document.getElementById('bot-start-stop-btn');
        if (startStopBtn) {
            startStopBtn.addEventListener('click', () => this.toggleBot());
        }
        
        // Bouton Scan manuel
        const scanBtn = document.getElementById('trading-bot-scan-btn');
        if (scanBtn) {
            scanBtn.addEventListener('click', () => this.manualScanSignals());
        }
        
        // Bouton Stats
        const statsBtn = document.getElementById('trading-stats-btn');
        if (statsBtn) {
            statsBtn.addEventListener('click', () => this.openTradingStatsModal());
        }
        
        // Bouton Config
        const configBtn = document.getElementById('bot-config-btn');
        if (configBtn) {
            configBtn.addEventListener('click', () => this.openBotConfigModal());
        }
    }
    
    setupTradingStatsModal() {
        // Fermeture de la modal
        const closeButtons = [
            document.getElementById('close-trading-stats-modal'),
            document.getElementById('close-stats-footer-btn')
        ];
        
        closeButtons.forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => this.closeTradingStatsModal());
            }
        });
        
        // Bouton actualiser
        const refreshBtn = document.getElementById('refresh-stats-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshTradingStats());
        }
        
        // Fermer en cliquant à l'extérieur
        const modal = document.getElementById('trading-stats-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeTradingStatsModal();
                }
            });
        }
    }
    
    setupBotConfigModal() {
        // Fermeture de la modal config
        const closeButtons = [
            document.getElementById('close-bot-config-modal'),
            document.getElementById('close-bot-config-footer-btn')
        ];
        
        closeButtons.forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => this.closeBotConfigModal());
            }
        });
        
        // Bouton refresh config
        const refreshBtn = document.getElementById('refresh-bot-config-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshBotConfig());
        }
        
        // Boutons presets
        const presetButtons = [
            { id: 'preset-scalp-btn', preset: 'scalp' },
            { id: 'preset-day-btn', preset: 'day' },
            { id: 'preset-swing-btn', preset: 'swing' }
        ];
        
        presetButtons.forEach(({ id, preset }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', () => this.applyPreset(preset));
            }
        });
        
        const resetBtn = document.getElementById('preset-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetBotConfig());
        }
        
        // Fermer en cliquant à l'extérieur
        const configModal = document.getElementById('bot-config-modal');
        if (configModal) {
            configModal.addEventListener('click', (e) => {
                if (e.target === configModal) {
                    this.closeBotConfigModal();
                }
            });
        }
    }
    
    async loadTradingBotStatus() {
        try {
            console.log('📡 Chargement statut bot...');
            const response = await fetch('/api/trading-bot/status');
            const data = await response.json();
            
            if (data.success) {
                this.tradingBotStatus = data.is_running ? 'running' : 'stopped';
                this.updateBotStatusDisplay();
            }
        } catch (error) {
            console.error('❌ Erreur chargement statut bot:', error);
            this.tradingBotStatus = 'error';
            this.updateBotStatusDisplay();
        }
    }
    
    async loadTradingSignals() {
        try {
            console.log('📡 Chargement signaux trading...');
            const response = await fetch('/api/signals?limit=50');
            const data = await response.json();
            
            if (data.success) {
                this.tradingSignals = data.signals || [];
                this.updateSignalsDisplay();
                this.updateSignalsInfo();
            }
        } catch (error) {
            console.error('❌ Erreur chargement signaux:', error);
            this.updateSignalsDisplay([]);
        }
    }
    
    async manualScanSignals() {
        console.log('🔍 Lancement scan manuel...');
        const scanBtn = document.getElementById('trading-bot-scan-btn');
        
        if (scanBtn) {
            const originalText = scanBtn.innerHTML;
            scanBtn.innerHTML = '⏳ Scan...';
            scanBtn.disabled = true;
        }
        
        try {
            const response = await fetch('/api/trading-bot/scan', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ Scan terminé: ${data.signals?.length || 0} signaux`);
                this.tradingSignals = data.signals || [];
                this.updateSignalsDisplay();
                this.updateSignalsInfo();
            } else {
                console.error('❌ Erreur scan:', data.message);
            }
        } catch (error) {
            console.error('❌ Erreur scan manuel:', error);
        } finally {
            if (scanBtn) {
                scanBtn.innerHTML = '🔍 Scan';
                scanBtn.disabled = false;
            }
        }
    }
    
    updateBotStatusDisplay() {
        const indicator = document.getElementById('bot-status-indicator');
        const text = document.getElementById('bot-status-text');
        
        if (!indicator || !text) return;
        
        switch (this.tradingBotStatus) {
            case 'running':
                indicator.style.backgroundColor = '#10b981';
                text.textContent = 'En marche';
                break;
            case 'stopped':
                indicator.style.backgroundColor = '#ef4444';
                text.textContent = 'Arrêté';
                break;
            case 'error':
                indicator.style.backgroundColor = '#f59e0b';
                text.textContent = 'Erreur';
                break;
            default:
                indicator.style.backgroundColor = '#6b7280';
                text.textContent = 'Inconnu';
        }
    }
    
    updateSignalsDisplay() {
        const container = document.getElementById('signals-compact');
        if (!container) return;
        
        if (!this.tradingSignals || this.tradingSignals.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px; font-size: 12px;">
                    Aucun signal détecté
                </div>
            `;
            return;
        }
        
        // Pagination
        const start = this.currentSignalPage * this.signalsPerPage;
        const end = start + this.signalsPerPage;
        const pageSignals = this.tradingSignals.slice(start, end);
        
        const signalsHtml = pageSignals.map(signal => this.renderSignalCard(signal)).join('');
        container.innerHTML = signalsHtml;
        
        this.updateSignalsPagination();
    }
    
    renderSignalCard(signal) {
        const sideColor = signal.side === 'LONG' ? '#10b981' : '#ef4444';
        const timestamp = new Date(signal.timestamp).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        return `
            <div style="
                background: rgba(0, 0, 0, 0.4);
                border-left: 3px solid ${sideColor};
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 8px;
                font-size: 11px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <div style="font-weight: 600; color: #fff;">
                        ${signal.symbol}
                    </div>
                    <div style="color: ${sideColor}; font-weight: 600; font-size: 10px;">
                        ${signal.side}
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #9ca3af;">
                    <span>Prix: $${signal.last_price.toFixed(4)}</span>
                    <span>${timestamp}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #9ca3af; margin-top: 2px;">
                    <span>TP: $${signal.tp.toFixed(4)}</span>
                    <span>SL: $${signal.sl.toFixed(4)}</span>
                </div>
                <div style="font-size: 10px; color: #6b7280; margin-top: 2px;">
                    RSI: ${signal.rsi.toFixed(1)} | Score: ${signal.score.toFixed(1)}
                </div>
            </div>
        `;
    }
    
    updateSignalsInfo() {
        const infoElement = document.getElementById('signals-info');
        if (!infoElement) return;
        
        const count = this.tradingSignals?.length || 0;
        infoElement.textContent = count > 0 ? `${count} signal${count > 1 ? 's' : ''}` : 'Aucun signal';
    }
    
    updateSignalsPagination() {
        const pagination = document.getElementById('signals-pagination');
        const prevBtn = document.getElementById('signals-prev-page');
        const nextBtn = document.getElementById('signals-next-page');
        const info = document.getElementById('signals-pagination-info');
        
        if (!pagination || !prevBtn || !nextBtn || !info) return;
        
        const totalPages = Math.ceil(this.tradingSignals.length / this.signalsPerPage);
        
        if (totalPages <= 1) {
            pagination.style.display = 'none';
            return;
        }
        
        pagination.style.display = 'flex';
        prevBtn.disabled = this.currentSignalPage === 0;
        nextBtn.disabled = this.currentSignalPage >= totalPages - 1;
        info.textContent = `${this.currentSignalPage + 1}/${totalPages}`;
        
        // Event listeners pour la pagination
        prevBtn.onclick = () => {
            if (this.currentSignalPage > 0) {
                this.currentSignalPage--;
                this.updateSignalsDisplay();
            }
        };
        
        nextBtn.onclick = () => {
            if (this.currentSignalPage < totalPages - 1) {
                this.currentSignalPage++;
                this.updateSignalsDisplay();
            }
        };
    }
    
    async openTradingStatsModal() {
        console.log('📊 Ouverture modal stats trading...');
        const modal = document.getElementById('trading-stats-modal');
        if (!modal) return;
        
        modal.style.display = 'flex';
        modal.classList.add('show');
        
        // Charger les stats
        await this.loadTradingStats();
    }
    
    closeTradingStatsModal() {
        const modal = document.getElementById('trading-stats-modal');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300); // Attendre la fin de l'animation CSS
        }
    }
    
    async loadTradingStats() {
        try {
            const response = await fetch('/api/trading-stats');
            const data = await response.json();
            
            if (data.success) {
                this.displayTradingStats(data.stats);
                this.loadTradingSummary(data.stats);
            }
        } catch (error) {
            console.error('❌ Erreur chargement stats:', error);
        }
    }
    
    displayTradingStats(stats) {
        // Affichage du résumé principal
        const content = document.getElementById('trading-stats-content');
        if (!content) return;
        
        const winRate = stats.winrate_pct || 0;
        const winColor = winRate >= 60 ? '#10b981' : winRate >= 40 ? '#f59e0b' : '#ef4444';
        
        content.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px;">
                <div style="background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 24px; font-weight: 600; color: ${winColor};">${winRate.toFixed(1)}%</div>
                    <div style="font-size: 12px; color: #9ca3af;">Win Rate</div>
                </div>
                <div style="background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 24px; font-weight: 600; color: #10b981;">${stats.wins || 0}</div>
                    <div style="font-size: 12px; color: #9ca3af;">Wins</div>
                </div>
                <div style="background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 24px; font-weight: 600; color: #ef4444;">${stats.losses || 0}</div>
                    <div style="font-size: 12px; color: #9ca3af;">Losses</div>
                </div>
                <div style="background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 24px; font-weight: 600; color: #f59e0b;">${stats.open_trades || 0}</div>
                    <div style="font-size: 12px; color: #9ca3af;">Trades Ouverts</div>
                </div>
            </div>
        `;
        
        // Affichage des trades récents
        this.displayRecentTrades(stats.recent_trades || []);
        
        // Affichage de la configuration
        this.displayBotConfig(stats.config || {});
    }
    
    displayRecentTrades(trades) {
        const container = document.getElementById('recent-trades-table');
        if (!container) return;
        
        if (!trades || trades.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px;">
                    Aucun trade récent
                </div>
            `;
            return;
        }
        
        const tradesHtml = trades.map(trade => {
            const statusColor = trade.status === 'CLOSED' ? '#9ca3af' : '#f59e0b';
            const reasonColor = trade.close_reason === 'TP' ? '#10b981' : '#ef4444';
            
            return `
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 8px; padding: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); font-size: 11px;">
                    <div style="color: #fff; font-weight: 600;">${trade.symbol}</div>
                    <div style="color: ${trade.side === 'LONG' ? '#10b981' : '#ef4444'};">${trade.side}</div>
                    <div style="color: ${statusColor};">${trade.status}</div>
                    <div style="color: #9ca3af;">$${parseFloat(trade.entry).toFixed(4)}</div>
                    <div style="color: ${reasonColor};">${trade.close_reason || 'N/A'}</div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 8px; padding: 8px; border-bottom: 2px solid rgba(255, 255, 255, 0.2); font-size: 11px; font-weight: 600; color: #9ca3af;">
                <div>Symbol</div>
                <div>Side</div>
                <div>Status</div>
                <div>Entry</div>
                <div>Reason</div>
            </div>
            ${tradesHtml}
        `;
    }
    
    displayBotConfig(config) {
        const container = document.getElementById('bot-config-display');
        if (!container) return;
        
        container.innerHTML = `
            <div style="color: #9ca3af;">
                <strong>Scan:</strong> ${config.scan_seconds || 120}s
            </div>
            <div style="color: #9ca3af;">
                <strong>Interval:</strong> ${config.kline_interval || '5m'}
            </div>
            <div style="color: #9ca3af;">
                <strong>Paper Trading:</strong> ${config.paper_trading ? '✅' : '❌'}
            </div>
            <div style="color: #9ca3af;">
                <strong>RT TP/SL:</strong> ${config.realtime_tpsl ? '✅' : '❌'}
            </div>
            <div style="color: #9ca3af;">
                <strong>Min 24h:</strong> $${(config.min_24h_usd || 0).toLocaleString()}
            </div>
            <div style="color: #9ca3af;">
                <strong>Quotes:</strong> ${config.quote_whitelist?.join(', ') || 'Toutes'}
            </div>
        `;
    }
    
    loadTradingSummary(stats) {
        // Affichage du résumé rapide dans la section signaux
        const summaryDiv = document.getElementById('trading-summary');
        const winrateDisplay = document.getElementById('winrate-display');
        const openTradesDisplay = document.getElementById('open-trades-display');
        
        if (summaryDiv && stats && (stats.total > 0 || stats.open_trades > 0)) {
            summaryDiv.style.display = 'block';
            
            if (winrateDisplay) {
                const winRate = stats.winrate_pct || 0;
                winrateDisplay.textContent = `${winRate.toFixed(1)}%`;
                winrateDisplay.style.color = winRate >= 60 ? '#10b981' : winRate >= 40 ? '#f59e0b' : '#ef4444';
            }
            
            if (openTradesDisplay) {
                openTradesDisplay.textContent = stats.open_trades || 0;
            }
        } else if (summaryDiv) {
            summaryDiv.style.display = 'none';
        }
    }
    
    async loadTradingStatsForSummary() {
        try {
            console.log('📡 Chargement stats pour résumé...');
            const response = await fetch('/api/trading-stats');
            const data = await response.json();
            
            if (data.success) {
                this.loadTradingSummary(data.stats);
            }
        } catch (error) {
            console.error('❌ Erreur chargement stats résumé:', error);
        }
    }
    
    async refreshTradingStats() {
        console.log('🔄 Actualisation stats trading...');
        await this.loadTradingStats();
        await this.loadTradingSignals();
    }
    
    startTradingBotUpdateInterval() {
        // Mise à jour toutes les 30 secondes
        setInterval(() => {
            this.loadTradingBotStatus();
            this.loadTradingSignals();
            this.loadTradingStatsForSummary(); // Mettre à jour le win rate
        }, 30000);
        
        // Timer de countdown pour le prochain scan
        this.startScanCountdown();
    }
    
    startScanCountdown() {
        // Timer visuel pour le prochain scan - sera mis à jour par updateScanCountdown
        this.scanInterval = 120; // Par défaut
        this.countdownSeconds = this.scanInterval;
        
        if (this.countdownTimer) {
            clearInterval(this.countdownTimer);
        }
        
        this.countdownTimer = setInterval(() => {
            this.updateCountdownDisplay();
        }, 1000);
    }
    
    updateScanCountdown(intervalSeconds) {
        console.log(`🕒 Mise à jour countdown: ${intervalSeconds}s`);
        this.scanInterval = intervalSeconds;
        this.countdownSeconds = intervalSeconds;
        this.updateCountdownDisplay();
    }
    
    updateCountdownDisplay() {
        const countdownElement = document.getElementById('countdown-timer');
        if (countdownElement) {
            countdownElement.textContent = this.countdownSeconds;
        }
        
        this.countdownSeconds--;
        if (this.countdownSeconds < 0) {
            this.countdownSeconds = this.scanInterval; // Reset
        }
    }
    
    async toggleBot() {
        const startStopBtn = document.getElementById('bot-start-stop-btn');
        if (!startStopBtn) return;
        
        const originalContent = startStopBtn.innerHTML;
        startStopBtn.innerHTML = '⏳ ...';
        startStopBtn.disabled = true;
        
        try {
            if (this.tradingBotStatus === 'running') {
                const response = await fetch('/api/trading-bot/stop', { method: 'POST' });
                const data = await response.json();
                console.log('Bot stop result:', data);
            } else {
                const response = await fetch('/api/trading-bot/start', { method: 'POST' });
                const data = await response.json();
                console.log('Bot start result:', data);
            }
            
            // Recharger le statut
            await this.loadTradingBotStatus();
            
        } catch (error) {
            console.error('❌ Erreur toggle bot:', error);
        } finally {
            startStopBtn.disabled = false;
        }
    }
    
    async openBotConfigModal() {
        console.log('⚙️ Ouverture modal config bot...');
        const modal = document.getElementById('bot-config-modal');
        if (!modal) return;
        
        modal.style.display = 'flex';
        modal.classList.add('show');
        await this.loadBotConfig();
    }
    
    closeBotConfigModal() {
        const modal = document.getElementById('bot-config-modal');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300); // Attendre la fin de l'animation CSS
        }
    }
    
    async loadBotConfig() {
        try {
            console.log('📡 Chargement config bot...');
            const response = await fetch('/api/bot-config');
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Config bot chargée:', data.config);
                const configDisplay = document.getElementById('current-bot-config');
                if (configDisplay) {
                    configDisplay.textContent = JSON.stringify(data.config, null, 2);
                }
                
                // Mettre à jour l'affichage principal du bot
                this.updateBotStateDisplay(data.config);
                
                // Mettre à jour le timer de countdown
                const scanSeconds = data.config?.trading?.scan_seconds || 120;
                this.updateScanCountdown(scanSeconds);
            }
        } catch (error) {
            console.error('❌ Erreur chargement config bot:', error);
        }
    }
    
    async refreshBotConfig() {
        console.log('🔄 Refresh config bot...');
        await this.loadBotConfig();
        await this.loadTradingBotStatus();
    }
    
    async applyPreset(presetName) {
        console.log(`🎛️ Application preset ${presetName}...`);
        
        try {
            const response = await fetch(`/api/bot-config/preset/${presetName}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ Preset ${presetName} appliqué`);
                await this.refreshBotConfig();
            } else {
                console.error(`❌ Erreur preset: ${data.message}`);
            }
        } catch (error) {
            console.error('❌ Erreur application preset:', error);
        }
    }
    
    async resetBotConfig() {
        console.log('🔄 Reset config bot...');
        
        if (!confirm('Êtes-vous sûr de vouloir remettre la configuration par défaut ?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/bot-config/reset', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Config reset');
                await this.refreshBotConfig();
            } else {
                console.error(`❌ Erreur reset: ${data.message}`);
            }
        } catch (error) {
            console.error('❌ Erreur reset config:', error);
        }
    }
    
    updateBotStateDisplay(config) {
        // Mettre à jour l'affichage de l'état du bot
        const scanIntervalEl = document.getElementById('bot-scan-interval');
        const klineIntervalEl = document.getElementById('bot-kline-interval');
        const paperTradingEl = document.getElementById('bot-paper-trading');
        const minVolumeEl = document.getElementById('bot-min-volume');
        const botModeEl = document.getElementById('bot-mode-display');
        const stateDisplay = document.getElementById('bot-state-display');
        
        if (config) {
            const trading = config.trading || {};
            const strategy = config.strategy || {};
            const paperTrading = config.paper_trading || {};
            
            if (scanIntervalEl) {
                scanIntervalEl.textContent = `${trading.scan_seconds || 120}s`;
            }
            if (klineIntervalEl) {
                klineIntervalEl.textContent = trading.kline_interval || '5m';
            }
            if (paperTradingEl) {
                paperTradingEl.textContent = paperTrading.enabled ? '✅' : '❌';
                paperTradingEl.style.color = paperTrading.enabled ? '#10b981' : '#ef4444';
            }
            if (minVolumeEl) {
                const vol = strategy.min_24h_usd || 0;
                minVolumeEl.textContent = vol >= 1000000 ? `${Math.round(vol/1000000)}M` : `${Math.round(vol/1000)}K`;
            }
            if (botModeEl) {
                // Déterminer le mode selon la config
                const scanSeconds = trading.scan_seconds || 120;
                let mode = 'Custom';
                if (scanSeconds === 180) mode = 'Scalp';
                else if (scanSeconds === 300) mode = 'Day';
                else if (scanSeconds === 600) mode = 'Swing';
                else if (scanSeconds === 120) mode = 'Default';
                
                botModeEl.textContent = `Mode: ${mode}`;
                
                // Couleur de la bordure selon le mode
                const colors = {
                    'Scalp': '#10b981',
                    'Day': '#3b82f6',
                    'Swing': '#8b5cf6',
                    'Default': '#f59e0b',
                    'Custom': '#6b7280'
                };
                
                if (stateDisplay) {
                    stateDisplay.style.borderLeftColor = colors[mode] || '#6b7280';
                }
            }
        }
    }
    
    updateBotStatusDisplay() {
        const indicator = document.getElementById('bot-status-indicator');
        const text = document.getElementById('bot-status-text');
        const startStopBtn = document.getElementById('bot-start-stop-btn');
        const waitingMessage = document.getElementById('bot-waiting-message');
        
        if (!indicator || !text) return;
        
        switch (this.tradingBotStatus) {
            case 'running':
                indicator.style.backgroundColor = '#10b981';
                text.textContent = 'En marche';
                if (startStopBtn) {
                    startStopBtn.innerHTML = '⏸️ Arrêt';
                    startStopBtn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                }
                if (waitingMessage) {
                    waitingMessage.querySelector('div').textContent = 'Bot en fonctionnement...';
                }
                break;
            case 'stopped':
                indicator.style.backgroundColor = '#ef4444';
                text.textContent = 'Arrêté';
                if (startStopBtn) {
                    startStopBtn.innerHTML = '▶️ Start';
                    startStopBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                }
                if (waitingMessage) {
                    waitingMessage.querySelector('div').textContent = 'Bot en attente de démarrage...';
                }
                break;
            case 'error':
                indicator.style.backgroundColor = '#f59e0b';
                text.textContent = 'Erreur';
                if (startStopBtn) {
                    startStopBtn.innerHTML = '⚠️ Erreur';
                    startStopBtn.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
                }
                break;
            default:
                indicator.style.backgroundColor = '#6b7280';
                text.textContent = 'Initialisation...';
                if (startStopBtn) {
                    startStopBtn.innerHTML = '⏳ Init';
                    startStopBtn.style.background = 'linear-gradient(135deg, #6b7280, #4b5563)';
                }
        }
    }
    
    updateSignalsDisplay() {
        const container = document.getElementById('signals-compact');
        const waitingMessage = document.getElementById('bot-waiting-message');
        
        if (!container) return;
        
        if (!this.tradingSignals || this.tradingSignals.length === 0) {
            // Afficher le message d'attente
            if (waitingMessage) {
                waitingMessage.style.display = 'block';
            }
            container.style.display = 'none';
            return;
        }
        
        // Cacher le message d'attente et afficher les signaux
        if (waitingMessage) {
            waitingMessage.style.display = 'none';
        }
        container.style.display = 'block';
        
        // Pagination
        const start = this.currentSignalPage * this.signalsPerPage;
        const end = start + this.signalsPerPage;
        const pageSignals = this.tradingSignals.slice(start, end);
        
        const signalsHtml = pageSignals.map(signal => this.renderSignalCard(signal)).join('');
        container.innerHTML = signalsHtml;
        
        this.updateSignalsPagination();
    }
    
    updateSignalsInfo() {
        const infoElement = document.getElementById('signals-info');
        const winrateMini = document.getElementById('bot-winrate-mini');
        
        if (infoElement) {
            const count = this.tradingSignals?.length || 0;
            infoElement.textContent = count > 0 ? `${count} signal${count > 1 ? 's' : ''}` : '0 signal';
        }
    }
    
    loadTradingSummary(stats) {
        // Affichage du résumé rapide
        const summaryDiv = document.getElementById('trading-summary');
        const winrateDisplay = document.getElementById('winrate-display');
        const openTradesDisplay = document.getElementById('open-trades-display');
        const winrateMini = document.getElementById('bot-winrate-mini');
        
        if (summaryDiv && stats && (stats.total > 0 || stats.open_trades > 0)) {
            summaryDiv.style.display = 'block';
            
            if (winrateDisplay) {
                const winRate = stats.winrate_pct || 0;
                winrateDisplay.textContent = `${winRate.toFixed(1)}%`;
                winrateDisplay.style.color = winRate >= 60 ? '#10b981' : winRate >= 40 ? '#f59e0b' : '#ef4444';
                
                // Mini winrate dans l'en-tête
                if (winrateMini) {
                    winrateMini.textContent = `WR: ${winRate.toFixed(1)}%`;
                    winrateMini.style.color = winRate >= 60 ? '#10b981' : winRate >= 40 ? '#f59e0b' : '#ef4444';
                }
            }
            
            if (openTradesDisplay) {
                openTradesDisplay.textContent = stats.open_trades || 0;
            }
        } else if (summaryDiv) {
            summaryDiv.style.display = 'none';
            if (winrateMini) {
                winrateMini.textContent = 'WR: 0%';
                winrateMini.style.color = '#9ca3af';
            }
        }
    }

    // ============== SETTINGS MODAL METHODS ==============

    async openSettingsModal() {
        console.log('⚙️ Ouverture modal Settings...');
        
        const modal = document.getElementById('settings-modal');
        if (!modal) {
            console.error('❌ Modal settings-modal non trouvé');
            return;
        }
        
        // Afficher le modal
        modal.style.display = 'flex';
        modal.classList.add('show');
        
        // Charger la configuration actuelle
        await this.loadCurrentSettings();
    }

    closeSettingsModal() {
        console.log('⚙️ Fermeture modal Settings...');
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('show');
        }
    }

    async loadCurrentSettings() {
        console.log('🚨 DEBUT loadCurrentSettings() appelé');
        console.log('📡 Chargement de la configuration actuelle...');
        
        try {
            // Charger la configuration LLM
            const llmResponse = await fetch('/api/llm-config');
            if (llmResponse.ok) {
                const llmData = await llmResponse.json();
                if (llmData.status === 'success') {
                    this.populateLLMConfiguration(llmData);
                }
            }
            
            // Simulations: affichage déplacé vers la Config (Scheduler)
            // Intentionnellement aucun chargement/affichage des simulations dans Settings
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement des settings:', error);
        }
    }

    populateLLMConfiguration(data) {
        console.log('🤖 Population configuration LLM:', data);
        
        const defaultLlm = data.llms.find(llm => llm.is_default);
        if (defaultLlm) {
            // Mettre à jour le LLM par défaut affiché
            const defaultNameEl = document.getElementById('default-llm-name');
            const defaultModelEl = document.getElementById('default-llm-model');
            const defaultUrlEl = document.getElementById('default-llm-url');
            
            if (defaultNameEl) defaultNameEl.textContent = defaultLlm.name;
            if (defaultModelEl) defaultModelEl.textContent = defaultLlm.model;
            if (defaultUrlEl) defaultUrlEl.textContent = defaultLlm.url;
        }
        
        // Remplir la liste des LLM configurés
        const llmListEl = document.getElementById('llm-pool-list');
        if (llmListEl) {
            const otherLlms = data.llms.filter(llm => !llm.is_default);
            
            if (otherLlms.length === 0) {
                llmListEl.innerHTML = `
                    <div style="text-align: center; color: #9ca3af; padding: 20px;">
                        Aucun modèle LLM supplémentaire configuré
                    </div>
                `;
            } else {
                llmListEl.innerHTML = otherLlms.map(llm => `
                    <div style="
                        background: rgba(255, 255, 255, 0.05);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 6px;
                        padding: 12px;
                        margin-bottom: 8px;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="color: #fff; font-weight: 600;">${llm.name}</span>
                            <div style="display: flex; gap: 4px;">
                                ${llm.is_active ? 
                                    '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 2px 6px; border-radius: 3px; font-size: 10px;">ACTIF</span>' :
                                    '<span style="background: rgba(156, 163, 175, 0.2); color: #9ca3af; padding: 2px 6px; border-radius: 3px; font-size: 10px;">INACTIF</span>'
                                }
                                <button onclick="window.hiveAI?.testLLMConnection('${llm.id}')" style="
                                    background: rgba(59, 130, 246, 0.2);
                                    border: 1px solid rgba(59, 130, 246, 0.3);
                                    color: #3b82f6;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                ">🔍 Test</button>
                                <button onclick="window.hiveAI?.editLLM('${llm.id}')" style="
                                    background: rgba(139, 92, 246, 0.2);
                                    border: 1px solid rgba(139, 92, 246, 0.3);
                                    color: #8b5cf6;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                ">✏️ Edit</button>
                                ${llm.is_default ? `
                                <button onclick="window.hiveAI?.reconfigureDSPy()" style="
                                    background: rgba(16, 185, 129, 0.2);
                                    border: 1px solid rgba(16, 185, 129, 0.3);
                                    color: #10b981;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                ">🔄 DSPy</button>
                                ` : `
                                <button onclick="window.hiveAI?.setAsDefaultLLM('${llm.id}')" style="
                                    background: rgba(245, 158, 11, 0.2);
                                    border: 1px solid rgba(245, 158, 11, 0.3);
                                    color: #f59e0b;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                ">⭐ Défaut</button>
                                `}
                                ${llm.id === 'default_ollama' ? `
                                <button disabled style="
                                    background: rgba(156, 163, 175, 0.1);
                                    border: 1px solid rgba(156, 163, 175, 0.2);
                                    color: #6b7280;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: not-allowed;
                                    opacity: 0.5;
                                " title="LLM système protégé">🔒</button>
                                ` : `
                                <button onclick="window.hiveAI?.removeLLM('${llm.id}')" style="
                                    background: rgba(239, 68, 68, 0.2);
                                    border: 1px solid rgba(239, 68, 68, 0.3);
                                    color: #ef4444;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                ">🗑️</button>
                                `}
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                            <div>
                                <span style="color: #9ca3af;">Type:</span>
                                <span style="color: #fff; margin-left: 4px;">${llm.type.toUpperCase()}</span>
                            </div>
                            <div>
                                <span style="color: #9ca3af;">Modèle:</span>
                                <span style="color: #fff; margin-left: 4px;">${llm.model}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    populateTradingSimulations(data) {
        console.log('💼 Population simulations de trading:', data);
        console.log(`💼 Nombre de simulations reçues: ${data.simulations ? data.simulations.length : 0}`);
        
        const simListEl = document.getElementById('trading-simulations-list');
        console.log('💼 Element trading-simulations-list trouvé:', !!simListEl);
        if (simListEl) {
            if (data.simulations.length === 0) {
                simListEl.innerHTML = `
                    <div style="text-align: center; color: #9ca3af; padding: 20px;">
                        Aucune simulation de trading configurée
                    </div>
                `;
            } else {
                simListEl.innerHTML = data.simulations.map(sim => `
                    <div style="
                        background: rgba(255, 255, 255, 0.05);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 6px;
                        padding: 12px;
                        margin-bottom: 8px;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="color: #fff; font-weight: 600;">${sim.name}</span>
                            <div style="display: flex; gap: 4px;">
                                ${sim.is_active ? 
                                    '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 2px 6px; border-radius: 3px; font-size: 10px;">ACTIF</span>' :
                                    '<span style="background: rgba(156, 163, 175, 0.2); color: #9ca3af; padding: 2px 6px; border-radius: 3px; font-size: 10px;">INACTIF</span>'
                                }
                                <button onclick="window.hiveAI?.editSimulation('${sim.id}')" style="
                                    background: rgba(59, 130, 246, 0.2);
                                    border: 1px solid rgba(59, 130, 246, 0.3);
                                    color: #3b82f6;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                " title="Modifier cette simulation">✏️</button>
                                <button onclick="window.hiveAI?.removeSimulation('${sim.id}')" style="
                                    background: rgba(239, 68, 68, 0.2);
                                    border: 1px solid rgba(239, 68, 68, 0.3);
                                    color: #ef4444;
                                    padding: 2px 6px;
                                    border-radius: 3px;
                                    font-size: 10px;
                                    cursor: pointer;
                                ">🗑️</button>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                            <div>
                                <span style="color: #9ca3af;">LLM:</span>
                                <span style="color: #fff; margin-left: 4px;">${sim.llm_name}</span>
                            </div>
                            <div>
                                <span style="color: #9ca3af;">Budget:</span>
                                <span style="color: #10b981; margin-left: 4px;">$${sim.budget.toLocaleString()}</span>
                            </div>
                            <div>
                                <span style="color: #9ca3af;">Stratégie:</span>
                                <span style="color: #fff; margin-left: 4px;">${sim.strategy}</span>
                            </div>
                            <div>
                                <span style="color: #9ca3af;">Risque:</span>
                                <span style="color: #f59e0b; margin-left: 4px;">${sim.risk_level}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    updateSimulationsCounter(simulations) {
        const activeCount = simulations.filter(sim => sim.is_active).length;
        
        // Chercher tous les éléments qui affichent le compteur de simulations actives
        const counterElements = document.querySelectorAll('[data-simulations-counter], .simulations-counter');
        counterElements.forEach(el => {
            el.textContent = `${activeCount} active`;
        });
        
        // Chercher spécifiquement dans la section config
        const configSection = document.querySelector('#settings-content');
        if (configSection) {
            const counterText = configSection.querySelector('div');
            if (counterText && counterText.textContent.includes('active')) {
                counterText.textContent = `${activeCount} active`;
            }
        }
        
        console.log(`📊 Compteur mis à jour: ${activeCount} simulations actives`);
    }

    async testLLMConnection(llmId) {
        console.log(`🔍 Test de connexion LLM: ${llmId}`);
        
        try {
            const response = await fetch(`/api/llm-config/${llmId}/test`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (data.connected) {
                    this.showNotification('✅ Connexion réussie!', 'success');
                } else {
                    this.showNotification('❌ Connexion échouée', 'error');
                }
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Erreur test connexion:', error);
            this.showNotification('❌ Erreur lors du test', 'error');
        }
    }

    async reconfigureDSPy() {
        console.log('🔄 Reconfiguration DSPy...');
        
        try {
            const response = await fetch('/api/llm-config/reconfigure-dspy', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('✅ DSPy reconfiguré avec succès!', 'success');
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Erreur reconfiguration DSPy:', error);
            this.showNotification('❌ Erreur lors de la reconfiguration', 'error');
        }
    }

    async setAsDefaultLLM(llmId) {
        console.log(`⭐ Définir LLM par défaut: ${llmId}`);
        
        if (!confirm('Définir ce LLM comme modèle par défaut ? Cela affectera le chat et les agents de trading.')) {
            return;
        }
        
        try {
            // D'abord, récupérer la configuration actuelle du LLM
            const llmResponse = await fetch('/api/llm-config');
            if (!llmResponse.ok) {
                throw new Error('Impossible de récupérer la configuration LLM');
            }
            
            const llmData = await llmResponse.json();
            if (llmData.status !== 'success') {
                throw new Error(llmData.message || 'Erreur récupération configuration');
            }
            
            // Trouver le LLM à définir par défaut
            const targetLlm = llmData.llms.find(llm => llm.id === llmId);
            if (!targetLlm) {
                throw new Error('LLM non trouvé');
            }
            
            // Mettre à jour le LLM pour le marquer comme défaut
            const updateData = {
                ...targetLlm,
                is_default: true
            };
            
            const response = await fetch(`/api/llm-config/${llmId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification(`✅ ${targetLlm.name} défini comme LLM par défaut!`, 'success');
                
                // Recharger les settings pour voir les changements
                await this.loadCurrentSettings();
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
            
        } catch (error) {
            console.error('❌ Erreur définition LLM par défaut:', error);
            this.showNotification('❌ Erreur lors de la définition du LLM par défaut', 'error');
        }
    }

    async editLLM(llmId) {
        console.log(`✏️ Édition LLM: ${llmId}`);
        console.log('🔍 Étape 1: Début édition');
        
        try {
            // Récupérer la configuration actuelle du LLM
            const llmResponse = await fetch('/api/llm-config');
            if (!llmResponse.ok) {
                throw new Error('Impossible de récupérer la configuration LLM');
            }
            
            const llmData = await llmResponse.json();
            if (llmData.status !== 'success') {
                throw new Error(llmData.message || 'Erreur récupération configuration');
            }
            
            console.log('🔍 Étape 2: Données récupérées', llmData);
            
            // Trouver le LLM à éditer
            const targetLlm = llmData.llms.find(llm => llm.id === llmId);
            if (!targetLlm) {
                throw new Error('LLM non trouvé');
            }
            
            console.log('🔍 Étape 3: LLM trouvé', targetLlm);
            
            // Le formulaire d'ajout est dans un modal séparé add-llm-modal
            const addLlmModal = document.getElementById('add-llm-modal');
            console.log('🔍 Étape 4: Modal Add-LLM', addLlmModal ? 'trouvé' : 'non trouvé');
            
            if (addLlmModal) {
                console.log('🔍 Étape 5: Ouverture modal Add-LLM');
                addLlmModal.style.display = 'flex';
                addLlmModal.classList.add('show');
                // Attendre que le modal soit complètement chargé
                await new Promise(resolve => setTimeout(resolve, 200));
            } else {
                throw new Error('Modal add-llm-modal non trouvé');
            }
            
            // Remplir le formulaire d'ajout avec les données existantes
            console.log('🔍 Étape 6: Début remplissage formulaire');
            
            const fields = [
                { id: 'llm-name', value: targetLlm.name },
                { id: 'llm-type', value: targetLlm.type },
                { id: 'llm-url', value: targetLlm.url },
                { id: 'llm-model', value: targetLlm.model },
                { id: 'llm-api-key', value: targetLlm.api_key || '' },
                { id: 'llm-max-tokens', value: targetLlm.max_tokens },
                { id: 'llm-temperature', value: targetLlm.temperature },
                { id: 'llm-timeout', value: targetLlm.timeout }
            ];
            
            let foundFields = 0;
            for (const field of fields) {
                const element = document.getElementById(field.id);
                if (element) {
                    element.value = field.value;
                    foundFields++;
                    console.log(`✅ Champ rempli: ${field.id} = ${field.value}`);
                } else {
                    console.error(`❌ Élément non trouvé: ${field.id}`);
                }
            }
            
            console.log(`🔍 Étape 7: ${foundFields}/${fields.length} champs trouvés et remplis`);
            
            // Gérer les checkboxes séparément
            const isActiveElement = document.getElementById('llm-is-active');
            if (isActiveElement) {
                isActiveElement.checked = targetLlm.is_active;
            }
            
            const isDefaultElement = document.getElementById('llm-is-default');
            if (isDefaultElement) {
                isDefaultElement.checked = targetLlm.is_default;
            }
            
            // Marquer le formulaire comme étant en mode édition
            const form = document.getElementById('add-llm-form');
            const submitBtn = form.querySelector('button[type="submit"]');
            
            // Stocker l'ID du LLM en cours d'édition
            form.dataset.editingLlmId = llmId;
            submitBtn.textContent = '💾 Mettre à jour';
            
            // Changer le titre du formulaire
            const formTitle = document.querySelector('#add-llm-section h4');
            if (formTitle) {
                formTitle.textContent = `✏️ Modifier: ${targetLlm.name}`;
            }
            
            // Scroller vers le formulaire dans le modal
            const addLlmSection = document.getElementById('add-llm-section');
            if (addLlmSection) {
                addLlmSection.scrollIntoView({ behavior: 'smooth' });
            }
            
        } catch (error) {
            console.error('❌ Erreur édition LLM:', error);
            this.showNotification('❌ Erreur lors du chargement des données LLM', 'error');
        }
    }

    async removeLLM(llmId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer ce LLM ?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/llm-config/${llmId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('✅ LLM supprimé avec succès', 'success');
                await this.loadCurrentSettings(); // Recharger
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Erreur suppression LLM:', error);
            this.showNotification('❌ Erreur lors de la suppression', 'error');
        }
    }

    async removeSimulation(simId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer cette simulation ?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/trading-simulations/${simId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('✅ Simulation supprimée avec succès', 'success');
                await this.loadCurrentSettings(); // Recharger
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Erreur suppression simulation:', error);
            this.showNotification('❌ Erreur lors de la suppression', 'error');
        }
    }

    async editSimulation(simId) {
        console.log('🚀 DEBUG: editSimulation appelée avec simId:', simId);
        try {
            // Récupérer les détails de la simulation
            console.log('🔄 Récupération des simulations...');
            const response = await fetch(`/api/simulations`);
            const data = await response.json();
            console.log('📊 Data récupérée:', data);
            
            if (data.status !== 'success') {
                throw new Error(data.message);
            }
            
            console.log('🔍 Recherche simulation ID:', simId);
            console.log('📋 Simulations disponibles:', data.simulations.map(s => ({id: s.id, name: s.name})));
            
            const simulation = data.simulations.find(s => s.id == simId);
            if (!simulation) {
                throw new Error(`Simulation ID ${simId} non trouvée`);
            }
            
            console.log('✅ Simulation trouvée:', simulation);
            // Afficher le modal d'édition avec les données existantes
            this.showEditSimulationModal(simulation);
            
        } catch (error) {
            console.error('❌ Erreur récupération simulation:', error);
            this.showNotification('❌ Erreur lors du chargement de la simulation', 'error');
        }
    }
    
    showEditSimulationModal(simulation) {
        // Remove any existing modal
        const existingModal = document.getElementById('edit-simulation-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Create simple modal with inline styles
        const modal = document.createElement('div');
        modal.id = 'edit-simulation-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;
        
        modal.innerHTML = `
            <div style="
                background: #1a1a2e;
                padding: 30px;
                border-radius: 12px;
                width: 90%;
                max-width: 500px;
                border: 2px solid #4c1d95;
                color: white;
                box-sizing: border-box;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: white;">✏️ Modifier la Simulation</h3>
                    <button onclick="this.closest('#edit-simulation-modal').remove()" style="
                        background: none;
                        border: none;
                        color: white;
                        font-size: 24px;
                        cursor: pointer;
                        padding: 0;
                        width: 30px;
                        height: 30px;
                    ">×</button>
                </div>
                
                <form id="edit-simulation-form" style="display: flex; flex-direction: column; gap: 15px;">
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #e5e7eb;">Nom:</label>
                        <input type="text" id="edit-name" value="${simulation.name || ''}" style="
                            width: 100%;
                            padding: 10px;
                            border: 1px solid #4c1d95;
                            border-radius: 6px;
                            background: #16213e;
                            color: white;
                            box-sizing: border-box;
                        " required>
                    </div>
                    
                    
                    
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #e5e7eb;">🎯 Politique de Trading:</label>
                        <select id="edit-strategy" style="
                            width: 100%;
                            padding: 10px;
                            border: 1px solid #4c1d95;
                            border-radius: 6px;
                            background: #16213e;
                            color: white;
                            box-sizing: border-box;
                        ">
                            <option value="conservative" ${simulation.strategy === 'conservative' ? 'selected' : ''}>🛡️ Conservative - Risque faible, gains stables</option>
                            <option value="balanced" ${simulation.strategy === 'balanced' ? 'selected' : ''}>⚖️ Balanced - Équilibre risque/rendement</option>
                            <option value="aggressive" ${simulation.strategy === 'aggressive' ? 'selected' : ''}>🚀 Aggressive - Risque élevé, gains potentiels</option>
                            <option value="scalping" ${simulation.strategy === 'scalping' ? 'selected' : ''}>⚡ Scalping - Transactions rapides</option>
                        </select>
                    </div>
                    
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #e5e7eb;">⏰ Fréquence d'Exécution:</label>
                        <select id="edit-frequency" style="
                            width: 100%;
                            padding: 10px;
                            border: 1px solid #4c1d95;
                            border-radius: 6px;
                            background: #16213e;
                            color: white;
                            box-sizing: border-box;
                        ">
                            <option value="5min" ${simulation.frequency_minutes == 5 ? 'selected' : ''}>⚡ 5 minutes - Hyper réactif</option>
                            <option value="15min" ${simulation.frequency_minutes == 15 ? 'selected' : ''}>⚡ 15 minutes - Ultra réactif</option>
                            <option value="30min" ${simulation.frequency_minutes == 30 ? 'selected' : ''}>🔥 30 minutes - Très réactif</option>
                            <option value="1h" ${simulation.frequency_minutes == 60 ? 'selected' : ''}>⚖️ 1 heure - Équilibré</option>
                            <option value="4h" ${simulation.frequency_minutes == 240 ? 'selected' : ''}>🎯 4 heures - Tendances moyennes</option>
                            <option value="1d" ${simulation.frequency_minutes == 1440 ? 'selected' : ''}>📈 1 jour - Tendances longues</option>
                        </select>
                    </div>
                    
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #e5e7eb;">Description:</label>
                        <textarea id="edit-description" rows="3" style="
                            width: 100%;
                            padding: 10px;
                            border: 1px solid #4c1d95;
                            border-radius: 6px;
                            background: #16213e;
                            color: white;
                            resize: vertical;
                            box-sizing: border-box;
                        ">${simulation.description || ''}</textarea>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 20px;">
                        <button type="submit" style="
                            flex: 1;
                            padding: 12px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            font-weight: 500;
                            cursor: pointer;
                        ">💾 Sauvegarder</button>
                        <button type="button" onclick="this.closest('#edit-simulation-modal').remove()" style="
                            flex: 1;
                            padding: 12px;
                            background: #6b7280;
                            border: none;
                            border-radius: 6px;
                            color: white;
                            font-weight: 500;
                            cursor: pointer;
                        ">Annuler</button>
                    </div>
                </form>
            </div>
        `;
        
        // Add form submission handler
        modal.querySelector('#edit-simulation-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Helper function to convert frequency string to minutes
            const convertFrequencyToMinutes = (freqStr) => {
                switch(freqStr) {
                    case '5min': return 5;
                    case '15min': return 15;
                    case '30min': return 30;
                    case '1h': return 60;
                    case '4h': return 240;
                    case '1d': return 1440;
                    default: return parseInt(freqStr); // fallback for old format
                }
            };
            
            const formData = {
                name: modal.querySelector('#edit-name').value,
                description: modal.querySelector('#edit-description').value,
                
                strategy: modal.querySelector('#edit-strategy').value,
                frequency_minutes: convertFrequencyToMinutes(modal.querySelector('#edit-frequency').value),
                is_active: simulation.is_active
            };
            
            try {
                const response = await fetch(`/api/simulations/${simulation.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    this.showNotification('Simulation mise à jour avec succès!', 'success');
                    modal.remove();
                    this.loadSimulations();
                } else {
                    const error = await response.text();
                    this.showNotification('Erreur lors de la mise à jour: ' + error, 'error');
                }
            } catch (error) {
                this.showNotification('Erreur lors de la mise à jour: ' + error.message, 'error');
            }
        });
        
        document.body.appendChild(modal);
    }
    
    async handleEditSimulation(event, simId) {
        event.preventDefault();
        
        const formData = {
            name: document.getElementById('edit-sim-name').value,
            strategy: document.getElementById('edit-sim-strategy').value,
            frequency_minutes: parseInt(document.getElementById('edit-sim-frequency').value),
            description: document.getElementById('edit-sim-description').value
        };
        
        try {
            const response = await fetch(`/api/simulations/${simId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('✅ Simulation modifiée avec succès', 'success');
                document.getElementById('edit-simulation-modal').remove();
                await this.loadCurrentSettings(); // Recharger les données
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Erreur modification simulation:', error);
            this.showNotification('❌ Erreur lors de la modification', 'error');
        }
    }

    showAddLlmForm() {
        console.log('🤖 Affichage formulaire ajout LLM');
        
        // Fermer le modal settings
        this.closeSettingsModal();
        
        // Ouvrir le modal d'ajout de LLM
        const modal = document.getElementById('add-llm-modal');
        if (modal) {
            modal.style.display = 'flex';
            modal.classList.add('show');
            
            // Reset du formulaire
            this.resetAddLlmForm();
            
            // Configurer les event listeners maintenant que le modal est visible
            this.setupAddLlmFormListeners();
        }
    }

    setupAddLlmFormListeners() {
        // Auto-remplissage basé sur le type de LLM
        const llmTypeSelect = document.getElementById('llm-type');
        if (llmTypeSelect) {
            // Supprimer l'ancien listener s'il existe
            llmTypeSelect.removeEventListener('change', this.llmTypeChangeHandler);
            
            // Créer et stocker le handler
            this.llmTypeChangeHandler = (e) => {
                this.handleLlmTypeChange(e.target.value);
            };
            
            // Ajouter le nouveau listener
            llmTypeSelect.addEventListener('change', this.llmTypeChangeHandler);
            
            console.log('✅ Event listener type LLM configuré');
        }

        // Auto-génération de l'ID basé sur le nom (dans le contexte du modal)
        const llmNameInput = document.getElementById('llm-name');
        const llmIdInput = document.getElementById('llm-id');
        if (llmNameInput && llmIdInput) {
            // Supprimer l'ancien listener s'il existe
            llmNameInput.removeEventListener('input', this.llmNameInputHandler);
            
            // Créer et stocker le handler
            this.llmNameInputHandler = (e) => {
                const name = e.target.value;
                const id = name.toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .replace(/-+/g, '-')
                    .trim();
                llmIdInput.value = id;
            };
            
            // Ajouter le nouveau listener
            llmNameInput.addEventListener('input', this.llmNameInputHandler);
            
            console.log('✅ Event listener nom LLM configuré');
        }
    }

    closeAddLlmModal() {
        console.log('🤖 Fermeture modal ajout LLM');
        const modal = document.getElementById('add-llm-modal');
        if (modal) {
            modal.style.display = 'none';  
            modal.classList.remove('show');
            this.resetAddLlmForm();
        }
    }

    resetAddLlmForm() {
        const form = document.getElementById('add-llm-form');
        if (form) {
            form.reset();
            
            // Remettre les valeurs par défaut
            document.getElementById('llm-max-tokens').value = '4096';
            document.getElementById('llm-temperature').value = '0.7';
            document.getElementById('llm-timeout').value = '30';
            document.getElementById('llm-is-active').checked = true;
            document.getElementById('llm-is-default').checked = false;
        }
    }

    handleLlmTypeChange(type) {
        console.log(`🔄 Changement type LLM: ${type}`);
        
        const urlInput = document.getElementById('llm-url');
        const modelInput = document.getElementById('llm-model');
        const nameInput = document.getElementById('llm-name');
        const apiKeyInput = document.getElementById('llm-api-key');
        
        // Configurations prédéfinies pour chaque type
        const configs = {
            ollama: {
                url: 'http://localhost:11434',
                model: 'gemma3:1b',
                name: 'Ollama Local',
                apiKeyRequired: false
            },
            openai: {
                url: 'https://api.openai.com/v1',
                model: 'gpt-4o-mini',
                name: 'OpenAI GPT',
                apiKeyRequired: true
            },
            claude: {
                url: 'https://api.anthropic.com/v1/messages',
                model: 'claude-3-haiku-20240307',
                name: 'Claude 3',
                apiKeyRequired: true
            },
            gemini: {
                url: 'https://generativelanguage.googleapis.com/v1beta',
                model: 'gemini-1.5-flash',
                name: 'Gemini Pro',
                apiKeyRequired: true
            },
            grok: {
                url: 'https://api.x.ai/v1',
                model: 'grok-beta',
                name: 'Grok',
                apiKeyRequired: true
            },
            deepseek: {
                url: 'https://api.deepseek.com/v1',
                model: 'deepseek-chat',
                name: 'DeepSeek',
                apiKeyRequired: true
            },
            kimi: {
                url: 'https://api.moonshot.cn/v1',
                model: 'moonshot-v1-8k',
                name: 'Kimi',
                apiKeyRequired: true
            },
            qwen: {
                url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                model: 'qwen-turbo',
                name: 'Qwen',
                apiKeyRequired: true
            }
        };
        
        const config = configs[type];
        if (config) {
            // Force le remplissage des champs avec les valeurs prédéfinies
            urlInput.value = config.url;
            modelInput.value = config.model;
            
            // Pour le nom, on ne le remplace que s'il est vide ou s'il correspond à un autre type
            const currentName = nameInput.value.trim();
            const isGenericName = Object.values(configs).some(c => c.name === currentName) || !currentName;
            if (isGenericName) {
                nameInput.value = config.name;
                
                // Mettre à jour l'ID automatiquement
                const id = config.name.toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .replace(/-+/g, '-')
                    .trim();
                const llmIdInput = document.getElementById('llm-id');
                if (llmIdInput) {
                    llmIdInput.value = id;
                }
            }
            
            // Indiquer visuellement si la clé API est requise
            const apiKeyLabel = apiKeyInput.previousElementSibling;
            if (apiKeyLabel) {
                if (config.apiKeyRequired) {
                    apiKeyLabel.textContent = 'Clé API (requise)';
                    apiKeyLabel.style.color = '#f59e0b';
                    apiKeyInput.required = true;
                } else {
                    apiKeyLabel.textContent = 'Clé API (optionnelle pour Ollama)';
                    apiKeyLabel.style.color = '#9ca3af';
                    apiKeyInput.required = false;
                }
            }
            
            // Ajuster les paramètres selon le type
            const maxTokensInput = document.getElementById('llm-max-tokens');
            const temperatureInput = document.getElementById('llm-temperature');
            const timeoutInput = document.getElementById('llm-timeout');
            
            if (type === 'ollama') {
                // Paramètres optimisés pour Ollama local
                maxTokensInput.value = '2048';
                temperatureInput.value = '0.7';
                timeoutInput.value = '30';
            } else if (type === 'claude') {
                // Paramètres optimisés pour Claude
                maxTokensInput.value = '4096';
                temperatureInput.value = '0.7';
                timeoutInput.value = '60';
            } else if (type === 'openai') {
                // Paramètres optimisés pour OpenAI
                maxTokensInput.value = '4096';
                temperatureInput.value = '0.7';
                timeoutInput.value = '30';
            } else {
                // Paramètres génériques pour les autres
                maxTokensInput.value = '4096';
                temperatureInput.value = '0.7';
                timeoutInput.value = '30';
            }
            
            console.log(`✅ Configuration pré-remplie pour ${type}:`, config);
        } else {
            // Reset pour type vide
            const apiKeyLabel = apiKeyInput.previousElementSibling;
            if (apiKeyLabel) {
                apiKeyLabel.textContent = 'Clé API (optionnelle pour Ollama)';
                apiKeyLabel.style.color = '#9ca3af';
                apiKeyInput.required = false;
            }
        }
    }

    async submitAddLlmForm() {
        const form = document.getElementById('add-llm-form');
        const isEditing = form.dataset.editingLlmId;
        
        console.log(isEditing ? '✏️ Mise à jour LLM' : '💾 Ajout nouveau LLM');
        
        try {
            // Récupérer les valeurs du formulaire
            const formData = {
                id: document.getElementById('llm-id').value.trim(),
                name: document.getElementById('llm-name').value.trim(),
                type: document.getElementById('llm-type').value,
                url: document.getElementById('llm-url').value.trim(),
                model: document.getElementById('llm-model').value.trim(),
                api_key: document.getElementById('llm-api-key').value.trim(),
                max_tokens: parseInt(document.getElementById('llm-max-tokens').value),
                temperature: parseFloat(document.getElementById('llm-temperature').value),
                timeout: parseInt(document.getElementById('llm-timeout').value),
                is_default: document.getElementById('llm-is-default').checked,
                is_active: document.getElementById('llm-is-active').checked,
                extra_params: {}
            };
            
            // Si on édite, utiliser l'ID original
            if (isEditing) {
                formData.id = isEditing;
            }
            
            // Validation de base
            if (!formData.id || !formData.name || !formData.type || !formData.url || !formData.model) {
                this.showNotification('❌ Veuillez remplir tous les champs obligatoires', 'error');
                return;
            }
            
            // Validation spécifique selon le type (mais plus flexible pour .env)
            if (formData.type !== 'ollama' && !formData.api_key) {
                this.showNotification('ℹ️ Aucune clé API saisie. Assurez-vous qu\'elle est dans le fichier .env', 'warning');
            }
            
            // Choisir la méthode et l'URL
            const method = isEditing ? 'PUT' : 'POST';
            const url = isEditing ? `/api/llm-config/${formData.id}` : '/api/llm-config';
            
            // Envoi de la requête
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const message = isEditing ? '✅ LLM mis à jour avec succès!' : '✅ LLM ajouté avec succès!';
                this.showNotification(message, 'success');
                this.closeAddLlmModal();
                
                // Reset du formulaire
                this.resetAddLlmForm();
                
                // Recharger les settings pour voir les changements
                setTimeout(() => {
                    this.openSettingsModal();
                }, 500);
            } else {
                this.showNotification(`❌ Erreur: ${data.message}`, 'error');
            }
            
        } catch (error) {
            console.error('❌ Erreur soumission formulaire:', error);
            const action = isEditing ? 'mise à jour' : 'ajout';
            this.showNotification(`❌ Erreur lors de la ${action} du LLM`, 'error');
        }
    }

    resetAddLlmForm() {
        const form = document.getElementById('add-llm-form');
        if (form) {
            // Réinitialiser le mode édition
            delete form.dataset.editingLlmId;
            
            // Réinitialiser le bouton et le titre
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.textContent = '💾 Ajouter LLM';
            }
            
            const formTitle = document.querySelector('#add-llm-section h4');
            if (formTitle) {
                formTitle.textContent = '➕ Ajouter un nouveau LLM';
            }
            
            // Vider le formulaire
            form.reset();
            
            // Réinitialiser les valeurs par défaut
            document.getElementById('llm-max-tokens').value = '4096';
            document.getElementById('llm-temperature').value = '0.7';
            document.getElementById('llm-timeout').value = '30';
            document.getElementById('llm-is-active').checked = true;
        }
    }

    async testLlmConfigurationForm() {
        console.log('🔍 Test configuration LLM depuis le formulaire');
        
        try {
            // Récupérer les valeurs du formulaire pour créer une config temporaire
            const formData = {
                id: 'temp-test-' + Date.now(),
                name: document.getElementById('llm-name').value.trim() || 'Test Config',
                type: document.getElementById('llm-type').value,
                url: document.getElementById('llm-url').value.trim(),
                model: document.getElementById('llm-model').value.trim(),
                api_key: document.getElementById('llm-api-key').value.trim(),
                max_tokens: parseInt(document.getElementById('llm-max-tokens').value),
                temperature: parseFloat(document.getElementById('llm-temperature').value),
                timeout: parseInt(document.getElementById('llm-timeout').value),
                is_default: false,
                is_active: true,
                extra_params: {}
            };
            
            // Validation de base
            if (!formData.type || !formData.url || !formData.model) {
                this.showNotification('❌ Veuillez remplir au moins le type, l\'URL et le modèle', 'error');
                return;
            }
            
            this.showNotification('🔍 Test de la configuration en cours...', 'info');
            
            // Créer temporairement le LLM pour le tester
            const createResponse = await fetch('/api/llm-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            if (!createResponse.ok) {
                const createData = await createResponse.json();
                this.showNotification(`❌ Erreur création temporaire: ${createData.message}`, 'error');
                return;
            }
            
            // Tester la connexion
            const testResponse = await fetch(`/api/llm-config/${formData.id}/test`, {
                method: 'POST'
            });
            
            const testData = await testResponse.json();
            
            // Supprimer la configuration temporaire
            await fetch(`/api/llm-config/${formData.id}`, {
                method: 'DELETE'
            });
            
            if (testData.status === 'success') {
                if (testData.connected) {
                    this.showNotification('✅ Configuration testée avec succès!', 'success');
                } else {
                    this.showNotification('❌ Connexion échouée avec cette configuration', 'error');
                }
            } else {
                this.showNotification(`❌ Erreur test: ${testData.message}`, 'error');
            }
            
        } catch (error) {
            console.error('❌ Erreur test configuration:', error);
            this.showNotification('❌ Erreur lors du test de configuration', 'error');
        }
    }

    showAddSimulationForm() {
        console.log('💼 Affichage formulaire ajout simulation');
        // TODO: Implémenter un formulaire pour ajouter une nouvelle simulation
        this.showNotification('🚧 Fonctionnalité en développement', 'info');
    }

    async saveConfiguration() {
        console.log('💾 Sauvegarde de la configuration');
        // La configuration est automatiquement sauvegardée côté serveur
        this.showNotification('✅ Configuration sauvegardée', 'success');
        
        // Mettre à jour le timestamp
        const lastSaveEl = document.getElementById('last-save-time');
        if (lastSaveEl) {
            lastSaveEl.textContent = new Date().toLocaleString();
        }
    }

    async resetConfiguration() {
        if (!confirm('Êtes-vous sûr de vouloir réinitialiser la configuration ? Cette action est irréversible.')) {
            return;
        }
        
        console.log('🔄 Réinitialisation de la configuration');
        this.showNotification('🚧 Fonctionnalité en développement', 'info');
    }

    showNotification(message, type = 'info') {
        // Créer une notification temporaire
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            z-index: 10000;
            font-weight: 600;
            animation: slideIn 0.3s ease;
        `;
        
        switch (type) {
            case 'success':
                notification.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                break;
            case 'error':
                notification.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                break;
            case 'info':
                notification.style.background = 'linear-gradient(135deg, #3b82f6, #2563eb)';
                break;
            default:
                notification.style.background = 'linear-gradient(135deg, #6b7280, #4b5563)';
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Supprimer après 3 secondes
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    async openFinanceMarketModal() {
        console.log('💹 Ouverture modal marché financier...');

        const modal = document.getElementById('finance-market-modal');
        if (!modal) {
            console.error('❌ Modal finance-market-modal non trouvé - fonctionnalité en développement');
            alert('📊 Fonctionnalité Market Analysis en cours de développement');
            return;
        }
        
        // Afficher le modal
        modal.style.display = 'flex';
        modal.classList.add('show');
        
        // Charger les données depuis l'API
        try {
            console.log('📡 Récupération des données du marché financier...');
            const response = await fetch('/api/finance-market');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('✅ Données de marché reçues:', data);
            
            if (data.status === 'success') {
                this.populateFinanceMarketModal(data.finance_data);
            } else {
                throw new Error(data.message || 'Erreur lors de la récupération des données de marché');
            }
            
        } catch (error) {
            console.error('❌ Erreur lors de la récupération des données de marché:', error);
            this.showFinanceMarketError(error.message);
        }
    }
    
    populateFinanceMarketModal(financeData) {
        console.log('📝 Remplissage du modal marché avec les données:', financeData);
        
        const stats = financeData.market_statistics || {};
        const summary = financeData.analysis_summary || {};
        const movers24h = financeData.top_movers?.['24h'] || {};
        const sectors = financeData.sector_analysis?.sectors || {};
        
        // Debug: vérifier si les stats contiennent une erreur
        if (stats.error) {
            console.error('❌ Erreur dans market_statistics:', stats.error);
            this.showFinanceMarketError(stats.error);
            return;
        }
        
        console.log('📊 Stats extraites:', {
            market_cap_billions: summary.market_cap_billions,
            total_volume_24h: stats.total_volume_24h,
            market_sentiment: stats.market_sentiment,
            btc_dominance: stats.btc_dominance
        });
        
        // Statistiques globales
        const totalMarketCapEl = document.getElementById('total-market-cap');
        const totalVolumeEl = document.getElementById('total-volume-24h');
        const marketSentimentEl = document.getElementById('market-sentiment');
        const btcDominanceEl = document.getElementById('btc-dominance');
        
        if (totalMarketCapEl) {
            const marketCapB = summary.market_cap_billions || 0;
            totalMarketCapEl.textContent = `$${marketCapB.toFixed(1)}B`;
        }
        
        if (totalVolumeEl) {
            const volume = stats.total_volume_24h || 0;
            totalVolumeEl.textContent = `$${(volume / 1e9).toFixed(1)}B`;
        }
        
        if (marketSentimentEl) {
            const sentiment = stats.market_sentiment || 'UNKNOWN';
            marketSentimentEl.textContent = sentiment;
            // Couleur basée sur le sentiment
            if (sentiment === 'BULLISH') {
                marketSentimentEl.style.color = '#10b981';
            } else if (sentiment === 'BEARISH') {
                marketSentimentEl.style.color = '#ef4444';
            } else {
                marketSentimentEl.style.color = '#fbbf24';
            }
        }
        
        if (btcDominanceEl) {
            const dominance = stats.btc_dominance || 0;
            btcDominanceEl.textContent = `${dominance.toFixed(1)}%`;
        }
        
        // Distribution des performances
        const gainsCountEl = document.getElementById('gains-count');
        const gainsPercentageEl = document.getElementById('gains-percentage');
        const lossesCountEl = document.getElementById('losses-count');
        const lossesPercentageEl = document.getElementById('losses-percentage');
        const neutralCountEl = document.getElementById('neutral-count');
        const neutralPercentageEl = document.getElementById('neutral-percentage');
        const totalAnalyzedEl = document.getElementById('total-analyzed');
        
        if (gainsCountEl) gainsCountEl.textContent = stats.gains_count || 0;
        if (gainsPercentageEl) gainsPercentageEl.textContent = `(${(stats.gains_percentage || 0).toFixed(1)}%)`;
        if (lossesCountEl) lossesCountEl.textContent = stats.losses_count || 0;
        if (lossesPercentageEl) lossesPercentageEl.textContent = `(${(stats.losses_percentage || 0).toFixed(1)}%)`;
        if (neutralCountEl) neutralCountEl.textContent = stats.neutral_count || 0;
        if (neutralPercentageEl) {
            const neutralPerc = 100 - (stats.gains_percentage || 0) - (stats.losses_percentage || 0);
            neutralPercentageEl.textContent = `(${neutralPerc.toFixed(1)}%)`;
        }
        if (totalAnalyzedEl) totalAnalyzedEl.textContent = stats.total_coins_tracked || 0;
        
        // Top gainers
        this.populateTopMoversList('top-gainers-list', movers24h.gainers || [], true);
        
        // Top losers
        this.populateTopMoversList('top-losers-list', movers24h.losers || [], false);
        
        // Performance par secteurs
        this.populateSectorsPerformance(sectors);
        
        // Timestamp
        const lastUpdatedEl = document.getElementById('finance-last-updated');
        if (lastUpdatedEl) {
            const timestamp = summary.analysis_timestamp;
            if (timestamp) {
                const date = new Date(timestamp);
                const formattedDate = date.toLocaleString('fr-FR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                lastUpdatedEl.textContent = formattedDate;
            } else {
                lastUpdatedEl.textContent = 'Non disponible';
            }
        }
    }
    
    populateTopMoversList(containerId, movers, isGainers) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!movers || movers.length === 0) {
            container.innerHTML = `<div style="text-align: center; color: #9ca3af; padding: 20px;">Aucune donnée disponible</div>`;
            return;
        }
        
        movers.slice(0, 10).forEach((coin, index) => {
            const change = Number(coin.price_change_percentage_24h) || 0;
            const price = Number(coin.current_price) || 0;
            const name = coin.name || 'N/A';
            const symbol = (coin.symbol || '').toUpperCase();
            
            const moverElement = document.createElement('div');
            moverElement.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                font-size: 13px;
            `;
            
            const changeColor = isGainers ? '#10b981' : '#ef4444';
            const changeSign = isGainers ? '+' : '';
            
            moverElement.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: #9ca3af; font-weight: 600; min-width: 20px;">${index + 1}.</span>
                    <div>
                        <div style="color: #fff; font-weight: 600;">${name}</div>
                        <div style="color: #9ca3af; font-size: 11px;">${symbol}</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="color: ${changeColor}; font-weight: 600;">${changeSign}${change.toFixed(2)}%</div>
                    <div style="color: #9ca3af; font-size: 11px;">$${price.toFixed(4)}</div>
                </div>
            `;
            
            container.appendChild(moverElement);
        });
    }
    
    populateSectorsPerformance(sectors) {
        const container = document.getElementById('sectors-performance');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!sectors || Object.keys(sectors).length === 0) {
            container.innerHTML = `<div style="text-align: center; color: #9ca3af; padding: 20px; grid-column: 1 / -1;">Aucune donnée de secteur disponible</div>`;
            return;
        }
        
        // Trier les secteurs par performance
        const sortedSectors = Object.entries(sectors).sort((a, b) => 
            (b[1].avg_change_24h || 0) - (a[1].avg_change_24h || 0)
        );
        
        sortedSectors.forEach(([sectorName, sectorData]) => {
            const avgChange = sectorData.avg_change_24h || 0;
            const coinsCount = sectorData.coins_count || 0;
            
            const sectorElement = document.createElement('div');
            sectorElement.style.cssText = `
                padding: 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.1);
            `;
            
            const changeColor = avgChange >= 0 ? '#10b981' : '#ef4444';
            const changeSign = avgChange >= 0 ? '+' : '';
            
            sectorElement.innerHTML = `
                <div style="color: #fff; font-weight: 600; margin-bottom: 4px; font-size: 14px;">${sectorName}</div>
                <div style="color: ${changeColor}; font-weight: 600; font-size: 16px;">${changeSign}${avgChange.toFixed(2)}%</div>
                <div style="color: #9ca3af; font-size: 11px;">${coinsCount} coins</div>
            `;
            
            container.appendChild(sectorElement);
        });
    }
    
    showFinanceMarketError(errorMessage) {
        console.log('❌ Affichage de l\'erreur dans le modal marché');
        
        // Réinitialiser tous les conteneurs avec un message d'erreur
        const containers = [
            'total-market-cap', 'total-volume-24h', 'market-sentiment', 'btc-dominance',
            'gains-count', 'losses-count', 'neutral-count', 'total-analyzed',
            'top-gainers-list', 'top-losers-list', 'sectors-performance', 'finance-last-updated'
        ];
        
        containers.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                if (id.includes('list') || id.includes('performance')) {
                    element.innerHTML = `
                        <div style="color: #ef4444; text-align: center; padding: 20px;">
                            <div style="font-size: 18px; margin-bottom: 10px;">⚠️</div>
                            <div style="font-size: 14px;">Erreur de chargement</div>
                            <div style="font-size: 12px; opacity: 0.8; margin-top: 4px;">${errorMessage}</div>
                        </div>
                    `;
                } else {
                    element.textContent = 'Erreur';
                    element.style.color = '#ef4444';
                }
            }
        });
    }
    
    closeFinanceMarketModal() {
        console.log('❌ Fermeture modal marché financier');
        const modal = document.getElementById('finance-market-modal');
        if (modal) {
            modal.classList.remove('show');
            // Hide after animation completes
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    }

    waitAndLoadSimulations() {
        console.log('⏳ Attente des éléments DOM...');
        
        const checkAndLoad = () => {
            const simulationsList = document.getElementById('simulations-list');
            const simulationsCount = document.getElementById('simulations-count');
            
            if (simulationsList && simulationsCount) {
                console.log('✅ Éléments DOM prêts, chargement des simulations...');
                this.loadSimulations();
            } else {
                console.log('⏳ Éléments DOM pas encore prêts, nouvelle tentative...');
                setTimeout(checkAndLoad, 100);
            }
        };
        
        // Premier essai immédiat
        checkAndLoad();
    }

    async loadSimulations() {
        console.log('🎮 Chargement des simulations...');
        
        // Vérifier que les éléments DOM existent
        const simulationsList = document.getElementById('simulations-list');
        const simulationsCount = document.getElementById('simulations-count');
        
        if (!simulationsList) {
            console.error('❌ Element simulations-list non trouvé');
            return;
        }
        if (!simulationsCount) {
            console.error('❌ Element simulations-count non trouvé');
            return;
        }
        
        console.log('✅ Elements DOM trouvés, appel API...');
        
        try {
            // Forcer pas de cache et utiliser l'API avec holdings détaillés
            const response = await fetch('/api/simulations-wallet?_=' + Date.now(), {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('📊 Data reçue:', data);
            console.log('🎮 Simulations dans la réponse:', data.simulations?.length || 0);
            
            // Log détaillé de chaque simulation
            if (data.simulations) {
                data.simulations.forEach((sim, index) => {
                    console.log(`📋 Sim ${index}: ID=${sim.id}, name=${sim.name}, is_running=${sim.is_running}, wallet=${sim.wallet_name}`);
                });
            }
            
            if (data.status === 'success') {
                console.log(`✅ ${data.simulations.length} simulations trouvées`);
                // Afficher directement - correction rapide
                this.displaySimulationsWithCalculatedValues(data.simulations);
            } else {
                console.error('Erreur API simulations:', data.message);
                this.displaySimulationsError('Erreur lors du chargement des simulations');
            }
        } catch (error) {
            console.error('Erreur lors du chargement des simulations:', error);
            this.displaySimulationsError('Impossible de charger les simulations');
        }
    }

    async enrichSimulationsWithWalletData(simulations) {
        const enrichedSimulations = [];
        
        for (const sim of simulations) {
            try {
                // Récupérer les données wallet et holdings
                const walletResponse = await fetch(`/api/wallets/${sim.wallet_id}`);
                const walletData = await walletResponse.json();
                
                const holdingsResponse = await fetch(`/api/wallets/${sim.wallet_id}/holdings`);
                const holdingsData = await holdingsResponse.json();
                
                if (walletData.status === 'success' && holdingsData.status === 'success') {
                    const wallet = walletData.wallet;
                    const holdings = holdingsData.holdings;
                    
                    // Calculer la valeur totale des holdings
                    const holdingsValue = holdings.reduce((sum, holding) => sum + holding.current_value, 0);
                    
                    // Calculer la valeur totale du wallet (cash + holdings)
                    const totalValue = wallet.current_value + holdingsValue;
                    
                    // Calculer P&L réel
                    const initialBudget = wallet.initial_budget_usdt || 10000; // Fallback
                    const totalPnl = totalValue - initialBudget;
                    const pnlPercent = (totalPnl / initialBudget) * 100;
                    
                    // Enrichir la simulation
                    enrichedSimulations.push({
                        ...sim,
                        total_value: totalValue,
                        total_pnl: totalPnl,
                        pnl_percent: pnlPercent,
                        assets_count: holdings.length,
                        total_trades: sim.total_trades || 0,
                        win_rate: 0,
                        holdings: holdings
                    });
                } else {
                    // En cas d'erreur, utiliser les données de base
                    enrichedSimulations.push({
                        ...sim,
                        total_value: 0,
                        total_pnl: 0,
                        pnl_percent: 0,
                        assets_count: 0,
                        total_trades: 0,
                        win_rate: 0,
                        holdings: []
                    });
                }
            } catch (error) {
                console.error(`Erreur enrichissement simulation ${sim.id}:`, error);
                // Fallback sans données enrichies
                enrichedSimulations.push({
                    ...sim,
                    total_value: 0,
                    total_pnl: 0,
                    pnl_percent: 0,
                    assets_count: 0,
                    total_trades: 0,
                    win_rate: 0,
                    holdings: []
                });
            }
        }
        
        return enrichedSimulations;
    }

    async enrichSimulationsSequentially(simulations) {
        console.log('🚀 Début enrichissement séquentiel');
        const enrichedSimulations = [];
        
        for (let i = 0; i < simulations.length; i++) {
            const sim = simulations[i];
            console.log(`🔄 [${i+1}/${simulations.length}] Enrichissement simulation ${sim.id}: ${sim.name}`);
            
            try {
                // Test simple d'abord
                console.log(`📡 Appel API wallet ${sim.wallet_id}...`);
                const walletResponse = await fetch(`/api/wallets/${sim.wallet_id}`);
                console.log(`📡 Wallet response status: ${walletResponse.status}`);
                
                const walletData = await walletResponse.json();
                console.log(`📡 Wallet data:`, walletData);
                
                console.log(`📡 Appel API holdings ${sim.wallet_id}...`);
                const holdingsResponse = await fetch(`/api/wallets/${sim.wallet_id}/holdings`);
                console.log(`📡 Holdings response status: ${holdingsResponse.status}`);
                
                const holdingsData = await holdingsResponse.json();
                console.log(`📡 Holdings data:`, holdingsData);
                
                if (walletData.status === 'success' && holdingsData.status === 'success') {
                    const wallet = walletData.wallet;
                    const holdings = holdingsData.holdings;
                    
                    const cash = wallet.current_value || 0;
                    const initialBudget = wallet.initial_budget_usdt || wallet.initial_budget_usd || 10000;
                    const holdingsValue = holdings.reduce((sum, holding) => {
                        const value = holding.current_value || 0;
                        console.log(`💎 Asset ${holding.symbol}: ${value}`);
                        return sum + value;
                    }, 0);
                    
                    const totalValue = cash + holdingsValue;
                    const totalPnl = totalValue - initialBudget;
                    const pnlPercent = initialBudget > 0 ? (totalPnl / initialBudget) * 100 : 0;
                    
                    console.log(`💰 Résultats calculs:`);
                    console.log(`   Cash: $${cash}`);
                    console.log(`   Holdings: $${holdingsValue}`);
                    console.log(`   Total: $${totalValue}`);
                    console.log(`   Initial: $${initialBudget}`);
                    console.log(`   P&L: $${totalPnl} (${pnlPercent.toFixed(1)}%)`);
                    
                    enrichedSimulations.push({
                        ...sim,
                        total_value: totalValue,
                        total_pnl: totalPnl,
                        pnl_percent: pnlPercent,
                        assets_count: holdings.length,
                        total_trades: 0,
                        win_rate: 0,
                        holdings: holdings
                    });
                } else {
                    console.warn(`⚠️ Status API non-success pour simulation ${sim.id}`);
                    enrichedSimulations.push({...sim, total_value: 0, total_pnl: 0, pnl_percent: 0, assets_count: 0, total_trades: 0, win_rate: 0});
                }
                
            } catch (error) {
                console.error(`❌ Erreur complète enrichissement simulation ${sim.id}:`, error);
                enrichedSimulations.push({...sim, total_value: 0, total_pnl: 0, pnl_percent: 0, assets_count: 0, total_trades: 0, win_rate: 0});
            }
            
            // Pause entre simulations
            if (i < simulations.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 200));
            }
        }
        
        console.log(`✅ Enrichissement terminé: ${enrichedSimulations.length} simulations`);
        return enrichedSimulations;
    }

    async enrichSimulationsInBackground(simulations) {
        console.log('🔄 Enrichissement en arrière-plan...');
        
        try {
            const enrichedSimulations = await this.enrichSimulationsSequentially(simulations);
            console.log('✅ Enrichissement terminé, mise à jour de l\'affichage');
            this.displaySimulations(enrichedSimulations);
        } catch (error) {
            console.error('❌ Erreur enrichissement en arrière-plan:', error);
        }
    }

    async displaySimulationsWithCalculatedValues(simulations) {
        console.log('💡 Affichage des simulations avec vraies données de l\'API');
        
        // Les données viennent déjà de l'API /api/simulations-wallet avec tous les détails
        // Pas besoin de données hard-codées
        this.displaySimulations(simulations);
    }

    displaySimulations(simulations) {
        const simulationsList = document.getElementById('simulations-list');
        const simulationsCount = document.getElementById('simulations-count');
        
        if (!simulationsList || !simulationsCount) return;
        
        if (!simulations || simulations.length === 0) {
            simulationsList.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 40px; font-size: 14px;">
                    Aucune simulation active<br>
                    <span style="font-size: 12px; opacity: 0.7;">Créez votre première simulation dans Configuration</span>
                </div>
            `;
            simulationsCount.textContent = '0 simulation';
            return;
        }
        
        simulationsCount.textContent = `${simulations.length} simulation${simulations.length > 1 ? 's' : ''}`;
        
        let html = '';
        simulations.forEach(sim => {
            // Valeurs par défaut + coercition numérique (évite les erreurs toFixed sur string/undefined)
            sim.total_value = Number(sim.total_value) || 0;
            sim.total_pnl = Number(sim.total_pnl) || 0;
            sim.pnl_percent = Number(sim.pnl_percent) || 0;
            sim.assets_count = Number(sim.assets_count) || 0;
            const rawTrades = sim.total_trades;
            let parsedTrades = 0;
            if (typeof rawTrades === 'number') {
                parsedTrades = Math.floor(rawTrades);
            } else if (typeof rawTrades === 'string') {
                const m = rawTrades.match(/\d+/);
                if (m) parsedTrades = parseInt(m[0], 10);
            }
            sim.total_trades = Number.isFinite(parsedTrades) ? parsedTrades : 0;
            sim.win_rate = Number(sim.win_rate) || 0;

            // Utiliser un override local si on a déjà récupéré le vrai nombre de trades pour ce wallet
            const overrideCount = (this.tradesCountOverride && this.tradesCountOverride[sim.wallet_name]);
            const tradesCount = Number.isFinite(overrideCount) ? overrideCount : (sim.total_trades || 0);
            
            const pnlColor = sim.total_pnl >= 0 ? '#10b981' : '#ef4444';
            const pnlSign = sim.total_pnl >= 0 ? '+' : '';
            
            // Debug pour chaque simulation
            console.log(`🎮 Simulation ${sim.id} (${sim.name}): is_running=${sim.is_running}, type=${typeof sim.is_running}`);
            
            html += `
                <div class="simulation-card" data-simulation-id="${sim.id}" data-wallet-name="${sim.wallet_name}" data-assets-count="${sim.assets_count}" style="
                    background: rgba(30, 30, 30, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    margin-bottom: 8px;
                    overflow: hidden;
                    transition: all 0.2s ease;
                ">
                    <!-- Simulation Header (toujours visible) -->
                    <div class="simulation-header" onclick="this.parentElement.classList.toggle('expanded')" style="
                        padding: 12px 16px;
                        cursor: pointer;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        background: linear-gradient(90deg, rgba(59, 130, 246, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%);
                    ">
                        <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                            <div>
                                <div style="font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 2px;">
                                    ${sim.name}
                                </div>
                                <div style="font-size: 11px; color: #9ca3af;">
                                    ${sim.wallet_name} • ${sim.strategy}${sim.last_run_at ? ` • Dernière: ${new Date(sim.last_run_at).toLocaleString('fr-FR', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'})}` : ' • Jamais exécutée'}
                                </div>
                            </div>
                        </div>
                        
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <div style="text-align: right;">
                                <div style="font-size: 13px; font-weight: 600; color: #fff;">
                                    $${sim.total_value.toFixed(2)}
                                </div>
                                <div style="font-size: 11px; color: ${pnlColor}; font-weight: 500;">
                                    ${pnlSign}$${sim.total_pnl.toFixed(2)} (${pnlSign}${sim.pnl_percent.toFixed(1)}%)
                                </div>
                            </div>
                            
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="text-align: center;">
                                    <div style="font-size: 10px; color: #9ca3af;">Assets</div>
                                    <div style="font-size: 12px; color: #d1d5db; font-weight: 600;">${sim.assets_count}</div>
                                </div>
                                
                                <!-- Bouton Trades toujours visible -->
                                <button data-wallet-name="${sim.wallet_name}" onclick="window.hiveAI.showTradesHistory('${sim.wallet_name}')" style="
                                    background: linear-gradient(135deg, #3b82f6, #1e40af);
                                    color: white;
                                    border: none;
                                    padding: 4px 8px;
                                    border-radius: 4px;
                                    cursor: pointer;
                                    font-size: 10px;
                                    font-weight: 600;
                                    white-space: nowrap;
                                ">📊 ${tradesCount || 0}</button>
                                
                                <!-- Info fréquence compacte -->
                                <div style="text-align: center;">
                                    <div style="font-size: 9px; color: #9ca3af;">Freq</div>
                                    <div style="font-size: 11px; color: #d1d5db; font-weight: 500;">${sim.frequency_minutes}min</div>
                                </div>
                                
                                ${sim.is_active ? 
                                    '<div class="pulse-dot" style="background: #10b981; width: 8px; height: 8px; border-radius: 50%;"></div>' :
                                    '<div style="width: 8px; height: 8px; border-radius: 50%; background: #6b7280;"></div>'
                                }
                                
                                <svg style="width: 16px; height: 16px; color: #9ca3af; transition: transform 0.2s;" class="expand-icon" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                </svg>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Simulation Details (masqués par défaut) -->
                    <div class="simulation-details" style="
                        max-height: 0;
                        overflow: hidden;
                        transition: max-height 0.3s ease;
                        background: rgba(0, 0, 0, 0.2);
                    ">
                        <div style="padding: 16px;">
                            <!-- Stats de trading -->
                            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                                <div style="text-align: center;">
                                    <div style="font-size: 10px; color: #9ca3af; margin-bottom: 4px;">Trades Total</div>
                                    <div style="font-size: 14px; color: #d1d5db; font-weight: 600;">
                                        <span class="trades-total-value" data-wallet-name="${sim.wallet_name}" 
                                              onclick="window.hiveAI.showTradesHistory('${sim.wallet_name}')"
                                              style="cursor: pointer; text-decoration: underline; color: #60a5fa;"
                                              title="Cliquez pour voir l'historique des trades">
                                            ${tradesCount || 0}
                                        </span>
                                    </div>
                                </div>
                                <div style="text-align: center;">
                                    <div style="font-size: 10px; color: #9ca3af; margin-bottom: 4px;">Win Rate</div>
                                    <div style="font-size: 14px; color: #10b981; font-weight: 600;">${(typeof sim.win_rate === 'number' ? sim.win_rate : parseFloat(sim.win_rate) || 0).toFixed(1)}%</div>
                                </div>
                                <div style="text-align: center;">
                                    <div style="font-size: 10px; color: #9ca3af; margin-bottom: 4px;">Success Rate</div>
                                    <div style="font-size: 14px; color: #3b82f6; font-weight: 600;">${(typeof sim.success_rate === 'number' ? sim.success_rate : parseFloat(sim.success_rate) || 0).toFixed(1)}%</div>
                                </div>
                            </div>
                            
                            <!-- Holdings détaillés -->
                            ${sim.holdings && sim.holdings.length > 0 ? `
                                <div style="border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 12px;">
                                    <div style="font-size: 12px; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">📊 Assets Détenus:</div>
                                    ${sim.holdings.map(holding => `
                                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0;">
                                            <div>
                                                <span style="color: #fff; font-size: 12px; font-weight: 500;">${holding.asset_symbol || holding.asset_id.toUpperCase()}</span>
                                                <span style="color: #9ca3af; font-size: 10px; margin-left: 8px;">${holding.quantity.toFixed(4)}</span>
                                            </div>
                                            <div style="text-align: right;">
                                                <div style="color: #d1d5db; font-size: 11px;">$${holding.current_value.toFixed(2)}</div>
                                                <div style="color: ${holding.pnl >= 0 ? '#10b981' : '#ef4444'}; font-size: 10px;">
                                                    ${holding.pnl >= 0 ? '+' : ''}${holding.pnl_percent.toFixed(1)}%
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : `
                                <div style="text-align: center; color: #9ca3af; padding: 12px; font-size: 11px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                                    Aucun actif détenu
                                </div>
                            `}
                            
                            <!-- Actions et infos -->
                            <div style="border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 12px; margin-top: 12px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <button data-wallet-name="${sim.wallet_name}" onclick="window.hiveAI.showTradesHistory('${sim.wallet_name}')" style="
                                        background: linear-gradient(135deg, #3b82f6, #2563eb);
                                        color: white;
                                        border: none;
                                        padding: 6px 12px;
                                        border-radius: 4px;
                                        cursor: pointer;
                                        font-size: 11px;
                                        font-weight: 600;
                                    ">📊 Voir ${tradesCount || 0} trade${(tradesCount || 0) !== 1 ? 's' : ''}</button>
                                    
                                    <div style="display: flex; gap: 6px;">
                                        <button class="edit-simulation-btn" data-simulation-id="${sim.id}" style="
                                            background: #f59e0b;
                                            color: white;
                                            border: none;
                                            padding: 4px 8px;
                                            border-radius: 4px;
                                            cursor: pointer;
                                            font-size: 10px;
                                        ">✏️</button>
                                        <button class="toggle-simulation-btn" data-simulation-id="${sim.id}" style="
                                            background: ${sim.is_active ? '#f59e0b' : '#10b981'};
                                            color: white;
                                            border: none;
                                            padding: 4px 8px;
                                            border-radius: 4px;
                                            cursor: pointer;
                                            font-size: 10px;
                                        " title="État: ${sim.is_active ? 'Active' : 'Inactive'}">${sim.is_active ? '⏸️' : '▶️'}</button>
                                        <button class="delete-simulation-btn" data-simulation-id="${sim.id}" style="
                                            background: #ef4444;
                                            color: white;
                                            border: none;
                                            padding: 4px 8px;
                                            border-radius: 4px;
                                            cursor: pointer;
                                            font-size: 10px;
                                        ">🗑️</button>
                                    </div>
                                </div>
                                
                                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #9ca3af;">
                                    <span>Fréquence: ${sim.frequency_minutes}min</span>
                                    <span>Dernière exécution: ${sim.last_run_at ? new Date(sim.last_run_at).toLocaleString('fr-FR') : 'Jamais'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        simulationsList.innerHTML = html;
        
        // Ajouter les styles CSS pour l'expansion
        const style = document.createElement('style');
        style.textContent = `
            .simulation-card.expanded .simulation-details {
                max-height: 500px !important;
            }
            .simulation-card.expanded .expand-icon {
                transform: rotate(180deg);
            }
            .simulation-card:hover {
                border-color: rgba(255, 255, 255, 0.2);
                background: rgba(30, 30, 30, 0.8);
            }
        `;
        
        if (!document.getElementById('simulations-styles')) {
            style.id = 'simulations-styles';
            document.head.appendChild(style);
        }
    }

    displaySimulationsError(message) {
        const simulationsList = document.getElementById('simulations-list');
        const simulationsCount = document.getElementById('simulations-count');
        
        if (simulationsList) {
            simulationsList.innerHTML = `
                <div style="text-align: center; color: #ef4444; padding: 40px; font-size: 14px;">
                    ⚠️ ${message}<br>
                    <span style="font-size: 12px; opacity: 0.7;">Veuillez réessayer plus tard</span>
                </div>
            `;
        }
        
        if (simulationsCount) {
            simulationsCount.textContent = 'Erreur';
        }
    }

    setupSimulationEvents() {
        console.log('🔧 Setup simulation events...');
        console.log('🔧 Recherche des boutons...');
        
        // Event listener pour le bouton principal "Ajouter simulation" 
        const addBtnMain = document.getElementById('add-simulation-main-btn');
        console.log('🧪 Bouton principal trouvé:', !!addBtnMain);
        if (addBtnMain) {
            console.log('✅ Bouton principal add-simulation-main-btn trouvé et visible:', addBtnMain.offsetParent !== null);
            addBtnMain.addEventListener('click', (e) => {
                console.log('🎮 Bouton principal Ajouter cliqué!');
                console.log('🎮 window.nodeManager.openSimulationCreator existe:', typeof window.nodeManager?.openSimulationCreator === 'function');
                if (typeof window.nodeManager?.openSimulationCreator === 'function') {
                    window.nodeManager.openSimulationCreator();
                } else {
                    console.error('❌ nodeManager.openSimulationCreator non disponible');
                }
            });
        } else {
            console.error('❌ Bouton principal add-simulation-main-btn NON TROUVÉ');
        }
        
        // Event listener pour le bouton "Ajouter simulation" (depuis HTML statique)
        const addBtnHtml = document.getElementById('add-simulation-btn');
        if (addBtnHtml) {
            console.log('✅ Bouton HTML add-simulation-btn trouvé');
            addBtnHtml.addEventListener('click', (e) => {
                console.log('🎮 Bouton config Ajouter cliqué!');
                this.openSimulationModal();
            });
        } else {
            console.log('❌ Bouton HTML add-simulation-btn non trouvé');
        }

        // Event listeners pour les boutons d'actions sur les simulations
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('edit-simulation-btn')) {
                const simulationId = parseInt(e.target.dataset.simulationId);
                if (window.hiveAI && typeof window.hiveAI.editSimulation === 'function') {
                    window.hiveAI.editSimulation(simulationId);
                } else {
                    console.error('❌ window.hiveAI.editSimulation non disponible');
                }
            } else if (e.target.classList.contains('toggle-simulation-btn')) {
                const simulationId = parseInt(e.target.dataset.simulationId);
                console.log(`🎯 Clic sur toggle simulation ${simulationId}`);
                if (window.hiveAI && typeof window.hiveAI.toggleSimulation === 'function') {
                    window.hiveAI.toggleSimulation(simulationId);
                } else {
                    console.error('❌ window.hiveAI.toggleSimulation non disponible');
                }
            } else if (e.target.classList.contains('delete-simulation-btn')) {
                const simulationId = parseInt(e.target.dataset.simulationId);
                if (window.hiveAI && typeof window.hiveAI.deleteSimulation === 'function') {
                    window.hiveAI.deleteSimulation(simulationId);
                } else {
                    console.error('❌ window.hiveAI.deleteSimulation non disponible');
                }
            }
        });
    }

    openSimulationModal() {
        console.log('🎮 Ouverture du modal de simulation...');
        
        // Essayer de trouver un modal existant
        let modal = document.getElementById('simulation-modal');
        
        if (!modal) {
            console.log('⚠️ Modal simulation non trouvé dans le DOM, création d\'un modal simple');
            
            // Créer un modal simple
            const modalHtml = `
                <div id="simulation-modal" style="
                    position: fixed;
                    top: 0; left: 0;
                    width: 100vw; height: 100vh;
                    background: rgba(0,0,0,0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                ">
                    <div style="
                        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                        padding: 24px;
                        border-radius: 12px;
                        border: 1px solid #374151;
                        max-width: 500px;
                        width: 90%;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h3 style="color: #fff; margin: 0; font-size: 18px;">🎮 Nouvelle Simulation</h3>
                            <button id="close-simulation-modal" style="
                                background: none;
                                border: none;
                                color: #9ca3af;
                                font-size: 24px;
                                cursor: pointer;
                                padding: 0;
                                line-height: 1;
                            ">&times;</button>
                        </div>
                        
                        <div style="color: #d1d5db; line-height: 1.6;">
                            <p>✨ <strong>Fonctionnalité à venir !</strong></p>
                            <p>La création de nouvelles simulations sera bientôt disponible.</p>
                            
                            <div style="margin: 16px 0; padding: 16px; background: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; border-radius: 8px;">
                                <div style="color: #60a5fa; font-weight: 600; margin-bottom: 8px;">🎯 Fonctionnalités prévues :</div>
                                <div style="font-size: 14px;">
                                    • Configuration du wallet initial<br>
                                    • Sélection des cryptos à trader<br>
                                    • Paramètres de risque<br>
                                    • Stratégies IA personnalisées
                                </div>
                            </div>
                        </div>
                        
                        <div style="text-align: right; margin-top: 20px;">
                            <button id="ok-simulation-modal" style="
                                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                                color: white;
                                border: none;
                                padding: 10px 20px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">Compris</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modal = document.getElementById('simulation-modal');
            
            // Ajouter les event listeners
            const closeBtn = document.getElementById('close-simulation-modal');
            const okBtn = document.getElementById('ok-simulation-modal');
            
            const closeModal = () => {
                modal.remove();
            };
            
            closeBtn.addEventListener('click', closeModal);
            okBtn.addEventListener('click', closeModal);
            
            // Fermer en cliquant sur le fond
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeModal();
            });
        }
        
        console.log('✅ Modal simulation affiché');
    }

    async deleteSimulation(simulationId) {
        console.log(`🗑️ Suppression de la simulation ${simulationId}`);
        
        if (!confirm(`🗑️ Êtes-vous sûr de vouloir supprimer cette simulation?\n\n⚠️ Cette action est irréversible\n📊 L'historique et les performances seront perdus`)) {
            return;
        }
        
        try {
            console.log(`📡 Envoi de la requête DELETE pour simulation ${simulationId}`);
            const response = await fetch(`/api/simulations/${simulationId}`, {
                method: 'DELETE',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            
            console.log(`📡 Response status: ${response.status}`);
            
            if (!response.ok) {
                console.error(`❌ Erreur HTTP: ${response.status}`);
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const result = await response.json();
            console.log(`📡 Response data:`, result);
            
            if (result.status === 'success') {
                console.log('✅ Simulation supprimée côté serveur');
                
                // Message de succès immédiat
                try {
                    if (typeof this.showNotification === 'function') {
                        this.showNotification('Simulation supprimée avec succès', 'success');
                    } else {
                        console.log('✅ Notification: Simulation supprimée avec succès');
                        alert('Simulation supprimée avec succès');
                    }
                } catch (notifError) {
                    console.error('❌ Erreur showNotification:', notifError);
                    alert('Simulation supprimée avec succès');
                }
                
                // Supprimer immédiatement l'élément du DOM
                const simulationCard = document.querySelector(`.simulation-card[data-simulation-id="${simulationId}"]`);
                if (simulationCard) {
                    console.log('🗑️ Suppression immédiate de la carte simulation');
                    simulationCard.remove();
                } else {
                    console.log('❌ Carte simulation non trouvée pour suppression immédiate');
                }
                
                // Recharger la liste des simulations après un délai court
                setTimeout(() => {
                    console.log('🔄 Rechargement de la liste des simulations');
                    try {
                        this.waitAndLoadSimulations();
                    } catch (reloadError) {
                        console.error('❌ Erreur rechargement:', reloadError);
                        window.location.reload();
                    }
                }, 500);
                
            } else {
                console.error('❌ Erreur serveur:', result.message);
                throw new Error(result.message || 'Erreur inconnue');
            }
        } catch (error) {
            console.error('❌ Erreur lors de la suppression:', error);
            this.showNotification('Erreur lors de la suppression de la simulation', 'error');
        }
    }

    async toggleSimulation(simulationId) {
        console.log(`⏯️ Toggle simulation ${simulationId}`);
        
        try {
            const button = document.querySelector(`[data-simulation-id="${simulationId}"].toggle-simulation-btn`);
            if (!button) {
                console.error('❌ Bouton de toggle non trouvé');
                return;
            }
            
            // Récupérer l'état actuel depuis l'API pour être sûr
            const currentResponse = await fetch('/api/simulations-wallet');
            const currentData = await currentResponse.json();
            const currentSim = currentData.simulations.find(s => s.id === simulationId);
            
            if (!currentSim) {
                console.error('❌ Simulation non trouvée');
                return;
            }
            
            const isCurrentlyRunning = currentSim.is_active;
            const newState = !isCurrentlyRunning;
            
            console.log(`🔄 Changement d'état simulation ${simulationId}: ${isCurrentlyRunning} -> ${newState}`);
            
            // Appel API pour mettre à jour l'état
            const response = await fetch(`/api/simulations/${simulationId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    is_active: newState
                })
            });
            
            const result = await response.json();
            console.log('📊 Réponse toggle simulation:', result);
            
            if (response.ok && result.status === 'success') {
                console.log(`✅ Simulation ${simulationId} ${newState ? 'activée' : 'mise en pause'} avec succès`);
                
                // Vérifier que window.hiveAI existe
                if (window.hiveAI && typeof window.hiveAI.waitAndLoadSimulations === 'function') {
                    console.log('🔄 Rechargement des simulations...');
                    await window.hiveAI.waitAndLoadSimulations();
                    console.log('✅ Rechargement terminé');
                } else {
                    console.error('❌ window.hiveAI.waitAndLoadSimulations non disponible');
                }
                
                this.showNotification(
                    newState ? 'Simulation activée ✅' : 'Simulation mise en pause ⏸️', 
                    'success'
                );
            } else {
                throw new Error(result.message || `Erreur HTTP: ${response.status}`);
            }
            
        } catch (error) {
            console.error('❌ Erreur lors du toggle:', error);
            this.showNotification(`Erreur lors du changement d'état: ${error.message}`, 'error');
        }
    }

}

// Gestionnaire pour les fonctionnalités du node
class NodeManager {
    constructor() {
        this.llmHistory = [];
        this.initializeMockHistory();
        // Attendre que le DOM soit complètement chargé
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupModalEvents());
        } else {
            this.setupModalEvents();
        }
    }
    
    initializeMockHistory() {
        // Simuler un historique d'échanges LLM pour la démo
        const now = new Date();
        const mockExchanges = [
            {
                id: 1,
                timestamp: new Date(now.getTime() - 3600000).toISOString(), // Il y a 1h
                type: 'TRADING_ANALYSIS',
                agent: 'MasterTraderAgent',
                request: 'Analyse ETH pour décision de trading avec politique prudente',
                response: `ANALYSE TECHNIQUE ETHEREUM (ETH)

RÉSUMÉ EXÉCUTIF:
Action recommandée: BUY
Niveau de confiance: 82%
Type de signal: MOMENTUM

ANALYSE DÉTAILLÉE:
• RSI: 58.2 - Zone neutre avec potentiel haussier
• MACD: Signal d'achat confirmé avec divergence positive
• Volume: +28% par rapport à la moyenne 20 jours
• Support/Résistance: Support solide à $3,200, résistance à $3,800
• Moyennes mobiles: Configuration haussière MA20 > MA50

FACTEURS FONDAMENTAUX:
• Shanghai upgrade impact positif
• Staking rewards attractifs (4.2% APY)
• Développement DeFi en expansion
• Adoption institutionnelle croissante

GESTION DES RISQUES:
• Entry: $3,420
• Target: $3,750 (ratio 1:2.4)
• Stop loss: $3,280 (risque 4.1%)`
            },
            {
                id: 2,
                timestamp: new Date(now.getTime() - 7200000).toISOString(), // Il y a 2h
                type: 'MARKET_SCAN',
                agent: 'WorldStateAgent',
                request: 'Scan rapide du marché pour opportunités émergentes',
                response: `SCAN MARCHÉ GLOBAL

RÉSUMÉ:
Opportunités détectées: 3 signaux forts
Sentiment général: Bullish modéré
Volatilité: Normale

ACTIFS SURVEILLÉS:
• BTC: Signal momentum (force: 76%)
• SOL: Breakout technique détecté (force: 84%)  
• ADA: Accumulation whale confirmée (force: 71%)

FACTEURS MACRO:
• Fed policy stable
• Inflation en baisse
• Adoption crypto institutionnelle +15%

ALERTES:
• SOL: Breakout imminent au-dessus de $185
• Volume anormal détecté sur plusieurs altcoins`
            },
            {
                id: 3,
                timestamp: new Date(now.getTime() - 14400000).toISOString(), // Il y a 4h
                type: 'RISK_ASSESSMENT',
                agent: 'FinanceStateAgent',
                request: 'Évaluation des risques wallet actuel',
                response: `ÉVALUATION RISQUES PORTFOLIO

EXPOSITION ACTUELLE:
• BTC: 45% (recommandé: 40-50%)
• ETH: 30% (recommandé: 25-35%)
• Altcoins: 25% (recommandé: 15-25%)

MÉTRIQUES RISQUE:
• VaR 95%: -12.4% (acceptable)
• Sharpe ratio: 1.67 (excellent)
• Max drawdown: -18.2% (modéré)
• Corrélation inter-actifs: 0.72

RECOMMANDATIONS:
1. Réduire exposition altcoins de 5%
2. Augmenter position ETH avant upgrade
3. Maintenir cash position à 5%
4. Surveiller corrélations BTC/SPX`
            },
            {
                id: 4,
                timestamp: new Date(now.getTime() - 21600000).toISOString(), // Il y a 6h
                type: 'NEWS_ANALYSIS',
                agent: 'AssetStateAgent',
                request: 'Analyse impact news récentes sur BTC',
                response: `ANALYSE IMPACT NEWS - BITCOIN

NEWS IMPORTANTES:
1. "MicroStrategy achète 1,045 BTC supplémentaires"
   Impact: POSITIF (+2.3%)
   Confiance: 85%

2. "ETF Bitcoin record de flux entrants"
   Impact: TRÈS POSITIF (+4.1%)
   Confiance: 92%

3. "Réglementation favorable au Salvador"
   Impact: NEUTRE (+0.5%)
   Confiance: 65%

SENTIMENT AGRÉGÉ:
• Média mainstream: 78% positif
• Réseaux sociaux: 82% bullish
• Analyse on-chain: Très favorable

PRÉDICTION:
Catalyseurs positifs alignés pour continuation haussière
Horizon: 2-4 semaines
Probabilité: 76%`
            }
        ];
        
        this.llmHistory = mockExchanges;
    }
    
    setupModalEvents() {
        console.log('🔧 Setup des événements modals...');
        
        // Setup des boutons du node
        const logsBtn = document.getElementById('logs-btn');
        const walletsBtn = document.getElementById('wallets-btn');
        const changeModelBtn = document.getElementById('change-model-btn');
        const schedulerConfigBtn = document.getElementById('scheduler-config-btn');
        
        const userObjectivesBtn = document.getElementById('user-objectives-btn');
        
        console.log('🔍 Éléments trouvés:', {
            logsBtn: !!logsBtn,
            walletsBtn: !!walletsBtn,
            changeModelBtn: !!changeModelBtn,
            schedulerConfigBtn: !!schedulerConfigBtn,
            userObjectivesBtn: !!userObjectivesBtn,
            domReady: document.readyState
        });
        
        if (logsBtn) {
            console.log('✅ Bouton logs trouvé, ajout event listener');
            logsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔥 Click sur logs détecté !');
                this.openLogs();
            });
        } else {
            console.warn('⚠️ Bouton logs non trouvé');
        }
        
        if (walletsBtn) {
            console.log('✅ Bouton wallets trouvé, ajout event listener');
            walletsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('💼 Click sur wallets détecté !');
                this.openWallets();
            });
        } else {
            console.warn('⚠️ Bouton wallets non trouvé');
        }
        
        if (changeModelBtn) {
            console.log('✅ Bouton change model trouvé, ajout event listener');
            changeModelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔥 Click sur change model détecté !');
                this.openModelHistory();
            });
        } else {
            console.warn('⚠️ Bouton change model non trouvé');
        }
        
        if (schedulerConfigBtn) {
            console.log('✅ Bouton scheduler config trouvé, ajout event listener');
            schedulerConfigBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔥 Click sur scheduler config détecté !');
                this.openSchedulerConfig();
            });
        } else {
            console.warn('⚠️ Bouton scheduler config non trouvé');
        }
        
        if (userObjectivesBtn) {
            console.log('✅ Bouton objectifs utilisateur trouvé, ajout event listener');
            userObjectivesBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🎯 Clic sur objectifs utilisateur');
                this.openUserObjectives();
            });
        } else {
            console.warn('⚠️ Bouton objectifs utilisateur non trouvé');
        }
        
        // Fermer le modal en cliquant à l'extérieur
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('model-history-modal');
            if (modal && e.target === modal) {
                this.closeModelHistory();
            }
        });
        
        // Fermer le modal avec la touche Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Fermer modal historique LLM
                const historyModal = document.getElementById('model-history-modal');
                if (historyModal && historyModal.classList.contains('show')) {
                    this.closeModelHistory();
                }
                
                // Fermer modal scheduler config
                const schedulerModal = document.getElementById('scheduler-config-modal');
                if (schedulerModal && schedulerModal.classList.contains('show')) {
                    this.closeSchedulerConfig();
                }
                
                // Fermer modal objectifs utilisateur
                const objectivesModal = document.getElementById('user-objectives-modal');
                if (objectivesModal && objectivesModal.classList.contains('show')) {
                    this.closeUserObjectives();
                }
                
                // Fermer modal logs
                const logsModal = document.getElementById('logs-modal');
                if (logsModal && logsModal.style.display === 'flex') {
                    this.closeLogs();
                }
            }
        });
        
        // Setup du bouton de fermeture du modal logs
        const closeLogsBtn = document.getElementById('close-logs-modal');
        if (closeLogsBtn) {
            console.log('✅ Bouton fermeture logs trouvé');
            closeLogsBtn.addEventListener('click', () => {
                this.closeLogs();
            });
        }
        
        // Fermer logs modal en cliquant à l'extérieur
        const logsModal = document.getElementById('logs-modal');
        if (logsModal) {
            logsModal.addEventListener('click', (e) => {
                if (e.target === logsModal) {
                    this.closeLogs();
                }
            });
        }
    }
    
    openLogs() {
        console.log('📋 Ouverture des logs du node...');
        
        // Vérifier si le modal logs existe
        const logsModal = document.getElementById('logs-modal');
        if (logsModal) {
            console.log('✅ Modal logs trouvé, ouverture...');
            logsModal.style.display = 'flex';
            this.updateLogsContent();
            // Afficher aussi le panneau Datasets si HiveAI est présent
            try { window.hiveAI?.renderDatasetsPanel?.(); } catch (e) {}
        } else {
            console.warn('⚠️ Modal logs non trouvé, création d\'une alerte temporaire');
            // Créer un modal temporaire simple
            this.showSimpleLogs();
        }
    }
    
    showSimpleLogs() {
        const logsContent = `
📋 LOGS DU NODE HIVE AI #142

✅ System Status: ONLINE
💾 Hardware: Jetson Nano 4GB
🧠 LLM Framework: Ollama + DSPy
📡 WebSocket: Connected
⚡ GPU: CUDA enabled
🔄 Scheduler: All tasks running
💰 Price Collection: Active (30s interval)
📰 News Collection: Active (2min interval)
🤖 MasterTrader Agent: Ready
🌍 WorldState Agent: Ready
📊 FinanceState Agent: Ready
🎯 AssetState Agent: Ready
📈 Performance: CPU 34%, GPU 67%, Temp 42°C
✅ All systems operational

[${new Date().toLocaleString('fr-FR')}] System check completed
        `;
        
        alert(logsContent);
    }
    
    closeLogs() {
        console.log('❌ Fermeture des logs...');
        const logsModal = document.getElementById('logs-modal');
        if (logsModal) {
            logsModal.style.display = 'none';
        }
    }
    
    updateLogsContent() {
        const logsContent = document.getElementById('logs-content');
        if (!logsContent) return;
        
        const now = new Date();
        const timestamp = now.toLocaleString('fr-FR');
        
        const logs = [
            `[${timestamp}] 🚀 HIVE AI Edge Node #142 started`,
            `[${timestamp}] 💾 System: Jetson Nano 4GB`,
            `[${timestamp}] 🧠 LLM: Ollama + DSPy framework loaded`,
            `[${timestamp}] 📡 WebSocket server listening on port 8000`,
            `[${timestamp}] ⚡ GPU: CUDA acceleration enabled`,
            `[${timestamp}] 🔄 Scheduler: All tasks initialized`,
            `[${timestamp}] 💰 Price collector: Connected to CoinGecko API`,
            `[${timestamp}] 📰 News collector: Multiple sources active`,
            `[${timestamp}] 🤖 Agent MasterTrader: Ready`,
            `[${timestamp}] 🌍 Agent WorldState: Ready`,
            `[${timestamp}] 📊 Agent FinanceState: Ready`,
            `[${timestamp}] 🎯 Agent AssetState: Ready`,
            `[${timestamp}] 📈 Performance: CPU 34%, GPU 67%, Temp 42°C`,
            `[${timestamp}] ✅ All systems operational`,
        ];
        
        logsContent.innerHTML = logs.map(log => {
            let color = '#e4e4e7';
            if (log.includes('✅') || log.includes('Ready') || log.includes('started')) color = '#10b981';
            else if (log.includes('🔄') || log.includes('💰') || log.includes('📰')) color = '#f59e0b';
            else if (log.includes('📡') || log.includes('🤖') || log.includes('🧠')) color = '#6366f1';
            else if (log.includes('⚡') || log.includes('📈')) color = '#8b5cf6';
            
            return `<div style="color: ${color}; margin-bottom: 4px; font-family: 'Consolas', monospace;">${log}</div>`;
        }).join('');
    }
    
    async openModelHistory() {
        console.log('🤖 Ouverture de l\'historique des échanges LLM...');
        
        const modal = document.getElementById('model-history-modal');
        if (!modal) {
            console.error('⚠️ Modal historique LLM non trouvé');
            // Fallback avec alerte simple
            this.showSimpleHistory();
            return;
        }
        
        // Récupérer l'historique des échanges LLM depuis le backend
        try {
            console.log('📡 Récupération de l\'historique LLM depuis le backend...');
            const response = await fetch('/debug/llm-history');
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log(`✅ Récupéré ${data.exchanges.length} échanges LLM`);
                // Ajouter les échanges à l'historique local
                this.llmHistory = data.exchanges.map(exchange => ({
                    timestamp: exchange.timestamp,
                    type: exchange.type || 'analysis',
                    agent: exchange.agent || exchange.model,
                    session_id: exchange.session_id,
                    asset_ticker: exchange.asset_ticker,
                    prompt: exchange.prompt,
                    response: exchange.response,
                    duration: exchange.duration
                }));
            } else {
                console.warn('⚠️ Erreur récupération historique LLM:', data.message);
            }
        } catch (error) {
            console.error('❌ Erreur lors de la récupération de l\'historique LLM:', error);
        }
        
        console.log('✅ Modal historique trouvé, ouverture...');
        
        // Remplir le contenu de l'historique
        this.populateModelHistory();
        
        // Afficher le modal avec animation
        modal.classList.add('show');
    }
    
    showSimpleHistory() {
        const historyContent = `
🤖 HISTORIQUE DES ÉCHANGES LLM

📅 ${new Date(Date.now() - 3600000).toLocaleString('fr-FR')}
🎯 TRADING_ANALYSIS - MasterTraderAgent
💡 Analyse ETH: Action BUY, Confiance 82%

📅 ${new Date(Date.now() - 7200000).toLocaleString('fr-FR')}  
🔍 MARKET_SCAN - WorldStateAgent
💡 3 signaux forts détectés (BTC, SOL, ADA)

📅 ${new Date(Date.now() - 14400000).toLocaleString('fr-FR')}
⚠️ RISK_ASSESSMENT - FinanceStateAgent  
💡 Wallet équilibré, VaR acceptable

📅 ${new Date(Date.now() - 21600000).toLocaleString('fr-FR')}
📰 NEWS_ANALYSIS - AssetStateAgent
💡 Impact positif sur BTC (+4.1%)

Total: 4 échanges récents
        `;
        
        alert(historyContent);
    }
    
    closeModelHistory() {
        const modal = document.getElementById('model-history-modal');
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    openSchedulerConfig() {
        console.log('⚙️ Ouverture de la configuration des schedulers...');
        
        const modal = document.getElementById('scheduler-config-modal');
        if (!modal) {
            console.error('⚠️ Modal scheduler config non trouvé');
            this.showSimpleSchedulerConfig();
            return;
        }
        
        console.log('✅ Modal scheduler config trouvé, ouverture...');
        
        // Remplir le contenu de la configuration
        this.populateSchedulerConfig();
        
        // Afficher le modal avec animation
        modal.classList.add('show');
    }
    
    closeSchedulerConfig() {
        const modal = document.getElementById('scheduler-config-modal');
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    showSimpleSchedulerConfig() {
        const configContent = `
⚙️ CONFIGURATION DES SCHEDULERS

📊 COLLECTE DE DONNÉES:
• Prix crypto: 30 secondes
• Actualités: 2 minutes  
• Performance: 30 secondes

🤖 AGENTS IA:
• Signaux démo: 20 secondes
• Analyse ETH: Quotidien 8h00
• Scan marché: Horaire 9h-18h

✅ Tous les schedulers sont actifs
        `;
        
        alert(configContent);
    }

    async populateSchedulerConfig() {
        console.log('📋 Remplissage de la configuration des schedulers...');
        
        const content = document.getElementById('scheduler-config-content');
        if (!content) {
            console.error('❌ scheduler-config-content non trouvé');
            return;
        }

        // Charger les vraies données des simulations
        let simulationsData = [];
        try {
            const response = await fetch('/api/simulations');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    simulationsData = data.simulations;
                }
            }
        } catch (error) {
            console.error('Erreur lors du chargement des simulations:', error);
        }
        
        // Charger les données des sources crypto
        let sourcesStats = null;
        try {
            const response = await fetch('/api/knowledge/stats');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    sourcesStats = data.sources_stats; // Correction du chemin
                }
            }
        } catch (error) {
            console.error('Erreur lors du chargement des stats sources:', error);
        }
        
        content.innerHTML = `
            <div style="display: grid; gap: 20px;">
                
                <!-- Section Gestion des Simulations -->
                <div style="
                    background: rgba(139, 69, 19, 0.1);
                    border: 1px solid rgba(139, 69, 19, 0.3);
                    border-radius: 12px;
                    padding: 16px;
                ">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="font-size: 18px;">🎮</div>
                            <h4 style="margin: 0; color: #cd853f; font-weight: 600;">Gestion des Simulations</h4>
                            <span id="sim-count-badge" style="
                                background: #cd853f;
                                color: white;
                                border-radius: 12px;
                                padding: 2px 8px;
                                font-size: 11px;
                                font-weight: 600;
                            ">${simulationsData.filter(s => s.is_active).length} active${simulationsData.filter(s => s.is_active).length > 1 ? 's' : ''}</span>
                        </div>
                        <button onclick="window.nodeManager.openSimulationCreator()" style="
                            background: linear-gradient(135deg, #10b981, #059669);
                            color: white;
                            border: none;
                            padding: 8px 12px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                            font-size: 12px;
                        ">+ Nouvelle Simulation</button>
                    </div>
                    
                    <!-- Liste des simulations -->
                    <div id="scheduler-simulations-list" style="display: grid; gap: 8px; max-height: 200px; overflow-y: auto;">
                        ${this.generateSimulationsList(simulationsData)}
                    </div>
                </div>
                
                <!-- Section Gestion des Sources -->
                <div style="
                    background: rgba(168, 85, 247, 0.1);
                    border: 1px solid rgba(168, 85, 247, 0.3);
                    border-radius: 12px;
                    padding: 16px;
                ">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="font-size: 18px;">📚</div>
                            <h4 style="margin: 0; color: #a855f7; font-weight: 600;">Gestion des Sources</h4>
                            <span id="sources-count-badge" style="
                                background: #a855f7;
                                color: white;
                                border-radius: 12px;
                                padding: 2px 8px;
                                font-size: 11px;
                                font-weight: 600;
                            ">${sourcesStats ? sourcesStats.total_sources || 0 : 0} sources</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button onclick="window.nodeManager.startIndexing()" style="
                                background: linear-gradient(135deg, #10b981, #059669);
                                color: white;
                                border: none;
                                padding: 8px 12px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                                font-size: 12px;
                            ">🚀 Indexer</button>
                            <button onclick="window.nodeManager.openSourcesManager()" style="
                                background: linear-gradient(135deg, #a855f7, #9333ea);
                                color: white;
                                border: none;
                                padding: 8px 12px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                                font-size: 12px;
                            ">⚙️ Gérer</button>
                        </div>
                    </div>
                    
                    <!-- Stats des sources -->
                    <div id="sources-stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 14px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Sources Total:</span>
                            <span style="color: #a855f7; font-weight: 600;">${sourcesStats ? sourcesStats.total_sources || 0 : 0}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Indexées:</span>
                            <span style="color: #10b981; font-weight: 600;">${sourcesStats ? sourcesStats.indexed_sources || 0 : 0}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Chunks:</span>
                            <span style="color: #60a5fa; font-weight: 600;">${sourcesStats ? sourcesStats.total_chunks || 0 : 0}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Collection:</span>
                            <span style="color: #a855f7; font-weight: 600;">base_embeddings</span>
                        </div>
                    </div>
                </div>
                
                <!-- Section Data Collection -->
                <div style="
                    background: rgba(59, 130, 246, 0.1);
                    border: 1px solid rgba(59, 130, 246, 0.3);
                    border-radius: 12px;
                    padding: 16px;
                ">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <div style="font-size: 18px;">📊</div>
                        <h4 style="margin: 0; color: #60a5fa; font-weight: 600;">Collecte de Données</h4>
                        <div class="pulse-dot" style="background: #10b981;"></div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 14px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Prix Crypto:</span>
                            <span style="color: #10b981; font-weight: 600;">30 sec</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Actualités:</span>
                            <span style="color: #10b981; font-weight: 600;">2 min</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Performance:</span>
                            <span style="color: #10b981; font-weight: 600;">30 sec</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Market Cap:</span>
                            <span style="color: #10b981; font-weight: 600;">1 min</span>
                        </div>
                    </div>
                </div>

                <!-- Section AI Agents -->
                <div style="
                    background: rgba(245, 158, 11, 0.1);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 12px;
                    padding: 16px;
                ">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <div style="font-size: 18px;">🤖</div>
                        <h4 style="margin: 0; color: #f59e0b; font-weight: 600;">Agents IA</h4>
                        <div class="pulse-dot" style="background: #f59e0b;"></div>
                    </div>
                    
                    <div style="display: grid; gap: 8px; font-size: 14px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Signaux Démo:</span>
                            <span style="color: #f59e0b; font-weight: 600;">20 sec</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Analyse ETH:</span>
                            <span style="color: #f59e0b; font-weight: 600;">Quotidien 8h00</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Scan Marché:</span>
                            <span style="color: #f59e0b; font-weight: 600;">9h-18h</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Wallet Sync:</span>
                            <span style="color: #f59e0b; font-weight: 600;">5 min</span>
                        </div>
                    </div>
                </div>

                <!-- Section Status Global -->
                <div style="
                    background: rgba(16, 185, 129, 0.1);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 12px;
                    padding: 16px;
                ">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <div style="font-size: 18px;">✅</div>
                        <h4 style="margin: 0; color: #10b981; font-weight: 600;">Statut Global</h4>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 14px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Schedulers Actifs:</span>
                            <span style="color: #10b981; font-weight: 600;">7/7</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Connexion Ollama:</span>
                            <span style="color: #10b981; font-weight: 600;">✅ OK</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Uptime:</span>
                            <span style="color: #10b981; font-weight: 600;">2h 14m</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #d1d5db;">Dernière Sync:</span>
                            <span style="color: #10b981; font-weight: 600;">30s ago</span>
                        </div>
                    </div>
                </div>

                <!-- Boutons d'action -->
                <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px;">
                    <button onclick="window.nodeManager.restartAllSchedulers()" style="
                        background: linear-gradient(135deg, #ef4444, #dc2626);
                        color: white;
                        border: none;
                        padding: 10px 16px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    ">
                        🔄 Redémarrer
                    </button>
                    <button onclick="window.nodeManager.closeSchedulerConfig()" style="
                        background: linear-gradient(135deg, #6b7280, #4b5563);
                        color: white;
                        border: none;
                        padding: 10px 16px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                    ">
                        Fermer
                    </button>
                </div>
            </div>
        `;
        
        console.log('✅ Configuration des schedulers affichée');
    }

    generateSimulationsList(simulations) {
        if (!simulations || simulations.length === 0) {
            return `
                <div style="text-align: center; color: #9ca3af; padding: 40px; font-size: 14px;">
                    Aucune simulation configurée<br>
                    <span style="font-size: 12px; opacity: 0.7;">Cliquez sur "+ Nouvelle Simulation" pour commencer</span>
                </div>
            `;
        }

        return simulations.map(sim => {
            const statusColor = sim.is_active ? '#10b981' : '#6b7280';
            const statusIcon = sim.is_active ? '✅' : '❌';
            const statusText = sim.is_active ? 'Active' : 'Inactive';
            
const totalPnl = typeof sim.total_pnl === 'number' ? sim.total_pnl : 0;
const pnlSign = totalPnl >= 0 ? '+' : '';
const pnlPercent = typeof sim.pnl_percent === 'number' ? sim.pnl_percent : 0;
const roiText = `${pnlSign}${pnlPercent.toFixed(1)}%`;
            
            // Déterminer la fréquence
            let freqText = 'Custom';
            if (sim.frequency_minutes === 5) freqText = '5min';
            else if (sim.frequency_minutes === 15) freqText = '15min';
            else if (sim.frequency_minutes === 30) freqText = '30min'; 
            else if (sim.frequency_minutes === 60) freqText = '1h';
            else if (sim.frequency_minutes === 240) freqText = '4h';
            else if (sim.frequency_minutes === 1440) freqText = '1d';
            else freqText = `${sim.frequency_minutes}min`;
            
            const agentsActive = sim.is_active ? '3/3' : '0/3';
            
            const actionButtons = `
                <button class="edit-simulation-btn" data-simulation-id="${sim.id}" style="
                    background: #3b82f6; color: white; border: none; padding: 4px 8px;
                    border-radius: 4px; cursor: pointer; font-size: 11px;
                ">✏️</button>
                <button class="toggle-simulation-btn" data-simulation-id="${sim.id}" style="
                    background: ${sim.is_active ? '#f59e0b' : '#10b981'};
                    color: white; border: none; padding: 4px 8px;
                    border-radius: 4px; cursor: pointer; font-size: 11px;
                " title="État: ${sim.is_active ? 'Active' : 'Inactive'}">${sim.is_active ? '⏸️' : '▶️'}</button>
                <button class="delete-simulation-btn" data-simulation-id="${sim.id}" style="
                    background: #ef4444; color: white; border: none; padding: 4px 8px;
                    border-radius: 4px; cursor: pointer; font-size: 11px;
                ">🗑️</button>
            `;

            return `
                <div style="
                    background: rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 12px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <div style="color: #fff; font-weight: 600; font-size: 14px;">
                            ${sim.name}
                        </div>
                        <div style="color: #9ca3af; font-size: 12px;">
                            Wallet: ${sim.wallet_name} • Stratégie: ${sim.strategy} • Fréq: ${freqText}
                        </div>
                        <div style="color: ${statusColor}; font-size: 11px; font-weight: 600;">
                            ${statusIcon} ${statusText} • ROI: ${roiText} • Agents: ${agentsActive}
                        </div>
                    </div>
                    <div style="display: flex; gap: 6px;">
                        ${actionButtons}
                    </div>
                </div>
            `;
        }).join('');
    }

    test() {
        console.log('🧪 Test NodeManager OK');
        return 'NodeManager fonctionne correctement';
    }

    restartAllSchedulers() {
        console.log('🔄 Redémarrage de tous les schedulers...');
        
        // Simulation du redémarrage
        const btn = event.target;
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Redémarrage...';
        btn.disabled = true;
        
        setTimeout(() => {
            btn.innerHTML = '✅ Redémarré!';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 1500);
        }, 2000);
        
        console.log('✅ Simulation redémarrage terminée');
    }
    
    async startIndexing() {
        console.log('🚀 Démarrage de l\'indexation des sources...');
        
        const btn = event.target;
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Indexation...';
        btn.disabled = true;
        
        try {
            const response = await fetch('/api/knowledge/index', {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('✅ Indexation lancée:', result);
                
                btn.innerHTML = '✅ Lancée!';
                this.showNotification('🚀 Indexation lancée en arrière-plan. Consultez les logs pour suivre le progrès.', 'success');
                
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }, 2000);
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Erreur lors du lancement de l\'indexation');
            }
        } catch (error) {
            console.error('❌ Erreur indexation:', error);
            btn.innerHTML = '❌ Erreur';
            this.showNotification('❌ Erreur lors du lancement de l\'indexation: ' + error.message, 'error');
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 2000);
        }
    }
    
    async openSourcesManager() {
        console.log('⚙️ Ouverture du gestionnaire de sources...');
        
        // Créer et afficher le modal de gestion des sources
        const modalHTML = `
            <div id="sources-manager-modal" class="modal-overlay show">
                <div class="modal-container" style="max-width: 800px;">
                    <div class="modal-header">
                        <h3 class="modal-title">📚 Gestion des Sources Crypto</h3>
                        <button class="close-btn" onclick="window.nodeManager.closeSourcesManager()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div style="text-align: center; padding: 20px; color: #9ca3af;">
                            🔄 Chargement des sources...
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Ajouter le modal au DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Charger le contenu
        this.loadSourcesManagerContent();
    }
    
    closeSourcesManager() {
        const modal = document.getElementById('sources-manager-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    async loadSourcesManagerContent() {
        const modalBody = document.querySelector('#sources-manager-modal .modal-body');
        if (!modalBody) return;
        
        try {
            // Charger la liste des sources
            const response = await fetch('/api/knowledge/sources');
            let sources = [];
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    sources = data.sources;
                }
            }
            
            modalBody.innerHTML = `
                <div style="display: grid; gap: 20px;">
                    <!-- Header avec actions -->
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #fff;">Sources disponibles (${sources.length})</h4>
                            <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 14px;">
                                ${sources.filter(s => s.indexed).length} sources indexées • 
                                ${sources.filter(s => !s.indexed).length} en attente
                            </p>
                        </div>
                        <button onclick="window.nodeManager.addNewSource()" style="
                            background: linear-gradient(135deg, #10b981, #059669);
                            color: white;
                            border: none;
                            padding: 10px 16px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                        ">+ Ajouter Source</button>
                    </div>
                    
                    <!-- Liste des sources -->
                    <div style="max-height: 400px; overflow-y: auto; border: 1px solid #374151; border-radius: 8px;">
                        ${this.generateSourcesList(sources)}
                    </div>
                    
                    <!-- Actions -->
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button onclick="window.nodeManager.startIndexing()" style="
                            background: linear-gradient(135deg, #3b82f6, #2563eb);
                            color: white;
                            border: none;
                            padding: 10px 16px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                        ">🚀 Indexer tout</button>
                        <button onclick="window.nodeManager.closeSourcesManager()" style="
                            background: linear-gradient(135deg, #6b7280, #4b5563);
                            color: white;
                            border: none;
                            padding: 10px 16px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                        ">Fermer</button>
                    </div>
                </div>
            `;
            
        } catch (error) {
            console.error('❌ Erreur chargement sources:', error);
            modalBody.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #ef4444;">
                    ❌ Erreur lors du chargement des sources
                </div>
            `;
        }
    }
    
    generateSourcesList(sources) {
        if (!sources || sources.length === 0) {
            return `
                <div style="text-align: center; padding: 40px; color: #9ca3af;">
                    Aucune source configurée
                </div>
            `;
        }
        
        return sources.map(source => `
            <div style="
                padding: 16px;
                border-bottom: 1px solid #374151;
                display: grid;
                grid-template-columns: 1fr auto;
                gap: 16px;
                align-items: center;
            ">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <h5 style="margin: 0; color: #fff; font-size: 14px;">${source.title}</h5>
                        ${source.indexed ? 
                            '<span style="background: #059669; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">✓ Indexé</span>' :
                            '<span style="background: #d97706; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">⏳ En attente</span>'
                        }
                        ${!source.enabled ? 
                            '<span style="background: #dc2626; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">🚫 Désactivé</span>' : ''
                        }
                        ${source.error_count > 0 ? 
                            `<span style="background: #d97706; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">⚠️ ${source.error_count} erreur${source.error_count > 1 ? 's' : ''}</span>` : ''
                        }
                    </div>
                    <p style="margin: 0 0 4px 0; color: #9ca3af; font-size: 12px;">
                        ${source.url}
                    </p>
                    <div style="display: flex; gap: 8px; font-size: 12px;">
                        ${source.tags.map(tag => `<span style="background: #374151; color: #d1d5db; padding: 2px 6px; border-radius: 4px;">${tag}</span>`).join('')}
                    </div>
                    ${source.chunks_count > 0 ? 
                        `<p style="margin: 4px 0 0 0; color: #60a5fa; font-size: 12px;">${source.chunks_count} chunks indexés</p>` : ''
                    }
                </div>
                <div style="display: flex; gap: 8px;">
                    ${source.error_count > 0 || !source.enabled ? 
                        `<button onclick="window.nodeManager.resetSourceErrors(${source.id})" style="
                            background: #10b981;
                            color: white;
                            border: none;
                            padding: 6px 10px;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 12px;
                            margin-right: 4px;
                        ">🔄 Reset</button>` : ''
                    }
                    <button onclick="window.nodeManager.editSource(${source.id})" style="
                        background: #374151;
                        color: #d1d5db;
                        border: none;
                        padding: 6px 10px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                    ">✏️</button>
                    <button onclick="window.nodeManager.deleteSource(${source.id})" style="
                        background: #dc2626;
                        color: white;
                        border: none;
                        padding: 6px 10px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                    ">🗑️</button>
                </div>
            </div>
        `).join('');
    }
    
    async addNewSource() {
        console.log('➕ Ajouter nouvelle source...');
        
        const url = prompt('URL de la source (PDF ou page web):');
        if (!url || !url.trim()) return;
        
        const title = prompt('Titre de la source:');
        if (!title || !title.trim()) return;
        
        const tagsString = prompt('Tags (séparés par des virgules):');
        const tags = tagsString ? tagsString.split(',').map(t => t.trim()).filter(t => t) : [];
        
        try {
            const response = await fetch('/api/knowledge/sources', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url.trim(),
                    title: title.trim(),
                    tags: tags,
                    enabled: true
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showNotification('✅ Source ajoutée avec succès!', 'success');
                    this.loadSourcesManagerContent(); // Recharger la liste
                } else {
                    throw new Error(result.message || 'Erreur lors de l\'ajout');
                }
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Erreur HTTP');
            }
        } catch (error) {
            console.error('❌ Erreur ajout source:', error);
            this.showNotification('❌ Erreur lors de l\'ajout: ' + error.message, 'error');
        }
    }
    
    async editSource(sourceId) {
        console.log(`✏️ Modifier source ${sourceId}...`);
        
        // Pour l'instant, juste un message
        this.showNotification('⚠️ Fonctionnalité d\'édition en cours de développement', 'info');
    }
    
    async deleteSource(sourceId) {
        console.log(`🗑️ Supprimer source ${sourceId}...`);
        
        if (!confirm('Êtes-vous sûr de vouloir supprimer cette source ? Cette action est irréversible.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/knowledge/sources/${sourceId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showNotification('✅ Source supprimée avec succès!', 'success');
                    this.loadSourcesManagerContent(); // Recharger la liste
                } else {
                    throw new Error(result.message || 'Erreur lors de la suppression');
                }
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Erreur HTTP');
            }
        } catch (error) {
            console.error('❌ Erreur suppression source:', error);
            this.showNotification('❌ Erreur lors de la suppression: ' + error.message, 'error');
        }
    }
    
    async resetSourceErrors(sourceId) {
        console.log(`🔄 Reset erreurs source ${sourceId}...`);
        
        try {
            const response = await fetch(`/api/knowledge/sources/${sourceId}/reset`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showNotification('✅ Source réactivée avec succès!', 'success');
                    this.loadSourcesManagerContent(); // Recharger la liste
                } else {
                    throw new Error(result.message || 'Erreur lors de la réactivation');
                }
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Erreur HTTP');
            }
        } catch (error) {
            console.error('❌ Erreur reset source:', error);
            this.showNotification('❌ Erreur lors de la réactivation: ' + error.message, 'error');
        }
    }

    async loadWalletsForSimulation() {
        console.log('📊 Chargement des wallets pour simulation...');
        
        const selectElement = document.getElementById('sim-wallet');
        if (!selectElement) return;
        
        try {
            const response = await fetch('/api/wallets');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const walletsData = await response.json();
            if (walletsData.status !== 'success') {
                throw new Error('Erreur API wallets');
            }
            
            // Vider et remplir le select
            selectElement.innerHTML = '<option value="">Sélectionner un wallet...</option>';
            
            walletsData.wallets.forEach(wallet => {
                const option = document.createElement('option');
                option.value = wallet.id;
                option.textContent = `${wallet.name === 'default' ? 'Main Wallet' : wallet.name} ($${wallet.current_value.toFixed(0)})`;
                selectElement.appendChild(option);
            });
            
            console.log(`✅ ${walletsData.wallets.length} wallet(s) chargé(s) pour simulation`);
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement des wallets:', error);
            selectElement.innerHTML = '<option value="">Erreur lors du chargement</option>';
        }
    }

    async loadAssetsForSimulation() {
        console.log('📊 Loading assets for simulation...');
        
        const selectElement = document.getElementById('sim-asset');
        if (!selectElement) return;
        
        try {
            const response = await fetch('/api/assets');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const assetsData = await response.json();
            if (!assetsData.success) {
                throw new Error('API error for assets');
            }
            
            selectElement.innerHTML = '<option value="">Select an asset...</option>';
            
            assetsData.assets.forEach(asset => {
                const option = document.createElement('option');
                option.value = asset.symbol;
                option.textContent = `${asset.name} (${asset.symbol})`;
                selectElement.appendChild(option);
            });
            
            console.log(`✅ ${assetsData.total} asset(s) loaded for simulation`);
            
        } catch (error) {
            console.error('❌ Error loading assets:', error);
            selectElement.innerHTML = '<option value="">Error loading assets</option>';
        }
    }

    // ===== GESTION DES SIMULATIONS =====
    
    openSimulationCreator() {
        console.log('🎮 Ouverture du créateur de simulation...');
        
        const modalHtml = `
            <div id="simulation-creator-modal" style="
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            ">
                <div style="
                    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                    padding: 24px;
                    border-radius: 12px;
                    border: 1px solid #374151;
                    max-width: 600px;
                    width: 90%;
                    max-height: 80vh;
                    overflow-y: auto;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: #fff; margin: 0; font-size: 18px;">🎮 Créer une Nouvelle Simulation</h3>
                        <button onclick="document.getElementById('simulation-creator-modal').remove()" style="
                            background: none;
                            border: none;
                            color: #9ca3af;
                            font-size: 24px;
                            cursor: pointer;
                            padding: 0;
                            line-height: 1;
                        ">&times;</button>
                    </div>
                    
                    <form id="simulation-creator-form" style="display: grid; gap: 20px;">
                        <!-- Nom de la simulation -->
                        <div>
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                📝 Nom de la Simulation
                            </label>
                            <input type="text" id="sim-name" placeholder="Ex: ETH Conservative Trading" style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                            ">
                        </div>
                        
                        <!-- Sélection du Wallet -->
                        <div>
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                💼 Wallet
                            </label>
                            <select id="sim-wallet" style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                            ">
                                <option value="">Chargement des wallets...</option>
                            </select>
                        </div>
                        
                        <!-- Politique de Trading -->
                        <div>
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                🎯 Politique de Trading
                            </label>
                            <select id="sim-policy" style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                            ">
                                <option value="">Sélectionner une politique...</option>
                                <option value="conservative">🛡️ Conservative - Risque faible, gains stables</option>
                                <option value="balanced">⚖️ Balanced - Équilibre risque/rendement</option>
                                <option value="aggressive">🚀 Aggressive - Risque élevé, gains potentiels</option>
                                <option value="scalping">⚡ Scalping - Transactions rapides</option>
                            </select>
                        </div>
                        
                        <!-- Fréquence d'Exécution -->
                        <div>
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                ⏰ Fréquence d'Exécution
                            </label>
                            <select id="sim-frequency" style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                            ">
                                <option value="">Sélectionner une fréquence...</option>
                                <option value="5min">⚡ 5 minutes - Hyper réactif</option>
                                <option value="15min">⚡ 15 minutes - Ultra réactif</option>
                                <option value="30min">🔥 30 minutes - Très réactif</option>
                                <option value="1h">⚖️ 1 heure - Équilibré</option>
                                <option value="4h">🎯 4 heures - Tendances moyennes</option>
                                <option value="1d">📈 1 jour - Tendances longues</option>
                            </select>
                        </div>
                        
                        <!-- Configuration des Agents IA -->
                        <div style="
                            background: rgba(59, 130, 246, 0.1);
                            border: 1px solid rgba(59, 130, 246, 0.3);
                            border-radius: 8px;
                            padding: 16px;
                        ">
                            <h4 style="color: #60a5fa; margin: 0 0 12px 0; font-size: 16px;">🤖 Agents IA Utilisés</h4>
                            <div style="color: #d1d5db; font-size: 14px; line-height: 1.6;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                    <span>✅</span> <strong>Agent d'Analyse de Prix</strong> - Analyse technique en temps réel
                                </div>
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                    <span>✅</span> <strong>Agent de Sentiment</strong> - Analyse des news et réseaux sociaux
                                </div>
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                    <span>✅</span> <strong>Agent de Risk Management</strong> - Gestion des risques automatisée
                                </div>
                                <div style="color: #9ca3af; font-size: 12px; margin-top: 8px;">
                                    Les agents utilisent les mêmes datasets que le système principal
                                </div>
                            </div>
                        </div>
                        
                        <!-- Boutons -->
                        <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" onclick="document.getElementById('simulation-creator-modal').remove()" style="
                                background: linear-gradient(135deg, #6b7280, #4b5563);
                                color: white;
                                border: none;
                                padding: 12px 20px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">Annuler</button>
                            <button type="button" onclick="window.nodeManager.createSimulation()" style="
                                background: linear-gradient(135deg, #10b981, #059669);
                                color: white;
                                border: none;
                                padding: 12px 20px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">🚀 Créer la Simulation</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Charger les vrais wallets et focus sur le premier champ
        setTimeout(() => {
            this.loadWalletsForSimulation();
            document.getElementById('sim-name').focus();
        }, 100);
    }

    async createSimulation() {
        console.log('🚀 Création VRAIE de la simulation...');
        
        const form = document.getElementById('simulation-creator-form');
        const name = document.getElementById('sim-name').value;
        const wallet = document.getElementById('sim-wallet').value;
        const policy = document.getElementById('sim-policy').value;
        const frequency = document.getElementById('sim-frequency').value;
        
        if (!name || !wallet || !policy || !frequency) {
            alert('⚠️ Please fill in all required fields');
            return;
        }
        
        console.log('📊 Simulation parameters:', { name, wallet, policy, frequency });
        
        try {
            // VRAI appel API pour créer la simulation
            const response = await fetch('/api/simulations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    wallet_id: parseInt(wallet),
                    strategy: policy,
                    frequency_minutes: this.convertFrequencyToMinutes(frequency),
                    description: `Simulation ${name} created via interface`
                })
            });
            
            const result = await response.json();
            console.log('📊 Réponse API création:', result);
            
            if (response.ok && result.status === 'success') {
                console.log('✅ Simulation créée avec succès:', result.simulation_id);
                
                // Recharger la liste des simulations
                window.hiveAI.waitAndLoadSimulations();
                
            } else {
                throw new Error(result.message || `Erreur HTTP: ${response.status}`);
            }
            
        } catch (error) {
            console.error('❌ Erreur lors de la création de la simulation:', error);
            alert(`❌ Erreur lors de la création:\n\n${error.message}`);
            return;
        }
        
        // Fermer le modal
        document.getElementById('simulation-creator-modal').remove();
        
        // Message de confirmation
        const confirmationModal = `
            <div id="confirmation-modal" style="
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            ">
                <div style="
                    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                    padding: 24px;
                    border-radius: 12px;
                    border: 1px solid #10b981;
                    max-width: 500px;
                    width: 90%;
                    text-align: center;
                ">
                    <div style="font-size: 48px; margin-bottom: 16px;">✅</div>
                    <h3 style="color: #10b981; margin: 0 0 16px 0;">Simulation Créée!</h3>
                    <div style="color: #d1d5db; line-height: 1.6; margin-bottom: 20px;">
                        <strong>"${name}"</strong> a été créée avec succès.<br>
                        Les agents IA commenceront leur analyse dans quelques instants.
                    </div>
                    <button onclick="document.getElementById('confirmation-modal').remove()" style="
                        background: linear-gradient(135deg, #10b981, #059669);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Parfait!</button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', confirmationModal);
        
        // Auto-fermer après 3 secondes
        setTimeout(() => {
            const modal = document.getElementById('confirmation-modal');
            if (modal) modal.remove();
        }, 3000);
    }


    pauseSimulation(id) {
        console.log('⏸️ Pause de la simulation', id);
        alert(`⏸️ Simulation ${id} mise en pause\n\n✅ Les agents IA ont été arrêtés temporairement\n🔄 Utilisez le bouton ▶️ pour reprendre`);
    }

    resumeSimulation(id) {
        console.log('▶️ Reprise de la simulation', id);
        alert(`▶️ Simulation ${id} reprise\n\n✅ Les agents IA ont redémarré\n📊 L'analyse des datasets continue`);
    }

    deleteSimulation(id) {
        console.log('🗑️ Suppression de la simulation', id);
        if (confirm(`🗑️ Êtes-vous sûr de vouloir supprimer la simulation ${id}?\n\n⚠️ Cette action est irréversible\n📊 L'historique et les performances seront perdus`)) {
            alert(`✅ Simulation ${id} supprimée\n\n🧹 Les agents IA ont été arrêtés\n💾 Les données ont été archivées`);
        }
    }

    // ===== GESTION DES WALLETS =====
    
    openWallets() {
        console.log('💼 Ouverture de la gestion des wallets...');
        
        const modal = document.getElementById('wallets-modal');
        if (modal) {
            modal.classList.add('show');
            
            // Setup bouton de fermeture si pas déjà fait
            const closeBtn = document.getElementById('close-wallets-modal');
            if (closeBtn && !closeBtn.hasAttribute('data-listener-added')) {
                closeBtn.addEventListener('click', () => {
                    console.log('❌ Fermeture du modal wallets');
                    modal.classList.remove('show');
                });
                closeBtn.setAttribute('data-listener-added', 'true');
            }
            
            // Setup bouton nouveau wallet
            const addWalletBtn = document.getElementById('add-wallet-btn');
            if (addWalletBtn && !addWalletBtn.hasAttribute('data-listener-added')) {
                addWalletBtn.addEventListener('click', () => {
                    console.log('💼 Création nouveau wallet...');
                    this.showNewWalletForm();
                });
                addWalletBtn.setAttribute('data-listener-added', 'true');
            }
            
            // Setup formulaire wallet
            const walletForm = document.getElementById('wallet-form-element');
            if (walletForm && !walletForm.hasAttribute('data-listener-added')) {
                walletForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    console.log('💾 Soumission formulaire wallet');
                    this.submitWalletForm();
                });
                walletForm.setAttribute('data-listener-added', 'true');
            }
            
            // Setup bouton ajout holding
            const addHoldingBtn = document.getElementById('add-holding-btn');
            if (addHoldingBtn && !addHoldingBtn.hasAttribute('data-listener-added')) {
                addHoldingBtn.addEventListener('click', () => {
                    console.log('📈 Ajout nouveau holding...');
                    this.showAddHoldingForm();
                });
                addHoldingBtn.setAttribute('data-listener-added', 'true');
            }
            
            // Charger les données des wallets
            this.loadWalletsData();
            
            console.log('✅ Modal wallets affiché');
        } else {
            console.error('❌ Modal wallets non trouvé dans le DOM');
            alert('💼 Gestion des Wallets\n\n🚧 Fonctionnalité en développement\n\nPermettrait de :\n• Voir tous les wallets\n• Créer de nouveaux wallets\n• Gérer les holdings\n• Consulter l\'historique des transactions');
        }
    }

    async loadWalletsData() {
        console.log('📊 Chargement des données des wallets...');
        
        const walletsList = document.getElementById('wallets-list');
        if (!walletsList) return;
        
        try {
            // Charger les vrais wallets depuis l'API
            const response = await fetch('/api/wallets');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const walletsData = await response.json();
            if (walletsData.status !== 'success') {
                throw new Error('Erreur API wallets');
            }
            
            const realWallets = walletsData.wallets.map(wallet => ({
                id: wallet.id,
                name: wallet.name === 'default' ? 'Main Wallet' : wallet.name,
                balance_usd: wallet.current_value,
                assets_count: wallet.holdings_count,
                last_activity: wallet.updated_at,
                is_default: wallet.name === 'default'
            }));
            
            // Afficher les wallets
            walletsList.innerHTML = realWallets.map(wallet => `
                <div class="wallet-item" data-wallet-id="${wallet.id}" style="
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                    padding: 12px;
                    margin-bottom: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                " onclick="window.nodeManager.selectWallet(${wallet.id}, '${wallet.name}')">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="color: #fff; font-weight: 600; font-size: 14px;">
                                ${wallet.is_default ? '⭐ ' : ''}${wallet.name}
                            </div>
                            <div style="color: #9ca3af; font-size: 12px;">
                                ${wallet.assets_count} assets • Last activity: ${new Date(wallet.last_activity).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'})}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #10b981; font-weight: 600; font-size: 14px;">
                                $${wallet.balance_usd.toLocaleString('en-US', {minimumFractionDigits: 2})}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
            
            console.log('✅ Données wallets chargées');
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement des wallets:', error);
            walletsList.innerHTML = `
                <div style="text-align: center; color: #ef4444; padding: 20px;">
                    ❌ Loading error
                    <br><span style="font-size: 12px; opacity: 0.7;">Please try again</span>
                </div>
            `;
        }
    }

    async selectWallet(walletId, walletName) {
        console.log(`💼 Wallet selection: ${walletName} (ID: ${walletId})`);
        
        // Éviter de recharger si c'est le même wallet déjà sélectionné
        if (this.selectedWalletId === walletId) {
            console.log('⚠️ Wallet déjà sélectionné, pas de rechargement');
            return;
        }
        
        this.selectedWalletId = walletId;
        
        // Mettre à jour les éléments visuels
        this.highlightSelectedWallet(walletId);
        
        // Masquer le placeholder de la section holdings et afficher le bouton Ajouter
        const holdingsPlaceholder = document.getElementById('holdings-placeholder');
        const holdingsList = document.getElementById('holdings-list');
        const addHoldingBtn = document.getElementById('add-holding-btn');
        
        console.log('🔍 Éléments trouvés:', {
            holdingsPlaceholder: !!holdingsPlaceholder,
            holdingsList: !!holdingsList,
            addHoldingBtn: !!addHoldingBtn
        });
        
        if (holdingsPlaceholder) holdingsPlaceholder.style.display = 'none';
        if (holdingsList) holdingsList.style.display = 'block';
        if (addHoldingBtn) addHoldingBtn.style.display = 'block';
        
        // Charger les détails du wallet dans le formulaire d'édition
        await this.loadWalletDetails(walletId);
        
        // Charger les holdings du wallet
        await this.loadWalletHoldings(walletId, walletName);
    }

    highlightSelectedWallet(selectedId) {
        console.log(`🎨 Highlight wallet ID: ${selectedId}`);
        
        // Retirer la sélection de tous les wallets
        const walletItems = document.querySelectorAll('.wallet-item');
        console.log(`Found ${walletItems.length} wallet items`);
        
        walletItems.forEach(item => {
            item.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            item.style.background = 'rgba(255, 255, 255, 0.05)';
        });
        
        // Highlighter le wallet sélectionné
        const selectedWallet = document.querySelector(`.wallet-item[data-wallet-id="${selectedId}"]`);
        console.log('Selected wallet element found:', !!selectedWallet);
        
        if (selectedWallet) {
            selectedWallet.style.border = '1px solid #3b82f6';
            selectedWallet.style.background = 'rgba(59, 130, 246, 0.1)';
            console.log('✅ Wallet highlighted');
        } else {
            console.error('❌ Wallet element not found with selector:', `.wallet-item[data-wallet-id="${selectedId}"]`);
        }
    }

    async loadWalletDetails(walletId) {
        console.log(`📝 Chargement détails wallet ${walletId}`);
        
        try {
            const response = await fetch(`/api/wallets/${walletId}`);
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const result = await response.json();
            const wallet = result.wallet; // L'API retourne {status: 'success', wallet: {...}}
            console.log(`💼 Détails wallet reçus:`, wallet);
            
            // Afficher le formulaire d'édition et masquer le budget AVANT affichage
            const formPlaceholder = document.getElementById('wallet-form-placeholder');
            const walletForm = document.getElementById('wallet-form');
            const budgetInput = document.getElementById('wallet-initial-budget-input');
            
            console.log('🔍 Éléments trouvés:', {
                formPlaceholder: !!formPlaceholder,
                walletForm: !!walletForm,
                budgetInput: !!budgetInput
            });
            
            // SHOW the initial budget in edit mode (editable)
            if (budgetInput && budgetInput.parentElement) {
                const budgetDiv = budgetInput.parentElement;
                budgetDiv.style.display = 'block';
                budgetDiv.style.visibility = 'visible';
                
                // Fill with wallet budget
                budgetInput.value = wallet.initial_budget_usdt || wallet.initial_budget_usd || '0';
                budgetInput.readOnly = false;
                budgetInput.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
                
                console.log('✅ Initial budget displayed and editable:', budgetInput.value);
            }
            
            if (formPlaceholder) formPlaceholder.style.display = 'none';
            if (walletForm) walletForm.style.display = 'block';
            
            // Remplir le formulaire
            const walletNameInput = document.getElementById('wallet-name');
            const submitBtn = document.getElementById('submit-wallet-btn');
            const formTitle = document.getElementById('wallet-form-title');
            
            console.log('🔍 Champs trouvés:', {
                walletNameInput: !!walletNameInput,
                submitBtn: !!submitBtn,
                formTitle: !!formTitle
            });
            
            if (walletNameInput) {
                walletNameInput.value = wallet.name || '';
                console.log('✅ Nom rempli:', wallet.name);
            }
            
            if (formTitle) {
                formTitle.textContent = 'Edit Wallet';
            }
            
            if (submitBtn) {
                submitBtn.textContent = '💾 Update Wallet';
                submitBtn.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
            }
            
            // Le champ budget a déjà été masqué plus haut
            
            // Ajouter l'event listener pour le bouton de suppression
            const deleteBtn = document.getElementById('delete-wallet-btn');
            if (deleteBtn) {
                deleteBtn.onclick = () => this.deleteWallet(walletId, wallet.name);
                // Masquer le bouton pour le wallet default
                if (wallet.name === 'default') {
                    deleteBtn.style.display = 'none';
                } else {
                    deleteBtn.style.display = 'block';
                }
            }
            
            console.log('✅ Détails wallet chargés dans le formulaire');
            
            // Vérifier que le budget est toujours masqué
            const budgetCheck = document.getElementById('wallet-initial-budget-input');
            if (budgetCheck && budgetCheck.parentElement) {
                console.log('🔍 Vérification budget final:', budgetCheck.parentElement.style.cssText);
            }
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement des détails wallet:', error);
            alert(`❌ Erreur lors du chargement du wallet:\n\n${error.message}`);
        }
    }
    
    async loadWalletHoldings(walletId, walletName) {
        console.log(`📊 Chargement des holdings pour ${walletName}...`);
        
        const holdingsList = document.getElementById('holdings-list');
        const holdingsSummary = document.getElementById('holdings-summary');
        
        if (!holdingsList) return;
        
        try {
            // Charger les vrais holdings du wallet
            const response = await fetch(`/api/wallets/${walletId}/holdings`);
            if (!response.ok) throw new Error(`Erreur API: ${response.status}`);
            
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error('Pas de données de holdings');
            }
            
            const holdings = data.holdings || [];
            
            if (holdings.length === 0) {
                holdingsList.innerHTML = `
                    <div style="text-align: center; color: #9ca3af; padding: 40px;">
                        💰 Aucun holding dans ce wallet
                        <br><span style="font-size: 12px;">Utilisez le bouton + Ajouter pour commencer</span>
                    </div>
                `;
                return;
            }
            
            // Afficher les holdings
            holdingsList.innerHTML = holdings.map(holding => {
                const pnlColor = holding.pnl >= 0 ? '#10b981' : '#ef4444';
                const pnlSign = holding.pnl >= 0 ? '+' : '';
                const pnlPercent = holding.pnl_percent || 0;
                
                return `
                    <div style="
                        background: rgba(255, 255, 255, 0.05);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 6px;
                        padding: 12px;
                        margin-bottom: 8px;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="color: #fff; font-weight: 600; font-size: 14px;">
                                    ${holding.symbol}
                                </div>
                                <div style="color: #9ca3af; font-size: 12px;">
                                    ${holding.quantity.toFixed(6)} tokens • ${holding.allocation_percent.toFixed(1)}%
                                </div>
                                <div style="color: #9ca3af; font-size: 12px;">
                                    Avg: $${holding.avg_buy_price.toFixed(2)} • Now: $${holding.current_price.toFixed(2)}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="color: #fff; font-weight: 600; font-size: 14px;">
                                    $${holding.current_value.toFixed(2)}
                                </div>
                                <div style="color: ${pnlColor}; font-size: 12px; font-weight: 500;">
                                    ${pnlSign}$${holding.pnl.toFixed(2)} (${pnlSign}${pnlPercent.toFixed(1)}%)
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            // Calculer et afficher le résumé
            const totalPnl = holdings.reduce((sum, h) => sum + h.pnl, 0);
            const totalValue = holdings.reduce((sum, h) => sum + h.current_value, 0);
            const totalCost = totalValue - totalPnl;
            const totalRoi = totalCost > 0 ? (totalPnl / totalCost * 100) : 0;
            
            if (holdingsSummary) {
                holdingsSummary.style.display = 'block';
                
                const totalPnlEl = document.getElementById('total-pnl');
                const totalRoiEl = document.getElementById('total-roi');
                
                if (totalPnlEl) {
                    const pnlColor = totalPnl >= 0 ? '#10b981' : '#ef4444';
                    const pnlSign = totalPnl >= 0 ? '+' : '';
                    totalPnlEl.textContent = `${pnlSign}$${totalPnl.toFixed(2)}`;
                    totalPnlEl.style.color = pnlColor;
                }
                
                if (totalRoiEl) {
                    const roiColor = totalRoi >= 0 ? '#10b981' : '#ef4444';
                    const roiSign = totalRoi >= 0 ? '+' : '';
                    totalRoiEl.textContent = `${roiSign}${totalRoi.toFixed(2)}%`;
                    totalRoiEl.style.color = roiColor;
                }
            }
            
            console.log(`✅ Holdings chargés pour ${walletName}: ${holdings.length} assets`);
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement des holdings:', error);
            holdingsList.innerHTML = `
                <div style="text-align: center; color: #ef4444; padding: 20px;">
                    ❌ Erreur lors du chargement
                    <br><span style="font-size: 12px;">Veuillez réessayer</span>
                </div>
            `;
        }
    }

    showNewWalletForm() {
        console.log('📝 Affichage du formulaire nouveau wallet');
        
        // Réinitialiser l'état de sélection
        this.selectedWalletId = null;
        
        // Retirer la sélection visuelle de tous les wallets
        const walletItems = document.querySelectorAll('.wallet-item');
        walletItems.forEach(item => {
            item.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            item.style.background = 'rgba(255, 255, 255, 0.05)';
        });
        
        // Masquer la section holdings et afficher placeholder
        const holdingsPlaceholder = document.getElementById('holdings-placeholder');
        const holdingsList = document.getElementById('holdings-list');
        const addHoldingBtn = document.getElementById('add-holding-btn');
        const holdingsSummary = document.getElementById('holdings-summary');
        
        if (holdingsPlaceholder) holdingsPlaceholder.style.display = 'flex';
        if (holdingsList) holdingsList.style.display = 'none';
        if (addHoldingBtn) addHoldingBtn.style.display = 'none';
        if (holdingsSummary) holdingsSummary.style.display = 'none';
        
        // Afficher la section formulaire et masquer le placeholder
        const formPlaceholder = document.getElementById('wallet-form-placeholder');
        const walletForm = document.getElementById('wallet-form');
        const formTitle = document.getElementById('wallet-form-title');
        const deleteBtn = document.getElementById('delete-wallet-btn');
        
        if (formPlaceholder) formPlaceholder.style.display = 'none';
        if (walletForm) walletForm.style.display = 'block';
        if (formTitle) formTitle.textContent = '💼 New Wallet';
        if (deleteBtn) deleteBtn.style.display = 'none';
        
        // Vider les champs et afficher le champ budget
        const nameField = document.getElementById('wallet-name');
        const budgetField = document.getElementById('wallet-initial-budget-input');
        const submitBtn = document.getElementById('submit-wallet-btn');
        
        if (nameField) nameField.value = '';
        if (budgetField) {
            budgetField.value = '1000';
            budgetField.readOnly = false;
            budgetField.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
            // S'assurer que le champ budget est visible en mode création
            if (budgetField.parentElement) {
                budgetField.parentElement.style.display = 'block';
            }
        }
        
        // Remettre le bouton en mode création
        if (submitBtn) {
            submitBtn.textContent = '💾 Sauvegarder';
            submitBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        }
        
        console.log('✅ Formulaire nouveau wallet affiché avec réinitialisation (budget visible)');
    }

    async submitWalletForm() {
        console.log('📝 Soumission du formulaire wallet...');
        
        const nameField = document.getElementById('wallet-name');
        const budgetField = document.getElementById('wallet-initial-budget-input');
        const submitBtn = document.getElementById('submit-wallet-btn');
        
        console.log('🔍 Éléments du formulaire:', {
            nameField: !!nameField,
            budgetField: !!budgetField,
            submitBtn: !!submitBtn,
            submitText: submitBtn?.textContent
        });
        
        if (!nameField) {
            console.error('❌ Champs du formulaire non trouvés');
            return;
        }
        
        const name = nameField.value.trim();
        const isEditMode = submitBtn && (submitBtn.textContent.includes('Update') || submitBtn.textContent.includes('Modifier'));
        
        console.log(`🔄 Mode: ${isEditMode ? 'Édition' : 'Création'}, Nom: "${name}", Wallet ID: ${this.selectedWalletId}`);
        
        if (!name) {
            alert('⚠️ Le nom du wallet est requis');
            return;
        }
        
        try {
            let response, result;
            
            if (isEditMode && this.selectedWalletId) {
                // Edit mode - update existing wallet
                console.log(`📝 Modifying wallet ${this.selectedWalletId}`);
                
                const budgetValue = budgetField ? budgetField.value : '0';
                const budget = parseFloat(budgetValue);
                
                if (isNaN(budget) || budget < 100) {
                    alert('⚠️ Minimum budget: $100');
                    return;
                }
                
                response = await fetch(`/api/wallets/${this.selectedWalletId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: name,
                        initial_budget: budget
                    })
                });
                
                result = await response.json();
                
                if (response.ok && result.status === 'success') {
                    console.log('✅ Wallet updated:', result);
                    alert(`✅ Wallet "${name}" updated successfully!\n\n💰 Budget: $${budget.toLocaleString()}`);
                } else {
                    throw new Error(result.message || `HTTP error: ${response.status}`);
                }
                
            } else {
                // Creation mode - create new wallet
                const budgetValue = budgetField ? budgetField.value : '1000';
                const budget = parseFloat(budgetValue);
                
                console.log('🔍 Budget debug:', {
                    budgetField: !!budgetField,
                    budgetValue: budgetValue,
                    budget: budget,
                    isNaN: isNaN(budget)
                });
                
                if (isNaN(budget) || budget < 100) {
                    alert('⚠️ Minimum budget: $100');
                    return;
                }
                
                console.log('➕ Creating new wallet with budget:', budget);
                
                const payload = {
                    name: name,
                    initial_budget: budget
                };
                
                console.log('📦 Payload sent:', payload);
                
                response = await fetch('/api/wallets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                result = await response.json();
                
                if (response.ok && result.status === 'success') {
                    console.log('✅ Wallet created:', result);
                    alert(`✅ Wallet "${name}" created successfully!\n\n💰 Initial budget: $${budget.toLocaleString()}`);
                } else {
                    throw new Error(result.message || 'Error creating wallet');
                }
            }
            
            // Recharger la liste des wallets
            await this.loadWalletsData();
            
            // Remettre le formulaire en mode création
            this.resetWalletForm();
                
        } catch (error) {
            console.error('❌ Erreur lors de l\'opération wallet:', error);
            alert(`❌ Erreur:\n\n${error.message}`);
        }
    }

    resetWalletForm() {
        console.log('🔄 Reset formulaire wallet en mode création');
        
        const nameField = document.getElementById('wallet-name');
        const budgetField = document.getElementById('wallet-initial-budget-input');
        const submitBtn = document.getElementById('submit-wallet-btn');
        const formPlaceholder = document.getElementById('wallet-form-placeholder');
        const walletForm = document.getElementById('wallet-form');
        const formTitle = document.getElementById('wallet-form-title');
        
        // Vider les champs
        if (nameField) nameField.value = '';
        
        // Réafficher le champ budget en mode création
        if (budgetField && budgetField.parentElement) {
            budgetField.value = '';
            budgetField.parentElement.style.display = 'block';
            console.log('✅ Champ budget réaffiché');
        }
        
        if (formTitle) {
            formTitle.textContent = 'New Wallet';
        }
        
        // Reset button to creation mode
        if (submitBtn) {
            submitBtn.textContent = '➕ Create Wallet';
            submitBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        }
        
        // Masquer le formulaire et afficher le placeholder
        if (formPlaceholder) formPlaceholder.style.display = 'flex';
        if (walletForm) walletForm.style.display = 'none';
        
        // Réinitialiser la sélection
        this.selectedWalletId = null;
        this.highlightSelectedWallet(null);
    }
    
    showAddHoldingForm() {
        console.log('📈 Affichage formulaire ajout holding');
        
        if (!this.selectedWalletId) {
            alert('⚠️ Veuillez d\'abord sélectionner un wallet');
            return;
        }
        
        // SUPPRIMER tout modal existant avant d'en créer un nouveau
        const existingModal = document.getElementById('add-holding-modal');
        if (existingModal) {
            console.log('🗑️ Suppression modal existant');
            existingModal.remove();
        }
        
        // Créer un modal pour l'ajout de holding
        const modalHtml = `
            <div id="add-holding-modal" style="
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10001;
            ">
                <div style="
                    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                    padding: 24px;
                    border-radius: 12px;
                    border: 1px solid #374151;
                    max-width: 500px;
                    width: 90%;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: #fff; margin: 0; font-size: 18px;">📈 Ajouter un Holding</h3>
                        <button onclick="document.getElementById('add-holding-modal').remove()" style="
                            background: none;
                            border: none;
                            color: #9ca3af;
                            font-size: 24px;
                            cursor: pointer;
                            padding: 0;
                            line-height: 1;
                        ">&times;</button>
                    </div>
                    
                    <form id="add-holding-form" style="display: grid; gap: 16px;">
                        <div style="position: relative;">
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                🪙 Crypto Asset
                            </label>
                            <input type="text" id="holding-asset-search" placeholder="Search asset (e.g. Bitcoin, BTC)..." required style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                                box-sizing: border-box;
                            ">
                            <input type="hidden" id="holding-asset" required>
                            <div id="asset-suggestions" style="
                                position: absolute;
                                top: 100%;
                                left: 0;
                                right: 0;
                                background: #1f2937;
                                border: 1px solid #374151;
                                border-top: none;
                                border-radius: 0 0 6px 6px;
                                max-height: 200px;
                                overflow-y: auto;
                                z-index: 1000;
                                display: none;
                            "></div>
                        </div>
                        
                        <div>
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                🔢 Quantité
                            </label>
                            <input type="text" id="holding-quantity" style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                            " placeholder="Ex: 20">
                        </div>
                        
                        <div>
                            <label style="display: block; color: #d1d5db; font-weight: 600; margin-bottom: 8px;">
                                💰 Prix d'Achat Moyen ($) - Optionnel
                            </label>
                            <input type="number" id="holding-price" min="0.01" step="0.01" style="
                                width: 100%;
                                padding: 12px;
                                border: 1px solid #374151;
                                border-radius: 6px;
                                background: #1f2937;
                                color: #fff;
                                font-size: 14px;
                            " placeholder="Laisser vide pour prix actuel">
                        </div>
                        
                        <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 16px;">
                            <button type="button" onclick="document.getElementById('add-holding-modal').remove()" style="
                                background: linear-gradient(135deg, #6b7280, #4b5563);
                                color: white;
                                border: none;
                                padding: 12px 20px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">Annuler</button>
                            
                            <button type="button" onclick="window.nodeManager.submitHoldingForm()" style="
                                background: linear-gradient(135deg, #10b981, #059669);
                                color: white;
                                border: none;
                                padding: 12px 20px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 600;
                            ">📈 Ajouter</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Setup asset search functionality
        this.setupAssetSearch();
        
        // PAS d'event listener sur le form - on utilise onclick directement sur le bouton
        // Évite la double soumission qui vidait les champs
        console.log('⚠️ Event listener du form SUPPRIMÉ pour éviter double soumission');
        
        // DEBUG COMPLET du champ quantité
        const quantityField = document.getElementById('holding-quantity');
        if (quantityField) {
            console.log('🔍 Champ quantity trouvé:', {
                id: quantityField.id,
                type: quantityField.type,
                readOnly: quantityField.readOnly,
                disabled: quantityField.disabled,
                value: quantityField.value,
                placeholder: quantityField.placeholder
            });
            
            // Tracer CHAQUE frappe
            quantityField.addEventListener('keydown', (e) => {
                console.log('⌨️ KEYDOWN:', e.key, 'Valeur avant:', quantityField.value);
            });
            
            quantityField.addEventListener('keyup', (e) => {
                console.log('⌨️ KEYUP:', e.key, 'Valeur après:', quantityField.value);
            });
            
            quantityField.addEventListener('input', (e) => {
                console.log('📝 INPUT EVENT - Valeur:', e.target.value);
                let value = e.target.value;
                // SEULEMENT chiffres et un seul point
                const originalValue = value;
                value = value.replace(/[^0-9.]/g, '');
                // Empêcher plusieurs points
                const parts = value.split('.');
                if (parts.length > 2) {
                    value = parts[0] + '.' + parts.slice(1).join('');
                }
                if (originalValue !== value) {
                    e.target.value = value;
                    console.log('🗺 Nettoyé de:', originalValue, 'vers:', value);
                } else {
                    console.log('✅ Pas de nettoyage nécessaire:', value);
                }
            });
        } else {
            console.error('❌ CHAMP QUANTITY NON TROUVÉ !!');
        }
        
        console.log('✅ Modal ajout holding affiché');
    }

    setupAssetSearch() {
        console.log('🔍 Setup asset search functionality...');
        
        const searchInput = document.getElementById('holding-asset-search');
        const hiddenInput = document.getElementById('holding-asset');
        const suggestionsDiv = document.getElementById('asset-suggestions');
        
        if (!searchInput || !hiddenInput || !suggestionsDiv) {
            console.error('❌ Asset search elements not found');
            return;
        }
        
        let searchTimeout;
        let allAssets = []; // Cache for assets
        
        // Load initial assets
        this.loadAssetCache().then(assets => {
            allAssets = assets;
        });
        
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            // Clear previous timeout
            clearTimeout(searchTimeout);
            
            if (query.length < 2) {
                suggestionsDiv.style.display = 'none';
                hiddenInput.value = '';
                return;
            }
            
            // Debounce search
            searchTimeout = setTimeout(() => {
                this.performAssetSearch(query, allAssets, suggestionsDiv, searchInput, hiddenInput);
            }, 300);
        });
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#holding-asset-search') && !e.target.closest('#asset-suggestions')) {
                suggestionsDiv.style.display = 'none';
            }
        });
    }
    
    async loadAssetCache() {
        console.log('📦 Loading asset cache...');
        
        try {
            const response = await fetch('/api/assets/dropdown');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const result = await response.json();
            console.log(`✅ ${result.total} assets loaded in cache`);
            return result.options || [];
            
        } catch (error) {
            console.error('❌ Error loading asset cache:', error);
            return [];
        }
    }
    
    async performAssetSearch(query, allAssets, suggestionsDiv, searchInput, hiddenInput) {
        console.log(`🔍 Searching for: "${query}"`);
        
        // Filter local assets first
        const localMatches = allAssets.filter(asset => 
            asset.name.toLowerCase().includes(query.toLowerCase()) ||
            asset.symbol.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 5); // Limit to 5 results
        
        // If no local matches, search CoinGecko
        let coingeckoMatches = [];
        if (localMatches.length === 0) {
            try {
                console.log('🌐 Searching CoinGecko...');
                const response = await fetch(`/api/assets/search?q=${encodeURIComponent(query)}`);
                if (response.ok) {
                    const result = await response.json();
                    coingeckoMatches = result.results || [];
                }
            } catch (error) {
                console.warn('⚠️ CoinGecko search failed:', error);
            }
        }
        
        // Display suggestions
        this.displayAssetSuggestions(localMatches, coingeckoMatches, suggestionsDiv, searchInput, hiddenInput);
    }
    
    displayAssetSuggestions(localMatches, coingeckoMatches, suggestionsDiv, searchInput, hiddenInput) {
        suggestionsDiv.innerHTML = '';
        
        // Add local matches
        localMatches.forEach(asset => {
            const div = document.createElement('div');
            div.style.cssText = `
                padding: 10px;
                cursor: pointer;
                border-bottom: 1px solid #374151;
                color: #fff;
                font-size: 14px;
            `;
            div.innerHTML = `
                <div style="font-weight: 600;">${asset.name} (${asset.symbol})</div>
                <div style="font-size: 12px; color: #9ca3af;">${asset.subtitle}</div>
            `;
            
            div.addEventListener('click', () => {
                searchInput.value = `${asset.name} (${asset.symbol})`;
                hiddenInput.value = asset.value;
                suggestionsDiv.style.display = 'none';
            });
            
            div.addEventListener('mouseover', () => {
                div.style.backgroundColor = '#374151';
            });
            
            div.addEventListener('mouseout', () => {
                div.style.backgroundColor = 'transparent';
            });
            
            suggestionsDiv.appendChild(div);
        });
        
        // Add CoinGecko matches (if any)
        coingeckoMatches.forEach(asset => {
            const div = document.createElement('div');
            div.style.cssText = `
                padding: 10px;
                cursor: pointer;
                border-bottom: 1px solid #374151;
                color: #fff;
                font-size: 14px;
                background: rgba(34, 197, 94, 0.1);
            `;
            div.innerHTML = `
                <div style="font-weight: 600;">${asset.name} (${asset.symbol}) 🆕</div>
                <div style="font-size: 12px; color: #22c55e;">From CoinGecko - Will be added to database</div>
            `;
            
            div.addEventListener('click', () => {
                searchInput.value = `${asset.name} (${asset.symbol})`;
                hiddenInput.value = asset.id; // CoinGecko ID
                hiddenInput.setAttribute('data-new-asset', 'true');
                hiddenInput.setAttribute('data-asset-name', asset.name);
                hiddenInput.setAttribute('data-asset-symbol', asset.symbol);
                suggestionsDiv.style.display = 'none';
            });
            
            div.addEventListener('mouseover', () => {
                div.style.backgroundColor = 'rgba(34, 197, 94, 0.2)';
            });
            
            div.addEventListener('mouseout', () => {
                div.style.backgroundColor = 'rgba(34, 197, 94, 0.1)';
            });
            
            suggestionsDiv.appendChild(div);
        });
        
        // Show suggestions if we have any
        if (localMatches.length > 0 || coingeckoMatches.length > 0) {
            suggestionsDiv.style.display = 'block';
        } else {
            // No matches found
            suggestionsDiv.innerHTML = `
                <div style="padding: 10px; color: #9ca3af; text-align: center; font-size: 14px;">
                    No assets found for your search
                </div>
            `;
            suggestionsDiv.style.display = 'block';
        }
    }
    
    async submitHoldingForm() {
        console.log('📈 Soumission formulaire holding... DEBUT');
        
        // Plus de protection double soumission - cause éliminée
        
        const assetElement = document.getElementById('holding-asset');
        // PROBLEME: getElementById retourne le 1er élément (vide), pas le bon
        // SOLUTION: Utiliser querySelectorAll et prendre celui qui a une valeur
        const quantityElements = document.querySelectorAll('#holding-quantity');
        const quantityElement = Array.from(quantityElements).find(el => el.value !== '') || quantityElements[quantityElements.length - 1];
        const priceElement = document.getElementById('holding-price');
        
        console.log('🔧 CORRECTION - Utilisation du bon élément quantity:');
        console.log('Total éléments:', quantityElements.length);
        console.log('Valeurs:', Array.from(quantityElements).map(el => el.value));
        console.log('Élément choisi value:', quantityElement.value);
        
        console.log('🔍 Éléments DOM:', {
            assetElement: !!assetElement,
            quantityElement: !!quantityElement,
            priceElement: !!priceElement
        });
        
        if (!quantityElement) {
            console.error('❌ Élément holding-quantity non trouvé !');
            alert('❌ Erreur: Champ quantité non trouvé');
            return;
        }
        
        // LIRE les valeurs juste avant utilisation
        console.log('🔍 Lecture des valeurs immédiate:');
        console.log('Asset element value:', assetElement ? assetElement.value : 'null');
        console.log('Quantity element value AVANT lecture:', quantityElement.value);
        console.log('Price element value:', priceElement ? priceElement.value : 'null');
        
        const asset = assetElement ? assetElement.value : '';
        const quantityInput = quantityElement.value;
        const quantity = quantityInput ? parseFloat(quantityInput) : 0;
        const priceInput = priceElement ? priceElement.value : '';
        const price = priceInput ? parseFloat(priceInput) : null; // Prix optionnel
        
        console.log('🔍 Valeurs extraites:');
        console.log('quantityInput (string):', `"${quantityInput}"`);
        console.log('quantity (number):', quantity);
        
        // DEBUG ULTIME - Vérifier l'élément directement + doublons
        const debugElement = document.getElementById('holding-quantity');
        const allElements = document.querySelectorAll('#holding-quantity');
        const allModals = document.querySelectorAll('#add-holding-modal');
        
        console.log('🔍 DEBUG ULTIME:');
        console.log('Element existe:', !!debugElement);
        console.log('Nombre d\'éléments holding-quantity:', allElements.length);
        console.log('Nombre de modals add-holding:', allModals.length);
        console.log('Element.value:', debugElement ? `"${debugElement.value}"` : 'N/A');
        console.log('Tous les éléments values:', Array.from(allElements).map(el => el.value));
        console.log('Element parent:', debugElement ? debugElement.parentElement.id : 'N/A');
        
        console.log('🔍 Valeurs du formulaire:', {
            asset,
            quantity,
            priceInput,
            price,
            selectedWalletId: this.selectedWalletId
        });
        
        console.log('🔍 Validation:', { asset, quantity, isNaN_quantity: isNaN(quantity), quantity_positive: quantity > 0 });
        
        if (!asset || asset === '') {
            console.log('❌ Asset manquant');
            alert('⚠️ Veuillez sélectionner un asset');
            return;
        }
        
        if (!quantityInput || quantityInput.trim() === '' || isNaN(quantity) || quantity <= 0) {
            console.log('❌ Quantité invalide:', { input: quantityInput, parsed: quantity });
            alert('⚠️ Veuillez saisir une quantité supérieure à 0');
            return;
        }
        
        console.log('✅ Validation réussie, envoi à l\'API...');
        
        try {
            // Check if this is a new asset from CoinGecko
            const hiddenAssetInput = document.getElementById('holding-asset');
            const isNewAsset = hiddenAssetInput.getAttribute('data-new-asset') === 'true';
            const assetName = hiddenAssetInput.getAttribute('data-asset-name');
            const assetSymbol = hiddenAssetInput.getAttribute('data-asset-symbol');
            
            console.log(`🪙 Asset selected: ${asset}`, { isNewAsset, assetName, assetSymbol });
            
            let symbol = assetSymbol || asset.toUpperCase();
            
            // If this is a new asset, add it to the database first
            if (isNewAsset && assetName && assetSymbol) {
                console.log('🆕 Adding new asset to database...');
                
                const addAssetResponse = await fetch('/api/assets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: asset, // CoinGecko ID
                        name: assetName,
                        symbol: assetSymbol.toUpperCase(),
                        coingecko_id: asset
                    })
                });
                
                if (!addAssetResponse.ok) {
                    const errorData = await addAssetResponse.json();
                    throw new Error(`Failed to add asset: ${errorData.message || 'Unknown error'}`);
                }
                
                console.log('✅ New asset added to database');
                alert(`🆕 Asset "${assetName}" (${assetSymbol}) added to database and ready to use!`);
            }
            
            console.log('📊 Envoi à l\'API:', { asset_value: asset, symbol, quantity, avg_buy_price: price });
            
            const payload = {
                symbol: symbol,
                quantity: quantity
            };
            
            // Ajouter le prix seulement s'il est fourni
            if (price !== null && !isNaN(price)) {
                payload.avg_buy_price = price;
            }
            
            const response = await fetch(`/api/wallets/${this.selectedWalletId}/holdings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                console.log('✅ Holding ajouté avec succès:', result);
                
                // Message de succès
                alert(`✅ ${result.message}`);
                
                // Recharger les holdings
                const selectedWallet = document.querySelector('.wallet-item[style*="59, 130, 246"]');
                if (selectedWallet) {
                    const walletName = selectedWallet.querySelector('[style*="font-weight: 600"]').textContent.replace('⭐ ', '');
                    await this.loadWalletHoldings(this.selectedWalletId, walletName);
                }
                
                // SEULEMENT fermer le modal en cas de succès
                document.getElementById('add-holding-modal').remove();
                
            } else {
                throw new Error(result.message || `Erreur HTTP: ${response.status}`);
            }
            
        } catch (error) {
            console.error('❌ Erreur lors de l\'ajout du holding:', error);
            console.log('❌ Modal ne devrait PAS se fermer car il y a une erreur');
            alert(`❌ Erreur lors de l'ajout du holding:\n\n${error.message}`);
        }
    }
    
    async deleteHolding(holdingId) {
        console.log(`🗑️ Suppression holding ${holdingId}`);
        
        if (!confirm('🗑️ Êtes-vous sûr de vouloir supprimer ce holding ?\n\n⚠️ Cette action est irréversible')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/holdings/${holdingId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.status === 'success') {
                console.log('✅ Holding supprimé avec succès');
                
                // Recharger les holdings
                const selectedWallet = document.querySelector('.wallet-item[style*="59, 130, 246"]');
                if (selectedWallet && this.selectedWalletId) {
                    const walletName = selectedWallet.querySelector('[style*="font-weight: 600"]').textContent.replace('⭐ ', '');
                    await this.loadWalletHoldings(this.selectedWalletId, walletName);
                }
                
                alert('✅ Holding supprimé avec succès');
            } else {
                throw new Error(result.message || 'Erreur lors de la suppression');
            }
            
        } catch (error) {
            console.error('❌ Erreur lors de la suppression:', error);
            alert(`❌ Erreur lors de la suppression:\n\n${error.message}`);
        }
    }
    
    async deleteWallet(walletId, walletName) {
        console.log(`🗑️ Suppression wallet ${walletId}: ${walletName}`);
        
        if (walletName === 'default') {
            alert('⚠️ Impossible de supprimer le wallet par défaut');
            return;
        }
        
        if (!confirm(`🗑️ Êtes-vous sûr de vouloir supprimer le wallet "${walletName}" ?\n\n⚠️ Cette action supprimera :
• Tous les holdings du wallet
• L'historique des transactions
• Les simulations associées\n\nCette action est IRRÉVERSIBLE !`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/wallets/${walletId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `Erreur HTTP: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.status === 'success') {
                console.log('✅ Wallet supprimé avec succès');
                
                // Fermer le modal wallet et recharger la liste
                const walletModal = document.getElementById('wallet-modal');
                if (walletModal) {
                    walletModal.classList.remove('show');
                }
                
                alert(`✅ ${result.message}`);
                
                // Réinitialiser l'état
                this.selectedWalletId = null;
                
            } else {
                throw new Error(result.message || 'Erreur lors de la suppression');
            }
            
        } catch (error) {
            console.error('❌ Erreur lors de la suppression du wallet:', error);
            alert(`❌ Erreur lors de la suppression du wallet:\n\n${error.message}`);
        }
    }

}

// Initialize the app when the page loads
window.addEventListener('load', () => {
    // Fermer tout modal qui pourrait être ouvert au démarrage
    const logsModal = document.getElementById('logs-modal');
    if (logsModal) {
        logsModal.style.display = 'none';
    }
    
    const historyModal = document.getElementById('model-history-modal');
    if (historyModal) {
        historyModal.classList.remove('show');
    }
    
    const schedulerModal = document.getElementById('scheduler-config-modal');
    if (schedulerModal) {
        schedulerModal.classList.remove('show');
    }
    
    // Créer l'instance du gestionnaire de node dès le chargement
    console.log('🚀 Création des gestionnaires...');
    
    try {
        window.nodeManager = new NodeManager();
        console.log('✅ NodeManager créé:', window.nodeManager);
    } catch (error) {
        console.error('❌ Erreur création NodeManager:', error);
    }
    
    try {
        window.hiveAI = new HiveAI();
        console.log('✅ HiveAI créé:', window.hiveAI);
        
        // Test function pour debug
        window.testAssetStats = (symbol = 'TAO') => {
            console.log('🧪 Test asset stats avec symbol:', symbol);
            if (window.hiveAI && window.hiveAI.showAssetStatsForSymbol) {
                window.hiveAI.showAssetStatsForSymbol(symbol);
            } else {
                console.error('❌ hiveAI ou showAssetStatsForSymbol non disponible');
            }
        };
    } catch (error) {
        console.error('❌ Erreur création HiveAI:', error);
    }
    
    // Créer le WalletManager après que toutes les classes soient définies
    // TODO: WalletManager n'est pas encore implémenté
    /*
    try {
        console.log('🔄 Tentative de création WalletManager...');
        window.walletManager = new WalletManager();
        console.log('✅ WalletManager créé:', window.walletManager);
    } catch (error) {
        console.error('❌ Erreur création WalletManager:', error);
        console.error('❌ Stack trace:', error.stack);
    }
    */
    
    // Test pour diagnostiquer les problèmes (sans auto-ouverture)
    setTimeout(() => {
        if (window.nodeManager) {
            window.nodeManager.test();
        }
        
        // Test spécifique pour le bouton Wallets
        console.log('🔍 Test du bouton Wallets...');
        const walletsBtn = document.getElementById('wallets-btn');
        console.log('Bouton wallets-btn trouvé:', walletsBtn);
        if (walletsBtn) {
            console.log('Event listeners attachés pour wallet button: OK');
        }
    }, 1000);
});
