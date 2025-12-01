/**
 * FedEdgeAI - Main Application Entry Point
 * A modular federated learning and trading AI platform
 *
 * This file serves as the entry point that loads all modules and initializes the application.
 */

import { FedEdgeAI } from './modules/core.js';
import { UIUtils } from './modules/ui-utils.js';

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing FedEdgeAI...');

    try {
        // Create global FedEdgeAI instance
        window.fedEdgeAI = new FedEdgeAI();

        console.log('FedEdgeAI instance created and available globally');
        console.log('🧠 Consciousness manager initialized via core.js');

        // Setup global helper functions for backward compatibility
        setupGlobalHelpers();

        // Show welcome notification
        setTimeout(() => {
            UIUtils.showNotification('Welcome to FedEdgeAI!', 'success');
        }, 1000);

    } catch (error) {
        console.error('Failed to initialize FedEdgeAI:', error);
        UIUtils.showNotification('Failed to initialize application', 'error');
    }
});

/**
 * Setup global helper functions for HTML event handlers
 */
function setupGlobalHelpers() {
    // Create a proxy to the main instance for easier access
    window.app = window.fedEdgeAI;

    // Global helper functions
    window.showAssetStats = (symbol) => {
        window.fedEdgeAI?.showAssetStatsForSymbol?.(symbol);
    };

    window.createNewWallet = () => {
        window.fedEdgeAI?.walletManager?.createNewWallet?.();
    };

    window.selectWallet = (id, name) => {
        window.fedEdgeAI?.walletManager?.selectWallet?.(id, name);
    };

    window.showTradesHistory = (walletName) => {
        window.fedEdgeAI?.tradingManager?.showTradesHistory?.(walletName);
    };

    window.toggleSimulation = (id) => {
        window.fedEdgeAI?.tradingManager?.toggleSimulation?.(id);
    };

    window.deleteSimulation = (id) => {
        window.fedEdgeAI?.tradingManager?.deleteSimulation?.(id);
    };

    window.createSimulation = () => {
        window.fedEdgeAI?.tradingManager?.showCreateSimulationModal?.();
    };

    window.addLLM = () => {
        window.fedEdgeAI?.settingsManager?.showAddLLMModal?.();
    };

    // Test function for debugging LLM loading
    window.testLoadLLM = () => {
        console.log('🧪 Manual test: Loading LLM config...');
        if (window.fedEdgeAI && window.fedEdgeAI.settingsManager) {
            window.fedEdgeAI.settingsManager.loadLLMConfig();
        } else {
            console.error('❌ fedEdgeAI or settingsManager not available');
        }
    };

    window.prevPage = () => {
        window.fedEdgeAI?.signalsManager?.prevPage?.();
    };

    window.nextPage = () => {
        window.fedEdgeAI?.signalsManager?.nextPage?.();
    };

    console.log('Global helper functions registered');
}

/**
 * Setup mobile hamburger menu
 */
function setupHamburgerMenu() {
    const hamburger = document.getElementById('hamburger-menu');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const sidebarItems = document.querySelectorAll('.sidebar-item');

    if (!hamburger || !sidebar || !overlay) {
        console.warn('Hamburger menu elements not found');
        return;
    }

    // Toggle sidebar
    const toggleSidebar = () => {
        const isActive = sidebar.classList.toggle('active');
        hamburger.classList.toggle('active');
        overlay.classList.toggle('active');
        document.body.classList.toggle('sidebar-open');
    };

    // Close sidebar
    const closeSidebar = () => {
        sidebar.classList.remove('active');
        hamburger.classList.remove('active');
        overlay.classList.remove('active');
        document.body.classList.remove('sidebar-open');
    };

    // Event listeners
    hamburger.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', closeSidebar);

    // Close sidebar when clicking on a menu item (on mobile)
    sidebarItems.forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    });

    // Close sidebar on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('active')) {
            closeSidebar();
        }
    });

    console.log('Hamburger menu initialized');
}

// Initialize hamburger menu after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(setupHamburgerMenu, 100);
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.fedEdgeAI) {
        window.fedEdgeAI.destroy();
    }
});

// Export for module usage
export { FedEdgeAI };
