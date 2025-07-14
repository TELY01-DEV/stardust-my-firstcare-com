/**
 * Device Status Dashboard JavaScript
 * Real-time device monitoring and management
 */

class DeviceStatusDashboard {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5054/api';
        this.websocketUrl = 'ws://localhost:5054/ws';
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.data = {
            devices: [],
            alerts: [],
            summary: {}
        };
        this.filters = {
            deviceType: '',
            status: '',
            search: '',
            alertSeverity: ''
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.connectWebSocket();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    bindEvents() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshData();
        });

        // Filters
        document.getElementById('deviceTypeFilter').addEventListener('change', (e) => {
            this.filters.deviceType = e.target.value;
            this.applyFilters();
        });

        document.getElementById('statusFilter').addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.applyFilters();
        });

        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.applyFilters();
        });

        document.getElementById('alertSeverityFilter').addEventListener('change', (e) => {
            this.filters.alertSeverity = e.target.value;
            this.applyFilters();
        });

        // Clear filters
        document.getElementById('clearFiltersBtn').addEventListener('click', () => {
            this.clearFilters();
        });

        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportData();
        });
    }

    async loadInitialData() {
        this.showLoading(true);
        
        try {
            await Promise.all([
                this.loadSummary(),
                this.loadDevices(),
                this.loadAlerts()
            ]);
            
            this.updateUI();
            this.showNotification('Data loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Failed to load data', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async loadSummary() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/devices/status/summary`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            if (data.success) {
                this.data.summary = data.data;
            } else {
                throw new Error(data.errors?.[0]?.message || 'Failed to load summary');
            }
        } catch (error) {
            console.error('Error loading summary:', error);
            throw error;
        }
    }

    async loadDevices() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/devices/status/recent`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            if (data.success) {
                this.data.devices = data.data || [];
            } else {
                throw new Error(data.errors?.[0]?.message || 'Failed to load devices');
            }
        } catch (error) {
            console.error('Error loading devices:', error);
            throw error;
        }
    }

    async loadAlerts() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/devices/status/alerts`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            if (data.success) {
                this.data.alerts = data.data || [];
            } else {
                throw new Error(data.errors?.[0]?.message || 'Failed to load alerts');
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
            throw error;
        }
    }

    connectWebSocket() {
        try {
            this.websocket = new WebSocket(this.websocketUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
                
                // Subscribe to device status updates
                this.websocket.send(JSON.stringify({
                    type: 'subscribe',
                    channel: 'device_status'
                }));
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.scheduleReconnect();
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'device_status_update':
                this.handleDeviceUpdate(data.device);
                break;
            case 'alert_update':
                this.handleAlertUpdate(data.alert);
                break;
            case 'summary_update':
                this.handleSummaryUpdate(data.summary);
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    handleDeviceUpdate(device) {
        const index = this.data.devices.findIndex(d => d.device_id === device.device_id);
        if (index !== -1) {
            this.data.devices[index] = { ...this.data.devices[index], ...device };
        } else {
            this.data.devices.unshift(device);
        }
        this.updateDeviceTable();
        this.updateSummary();
    }

    handleAlertUpdate(alert) {
        const index = this.data.alerts.findIndex(a => a.id === alert.id);
        if (index !== -1) {
            this.data.alerts[index] = alert;
        } else {
            this.data.alerts.unshift(alert);
        }
        this.updateAlerts();
        this.updateSummary();
    }

    handleSummaryUpdate(summary) {
        this.data.summary = { ...this.data.summary, ...summary };
        this.updateSummary();
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connectWebSocket();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            this.showNotification('WebSocket connection failed. Please refresh the page.', 'error');
        }
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connectionStatus');
        const text = document.getElementById('connectionText');
        
        if (connected) {
            indicator.className = 'status-indicator connected';
            text.textContent = 'Connected';
        } else {
            indicator.className = 'status-indicator disconnected';
            text.textContent = 'Disconnected';
        }
    }

    updateUI() {
        this.updateSummary();
        this.updateDeviceBreakdown();
        this.updateDeviceTable();
        this.updateAlerts();
    }

    updateSummary() {
        const summary = this.data.summary;
        
        document.getElementById('totalDevices').textContent = summary.total_devices || 0;
        document.getElementById('onlineDevices').textContent = summary.online_devices || 0;
        document.getElementById('offlineDevices').textContent = summary.offline_devices || 0;
        document.getElementById('lowBatteryDevices').textContent = summary.low_battery_devices || 0;
        document.getElementById('activeAlerts').textContent = summary.active_alerts || 0;
        
        const onlinePercentage = summary.total_devices > 0 
            ? Math.round((summary.online_devices / summary.total_devices) * 100) 
            : 0;
        document.getElementById('onlinePercentage').textContent = `${onlinePercentage}%`;
    }

    updateDeviceBreakdown() {
        const breakdown = this.data.summary.device_breakdown || {};
        const container = document.getElementById('deviceBreakdown');
        
        container.innerHTML = '';
        
        Object.entries(breakdown).forEach(([type, data]) => {
            const card = document.createElement('div');
            card.className = 'breakdown-card';
            card.innerHTML = `
                <div class="breakdown-info">
                    <h4>${this.formatDeviceType(type)}</h4>
                </div>
                <div class="breakdown-stats">
                    <div class="total">${data.total || 0}</div>
                    <div class="online">${data.online || 0} online</div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    updateDeviceTable() {
        const tbody = document.getElementById('deviceTableBody');
        const filteredDevices = this.getFilteredDevices();
        
        tbody.innerHTML = '';
        
        filteredDevices.forEach(device => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${device.device_id}</strong></td>
                <td>${this.formatDeviceType(device.device_type)}</td>
                <td><span class="status-badge ${device.status}">${device.status}</span></td>
                <td>${this.renderBatteryIndicator(device.battery_level)}</td>
                <td>${this.renderSignalIndicator(device.signal_strength)}</td>
                <td>${this.formatTimestamp(device.last_updated)}</td>
                <td>${device.patient_id || 'N/A'}</td>
                <td>
                    <button class="action-btn" onclick="dashboard.viewDevice('${device.device_id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn" onclick="dashboard.refreshDevice('${device.device_id}')">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        document.getElementById('deviceCount').textContent = `${filteredDevices.length} devices`;
    }

    updateAlerts() {
        const container = document.getElementById('alertsContainer');
        const filteredAlerts = this.getFilteredAlerts();
        
        container.innerHTML = '';
        
        if (filteredAlerts.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;">No alerts found</p>';
            return;
        }
        
        filteredAlerts.forEach(alert => {
            const alertElement = document.createElement('div');
            alertElement.className = `alert-item ${alert.severity}`;
            alertElement.innerHTML = `
                <div class="alert-header">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-time">${this.formatTimestamp(alert.timestamp)}</div>
                </div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-meta">
                    <span>Device: ${alert.device_id}</span>
                    <span>Type: ${this.formatDeviceType(alert.device_type)}</span>
                    <span>Severity: ${alert.severity}</span>
                </div>
            `;
            container.appendChild(alertElement);
        });
    }

    getFilteredDevices() {
        let devices = [...this.data.devices];
        
        if (this.filters.deviceType) {
            devices = devices.filter(d => d.device_type === this.filters.deviceType);
        }
        
        if (this.filters.status) {
            devices = devices.filter(d => d.status === this.filters.status);
        }
        
        if (this.filters.search) {
            const search = this.filters.search.toLowerCase();
            devices = devices.filter(d => 
                d.device_id.toLowerCase().includes(search) ||
                (d.patient_id && d.patient_id.toLowerCase().includes(search))
            );
        }
        
        return devices;
    }

    getFilteredAlerts() {
        let alerts = [...this.data.alerts];
        
        if (this.filters.alertSeverity) {
            alerts = alerts.filter(a => a.severity === this.filters.alertSeverity);
        }
        
        return alerts;
    }

    applyFilters() {
        this.updateDeviceTable();
        this.updateAlerts();
    }

    clearFilters() {
        this.filters = {
            deviceType: '',
            status: '',
            search: '',
            alertSeverity: ''
        };
        
        document.getElementById('deviceTypeFilter').value = '';
        document.getElementById('statusFilter').value = '';
        document.getElementById('searchInput').value = '';
        document.getElementById('alertSeverityFilter').value = '';
        
        this.applyFilters();
    }

    async refreshData() {
        this.showLoading(true);
        
        try {
            await Promise.all([
                this.loadSummary(),
                this.loadDevices(),
                this.loadAlerts()
            ]);
            
            this.updateUI();
            this.showNotification('Data refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Failed to refresh data', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async viewDevice(deviceId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/devices/status/${deviceId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            if (data.success) {
                this.showDeviceDetails(data.data);
            } else {
                throw new Error(data.errors?.[0]?.message || 'Failed to load device details');
            }
        } catch (error) {
            console.error('Error loading device details:', error);
            this.showNotification('Failed to load device details', 'error');
        }
    }

    async refreshDevice(deviceId) {
        try {
            // This would typically trigger a device refresh command
            this.showNotification(`Refreshing device ${deviceId}...`, 'info');
            
            // Simulate refresh by reloading device data
            await this.loadDevices();
            this.updateDeviceTable();
            
            this.showNotification(`Device ${deviceId} refreshed`, 'success');
        } catch (error) {
            console.error('Error refreshing device:', error);
            this.showNotification('Failed to refresh device', 'error');
        }
    }

    showDeviceDetails(device) {
        // Create a modal or expandable section to show device details
        const details = `
Device ID: ${device.device_id}
Type: ${this.formatDeviceType(device.device_type)}
Status: ${device.status}
Battery: ${device.battery_level}%
Signal: ${device.signal_strength}
Last Updated: ${this.formatTimestamp(device.last_updated)}
Patient ID: ${device.patient_id || 'N/A'}
        `;
        
        alert(details); // Replace with proper modal implementation
    }

    exportData() {
        const data = {
            summary: this.data.summary,
            devices: this.getFilteredDevices(),
            alerts: this.getFilteredAlerts(),
            exportTime: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `device-status-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Data exported successfully', 'success');
    }

    startAutoRefresh() {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.refreshData();
        }, 30000);
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    }

    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; cursor: pointer; color: #64748b;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        notifications.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    // Utility functions
    formatDeviceType(type) {
        const types = {
            'kati': 'Kati Watch',
            'ava4': 'AVA4',
            'qube-vital': 'Qube-Vital'
        };
        return types[type] || type;
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        
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

    renderBatteryIndicator(level) {
        if (level === null || level === undefined) return 'N/A';
        
        let className = 'high';
        if (level <= 20) className = 'low';
        else if (level <= 50) className = 'medium';
        
        const width = Math.max(0, Math.min(100, level));
        
        return `
            <div class="battery-indicator">
                <div class="battery-bar">
                    <div class="battery-fill ${className}" style="width: ${width}%"></div>
                </div>
                <span>${level}%</span>
            </div>
        `;
    }

    renderSignalIndicator(strength) {
        if (strength === null || strength === undefined) return 'N/A';
        
        const bars = Math.ceil((strength / 100) * 4);
        const barsHtml = Array.from({ length: 4 }, (_, i) => 
            `<div class="signal-bar ${i < bars ? 'active' : ''}" style="height: ${(i + 1) * 4}px;"></div>`
        ).join('');
        
        return `
            <div class="signal-indicator">
                ${barsHtml}
                <span style="margin-left: 4px; font-size: 0.75rem;">${strength}%</span>
            </div>
        `;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DeviceStatusDashboard();
}); 