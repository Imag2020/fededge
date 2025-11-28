/**
 * FedEdgeAI Core Module
 * Main application class that coordinates all managers and modules
 */

import { UIUtils } from './ui-utils.js';
import { WebSocketManager } from './websocket.js';
import { ChatManager } from './chat.js';
import { WalletManager } from './wallet.js';
import { SignalsManager } from './signals.js';
import { TradingManager } from './trading.js';
import { DashboardManager } from './dashboard.js';
import { LicenseManager } from './license.js';
import { RagManager } from './rag.js';
import { SettingsManager } from './settings.js';
import { SignalNotifications } from './signal-notifications.js';
import { ConsciousnessManager } from './consciousness.js';

// import {AgentMonitor} from './agent-monitor.js';  // Disabled - Agent V2 section removed

export class FedEdgeAI {
    constructor() {
        console.log('FedEdgeAI initialization started...');

        // Initialize all managers
        this.websocketManager = new WebSocketManager(this);
        this.consciousnessManager = new ConsciousnessManager(this.websocketManager);
        this.chatManager = new ChatManager(this);
        this.walletManager = new WalletManager(this);
        this.signalsManager = new SignalsManager(this);
        this.tradingManager = new TradingManager(this);
        this.dashboardManager = new DashboardManager(this);
        this.licenseManager = new LicenseManager(this);
        this.ragManager = new RagManager(this);
        this.settingsManager = new SettingsManager(this);
        this.signalNotifications = new SignalNotifications(this);

        // Initialize the application
        this.init();

        console.log('FedEdgeAI initialized successfully');
    }

  

    /**
     * Initialize the application
     */
    async init() {
        console.log('Setting up FedEdgeAI...');

        // Setup WebSocket connection
        this.websocketManager.connect();

        // Setup sidebar and settings first (they're in index.html)
        this.setupSidebarNavigation();
        this.setupSettingsModal();
        this.setupConfigButton();

        // Initialize license system
        this.licenseManager.init();

        // Preload all pages (HTML only, no data yet)
        await this.preloadAllPages();

        // Show dashboard page (no data reload)
        this.switchToPage('dashboard');

        // Setup modals AFTER pages are loaded (buttons are in dashboard.html)
        this.setupModals();

        // Setup UI components that require page elements to be loaded
        this.chatManager.setupChatInterface();
        this.walletManager.setupWalletInterface();
        this.signalsManager.setupSignalPagination();
        this.tradingManager.setupTradingBotInterface();

        this.ragManager.setupKnowledgeBase();

        // Load initial data ONCE
        setTimeout(() => {
            this.loadInitialData();
        }, 500);

        // Setup auto-refresh intervals
        this.setupAutoRefresh();

        // Load initial settings (LLM config + Embeddings)
        setTimeout(() => {
            console.log('⚙️ Loading initial settings...');
            if (this.settingsManager) {
                this.settingsManager.loadLLMConfig();
                this.settingsManager.loadEmbeddingsConfig();
            }
        }, 1000);

        // Force news reload after 3 seconds (in case they're not loaded yet)
        setTimeout(() => {
            console.log('🔄 Reloading news after startup delay...');
            if (this.dashboardManager) {
                this.dashboardManager.loadInitialNews();
            }
        }, 3000);

        // ✅ Initialiser l'agent monitor ici
        // if (this.agentMonitor) {
        //     this.agentMonitor.init();
        //     console.log('============= agent Monitorinit');
        // }  // Disabled - Agent V2 section removed

        // Initialize signal notifications (loads modal + counters)
        setTimeout(() => {
            console.log('🎯 Initializing signal notifications...');
            if (this.signalNotifications) {
                this.signalNotifications.init();
            }
        }, 1500);

        console.log('FedEdgeAI setup complete');
    }

