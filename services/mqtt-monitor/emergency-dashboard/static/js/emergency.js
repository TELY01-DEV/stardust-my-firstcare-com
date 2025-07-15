// Emergency Dashboard JavaScript

let socket;
let alerts = [];
let currentAlertId = null;
let notificationPermission = false;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    loadData();
    updateTime();
    requestNotificationPermission();
    
    // Set up event listeners
    setupEventListeners();
    
    // Update time every second
    setInterval(updateTime, 1000);
    
    // Auto-refresh data every 30 seconds
    setInterval(loadData, 30000);
});

// Initialize WebSocket connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to Emergency Dashboard');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from Emergency Dashboard');
        updateConnectionStatus(false);
    });
    
    socket.on('new_emergency_alert', function(alert) {
        console.log('New emergency alert received:', alert);
        handleNewAlert(alert);
    });
    
    socket.on('alert_processed', function(data) {
        console.log('Alert processed:', data);
        handleAlertProcessed(data);
    });
    
    socket.on('connected', function(data) {
        console.log('Socket connected:', data.message);
        showNotification('Connected to Emergency Dashboard', 'success');
    });
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusIcon = document.getElementById('connection-status');
    const statusText = document.getElementById('connection-text');
    
    if (connected) {
        statusIcon.className = 'fas fa-circle text-success';
        statusText.textContent = 'Connected';
    } else {
        statusIcon.className = 'fas fa-circle text-danger';
        statusText.textContent = 'Disconnected';
    }
}

// Load emergency alerts data
async function loadData() {
    try {
        // Load alerts
        const alertsResponse = await fetch('/api/emergency-alerts');
        const alertsData = await alertsResponse.json();
        
        if (alertsData.success) {
            alerts = alertsData.alerts;
            renderAlertsTable();
        }
        
        // Load statistics
        const statsResponse = await fetch('/api/emergency-stats');
        const statsData = await statsResponse.json();
        
        if (statsData.success) {
            updateStatistics(statsData.stats);
        }
        
    } catch (error) {
        console.error('Error loading data:', error);
        showNotification('Error loading data', 'error');
    }
}

// Render alerts table
function renderAlertsTable() {
    const tbody = document.getElementById('alerts-table-body');
    
    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No emergency alerts found</td></tr>';
        return;
    }
    
    tbody.innerHTML = alerts.map(alert => createAlertRow(alert)).join('');
}

// Create alert row HTML
function createAlertRow(alert) {
    const timestamp = new Date(alert.timestamp).toLocaleString();
    const alertType = getAlertTypeBadge(alert.alert_type);
    const priority = getPriorityBadge(alert.alert_data?.priority || 'MEDIUM');
    const status = getStatusBadge(alert.processed);
    const location = getLocationDisplay(alert.alert_data?.location);
    
    return `
        <tr class="${alert.processed ? '' : 'new-alert'}" data-alert-id="${alert._id}">
            <td class="time-display">${timestamp}</td>
            <td class="patient-info">${alert.patient_name || 'Unknown'}</td>
            <td>${alertType}</td>
            <td>${priority}</td>
            <td>${status}</td>
            <td class="location-info">${location}</td>
            <td>
                <button class="btn btn-sm btn-primary btn-action" onclick="viewAlertDetails('${alert._id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                ${!alert.processed ? `
                    <button class="btn btn-sm btn-success btn-action" onclick="markAlertProcessed('${alert._id}')">
                        <i class="fas fa-check"></i> Process
                    </button>
                ` : ''}
            </td>
        </tr>
    `;
}

// Get alert type badge
function getAlertTypeBadge(type) {
    const icons = {
        'sos': 'fas fa-phone',
        'fall_down': 'fas fa-user-fall',
        'low_battery': 'fas fa-battery-quarter'
    };
    
    const icon = icons[type] || 'fas fa-exclamation-triangle';
    return `<span class="alert-type ${type}"><i class="${icon}"></i> ${type.replace('_', ' ').toUpperCase()}</span>`;
}

// Get priority badge
function getPriorityBadge(priority) {
    const priorityClass = `priority-${priority.toLowerCase()}`;
    const icons = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '⚡',
        'LOW': 'ℹ️'
    };
    
    const icon = icons[priority] || '⚡';
    return `<span class="priority-badge ${priorityClass}">${icon} ${priority}</span>`;
}

// Get status badge
function getStatusBadge(processed) {
    if (processed) {
        return '<span class="status-badge status-processed"><i class="fas fa-check"></i> Processed</span>';
    } else {
        return '<span class="status-badge status-active"><i class="fas fa-clock"></i> Active</span>';
    }
}

