/**
 * FedEdge - Intégration du bouton License dans l'UI
 * À intégrer dans votre fichier frontend existant
 */

// ============================================
// 1. REMPLACER LES BOUTONS LOGS/DEBUG
// ============================================

/**
 * Au lieu de:
 * - Bouton "Logs"
 * - Bouton "Config"  (garder)
 * - Bouton "Debug"
 *
 * Avoir:
 * - Bouton "Config"
 * - Bouton "License" (nouveau!)
 */

class FedEdgeLicenseUI {
  constructor(websocket) {
    this.ws = websocket;
    this.nodeInfo = null;
    this.init();
  }

  init() {
    // Charger les infos du node au démarrage
    this.loadNodeInfo();

    // Refresh toutes les 30 secondes pour voir si email vérifié
    setInterval(() => this.loadNodeInfo(), 30000);
  }

  // Demander les infos au backend
  loadNodeInfo() {
    this.ws.send(JSON.stringify({
      type: 'get_node_info'
    }));
  }

  // Recevoir les infos depuis le backend
  handleNodeInfo(data) {
    console.log('📊 Node info received:', data);
    this.nodeInfo = data;
    this.updateLicenseButton();
    this.updateSystemInfo();
  }

  // Gérer la réponse d'enregistrement
  handleRegistrationResult(data) {
    console.log('📧 Registration result received:', data);

    if (data.success) {
      this.showNotification(data.message || 'Registration sent! Please check your email.');
    } else {
      this.showNotification(data.message || 'Registration failed. Please try again.');
    }

    // Reload node info after registration
    setTimeout(() => this.loadNodeInfo(), 1000);
  }

  // Mettre à jour les informations système affichées
  updateSystemInfo() {
    console.log('🔧 Updating system info with:', this.nodeInfo);
    if (!this.nodeInfo) {
      console.warn('⚠️ No node info available');
      return;
    }

    // OS Info
    const osInfo = document.querySelector('#system-os-info span');
    if (osInfo && this.nodeInfo.os) {
      osInfo.textContent = this.nodeInfo.os.split(' ')[0] || 'Unknown';
    }

    // CPU/GPU Info
    const cpuInfo = document.querySelector('#system-cpu-info span');
    if (cpuInfo) {
      if (this.nodeInfo.has_gpu) {
        cpuInfo.textContent = 'GPU';
        cpuInfo.parentElement.style.color = '#10b981'; // Green for GPU
      } else {
        cpuInfo.textContent = 'CPU';
        cpuInfo.parentElement.style.color = 'rgba(255, 255, 255, 0.8)';
      }
    }

    // License Status
    const licenseInfo = document.querySelector('#system-license-info span');
    if (licenseInfo) {
      if (this.nodeInfo.verified) {
        licenseInfo.textContent = '✓ Verified';
        licenseInfo.parentElement.style.color = '#10b981'; // Green
      } else if (this.nodeInfo.user_email) {
        licenseInfo.textContent = '⏳ Pending';
        licenseInfo.parentElement.style.color = '#f59e0b'; // Orange
      } else {
        licenseInfo.textContent = '✗ None';
        licenseInfo.parentElement.style.color = '#ef4444'; // Red
      }
    }

    // User Info
    const userInfo = document.querySelector('#system-user-info span');
    if (userInfo) {
      if (this.nodeInfo.user_name) {
        userInfo.textContent = this.nodeInfo.user_name;
      } else if (this.nodeInfo.user_email) {
        userInfo.textContent = this.nodeInfo.user_email.split('@')[0];
      } else {
        userInfo.textContent = 'Guest';
      }
    }
  }