    /**
     * Load initial application data
     */
    async loadInitialData() {
        try {
            // Load dashboard data
            await this.dashboardManager.loadInitialDashboardData();

            // Load AI signals
            await this.signalsManager.loadAISignals();

            // Load wallets
            await this.walletManager.loadWalletsData();

            // Load simulations
            await this.tradingManager.loadSimulations();

            // Load initial prices
            await this.loadPrices();

            console.log('Initial data loaded successfully');
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    /**
     * Load cryptocurrency prices
     */
    async loadPrices() {
        try {
            const response = await fetch('/api/assets');
            if (!response.ok) {
                console.warn('Failed to fetch prices');
                return;
            }

            const data = await response.json();

            if (data.success && data.assets) {
                // Convert to price update format
                const prices = {};
                data.assets.forEach(asset => {
                    // Use asset.id (e.g., "bitcoin", "ethereum")
                    const assetId = asset.id;
                    if (assetId) {
                        prices[assetId] = {
                            usd: asset.current_price || 0,
                            usd_24h_change: asset.price_change_24h || 0,
                            market_cap: asset.market_cap || 0
                        };
                    }
                });

                console.log(`✅ Loaded prices for ${Object.keys(prices).length} assets`);

                // Update wallet manager with prices
                this.walletManager?.handlePriceUpdate({ payload: prices });

                // Update dashboard with prices
                this.dashboardManager?.updateMarketCapVisualization(prices);
            }
        } catch (error) {
            console.error('❌ Error loading prices:', error);
        }
    }

    /**
     * Setup auto-refresh intervals
     */
    setupAutoRefresh() {
        // Refresh signals every 5 minutes
        setInterval(() => {
            this.signalsManager.loadAISignals();
        }, 5 * 60 * 1000);

        // Refresh simulations every 30 seconds
        setInterval(() => {
            this.tradingManager.loadSimulations();
        }, 30 * 1000);

        // Refresh dashboard stats every 2 minutes
        setInterval(() => {
            this.dashboardManager.loadMarketStats();
        }, 2 * 60 * 1000);

        // Refresh prices every 30 seconds
        setInterval(() => {
            this.loadPrices();
        }, 30 * 1000);
    }

    /**
     * Setup sidebar navigation
     */
    setupSidebarNavigation() {
        console.log('Setting up sidebar navigation...');

        // Get all navigation items with data-page attribute
        const navItems = document.querySelectorAll('.sidebar-item[data-page]');

        console.log(`Found ${navItems.length} navigation items`);

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = item.getAttribute('data-page');

                console.log(`Navigation clicked: ${targetPage}`);

                if (targetPage) {
                    // Use switchToPage instead of navigateToPage (no reload)
                    this.switchToPage(targetPage);

                    // Update active state
                    navItems.forEach(nav => nav.classList.remove('active'));
                    item.classList.add('active');
                }
            });
        });
    }

    /**
     * Navigate to page
     */
    async navigateToPage(pageId) {
        console.log(`Navigating to page: ${pageId}`);

        // Get or create main content container
        let mainContent = document.querySelector('.main-content');
        if (!mainContent) {
            console.error('❌ Main content container not found');
            return;
        }

        // Show loading state
        mainContent.innerHTML = '<div style="text-align: center; padding: 50px; color: #9ca3af;">Loading...</div>';

        try {
            // Fetch page module
            const response = await fetch(`/pages/${pageId}.html`);

            if (!response.ok) {
                throw new Error(`Failed to load page: ${response.status} ${response.statusText}`);
            }

            const html = await response.text();

            // Create a wrapper div with content-page class
            mainContent.innerHTML = `<div class="content-page active" id="${pageId}-page">${html}</div>`;

            console.log(`✅ Loaded page module: ${pageId}.html`);

            // Re-initialize page-specific functionality after DOM update
            this.reinitializePageContent(pageId);

        } catch (error) {
            console.error(`❌ Error loading page ${pageId}:`, error);
            mainContent.innerHTML = `
                <div style="text-align: center; padding: 50px;">
                    <div style="color: #ef4444; font-size: 18px; margin-bottom: 10px;">⚠️ Error Loading Page</div>
                    <div style="color: #9ca3af; font-size: 14px;">${error.message}</div>
                    <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #3b82f6; border: none; border-radius: 6px; color: white; cursor: pointer;">
                        Reload Page
                    </button>
                </div>
            `;
        }
    }

    /**
     * Reinitialize page-specific content after dynamic loading
     * NOTE: Deprecated - We now preload all pages and use switchToPage() instead
     */
    reinitializePageContent(pageId) {
        console.log(`⚠️ reinitializePageContent called (deprecated) for: ${pageId}`);

        // NO LONGER RELOADING DATA ON NAVIGATION
        // Data is loaded ONCE at startup and refreshed periodically
        // This prevents unnecessary API calls when switching pages

        /* DEPRECATED CODE - Kept for reference
        switch(pageId) {
            case 'dashboard':
                // Reload dashboard data
                if (this.dashboardManager) {
                    this.dashboardManager.loadInitialDashboardData();
                }
                if (this.signalsManager) {
                    this.signalsManager.loadAISignals();
                }
                break;

            case 'wallets':
                // Reload wallet data
                if (this.walletManager) {
                    this.walletManager.loadWalletsData();
                }
                break;

            case 'simulations':
                // Reload simulations
                if (this.tradingManager) {
                    this.tradingManager.loadSimulations();
                }
                break;

            case 'bots':
                // Initialize bots page
                console.log('Bots page loaded');
                break;

            case 'knowledge':
                // Initialize knowledge page
                console.log('Knowledge page loaded');
                break;

            case 'collective-iq':
                // Initialize collective IQ page
                console.log('Collective IQ page loaded');
                break;

            case 'settings':
                // Initialize settings page
                console.log('Settings page loaded');
                // Render simulations in settings page
                this.tradingManager.renderSimulationsInSettings();
                // Load LLM configuration with small delay to ensure DOM is ready
                setTimeout(() => {
                    console.log('🤖 Loading LLM config after DOM ready...');
                    this.settingsManager.loadLLMConfig();
                }, 100);
                break;

            case 'knowledge':
                // Initialize knowledge page
                console.log('Knowledge page loaded');
                // Load knowledge stats automatically
                this.ragManager.loadKnowledgePageStats();
                break;

            default:
                console.warn(`No reinitialization handler for page: ${pageId}`);
        }
        */
    }

    /**
     * Setup modals
     */
    setupModals() {
        // Setup logs modal
        this.setupLogsModal();

        // Setup debug console
        this.setupDebugConsole();

        // Setup signal modal
        this.setupSignalModal();

        // Setup asset stats modal
        this.setupAssetStatsModal();

        // Setup world context modal
        this.setupWorldContextModal();

        // Setup finance market modal
        this.setupFinanceMarketModal();

        // Setup create simulation button
        this.setupCreateSimulationButton();

        // Setup add LLM button
        this.setupAddLLMButton();

        // Setup add Embedding button
        this.setupAddEmbeddingButton();
    }

    /**
     * Setup logs modal
     */
    setupLogsModal() {
        const logsBtn = document.getElementById('logs-button');
        const logsModal = document.getElementById('logs-modal');
        const logsClose = document.getElementById('logs-close');

        if (logsBtn && logsModal) {
            logsBtn.addEventListener('click', () => {
                logsModal.style.display = 'flex';
                this.updateLogsContent();
            });
        }

        if (logsClose && logsModal) {
            logsClose.addEventListener('click', () => {
                logsModal.style.display = 'none';
            });
        }
    }

    /**
     * Update logs content
     */
    updateLogsContent() {
        // This would fetch and display logs from the backend
        console.log('Updating logs content...');
    }

    /**
     * Setup debug console
     */
    setupDebugConsole() {
        const debugBtn = document.getElementById('debug-console-btn');
        const debugModal = document.getElementById('debug-console-modal');
        const debugClose = document.getElementById('debug-console-close');

        if (debugBtn && debugModal) {
            debugBtn.addEventListener('click', () => {
                debugModal.style.display = 'flex';
            });
        }

        if (debugClose && debugModal) {
            debugClose.addEventListener('click', () => {
                debugModal.style.display = 'none';
            });
        }
    }

    /**
     * Setup signal modal
     */
    setupSignalModal() {
        const signalModal = document.getElementById('signal-modal');
        const signalClose = document.getElementById('signal-close');

        if (signalClose && signalModal) {
            signalClose.addEventListener('click', () => {
                signalModal.style.display = 'none';
            });
        }
    }

    /**
     * Setup asset stats modal
     */
    setupAssetStatsModal() {
        const assetStatsModal = document.getElementById('asset-stats-modal');
        const assetStatsClose = document.getElementById('close-asset-stats-modal');

        if (assetStatsClose && assetStatsModal) {
            assetStatsClose.addEventListener('click', () => {
                // Destroy chart if exists
                if (this.assetChart) {
                    this.assetChart.destroy();
                    this.assetChart = null;
                }

                assetStatsModal.classList.remove('show');
                setTimeout(() => {
                    assetStatsModal.style.display = 'none';
                }, 300); // Wait for transition
            });
        }
    }

    /**
     * Show asset stats for symbol
     */
    async showAssetStatsForSymbol(symbol) {
        console.log(`Showing asset stats for: ${symbol}`);

        const modal = document.getElementById('asset-stats-modal');
        if (!modal) {
            console.error('❌ asset-stats-modal not found in DOM');
            alert(`Asset Stats Modal not found. Showing data in console instead.\n\nAsset: ${symbol}`);
            return;
        }

        modal.style.display = 'flex';
        modal.classList.add('show');
        console.log('✅ Modal display set to flex');

        // Show loading, hide content and error
        const loading = document.getElementById('asset-stats-loading');
        const content = document.getElementById('asset-stats-content');
        const error = document.getElementById('asset-stats-error');

        if (loading) loading.style.display = 'block';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'none';

        try {
            // Get current price data from wallet manager
            const prices = this.walletManager?.currentPrices || {};
            const assetData = prices[symbol];

            if (!assetData) {
                throw new Error(`No data available for ${symbol}`);
            }

            // Fetch chart data from API
            let chartData = null;
            try {
                const chartResponse = await fetch(`/api/assets/${symbol}/chart-data?days=1`);
                if (chartResponse.ok) {
                    const chartResult = await chartResponse.json();
                    if (chartResult.status === 'success') {
                        chartData = chartResult.chart_data;
                    }
                }
            } catch (chartError) {
                console.warn('Chart data not available:', chartError);
            }

            // Create analysis data from current prices
            const data = {
                status: 'success',
                analysis: {
                    asset_id: symbol,
                    period_days: 1,
                    stats: {
                        price_change_24h: assetData.usd_24h_change || 0,
                        volume_24h: assetData.volume_24h || 0,
                        market_cap: assetData.market_cap || 0,
                        current_price: assetData.usd || 0,
                        volatility: Math.abs(assetData.usd_24h_change || 0) // Simple volatility estimate
                    },
                    analysis_timestamp: new Date().toISOString(),
                    note: null
                }
            };

            // Hide loading, show content
            if (loading) loading.style.display = 'none';
            if (content) {
                content.style.display = 'block';
                this.displayAssetStatsData(content, data, chartData);
            }
        } catch (error) {
            console.error('Error loading asset stats:', error);

            // Hide loading, show error
            if (loading) loading.style.display = 'none';
            if (error) {
                error.style.display = 'block';
                error.innerHTML = `
                    <div style="font-size: 24px; margin-bottom: 10px;">❌</div>
                    <div>Failed to load asset statistics</div>
                    <div style="font-size: 12px; color: #9ca3af; margin-top: 8px;">${error.message}</div>
                `;
            }
        }
    }

    /**
     * Display asset stats data
     */
    displayAssetStatsData(container, data, chartData) {
        const analysis = data.analysis || {};
        const stats = analysis.stats || {};
        const assetId = analysis.asset_id || 'Unknown';

        container.innerHTML = `
            <div style="padding: 20px;">
                <h2 style="margin-bottom: 20px; color: #fff;">
                    ${assetId.toUpperCase().replace(/-/g, ' ')} Analysis
                </h2>
                ${analysis.note ? `
                    <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 12px; margin-bottom: 16px; border-radius: 6px;">
                        <div style="font-size: 12px; color: #f59e0b;">
                            ⚠️ ${analysis.note}
                        </div>
                    </div>
                ` : ''}
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                    <div style="background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 16px; border-left: 3px solid #6366f1;">
                        <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">Current Price</div>
                        <div style="font-size: 24px; font-weight: 700; color: #fff;">
                            ${UIUtils.formatPrice(stats.current_price || 0)}
                        </div>
                    </div>
                    <div style="background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 16px; border-left: 3px solid #6366f1;">
                        <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">24h Price Change</div>
                        <div style="font-size: 24px; font-weight: 700; color: ${UIUtils.getValueColor(stats.price_change_24h || 0)};">
                            ${UIUtils.formatPercentage(stats.price_change_24h || 0)}
                        </div>
                    </div>
                    <div style="background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 16px; border-left: 3px solid #6366f1;">
                        <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">24h Volume</div>
                        <div style="font-size: 20px; font-weight: 700; color: #fff;">
                            ${UIUtils.formatMarketCap(stats.volume_24h || 0)}
                        </div>
                    </div>
                    <div style="background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 16px; border-left: 3px solid #6366f1;">
                        <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">Market Cap</div>
                        <div style="font-size: 20px; font-weight: 700; color: #fff;">
                            ${UIUtils.formatMarketCap(stats.market_cap || 0)}
                        </div>
                    </div>
                    <div style="background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 16px; border-left: 3px solid #6366f1;">
                        <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">Volatility</div>
                        <div style="font-size: 20px; font-weight: 700; color: #fff;">
                            ${UIUtils.formatPercentage(stats.volatility || 0)}
                        </div>
                    </div>
                </div>
                <div style="margin-top: 16px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 6px;">
                    <div style="font-size: 11px; color: #9ca3af;">
                        Analysis Period: ${analysis.period_days || 1} day(s) |
                        Updated: ${analysis.analysis_timestamp ? new Date(analysis.analysis_timestamp).toLocaleString() : 'N/A'}
                    </div>
                </div>
                ${chartData && chartData.labels && chartData.labels.length > 0 ? `
                    <div style="margin-top: 20px;">
                        <h3 style="color: #fff; margin-bottom: 12px; font-size: 16px;">📈 Price Chart (24h)</h3>
                        <div style="background: rgba(31, 41, 55, 0.5); border-radius: 8px; padding: 16px; height: 300px;">
                            <canvas id="asset-chart"></canvas>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        // Create chart if data is available
        if (chartData && chartData.labels && chartData.labels.length > 0) {
            setTimeout(() => this.createAssetChart(chartData), 100);
        }
    }

    /**
     * Create asset price chart
     */
    createAssetChart(chartData) {
        const canvas = document.getElementById('asset-chart');
        if (!canvas || !chartData) {
            console.warn('Cannot create chart:', { canvas: !!canvas, chartData: !!chartData });
            return;
        }

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
                    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                }),
                datasets: [{
                    label: 'Price (USD)',
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
                                return '$' + value.toLocaleString();
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

    /**
     * Setup world context modal
     */
    setupWorldContextModal() {
        const worldContextBtn = document.getElementById('world-context-btn');
        const worldContextModal = document.getElementById('world-context-modal');
        const worldContextClose = document.getElementById('close-world-context-modal');

        if (worldContextBtn && worldContextModal) {
            worldContextBtn.addEventListener('click', async () => {
                worldContextModal.style.display = 'flex';
                worldContextModal.classList.add('show');
                console.log('✅ World Context modal opened');

                // Load world context data
                await this.loadWorldContextData();
            });
        }

        if (worldContextClose && worldContextModal) {
            worldContextClose.addEventListener('click', () => {
                worldContextModal.classList.remove('show');
                setTimeout(() => {
                    worldContextModal.style.display = 'none';
                }, 300); // Wait for transition
            });
        }
    }

    /**
     * Load world context data
     */
    async loadWorldContextData() {
        const loading = document.getElementById('world-context-loading');
        const content = document.getElementById('world-context-content');

        try {
            // Show loading
            if (loading) loading.style.display = 'block';
            if (content) content.style.display = 'none';

            const response = await fetch('/api/world-context');
            if (!response.ok) throw new Error('Failed to fetch world context');

            const data = await response.json();
            const worldContext = data.world_context || {};

            // Hide loading, show content
            if (loading) loading.style.display = 'none';
            if (content) content.style.display = 'block';

            // Update last updated time
            const lastUpdated = document.getElementById('context-last-updated');
            if (lastUpdated) {
                lastUpdated.textContent = worldContext.last_updated || new Date().toLocaleString();
            }

            // Update summary
            const summary = document.getElementById('world-context-summary');
            if (summary) {
                summary.textContent = worldContext.world_summary || 'No world context data available yet.';
            }

            // Update sentiment (score is between -1.0 and +1.0)
            const sentimentScore = document.getElementById('sentiment-score');
            if (sentimentScore) {
                const score = worldContext.sentiment_score || 0;
                sentimentScore.textContent = score.toFixed(2);
                // Color based on sentiment: negative=red, neutral=yellow, positive=green
                sentimentScore.style.color = score > 0.2 ? '#10b981' : score < -0.2 ? '#ef4444' : '#f59e0b';
            }

            // Update key themes
            const themesContainer = document.getElementById('key-themes-container');
            if (themesContainer && worldContext.key_themes) {
                const themes = worldContext.key_themes;
                themesContainer.innerHTML = themes.length > 0 ? themes.map(theme => {
                    const themeText = typeof theme === 'string' ? theme : (theme.title || theme.name || 'Unknown');
                    const themeDesc = typeof theme === 'object' ? theme.description : '';
                    return `
                        <div style="background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px;">
                            <div style="color: #fff; font-weight: 600; margin-bottom: 4px;">${UIUtils.escapeHtml(themeText)}</div>
                            ${themeDesc ? `<div style="color: #9ca3af; font-size: 12px;">${UIUtils.escapeHtml(themeDesc)}</div>` : ''}
                        </div>
                    `;
                }).join('') : '<div style="color: #9ca3af; font-style: italic;">No themes identified</div>';
            }

        } catch (error) {
            console.error('Error loading world context:', error);

            // Hide loading
            if (loading) loading.style.display = 'none';

            // Show error in content
            if (content) {
                content.style.display = 'block';
                content.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #ef4444;">
                        <div style="font-size: 24px; margin-bottom: 10px;">❌</div>
                        <div>Failed to load world context data</div>
                        <div style="font-size: 12px; color: #9ca3af; margin-top: 8px;">${error.message}</div>
                    </div>
                `;
            }
        }
    }

    /**
     * Setup finance market modal
     */
    setupFinanceMarketModal() {
        const financeMarketBtn = document.getElementById('finance-market-btn');
        const financeMarketModal = document.getElementById('finance-market-modal');
        const financeMarketClose = document.getElementById('close-finance-market-modal');

        if (financeMarketBtn && financeMarketModal) {
            financeMarketBtn.addEventListener('click', async () => {
                financeMarketModal.style.display = 'flex';
                financeMarketModal.classList.add('show');
                console.log('✅ Finance Market modal opened');

                // Load market data
                await this.loadFinanceMarketData();
            });
        }

        if (financeMarketClose && financeMarketModal) {
            financeMarketClose.addEventListener('click', () => {
                financeMarketModal.classList.remove('show');
                setTimeout(() => {
                    financeMarketModal.style.display = 'none';
                }, 300); // Wait for transition
            });
        }
    }

    /**
     * Load finance market data
     */
    async loadFinanceMarketData() {
        try {
            const prices = this.walletManager?.currentPrices || {};

            if (Object.keys(prices).length === 0) {
                console.warn('No price data available for Finance Market modal');
                return;
            }

            // Calculate total market cap
            let totalMarketCap = 0;
            let total24hVolume = 0;
            const cryptos = [];

            Object.entries(prices).forEach(([id, data]) => {
                if (data.market_cap) {
                    totalMarketCap += data.market_cap;
                    cryptos.push({ id, ...data });
                }
                if (data.volume_24h) {
                    total24hVolume += data.volume_24h;
                }
            });

            // Sort by 24h change
            cryptos.sort((a, b) => (b.usd_24h_change || 0) - (a.usd_24h_change || 0));
            const topGainers = cryptos.slice(0, 10);
            const topLosers = cryptos.slice(-10).reverse();

            // Update the modal content (note: these are different elements than dashboard)
            const financeMarketModal = document.getElementById('finance-market-modal');
            const modalMarketCap = financeMarketModal?.querySelector('#total-market-cap');
            const modalVolume = financeMarketModal?.querySelector('#total-volume-24h');
            const modalBtcDom = financeMarketModal?.querySelector('#btc-dominance');
            const modalSentiment = financeMarketModal?.querySelector('#market-sentiment');

            if (modalMarketCap) modalMarketCap.textContent = UIUtils.formatMarketCap(totalMarketCap);
            if (modalVolume) modalVolume.textContent = total24hVolume > 0 ? UIUtils.formatMarketCap(total24hVolume) : 'N/A';

            if (prices.bitcoin && totalMarketCap > 0) {
                const btcDominance = (prices.bitcoin.market_cap / totalMarketCap) * 100;
                if (modalBtcDom) modalBtcDom.textContent = UIUtils.formatPercentage(btcDominance, 2);
            }

            if (modalSentiment) modalSentiment.textContent = 'Neutral';

            // Calculate performance distribution
            const gainers = cryptos.filter(c => (c.usd_24h_change || 0) > 0.5);
            const losers = cryptos.filter(c => (c.usd_24h_change || 0) < -0.5);
            const neutral = cryptos.filter(c => Math.abs(c.usd_24h_change || 0) <= 0.5);
            const total = cryptos.length;

            // Update performance distribution
            const gainsCount = document.getElementById('gains-count');
            const gainsPercentage = document.getElementById('gains-percentage');
            const lossesCount = document.getElementById('losses-count');
            const lossesPercentage = document.getElementById('losses-percentage');
            const neutralCount = document.getElementById('neutral-count');
            const neutralPercentage = document.getElementById('neutral-percentage');
            const totalAnalyzed = document.getElementById('total-analyzed');
            const financeLastUpdated = document.getElementById('finance-last-updated');

            if (gainsCount) gainsCount.textContent = gainers.length;
            if (gainsPercentage) gainsPercentage.textContent = `(${((gainers.length / total) * 100).toFixed(1)}%)`;
            if (lossesCount) lossesCount.textContent = losers.length;
            if (lossesPercentage) lossesPercentage.textContent = `(${((losers.length / total) * 100).toFixed(1)}%)`;
            if (neutralCount) neutralCount.textContent = neutral.length;
            if (neutralPercentage) neutralPercentage.textContent = `(${((neutral.length / total) * 100).toFixed(1)}%)`;
            if (totalAnalyzed) totalAnalyzed.textContent = total;
            if (financeLastUpdated) financeLastUpdated.textContent = new Date().toLocaleTimeString();

            // Populate top gainers
            const gainersContainer = document.getElementById('top-gainers-list');
            if (gainersContainer) {
                gainersContainer.innerHTML = topGainers.map(crypto => `
                    <div style="background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="color: #fff; font-weight: 600;">${crypto.id.toUpperCase()}</div>
                        <div style="color: #10b981; font-weight: 600;">+${UIUtils.formatPercentage(Math.abs(crypto.usd_24h_change || 0))}</div>
                    </div>
                `).join('');
            }

            // Populate top losers
            const losersContainer = document.getElementById('top-losers-list');
            if (losersContainer) {
                losersContainer.innerHTML = topLosers.map(crypto => `
                    <div style="background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="color: #fff; font-weight: 600;">${crypto.id.toUpperCase()}</div>
                        <div style="color: #ef4444; font-weight: 600;">${UIUtils.formatPercentage(crypto.usd_24h_change || 0)}</div>
                    </div>
                `).join('');
            }

            // Calculate and display sector performance
            const sectorsPerformanceContainer = document.getElementById('sectors-performance');
            if (sectorsPerformanceContainer) {
                // Define crypto sectors
                const sectors = {
                    "Layer 1": ["bitcoin", "ethereum", "solana", "cardano", "polkadot", "avalanche-2", "near", "cosmos", "fantom"],
                    "DeFi": ["uniswap", "aave", "compound-governance-token", "maker", "synthetix-network-token", "curve-dao-token", "1inch"],
                    "Layer 2": ["polygon", "optimism", "arbitrum"],
                    "Meme": ["dogecoin", "shiba-inu", "pepe", "floki"],
                    "AI": ["fetch-ai", "bittensor", "render-token", "ocean-protocol"],
                    "Gaming": ["axie-infinity", "the-sandbox", "decentraland", "immutable-x"],
                    "Storage": ["filecoin", "arweave", "siacoin"],
                    "Oracle": ["chainlink", "band-protocol", "api3"]
                };

                const sectorPerformance = {};

                // Calculate average performance per sector
                for (const [sectorName, cryptoIds] of Object.entries(sectors)) {
                    const sectorCryptos = cryptoIds
                        .map(id => prices[id])
                        .filter(crypto => crypto && crypto.usd_24h_change !== undefined);

                    if (sectorCryptos.length > 0) {
                        const avgChange = sectorCryptos.reduce((sum, crypto) => sum + (crypto.usd_24h_change || 0), 0) / sectorCryptos.length;
                        sectorPerformance[sectorName] = {
                            avgChange: avgChange,
                            count: sectorCryptos.length
                        };
                    }
                }

                // Sort sectors by performance
                const sortedSectors = Object.entries(sectorPerformance)
                    .sort(([, a], [, b]) => b.avgChange - a.avgChange);

                // Display sectors
                if (sortedSectors.length > 0) {
                    sectorsPerformanceContainer.innerHTML = sortedSectors.map(([sectorName, data]) => {
                        const color = data.avgChange > 0 ? '#10b981' : data.avgChange < 0 ? '#ef4444' : '#9ca3af';
                        const sign = data.avgChange > 0 ? '+' : '';
                        return `
                            <div style="
                                background: rgba(255,255,255,0.05);
                                padding: 12px;
                                border-radius: 8px;
                                border-left: 4px solid ${color};
                            ">
                                <div style="color: #fff; font-weight: 600; font-size: 13px; margin-bottom: 6px;">
                                    ${sectorName}
                                </div>
                                <div style="color: ${color}; font-weight: 700; font-size: 16px;">
                                    ${sign}${data.avgChange.toFixed(2)}%
                                </div>
                                <div style="color: #9ca3af; font-size: 11px; margin-top: 4px;">
                                    ${data.count} coins
                                </div>
                            </div>
                        `;
                    }).join('');
                } else {
                    sectorsPerformanceContainer.innerHTML = `
                        <div style="text-align: center; color: #9ca3af; padding: 20px; grid-column: 1 / -1;">
                            No sector data available
                        </div>
                    `;
                }
            }

        } catch (error) {
            console.error('Error loading finance market data:', error);
        }
    }

    /**
     * Setup settings modal
     */
    setupSettingsModal() {
        const settingsBtn = document.getElementById('settings-button');
        const settingsModal = document.getElementById('settings-modal');
        const settingsClose = document.getElementById('settings-close');

        if (settingsBtn && settingsModal) {
            settingsBtn.addEventListener('click', () => {
                settingsModal.style.display = 'flex';
            });
        }

        if (settingsClose && settingsModal) {
            settingsClose.addEventListener('click', () => {
                settingsModal.style.display = 'none';
            });
        }
    }

    /**
     * Setup config button (Scheduler Configuration)
     */
    setupConfigButton() {
        const configBtn = document.getElementById('scheduler-config-btn');

        if (configBtn) {
            configBtn.addEventListener('click', () => {
                console.log('⚙️ Config button clicked');
                this.showSchedulerConfig();
            });
            console.log('✅ Config button handler attached');
        } else {
            console.warn('⚠️ Config button not found in DOM (looking for scheduler-config-btn)');
        }
    }

    /**
     * Setup create simulation button
     */
    setupCreateSimulationButton() {
        const createSimBtn = document.getElementById('add-simulation-btn');

        if (createSimBtn) {
            createSimBtn.addEventListener('click', () => {
                console.log('🎮 Create simulation button clicked');
                this.tradingManager.showCreateSimulationModal();
            });
            console.log('✅ Create simulation button handler attached');
        } else {
            console.warn('⚠️ Create simulation button not found in DOM (looking for add-simulation-btn)');
        }
    }

    /**
     * Setup add LLM button
     */
    setupAddLLMButton() {
        const addLlmBtn = document.getElementById('add-llm-btn');

        if (addLlmBtn) {
            addLlmBtn.addEventListener('click', () => {
                console.log('🤖 Add LLM button clicked');
                this.settingsManager.showAddLLMModal();
            });
            console.log('✅ Add LLM button handler attached');
        } else {
            console.warn('⚠️ Add LLM button not found in DOM (looking for add-llm-btn)');
        }
    }

    /**
     * Setup add Embedding button
     */
    setupAddEmbeddingButton() {
        const addEmbeddingBtn = document.getElementById('add-embedding-btn');

        if (addEmbeddingBtn) {
            addEmbeddingBtn.addEventListener('click', () => {
                console.log('🧮 Add Embedding button clicked');
                this.settingsManager.showAddEmbeddingModal();
            });
            console.log('✅ Add Embedding button handler attached');
        } else {
            console.warn('⚠️ Add Embedding button not found in DOM (looking for add-embedding-btn)');
        }
    }

    /**
     * Show scheduler configuration modal
     */
    async showSchedulerConfig() {
        console.log('📋 showSchedulerConfig called');

        let data = null;

        try {
            const response = await fetch('/api/scheduler/status');
            if (response.ok) {
                data = await response.json();
            }
        } catch (error) {
            console.log('Scheduler status endpoint not available, showing static info');
        }

        // Find or create scheduler modal container
        let modal = document.getElementById('scheduler-config-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'scheduler-config-modal';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
            console.log('Created scheduler modal container');
        }

        // Build status section
        let statusHTML = '';
        if (data) {
            statusHTML = '<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 12px; margin-bottom: 16px;">' +
                '<div style="color: #10b981; font-size: 13px; font-weight: 600; margin-bottom: 8px;">✓ Scheduler Status: Active</div>' +
                '<div style="color: #9ca3af; font-size: 11px;">Last health check: ' + new Date().toLocaleTimeString() + '</div>' +
                '</div>';
        }

        const modalHTML =
            '<div class="modal-content" style="max-width: 700px;">' +
                '<div class="modal-header">' +
                    '<h2 style="color: #fff; margin: 0;">⚙️ Scheduler Configuration</h2>' +
                    '<span class="close-btn" id="close-scheduler-modal">&times;</span>' +
                '</div>' +
                '<div class="modal-body">' +
                    '<div style="background: rgba(31, 41, 55, 0.5); border-radius: 6px; padding: 16px; margin-bottom: 20px;">' +
                        '<h3 style="color: #fff; font-size: 14px; margin: 0 0 12px 0;">Scheduled Tasks</h3>' +
                        '<div style="font-size: 12px; color: #9ca3af;">' +
                            '<p style="margin-bottom: 8px;">The scheduler manages automated tasks:</p>' +
                            '<ul style="margin: 0; padding-left: 20px;">' +
                                '<li>Price updates every 10 minutes</li>' +
                                '<li>News collection every 10 minutes</li>' +
                                '<li>Trading signals scan every 3 minutes</li>' +
                                '<li>Performance updates every 8 minutes</li>' +
                                '<li>World context updates every 20 minutes</li>' +
                                '<li>Crypto registry updates daily at 2 AM</li>' +
                            '</ul>' +
                        '</div>' +
                    '</div>' +
                    statusHTML +
                    '<div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 6px; padding: 12px;">' +
                        '<p style="color: #9ca3af; font-size: 12px; margin: 0;">💡 Tip: Scheduler configuration can be modified in the backend settings.</p>' +
                    '</div>' +
                '</div>' +
            '</div>';

        modal.innerHTML = modalHTML;
        modal.style.display = 'flex';
        modal.classList.add('show');

        console.log('✅ Modal HTML set and displayed');

        // Attach close handler
        const closeBtn = document.getElementById('close-scheduler-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                console.log('Close button clicked');
                modal.classList.remove('show');
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 300);
            });
            console.log('✅ Close handler attached');
        } else {
            console.error('❌ Close button not found');
        }
    }

    /**
     * Show notification (reused from license)
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            z-index: 10001;
            max-width: 300px;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Preload all pages at startup
     */
    async preloadAllPages() {
        const pages = ['dashboard', 'wallets', 'simulations', 'bots', 'knowledge', 'collective-iq', 'settings'];
        const mainContent = document.querySelector('.main-content');

        if (!mainContent) {
            console.error('❌ Main content container not found');
            return;
        }

        console.log('📦 Preloading all pages...');

        // Clear existing content
        mainContent.innerHTML = '';

        // Load all pages in parallel
        const loadPromises = pages.map(async (pageId) => {
            try {
                const response = await fetch(`/pages/${pageId}.html`);
                if (!response.ok) {
                    console.warn(`⚠️ Could not preload page: ${pageId}`);
                    return null;
                }

                const html = await response.text();

                // Create page container (hidden by default)
                const pageDiv = document.createElement('div');
                pageDiv.className = 'content-page';
                pageDiv.id = `${pageId}-page`;
                pageDiv.style.display = 'none';
                pageDiv.innerHTML = html;

                mainContent.appendChild(pageDiv);

                console.log(`✅ Preloaded: ${pageId}`);
                return pageId;
            } catch (error) {
                console.error(`❌ Error preloading ${pageId}:`, error);
                return null;
            }
        });

        await Promise.all(loadPromises);
        console.log('✅ All pages preloaded');
    }

    /**
     * Switch to page (no reload, just show/hide)
     */
    switchToPage(pageId) {
        console.log(`🔄 Switching to page: ${pageId}`);

        // Hide all pages
        const allPages = document.querySelectorAll('.content-page');
        allPages.forEach(page => {
            page.style.display = 'none';
            page.classList.remove('active');
        });

        // Show target page
        const targetPage = document.getElementById(`${pageId}-page`);
        if (targetPage) {
            targetPage.style.display = 'block';
            targetPage.classList.add('active');
            console.log(`✅ Switched to: ${pageId}`);
        } else {
            console.error(`❌ Page not found: ${pageId}`);
        }

        // Update active navigation
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            if (item.dataset.page === pageId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        // Close WebSocket connection
        this.websocketManager.close();

        console.log('FedEdgeAI destroyed');
    }
}

// Make FedEdgeAI available globally
window.FedEdgeAI = FedEdgeAI;
