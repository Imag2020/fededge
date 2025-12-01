# FedEdgeAI - Modular Frontend Architecture

## Overview

FedEdgeAI has been refactored into a clean, modular architecture that replaces the previous monolithic `HiveAI` and `NodeManager` classes. The new architecture uses ES6 modules for better code organization, maintainability, and scalability.

## Architecture

### Module Structure

```
frontend/js/
├── main.js                    # Entry point - initializes the application
└── modules/
    ├── core.js                # Main FedEdgeAI class - coordinates all modules
    ├── ui-utils.js            # UI utilities (formatting, notifications, modals)
    ├── websocket.js           # WebSocket connection and message routing
    ├── chat.js                # Chat interface and streaming
    ├── wallet.js              # Wallet management and holdings
    ├── signals.js             # AI trading signals and pagination
    ├── trading.js             # Trading operations and simulations
    └── dashboard.js           # Dashboard stats, news, and visualizations
```

### Key Features

- **Modular Design**: Each module handles a specific domain (chat, wallet, signals, etc.)
- **ES6 Modules**: Uses modern JavaScript module syntax for better code organization
- **Single Responsibility**: Each module has a clear, focused purpose
- **Centralized Coordination**: The `FedEdgeAI` core class coordinates all modules
- **Backward Compatibility**: Global helper functions ensure existing HTML onclick handlers work

## Module Descriptions

### core.js - FedEdgeAI

Main application class that:
- Initializes all manager modules
- Coordinates inter-module communication
- Handles application lifecycle
- Sets up navigation and modal systems
- Manages auto-refresh intervals

### ui-utils.js - UIUtils

Utility functions for:
- Displaying notifications (success, error, warning, info)
- Formatting prices, percentages, market caps
- Escaping HTML to prevent XSS
- Creating loading spinners and error displays
- Color coding based on values
- Timestamp formatting

### websocket.js - WebSocketManager

Handles:
- WebSocket connection establishment
- Auto-reconnection logic
- Message routing to appropriate modules
- Connection status updates
- Error handling

### chat.js - ChatManager

Manages:
- Chat interface setup and event handlers
- Message sending and receiving
- Streaming responses from LLM
- Conversation history and KV cache optimization
- RAG toggle and source display
- Typing indicators

### wallet.js - WalletManager

Responsible for:
- Wallet CRUD operations
- Holdings display and updates
- Price updates and calculations
- Performance tracking (best/worst performers)
- Wallet selection

### signals.js - SignalsManager

Handles:
- Loading AI trading signals
- Signal display and formatting
- Pagination of signals
- Real-time signal updates via WebSocket
- Signal confidence and action indicators

### trading.js - TradingManager

Manages:
- Trading bot simulations
- Trade execution notifications
- Trade history display
- Simulation start/stop/delete operations
- Performance metrics

### dashboard.js - DashboardManager

Controls:
- Market statistics display
- News feed management
- Market sentiment gauge
- Market cap visualization
- Real-time market alerts
- Dashboard data refresh

## Global Access

The application is accessible globally through:

```javascript
window.fedEdgeAI          // Main FedEdgeAI instance
window.app                // Alias to fedEdgeAI

// Direct module access
window.fedEdgeAI.chatManager
window.fedEdgeAI.walletManager
window.fedEdgeAI.signalsManager
window.fedEdgeAI.tradingManager
window.fedEdgeAI.dashboardManager
window.fedEdgeAI.websocketManager
```

## Global Helper Functions

For backward compatibility with existing HTML event handlers:

```javascript
window.showAssetStats(symbol)
window.createNewWallet()
window.selectWallet(id, name)
window.showTradesHistory(walletName)
window.toggleSimulation(id)
window.deleteSimulation(id)
window.prevPage()
window.nextPage()
```

## Usage Examples

### Showing a Notification

```javascript
import { UIUtils } from './modules/ui-utils.js';

UIUtils.showNotification('Trade executed successfully', 'success');
```

### Accessing Managers

```javascript
// Get current signals
const signals = window.fedEdgeAI.signalsManager.signals;

// Load wallet data
await window.fedEdgeAI.walletManager.loadWalletsData();

// Send chat message
window.fedEdgeAI.chatManager.sendChatMessage('What is the market sentiment?');
```

### WebSocket Communication

```javascript
// Send message through WebSocket
window.fedEdgeAI.websocketManager.send({
    type: 'custom_message',
    payload: { data: 'value' }
});
```

## Migration from Old Code

### Before (Old Code)

```javascript
window.hiveAI = new HiveAI();
window.nodeManager = new NodeManager();

window.hiveAI.showTradesHistory('wallet1');
window.nodeManager.createNewWallet();
```

### After (New Code)

```javascript
// Automatically created on DOMContentLoaded
// window.fedEdgeAI is ready

window.fedEdgeAI.tradingManager.showTradesHistory('wallet1');
window.fedEdgeAI.walletManager.createNewWallet();

// Or use global helpers (backward compatible)
window.showTradesHistory('wallet1');
window.createNewWallet();
```

## Key Improvements

1. **Separation of Concerns**: Each module handles one aspect of the application
2. **Maintainability**: ~11,000 lines split into manageable ~300-500 line modules
3. **Testability**: Modules can be tested independently
4. **Reusability**: Utilities can be imported and reused across modules
5. **Modern JavaScript**: Uses ES6+ features (modules, classes, async/await)
6. **Type Safety Ready**: Structure makes it easier to add TypeScript in the future
7. **Performance**: Only loads required code through module imports
8. **Debugging**: Easier to locate and fix issues in specific modules

## Error Fixed

The original error `window.nodeManager?.createNewWallet is not a function` has been resolved by:

1. Consolidating `HiveAI` and `NodeManager` into a single `FedEdgeAI` class
2. Properly organizing wallet operations in `WalletManager`
3. Creating global helper functions for HTML onclick compatibility
4. Ensuring `createNewWallet` is accessible via `window.fedEdgeAI.walletManager.createNewWallet()`

## Development Notes

- The old `main.js` has been backed up to `main.js.backup`
- All code is now in English (translated from French)
- Modular structure allows for easier feature additions
- Each module exports its class for potential external use
- Global access is maintained for backward compatibility

## Future Enhancements

Potential improvements for the architecture:

1. Add TypeScript type definitions
2. Implement unit tests for each module
3. Add state management (e.g., Redux pattern)
4. Implement service workers for offline support
5. Add performance monitoring
6. Create component library for reusable UI elements
7. Add E2E testing with Playwright or Cypress