// Get location display
function getLocationDisplay(location) {
    if (!location) return 'No location data';
    
    if (location.GPS) {
        const lat = location.GPS.latitude?.toFixed(6) || 'N/A';
        const lng = location.GPS.longitude?.toFixed(6) || 'N/A';
        return `<span class="location-gps"><i class="fas fa-map-marker-alt"></i> ${lat}, ${lng}</span>`;
    }
    
    if (location.WiFi) {
        return '<span class="location-info"><i class="fas fa-wifi"></i> WiFi Available</span>';
    }
    
    if (location.LBS) {
        return '<span class="location-info"><i class="fas fa-mobile-alt"></i> Cell Tower</span>';
    }
    
    return 'Location data available';
}

// Update statistics
function updateStatistics(stats) {
    document.getElementById('total-alerts').textContent = stats.total_24h;
    document.getElementById('sos-count').textContent = stats.sos_count;
    document.getElementById('fall-count').textContent = stats.fall_count;
    document.getElementById('active-count').textContent = stats.active_count;
    document.getElementById('critical-count').textContent = stats.critical_count;
    document.getElementById('high-count').textContent = stats.high_count;
}

// Handle new emergency alert
function handleNewAlert(alert) {
    // Add to alerts array
    alerts.unshift(alert);
    
    // Update display
    renderAlertsTable();
    loadData(); // Refresh statistics
    
    // Show emergency banner
    showEmergencyBanner(alert);
    
    // Play sound
    playEmergencySound();
    
    // Show notification
    const message = `${alert.alert_type.toUpperCase()} Alert for ${alert.patient_name}`;
    showNotification(message, 'emergency');
    
    // Send browser notification
    sendBrowserNotification(alert);
}

// Show emergency banner
function showEmergencyBanner(alert) {
    const banner = document.getElementById('emergency-banner');
    const message = document.getElementById('emergency-message');
    
    message.textContent = `${alert.alert_type.toUpperCase()} ALERT - ${alert.patient_name} - ${alert.alert_data?.priority || 'HIGH'} PRIORITY`;
    
    banner.style.display = 'block';
    
    // Hide after 10 seconds
    setTimeout(() => {
        banner.style.display = 'none';
    }, 10000);
}

// Play emergency sound
function playEmergencySound() {
    const audio = document.getElementById('emergency-sound');
    if (audio) {
        audio.play().catch(e => console.log('Audio play failed:', e));
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Get notification icon
function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'emergency': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    return icons[type] || 'info-circle';
}

// Send browser notification
function sendBrowserNotification(alert) {
    if (!notificationPermission) return;
    
    const title = `${alert.alert_type.toUpperCase()} Alert`;
    const body = `${alert.patient_name} - ${alert.alert_data?.priority || 'HIGH'} Priority`;
    const icon = '/static/AMY_LOGO.png';
    
    new Notification(title, {
        body: body,
        icon: icon,
        tag: 'emergency-alert',
        requireInteraction: true
    });
}

// Request notification permission
async function requestNotificationPermission() {
    if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        notificationPermission = permission === 'granted';
    }
}

// View alert details
async function viewAlertDetails(alertId) {
    const alert = alerts.find(a => a._id === alertId);
    if (!alert) return;
    
    currentAlertId = alertId;
    
    const modalBody = document.getElementById('alert-modal-body');
    modalBody.innerHTML = createAlertDetailsHTML(alert);
    
    const modal = new bootstrap.Modal(document.getElementById('alertModal'));
    modal.show();
}

