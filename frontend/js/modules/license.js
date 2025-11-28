/**
 * License Manager Module
 * Handles license registration, verification, and UI updates
 */

export class LicenseManager {
    constructor(core) {
        this.core = core;
        this.nodeInfo = null;
        console.log('LicenseManager initialized');
    }

    /**
     * Initialize license system
     */
    init() {
        this.setupLicenseButton();

        // Wait for WebSocket to be ready before requesting node info
        let attempts = 0;
        const checkWebSocketReady = setInterval(() => {
            attempts++;
            console.log(`🔍 Checking WebSocket readiness (attempt ${attempts})...`);

            if (this.core.websocketManager?.socket?.readyState === WebSocket.OPEN) {
                console.log('✅ WebSocket is ready!');
                clearInterval(checkWebSocketReady);
                this.setupWebSocketListener();
                this.requestNodeInfo();
            } else {
                console.log('⏳ WebSocket not ready yet, state:', this.core.websocketManager?.socket?.readyState);
            }
        }, 100);

        // Timeout after 10 seconds
        setTimeout(() => {
            clearInterval(checkWebSocketReady);
            console.warn('⚠️ Timeout waiting for WebSocket connection');
        }, 10000);

        // Refresh node info every 30 seconds to check verification status
        setInterval(() => this.requestNodeInfo(), 30000);
    }

    /**
     * Setup license button click handler
     */
    setupLicenseButton() {
        const licenseBtn = document.getElementById('license-button');
        if (licenseBtn) {
            licenseBtn.addEventListener('click', () => {
                console.log('📧 License button clicked');
                this.showLicenseModal();
            });
            console.log('✅ License button handler attached');
        } else {
            console.warn('⚠️ License button not found in DOM');
        }
    }

    /**
     * Request node information via WebSocket
     */
    requestNodeInfo() {
        if (!this.core.websocketManager?.socket || this.core.websocketManager.socket.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket not connected, cannot request node info. State:', this.core.websocketManager?.socket?.readyState);
            return;
        }

        console.log('📡 Requesting node info via WebSocket...');
        this.core.websocketManager.socket.send(JSON.stringify({
            type: 'get_node_info'
        }));
        console.log('✅ get_node_info message sent');
    }

    /**
     * Setup WebSocket listener for node_info messages
     */
    setupWebSocketListener() {
        console.log('🔌 Setting up WebSocket listener for node_info...');

        // Add event listener to WebSocket manager's custom handlers
        if (!this.core.websocketManager.customHandlers) {
            this.core.websocketManager.customHandlers = [];
            console.log('✅ Created customHandlers array');
        }

        // Add our custom handler for node_info
        this.core.websocketManager.customHandlers.push((message) => {
            console.log('🔍 Custom handler received message type:', message.type);
            if (message.type === 'node_info') {
                console.log('📊 Node info received via WebSocket:', message);
                this.nodeInfo = message;
                this.updateLicenseButton();
                this.updateSystemInfo();
                return true; // Message handled
            }
            return false; // Not handled, pass to other handlers
        });

        console.log('✅ WebSocket listener registered, total handlers:', this.core.websocketManager.customHandlers.length);
    }

    /**
     * Update license button text based on status
     */
    updateLicenseButton() {
        const button = document.getElementById('license-button');
        if (!button || !this.nodeInfo) return;

        if (this.nodeInfo.verified) {
            // Verified user
            button.innerHTML = '🔐 License';
            button.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        } else if (this.nodeInfo.user_email) {
            // Registered but not verified
            button.innerHTML = '⏳ Pending';
            button.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
        } else {
            // Not registered
            button.innerHTML = '📧 Register';
            button.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
        }
    }

