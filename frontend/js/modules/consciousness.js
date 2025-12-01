/**
 * Agent Consciousness Display Module
 * Handles real-time updates of the Agent V3 consciousness state
 */

export class ConsciousnessManager {
    constructor(websocketManager) {
        this.websocketManager = websocketManager;
        this.lastUpdate = null;

        // Register WebSocket handler
        this.registerHandler();
    }

    registerHandler() {
        this.websocketManager.customHandlers.push((message) => {
            if (message.type === 'agent_consciousness') {
                console.log('🧠 Received agent_consciousness message:', message.payload);
                this.handleConsciousnessUpdate(message.payload);
                return true; // Mark as handled
            }
            return false;
        });

        console.log('🧠 Consciousness manager initialized and handler registered');
        console.log('🧠 Total custom handlers:', this.websocketManager.customHandlers.length);
    }

    handleConsciousnessUpdate(payload) {
        if (!payload) {
            console.warn('🧠 Received empty payload');
            return;
        }

        this.lastUpdate = Date.now();

        console.log('🧠 Updating UI with payload:', payload);

        // Update timestamp
        const timestampEl = document.getElementById('consciousness-updated');
        if (timestampEl) {
            const now = new Date();
            timestampEl.textContent = now.toLocaleTimeString();
            console.log('🧠 Updated timestamp:', timestampEl.textContent);
        } else {
            console.warn('🧠 Element not found: consciousness-updated');
        }

        // Update global consciousness
        const globalEl = document.getElementById('consciousness-global');
        if (globalEl) {
            const consciousness = payload.global_consciousness || 'Monitoring crypto markets and user activities...';
            globalEl.textContent = consciousness;
            console.log('🧠 Updated global consciousness:', consciousness.substring(0, 50));
        } else {
            console.warn('🧠 Element not found: consciousness-global');
        }

        // Update working memory (last event)
        const workingEl = document.getElementById('consciousness-last-event');
        if (workingEl) {
            const working = payload.working_memory || 'Idle - Ready for tasks';
            workingEl.textContent = working;
            console.log('🧠 Updated working memory:', working);
        } else {
            console.warn('🧠 Element not found: consciousness-last-event');
        }

        // Update cycle count
        const cyclesEl = document.getElementById('consciousness-cycles');
        if (cyclesEl) {
            cyclesEl.textContent = payload.cycle || '0';
            console.log('🧠 Updated cycle count:', payload.cycle);
        } else {
            console.warn('🧠 Element not found: consciousness-cycles');
        }

        console.log('✅ Consciousness UI update complete');
    }

    // Manual refresh (can be called from debug tools)
    async refresh() {
        console.log('🔄 Manually refreshing consciousness...');
        // Could trigger a backend API call here if needed
    }
}