  // Mettre à jour le label du bouton
  updateLicenseButton() {
    const button = document.getElementById('license-button');
    if (!button) return;

    if (this.nodeInfo && this.nodeInfo.verified) {
      // Utilisateur vérifié
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2"/>
        </svg>
        <span>License</span>
      `;
      button.classList.add('verified');
    } else if (this.nodeInfo && this.nodeInfo.user_email) {
      // Email enregistré mais pas vérifié
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10" stroke-width="2"/>
          <path d="M12 6v6l4 2" stroke-width="2"/>
        </svg>
        <span>Pending...</span>
      `;
      button.classList.add('pending');
    } else {
      // Pas enregistré
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M12 15v2m0 0v2m0-2h2m-2 0H10m10 0a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2"/>
        </svg>
        <span>Register</span>
      `;
      button.classList.remove('verified', 'pending');
    }
  }

  // Afficher la modal de registration/license
  showLicenseModal() {
    console.log('🔐 showLicenseModal called, nodeInfo:', this.nodeInfo);
    if (!this.nodeInfo) {
      console.warn('⚠️ nodeInfo not available yet');
      return;
    }

    // Si non enregistré, afficher formulaire d'inscription
    if (!this.nodeInfo.user_email) {
      this.showRegisterForm();
    }
    // Si enregistré mais pas vérifié, afficher status
    else if (!this.nodeInfo.verified) {
      this.showPendingStatus();
    }
    // Si vérifié, afficher les infos de licence
    else {
      this.showLicenseInfo();
    }
  }

  // Formulaire d'inscription
  showRegisterForm() {
    console.log('📝 showRegisterForm called');

    // Remove any existing modal first
    const existingModal = document.getElementById('license-modal');
    if (existingModal) {
      existingModal.remove();
      console.log('🗑️ Removed existing modal');
    }

    // Create fresh modal directly in body
    const modal = document.createElement('div');
    modal.id = 'license-modal';
    modal.className = 'license-modal-container';

    // Set styles before adding to DOM
    modal.style.cssText = `
      display: flex !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      z-index: 2147483647 !important;
      pointer-events: auto !important;
      background: rgba(0, 0, 0, 0.8) !important;
      align-items: center !important;
      justify-content: center !important;
      margin: 0 !important;
      padding: 0 !important;
    `;

    modal.innerHTML = `
      <div class="modal-content" style="background: #1e293b !important; color: white !important; padding: 30px !important; border-radius: 10px !important; max-width: 500px !important; width: 90% !important; position: relative !important; z-index: 2147483647 !important; box-shadow: 0 20px 60px rgba(0,0,0,0.9) !important;" onclick="event.stopPropagation()">
        <h2 style="color: #3b82f6 !important; margin-top: 0;">Register Your Node</h2>
        <p style="color: #cbd5e1;">Register to track your node and receive updates</p>

        <form id="register-form">
          <div class="form-group" style="margin: 1.5rem 0;">
            <label style="display: block; margin-bottom: 0.5rem; color: #cbd5e1;">Email Address *</label>
            <input type="email" id="reg-email" required placeholder="your@email.com" style="width: 100%; padding: 0.75rem; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: white; font-size: 1rem; box-sizing: border-box;">
          </div>

          <div class="form-group" style="margin: 1.5rem 0;">
            <label style="display: block; margin-bottom: 0.5rem; color: #cbd5e1;">Name (Optional)</label>
            <input type="text" id="reg-name" placeholder="Your Name" style="width: 100%; padding: 0.75rem; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: white; font-size: 1rem; box-sizing: border-box;">
          </div>

          <div class="form-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" id="cancel-btn" style="flex: 1; padding: 0.75rem; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; background: #475569; color: white;">
              Cancel
            </button>
            <button type="submit" class="primary" style="flex: 1; padding: 0.75rem; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white;">Register</button>
          </div>
        </form>

        <div class="node-id" style="text-align: center; margin-top: 1rem; color: #64748b;">
          <small>Node ID: ${this.nodeInfo.node_id.substring(0, 8)}...</small>
        </div>
      </div>
    `;

    // Add to body as last child
    document.body.appendChild(modal);
    console.log('✅ Modal added to DOM');
    console.log('Modal position:', modal.getBoundingClientRect());
    console.log('Modal z-index:', window.getComputedStyle(modal).zIndex);

    // Handle cancel button
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
      cancelBtn.onclick = () => {
        modal.remove();
      };
    }

    // Handle click on background to close
    modal.onclick = (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    };

    // Handle form submit
    const form = document.getElementById('register-form');
    if (form) {
      form.onsubmit = (e) => {
        e.preventDefault();
        const email = document.getElementById('reg-email').value;
        const name = document.getElementById('reg-name').value;
        this.registerNode(email, name);
      };
    }
  }

  // Status en attente de vérification
  showPendingStatus() {
    // Remove existing modal
    const existingModal = document.getElementById('license-modal');
    if (existingModal) existingModal.remove();

    // Create fresh modal
    const modal = document.createElement('div');
    modal.id = 'license-modal';

    modal.style.cssText = `
      display: flex !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      z-index: 2147483647 !important;
      pointer-events: auto !important;
      background: rgba(0, 0, 0, 0.8) !important;
      align-items: center !important;
      justify-content: center !important;
      margin: 0 !important;
      padding: 0 !important;
    `;

    modal.innerHTML = `
      <div class="modal-content" style="background: #1e293b !important; color: white !important; padding: 30px !important; border-radius: 10px !important; max-width: 500px !important; width: 90% !important; position: relative !important; z-index: 2147483647 !important; box-shadow: 0 20px 60px rgba(0,0,0,0.9) !important;" onclick="event.stopPropagation()">
        <h2 style="color: #3b82f6 !important; margin-top: 0;">⏳ Verification Pending</h2>

        <div class="status-info" style="background: #0f172a; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Email:</strong> ${this.nodeInfo.user_email}</p>
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Node:</strong> ${this.nodeInfo.node_name || 'Unnamed'}</p>
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Status:</strong> <span style="color: #f59e0b; font-weight: bold;">Not Verified</span></p>
        </div>

        <div class="alert alert-info" style="padding: 1rem; border-radius: 8px; margin: 1rem 0; display: flex; gap: 1rem; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" stroke-width="2"/>
            <path d="M12 16v-4M12 8h.01" stroke-width="2"/>
          </svg>
          <div>
            <strong>Please check your email</strong>
            <p>Click the verification link we sent to activate your node.</p>
          </div>
        </div>

        <div class="node-id" style="text-align: center; margin-top: 1rem; color: #64748b;">
          <small>Node ID: ${this.nodeInfo.node_id.substring(0, 16)}</small>
        </div>

        <button id="close-btn" style="width: 100%; padding: 0.75rem; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; background: #475569; color: white; margin-top: 1rem;">
          Close
        </button>
      </div>
    `;

    document.body.appendChild(modal);

    // Handle close button
    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {
      closeBtn.onclick = () => modal.remove();
    }

    // Handle click on background
    modal.onclick = (e) => {
      if (e.target === modal) modal.remove();
    };
  }

  // Afficher les infos de licence (vérifié)
  showLicenseInfo() {
    let modal = document.getElementById('license-modal');

    if (!modal || modal.parentElement.tagName !== 'BODY') {
      if (modal) modal.remove();
      modal = document.createElement('div');
      modal.id = 'license-modal';
      document.body.appendChild(modal);
    } else {
      document.body.appendChild(modal);
    }

    modal.style.cssText = `
      display: flex !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      z-index: 2147483647 !important;
      pointer-events: auto !important;
      background: rgba(0, 0, 0, 0.8) !important;
      align-items: center !important;
      justify-content: center !important;
      margin: 0 !important;
      padding: 0 !important;
    `;

    modal.innerHTML = `
      <div class="modal-content" style="background: #1e293b !important; color: white !important; padding: 30px !important; border-radius: 10px !important; max-width: 500px !important; width: 90% !important; position: relative !important; z-index: 2147483647 !important; box-shadow: 0 20px 60px rgba(0,0,0,0.9) !important;" onclick="event.stopPropagation()">
        <h2 style="color: #3b82f6 !important; margin-top: 0;">✅ Node Registered</h2>

        <div class="status-info" style="background: #0f172a; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Email:</strong> ${this.nodeInfo.user_email}</p>
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Node:</strong> ${this.nodeInfo.node_name || 'Unnamed'}</p>
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Version:</strong> ${this.nodeInfo.version}</p>
          <p style="margin: 0.5rem 0; color: #cbd5e1;"><strong>Status:</strong> <span style="color: #10b981; font-weight: bold;">Verified</span></p>
        </div>

        <div class="node-details">
          <h3 style="color: #cbd5e1;">Node ID</h3>
          <code class="node-id-full" style="display: block; background: #0f172a; padding: 0.75rem; border-radius: 6px; font-family: monospace; font-size: 0.875rem; word-break: break-all;">${this.nodeInfo.node_id}</code>
        </div>

        <button id="close-verified-btn" style="width: 100%; padding: 0.75rem; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; background: #475569; color: white; margin-top: 1rem;">
          Close
        </button>
      </div>
    `;

    document.body.appendChild(modal);

    // Handle close button
    const closeBtn = document.getElementById('close-verified-btn');
    if (closeBtn) {
      closeBtn.onclick = () => modal.remove();
    }

    // Handle click on background
    modal.onclick = (e) => {
      if (e.target === modal) modal.remove();
    };
  }

  // Envoyer la demande d'enregistrement au backend
  registerNode(email, name) {
    console.log('📤 Sending registration to backend:', { email, name });

    this.ws.send(JSON.stringify({
      type: 'register_node',
      email: email,
      name: name
    }));

    // Fermer la modal
    const modal = document.getElementById('license-modal');
    if (modal) {
      modal.remove();
    }

    // Afficher une notification temporaire (sera remplacée par la réponse du serveur)
    this.showNotification('Sending registration...');

    // Recharger les infos dans 2 secondes
    setTimeout(() => this.loadNodeInfo(), 2000);
  }

  // Notification simple
  showNotification(message) {
    const notif = document.createElement('div');
    notif.className = 'notification';
    notif.textContent = message;
    document.body.appendChild(notif);

    setTimeout(() => {
      notif.classList.add('show');
    }, 100);

    setTimeout(() => {
      notif.classList.remove('show');
      setTimeout(() => notif.remove(), 300);
    }, 5000);
  }
}

// ============================================
// 2. INTEGRATION DANS VOTRE HTML
// ============================================

/**
 * Dans votre HTML, remplacer:
 *
 * <button id="logs-button">Logs</button>
 * <button id="config-button">Config</button>
 * <button id="debug-button">Debug</button>
 *
 * Par:
 *
 * <button id="config-button">Config</button>
 * <button id="license-button">Register</button>
 *
 * Et ajouter la modal:
 * <div id="license-modal" style="display: none;"></div>
 */

// ============================================
// 3. INTEGRATION DANS VOTRE WEBSOCKET
// ============================================

// ============================================
// 4. CSS À AJOUTER
// ============================================

const licenseCss = `
/* Bouton License */
#license-button.verified {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

#license-button.pending {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1e293b;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  color: white;
}

.modal-content h2 {
  margin-top: 0;
  color: #3b82f6;
}

.form-group {
  margin: 1.5rem 0;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #cbd5e1;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: white;
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.form-actions button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.form-actions button.primary {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
}

.status-info {
  background: #0f172a;
  border-radius: 8px;
  padding: 1.5rem;
  margin: 1.5rem 0;
}

.status-info p {
  margin: 0.5rem 0;
  color: #cbd5e1;
}

.status-verified {
  color: #10b981;
  font-weight: bold;
}

.status-pending {
  color: #f59e0b;
  font-weight: bold;
}

.alert {
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  display: flex;
  gap: 1rem;
}

.alert-info {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.node-id {
  text-align: center;
  margin-top: 1rem;
  color: #64748b;
}

.node-id-full {
  display: block;
  background: #0f172a;
  padding: 0.75rem;
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.875rem;
  word-break: break-all;
}

/* Notification */
.notification {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  background: #10b981;
  color: white;
  padding: 1rem 1.5rem;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  transform: translateY(100px);
  opacity: 0;
  transition: all 0.3s;
  z-index: 2000;
}

.notification.show {
  transform: translateY(0);
  opacity: 1;
}
`;

// Inject CSS into the page
if (!document.getElementById('license-ui-styles')) {
  const styleEl = document.createElement('style');
  styleEl.id = 'license-ui-styles';
  styleEl.textContent = licenseCss;
  document.head.appendChild(styleEl);
  console.log('✅ License UI styles injected');
}

// Expose FedEdgeLicenseUI globally
window.FedEdgeLicenseUI = FedEdgeLicenseUI;
// Cache bust timestamp: 1759920500
