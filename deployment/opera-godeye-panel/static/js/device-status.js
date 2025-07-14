// Device Status Dashboard JavaScript
// Enhanced with real-time updates, better status detection, and improved UI

class DeviceStatusDashboard {
    constructor() {
        this.currentData = null;
        this.updateInterval = null;
        this.websocket = null;
        this.isConnected = false;
        this.retryCount = 0;
        this.maxRetries = 5;
        
        this.init();
    }
    
    init() {
        console.log('🚀 Initializing Enhanced Device Status Dashboard');
        this.setupEventListeners();
        this.loadInitialData();
        this.setupWebSocket();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-device-status');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
        
        // Filter controls
        const deviceTypeFilter = document.getElementById('device-type-filter');
        if (deviceTypeFilter) {
            deviceTypeFilter.addEventListener('change', () => this.applyFilters());
        }
        
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }
        
        // Search functionality
        const searchInput = document.getElementById('device-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
        }
        
        // Export functionality
        const exportBtn = document.getElementById('export-device-data');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportData());
        }
        
        // Health overview tab
        const healthTab = document.getElementById('health-overview-tab');
        if (healthTab) {
            healthTab.addEventListener('click', () => this.showHealthOverview());
        }
    }
    
    async loadInitialData() {
        try {
            this.showLoading(true);
            
            // Load summary data
            const summaryResponse = await this.fetchDeviceStatusSummary();
            if (summaryResponse.success) {
                this.updateSummaryCards(summaryResponse.data);
            }
            
            // Load recent devices
            const recentResponse = await this.fetchRecentDevices();
            if (recentResponse.success) {
                this.updateDeviceTable(recentResponse.data.devices);
            }
            
            // Load health overview
            const healthResponse = await this.fetchHealthOverview();
            if (healthResponse.success) {
                this.updateHealthMetrics(healthResponse.data);
            }
            
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            this.showError('Failed to load device status data');
        } finally {
            this.showLoading(false);
        }
    }
    
    async fetchDeviceStatusSummary() {
        const response = await fetch('/api/devices/status/summary', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return await response.json();
    }
    
    async fetchRecentDevices(deviceType = null, statusFilter = null) {
        let url = '/api/devices/status/recent?limit=100';
        if (deviceType) url += `&device_type=${deviceType}`;
        if (statusFilter) url += `&status_filter=${statusFilter}`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return await response.json();
    }
    
    async fetchHealthOverview() {
        const response = await fetch('/api/devices/status/health/overview', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return await response.json();
    }
    
    updateSummaryCards(summary) {
        // Update summary cards
        this.updateCard('total-devices', summary.total_devices);
        this.updateCard('online-devices', summary.online_devices, 'success');
        this.updateCard('offline-devices', summary.offline_devices, 'warning');
        this.updateCard('unknown-devices', summary.unknown_devices, 'info');
        this.updateCard('low-battery-devices', summary.low_battery_devices, 'danger');
        this.updateCard('devices-with-alerts', summary.devices_with_alerts, 'danger');
        this.updateCard('stale-devices', summary.stale_devices, 'warning');
        this.updateCard('online-percentage', `${summary.online_percentage}%`, 'success');
        
        // Update device type breakdown
        this.updateDeviceTypeBreakdown(summary.by_type);
        
        // Update last updated timestamp
        const lastUpdated = document.getElementById('last-updated');
        if (lastUpdated && summary.last_updated) {
            lastUpdated.textContent = new Date(summary.last_updated).toLocaleString();
        }
    }
    
    updateCard(elementId, value, status = 'primary') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            
            // Update card styling based on status
            const card = element.closest('.card');
            if (card) {
                card.className = `card border-${status}`;
            }
        }
    }
    
    updateDeviceTypeBreakdown(typeStats) {
        const container = document.getElementById('device-type-breakdown');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(typeStats).forEach(([type, stats]) => {
            const typeCard = document.createElement('div');
            typeCard.className = 'col-md-3 mb-3';
            typeCard.innerHTML = `
                <div class="card border-primary">
                    <div class="card-body text-center">
                        <h6 class="card-title text-capitalize">${type}</h6>
                        <div class="row">
                            <div class="col-4">
                                <small class="text-muted">Total</small>
                                <div class="h5 mb-0">${stats.total}</div>
                            </div>
                            <div class="col-4">
                                <small class="text-success">Online</small>
                                <div class="h5 mb-0 text-success">${stats.online}</div>
                            </div>
                            <div class="col-4">
                                <small class="text-warning">Offline</small>
                                <div class="h5 mb-0 text-warning">${stats.offline}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(typeCard);
        });
    }
    
    updateDeviceTable(devices) {
        const tbody = document.getElementById('device-status-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        devices.forEach(device => {
            const row = this.createDeviceRow(device);
            tbody.appendChild(row);
        });
        
        // Update device count
        const deviceCount = document.getElementById('device-count');
        if (deviceCount) {
            deviceCount.textContent = devices.length;
        }
    }
    
    createDeviceRow(device) {
        const row = document.createElement('tr');
        const statusClass = this.getStatusClass(device.online_status);
        const batteryClass = this.getBatteryClass(device.battery_level);
        const signalClass = this.getSignalClass(device.signal_strength);
        
        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="status-indicator ${statusClass} me-2"></div>
                    <div>
                        <div class="fw-bold">${device.device_id || 'N/A'}</div>
                        <small class="text-muted">${device.device_type || 'Unknown'}</small>
                    </div>
                </div>
            </td>
            <td>
                <span class="badge bg-${statusClass}">${device.online_status}</span>
            </td>
            <td>
                ${device.battery_level !== null ? 
                    `<span class="badge bg-${batteryClass}">${device.battery_level}%</span>` : 
                    '<span class="text-muted">N/A</span>'
                }
            </td>
            <td>
                ${device.signal_strength !== null ? 
                    `<span class="badge bg-${signalClass}">${device.signal_strength} dBm</span>` : 
                    '<span class="text-muted">N/A</span>'
                }
            </td>
            <td>
                ${device.last_updated ? 
                    new Date(device.last_updated).toLocaleString() : 
                    '<span class="text-muted">Never</span>'
                }
            </td>
            <td>
                ${device.alerts && device.alerts.length > 0 ? 
                    `<span class="badge bg-danger">${device.alerts.length} alerts</span>` : 
                    '<span class="text-muted">None</span>'
                }
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="deviceDashboard.showDeviceDetails('${device.device_id}')">
                    Details
                </button>
            </td>
        `;
        
        return row;
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'online': return 'success';
            case 'offline': return 'warning';
            case 'unknown': return 'secondary';
            default: return 'secondary';
        }
    }
    
    getBatteryClass(level) {
        if (level === null) return 'secondary';
        if (level < 20) return 'danger';
        if (level < 50) return 'warning';
        return 'success';
    }
    
    getSignalClass(strength) {
        if (strength === null) return 'secondary';
        if (strength < 30) return 'danger';
        if (strength < 60) return 'warning';
        return 'success';
    }
    
    updateHealthMetrics(health) {
        // Update health overview charts
        this.updateHealthChart('status-chart', health.status_breakdown);
        this.updateHealthChart('battery-chart', health.battery_health);
        this.updateHealthChart('signal-chart', health.signal_health);
        
        // Update activity metrics
        this.updateActivityMetrics(health.recent_activity);
        
        // Update alerts summary
        this.updateAlertsSummary(health.alerts_summary);
    }
    
    updateHealthChart(chartId, data) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(data),
                datasets: [{
                    data: Object.values(data),
                    backgroundColor: [
                        '#28a745', // success
                        '#ffc107', // warning
                        '#dc3545', // danger
                        '#6c757d'  // secondary
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    updateActivityMetrics(activity) {
        const container = document.getElementById('activity-metrics');
        if (!container) return;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="card border-success">
                        <div class="card-body text-center">
                            <h5 class="text-success">${activity.last_hour}</h5>
                            <small>Last Hour</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-primary">
                        <div class="card-body text-center">
                            <h5 class="text-primary">${activity.last_24h}</h5>
                            <small>Last 24 Hours</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-info">
                        <div class="card-body text-center">
                            <h5 class="text-info">${activity.last_week}</h5>
                            <small>Last Week</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateAlertsSummary(alerts) {
        const container = document.getElementById('alerts-summary');
        if (!container) return;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="alert alert-danger">
                        <h6>Critical Alerts</h6>
                        <h4>${alerts.critical}</h4>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="alert alert-warning">
                        <h6>Warning Alerts</h6>
                        <h4>${alerts.warning}</h4>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="alert alert-info">
                        <h6>Info Alerts</h6>
                        <h4>${alerts.info}</h4>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/realtime/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected');
                this.isConnected = true;
                this.retryCount = 0;
                
                // Subscribe to device status updates
                this.websocket.send(JSON.stringify({
                    type: 'subscribe',
                    room: 'device_status_updates'
                }));
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('❌ Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('❌ WebSocket disconnected');
                this.isConnected = false;
                this.scheduleReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.isConnected = false;
            };
            
        } catch (error) {
            console.error('❌ Failed to setup WebSocket:', error);
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'device_status_update':
                this.handleDeviceStatusUpdate(data.data);
                break;
            case 'device_alert':
                this.handleDeviceAlert(data.data);
                break;
            case 'system_alert':
                this.handleSystemAlert(data.data);
                break;
            default:
                console.log('📨 Unknown WebSocket message type:', data.type);
        }
    }
    
    handleDeviceStatusUpdate(deviceData) {
        // Update device in table if it exists
        const row = document.querySelector(`[data-device-id="${deviceData.device_id}"]`);
        if (row) {
            // Update the row with new data
            this.updateDeviceRow(deviceData);
        } else {
            // Add new device to table
            this.addDeviceToTable(deviceData);
        }
        
        // Update summary if needed
        this.refreshSummary();
    }
    
    handleDeviceAlert(alertData) {
        // Show alert notification
        this.showAlertNotification(alertData);
        
        // Update alerts count
        this.updateAlertsCount();
    }
    
    handleSystemAlert(alertData) {
        // Show system alert
        this.showSystemAlert(alertData);
    }
    
    showAlertNotification(alert) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${alert.severity} alert-dismissible fade show`;
        notification.innerHTML = `
            <strong>${alert.alert_type}</strong> - ${alert.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.getElementById('notifications-container');
        if (container) {
            container.appendChild(notification);
            
            // Auto-remove after 10 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 10000);
        }
    }
    
    scheduleReconnect() {
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
            
            console.log(`🔄 Scheduling WebSocket reconnect in ${delay}ms (attempt ${this.retryCount})`);
            
            setTimeout(() => {
                this.setupWebSocket();
            }, delay);
        } else {
            console.error('❌ Max WebSocket reconnection attempts reached');
        }
    }
    
    startAutoRefresh() {
        // Refresh data every 30 seconds
        this.updateInterval = setInterval(() => {
            this.refreshData();
        }, 30000);
    }
    
    async refreshData() {
        try {
            await this.loadInitialData();
            console.log('✅ Device status data refreshed');
        } catch (error) {
            console.error('❌ Failed to refresh data:', error);
        }
    }
    
    applyFilters() {
        const deviceType = document.getElementById('device-type-filter')?.value;
        const statusFilter = document.getElementById('status-filter')?.value;
        
        this.loadFilteredData(deviceType, statusFilter);
    }
    
    async loadFilteredData(deviceType, statusFilter) {
        try {
            this.showLoading(true);
            
            const response = await this.fetchRecentDevices(deviceType, statusFilter);
            if (response.success) {
                this.updateDeviceTable(response.data.devices);
            }
            
        } catch (error) {
            console.error('❌ Failed to load filtered data:', error);
            this.showError('Failed to load filtered data');
        } finally {
            this.showLoading(false);
        }
    }
    
    handleSearch(query) {
        const rows = document.querySelectorAll('#device-status-table-body tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const matches = text.includes(query.toLowerCase());
            row.style.display = matches ? '' : 'none';
        });
    }
    
    async showDeviceDetails(deviceId) {
        try {
            const response = await fetch(`/api/devices/status/${deviceId}`, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            const data = await response.json();
            if (data.success) {
                this.showDeviceDetailsModal(data.data);
            }
        } catch (error) {
            console.error('❌ Failed to load device details:', error);
        }
    }
    
    showDeviceDetailsModal(device) {
        const modal = document.getElementById('device-details-modal');
        if (!modal) return;
        
        // Populate modal with device details
        document.getElementById('device-details-id').textContent = device.device_id;
        document.getElementById('device-details-type').textContent = device.device_type;
        document.getElementById('device-details-status').textContent = device.online_status;
        document.getElementById('device-details-battery').textContent = device.battery_level || 'N/A';
        document.getElementById('device-details-signal').textContent = device.signal_strength || 'N/A';
        document.getElementById('device-details-last-updated').textContent = 
            device.last_updated ? new Date(device.last_updated).toLocaleString() : 'Never';
        
        // Show alerts
        const alertsContainer = document.getElementById('device-details-alerts');
        if (device.alerts && device.alerts.length > 0) {
            alertsContainer.innerHTML = device.alerts.map(alert => `
                <div class="alert alert-${alert.severity}">
                    <strong>${alert.alert_type}</strong>: ${alert.message}
                </div>
            `).join('');
        } else {
            alertsContainer.innerHTML = '<p class="text-muted">No alerts</p>';
        }
        
        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
    
    async showHealthOverview() {
        try {
            this.showLoading(true);
            
            const response = await this.fetchHealthOverview();
            if (response.success) {
                this.updateHealthMetrics(response.data);
                this.showHealthOverviewTab();
            }
            
        } catch (error) {
            console.error('❌ Failed to load health overview:', error);
            this.showError('Failed to load health overview');
        } finally {
            this.showLoading(false);
        }
    }
    
    showHealthOverviewTab() {
        // Switch to health overview tab
        const healthTab = document.getElementById('health-overview-tab');
        const healthContent = document.getElementById('health-overview-content');
        
        if (healthTab && healthContent) {
            // Remove active class from all tabs
            document.querySelectorAll('.nav-link').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            // Add active class to health tab
            healthTab.classList.add('active');
            healthContent.classList.add('active');
        }
    }
    
    exportData() {
        // Export device data as CSV
        const devices = this.currentData?.devices || [];
        
        if (devices.length === 0) {
            this.showError('No data to export');
            return;
        }
        
        const csv = this.convertToCSV(devices);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `device-status-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        
        window.URL.revokeObjectURL(url);
    }
    
    convertToCSV(data) {
        const headers = ['Device ID', 'Device Type', 'Status', 'Battery', 'Signal', 'Last Updated', 'Alerts'];
        const rows = data.map(device => [
            device.device_id,
            device.device_type,
            device.online_status,
            device.battery_level || 'N/A',
            device.signal_strength || 'N/A',
            device.last_updated ? new Date(device.last_updated).toLocaleString() : 'Never',
            device.alerts ? device.alerts.length : 0
        ]);
        
        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }
    
    showLoading(show) {
        const loadingElement = document.getElementById('loading-indicator');
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
    }
    
    showError(message) {
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
        }
    }
    
    getAuthToken() {
        // Get auth token from localStorage or other storage
        return localStorage.getItem('auth_token') || '';
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.websocket) {
            this.websocket.close();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.deviceDashboard = new DeviceStatusDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.deviceDashboard) {
        window.deviceDashboard.destroy();
    }
}); 