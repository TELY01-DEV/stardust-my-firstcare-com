// ===== OPERA GODEYE PANEL - ENHANCED JAVASCRIPT =====
console.log('🚀 Opera GodEye Panel v2.0 loaded successfully!');

// ===== GLOBAL CONFIGURATION =====
const CONFIG = {
    AUTO_REFRESH_INTERVAL: 30000, // 30 seconds
    MAX_MESSAGES: 100,
    MAX_TRANSACTIONS: 50,
    WEBSOCKET_RECONNECT_DELAY: 5000,
    ANIMATION_DURATION: 300,
    CHART_COLORS: {
        primary: '#024F96',
        secondary: '#00A1E8',
        success: '#28a745',
        warning: '#ffc107',
        danger: '#dc3545',
        info: '#17a2b8'
    }
};

// ===== MAIN APPLICATION CLASS =====
class OperaGodEyeApp {
    constructor() {
        this.socket = null;
        this.messages = [];
        this.transactions = [];
        this.stats = {
            totalMessages: 0,
            ava4Count: 0,
            katiCount: 0,
            qubeCount: 0,
            ava4Active: 0,
            katiActive: 0,
            qubeActive: 0,
            processingRate: 0
        };
        this.devices = {
            ava4: [],
            kati: [],
            qube: []
        };
        this.patients = [];
        this.recentMappings = [];
        this.deviceMappings = { ava4: [], kati: [], qube: [], summary: {} };
        this.patientMappings = { patients: [], summary: {} };
        this.userProfile = null;
        this.currentTab = 'dashboard';
        this.charts = {};
        this.notifications = [];
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }
    
    init() {
        console.log('🚀 Initializing Opera GodEye App...');
        
        // Setup navigation
        this.setupNavigation();
        
        // Setup notifications
        this.setupNotifications();
        
        // Setup charts
        this.setupCharts();
        
        // Load initial data
        this.loadInitialData();
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Setup auto-refresh
        this.setupAutoRefresh();
        
        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        console.log('✅ Opera GodEye App initialized');
    }
    
