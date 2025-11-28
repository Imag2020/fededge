// Federated Edge Preview - Data injection script
// Mock data for federated learning node

const FED_STATE = {
  nodeId: "fededge-node-local",
  device: { os: "Linux", cpu: "x86_64", accel: "CPU", ramGB: 16 },
  model: { name: "Gemma3-mini-LoRA", version: "0.6.2", sizeMB: 820 },
  agents: [
    { name: "Orchestrator", status: "running", lastRun: "13:02" },
    { name: "Scanner", status: "running", lastRun: "13:04" },
    { name: "Critic", status: "idle", lastRun: "12:58" },
    { name: "Compressor", status: "idle", lastRun: "03:11" }
  ],
  todaySignalsLocal: 3,
  peers: 0,
  port: 8787,
  storageUsedGB: 2.3
};

// Initialize Federated Edge Preview UI
function initFederatedEdgePreview() {
  console.log('🌐 Initializing Federated Edge Preview...');

  // Responsive timeline display
  function updateTimelineDisplay() {
    const desktop = document.querySelector('.fed-timeline-desktop');
    const mobile = document.querySelector('.fed-timeline-mobile');

    if (window.innerWidth >= 768) {
      if (desktop) desktop.style.display = 'flex';
      if (mobile) mobile.style.display = 'none';
    } else {
      if (desktop) desktop.style.display = 'none';
      if (mobile) mobile.style.display = 'flex';
    }
  }

  // Update Node Essentials
  function updateNodeEssentials() {
    // Node ID
    const nodeIdEl = document.getElementById('fed-node-id');
    if (nodeIdEl) {
      nodeIdEl.textContent = FED_STATE.nodeId;
      nodeIdEl.setAttribute('aria-label', `Node ID: ${FED_STATE.nodeId}`);
    }

    // Device info
    const deviceInfoEl = document.getElementById('fed-device-info');
    const deviceSpecsEl = document.getElementById('fed-device-specs');
    if (deviceInfoEl && deviceSpecsEl) {
      deviceInfoEl.textContent = `${FED_STATE.device.os} (${FED_STATE.device.cpu})`;
      deviceSpecsEl.textContent = `${FED_STATE.device.accel} • ${FED_STATE.device.ramGB}GB RAM`;
    }

    // Model info
    const modelNameEl = document.getElementById('fed-model-name');
    const modelInfoEl = document.getElementById('fed-model-info');
    if (modelNameEl && modelInfoEl) {
      modelNameEl.textContent = FED_STATE.model.name;
      modelInfoEl.textContent = `v${FED_STATE.model.version} • ${FED_STATE.model.sizeMB}MB`;
    }

    // Signals today
    const signalsTodayEl = document.getElementById('fed-signals-today');
    if (signalsTodayEl) {
      signalsTodayEl.textContent = FED_STATE.todaySignalsLocal;
      signalsTodayEl.setAttribute('aria-label', `${FED_STATE.todaySignalsLocal} signals generated today`);
    }

    // Peers
    const peersCountEl = document.getElementById('fed-peers-count');
    const peersBadgeEl = document.getElementById('fed-peers-badge');
    const portEl = document.getElementById('fed-port');
    if (peersCountEl) {
      peersCountEl.textContent = FED_STATE.peers;
    }
    if (peersBadgeEl && FED_STATE.peers === 0) {
      peersBadgeEl.style.display = 'inline-block';
      peersBadgeEl.setAttribute('aria-label', 'Pre-production mode, local only');
    }
    if (portEl) {
      portEl.textContent = `Port: ${FED_STATE.port}`;
    }

    // Storage
    const storageEl = document.getElementById('fed-storage');
    if (storageEl) {
      storageEl.textContent = `${FED_STATE.storageUsedGB.toFixed(1)} GB`;
      storageEl.setAttribute('aria-label', `${FED_STATE.storageUsedGB.toFixed(1)} GB storage used`);
    }
  }

  // Update AI Agents list
  function updateAgentsList() {
    const agentsListEl = document.getElementById('fed-agents-list');
    if (!agentsListEl) return;

    const statusColors = {
      running: '#10b981',
      idle: '#9fb0c3',
      error: '#ef4444'
    };

    const statusIcons = {
      running: '▶',
      idle: '⏸',
      error: '⚠'
    };

    const agentsHTML = FED_STATE.agents.map(agent => `
      <div style="
        background: rgba(0, 0, 0, 0.2);
        border-left: 3px solid ${statusColors[agent.status]};
        padding: 10px;
        border-radius: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      " role="listitem" aria-label="${agent.name} agent ${agent.status}">
        <div>
          <div style="color: #e5eef6; font-size: 12px; font-weight: 600; margin-bottom: 2px;">
            ${agent.name}
          </div>
          <div style="color: #9fb0c3; font-size: 10px;">
            Last run: ${agent.lastRun}
          </div>
        </div>
        <div style="
          color: ${statusColors[agent.status]};
          font-size: 10px;
          font-weight: 600;
          padding: 4px 8px;
          background: rgba(${agent.status === 'running' ? '16, 185, 129' : '156, 163, 175'}, 0.1);
          border-radius: 4px;
          display: flex;
          align-items: center;
          gap: 4px;
        ">
          <span style="font-size: 8px;">${statusIcons[agent.status]}</span>
          ${agent.status.toUpperCase()}
        </div>
      </div>
    `).join('');

    agentsListEl.innerHTML = agentsHTML;
    agentsListEl.setAttribute('role', 'list');
  }

  // Initial load
  updateTimelineDisplay();
  updateNodeEssentials();
  updateAgentsList();

  // Handle window resize for responsive timeline
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(updateTimelineDisplay, 150);
  });

  console.log('✅ Federated Edge Preview initialized');
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initFederatedEdgePreview);
} else {
  initFederatedEdgePreview();
}

// Export for manual refresh if needed
window.refreshFederatedEdgePreview = () => {
  initFederatedEdgePreview();
};
