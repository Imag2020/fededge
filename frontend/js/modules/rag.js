/**
 * Wallet Manager Module
 * Handles wallet operations, holdings, and performance tracking
 */

import { UIUtils } from './ui-utils.js';

export class RagManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
       
    }

    /**
     * Setup  interface event listeners
     */
   setupKnowledgeBase() {
        console.log('🧠 Setup Knowledge Base interface...');

        // Bouton refresh
        const refreshBtn = document.getElementById('knowledge-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('🔄 Actualisation des stats Knowledge Base...');
                this.loadKnowledgeStats();
            });
        }

        // Bouton recherche
        const searchBtn = document.getElementById('knowledge-search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                console.log('🔍 Ouverture interface de recherche...');
                this.toggleKnowledgeSearch();
            });
        }

        // Bouton submit recherche
        const searchSubmitBtn = document.getElementById('knowledge-search-submit');
        if (searchSubmitBtn) {
            searchSubmitBtn.addEventListener('click', () => {
                this.performKnowledgeSearch();
            });
        }

        // Enter sur input de recherche
        const searchInput = document.getElementById('knowledge-search-input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performKnowledgeSearch();
                }
            });
        }

        // Setup de la page Knowledge dédiée uniquement
        this.setupKnowledgePage();
    }


    // ==================

    async loadKnowledgeStats() {
        console.log('📊 Chargement des statistiques Knowledge Base...');

        try {
            const response = await fetch('/api/knowledge/stats');
            const data = await response.json();

            if (data.status === "success") {
                console.log('✅ Stats Knowledge Base reçues:', data);
                this.updateKnowledgeStatsDisplay(data);
            } else {
                console.error('❌ Error API stats:', data.error);
                this.showKnowledgeError('Error de chargement des statistiques');
            }
        } catch (error) {
            console.error('❌ Error chargement stats Knowledge Base:', error);
            this.showKnowledgeError('Impossible de charger les statistiques');
        }
    }

    updateKnowledgeStatsDisplay(stats) {
        console.log('📊 Mise à jour affichage stats:', stats);

        // Vector Database Stats (ChromaDB format)
        const vectorDb = stats.knowledge_stats?.vector_database;

        const vectorDbStatus = document.getElementById('vector-db-status');
        if (vectorDbStatus) {
            vectorDbStatus.textContent = vectorDb?.status || 'Inconnu';
            vectorDbStatus.style.color = vectorDb?.status === 'healthy' ? '#10b981' : '#ef4444';
        }

        const newsEmbeddingsCount = document.getElementById('news-embeddings-count');
        if (newsEmbeddingsCount) {
            newsEmbeddingsCount.textContent = vectorDb?.news_embeddings?.toLocaleString() || '0';
        }

        const cryptoKnowledgeCount = document.getElementById('crypto-knowledge-count');
        if (cryptoKnowledgeCount) {
            cryptoKnowledgeCount.textContent = vectorDb?.crypto_seed_knowledge?.toLocaleString() || '0';
        }

        const totalVectorsCount = document.getElementById('total-vectors-count');
        if (totalVectorsCount) {
            totalVectorsCount.textContent = vectorDb?.total_vectors?.toLocaleString() || '0';
        }

        // News Database Stats (nouveau format)
        const newsDb = stats.knowledge_stats?.news_database;

        const totalArticlesCount = document.getElementById('total-articles-count');
        if (totalArticlesCount) {
            totalArticlesCount.textContent = newsDb?.total_articles?.toLocaleString() || '0';
        }

        const recentArticlesCount = document.getElementById('recent-articles-count');
        if (recentArticlesCount) {
            recentArticlesCount.textContent = newsDb?.recent_articles_7d?.toLocaleString() || '0';
        }

        // Training Datasets Stats (nouveau format)
        const datasets = stats.knowledge_stats?.training_datasets;

        const worldStateSessions = document.getElementById('world-state-sessions');
        if (worldStateSessions) {
            worldStateSessions.textContent = datasets?.world_state?.total_sessions?.toLocaleString() || '0';
        }

        const candidatesSessions = document.getElementById('candidates-sessions');
        if (candidatesSessions) {
            candidatesSessions.textContent = datasets?.candidates_trader?.total_sessions?.toLocaleString() || '0';
        }

        const deciderSessions = document.getElementById('decider-sessions');
        if (deciderSessions) {
            deciderSessions.textContent = datasets?.decider_trader?.total_sessions?.toLocaleString() || '0';
        }
    }

    showKnowledgeError(message) {
        console.error('❌ Affichage erreur Knowledge Base:', message);

        // Mettre toutes les stats à "Error"
        const errorElements = [
            'vector-db-status', 'news-embeddings-count', 'crypto-knowledge-count',
            'total-vectors-count', 'total-articles-count', 'recent-articles-count',
            'world-state-sessions', 'candidates-sessions', 'decider-sessions'
        ];

        errorElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = 'Error';
                element.style.color = '#ef4444';
            }
        });
    }

    toggleKnowledgeSearch() {
        const searchInterface = document.getElementById('knowledge-search-interface');
        if (searchInterface) {
            const isVisible = searchInterface.style.display !== 'none';
            searchInterface.style.display = isVisible ? 'none' : 'block';

            if (!isVisible) {
                // Focus sur l'input de recherche
                const searchInput = document.getElementById('knowledge-search-input');
                if (searchInput) {
                    setTimeout(() => searchInput.focus(), 100);
                }
            }
        }
    }

    async performKnowledgeSearch() {
        const searchInput = document.getElementById('knowledge-search-input');
        const resultsContainer = document.getElementById('knowledge-search-results');

        if (!searchInput || !resultsContainer) {
            console.error('❌ Éléments de recherche non trouvés');
            return;
        }

        const query = searchInput.value.trim();
        if (!query) {
            alert('Veuillez saisir une requête de recherche');
            return;
        }

        console.log('🔍 Recherche Knowledge Base:', query);

        // Afficher le loading
        resultsContainer.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #9ca3af;">
                <div style="font-size: 24px; margin-bottom: 10px;">⏳</div>
                <div>Recherche en cours...</div>
            </div>
        `;
        resultsContainer.style.display = 'block';

        try {
            const response = await fetch(`/api/knowledge/search?query=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.status === "success" && data.results) {
                console.log('✅ Résultats de recherche reçus:', data.results);
                this.displayKnowledgeSearchResults(data.results);
            } else {
                console.error('❌ Error API recherche:', data.error);
                this.showKnowledgeSearchError('No results found');
            }
        } catch (error) {
            console.error('❌ Error recherche Knowledge Base:', error);
            this.showKnowledgeSearchError('Error de recherche');
        }
    }

    displayKnowledgeSearchResults(results) {
        const resultsContainer = document.getElementById('knowledge-search-results');
        if (!resultsContainer) return;

        if (!results || results.length === 0) {
            this.showKnowledgeSearchError('Aucun résultat trouvé');
            return;
        }

        let resultsHtml = '';

        results.forEach((result, index) => {
            const resultId = `knowledge-result-${index}`;
            const contentPreview = result.content?.substring(0, 200) || '';
            const hasMoreContent = result.content && result.content.length > 200;
            const isUrl = result.metadata?.url && result.metadata.url.startsWith('http');

            console.log(`DEBUG Result ${index}:`, {
                title: result.title,
                hasMoreContent,
                contentLength: result.content?.length,
                isUrl,
                url: result.metadata?.url
            });

            resultsHtml += `
            <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 6px;">
                    <div style="font-weight: 600; color: #fff; font-size: 13px;">
                        ${result.title || result.metadata?.title || 'Document'}`;

            if (isUrl) {
                resultsHtml += ` <a href="${result.metadata.url}" target="_blank" style="color: #60a5fa; text-decoration: none; margin-left: 8px; font-size: 11px;">🔗 Lien original</a>`;
            }

            resultsHtml += `
                    </div>
                    <div style="color: #8b5cf6; font-size: 11px;">Score: ${(result.score * 100).toFixed(1)}%</div>
                </div>
                <div id="${resultId}-preview" style="color: #d1d5db; font-size: 12px; line-height: 1.4;">
                    ${contentPreview}${hasMoreContent ? '...' : ''}
                </div>`;

            if (hasMoreContent) {
                // Échapper le contenu HTML pour éviter les problèmes
                const escapedContent = result.content
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');

                resultsHtml += `
                <div id="${resultId}-full" style="color: #d1d5db; font-size: 12px; line-height: 1.4; display: none;">${escapedContent}</div>
                <button onclick="window.appManager.toggleKnowledgeContent('${resultId}')" style="background: #1f2937; border: 1px solid #374151; color: #60a5fa; padding: 4px 8px; border-radius: 4px; font-size: 11px; margin-top: 6px; cursor: pointer;" id="${resultId}-toggle">Voir plus</button>`;
            }

            resultsHtml += `
                <div style="margin-top: 6px; font-size: 10px; color: #9ca3af; display: flex; justify-content: space-between;">
                    <span>Source: ${result.source || result.metadata?.source || 'knowledge_base'}</span>`;

            if (result.metadata?.timestamp) {
                resultsHtml += `<span>Date: ${new Date(result.metadata.timestamp).toLocaleDateString()}</span>`;
            }

            resultsHtml += `
                </div>
            </div>`;
        });

        resultsContainer.innerHTML = resultsHtml;
    }

    showKnowledgeSearchError(message) {
        const resultsContainer = document.getElementById('knowledge-search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #ef4444;">
                    <div style="font-size: 24px; margin-bottom: 10px;">❌</div>
                    <div>${message}</div>
                </div>
            `;
            resultsContainer.style.display = 'block';
        }
    }

    toggleKnowledgeContent(resultId) {
        const previewElement = document.getElementById(`${resultId}-preview`);
        const fullElement = document.getElementById(`${resultId}-full`);
        const toggleButton = document.getElementById(`${resultId}-toggle`);

        if (!previewElement || !fullElement || !toggleButton) return;

        if (fullElement.style.display === 'none') {
            // Afficher le contenu complet
            previewElement.style.display = 'none';
            fullElement.style.display = 'block';
            toggleButton.textContent = 'Voir moins';
        } else {
            // Afficher le preview
            previewElement.style.display = 'block';
            fullElement.style.display = 'none';
            toggleButton.textContent = 'Voir plus';
        }
    }

    setupKnowledgePage() {
        console.log('🧠 Setup Knowledge Page dédiée...');

        // Bouton refresh page dédiée
        const pageRefreshBtn = document.getElementById('knowledge-page-refresh-btn');
        if (pageRefreshBtn) {
            pageRefreshBtn.addEventListener('click', () => {
                console.log('🔄 Actualisation des stats Knowledge Page...');
                this.loadKnowledgePageStats();
            });
        }

        // Bouton recherche page dédiée
        const pageSearchBtn = document.getElementById('knowledge-page-search-btn');
        if (pageSearchBtn) {
            pageSearchBtn.addEventListener('click', () => {
                console.log('🔍 Ouverture interface de recherche page...');
                this.toggleKnowledgePageSearch();
            });
        }

        // Bouton ajouter documents
        const addDocumentBtn = document.getElementById('knowledge-page-add-document-btn');
        if (addDocumentBtn) {
            addDocumentBtn.addEventListener('click', () => {
                console.log('📄 Ouverture interface d\'upload de documents...');
                this.toggleKnowledgePageUpload();
            });
        }

        // Bouton submit recherche page dédiée
        const pageSearchSubmitBtn = document.getElementById('knowledge-page-search-submit');
        if (pageSearchSubmitBtn) {
            pageSearchSubmitBtn.addEventListener('click', () => {
                this.performKnowledgePageSearch();
            });
        }

        // Enter sur input de recherche page dédiée
        const pageSearchInput = document.getElementById('knowledge-page-search-input');
        if (pageSearchInput) {
            pageSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performKnowledgePageSearch();
                }
            });
        }
    }

    async loadKnowledgePageStats() {
        console.log('📊 Chargement des statistiques Knowledge Page...');

        try {
            const response = await fetch('/api/knowledge/stats');
            const data = await response.json();

            if (data.status === "success") {
                console.log('✅ Stats Knowledge Page reçues:', data);
                this.updateKnowledgePageStatsDisplay(data);
            } else {
                console.error('❌ Error API stats page:', data.error);
                this.showKnowledgePageError('Error de chargement des statistiques');
            }
        } catch (error) {
            console.error('❌ Error chargement stats Knowledge Page:', error);
            this.showKnowledgePageError('Impossible de charger les statistiques');
        }
    }

    updateKnowledgePageStatsDisplay(stats) {
        console.log('📊 Mise à jour affichage stats page:', stats);

        // Vector Database Stats (ChromaDB format)
        const vectorDb = stats.knowledge_stats?.vector_database;

        const vectorDbStatus = document.getElementById('knowledge-page-vector-db-status');
        if (vectorDbStatus) {
            vectorDbStatus.textContent = vectorDb?.status || 'Inconnu';
            vectorDbStatus.style.color = vectorDb?.status === 'healthy' ? '#10b981' : '#ef4444';
        }

        const newsEmbeddingsCount = document.getElementById('knowledge-page-news-embeddings-count');
        if (newsEmbeddingsCount) {
            newsEmbeddingsCount.textContent = vectorDb?.news_embeddings?.toLocaleString() || '0';
        }

        const cryptoKnowledgeCount = document.getElementById('knowledge-page-crypto-knowledge-count');
        if (cryptoKnowledgeCount) {
            cryptoKnowledgeCount.textContent = vectorDb?.crypto_seed_knowledge?.toLocaleString() || '0';
        }

        const totalVectorsCount = document.getElementById('knowledge-page-total-vectors-count');
        if (totalVectorsCount) {
            totalVectorsCount.textContent = vectorDb?.total_vectors?.toLocaleString() || '0';
        }

        // News Database Stats (nouveau format)
        const newsDb = stats.knowledge_stats?.news_database;

        const totalArticlesCount = document.getElementById('knowledge-page-total-articles-count');
        if (totalArticlesCount) {
            totalArticlesCount.textContent = newsDb?.total_articles?.toLocaleString() || '0';
        }

        const recentArticlesCount = document.getElementById('knowledge-page-recent-articles-count');
        if (recentArticlesCount) {
            recentArticlesCount.textContent = newsDb?.recent_articles_7d?.toLocaleString() || '0';
        }

        // News last updated
        const newsLastUpdated = document.getElementById('knowledge-page-news-last-updated');
        if (newsLastUpdated) {
            if (newsDb?.last_updated) {
                const date = new Date(newsDb.last_updated);
                newsLastUpdated.textContent = date.toLocaleString('fr-FR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } else {
                newsLastUpdated.textContent = '-';
            }
        }

        // Training Datasets Stats (nouveau format)
        const datasets = stats.knowledge_stats?.training_datasets;

        const worldStateSessions = document.getElementById('knowledge-page-world-state-sessions');
        if (worldStateSessions) {
            worldStateSessions.textContent = datasets?.world_state?.total_sessions?.toLocaleString() || '0';
        }

        const candidatesSessions = document.getElementById('knowledge-page-candidates-sessions');
        if (candidatesSessions) {
            candidatesSessions.textContent = datasets?.candidates_trader?.total_sessions?.toLocaleString() || '0';
        }

        const deciderSessions = document.getElementById('knowledge-page-decider-sessions');
        if (deciderSessions) {
            deciderSessions.textContent = datasets?.decider_trader?.total_sessions?.toLocaleString() || '0';
        }

        // Datasets last updated
        const datasetsLastUpdated = document.getElementById('knowledge-page-datasets-last-updated');
        if (datasetsLastUpdated) {
            if (datasets?.last_updated) {
                const date = new Date(datasets.last_updated);
                datasetsLastUpdated.textContent = date.toLocaleString('fr-FR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } else {
                datasetsLastUpdated.textContent = '-';
            }
        }
    }

    showKnowledgePageError(message) {
        console.error('❌ Affichage erreur Knowledge Page:', message);

        // Mettre toutes les stats à "Error"
        const errorElements = [
            'knowledge-page-vector-db-status', 'knowledge-page-news-embeddings-count', 'knowledge-page-crypto-knowledge-count',
            'knowledge-page-total-vectors-count', 'knowledge-page-total-articles-count', 'knowledge-page-recent-articles-count',
            'knowledge-page-world-state-sessions', 'knowledge-page-candidates-sessions', 'knowledge-page-decider-sessions'
        ];

        errorElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = 'Error';
                element.style.color = '#ef4444';
            }
        });
    }

    toggleKnowledgePageSearch() {
        const searchInterface = document.getElementById('knowledge-page-search-interface');
        if (searchInterface) {
            const isVisible = searchInterface.style.display !== 'none';
            searchInterface.style.display = isVisible ? 'none' : 'block';

            if (!isVisible) {
                // Focus sur l'input de recherche
                const searchInput = document.getElementById('knowledge-page-search-input');
                if (searchInput) {
                    setTimeout(() => searchInput.focus(), 100);
                }
            }
        }
    }

    async performKnowledgePageSearch() {
        const searchInput = document.getElementById('knowledge-page-search-input');
        const resultsContainer = document.getElementById('knowledge-page-search-results');

        if (!searchInput || !resultsContainer) {
            console.error('❌ Éléments de recherche page non trouvés');
            return;
        }

        const query = searchInput.value.trim();
        if (!query) {
            alert('Veuillez saisir une requête de recherche');
            return;
        }

        console.log('🔍 Recherche Knowledge Page:', query);

        // Afficher le loading
        resultsContainer.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #9ca3af;">
                <div style="font-size: 24px; margin-bottom: 10px;">⏳</div>
                <div>Recherche en cours...</div>
            </div>
        `;
        resultsContainer.style.display = 'block';

        try {
            const response = await fetch(`/api/knowledge/search?query=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.status === "success" && data.results) {
                console.log('✅ Résultats de recherche page reçus:', data.results);
                this.displayKnowledgePageSearchResults(data.results);
            } else {
                console.error('❌ Error API recherche page:', data.error);
                this.showKnowledgePageSearchError('No results found');
            }
        } catch (error) {
            console.error('❌ Error recherche Knowledge Page:', error);
            this.showKnowledgePageSearchError('Error de recherche');
        }
    }

    displayKnowledgePageSearchResults(results) {
        const resultsContainer = document.getElementById('knowledge-page-search-results');
        if (!resultsContainer) return;

        if (!results || results.length === 0) {
            this.showKnowledgePageSearchError('No results found');
            return;
        }

        const resultsHtml = results.map(result => `
            <div style="
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 6px;">
                    <div style="font-weight: 600; color: #fff; font-size: 13px;">
                        ${result.title || 'Document'}
                    </div>
                    <div style="color: #8b5cf6; font-size: 11px;">
                        Score: ${(result.score * 100).toFixed(1)}%
                    </div>
                </div>
                <div style="color: #d1d5db; font-size: 12px; line-height: 1.4;">
                    ${result.content?.substring(0, 200)}${result.content?.length > 200 ? '...' : ''}
                </div>
                ${result.source ? `
                    <div style="margin-top: 6px; font-size: 10px; color: #9ca3af;">
                        Source: ${result.source}
                    </div>
                ` : ''}
            </div>
        `).join('');

        resultsContainer.innerHTML = resultsHtml;
    }

    showKnowledgePageSearchError(message) {
        const resultsContainer = document.getElementById('knowledge-page-search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #ef4444;">
                    <div style="font-size: 24px; margin-bottom: 10px;">❌</div>
                    <div>${message}</div>
                </div>
            `;
            resultsContainer.style.display = 'block';
        }
    }

    // ============== DOCUMENT UPLOAD FUNCTIONS ==============

    toggleKnowledgePageUpload() {
        const uploadInterface = document.getElementById('knowledge-page-upload-interface');
        if (uploadInterface) {
            const isVisible = uploadInterface.style.display !== 'none';
            uploadInterface.style.display = isVisible ? 'none' : 'block';

            if (!isVisible) {
                this.setupDocumentUploadHandlers();
            }
        }
    }

    setupDocumentUploadHandlers() {
        // Upload tabs
        const textTab = document.getElementById('upload-tab-text');
        const fileTab = document.getElementById('upload-tab-file');
        const urlTab = document.getElementById('upload-tab-url');

        [textTab, fileTab, urlTab].forEach(tab => {
            if (tab) {
                tab.addEventListener('click', (e) => {
                    this.switchUploadTab(e.target.id.split('-').pop());
                });
            }
        });

        // Text upload
        const textSubmit = document.getElementById('upload-text-submit');
        if (textSubmit) {
            textSubmit.addEventListener('click', () => this.handleTextUpload());
        }

        // File upload
        const fileInput = document.getElementById('file-input');
        const fileDropZone = document.getElementById('file-drop-zone');
        const fileSubmit = document.getElementById('upload-file-submit');

        if (fileDropZone) {
            fileDropZone.addEventListener('click', () => fileInput?.click());

            // Drag and drop
            fileDropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                fileDropZone.style.borderColor = '#f59e0b';
            });

            fileDropZone.addEventListener('dragleave', () => {
                fileDropZone.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            });

            fileDropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                fileDropZone.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileSelection(files[0]);
                }
            });
        }

        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelection(e.target.files[0]);
                }
            });
        }

        if (fileSubmit) {
            fileSubmit.addEventListener('click', () => this.handleFileUpload());
        }

        // URL upload
        const urlSubmit = document.getElementById('upload-url-submit');
        if (urlSubmit) {
            urlSubmit.addEventListener('click', () => this.handleUrlUpload());
        }
    }

    switchUploadTab(tabType) {
        // Update tab styles
        document.querySelectorAll('.upload-tab').forEach(tab => {
            tab.style.color = '#9ca3af';
            tab.style.borderBottomColor = 'transparent';
        });

        const activeTab = document.getElementById(`upload-tab-${tabType}`);
        if (activeTab) {
            activeTab.style.color = '#f59e0b';
            activeTab.style.borderBottomColor = '#f59e0b';
        }

        // Switch content
        document.querySelectorAll('.upload-content').forEach(content => {
            content.style.display = 'none';
        });

        const activeContent = document.getElementById(`upload-content-${tabType}`);
        if (activeContent) {
            activeContent.style.display = 'block';
        }
    }

    handleFileSelection(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = ['.pdf', '.txt', '.doc', '.docx'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();

        if (file.size > maxSize) {
            alert('Le fichier est trop volumineux (max 10MB)');
            return;
        }

        if (!allowedTypes.includes(fileExt)) {
            alert('Type de fichier non supporté. Utilisez: PDF, TXT, DOC, DOCX');
            return;
        }

        // Update UI
        const fileDropZone = document.getElementById('file-drop-zone');
        const fileSelected = document.getElementById('file-selected');
        const fileSubmit = document.getElementById('upload-file-submit');

        if (fileDropZone) fileDropZone.style.display = 'none';
        if (fileSelected) {
            fileSelected.textContent = `✅ ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            fileSelected.style.display = 'block';
        }
        if (fileSubmit) {
            fileSubmit.disabled = false;
            fileSubmit.style.opacity = '1';
        }

        this.selectedFile = file;
    }

    async handleTextUpload() {
        const title = document.getElementById('text-title')?.value.trim();
        const content = document.getElementById('text-content')?.value.trim();

        if (!title || !content) {
            alert('Veuillez remplir le titre et le contenu');
            return;
        }

        this.showUploadProgress('Ajout du texte à la base RAG...', 50);

        try {
            const response = await fetch('/api/knowledge/add-text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    source: 'user_upload'
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showUploadProgress('Texte ajouté avec succès!', 100);
                setTimeout(() => {
                    this.hideUploadProgress();
                    this.clearTextForm();
                    this.loadKnowledgePageStats(); // Refresh stats
                }, 2000);
            } else {
                throw new Error(data.message || 'Error lors de l\'ajout');
            }
        } catch (error) {
            console.error('❌ Error upload texte:', error);
            this.showUploadError('Error lors de l\'ajout du texte');
        }
    }

    async handleFileUpload() {
        if (!this.selectedFile) {
            alert('No file selected');
            return;
        }

        const formData = new FormData();
        formData.append('file', this.selectedFile);

        this.showUploadProgress('Traitement du fichier...', 30);

        try {
            const response = await fetch('/api/knowledge/add-file', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showUploadProgress('Fichier traité avec succès!', 100);
                setTimeout(() => {
                    this.hideUploadProgress();
                    this.clearFileForm();
                    this.loadKnowledgePageStats();
                }, 2000);
            } else {
                throw new Error(data.message || 'Error lors du traitement');
            }
        } catch (error) {
            console.error('❌ Error upload fichier:', error);
            this.showUploadError('Error lors du traitement du fichier');
        }
    }

    async handleUrlUpload() {
        const url = document.getElementById('url-input')?.value.trim();
        const convertToPdf = document.getElementById('url-convert-pdf')?.checked;

        if (!url) {
            alert('Veuillez saisir une URL');
            return;
        }

        this.showUploadProgress('Récupération du contenu...', 25);

        try {
            const response = await fetch('/api/knowledge/add-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    convert_to_pdf: convertToPdf
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showUploadProgress('URL traitée avec succès!', 100);
                setTimeout(() => {
                    this.hideUploadProgress();
                    this.clearUrlForm();
                    this.loadKnowledgePageStats();
                }, 2000);
            } else {
                throw new Error(data.message || 'Error lors du traitement');
            }
        } catch (error) {
            console.error('❌ Error upload URL:', error);
            this.showUploadError('Error lors du traitement de l\'URL');
        }
    }

    showUploadProgress(text, percentage) {
        const progressDiv = document.getElementById('upload-progress');
        const statusText = document.getElementById('upload-status-text');
        const progressBar = document.getElementById('upload-progress-bar');

        if (progressDiv) progressDiv.style.display = 'block';
        if (statusText) statusText.textContent = text;
        if (progressBar) progressBar.style.width = `${percentage}%`;
    }

    showUploadError(message) {
        this.showUploadProgress(`❌ ${message}`, 0);
        const progressBar = document.getElementById('upload-progress-bar');
        if (progressBar) {
            progressBar.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
        }
    }

    hideUploadProgress() {
        const progressDiv = document.getElementById('upload-progress');
        if (progressDiv) progressDiv.style.display = 'none';

        // Reset progress bar color
        const progressBar = document.getElementById('upload-progress-bar');
        if (progressBar) {
            progressBar.style.background = 'linear-gradient(135deg, #8b5cf6, #7c3aed)';
            progressBar.style.width = '0%';
        }
    }

    clearTextForm() {
        const title = document.getElementById('text-title');
        const content = document.getElementById('text-content');
        if (title) title.value = '';
        if (content) content.value = '';
    }

    clearFileForm() {
        const fileInput = document.getElementById('file-input');
        const fileDropZone = document.getElementById('file-drop-zone');
        const fileSelected = document.getElementById('file-selected');
        const fileSubmit = document.getElementById('upload-file-submit');

        if (fileInput) fileInput.value = '';
        if (fileDropZone) fileDropZone.style.display = 'block';
        if (fileSelected) fileSelected.style.display = 'none';
        if (fileSubmit) {
            fileSubmit.disabled = true;
            fileSubmit.style.opacity = '0.5';
        }

        this.selectedFile = null;
    }

    clearUrlForm() {
        const urlInput = document.getElementById('url-input');
        const convertCheckbox = document.getElementById('url-convert-pdf');
        if (urlInput) urlInput.value = '';
        if (convertCheckbox) convertCheckbox.checked = false;
    }
    // ================


}