    // ===== NAVIGATION SYSTEM =====
    setupNavigation() {
        console.log('🔧 Setting up navigation...');
        
        const navLinks = document.querySelectorAll('[data-tab]');
        console.log('📋 Found navigation links:', navLinks.length);
        
        navLinks.forEach(link => {
            console.log('🔗 Setting up link:', link.getAttribute('data-tab'));
            
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = link.getAttribute('data-tab');
                console.log('🖱️ Navigation link clicked:', tabName);
                this.switchTab(tabName);
            });
        });
        
        // Handle URL hash changes
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.substring(1);
            console.log('🔗 Hash changed:', hash);
            if (hash) {
                this.switchTab(hash);
            }
        });
        
        // Handle initial hash
        const hash = window.location.hash.substring(1);
        console.log('🔗 Initial hash:', hash);
        if (hash) {
            this.switchTab(hash);
        }
        
        console.log('✅ Navigation setup complete');
    }
    
    switchTab(tabName) {
        console.log('🔄 Switching to tab:', tabName);
        
        try {
            // Update navigation
            document.querySelectorAll('[data-tab]').forEach(link => {
                link.classList.remove('active');
            });
            
            const activeLink = document.querySelector(`[data-tab="${tabName}"]`);
            if (activeLink) {
                activeLink.classList.add('active');
                console.log('✅ Navigation link updated');
            } else {
                console.error('❌ Navigation link not found:', tabName);
            }
            
            // Update tab content with animation
            document.querySelectorAll('.main-tab-content').forEach(tab => {
                tab.classList.remove('active');
                tab.style.opacity = '0';
                tab.style.transform = 'translateY(20px)';
            });
            
            const activeTab = document.getElementById(`${tabName}-tab`);
            if (activeTab) {
                activeTab.classList.add('active');
                // Animate in
                setTimeout(() => {
                    activeTab.style.opacity = '1';
                    activeTab.style.transform = 'translateY(0)';
                }, 50);
                console.log('✅ Tab content updated');
            } else {
                console.error('❌ Tab content not found:', `${tabName}-tab`);
            }
            
            // Update page title and description
            this.updatePageHeader(tabName);
            
            // Load tab-specific data
            this.loadTabData(tabName);
            
            this.currentTab = tabName;
            console.log('✅ Tab switch complete:', tabName);
            
        } catch (error) {
            console.error('💥 Error switching tab:', error);
            this.showNotification('Error switching tab', 'error');
        }
    }
    
    updatePageHeader(tabName) {
        const titles = {
            'dashboard': 'Real-time MQTT Monitoring Dashboard',
            'messages': 'MQTT Message Transactions',
            'devices': 'Device Management',
            'patients': 'Patient Management',
            'transactions': 'Data Processing Transactions',
            'device-status': 'Device Status Dashboard'
        };
        
        const descriptions = {
            'dashboard': 'Monitor device messages, patient mapping, and system statistics',
            'messages': 'View all MQTT message transactions and device communications',
            'devices': 'Manage and monitor AVA4, Kati Watch, and Qube-Vital devices',
            'patients': 'View patient information and device mapping status',
            'transactions': 'Monitor data processing transactions, schema, and collection statistics',
            'device-status': 'Real-time device status monitoring and management'
        };
        
        const titleElement = document.getElementById('page-title');
        const descElement = document.getElementById('page-description');
        
        if (titleElement) {
            titleElement.textContent = titles[tabName] || titles['dashboard'];
            titleElement.classList.add('fade-in');
        }
        if (descElement) {
            descElement.textContent = descriptions[tabName] || descriptions['dashboard'];
            descElement.classList.add('fade-in');
        }
    }
    
    loadTabData(tabName) {
        console.log('📋 Loading data for tab:', tabName);
        
        switch (tabName) {
            case 'dashboard':
                this.loadStatistics();
                this.loadRecentMappings();
                break;
            case 'messages':
                this.updateMessagesTable();
                break;
            case 'devices':
                this.loadDeviceMappings();
                this.updateDevicesTables();
                break;
            case 'patients':
                this.loadPatientMappings();
                this.updatePatientsTable();
                break;
            case 'transactions':
                this.updateTransactionsData();
                break;
            case 'device-status':
                this.updateDeviceStatusDisplay();
                break;
        }
    }
    
    // ===== NOTIFICATION SYSTEM =====
    setupNotifications() {
        // Create notification container
        const notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.className = 'notification-container';
        notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(notificationContainer);
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} slide-in-right`;
        notification.style.cssText = `
            background: white;
            border-left: 4px solid var(--mfc-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'});
            border-radius: var(--mfc-radius);
            box-shadow: var(--mfc-shadow-lg);
            padding: var(--mfc-spacing-4);
            margin-bottom: var(--mfc-spacing-3);
            display: flex;
            align-items: center;
            gap: var(--mfc-spacing-3);
            animation: slideInRight 0.3s ease-out;
        `;
        
        const icon = document.createElement('i');
        icon.className = `ti ti-${type === 'error' ? 'alert-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}`;
        icon.style.color = `var(--mfc-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'})`;
        
        const text = document.createElement('span');
        text.textContent = message;
        
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '<i class="ti ti-x"></i>';
        closeBtn.className = 'btn btn-sm btn-outline-secondary ms-auto';
        closeBtn.onclick = () => this.removeNotification(notification);
        
        notification.appendChild(icon);
        notification.appendChild(text);
        notification.appendChild(closeBtn);
        
        document.getElementById('notification-container').appendChild(notification);
        
        // Auto remove after duration
        setTimeout(() => {
            this.removeNotification(notification);
        }, duration);
        
        this.notifications.push(notification);
    }
    
    removeNotification(notification) {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications = this.notifications.filter(n => n !== notification);
        }, 300);
    }
    
    // ===== CHART SYSTEM =====
    setupCharts() {
        // Initialize charts when needed
        this.charts = {};
    }
    
    createChart(canvasId, type, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Create new chart
        this.charts[canvasId] = new Chart(ctx, {
            type: type,
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                },
                ...options
            }
        });
        
        return this.charts[canvasId];
    }
    
    // ===== WEBSOCKET CONNECTION =====
    connectWebSocket() {
        try {
            console.log('🔌 WebSocket connection temporarily disabled - focusing on data loading first');
            this.updateConnectionStatus('disconnected');
            this.showNotification('WebSocket disabled - using polling mode', 'info');
            return;
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/socket.io/`;
            
            console.log('🔌 Connecting to WebSocket:', wsUrl);
            
            // Check if Socket.IO is available
            if (typeof io === 'undefined') {
                console.warn('⚠️ Socket.IO not available, skipping WebSocket connection');
                this.updateConnectionStatus('disconnected');
                return;
            }
            
            this.socket = io(wsUrl, {
                transports: ['websocket', 'polling'],
                timeout: 20000,
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: this.maxReconnectAttempts,
                forceNew: true
            });
            
            this.socket.on('connect', () => {
                console.log('✅ WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.showNotification('WebSocket connected', 'success');
                
                // Subscribe to events
                this.socket.emit('get_statistics');
                this.socket.emit('subscribe_transactions');
            });
            
            this.socket.on('disconnect', () => {
                console.log('❌ WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.showNotification('WebSocket disconnected', 'error');
            });
            
            this.socket.on('connect_error', (error) => {
                console.error('💥 WebSocket connection error:', error);
                this.reconnectAttempts++;
                this.updateConnectionStatus('connecting');
                
                if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    this.showNotification('Failed to connect to WebSocket', 'error');
                    console.warn('⚠️ WebSocket connection failed, continuing without real-time updates');
                }
            });
            
            this.socket.on('mqtt_message', (data) => {
                this.handleMQTTMessage(data);
            });
            
            this.socket.on('transaction', (data) => {
                this.handleTransaction(data);
            });
            
            this.socket.on('statistics', (data) => {
                this.handleStatistics(data);
            });
            
        } catch (error) {
            console.error('💥 Error setting up WebSocket:', error);
            this.showNotification('Failed to setup WebSocket connection', 'error');
            console.warn('⚠️ WebSocket setup failed, continuing without real-time updates');
        }
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        const textElement = document.getElementById('connection-text');
        
        if (statusElement) {
            statusElement.className = `connection-indicator connection-${status}`;
        }
        
        if (textElement) {
            const statusTexts = {
                'connected': 'Connected',
                'connecting': 'Connecting...',
                'disconnected': 'Disconnected'
            };
            textElement.textContent = statusTexts[status] || 'Unknown';
        }
    }
    
    // ===== DATA HANDLING =====
    handleMQTTMessage(message) {
        console.log('📨 Received MQTT message:', message);
        
        // Add to messages array
        this.messages.unshift(message);
        if (this.messages.length > CONFIG.MAX_MESSAGES) {
            this.messages = this.messages.slice(0, CONFIG.MAX_MESSAGES);
        }
        
        // Update display
        this.addMessageToDisplay(message);
        
        // Update statistics
        this.stats.totalMessages++;
        this.updateStatisticsDisplay();
        
        // Show notification for important messages
        if (message.status === 'error' || message.status === 'patient_not_found') {
            this.showNotification(`MQTT Error: ${message.topic}`, 'error');
        }
    }
    
    handleTransaction(transaction) {
        console.log('📊 Received transaction:', transaction);
        
        // Add to transactions array
        this.transactions.unshift(transaction);
        if (this.transactions.length > CONFIG.MAX_TRANSACTIONS) {
            this.transactions = this.transactions.slice(0, CONFIG.MAX_TRANSACTIONS);
        }
        
        // Update display
        this.updateTransactionsDisplay(this.transactions);
        
        // Show notification for failed transactions
        if (transaction.status === 'error') {
            this.showNotification(`Transaction failed: ${transaction.operation}`, 'error');
        }
    }
    
    handleStatistics(stats) {
        console.log('📈 Received statistics:', stats);
        this.stats = { ...this.stats, ...stats };
        this.updateStatisticsDisplay();
    }
    
    // ===== DISPLAY UPDATES =====
    addMessageToDisplay(message) {
        const container = document.getElementById('messages-container');
        if (!container) return;
        
        const messageElement = this.createMessageElement(message);
        
        // Add animation class
        messageElement.classList.add('new');
        
        // Insert at top
        if (container.firstChild) {
            container.insertBefore(messageElement, container.firstChild);
        } else {
            container.appendChild(messageElement);
        }
        
        // Remove animation class after animation completes
        setTimeout(() => {
            messageElement.classList.remove('new');
        }, 500);
    }
    
    createMessageElement(message) {
        const div = document.createElement('div');
        div.className = 'message-card';
        
        const deviceType = this.getDeviceType(message.topic);
        const deviceBadgeClass = this.getDeviceBadgeClass(deviceType);
        const statusClass = this.getStatusClass(message.status);
        
        div.innerHTML = `
            <div class="message-header">
                <div class="d-flex align-items-center gap-2">
                    <span class="badge ${deviceBadgeClass}">${deviceType.toUpperCase()}</span>
                    <span class="badge ${statusClass}">${message.status}</span>
                </div>
                <div class="message-timestamp">${this.formatTimestamp(message.timestamp)}</div>
            </div>
            <div class="message-preview">
                <strong>Topic:</strong> ${message.topic}<br>
                <strong>Payload:</strong> ${this.truncateText(JSON.stringify(message.payload), 100)}
            </div>
            ${message.patient_mapping ? `
                <div class="patient-mapping ${message.patient_mapping.success ? 'patient-mapping-success' : 'patient-mapping-error'}">
                    <div class="patient-info">
                        <span class="patient-name">${message.patient_mapping.patient_name || 'Unknown'}</span>
                        <span class="patient-id">(${message.patient_mapping.patient_id || 'N/A'})</span>
                    </div>
                    <div class="mapping-details">${message.patient_mapping.details || ''}</div>
                </div>
            ` : ''}
        `;
        
        return div;
    }
    
    updateStatisticsDisplay() {
        // Update main statistics
        document.getElementById('total-messages').textContent = this.stats.totalMessages.toLocaleString();
        document.getElementById('ava4-count').textContent = this.stats.ava4Count.toLocaleString();
        document.getElementById('kati-count').textContent = this.stats.katiCount.toLocaleString();
        document.getElementById('qube-count').textContent = this.stats.qubeCount.toLocaleString();
        document.getElementById('ava4-active').textContent = this.stats.ava4Active.toLocaleString();
        document.getElementById('kati-active').textContent = this.stats.katiActive.toLocaleString();
        document.getElementById('qube-active').textContent = this.stats.qubeActive.toLocaleString();
        document.getElementById('processing-rate').textContent = this.stats.processingRate.toLocaleString();
        
        // Update progress bars
        this.updateProgressBar('processing-progress', this.stats.processingRate, 100);
        this.updateProgressBar('ava4-progress', this.stats.ava4Active, this.stats.ava4Count);
        this.updateProgressBar('kati-progress', this.stats.katiActive, this.stats.katiCount);
        this.updateProgressBar('qube-progress', this.stats.qubeActive, this.stats.qubeCount);
    }
    
    updateProgressBar(elementId, value, max) {
        const element = document.getElementById(elementId);
        if (element) {
            const percentage = max > 0 ? (value / max) * 100 : 0;
            element.style.width = `${percentage}%`;
            element.style.transition = 'width 0.5s ease-in-out';
        }
    }
    
    // ===== UTILITY FUNCTIONS =====
    getDeviceType(topic) {
        if (topic.includes('ava4')) return 'ava4';
        if (topic.includes('kati')) return 'kati';
        if (topic.includes('qube')) return 'qube';
        return 'unknown';
    }
    
    getDeviceBadgeClass(deviceType) {
        const classes = {
            'ava4': 'device-type-ava4',
            'kati': 'device-type-kati',
            'qube': 'device-type-qube',
            'unknown': 'badge-secondary'
        };
        return classes[deviceType] || 'badge-secondary';
    }
    
    getStatusClass(status) {
        const classes = {
            'processed': 'badge-success',
            'patient_not_found': 'badge-warning',
            'error': 'badge-danger',
            'unknown': 'badge-secondary'
        };
        return classes[status] || 'badge-secondary';
    }
    
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        } else if (diff < 86400000) { // Less than 1 day
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        } else {
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }
    }
    
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    // ===== AUTO REFRESH =====
    setupAutoRefresh() {
        // Auto refresh every 30 seconds
        setInterval(() => {
            if (this.currentTab === 'dashboard') {
                this.loadStatistics();
            }
        }, CONFIG.AUTO_REFRESH_INTERVAL);
    }
    
    // ===== KEYBOARD SHORTCUTS =====
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + R to refresh
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                this.refreshData();
            }
            
            // Ctrl/Cmd + F to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                const searchInput = document.getElementById('search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape to clear filters
            if (e.key === 'Escape') {
                this.clearDeviceFilters();
            }
        });
    }
    
    // ===== API CALLS =====
    async loadInitialData() {
        console.log('📊 Loading initial data...');
        
        try {
            await Promise.all([
                this.loadUserProfile(),
                this.loadStatistics(),
                this.loadDevices(),
                this.loadPatients(),
                this.loadRecentMappings()  // Add recent mappings for dashboard
            ]);
            
            console.log('✅ Initial data loaded successfully');
        } catch (error) {
            console.error('❌ Error loading initial data:', error);
        }
    }
    
    async loadUserProfile() {
        try {
            const response = await fetch('/api/user/profile');
            if (response.ok) {
                this.userProfile = await response.json();
                this.updateUserDisplay();
            }
        } catch (error) {
            console.error('Error loading user profile:', error);
        }
    }
    
    updateUserDisplay() {
        const userNameElement = document.getElementById('user-name');
        if (userNameElement && this.userProfile) {
            userNameElement.textContent = this.userProfile.name || 'User';
        }
    }
    
    async loadStatistics() {
        try {
            const response = await fetch('/api/statistics');
            if (response.ok) {
                const data = await response.json();
                this.stats = { ...this.stats, ...data };
                this.updateStatisticsDisplay();
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }
    
    async loadDevices() {
        try {
            const response = await fetch('/api/devices');
            if (response.ok) {
                const result = await response.json();
                console.log('🔍 Devices API response:', result);
                
                // Handle the nested data structure from API
                if (result.success && result.data) {
                    this.devices = result.data;
                    console.log('✅ Devices loaded from result.data:', this.devices);
                } else if (Array.isArray(result)) {
                    this.devices = result;
                    console.log('✅ Devices loaded from array:', this.devices);
                } else if (result && typeof result === 'object') {
                    // If it's an object with device types, extract arrays
                    this.devices = {
                        ava4: Array.isArray(result.ava4) ? result.ava4 : [],
                        kati: Array.isArray(result.kati) ? result.kati : [],
                        qube: Array.isArray(result.qube) ? result.qube : []
                    };
                    console.log('✅ Devices loaded from object structure:', this.devices);
                } else {
                    this.devices = { ava4: [], kati: [], qube: [] };
                    console.log('⚠️ No devices data found, using empty structure');
                }
                this.updateDevicesDisplay();
            } else {
                console.error('❌ Devices API error:', response.status, response.statusText);
                this.devices = { ava4: [], kati: [], qube: [] };
            }
        } catch (error) {
            console.error('Error loading devices:', error);
            this.devices = { ava4: [], kati: [], qube: [] };
        }
    }
    
    async loadPatients() {
        try {
            const response = await fetch('/api/patients');
            if (response.ok) {
                const result = await response.json();
                console.log('🔍 Patients API response:', result);
                
                // Handle the nested data structure from API
                if (result.success && result.data) {
                    this.patients = result.data;
                    console.log('✅ Patients loaded from result.data:', this.patients);
                } else if (Array.isArray(result)) {
                    this.patients = result;
                    console.log('✅ Patients loaded from array:', this.patients);
                } else if (result && typeof result === 'object' && Array.isArray(result.patients)) {
                    this.patients = result.patients;
                    console.log('✅ Patients loaded from result.patients:', this.patients);
                } else {
                    this.patients = [];
                    console.log('⚠️ No patients data found, using empty array');
                }
                this.updatePatientsDisplay();
            } else {
                console.error('❌ Patients API error:', response.status, response.statusText);
                this.patients = [];
            }
        } catch (error) {
            console.error('Error loading patients:', error);
            this.patients = [];
        }
    }
    
    // ===== DISPLAY UPDATES =====
    updateDevicesDisplay() {
        // Update device containers
        this.updateDevicesContainer('devices-container', this.devices);
    }
    
    updateDevicesContainer(containerId, devices) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Handle different data structures
        let deviceArray = [];
        
        if (Array.isArray(devices)) {
            deviceArray = devices;
        } else if (devices && typeof devices === 'object') {
            // If it's an object with device types, flatten into array
            if (devices.ava4 && Array.isArray(devices.ava4)) {
                deviceArray = deviceArray.concat(devices.ava4.map(d => ({...d, type: 'AVA4'})));
            }
            if (devices.kati && Array.isArray(devices.kati)) {
                deviceArray = deviceArray.concat(devices.kati.map(d => ({...d, type: 'Kati'})));
            }
            if (devices.qube && Array.isArray(devices.qube)) {
                deviceArray = deviceArray.concat(devices.qube.map(d => ({...d, type: 'Qube-Vital'})));
            }
        }
        
        if (!deviceArray || deviceArray.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-devices"></i>
                    <p class="mt-2">No devices found</p>
                </div>
            `;
            return;
        }
        
        const html = deviceArray.map(device => `
            <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
                <div>
                    <div class="fw-semibold">${device.name || device.device_id || device.id || 'Unknown'}</div>
                    <div class="text-muted small">${device.type || device.device_type || 'Unknown'}</div>
                </div>
                <span class="badge ${device.active ? 'badge-success' : 'badge-secondary'}">
                    ${device.active ? 'Active' : 'Inactive'}
                </span>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    updatePatientsDisplay() {
        // Update patient containers
        this.updatePatientsContainer('patients-container', this.patients);
    }
    
    updatePatientsContainer(containerId, patients) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Handle different data structures
        let patientArray = [];
        
        if (Array.isArray(patients)) {
            patientArray = patients;
        } else if (patients && typeof patients === 'object' && patients.data && Array.isArray(patients.data)) {
            patientArray = patients.data;
        }
        
        if (!patientArray || patientArray.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-users"></i>
                    <p class="mt-2">No patients found</p>
                </div>
            `;
            return;
        }
        
        const html = patientArray.map(patient => `
            <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
                <div>
                    <div class="fw-semibold">${patient.name || `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || 'Unknown'}</div>
                    <div class="text-muted small">ID: ${patient.patient_id || patient.id || 'N/A'}</div>
                </div>
                <span class="badge ${patient.status === 'Active' ? 'badge-success' : 'badge-secondary'}">
                    ${patient.status || 'Unknown'}
                </span>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    // ===== TAB-SPECIFIC UPDATES =====
    updateMessagesTable() {
        const container = document.getElementById('messages-table-container');
        if (!container) return;
        
        if (this.messages.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-message-circle-off"></i>
                    <p class="mt-2">No messages available</p>
                </div>
            `;
            return;
        }
        
        const html = this.messages.map(message => `
            <div class="message-card">
                ${this.createMessageElement(message).innerHTML}
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    updateDevicesTables() {
        // Update device tables for each type
        this.updateAva4DevicesTable();
        this.updateKatiDevicesTable();
        this.updateQubeDevicesTable();
    }
    
    updateAva4DevicesTable() {
        const container = document.getElementById('ava4-devices-table');
        if (!container) return;
        
        const ava4Devices = this.devices.ava4 || [];
        this.updateDeviceTable(container, ava4Devices, 'AVA4');
    }
    
    updateKatiDevicesTable() {
        const container = document.getElementById('kati-devices-table');
        if (!container) return;
        
        const katiDevices = this.devices.kati || [];
        this.updateDeviceTable(container, katiDevices, 'Kati');
    }
    
    updateQubeDevicesTable() {
        const container = document.getElementById('qube-devices-table');
        if (!container) return;
        
        const qubeDevices = this.devices.qube || [];
        this.updateDeviceTable(container, qubeDevices, 'Qube-Vital');
    }
    
    updateDeviceTable(container, devices, deviceType) {
        if (!devices || devices.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-devices"></i>
                    <p class="mt-2">No ${deviceType} devices found</p>
                </div>
            `;
            return;
        }
        
        const html = `
            <div class="table-responsive">
                <table class="table table-vcenter">
                    <thead>
                        <tr>
                            <th>Device ID</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Last Seen</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${devices.map(device => `
                            <tr>
                                <td>${device.id}</td>
                                <td>${device.name || 'Unknown'}</td>
                                <td>
                                    <span class="badge ${device.active ? 'badge-success' : 'badge-secondary'}">
                                        ${device.active ? 'Active' : 'Inactive'}
                                    </span>
                                </td>
                                <td>${this.formatTimestamp(device.last_seen)}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewDevice('${device.id}')">
                                        <i class="ti ti-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    updatePatientsTable() {
        const container = document.getElementById('patients-table-container');
        if (!container) return;
        
        if (!this.patients || this.patients.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-users"></i>
                    <p class="mt-2">No patients found</p>
                </div>
            `;
            return;
        }
        
        const html = `
            <div class="table-responsive">
                <table class="table table-vcenter">
                    <thead>
                        <tr>
                            <th>Patient ID</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Devices</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.patients.map(patient => `
                            <tr>
                                <td>${patient.id}</td>
                                <td>${patient.first_name} ${patient.last_name}</td>
                                <td>
                                    <span class="badge ${patient.active ? 'badge-success' : 'badge-secondary'}">
                                        ${patient.active ? 'Active' : 'Inactive'}
                                    </span>
                                </td>
                                <td>${patient.device_count || 0}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewPatient('${patient.id}')">
                                        <i class="ti ti-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    updateTransactionsData() {
        this.updateTransactionsDisplay(this.transactions);
    }
    
    updateTransactionsDisplay(transactions) {
        const container = document.getElementById('transactions-container');
        if (!container) return;
        
        if (!transactions || transactions.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-activity"></i>
                    <p class="mt-2">No transactions available</p>
                </div>
            `;
            return;
        }
        
        const html = transactions.map(transaction => `
            <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
                <div>
                    <div class="fw-semibold">${transaction.operation}</div>
                    <div class="text-muted small">${transaction.data_type} - ${transaction.collection}</div>
                </div>
                <div class="text-end">
                    <span class="badge ${transaction.status === 'success' ? 'badge-success' : 'badge-danger'}">
                        ${transaction.status}
                    </span>
                    <div class="text-muted small">${this.formatTimestamp(transaction.timestamp)}</div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    // ===== DEVICE STATUS FUNCTIONS =====
    async updateDeviceStatusDisplay() {
        try {
            await Promise.all([
                this.loadDeviceStatusSummary(),
                this.loadDeviceHealthOverview(),
                this.loadDeviceStatusRecent(),
                this.loadDeviceStatusAlerts()
            ]);
        } catch (error) {
            console.error('Error updating device status:', error);
            this.showNotification('Failed to load device status', 'error');
        }
    }
    
    async loadDeviceStatusSummary() {
        try {
            const response = await fetch('/test/device-status/summary');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateDeviceStatusSummary(data.data);
                }
            }
        } catch (error) {
            console.error('Error loading device status summary:', error);
        }
    }
    
    async loadDeviceHealthOverview() {
        try {
            const response = await fetch('/test/device-status/health/overview');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateDeviceHealthOverview(data.data);
                }
            }
        } catch (error) {
            console.error('Error loading device health overview:', error);
        }
    }
    
    async loadDeviceStatusRecent() {
        try {
            const response = await fetch('/test/device-status/recent');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateDeviceStatusTable(data.data.devices || []);
                }
            }
        } catch (error) {
            console.error('Error loading recent device status:', error);
        }
    }
    
    async loadDeviceStatusAlerts() {
        try {
            const response = await fetch('/test/device-status/alerts');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateDeviceStatusAlerts(data.data.alerts || []);
                }
            }
        } catch (error) {
            console.error('Error loading device alerts:', error);
        }
    }
    
    updateDeviceStatusSummary(summary) {
        document.getElementById('total-devices').textContent = summary.total_devices || 0;
        document.getElementById('online-devices').textContent = summary.online_devices || 0;
        document.getElementById('offline-devices').textContent = summary.offline_devices || 0;
        document.getElementById('low-battery-devices').textContent = summary.low_battery_devices || 0;
        document.getElementById('active-alerts').textContent = summary.devices_with_alerts || 0;
        document.getElementById('online-percentage').textContent = `${summary.online_percentage || 0}%`;
    }
    
    updateDeviceHealthOverview(health) {
        document.getElementById('system-health-score').textContent = health.system_health_score || '--';
        document.getElementById('avg-response-time').textContent = health.avg_response_time || '--';
        document.getElementById('data-integrity').textContent = health.data_integrity || '--';
        document.getElementById('uptime-percentage').textContent = health.uptime_percentage || '--';
    }
    
    updateDeviceStatusTable(devices) {
        const tbody = document.getElementById('device-status-table');
        if (!tbody) return;
        
        if (!devices || devices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="13" class="text-center text-muted py-4">
                        <div class="loading-container">
                            <i class="ti ti-devices"></i>
                            <p class="mt-2">No devices found</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        const html = devices.map(device => `
            <tr>
                <td>${device.device_id || 'N/A'}</td>
                <td>
                    <span class="badge device-type-${device.device_type || 'unknown'}">
                        ${this.formatDeviceType(device.device_type)}
                    </span>
                </td>
                <td>${device.imei || 'N/A'}</td>
                <td>${device.mac_address || 'N/A'}</td>
                <td>${device.message_type || 'N/A'}</td>
                <td>
                    <span class="status-indicator ${device.online_status === 'online' ? 'success' : 'danger'}"></span>
                    <span class="badge ${device.online_status === 'online' ? 'badge-success' : 'badge-danger'}">
                        ${device.online_status || 'unknown'}
                    </span>
                </td>
                <td>${this.renderBatteryIndicator(device.battery_level)}</td>
                <td>${this.renderSignalIndicator(device.signal_strength)}</td>
                <td>${this.renderHealthMetrics(device.health_metrics)}</td>
                <td>${this.formatLastReading(device.last_reading)}</td>
                <td>${this.formatTimestamp(device.last_updated)}</td>
                <td>${device.patient_id || 'N/A'}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary" onclick="viewDeviceStatus('${device.device_id}')" title="View Details">
                            <i class="ti ti-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="viewDeviceHistory('${device.device_id}')" title="View History">
                            <i class="ti ti-history"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        tbody.innerHTML = html;
    }
    
    updateDeviceStatusAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        if (!container) return;
        
        if (!alerts || alerts.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-alert-triangle"></i>
                    <p class="mt-2">No active alerts</p>
                </div>
            `;
            return;
        }
        
        const html = alerts.map(alert => `
            <div class="alert alert-${this.getAlertClass(alert.severity)} d-flex align-items-center">
                <i class="ti ti-alert-triangle me-2"></i>
                <div>
                    <strong>${alert.title || 'Alert'}</strong>
                    <div class="small">${alert.message || ''}</div>
                    <div class="text-muted small">${this.formatTimestamp(alert.timestamp)}</div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    // ===== UTILITY FUNCTIONS FOR DEVICE STATUS =====
    formatDeviceType(type) {
        const types = {
            'ava4': 'AVA4',
            'kati': 'Kati Watch',
            'qube-vital': 'Qube-Vital',
            'unknown': 'Unknown'
        };
        return types[type] || type;
    }
    
    renderBatteryIndicator(level) {
        if (level === null || level === undefined) return 'N/A';
        
        let color = 'success';
        if (level < 20) color = 'danger';
        else if (level < 50) color = 'warning';
        
        return `
            <div class="d-flex align-items-center">
                <div class="progress flex-grow-1 me-2" style="height: 6px;">
                    <div class="progress-bar bg-${color}" style="width: ${level}%"></div>
                </div>
                <span class="small">${level}%</span>
            </div>
        `;
    }
    
    renderSignalIndicator(strength) {
        if (strength === null || strength === undefined) return 'N/A';
        
        let color = 'success';
        if (strength < 30) color = 'danger';
        else if (strength < 60) color = 'warning';
        
        return `
            <div class="d-flex align-items-center">
                <div class="progress flex-grow-1 me-2" style="height: 6px;">
                    <div class="progress-bar bg-${color}" style="width: ${strength}%"></div>
                </div>
                <span class="small">${strength}%</span>
            </div>
        `;
    }
    
    renderHealthMetrics(metrics) {
        if (!metrics || Object.keys(metrics).length === 0) return 'N/A';
        
        const html = Object.entries(metrics).map(([key, value]) => {
            let color = 'success';
            if (value < 50) color = 'warning';
            if (value < 20) color = 'danger';
            
            return `
                <div class="d-flex align-items-center">
                    <span class="badge bg-${color} me-1">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                    <span class="small">${value}%</span>
                </div>
            `;
        }).join('');
        
        return html;
    }
    
    formatLastReading(reading) {
        if (!reading) return 'N/A';
        return `${this.formatTimestamp(reading.timestamp)} (${reading.value})`;
    }
    
    // ===== CHART FUNCTIONS =====
    updateDeviceStatusCharts() {
        this.createDeviceActivityChart();
        this.createDevicePerformanceChart();
    }
    
    createDeviceActivityChart() {
        const ctx = document.getElementById('device-activity-chart');
        if (!ctx) return;
        
        // Sample data - replace with real API data
        const data = {
            labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
            datasets: [{
                label: 'AVA4',
                data: [12, 19, 15, 25, 22, 18, 14],
                borderColor: CONFIG.CHART_COLORS.primary,
                backgroundColor: CONFIG.CHART_COLORS.primary + '20',
                tension: 0.4
            }, {
                label: 'Kati Watch',
                data: [8, 12, 10, 18, 15, 12, 9],
                borderColor: CONFIG.CHART_COLORS.secondary,
                backgroundColor: CONFIG.CHART_COLORS.secondary + '20',
                tension: 0.4
            }, {
                label: 'Qube-Vital',
                data: [5, 8, 6, 12, 10, 8, 6],
                borderColor: CONFIG.CHART_COLORS.success,
                backgroundColor: CONFIG.CHART_COLORS.success + '20',
                tension: 0.4
            }]
        };
        
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Device Activity (24h)'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        };
        
        if (this.charts.deviceActivity) {
            this.charts.deviceActivity.destroy();
        }
        
        this.charts.deviceActivity = new Chart(ctx, {
            type: 'line',
            data: data,
            options: options
        });
    }
    
    createDevicePerformanceChart() {
        const ctx = document.getElementById('device-performance-chart');
        if (!ctx) return;
        
        // Sample data - replace with real API data
        const data = {
            labels: ['Online', 'Offline', 'Low Battery', 'Poor Signal'],
            datasets: [{
                data: [65, 15, 12, 8],
                backgroundColor: [
                    CONFIG.CHART_COLORS.success,
                    CONFIG.CHART_COLORS.danger,
                    CONFIG.CHART_COLORS.warning,
                    CONFIG.CHART_COLORS.info
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        };
        
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                title: {
                    display: true,
                    text: 'Device Performance Overview'
                }
            }
        };
        
        if (this.charts.devicePerformance) {
            this.charts.devicePerformance.destroy();
        }
        
        this.charts.devicePerformance = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: options
        });
    }
    
    // ===== ALERT SYSTEM FUNCTIONS =====
    setupAlertConfiguration() {
        const batteryThreshold = document.getElementById('battery-threshold');
        const signalThreshold = document.getElementById('signal-threshold');
        const batteryValue = document.getElementById('battery-threshold-value');
        const signalValue = document.getElementById('signal-threshold-value');
        
        if (batteryThreshold && batteryValue) {
            batteryThreshold.addEventListener('input', (e) => {
                batteryValue.textContent = e.target.value + '%';
            });
        }
        
        if (signalThreshold && signalValue) {
            signalThreshold.addEventListener('input', (e) => {
                signalValue.textContent = e.target.value + '%';
            });
        }
    }
    
    async loadAlertHistory() {
        try {
            const response = await fetch('/api/device-status/alerts/history');
            if (response.ok) {
                const alerts = await response.json();
                this.updateAlertHistoryTable(alerts);
            } else {
                // Fallback to sample data
                this.updateAlertHistoryTable(this.getSampleAlertHistory());
            }
        } catch (error) {
            console.error('Error loading alert history:', error);
            this.updateAlertHistoryTable(this.getSampleAlertHistory());
        }
    }
    
    updateAlertHistoryTable(alerts) {
        const tbody = document.getElementById('alert-history-table');
        if (!tbody) return;
        
        if (!alerts || alerts.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <div class="loading-container">
                            <i class="ti ti-history"></i>
                            <p class="mt-2">No alert history</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        const html = alerts.map(alert => `
            <tr>
                <td>${this.formatTimestamp(alert.timestamp)}</td>
                <td>${alert.device_id || 'N/A'}</td>
                <td>${alert.alert_type || 'Unknown'}</td>
                <td>
                    <span class="badge bg-${this.getAlertClass(alert.severity)}">
                        ${alert.severity || 'info'}
                    </span>
                </td>
                <td>${alert.message || 'N/A'}</td>
                <td>
                    <span class="badge ${alert.resolved ? 'bg-success' : 'bg-warning'}">
                        ${alert.resolved ? 'Resolved' : 'Active'}
                    </span>
                </td>
            </tr>
        `).join('');
        
        tbody.innerHTML = html;
    }
    
    getSampleAlertHistory() {
        return [
            {
                timestamp: new Date(Date.now() - 3600000),
                device_id: 'KATI001',
                alert_type: 'Low Battery',
                severity: 'warning',
                message: 'Battery level below 20%',
                resolved: false
            },
            {
                timestamp: new Date(Date.now() - 7200000),
                device_id: 'AVA4001',
                alert_type: 'Poor Signal',
                severity: 'warning',
                message: 'Signal strength below 30%',
                resolved: true
            },
            {
                timestamp: new Date(Date.now() - 10800000),
                device_id: 'QUBE001',
                alert_type: 'Device Offline',
                severity: 'critical',
                message: 'Device not responding for 10 minutes',
                resolved: true
            }
        ];
    }
    
    getAlertClass(severity) {
        const classes = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'info',
            'success': 'success'
        };
        return classes[severity] || 'info';
    }
    
    // ===== MAPPING DATA FUNCTIONS =====
    async loadRecentMappings() {
        try {
            const response = await fetch('/api/recent-mappings');
            if (response.ok) {
                const result = await response.json();
                console.log('🔍 Recent mappings API response:', result);
                
                if (result.success && result.data) {
                    this.recentMappings = result.data;
                    console.log('✅ Recent mappings loaded:', this.recentMappings);
                    this.updateRecentMappingsDisplay();
                } else {
                    console.log('⚠️ No recent mappings data found');
                    this.recentMappings = [];
                }
            } else {
                console.error('❌ Recent mappings API error:', response.status, response.statusText);
                this.recentMappings = [];
            }
        } catch (error) {
            console.error('Error loading recent mappings:', error);
            this.recentMappings = [];
        }
    }
    
    async loadDeviceMappings() {
        try {
            const response = await fetch('/api/device-mappings');
            if (response.ok) {
                const result = await response.json();
                console.log('🔍 Device mappings API response:', result);
                
                if (result.success && result.data) {
                    this.deviceMappings = result.data;
                    console.log('✅ Device mappings loaded:', this.deviceMappings);
                    this.updateDeviceMappingsDisplay();
                } else {
                    console.log('⚠️ No device mappings data found');
                    this.deviceMappings = { ava4: [], kati: [], qube: [], summary: {} };
                }
            } else {
                console.error('❌ Device mappings API error:', response.status, response.statusText);
                this.deviceMappings = { ava4: [], kati: [], qube: [], summary: {} };
            }
        } catch (error) {
            console.error('Error loading device mappings:', error);
            this.deviceMappings = { ava4: [], kati: [], qube: [], summary: {} };
        }
    }
    
    async loadPatientMappings() {
        try {
            const response = await fetch('/api/patient-mappings');
            if (response.ok) {
                const result = await response.json();
                console.log('🔍 Patient mappings API response:', result);
                
                if (result.success && result.data) {
                    this.patientMappings = result.data;
                    console.log('✅ Patient mappings loaded:', this.patientMappings);
                    this.updatePatientMappingsDisplay();
                } else {
                    console.log('⚠️ No patient mappings data found');
                    this.patientMappings = { patients: [], summary: {} };
                }
            } else {
                console.error('❌ Patient mappings API error:', response.status, response.statusText);
                this.patientMappings = { patients: [], summary: {} };
            }
        } catch (error) {
            console.error('Error loading patient mappings:', error);
            this.patientMappings = { patients: [], summary: {} };
        }
    }
    
    updateRecentMappingsDisplay() {
        const container = document.getElementById('recent-mappings-container');
        if (!container) return;
        
        if (!this.recentMappings || this.recentMappings.length === 0) {
            container.innerHTML = `
                <div class="loading-container">
                    <i class="ti ti-clock"></i>
                    <p class="mt-2">No recent mappings</p>
                </div>
            `;
            return;
        }
        
        const html = this.recentMappings.map(mapping => {
            let icon = 'ti-devices';
            let badgeClass = 'badge-secondary';
            let title = '';
            
            if (mapping.type === 'device_mapping') {
                icon = mapping.device_type === 'AVA4' ? 'ti-devices' : 'ti-watch';
                badgeClass = mapping.mapping_status === 'Mapped' ? 'badge-success' : 'badge-warning';
                title = `${mapping.device_type} ${mapping.mapping_status}`;
            } else if (mapping.type === 'patient_registration') {
                icon = 'ti-user';
                badgeClass = 'badge-info';
                title = `Patient Registration`;
            }
            
            return `
                <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
                    <div class="d-flex align-items-center">
                        <i class="ti ${icon} me-3 text-primary"></i>
                        <div>
                            <div class="fw-semibold">${mapping.patient_name || mapping.device_identifier || 'Unknown'}</div>
                            <div class="text-muted small">
                                ${mapping.device_type || mapping.type.replace('_', ' ').toUpperCase()}
                                ${mapping.device_count ? `(${mapping.device_count} devices)` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="text-end">
                        <span class="badge ${badgeClass}">${mapping.mapping_status || title}</span>
                        <div class="text-muted small mt-1">${this.formatTimestamp(mapping.timestamp)}</div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    }
    
    updateDeviceMappingsDisplay() {
        // Update device mappings summary cards
        if (this.deviceMappings.summary) {
            const summary = this.deviceMappings.summary;
            // Main summary cards
            var el;
            el = document.getElementById('total-devices-mapped'); if (el) el.textContent = summary.total_devices || 0;
            el = document.getElementById('mapped-devices-count'); if (el) el.textContent = summary.mapped_devices || 0;
            el = document.getElementById('unmapped-devices-count'); if (el) el.textContent = summary.unmapped_devices || 0;
            // Device type specific cards
            el = document.getElementById('ava4-devices-count'); if (el) el.textContent = summary.ava4_count || 0;
            el = document.getElementById('kati-devices-count'); if (el) el.textContent = summary.kati_count || 0;
            el = document.getElementById('qube-devices-count'); if (el) el.textContent = summary.qube_count || 0;
            // Calculate mapped counts for each device type
            const ava4Mapped = (this.deviceMappings.ava4 || []).filter(d => d.mapping_status === 'Mapped').length;
            const katiMapped = (this.deviceMappings.kati || []).filter(d => d.mapping_status === 'Mapped').length;
            const qubeMapped = (this.deviceMappings.qube || []).filter(d => d.mapping_status === 'Hospital Device').length;
            el = document.getElementById('ava4-mapped-count'); if (el) el.textContent = ava4Mapped;
            el = document.getElementById('kati-mapped-count'); if (el) el.textContent = katiMapped;
            el = document.getElementById('qube-mapped-count'); if (el) el.textContent = qubeMapped;
            // Update progress bars
            const totalMappingProgress = summary.total_devices > 0 ? (summary.mapped_devices / summary.total_devices) * 100 : 0;
            const ava4Progress = summary.ava4_count > 0 ? (ava4Mapped / summary.ava4_count) * 100 : 0;
            const katiProgress = summary.kati_count > 0 ? (katiMapped / summary.kati_count) * 100 : 0;
            const qubeProgress = summary.qube_count > 0 ? (qubeMapped / summary.qube_count) * 100 : 0;
            el = document.getElementById('mapping-progress'); if (el) el.style.width = `${totalMappingProgress}%`;
            el = document.getElementById('ava4-mapping-progress'); if (el) el.style.width = `${ava4Progress}%`;
            el = document.getElementById('kati-mapping-progress'); if (el) el.style.width = `${katiProgress}%`;
            el = document.getElementById('qube-mapping-progress'); if (el) el.style.width = `${qubeProgress}%`;
        }
        // Update device mappings table
        this.updateDeviceMappingsTable();
    }
    
    updateDeviceMappingsTable() {
        const container = document.getElementById('device-mappings-table');
        if (!container) return;
        
        const allDevices = [
            ...(this.deviceMappings.ava4 || []),
            ...(this.deviceMappings.kati || []),
            ...(this.deviceMappings.qube || [])
        ];
        
        if (!allDevices || allDevices.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                        <div class="loading-container">
                            <i class="ti ti-devices"></i>
                            <p class="mt-2">No device mappings found</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        const html = allDevices.map(device => `
            <tr>
                <td>${device.device_id || 'N/A'}</td>
                <td>
                    <span class="badge device-type-${device.device_type.toLowerCase().replace(' ', '-')}">
                        ${device.device_type}
                    </span>
                </td>
                <td>${device.mac_address || device.imei || 'N/A'}</td>
                <td>${device.name || 'N/A'}</td>
                <td>
                    ${device.patient_info ? `
                        <div>
                            <div class="fw-semibold">${device.patient_info.patient_name}</div>
                            <div class="text-muted small">ID: ${device.patient_info.patient_id}</div>
                        </div>
                    ` : 'N/A'}
                </td>
                <td>
                    <span class="badge ${device.mapping_status === 'Mapped' ? 'badge-success' : 'badge-warning'}">
                        ${device.mapping_status}
                    </span>
                </td>
                <td>${this.formatTimestamp(device.updated_at)}</td>
            </tr>
        `).join('');
        
        container.innerHTML = html;
    }
    
    updatePatientMappingsDisplay() {
        // Update patient mappings summary cards
        if (this.patientMappings.summary) {
            const summary = this.patientMappings.summary;
            var el;
            // Main summary cards
            el = document.getElementById('total-patients-mapped'); if (el) el.textContent = summary.total_patients || 0;
            el = document.getElementById('patients-with-devices'); if (el) el.textContent = summary.patients_with_devices || 0;
            el = document.getElementById('patients-without-devices'); if (el) el.textContent = summary.patients_without_devices || 0;
            el = document.getElementById('total-device-mappings'); if (el) el.textContent = summary.total_device_mappings || 0;
            // Calculate device type specific mappings
            const patients = this.patientMappings.patients || [];
            const ava4Mappings = patients.filter(p => p.devices.ava4).length;
            const katiMappings = patients.filter(p => p.devices.kati).length;
            const completeMappings = patients.filter(p => p.mapping_summary.mapped_devices === p.mapping_summary.total_devices).length;
            el = document.getElementById('ava4-patient-mappings'); if (el) el.textContent = ava4Mappings;
            el = document.getElementById('kati-patient-mappings'); if (el) el.textContent = katiMappings;
            el = document.getElementById('complete-mappings'); if (el) el.textContent = completeMappings;
            // Calculate active patients (with Active registration status)
            const activePatients = patients.filter(p => p.registration_status === 'Active');
            const ava4Active = activePatients.filter(p => p.devices.ava4).length;
            const katiActive = activePatients.filter(p => p.devices.kati).length;
            el = document.getElementById('ava4-active-patients'); if (el) el.textContent = ava4Active;
            el = document.getElementById('kati-active-patients'); if (el) el.textContent = katiActive;
            // Update progress bars
            const patientMappingProgress = summary.total_patients > 0 ? (summary.patients_with_devices / summary.total_patients) * 100 : 0;
            const ava4Progress = summary.total_patients > 0 ? (ava4Mappings / summary.total_patients) * 100 : 0;
            const katiProgress = summary.total_patients > 0 ? (katiMappings / summary.total_patients) * 100 : 0;
            const completeProgress = summary.total_patients > 0 ? (completeMappings / summary.total_patients) * 100 : 0;
            el = document.getElementById('patient-mapping-progress'); if (el) el.style.width = `${patientMappingProgress}%`;
            el = document.getElementById('ava4-patient-progress'); if (el) el.style.width = `${ava4Progress}%`;
            el = document.getElementById('kati-patient-progress'); if (el) el.style.width = `${katiProgress}%`;
            el = document.getElementById('complete-mapping-progress'); if (el) el.style.width = `${completeProgress}%`;
        }
        // Update patient mappings table
        this.updatePatientMappingsTable();
    }
    
    updatePatientMappingsTable() {
        const container = document.getElementById('patient-mappings-table');
        if (!container) return;
        
        const patients = this.patientMappings.patients || [];
        
        if (!patients || patients.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <div class="loading-container">
                            <i class="ti ti-users"></i>
                            <p class="mt-2">No patient mappings found</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        const html = patients.map(patient => `
            <tr>
                <td>${patient.patient_id || 'N/A'}</td>
                <td>${patient.patient_name || 'N/A'}</td>
                <td>
                    <span class="badge ${patient.registration_status === 'Active' ? 'badge-success' : 'badge-secondary'}">
                        ${patient.registration_status}
                    </span>
                </td>
                <td>
                    <div class="d-flex flex-column gap-1">
                        ${patient.devices.ava4 ? `
                            <span class="badge badge-sm badge-primary">AVA4: ${patient.devices.ava4.mac_address}</span>
                        ` : '<span class="badge badge-sm badge-secondary">No AVA4</span>'}
                        ${patient.devices.kati ? `
                            <span class="badge badge-sm badge-info">Kati: ${patient.devices.kati.imei}</span>
                        ` : '<span class="badge badge-sm badge-secondary">No Kati</span>'}
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress flex-grow-1 me-2" style="height: 6px;">
                            <div class="progress-bar bg-success" style="width: ${(patient.mapping_summary.mapped_devices / patient.mapping_summary.total_devices) * 100}%"></div>
                        </div>
                        <span class="small">${patient.mapping_summary.mapped_devices}/${patient.mapping_summary.total_devices}</span>
                    </div>
                </td>
                <td>${this.formatTimestamp(patient.updated_at)}</td>
            </tr>
        `).join('');
        
        container.innerHTML = html;
    }
    
    // ===== PUBLIC METHODS =====
    refreshData() {
        console.log('🔄 Refreshing data...');
        this.showNotification('Refreshing data...', 'info');
        
        switch (this.currentTab) {
            case 'dashboard':
                this.loadStatistics();
                break;
            case 'messages':
                this.updateMessagesTable();
                break;
            case 'devices':
                this.updateDevicesTables();
                break;
            case 'patients':
                this.updatePatientsTable();
                break;
            case 'transactions':
                this.updateTransactionsData();
                break;
            case 'device-status':
                this.updateDeviceStatusDisplay();
                break;
        }
    }
}

// ===== GLOBAL FUNCTIONS =====
let app;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    app = new OperaGodEyeApp();
});

// Global functions for HTML onclick handlers
function refreshData() {
    if (app) app.refreshData();
}

function clearMessages() {
    if (app) {
        app.messages = [];
        app.updateMessagesTable();
        app.showNotification('Messages cleared', 'success');
    }
}

function clearTransactions() {
    if (app) {
        app.transactions = [];
        app.updateTransactionsData();
        app.showNotification('Transactions cleared', 'success');
    }
}

function refreshDeviceStatus() {
    if (app) {
        app.updateDeviceStatusDisplay();
        app.showNotification('Device status refreshed', 'success');
    }
}

function exportDeviceStatus() {
    if (app) {
        // Create CSV export
        const csv = [
            ['Device ID', 'Type', 'Status', 'Battery', 'Signal', 'Last Updated', 'Patient ID'].join(','),
            // Add device data here
        ].join('\n');
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `device-status-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        app.showNotification('Device status exported', 'success');
    }
}

function clearDeviceFilters() {
    document.getElementById('device-type-filter').value = '';
    document.getElementById('status-filter').value = '';
    document.getElementById('search-input').value = '';
    
    if (app) {
        app.showNotification('Filters cleared', 'success');
    }
}

function viewDevice(deviceId) {
    if (app) {
        app.showNotification(`Viewing device: ${deviceId}`, 'info');
        // Implement device detail view
    }
}

function viewPatient(patientId) {
    if (app) {
        app.showNotification(`Viewing patient: ${patientId}`, 'info');
        // Implement patient detail view
    }
}

function viewDeviceStatus(deviceId) {
    if (app) {
        app.showNotification(`Viewing device status: ${deviceId}`, 'info');
        // Implement device status detail view
    }
}

function refreshRecentMappings() {
    if (app) {
        app.loadRecentMappings();
        app.showNotification('Recent mappings refreshed', 'success');
    }
}

function refreshDeviceMappings() {
    if (app) {
        app.loadDeviceMappings();
        app.showNotification('Device mappings refreshed', 'success');
    }
}

function refreshPatientMappings() {
    if (app) {
        app.loadPatientMappings();
        app.showNotification('Patient mappings refreshed', 'success');
    }
}

// ===== CSS ANIMATIONS =====
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-in-out;
    }
    
    .slide-in-right {
        animation: slideInRight 0.5s ease-out;
    }
`;
document.head.appendChild(style);