    /**
     * Update system info display
     */
    updateSystemInfo() {
        if (!this.nodeInfo) return;

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
                cpuInfo.parentElement.style.color = '#10b981';
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
                licenseInfo.parentElement.style.color = '#10b981';
            } else if (this.nodeInfo.user_email) {
                licenseInfo.textContent = '⏳ Pending';
                licenseInfo.parentElement.style.color = '#f59e0b';
            } else {
                licenseInfo.textContent = '✗ None';
                licenseInfo.parentElement.style.color = '#ef4444';
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

    /**
     * Show license modal based on current status
     */
    showLicenseModal() {
        if (!this.nodeInfo) {
            console.warn('⚠️ Node info not loaded yet');
            this.showNotification('Loading node information...', 'info');
            return;
        }

        if (!this.nodeInfo.user_email) {
            this.showRegisterForm();
        } else if (!this.nodeInfo.verified) {
            this.showPendingStatus();
        } else {
            this.showLicenseInfo();
        }
    }

    /**
     * Show registration form
     */
    showRegisterForm() {
        const modalHTML = `
            <div class="modal-overlay show" style="display: flex; z-index: 10000;">
                <div class="modal-content" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2 style="color: #fff; margin: 0;">📧 Register Your Node</h2>
                        <span class="close-btn" id="close-license-modal">&times;</span>
                    </div>
                    <div class="modal-body">
                        <p style="color: #d1d5db; margin-bottom: 20px;">
                            Register your node to join the FedEdge network and access advanced features.
                        </p>
                        <form id="register-form">
                            <div style="margin-bottom: 16px;">
                                <label style="color: #9ca3af; font-size: 12px; display: block; margin-bottom: 6px;">
                                    Email Address *
                                </label>
                                <input type="email" id="register-email" required
                                    style="width: 100%; padding: 10px; background: rgba(31, 41, 55, 0.5);
                                           border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px;
                                           color: #fff; font-size: 14px;"
                                    placeholder="your@email.com">
                            </div>
                            <div style="margin-bottom: 16px;">
                                <label style="color: #9ca3af; font-size: 12px; display: block; margin-bottom: 6px;">
                                    Name (Optional)
                                </label>
                                <input type="text" id="register-name"
                                    style="width: 100%; padding: 10px; background: rgba(31, 41, 55, 0.5);
                                           border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px;
                                           color: #fff; font-size: 14px;"
                                    placeholder="Your Name">
                            </div>
                            <div style="margin-bottom: 20px;">
                                <label style="color: #9ca3af; font-size: 11px; display: flex; align-items: center;">
                                    <input type="checkbox" id="register-terms" required
                                        style="margin-right: 8px;">
                                    I agree to the Terms of Service and Privacy Policy
                                </label>
                            </div>
                            <button type="submit" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                                   border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer;">
                                Register Node
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;

        const modal = document.getElementById('license-modal');
        modal.innerHTML = modalHTML;
        modal.style.display = 'flex';

        // Attach event listeners
        document.getElementById('close-license-modal').addEventListener('click', () => {
            modal.style.display = 'none';
        });

        document.getElementById('register-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.submitRegistration();
        });
    }

    /**
     * Show pending verification status
     */
    showPendingStatus() {
        const modalHTML = `
            <div class="modal-overlay show" style="display: flex; z-index: 10000;">
                <div class="modal-content" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2 style="color: #fff; margin: 0;">⏳ Verification Pending</h2>
                        <span class="close-btn" id="close-license-modal">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 48px; margin-bottom: 16px;">📧</div>
                            <h3 style="color: #fff; margin-bottom: 12px;">Check Your Email</h3>
                            <p style="color: #9ca3af; margin-bottom: 20px;">
                                We've sent a verification link to:<br>
                                <strong style="color: #3b82f6;">${this.nodeInfo.user_email}</strong>
                            </p>
                            <p style="color: #d1d5db; font-size: 14px; margin-bottom: 20px;">
                                Please click the link in the email to verify your account.<br>
                                This page will update automatically once verified.
                            </p>
                            <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2);
                                        border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                                    💡 Tip: Check your spam folder if you don't see the email within a few minutes.
                                </p>
                            </div>
                            <button id="resend-verification" style="padding: 10px 20px; background: rgba(255, 255, 255, 0.1);
                                   border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px; color: white; cursor: pointer;">
                                Resend Verification Email
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const modal = document.getElementById('license-modal');
        modal.innerHTML = modalHTML;
        modal.style.display = 'flex';

        document.getElementById('close-license-modal').addEventListener('click', () => {
            modal.style.display = 'none';
        });

        document.getElementById('resend-verification').addEventListener('click', () => {
            this.resendVerification();
        });
    }

