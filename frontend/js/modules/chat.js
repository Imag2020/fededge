/**
 * Chat Manager Module
 * Handles chat interface, streaming, and conversation management
 */

import { UIUtils } from './ui-utils.js';

export class ChatManager {
    constructor(fedEdgeAI) {
        this.fedEdgeAI = fedEdgeAI;
        this.isStreaming = false;
        this.shouldStopStream = false;
        this.conversationId = this.generateConversationId();
        this.conversationHistory = [];
        this.currentStreamingMessage = null;
    }

    /**
     * Setup chat interface event listeners
     */
    setupChatInterface() {
        const chatButton = document.getElementById('chat-button');
        const chatPopup = document.getElementById('chat-popup');
        const chatClose = document.getElementById('chat-close');
        const chatClear = document.getElementById('chat-clear');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        const stopBtn = document.getElementById('chat-stop-btn');

        // Toggle chat popup
        if (chatButton && chatPopup) {
            chatButton.addEventListener('click', () => {
                const isVisible = chatPopup.style.display === 'flex';
                chatPopup.style.display = isVisible ? 'none' : 'flex';
                if (!isVisible && chatInput) {
                    chatInput.focus();
                }
            });
        }

        // Close chat popup
        if (chatClose && chatPopup) {
            chatClose.addEventListener('click', () => {
                chatPopup.style.display = 'none';
            });
        }

        // Clear conversation
        if (chatClear) {
            chatClear.addEventListener('click', () => {
                if (confirm('Are you sure you want to clear the entire conversation?')) {
                    this.clearConversation();
                }
            });
        }

        // Handle stop button
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.stopStreaming();
            });
        }

        // Handle form submission
        if (chatForm && chatInput) {
            chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const message = chatInput.value.trim();
                if (message && !this.isStreaming) {
                    this.sendChatMessage(message);
                    chatInput.value = '';
                }
            });
        }

        // Handle enter key
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (chatForm) {
                        chatForm.dispatchEvent(new Event('submit'));
                    }
                }
            });
        }

        // Handle RAG toggle
        const ragToggle = document.getElementById('rag-toggle');
        const ragStatus = document.getElementById('rag-status');
        const ragIndicator = document.getElementById('rag-indicator');

        if (ragToggle && ragStatus && ragIndicator) {
            ragToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    ragStatus.textContent = 'On';
                    ragIndicator.style.background = '#10b981';
                } else {
                    ragStatus.textContent = 'Off';
                    ragIndicator.style.background = '#ef4444';
                }
            });
        }
    }

    /**
     * Send chat message
     */
    sendChatMessage(message) {
        if (!this.fedEdgeAI.websocketManager?.socket) {
            UIUtils.showNotification('WebSocket not connected', 'error');
            return;
        }

        // Add user message to chat display
        this.addMessageToChat(message, 'user');

        // Show typing indicator and switch to stop button
        this.showTypingIndicator();
        this.toggleStreamingUI(true);

        // Reset streaming state
        this.isStreaming = true;
        this.shouldStopStream = false;

        // Check RAG toggle
        const ragToggle = document.getElementById('rag-toggle');
        const useRag = ragToggle && ragToggle.checked ? 'true' : 'false';

        // Send message with conversation context
        const data = {
            type: 'chat_message',
            payload: message,
            use_rag: useRag,
            conversation_id: this.conversationId,
            conversation_history: this.conversationHistory
        };

        // Add user message to history
        this.conversationHistory.push({ role: 'user', content: message });

        console.log(`Sending chat with conversation_id: ${this.conversationId}, history length: ${this.conversationHistory.length}`);
        this.fedEdgeAI.websocketManager.send(data);
    }

    /**
     * Stop streaming
     */
    stopStreaming() {
        console.log('Stop streaming requested');
        this.shouldStopStream = true;
        this.isStreaming = false;

        // Send stop signal to backend
        this.fedEdgeAI.websocketManager?.send({
            type: 'stop_stream',
            payload: {}
        });

        // Hide typing indicator and switch back to send button
        this.hideTypingIndicator();
        this.toggleStreamingUI(false);
    }

    /**
     * Toggle streaming UI
     */
    toggleStreamingUI(isStreaming) {
        const sendBtn = document.getElementById('chat-send-btn');
        const stopBtn = document.getElementById('chat-stop-btn');

        if (sendBtn && stopBtn) {
            if (isStreaming) {
                sendBtn.style.display = 'none';
                stopBtn.style.display = 'flex';
            } else {
                sendBtn.style.display = 'flex';
                stopBtn.style.display = 'none';
            }
        }
    }

    /**
     * Generate unique conversation ID
     */
    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Add message to chat display
     */
    addMessageToChat(message, type, payload = null) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        if (type === 'ai' && payload?.is_rag_response && payload?.sources?.length > 0) {
            // Enhanced AI message with RAG sources
            messageDiv.innerHTML = `
                <div style="margin-bottom: 8px;">${UIUtils.escapeHtml(message)}</div>
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
                        RAG Sources (${payload.source_count})
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
                                    <span style="color: #6b7280; font-weight: 500;">${UIUtils.escapeHtml(source.file || 'Unknown')}</span>
                                </div>
                                <div style="color: #9ca3af; font-size: 10px; line-height: 1.4;">
                                    ${UIUtils.escapeHtml(source.text?.substring(0, 100) || '')}${source.text?.length > 100 ? '...' : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else {
            messageDiv.textContent = message;
        }

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        if (type === 'ai') {
            this.currentStreamingMessage = messageDiv;
        }
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator(mode = 'thinking') {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;

        // Remove existing indicator
        const existingIndicator = document.getElementById('typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.className = 'message ai typing';
        indicator.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span class="typing-status">${this.getStatusMessage(mode)}</span>
        `;

        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Set indicator mode
     */
    setIndicatorMode(statusData) {
        const statusElement = document.querySelector('.typing-status');
        if (statusElement && statusData?.status) {
            statusElement.textContent = this.getStatusMessage(statusData.status);
        }
    }

    /**
     * Get status message
     */
    getStatusMessage(status) {
        const messages = {
            'thinking': 'Thinking...',
            'searching': 'Searching knowledge base...',
            'analyzing': 'Analyzing market data...',
            'processing': 'Processing...',
            'generating': 'Generating response...'
        };
        return messages[status] || 'Processing...';
    }

    /**
     * Handle chat response
     */
    handleChatResponse(data) {
        const payload = data.payload || {};
        const message = payload.message || '';

        this.hideTypingIndicator();

        // Add assistant message to history
        this.conversationHistory.push({ role: 'assistant', content: message });

        // Add message to chat
        this.addMessageToChat(message, 'ai', payload);

        // Reset streaming state
        this.isStreaming = false;
        this.toggleStreamingUI(false);
    }

    /**
     * Handle chat token (streaming)
     */
    handleChatToken(data) {
        const payload = data.payload || {};
        const token = payload.token || '';

        // Hide typing indicator on first token
        if (!this.currentStreamingMessage) {
            this.hideTypingIndicator();
            this.addMessageToChat('', 'ai');
        }

        // Append token to current message
        if (this.currentStreamingMessage) {
            this.currentStreamingMessage.textContent += token;

            // Scroll to bottom
            const messagesContainer = document.getElementById('chat-messages');
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    }

    /**
     * Handle chat stream end
     */
    handleChatStreamEnd(data) {
        const payload = data.payload || {};
        const fullMessage = payload.full_message || '';

        console.log('Chat stream ended');

        // Add complete message to history
        if (fullMessage) {
            this.conversationHistory.push({ role: 'assistant', content: fullMessage });
        }

        // Reset streaming state
        this.isStreaming = false;
        this.currentStreamingMessage = null;
        this.toggleStreamingUI(false);
        this.hideTypingIndicator();
    }

    /**
     * Handle conversation cleared
     */
    handleConversationCleared(data) {
        this.conversationHistory = [];
        this.conversationId = this.generateConversationId();

        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="message ai">
                    Hello! I'm your FedEdge AI assistant. How can I help you today?
                </div>
            `;
        }

        UIUtils.showNotification('Conversation cleared', 'success');
    }

    /**
     * Clear conversation
     */
    clearConversation() {
        // Send clear request to backend
        this.fedEdgeAI.websocketManager?.send({
            type: 'clear_conversation',
            payload: {
                conversation_id: this.conversationId
            }
        });

        // Reset local state
        this.conversationHistory = [];
        this.conversationId = this.generateConversationId();

        // Clear UI
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="message ai">
                    Hello! I'm your FedEdge AI assistant. How can I help you today?
                </div>
            `;
        }
    }
}
