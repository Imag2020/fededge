/**
 * Settings Manager Module
 * Handles LLM and Embeddings configuration
 */

import { UIUtils } from './ui-utils.js';

export class SettingsManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.llmConfigs = [];
        this.defaultLlmId = null;
        this.embeddingConfigs = [];
        this.defaultEmbeddingId = null;
        console.log('✅ SettingsManager initialized');
    }

    /**
     * Setup settings interface
     */
    setupSettings() {
        console.log('⚙️ Setup Settings interface...');

        // Load LLM configuration automatically
        this.loadLLMConfig();

        // Load Embeddings configuration automatically
        this.loadEmbeddingsConfig();
    }

    /**
     * Load LLM configuration from API
     */
    async loadLLMConfig() {
        console.log('📊 Loading LLM configuration...');

        try {
            console.log('📊 Fetching /api/llm-config...');
            const response = await fetch('/api/llm-config');
            console.log('📊 Response status:', response.status, response.ok);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Response not OK:', errorText);
                throw new Error(`Failed to fetch LLM config: ${response.status}`);
            }

            const data = await response.json();
            console.log('📊 Response data:', data);

            if (data.status === 'success') {
                console.log('✅ LLM config received:', data);
                console.log('📊 Number of LLMs:', data.llms ? data.llms.length : 0);
                this.llmConfigs = data.llms || [];
                this.defaultLlmId = data.default_llm_id;
                console.log('📊 Calling updateLLMConfigDisplay...');
                this.updateLLMConfigDisplay();
                console.log('📊 updateLLMConfigDisplay completed');
            } else {
                console.error('❌ Error API LLM config:', data.message);
                this.showLLMConfigError('Error loading LLM configuration');
            }
        } catch (error) {
            console.error('❌ Error loading LLM config:', error);
            console.error('❌ Error stack:', error.stack);
            this.showLLMConfigError('Unable to load LLM configuration');
        }
    }

    /**
     * Update LLM configuration display
     */
    updateLLMConfigDisplay() {
        console.log('📊 Updating LLM config display');
        console.log('📊 LLM configs:', this.llmConfigs);
        console.log('📊 Default LLM ID:', this.defaultLlmId);

        // Find default LLM
        const defaultLlm = this.llmConfigs.find(llm => llm.is_default) || this.llmConfigs[0];
        console.log('📊 Default LLM found:', defaultLlm);

        // Update default LLM section
        const nameEl = document.getElementById('default-llm-name');
        const modelEl = document.getElementById('default-llm-model');
        const urlEl = document.getElementById('default-llm-url');
        const typeEl = document.getElementById('default-llm-type');

        console.log('📊 Elements found:', { nameEl: !!nameEl, modelEl: !!modelEl, urlEl: !!urlEl, typeEl: !!typeEl });

        if (defaultLlm) {
            if (nameEl) nameEl.textContent = defaultLlm.name || 'N/A';
            if (modelEl) modelEl.textContent = defaultLlm.model || 'N/A';
            if (urlEl) urlEl.textContent = defaultLlm.url || 'N/A';
            if (typeEl) typeEl.textContent = defaultLlm.type || 'N/A';
        } else {
            if (nameEl) nameEl.textContent = 'No LLM configured';
            if (modelEl) modelEl.textContent = 'N/A';
            if (urlEl) urlEl.textContent = 'N/A';
            if (typeEl) typeEl.textContent = 'N/A';
        }

        // Update LLM pool list
        this.updateLLMPoolDisplay();
    }

    /**
     * Update LLM pool display
     */
    updateLLMPoolDisplay() {
        const poolListEl = document.getElementById('llm-pool-list');

        if (!poolListEl) return;

        // Filter non-default LLMs
        const additionalLlms = this.llmConfigs.filter(llm => !llm.is_default);

        if (additionalLlms.length === 0) {
            poolListEl.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px;">
                    No additional LLM models configured
                </div>
            `;
            return;
        }

        poolListEl.innerHTML = additionalLlms.map(llm => `
            <div style="
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div>
                        <div style="color: #fff; font-weight: 600; font-size: 14px; margin-bottom: 4px;">
                            ${UIUtils.escapeHtml(llm.name)}
                        </div>
                        <div style="color: #9ca3af; font-size: 12px;">
                            ${UIUtils.escapeHtml(llm.url)}
                        </div>
                    </div>
                    <div style="
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 600;
                        background: ${llm.is_active ? '#10b981' : '#6b7280'};
                        color: white;
                    ">
                        ${llm.is_active ? 'Active' : 'Inactive'}
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; margin-bottom: 8px;">
                    <div>
                        <span style="color: #9ca3af;">Type:</span>
                        <span style="color: #fff; margin-left: 4px;">${llm.type}</span>
                    </div>
                    <div>
                        <span style="color: #9ca3af;">Model:</span>
                        <span style="color: #fff; margin-left: 4px;">${UIUtils.escapeHtml(llm.model || 'N/A')}</span>
                    </div>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button onclick="window.fedEdgeAI.settingsManager.setDefaultLLM('${llm.id}')" style="
                        flex: 1;
                        padding: 6px;
                        background: #3b82f6;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 11px;
                        font-weight: 600;
                    ">
                        Set as Default
                    </button>
                    <button onclick="window.fedEdgeAI.settingsManager.deleteLLM('${llm.id}')" style="
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
     * Show error in LLM config display
     */
    showLLMConfigError(message) {
        console.error('❌ LLM config error:', message);

        const nameEl = document.getElementById('default-llm-name');
        const modelEl = document.getElementById('default-llm-model');
        const urlEl = document.getElementById('default-llm-url');
        const typeEl = document.getElementById('default-llm-type');

        if (nameEl) nameEl.textContent = 'Error';
        if (modelEl) modelEl.textContent = 'Error';
        if (urlEl) urlEl.textContent = 'Error';
        if (typeEl) typeEl.textContent = 'Error';
    }

    /**
     * Show modal to add new LLM
     */
    async showAddLLMModal() {
        const modal = UIUtils.createModal(`
            <div style="max-width: 600px;">
                <h2 style="margin-bottom: 20px; color: #1f2937;">Add New LLM Model</h2>

                <form id="add-llm-form" style="display: flex; flex-direction: column; gap: 16px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">ID *</label>
                            <input type="text" id="llm-id" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " placeholder="my-llm" />
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Name *</label>
                            <input type="text" id="llm-name" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " placeholder="My LLM Model" />
                        </div>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Type *</label>
                        <select id="llm-type" required style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                            background: white;
                        ">
                            <option value="">Select type...</option>
                            <option value="llamacpp">llama.cpp (Direct)</option>
                            <option value="llamacpp_server">llama.cpp Server</option>
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI API</option>
                            <option value="claude">Claude API</option>
                            <option value="gemini">Gemini API</option>
                            <option value="grok">Grok API</option>
                            <option value="deepseek">DeepSeek API</option>
                            <option value="kimi">Kimi API</option>
                            <option value="qwen">Qwen API</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">URL *</label>
                        <input type="url" id="llm-url" required style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                        " placeholder="http://localhost:11434" />
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Model</label>
                        <input type="text" id="llm-model" style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                        " placeholder="qwen2.5:14b" />
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">API Key (optional)</label>
                        <input type="password" id="llm-api-key" style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                        " placeholder="sk-..." />
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Max Tokens</label>
                            <input type="number" id="llm-max-tokens" value="4096" min="100" max="100000" style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " />
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Temperature</label>
                            <input type="number" id="llm-temperature" value="0.7" min="0" max="2" step="0.1" style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " />
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Timeout (s)</label>
                            <input type="number" id="llm-timeout" value="30" min="5" max="300" style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " />
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" id="llm-is-default" style="width: 16px; height: 16px;" />
                        <label for="llm-is-default" style="color: #6b7280; font-size: 14px;">Set as default LLM</label>
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
                            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                            color: white;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                        ">Add LLM</button>
                    </div>
                </form>
            </div>
        `, { maxWidth: '600px' });

        document.body.appendChild(modal);

        // Handle form submission
        document.getElementById('add-llm-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            const llmData = {
                id: document.getElementById('llm-id').value,
                name: document.getElementById('llm-name').value,
                type: document.getElementById('llm-type').value,
                url: document.getElementById('llm-url').value,
                model: document.getElementById('llm-model').value || '',
                api_key: document.getElementById('llm-api-key').value || '',
                is_default: document.getElementById('llm-is-default').checked,
                is_active: true,
                max_tokens: parseInt(document.getElementById('llm-max-tokens').value),
                temperature: parseFloat(document.getElementById('llm-temperature').value),
                timeout: parseInt(document.getElementById('llm-timeout').value),
                extra_params: {}
            };

            try {
                console.log('Sending LLM config:', llmData);

                const response = await fetch('/api/llm-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(llmData)
                });

                const result = await response.json();
                console.log('Response from server:', result);

                if (result.status === 'success') {
                    UIUtils.showNotification('LLM added successfully', 'success');
                    modal.remove();
                    await this.loadLLMConfig();
                } else {
                    throw new Error(result.message || 'Failed to add LLM');
                }
            } catch (error) {
                console.error('Error adding LLM:', error);
                UIUtils.showNotification('Failed to add LLM: ' + error.message, 'error');
            }
        });
    }

    /**
     * Set LLM as default
     */
    async setDefaultLLM(llmId) {
        try {
            const response = await fetch(`/api/llm-config/${llmId}/set-default`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to set default LLM');

            const result = await response.json();

            if (result.status === 'success') {
                UIUtils.showNotification('Default LLM updated', 'success');
                this.loadLLMConfig();
            } else {
                throw new Error(result.message || 'Failed to set default LLM');
            }
        } catch (error) {
            console.error('Error setting default LLM:', error);
            UIUtils.showNotification('Failed to set default LLM', 'error');
        }
    }

    /**
     * Delete LLM
     */
    async deleteLLM(llmId) {
        if (!confirm('Are you sure you want to delete this LLM configuration?')) return;

        try {
            const response = await fetch(`/api/llm-config/${llmId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete LLM');

            UIUtils.showNotification('LLM deleted', 'success');
            this.loadLLMConfig();
        } catch (error) {
            console.error('Error deleting LLM:', error);
            UIUtils.showNotification('Failed to delete LLM', 'error');
        }
    }

    // ===== Embeddings Configuration Methods =====

    /**
     * Load Embeddings configuration from API
     */
    async loadEmbeddingsConfig() {
        console.log('🧮 Loading Embeddings configuration...');

        try {
            const response = await fetch('/api/embeddings-config');

            if (!response.ok) {
                throw new Error(`Failed to fetch embeddings config: ${response.status}`);
            }

            const data = await response.json();

            if (data.status === 'success') {
                console.log('✅ Embeddings config received:', data);
                this.embeddingConfigs = data.embeddings || [];
                this.defaultEmbeddingId = data.default_embedding_id;
                this.updateEmbeddingsListDisplay();
            } else {
                console.error('❌ Error API embeddings config:', data.message);
                this.showEmbeddingsError('Error loading embeddings configuration');
            }
        } catch (error) {
            console.error('❌ Error loading embeddings config:', error);
            this.showEmbeddingsError('Unable to load embeddings configuration');
        }
    }

    /**
     * Update embeddings list display
     */
    updateEmbeddingsListDisplay() {
        const listEl = document.getElementById('embeddings-list');

        if (!listEl) return;

        if (this.embeddingConfigs.length === 0) {
            listEl.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px;">
                    No embedding models configured
                </div>
            `;
            return;
        }

        listEl.innerHTML = this.embeddingConfigs.map(emb => `
            <div style="
                background: rgba(139, 92, 246, 0.1);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div>
                        <div style="color: #fff; font-weight: 600; font-size: 14px; margin-bottom: 4px;">
                            ${UIUtils.escapeHtml(emb.name)}
                            ${emb.is_default ? '<span style="background: #8b5cf6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 8px;">DEFAULT</span>' : ''}
                        </div>
                        <div style="color: #9ca3af; font-size: 12px;">
                            ${UIUtils.escapeHtml(emb.url)}
                        </div>
                    </div>
                    <div style="
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 600;
                        background: ${emb.is_active ? '#8b5cf6' : '#6b7280'};
                        color: white;
                    ">
                        ${emb.is_active ? 'Active' : 'Inactive'}
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; margin-bottom: 8px;">
                    <div>
                        <span style="color: #9ca3af;">Type:</span>
                        <span style="color: #fff; margin-left: 4px;">${emb.type}</span>
                    </div>
                    <div>
                        <span style="color: #9ca3af;">Model:</span>
                        <span style="color: #fff; margin-left: 4px;">${UIUtils.escapeHtml(emb.model || 'N/A')}</span>
                    </div>
                    <div>
                        <span style="color: #9ca3af;">Dimension:</span>
                        <span style="color: #8b5cf6; margin-left: 4px; font-weight: 600;">${emb.dimension}</span>
                    </div>
                    <div>
                        <span style="color: #9ca3af;">Timeout:</span>
                        <span style="color: #fff; margin-left: 4px;">${emb.timeout}s</span>
                    </div>
                </div>
                ${!emb.is_default ? `
                    <div style="display: flex; gap: 8px;">
                        <button onclick="window.fedEdgeAI.settingsManager.setDefaultEmbedding('${emb.id}')" style="
                            flex: 1;
                            padding: 6px;
                            background: #8b5cf6;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 11px;
                            font-weight: 600;
                        ">
                            Set as Default
                        </button>
                        <button onclick="window.fedEdgeAI.settingsManager.deleteEmbedding('${emb.id}')" style="
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
                ` : ''}
            </div>
        `).join('');
    }

    /**
     * Show error in embeddings display
     */
    showEmbeddingsError(message) {
        console.error('❌ Embeddings config error:', message);
        const listEl = document.getElementById('embeddings-list');
        if (listEl) {
            listEl.innerHTML = `
                <div style="text-align: center; color: #ef4444; padding: 20px;">
                    ${message}
                </div>
            `;
        }
    }

    /**
     * Show modal to add new Embedding
     */
    async showAddEmbeddingModal() {
        const modal = UIUtils.createModal(`
            <div style="max-width: 600px;">
                <h2 style="margin-bottom: 20px; color: #1f2937;">Add New Embedding Model</h2>

                <form id="add-embedding-form" style="display: flex; flex-direction: column; gap: 16px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">ID *</label>
                            <input type="text" id="emb-id" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " placeholder="my-embedding" />
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Name *</label>
                            <input type="text" id="emb-name" required style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " placeholder="My Embedding Model" />
                        </div>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Type *</label>
                        <select id="emb-type" required style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                            background: white;
                        ">
                            <option value="">Select type...</option>
                            <option value="openai_compatible">OpenAI-compatible Server</option>
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI API</option>
                            <option value="huggingface">HuggingFace</option>
                            <option value="custom">Custom</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">URL *</label>
                        <input type="url" id="emb-url" required style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                        " placeholder="http://localhost:9002/v1" />
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Model *</label>
                        <input type="text" id="emb-model" required style="
                            width: 100%;
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 14px;
                        " placeholder="embeddinggemma" />
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Dimension</label>
                            <input type="number" id="emb-dimension" value="768" min="128" max="4096" style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " />
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6b7280; font-size: 14px;">Timeout (seconds)</label>
                            <input type="number" id="emb-timeout" value="30" min="5" max="300" style="
                                width: 100%;
                                padding: 8px 12px;
                                border: 1px solid #d1d5db;
                                border-radius: 6px;
                                font-size: 14px;
                            " />
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" id="emb-is-default" style="width: 16px; height: 16px;" />
                        <label for="emb-is-default" style="color: #6b7280; font-size: 14px; cursor: pointer;">Set as default embedding model</label>
                    </div>

                    <div style="display: flex; gap: 12px; margin-top: 8px;">
                        <button type="submit" style="
                            flex: 1;
                            padding: 10px;
                            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                            color: white;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                            font-size: 14px;
                        ">
                            Add Embedding Model
                        </button>
                        <button type="button" class="close-modal" style="
                            padding: 10px 20px;
                            background: #6b7280;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                            font-size: 14px;
                        ">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        `);

        // Handle form submission (wait for modal to be in DOM)
        setTimeout(() => {
            const form = document.getElementById('add-embedding-form');
            if (!form) {
                console.error('❌ add-embedding-form not found in DOM');
                return;
            }

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const embeddingConfig = {
                    id: document.getElementById('emb-id').value,
                    name: document.getElementById('emb-name').value,
                    type: document.getElementById('emb-type').value,
                    url: document.getElementById('emb-url').value,
                    model: document.getElementById('emb-model').value,
                    dimension: parseInt(document.getElementById('emb-dimension').value),
                    timeout: parseInt(document.getElementById('emb-timeout').value),
                    is_default: document.getElementById('emb-is-default').checked,
                    is_active: true,
                    api_key: "",
                    extra_params: {}
                };

                try {
                    const response = await fetch('/api/embeddings-config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(embeddingConfig)
                    });

                    if (!response.ok) throw new Error('Failed to add embedding');

                    const result = await response.json();

                    if (result.status === 'success') {
                        UIUtils.showNotification('Embedding model added successfully', 'success');
                        modal.remove();
                        this.loadEmbeddingsConfig();
                    } else {
                        throw new Error(result.message || 'Failed to add embedding');
                    }
                } catch (error) {
                    console.error('Error adding embedding:', error);
                    UIUtils.showNotification('Failed to add embedding model', 'error');
                }
            });
        }, 100);
    }

    /**
     * Set embedding as default
     */
    async setDefaultEmbedding(embeddingId) {
        try {
            // We need to update the embedding with is_default=true
            const embedding = this.embeddingConfigs.find(e => e.id === embeddingId);
            if (!embedding) throw new Error('Embedding not found');

            embedding.is_default = true;

            const response = await fetch(`/api/embeddings-config/${embeddingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(embedding)
            });

            if (!response.ok) throw new Error('Failed to set default embedding');

            const result = await response.json();

            if (result.status === 'success') {
                UIUtils.showNotification('Default embedding updated', 'success');
                this.loadEmbeddingsConfig();
            } else {
                throw new Error(result.message || 'Failed to set default embedding');
            }
        } catch (error) {
            console.error('Error setting default embedding:', error);
            UIUtils.showNotification('Failed to set default embedding', 'error');
        }
    }

    /**
     * Delete embedding
     */
    async deleteEmbedding(embeddingId) {
        if (!confirm('Are you sure you want to delete this embedding configuration?')) return;

        try {
            const response = await fetch(`/api/embeddings-config/${embeddingId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete embedding');

            UIUtils.showNotification('Embedding deleted', 'success');
            this.loadEmbeddingsConfig();
        } catch (error) {
            console.error('Error deleting embedding:', error);
            UIUtils.showNotification('Failed to delete embedding', 'error');
        }
    }
}
