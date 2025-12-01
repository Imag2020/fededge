/**
 * Dashboard Manager Module
 * Handles dashboard stats, news, market updates, and visualizations
 */

import { UIUtils } from './ui-utils.js';

export class DashboardManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.newsPage = 1;
        this.newsLimit = 10;
        this.newsArticles = [];
    }

    /**
     * Load initial dashboard data
     */
    async loadInitialDashboardData() {
        try {
            // Load market stats
            await this.loadMarketStats();

            // Load initial news
            await this.loadInitialNews();

            console.log('Dashboard data loaded');
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    /**
     * Load market stats
     */
    async loadMarketStats() {
        try {
            // Use trading stats endpoint instead of market/stats
            const response = await fetch('/api/trading-stats');
            if (!response.ok) {
                console.warn('Trading stats endpoint not available');
                return;
            }

            const data = await response.json();
            if (data.success && data.stats) {
                this.updateDashboardStats(data.stats);
            }
        } catch (error) {
            console.error('Error loading market stats:', error);
        }
    }

    /**
     * Load initial news
     */
    async loadInitialNews(page = 1, limit = 10) {
        try {
            const response = await fetch(`/api/news?limit=${limit}`);
            if (!response.ok) throw new Error('Failed to fetch news');

            const data = await response.json();

            // Backend returns {success: true, articles: [...]}
            if (data.success) {
                this.newsArticles = data.articles || [];
            } else {
                this.newsArticles = [];
            }

            this.renderNews();
        } catch (error) {
            console.error('Error loading news:', error);
            this.showNewsError();
        }
    }


    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Update dashboard stats
     */
    updateDashboardStats(marketStats) {
        // Update total market cap
        const marketCapElement = document.getElementById('total-market-cap');
        if (marketCapElement && marketStats.total_market_cap) {
            marketCapElement.textContent = UIUtils.formatMarketCap(marketStats.total_market_cap);
        }

        // Update 24h volume
        const volumeElement = document.getElementById('total-volume-24h');
        if (volumeElement && marketStats.total_volume_24h) {
            volumeElement.textContent = UIUtils.formatMarketCap(marketStats.total_volume_24h);
            volumeElement.style.color = '#3b82f6';
        }

        // Update BTC dominance
        const btcDomElement = document.getElementById('btc-dominance');
        if (btcDomElement && marketStats.btc_dominance) {
            btcDomElement.textContent = UIUtils.formatPercentage(marketStats.btc_dominance);
        }

        // Update market sentiment (both gauge and text)
        if (marketStats.market_sentiment) {
            this.updateSentimentGauge(marketStats.market_sentiment);

            // Also update the sentiment text element
            const sentimentTextElement = document.getElementById('market-sentiment-text');
            if (sentimentTextElement) {
                const sentimentLabel = marketStats.market_sentiment.label || 'Neutral';
                const sentimentScore = marketStats.market_sentiment.score || 50;
                const sentimentColor = this.getSentimentColor(sentimentScore);

                sentimentTextElement.textContent = sentimentLabel;
                sentimentTextElement.style.color = sentimentColor;
            }
        }
    }

    /**
     * Update sentiment gauge (dashboard needle)
     */
    updateSentimentGauge(sentiment) {
        const needleElement = document.getElementById('sentiment-gauge-needle');
        if (!needleElement) {
            console.warn('Sentiment gauge needle element not found');
            return;
        }

        const sentimentValue = sentiment.score || 50;
        const sentimentLabel = sentiment.label || 'Neutral';

        // Calculate rotation angle
        // Score 0 = -90deg (left/bearish), Score 50 = 0deg (center), Score 100 = +90deg (right/bullish)
        const angle = ((sentimentValue - 50) / 50) * 90;

        // Apply rotation to needle
        needleElement.style.transform = `rotate(${angle}deg)`;

        console.log(`📊 Sentiment gauge updated: ${sentimentLabel} (${sentimentValue}/100) -> ${angle.toFixed(1)}°`);
    }

    /**
     * Get sentiment color based on score
     */
    getSentimentColor(score) {
        if (score >= 70) return '#10b981';
        if (score >= 40) return '#f59e0b';
        return '#ef4444';
    }

    /**
     * Render news articles
     */
    renderNews() {
        const newsContainer = document.getElementById('crypto-news');
        if (!newsContainer) {
            console.warn('crypto-news element not found');
            return;
        }

        if (!this.newsArticles || this.newsArticles.length === 0) {
            newsContainer.innerHTML = `
                <div style="text-align: center; color: #6b7280; padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📰</div>
                    <div>No news articles available</div>
                </div>
            `;
            return;
        }

        // Remove duplicates based on title
        const uniqueArticles = [];
        const seenTitles = new Set();

        for (const article of this.newsArticles) {
            if (!seenTitles.has(article.title)) {
                seenTitles.add(article.title);
                uniqueArticles.push(article);
            }
        }

        // Update last update time
        const newsUpdateTime = document.getElementById('news-last-update');
        if (newsUpdateTime) {
            newsUpdateTime.textContent = new Date().toLocaleTimeString();
        }

        newsContainer.innerHTML = uniqueArticles.map(article => `
            <div class="news-article" onclick="window.open('${article.url}', '_blank')" style="
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                cursor: pointer;
                border-left: 3px solid #3b82f6;
                transition: all 0.2s;
            " onmouseover="this.style.background='rgba(59, 130, 246, 0.1)'" onmouseout="this.style.background='rgba(0, 0, 0, 0.4)'">
                <div style="font-weight: 600; font-size: 13px; color: #fff; margin-bottom: 6px; line-height: 1.4;">
                    ${UIUtils.escapeHtml(article.title || 'Untitled')}
                </div>
                <div style="font-size: 12px; color: #9ca3af; margin-bottom: 8px; line-height: 1.5;">
                    ${UIUtils.escapeHtml((article.description || article.summary || article.content || '').substring(0, 120))}${(article.description || article.summary || article.content || '').length > 120 ? '...' : ''}
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #6b7280;">
                    <div>
                        ${UIUtils.escapeHtml(article.source || 'Unknown Source')}
                    </div>
                    <div>
                        ${UIUtils.formatTimestamp(article.published_at || article.timestamp || article.created_at)}
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Handle new article from WebSocket
     */
    handleNewArticle(data) {
        const article = data.payload || {};

        // Add to beginning of articles array
        this.newsArticles.unshift(article);

        // Keep only last 50 articles
        if (this.newsArticles.length > 50) {
            this.newsArticles = this.newsArticles.slice(0, 50);
        }

        // Re-render news
        this.renderNews();
    }

    /**
     * Handle news update from WebSocket (array of articles)
     */
    handleNewsUpdate(data) {
        const articles = data.payload || [];

        if (!Array.isArray(articles)) {
            console.warn('handleNewsUpdate received non-array payload:', articles);
            return;
        }

        console.log(`📰 Received ${articles.length} news articles via WebSocket`);

        // Replace all news articles with the new ones
        this.newsArticles = articles;

        // Re-render news
        this.renderNews();

        // Show notification
        UIUtils.showNotification(`${articles.length} news articles updated`, 'success', 2000);
    }

    /**
     * Handle stats update from WebSocket
     */
    handleStatsUpdate(data) {
        const payload = data.payload || {};

        if (payload.market_stats) {
            this.updateDashboardStats(payload.market_stats);
        }
    }

    /**
     * Handle market alert from WebSocket
     */
    handleMarketAlert(data) {
        const payload = data.payload || {};
        const alert = payload.alert || payload;

        // Show alert notification
        const message = alert.message || `${alert.ticker}: ${alert.type}`;
        const type = alert.severity === 'high' ? 'warning' : 'info';

        UIUtils.showNotification(message, type, 5000);

        // Create alert element in UI if container exists
        const alertsContainer = document.getElementById('market-alerts');
        if (alertsContainer) {
            const alertElement = this.createAlertElement(alert);
            alertsContainer.insertAdjacentHTML('afterbegin', alertElement);

            // Keep only last 10 alerts
            const alerts = alertsContainer.querySelectorAll('.alert-item');
            if (alerts.length > 10) {
                alerts[alerts.length - 1].remove();
            }
        }
    }

    /**
     * Create alert element
     */
    createAlertElement(alert) {
        const severityColor = {
            'high': '#ef4444',
            'medium': '#f59e0b',
            'low': '#3b82f6'
        }[alert.severity] || '#6b7280';

        return `
            <div class="alert-item" style="
                background: linear-gradient(135deg, ${severityColor}22, ${severityColor}11);
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
                border-left: 4px solid ${severityColor};
            ">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">
                            ${UIUtils.escapeHtml(alert.ticker || 'Market Alert')}
                        </div>
                        <div style="font-size: 14px; color: #6b7280;">
                            ${UIUtils.escapeHtml(alert.message || alert.type)}
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #9ca3af;">
                        ${UIUtils.formatTimestamp(alert.timestamp)}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Update market cap visualization
     */
    updateMarketCapVisualization(prices) {
        const vizContainer = document.getElementById('market-cap-visualization');
        if (!vizContainer) {
            console.warn('market-cap-visualization element not found');
            return;
        }

        // Calculate total market cap
        let totalMarketCap = 0;
        const cryptos = [];

        Object.entries(prices).forEach(([id, data]) => {
            if (data.market_cap) {
                totalMarketCap += data.market_cap;
                cryptos.push({ id, ...data });
            }
        });

        // Sort by market cap
        cryptos.sort((a, b) => b.market_cap - a.market_cap);

        // Take top 10
        const topCryptos = cryptos.slice(0, 10);

        // Render visualization in a scrollable container
        vizContainer.innerHTML = `
            <div style="max-height: 220px; overflow-y: auto; padding: 0 16px;">
                ${topCryptos.map((crypto, index) => {
                    const percentage = (crypto.market_cap / totalMarketCap) * 100;
                    return this.createMarketCapBlock(crypto, percentage, index);
                }).join('')}
            </div>
        `;

        // Update total market cap in stats
        this.updateMarketStats(totalMarketCap);
    }

    /**
     * Update market stats display
     * NOTE: Volume 24h and Sentiment are managed by updateDashboardStats() from API
     * This function only updates Market Cap visualization
     */
    updateMarketStats(totalMarketCap) {
        const marketCapElement = document.getElementById('total-market-cap');
        if (marketCapElement && totalMarketCap > 0) {
            marketCapElement.textContent = UIUtils.formatMarketCap(totalMarketCap);
            marketCapElement.style.color = '#10b981';
        }

        // Calculate BTC dominance if we have BTC price data
        const prices = this.fedEdgeAI?.walletManager?.currentPrices || {};
        if (prices.bitcoin && totalMarketCap > 0) {
            const btcDominance = (prices.bitcoin.market_cap / totalMarketCap) * 100;
            const btcDomElement = document.getElementById('btc-dominance');
            if (btcDomElement) {
                btcDomElement.textContent = UIUtils.formatPercentage(btcDominance, 2);
                btcDomElement.style.color = '#f59e0b';
            }
        }

        // DO NOT update volume 24h here - it comes from /api/trading-stats via updateDashboardStats()
        // DO NOT update sentiment here - it comes from /api/trading-stats via updateDashboardStats()
    }

    /**
     * Create market cap block
     */
    createMarketCapBlock(crypto, percentage, index) {
        const colors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16'
        ];
        const color = colors[index % colors.length];

        return `
            <div style="
                background: linear-gradient(135deg, ${color}, ${color}dd);
                border-radius: 6px;
                padding: 8px;
                margin-bottom: 6px;
                color: white;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <div style="font-weight: 700; font-size: 12px;">
                        ${crypto.id.toUpperCase()}
                    </div>
                    <div style="font-weight: 600; font-size: 11px;">
                        ${UIUtils.formatPercentage(percentage)}
                    </div>
                </div>
                <div style="background: rgba(255, 255, 255, 0.3); border-radius: 3px; height: 4px; overflow: hidden;">
                    <div style="background: white; height: 100%; width: ${percentage}%;"></div>
                </div>
                <div style="font-size: 10px; margin-top: 4px; opacity: 0.9;">
                    ${UIUtils.formatMarketCap(crypto.market_cap)}
                </div>
            </div>
        `;
    }

    /**
     * Show news error
     */
    showNewsError() {
        const newsContainer = document.getElementById('crypto-news');
        if (!newsContainer) return;

        UIUtils.showError(newsContainer, 'Failed to load news articles');
    }
}
