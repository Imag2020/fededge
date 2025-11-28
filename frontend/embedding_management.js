/**
 * Embedding Management JavaScript Functions
 * Add these functions to your main.js file in the HiveAI class
 */

// ============== EMBEDDING CONFIGURATION MANAGEMENT ==============

async loadEmbeddingConfig() {
    console.log('🧠 Loading embedding configuration...');

    try {
        const response = await fetch('/api/embedding-config');
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                this.populateEmbeddingConfiguration(data);
            }
        }
    } catch (error) {
        console.error('❌ Error loading embedding config:', error);
    }
}

populateEmbeddingConfiguration(data) {
    console.log('🧠 Populating embedding configuration:', data);

    const defaultEmb = data.embeddings.find(emb => emb.is_default);
    if (defaultEmb) {
        // Update default embedding display
        const nameEl = document.getElementById('default-embedding-name');
        const modelEl = document.getElementById('default-embedding-model');
        const urlEl = document.getElementById('default-embedding-url');
        const typeEl = document.getElementById('default-embedding-type');
        const dimEl = document.getElementById('default-embedding-dimension');

        if (nameEl) nameEl.textContent = defaultEmb.name;
        if (modelEl) modelEl.textContent = defaultEmb.model || 'N/A';
        if (urlEl) urlEl.textContent = defaultEmb.url;
        if (dimEl) dimEl.textContent = defaultEmb.dimension;
        if (typeEl) {
            const typeLabel = defaultEmb.type === 'llamacpp' ? 'LlamaCpp Local' :
                             defaultEmb.type === 'ollama' ? 'Ollama Local' :
                             defaultEmb.type === 'openai' ? 'OpenAI Cloud' :
                             defaultEmb.type === 'cohere' ? 'Cohere Cloud' :
                             defaultEmb.type.charAt(0).toUpperCase() + defaultEmb.type.slice(1);
            typeEl.textContent = typeLabel;
        }
    }

    // Fill embedding pool list
    const embListEl = document.getElementById('embedding-pool-list');
    if (embListEl) {
        const otherEmbs = data.embeddings.filter(emb => !emb.is_default);

        if (otherEmbs.length === 0) {
            embListEl.innerHTML = `
                <div style="text-align: center; color: #9ca3af; padding: 20px;">
                    No additional embedding models configured
                </div>
            `;
        } else {
            embListEl.innerHTML = otherEmbs.map(emb => `
                <div style="
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                    padding: 12px;
                    margin-bottom: 8px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="color: #fff; font-weight: 600;">${emb.name}</span>
                        <div style="display: flex; gap: 4px;">
                            ${emb.is_active ?
                                '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 2px 6px; border-radius: 3px; font-size: 10px;">ACTIVE</span>' :
                                '<span style="background: rgba(156, 163, 175, 0.2); color: #9ca3af; padding: 2px 6px; border-radius: 3px; font-size: 10px;">INACTIVE</span>'
                            }
                            <button onclick="window.hiveAI?.testEmbeddingConnection('${emb.id}')" style="
                                background: rgba(59, 130, 246, 0.2);
                                border: 1px solid rgba(59, 130, 246, 0.3);
                                color: #3b82f6;
                                padding: 2px 6px;
                                border-radius: 3px;
                                font-size: 10px;
                                cursor: pointer;
                            ">🔍 Test</button>
                            ${!emb.is_default ? `
                            <button onclick="window.hiveAI?.setAsDefaultEmbedding('${emb.id}')" style="
                                background: rgba(245, 158, 11, 0.2);
                                border: 1px solid rgba(245, 158, 11, 0.3);
                                color: #f59e0b;
                                padding: 2px 6px;
                                border-radius: 3px;
                                font-size: 10px;
                                cursor: pointer;
                            ">⭐ Default</button>
                            ` : ''}
                            ${emb.id === 'default_llamacpp_embedding' ? `
                            <button disabled style="
                                background: rgba(156, 163, 175, 0.1);
                                border: 1px solid rgba(156, 163, 175, 0.2);
                                color: #6b7280;
                                padding: 2px 6px;
                                border-radius: 3px;
                                font-size: 10px;
                                cursor: not-allowed;
                                opacity: 0.5;
                            " title="Protected system embedding">🔒</button>
                            ` : `
                            <button onclick="window.hiveAI?.removeEmbedding('${emb.id}')" style="
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
                            <span style="color: #fff; margin-left: 4px;">${emb.type}</span>
                        </div>
                        <div>
                            <span style="color: #9ca3af;">Model:</span>
                            <span style="color: #fff; margin-left: 4px;">${emb.model || 'N/A'}</span>
                        </div>
                        <div>
                            <span style="color: #9ca3af;">URL:</span>
                            <span style="color: #fff; margin-left: 4px; font-size: 11px;">${emb.url}</span>
                        </div>
                        <div>
                            <span style="color: #9ca3af;">Dimension:</span>
                            <span style="color: #fff; margin-left: 4px;">${emb.dimension}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }
}

async testEmbeddingConnection(embId) {
    console.log(`🔍 Testing embedding connection: ${embId}`);

    this.showNotification('⏳ Testing embedding connection...', 'info');

    try {
        const response = await fetch(`/api/embedding-config/${embId}/test`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.status === 'success' && result.connected) {
            this.showNotification('✅ Embedding connection successful!', 'success');
        } else {
            this.showNotification('❌ Embedding connection failed: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('❌ Error testing embedding:', error);
        this.showNotification('❌ Error testing embedding connection', 'error');
    }
}

async setAsDefaultEmbedding(embId) {
    console.log(`⭐ Setting ${embId} as default embedding`);

    try {
        const response = await fetch(`/api/embedding-config/${embId}/set-default`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.status === 'success') {
            this.showNotification('✅ Default embedding updated!', 'success');
            await this.loadEmbeddingConfig();
        } else {
            this.showNotification('❌ Failed to set default: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('❌ Error setting default embedding:', error);
        this.showNotification('❌ Error setting default embedding', 'error');
    }
}

async removeEmbedding(embId) {
    if (!confirm('Are you sure you want to remove this embedding configuration?')) {
        return;
    }

    console.log(`🗑️ Removing embedding: ${embId}`);

    try {
        const response = await fetch(`/api/embedding-config/${embId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.status === 'success') {
            this.showNotification('✅ Embedding removed!', 'success');
            await this.loadEmbeddingConfig();
        } else {
            this.showNotification('❌ Failed to remove: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('❌ Error removing embedding:', error);
        this.showNotification('❌ Error removing embedding', 'error');
    }
}

// ============== MODAL MANAGEMENT ==============

openAddEmbeddingModal() {
    const modal = document.getElementById('add-embedding-modal');
    if (modal) {
        modal.style.display = 'flex';
        // Reset form
        document.getElementById('add-embedding-form').reset();
    }
}

closeAddEmbeddingModal() {
    const modal = document.getElementById('add-embedding-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// ============== ADD EMBEDDING FORM ==============

async handleAddEmbeddingSubmit(e) {
    e.preventDefault();

    const embeddingData = {
        id: document.getElementById('embedding-id').value,
        name: document.getElementById('embedding-name').value,
        type: document.getElementById('embedding-type').value,
        url: document.getElementById('embedding-url').value,
        model: document.getElementById('embedding-model').value,
        api_key: document.getElementById('embedding-api-key').value,
        dimension: parseInt(document.getElementById('embedding-dimension').value),
        timeout: parseInt(document.getElementById('embedding-timeout').value),
        is_default: document.getElementById('embedding-is-default').checked,
        is_active: document.getElementById('embedding-is-active').checked,
        extra_params: {}
    };

    console.log('💾 Adding embedding:', embeddingData);

    try {
        const response = await fetch('/api/embedding-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(embeddingData)
        });

        const result = await response.json();

        if (result.status === 'success') {
            this.showNotification('✅ Embedding added successfully!', 'success');
            this.closeAddEmbeddingModal();
            await this.loadEmbeddingConfig();
        } else {
            this.showNotification('❌ Failed to add embedding: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('❌ Error adding embedding:', error);
        this.showNotification('❌ Error adding embedding', 'error');
    }
}

// ============== EVENT LISTENERS ==============

setupEmbeddingEventListeners() {
    // Add embedding button
    const addEmbBtn = document.getElementById('add-embedding-btn');
    if (addEmbBtn) {
        addEmbBtn.addEventListener('click', () => this.openAddEmbeddingModal());
    }

    // Close modal button
    const closeBtn = document.getElementById('close-add-embedding-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => this.closeAddEmbeddingModal());
    }

    // Cancel button
    const cancelBtn = document.getElementById('cancel-add-embedding-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => this.closeAddEmbeddingModal());
    }

    // Form submit
    const form = document.getElementById('add-embedding-form');
    if (form) {
        form.addEventListener('submit', (e) => this.handleAddEmbeddingSubmit(e));
    }

    // Test embedding config button
    const testBtn = document.getElementById('test-embedding-config-btn');
    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            const embData = {
                type: document.getElementById('embedding-type').value,
                url: document.getElementById('embedding-url').value,
                model: document.getElementById('embedding-model').value
            };

            this.showNotification('⏳ Testing embedding configuration...', 'info');
            // You can implement a test without saving first if needed
            this.showNotification('💡 Please save the embedding first to test it', 'info');
        });
    }
}

// ============== INITIALIZE ==============

// Add this to your existing loadCurrentSettings() function:
async loadCurrentSettings() {
    console.log('🚨 Loading current settings...');

    try {
        // Load LLM config
        const llmResponse = await fetch('/api/llm-config');
        if (llmResponse.ok) {
            const llmData = await llmResponse.json();
            if (llmData.status === 'success') {
                this.populateLLMConfiguration(llmData);
            }
        }

        // Load EMBEDDING config
        await this.loadEmbeddingConfig();

        // Load trading simulations
        const simsResponse = await fetch('/api/simulations');
        if (simsResponse.ok) {
            const simsData = await simsResponse.json();
            if (simsData.status === 'success') {
                this.populateTradingSimulations(simsData);
            }
        }

    } catch (error) {
        console.error('❌ Error loading settings:', error);
    }
}