    /**
     * Show verified license information
     */
    showLicenseInfo() {
        const modalHTML = `
            <div class="modal-overlay show" style="display: flex; z-index: 10000;">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h2 style="color: #fff; margin: 0;">🔐 License Information</h2>
                        <span class="close-btn" id="close-license-modal">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.1));
                                    border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                            <div style="text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 12px;">✓</div>
                                <h3 style="color: #10b981; margin: 0;">Verified Node</h3>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                            <div style="background: rgba(31, 41, 55, 0.5); border-radius: 6px; padding: 12px;">
                                <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Node ID</div>
                                <div style="color: #fff; font-size: 13px; font-family: monospace;">${this.nodeInfo.node_id || 'N/A'}</div>
                            </div>
                            <div style="background: rgba(31, 41, 55, 0.5); border-radius: 6px; padding: 12px;">
                                <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">User</div>
                                <div style="color: #fff; font-size: 13px;">${this.nodeInfo.user_name || this.nodeInfo.user_email}</div>
                            </div>
                            <div style="background: rgba(31, 41, 55, 0.5); border-radius: 6px; padding: 12px;">
                                <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Email</div>
                                <div style="color: #fff; font-size: 13px;">${this.nodeInfo.user_email || 'N/A'}</div>
                            </div>
                            <div style="background: rgba(31, 41, 55, 0.5); border-radius: 6px; padding: 12px;">
                                <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px;">Status</div>
                                <div style="color: #10b981; font-size: 13px; font-weight: 600;">✓ Verified</div>
                            </div>
                        </div>

                        <div style="background: rgba(31, 41, 55, 0.5); border-radius: 6px; padding: 16px;">
                            <h4 style="color: #fff; font-size: 14px; margin: 0 0 12px 0;">System Information</h4>
                            <div style="display: grid; gap: 8px; font-size: 12px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #9ca3af;">Operating System:</span>
                                    <span style="color: #fff;">${this.nodeInfo.os || 'N/A'}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #9ca3af;">Hardware:</span>
                                    <span style="color: #fff;">${this.nodeInfo.has_gpu ? 'GPU Available ✓' : 'CPU Only'}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #9ca3af;">Registration Date:</span>
                                    <span style="color: #fff;">${new Date().toLocaleDateString()}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const modal = document.getElementById('license-modal');
        modal.innerHTML = modalHTML;
        modal.style.display = 'flex';

        document.getElementById('close-license-modal').addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    /**
     * Submit registration to backend
     */
    async submitRegistration() {
        const email = document.getElementById('register-email').value;
        const name = document.getElementById('register-name').value;

        try {
            // Get client's public IP
            let clientPublicIp = null;
            try {
                console.log('🌐 Fetching client public IP for registration...');
                const ipResponse = await fetch('https://api.ipify.org?format=json', { timeout: 3000 });
                if (ipResponse.ok) {
                    const ipData = await ipResponse.json();
                    clientPublicIp = ipData.ip;
                    console.log(`✅ Client public IP: ${clientPublicIp}`);
                }
            } catch (error) {
                console.warn('⚠️ Could not fetch client public IP:', error);
            }

            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    name,
                    client_public_ip: clientPublicIp
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Registration successful! Check your email for verification.', 'success');
                document.getElementById('license-modal').style.display = 'none';
                setTimeout(() => this.requestNodeInfo(), 1000);
            } else {
                this.showNotification(data.message || 'Registration failed', 'error');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showNotification('Error connecting to server', 'error');
        }
    }

    /**
     * Resend verification email
     */
    async resendVerification() {
        try {
            const response = await fetch('/api/resend-verification', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                this.showNotification('Verification email resent!', 'success');
            } else {
                this.showNotification(data.message || 'Failed to resend email', 'error');
            }
        } catch (error) {
            console.error('Resend error:', error);
            this.showNotification('Error connecting to server', 'error');
        }
    }

    /**
     * Show notification message
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            z-index: 10001;
            max-width: 300px;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}