// Create alert details HTML
function createAlertDetailsHTML(alert) {
    const timestamp = new Date(alert.timestamp).toLocaleString();
    const location = alert.alert_data?.location;
    
    return `
        <div class="alert-details">
            <h6><i class="fas fa-user"></i> Patient Information</h6>
            <p><strong>Name:</strong> ${alert.patient_name}</p>
            <p><strong>Patient ID:</strong> ${alert.patient_id}</p>
        </div>
        
        <div class="alert-details">
            <h6><i class="fas fa-exclamation-triangle"></i> Alert Information</h6>
            <p><strong>Type:</strong> ${getAlertTypeBadge(alert.alert_type)}</p>
            <p><strong>Priority:</strong> ${getPriorityBadge(alert.alert_data?.priority || 'MEDIUM')}</p>
            <p><strong>Status:</strong> ${getStatusBadge(alert.processed)}</p>
            <p><strong>Time:</strong> <span class="timestamp">${timestamp}</span></p>
        </div>
        
        ${location ? `
            <div class="alert-details">
                <h6><i class="fas fa-map-marker-alt"></i> Location Information</h6>
                ${location.GPS ? `
                    <p><strong>GPS:</strong> ${location.GPS.latitude}, ${location.GPS.longitude}</p>
                    <p><strong>Speed:</strong> ${location.GPS.speed || 'N/A'} km/h</p>
                    <p><strong>Heading:</strong> ${location.GPS.header || 'N/A'}°</p>
                ` : ''}
                ${location.WiFi ? `<p><strong>WiFi Networks:</strong> Available</p>` : ''}
                ${location.LBS ? `
                    <p><strong>Cell Tower:</strong> MCC: ${location.LBS.MCC}, MNC: ${location.LBS.MNC}</p>
                    <p><strong>LAC:</strong> ${location.LBS.LAC}, CID: ${location.LBS.CID}</p>
                ` : ''}
            </div>
        ` : ''}
        
        <div class="alert-details">
            <h6><i class="fas fa-mobile-alt"></i> Device Information</h6>
            <p><strong>IMEI:</strong> ${alert.alert_data?.imei || 'N/A'}</p>
            <p><strong>Source:</strong> ${alert.source}</p>
        </div>
    `;
}

// Mark alert as processed
async function markAlertProcessed(alertId) {
    try {
        const response = await fetch(`/api/mark-processed/${alertId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Alert marked as processed', 'success');
            loadData(); // Refresh data
        } else {
            showNotification('Error marking alert as processed', 'error');
        }
    } catch (error) {
        console.error('Error marking alert as processed:', error);
        showNotification('Error marking alert as processed', 'error');
    }
}

// Handle alert processed event
function handleAlertProcessed(data) {
    const row = document.querySelector(`tr[data-alert-id="${data.alert_id}"]`);
    if (row) {
        row.classList.remove('new-alert');
        row.querySelector('td:nth-child(5)').innerHTML = getStatusBadge(true);
        
        // Remove process button
        const processBtn = row.querySelector('.btn-success');
        if (processBtn) {
            processBtn.remove();
        }
    }
}

// Mark all alerts as processed
async function markAllProcessed() {
    if (!confirm('Mark all active alerts as processed?')) return;
    
    const activeAlerts = alerts.filter(alert => !alert.processed);
    
    for (const alert of activeAlerts) {
        await markAlertProcessed(alert._id);
    }
    
    showNotification(`Marked ${activeAlerts.length} alerts as processed`, 'success');
}

// Refresh data
function refreshData() {
    loadData();
    showNotification('Data refreshed', 'success');
}

// Update current time
function updateTime() {
    const timeElement = document.getElementById('current-time');
    timeElement.textContent = new Date().toLocaleString();
}

// Setup event listeners
function setupEventListeners() {
    // Filter event listeners
    document.getElementById('alert-type-filter').addEventListener('change', filterAlerts);
    document.getElementById('priority-filter').addEventListener('change', filterAlerts);
    document.getElementById('status-filter').addEventListener('change', filterAlerts);
    
    // Mark processed button in modal
    document.getElementById('mark-processed-btn').addEventListener('click', function() {
        if (currentAlertId) {
            markAlertProcessed(currentAlertId);
            bootstrap.Modal.getInstance(document.getElementById('alertModal')).hide();
        }
    });
}

// Filter alerts
function filterAlerts() {
    const typeFilter = document.getElementById('alert-type-filter').value;
    const priorityFilter = document.getElementById('priority-filter').value;
    const statusFilter = document.getElementById('status-filter').value;
    
    const filteredAlerts = alerts.filter(alert => {
        const typeMatch = !typeFilter || alert.alert_type === typeFilter;
        const priorityMatch = !priorityFilter || alert.alert_data?.priority === priorityFilter;
        const statusMatch = !statusFilter || 
            (statusFilter === 'active' && !alert.processed) ||
            (statusFilter === 'processed' && alert.processed);
        
        return typeMatch && priorityMatch && statusMatch;
    });
    
    renderFilteredAlerts(filteredAlerts);
}

// Render filtered alerts
function renderFilteredAlerts(filteredAlerts) {
    const tbody = document.getElementById('alerts-table-body');
    
    if (filteredAlerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No alerts match the selected filters</td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredAlerts.map(alert => createAlertRow(alert)).join('');
}

// Export functions for global access
window.viewAlertDetails = viewAlertDetails;
window.markAlertProcessed = markAlertProcessed;
window.refreshData = refreshData;
window.markAllProcessed = markAllProcessed; 